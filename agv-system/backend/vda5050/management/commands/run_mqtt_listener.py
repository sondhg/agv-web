import json
import logging
import os
import uuid
from datetime import datetime
from django.core.management.base import BaseCommand
from django.utils import timezone
import paho.mqtt.client as mqtt
from vda5050.models import AGV, AGVState, Order
from vda5050.graph_engine import GraphEngine
from vda5050.modules.battery_manager import BatteryManager
from vda5050.modules.deadlock import DeadlockMonitorService
from vda5050.modules.reservation import ReservationService

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Listen to MQTT messages from AGVs (VDA5050 protocol)"

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS("Starting MQTT Listener..."))
        self.graph_engine = GraphEngine()
        self.deadlock_monitor = DeadlockMonitorService(
            stuck_threshold_s=float(os.environ.get("DEADLOCK_STUCK_THRESHOLD_S", "45")),
            position_epsilon_m=float(os.environ.get("DEADLOCK_POSITION_EPS_M", "0.2")),
        )
        self.reservation_service = ReservationService()
        self.battery_manager = BatteryManager()
        self._progress_cache = {}
        self._telemetry_cache = {}
        self._eta_speed_mps = float(os.environ.get("AGV_PROGRESS_ETA_SPEED_MPS", "10.0"))
        self._horizon_release_window_seq = int(
            os.environ.get("HORIZON_RELEASE_WINDOW_SEQ", "4")
        )
        self._state_persist_heartbeat_s = float(
            os.environ.get("STATE_PERSIST_HEARTBEAT_S", "5")
        )
        self._state_position_delta_m = float(
            os.environ.get("STATE_PERSIST_POSITION_DELTA_M", "0.5")
        )
        self._state_battery_delta_pct = float(
            os.environ.get("STATE_PERSIST_BATTERY_DELTA_PCT", "1.0")
        )

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

        if timezone.is_naive(ts_obj):
            ts_obj = timezone.make_aware(ts_obj, timezone.get_current_timezone())

        # Build state snapshot once; decide later whether to persist it.
        state_data = dict(
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

        should_persist, persist_reason = self.should_persist_state(
            serial_number,
            payload,
            ts_obj,
        )

        if should_persist:
            state = AGVState.objects.create(**state_data)
            logger.debug(
                "Persisted state for %s (reason=%s)",
                serial_number,
                persist_reason,
            )
        else:
            # Keep realtime processing while skipping DB write for high-frequency frames.
            state = AGVState(**state_data)
            self.check_battery_from_state(agv, state)

        self.update_telemetry_cache(serial_number, payload, ts_obj, should_persist)

        # 3. Update Order status based on AGVState
        # Use order_id from payload to identify the running order
        current_order_id = payload.get("orderId")

        self.check_deadlock_monitor(agv, state, current_order_id)

        # If the AGV is running an Order (has ID)
        if state.order_id:
            self.update_order_status(agv, state, current_order_id)

        # Special case: AGV reports without orderId (finished)
        # Or just finished an order, check queue once more
        if not state.driving and (not current_order_id or current_order_id == ""):
            self.check_and_process_queue(agv)

    @staticmethod
    def _safe_float(value):
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _safe_int(value, default=0):
        try:
            return int(value)
        except (TypeError, ValueError):
            return default

    def _extract_battery_charge(self, payload):
        battery = payload.get("batteryState") or {}
        for key in ("charge", "batteryCharge", "battery_charge"):
            value = self._safe_float(battery.get(key))
            if value is not None:
                return value
        return None

    def _is_safety_event(self, payload):
        safety = payload.get("safetyState") or {}
        if bool(safety.get("fieldViolation")):
            return True

        estop = str(safety.get("eStop") or "").upper()
        return estop not in {"", "NONE", "NO_STOP"}

    def should_persist_state(self, serial_number, payload, ts_obj):
        cache = self._telemetry_cache.get(serial_number)
        if not cache:
            return True, "first_state"

        prev_snapshot = cache.get("last_seen") or {}
        last_persist_ts = cache.get("last_persist_ts")

        current_order_id = payload.get("orderId") or ""
        current_node_id = payload.get("lastNodeId") or ""
        current_seq = self._safe_int(payload.get("lastNodeSequenceId"), 0)
        current_driving = bool(payload.get("driving", False))
        current_paused = bool(payload.get("paused", False))
        current_errors = bool(payload.get("errors") or [])
        current_charging = bool((payload.get("batteryState") or {}).get("charging"))
        current_battery = self._extract_battery_charge(payload)
        current_pos = payload.get("agvPosition") or {}
        current_x = self._safe_float(current_pos.get("x"))
        current_y = self._safe_float(current_pos.get("y"))

        if current_errors:
            return True, "errors"
        if self._is_safety_event(payload):
            return True, "safety_event"

        if current_order_id != (prev_snapshot.get("order_id") or ""):
            return True, "order_changed"
        if current_node_id != (prev_snapshot.get("node_id") or ""):
            return True, "node_changed"
        if current_seq != self._safe_int(prev_snapshot.get("sequence_id"), 0):
            return True, "sequence_changed"
        if current_driving != bool(prev_snapshot.get("driving", False)):
            return True, "driving_changed"
        if current_paused != bool(prev_snapshot.get("paused", False)):
            return True, "paused_changed"
        if current_charging != bool(prev_snapshot.get("charging", False)):
            return True, "charging_changed"

        prev_battery = prev_snapshot.get("battery")
        if (
            current_battery is not None
            and prev_battery is not None
            and abs(current_battery - prev_battery) >= self._state_battery_delta_pct
        ):
            return True, "battery_delta"

        prev_x = prev_snapshot.get("x")
        prev_y = prev_snapshot.get("y")
        if (
            current_x is not None
            and current_y is not None
            and prev_x is not None
            and prev_y is not None
        ):
            dx = current_x - prev_x
            dy = current_y - prev_y
            if (dx * dx + dy * dy) ** 0.5 >= self._state_position_delta_m:
                return True, "position_delta"

        if last_persist_ts is None:
            return True, "first_persist"

        elapsed_s = (ts_obj - last_persist_ts).total_seconds()
        if elapsed_s >= self._state_persist_heartbeat_s:
            return True, "heartbeat"

        return False, "sampled_out"

    def update_telemetry_cache(self, serial_number, payload, ts_obj, persisted):
        battery_state = payload.get("batteryState") or {}
        position = payload.get("agvPosition") or {}

        snapshot = {
            "order_id": payload.get("orderId") or "",
            "node_id": payload.get("lastNodeId") or "",
            "sequence_id": self._safe_int(payload.get("lastNodeSequenceId"), 0),
            "driving": bool(payload.get("driving", False)),
            "paused": bool(payload.get("paused", False)),
            "charging": bool(battery_state.get("charging")),
            "battery": self._extract_battery_charge(payload),
            "x": self._safe_float(position.get("x")),
            "y": self._safe_float(position.get("y")),
        }

        cache = self._telemetry_cache.get(serial_number) or {}
        cache["last_seen"] = snapshot
        if persisted or cache.get("last_persist_ts") is None:
            cache["last_persist_ts"] = ts_obj
        self._telemetry_cache[serial_number] = cache

    def check_battery_from_state(self, agv, state):
        """Run battery manager for non-persisted frames (persisted frames use signal)."""
        battery_data = state.battery_state or {}
        if battery_data.get("charging") is True:
            return

        current_battery = battery_data.get("charge")
        if current_battery is None:
            current_battery = battery_data.get("batteryCharge")
        if current_battery is None:
            current_battery = battery_data.get("battery_charge")
        if current_battery is None:
            return

        try:
            current_battery = float(current_battery)
        except (TypeError, ValueError):
            return

        try:
            self.battery_manager.check_and_charge(
                agv=agv,
                current_battery=current_battery,
                current_node_id=state.last_node_id,
            )
        except Exception as exc:
            logger.error(
                "Battery manager failed for %s: %s",
                agv.serial_number,
                exc,
            )

    def check_deadlock_monitor(self, agv, state, current_order_id):
        """Run server-side deadlock monitor and emit potential events."""
        try:
            monitor_result = self.deadlock_monitor.process_state(
                agv=agv,
                state=state,
                order_id=current_order_id,
            )
            if monitor_result:
                logger.warning(
                    "[DeadlockMonitor] event_id=%s created=%s agv=%s order_id=%s node=%s sequence=%s stuck=%.2fs",
                    monitor_result["event_id"],
                    monitor_result["created"],
                    agv.serial_number,
                    monitor_result["order_id"],
                    monitor_result["node_id"],
                    monitor_result["sequence_id"],
                    monitor_result["stuck_duration_s"],
                )
        except Exception as exc:
            logger.error("Deadlock monitor failed for %s: %s", agv.serial_number, exc)

    def update_order_status(self, agv, state, current_order_id):
        """Logic to update Order status and trigger Queue if done"""
        try:
            order = Order.objects.get(order_id=current_order_id, agv=agv)
            self.log_order_progress(agv, state, order)
            self.maybe_release_horizon_segment(agv, state, order)

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
                            self.reservation_service.release_order_reservations(
                                order,
                                reason="order_rejected",
                            )
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

                # Compare with AGV reports
                # Note: VDA standard checks both sequenceId to avoid duplicate loops
                if state.last_node_id == last_node_in_order and not state.driving:
                    if order.status != Order.OrderStatus.COMPLETED:
                        order.status = Order.OrderStatus.COMPLETED
                        order.save()
                        self.reservation_service.release_order_reservations(
                            order,
                            reason="order_completed",
                        )
                        logger.info(f"Order {order.order_id} COMPLETED!")

                        self.check_and_process_queue(agv)

        except Order.DoesNotExist:
            pass  # No matching order found

    def maybe_release_horizon_segment(self, agv, state, order):
        """Progressively release additional route segments for horizon-based orders."""
        if not order.nodes or not order.edges:
            return

        current_seq = int(state.last_node_sequence_id or 0)
        release_upto_seq = current_seq + max(self._horizon_release_window_seq, 2)

        node_updates = []
        node_changed = False
        for node in order.nodes:
            node_copy = dict(node)
            node_seq = int(node_copy.get("sequenceId", 0))
            if not bool(node_copy.get("released", True)) and node_seq <= release_upto_seq:
                node_copy["released"] = True
                node_changed = True
            node_updates.append(node_copy)

        edge_updates = []
        edge_changed = False
        for edge in order.edges:
            edge_copy = dict(edge)
            edge_seq = int(edge_copy.get("sequenceId", 0))
            if not bool(edge_copy.get("released", True)) and edge_seq <= release_upto_seq:
                edge_copy["released"] = True
                edge_changed = True
            edge_updates.append(edge_copy)

        if not (node_changed or edge_changed):
            return

        order.nodes = node_updates
        order.edges = edge_updates
        order.order_update_id = int(order.order_update_id or 0) + 1
        order.save(update_fields=["nodes", "edges", "order_update_id", "updated_at"])
        self.publish_order_update(order)

        logger.info(
            "[HorizonRelease] order_id=%s agv=%s released_upto_seq=%s update_id=%s",
            order.order_id,
            agv.serial_number,
            release_upto_seq,
            order.order_update_id,
        )

    def estimate_remaining_eta_s(self, order, current_node_id):
        """Estimate remaining travel ETA to the order final node."""
        if not order.nodes or not current_node_id:
            return None

        final_node = order.nodes[-1].get("nodeId")
        if not final_node or final_node == current_node_id:
            return 0.0

        remaining_distance = self.graph_engine.get_path_cost(current_node_id, final_node)
        if remaining_distance == float("inf"):
            return None

        eta = remaining_distance / max(self._eta_speed_mps, 0.1)
        return round(eta, 2)

    def log_order_progress(self, agv, state, order):
        """Log order progress with context for debugging and traceability."""
        cache_key = agv.serial_number
        current_seq = int(state.last_node_sequence_id or 0)
        current_node = state.last_node_id or ""
        current_driving = bool(state.driving)

        prev = self._progress_cache.get(cache_key)
        if prev == (order.order_id, current_seq, current_node, current_driving):
            return

        eta_s = self.estimate_remaining_eta_s(order, current_node)
        eta_str = "unknown" if eta_s is None else f"{eta_s:.2f}s"

        logger.info(
            "[OrderProgress] order_id=%s agv=%s sequence=%s node=%s driving=%s eta=%s",
            order.order_id,
            agv.serial_number,
            current_seq,
            current_node,
            current_driving,
            eta_str,
        )

        self._progress_cache[cache_key] = (
            order.order_id,
            current_seq,
            current_node,
            current_driving,
        )

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

    def publish_order_update(self, order):
        """Publish order update with incremented orderUpdateId."""
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
            self.mqtt_client.publish(topic, json.dumps(payload), qos=1)
        except Exception as exc:
            logger.error("Failed to publish order update %s: %s", order.order_id, exc)

    def on_disconnect(self, client, userdata, rc):
        if rc != 0:
            logger.warning(f"Unexpected disconnection: {rc}")
