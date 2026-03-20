import json
import logging
import os
import uuid
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
import paho.mqtt.client as mqtt
from vda5050.models import AGV, AGVState, Order

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Listen to MQTT messages from AGVs (VDA5050 protocol)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting MQTT Listener..."))

        mqtt_broker = os.environ.get("MQTT_BROKER", "mqtt")
        mqtt_port = int(os.environ.get("MQTT_PORT", "1883"))

        # Create a random Client ID to avoid conflicts when restarting the container
        client_id = f"django_worker_{uuid.uuid4().hex[:8]}"
        self.mqtt_client = mqtt.Client(client_id=client_id)

        self.mqtt_client.on_connect = self.on_connect
        self.mqtt_client.on_message = self.on_message
        self.mqtt_client.on_disconnect = self.on_disconnect

        try:
            self.stdout.write(
                f"Connecting to {mqtt_broker}:{mqtt_port} as {client_id}..."
            )
            self.mqtt_client.connect(mqtt_broker, mqtt_port, 60)
            self.mqtt_client.loop_forever()
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING("\nShutting down..."))
            self.mqtt_client.disconnect()
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Fatal Error: {e}"))

    def on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self.stdout.write(self.style.SUCCESS("✓ MQTT Connected"))
            # Subscribe to all AGVs
            topics = [
                ("uagv/v2/+/+/state", 0),
                ("uagv/v2/+/+/connection", 0),
            ]
            client.subscribe(topics)
        else:
            self.stdout.write(self.style.ERROR(f"Connection failed: {rc}"))

    def on_message(self, client, userdata, msg):
        try:
            # Topic: uagv/v2/{manufacturer}/{serial_number}/{type}
            parts = msg.topic.split("/")
            if len(parts) < 5:
                return

            manufacturer, serial_number, msg_type = parts[2], parts[3], parts[4]

            payload = json.loads(msg.payload.decode("utf-8"))

            if msg_type == "state":
                self.handle_state(manufacturer, serial_number, payload)
            elif msg_type == "connection":
                self.handle_connection(manufacturer, serial_number, payload)

        except Exception as e:
            logger.error(f"Error processing {msg.topic}: {e}")

    def handle_state(self, manufacturer, serial_number, payload):
        # 1. Find or Create AGV
        agv, created = AGV.objects.get_or_create(
            manufacturer=manufacturer,
            serial_number=serial_number,
            defaults={"is_online": True},
        )
        if created:
            # Update version info if available
            logger.info(f"New AGV discovered: {serial_number}")

        # Update last seen time
        agv.last_seen = timezone.now()
        if payload.get("agvPosition"):
            agv.current_map_id = payload["agvPosition"].get("mapId")
        agv.save()

        # ISO8601 timestamp parsing
        ts_str = payload.get("timestamp")
        if ts_str:
            if ts_str.endswith("Z"):
                ts_str = ts_str.replace("Z", "+00:00")
            try:
                ts_obj = datetime.fromisoformat(ts_str)
            except ValueError:
                ts_obj = timezone.now()
        else:
            ts_obj = timezone.now()

        # 2. Create AGVState log
        state = AGVState.objects.create(
            agv=agv,
            header_id=payload.get("headerId", 0),
            timestamp=ts_obj,
            order_id=payload.get("orderId"),
            last_node_id=payload.get("lastNodeId"),
            last_node_sequence_id=payload.get("lastNodeSequenceId", 0),
            driving=payload.get("driving", False),
            paused=payload.get("paused", False),
            operating_mode=payload.get("operatingMode"),
            battery_state=payload.get("batteryState", {}),
            agv_position=payload.get("agvPosition", {}),
            velocity=payload.get("velocity", {}),
            safety_state=payload.get("safetyState", {}),
            errors=payload.get("errors", []),
            loads=payload.get("loads", []),
            information=payload.get("information", {}),
        )

        # 3. Update Order status based on AGVState
        # Use order_id from payload to identify the running order
        current_order_id = payload.get("orderId")

        # If the AGV is running an Order (has ID)
        if state.order_id:
            self.update_order_status(agv, state, current_order_id)

        # Special case: AGV reports without orderId (finished)
        # Or just finished an order, check queue once more
        if not state.driving and (not current_order_id or current_order_id == ""):
            self.check_and_process_queue(agv)

    def update_order_status(self, agv, state, current_order_id):
        """Logic to update Order status and trigger Queue if done"""
        try:
            order = Order.objects.get(order_id=current_order_id, agv=agv)

            # Handle Rejection (AGV reports error -> Server marks Order as rejected)
            if state.errors:
                for err in state.errors:
                    # Error types related to Order (Validation, No Route...)
                    # Refer to VDA 5050 specs for Error types
                    if err.get("errorType") in [
                        "orderError",
                        "validationError",
                        "noRouteError",
                    ]:
                        if order.status != Order.OrderStatus.REJECTED:
                            order.status = Order.OrderStatus.REJECTED
                            order.rejection_reason = (
                                f"{err.get('errorType')}: {err.get('errorDescription')}"
                            )
                            order.save()
                            logger.warning(
                                f"Order {order.order_id} REJECTED by AGV: {order.rejection_reason}"
                            )
                        return  # Stop processing if already rejected

            # Handle Active
            if order.status == Order.OrderStatus.SENT:
                # If AGV reports running this order -> Change to ACTIVE
                order.status = Order.OrderStatus.ACTIVE
                order.save()
                logger.info(f"Order {order.order_id} is now ACTIVE")

            # Handle Completed
            # If current position matches final node of order -> mark as COMPLETED
            # AND Driving = FALSE
            if order.nodes:  # Make sure order has nodes
                last_node_in_order = order.nodes[-1]["nodeId"]  # Lấy ID node cuối
                last_seq_id = order.nodes[-1]["sequenceId"]

                # Compare with AGV reports
                # Note: VDA standard checks both sequenceId to avoid duplicate loops
                if state.last_node_id == last_node_in_order and not state.driving:
                    if order.status != Order.OrderStatus.COMPLETED:
                        order.status = Order.OrderStatus.COMPLETED
                        order.save()
                        logger.info(f"Order {order.order_id} COMPLETED!")

                        self.check_and_process_queue(agv)

        except Order.DoesNotExist:
            pass  # No matching order found

    def check_and_process_queue(self, agv):
        """Check and send next queued order if available"""
        # Get the next queued order
        next_order = (
            Order.objects.filter(agv=agv, status="QUEUED")
            .order_by("created_at")
            .first()
        )

        if next_order:
            logger.info(
                f"Found queued order {next_order.order_id} for {agv.serial_number}. Dispatching now..."
            )

            # Send this order
            self.publish_order(next_order)

    def handle_connection(self, manufacturer, serial_number, payload):
        try:
            agv = AGV.objects.get(
                manufacturer=manufacturer, serial_number=serial_number
            )
            status = payload.get("connectionState")
            agv.is_online = status == "ONLINE"
            agv.save()
            logger.info(f"AGV {serial_number} is {status}")
        except AGV.DoesNotExist:
            pass

    def publish_order(self, order):
        """Send order to AGV via MQTT"""
        agv = order.agv
        topic = f"uagv/v2/{agv.manufacturer}/{agv.serial_number}/order"

        payload = {
            "headerId": order.header_id,
            "timestamp": timezone.now().isoformat(),
            "version": "2.1.0",
            "manufacturer": agv.manufacturer,
            "serialNumber": agv.serial_number,
            "orderId": order.order_id,
            "orderUpdateId": order.order_update_id,
            "zoneSetId": order.zone_set_id,
            "nodes": order.nodes,
            "edges": order.edges,
        }

        try:
            # Use the currently running MQTT client to publish
            self.mqtt_client.publish(topic, json.dumps(payload), qos=1)

            # Update order status
            order.status = "SENT"
            order.save()
            logger.info(
                f"Dispatched Queued Order {order.order_id} to {agv.serial_number}"
            )
        except Exception as e:
            logger.error(f"Failed to dispatch queued order: {e}")

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning(f"Unexpected disconnection: {rc}")
