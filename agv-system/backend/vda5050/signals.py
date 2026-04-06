import json
import logging
import uuid 
import paho.mqtt.client as mqtt
import os
from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import AGVState, InstantAction, Order
from .modules.battery_manager import BatteryManager

logger = logging.getLogger(__name__)

# Get MQTT configuration from environment variables
MQTT_BROKER = os.environ.get('MQTT_BROKER', 'mqtt')
MQTT_PORT = int(os.environ.get('MQTT_PORT', '1883'))

def publish_mqtt_message(topic, payload, description):
    """Common function to safely send MQTT messages"""
    client_id = f"django_pub_{uuid.uuid4().hex[:8]}" 
    client = mqtt.Client(client_id=client_id)
    
    try:
        # 1. Connect
        logger.info(f"Connecting to Broker {MQTT_BROKER}:{MQTT_PORT}...")
        client.connect(MQTT_BROKER, MQTT_PORT, 5) 
        
        # 2. Publish message
        client.publish(topic, json.dumps(payload), qos=1)
        
        # 3. Disconnect
        client.disconnect()
        logger.info(f"Sent {description} to {topic}")
        return True
        
    except Exception as e:
        logger.error(f"FAILED to send {description}: {e}")
        return False

# --- SIGNAL: SEND ORDER ---
@receiver(post_save, sender=Order)
def on_order_created(sender, instance, created, **kwargs):
    if created and instance.status == 'CREATED':
        agv = instance.agv
        topic = f"uagv/v2/{agv.manufacturer}/{agv.serial_number}/order"
        
        payload = {
            "headerId": instance.header_id,
            "timestamp": instance.timestamp.isoformat(),
            "version": "2.1.0",
            "manufacturer": agv.manufacturer,
            "serialNumber": agv.serial_number,
            "orderId": instance.order_id,
            "orderUpdateId": instance.order_update_id,
            "zoneSetId": instance.zone_set_id,
            "nodes": instance.nodes,
            "edges": instance.edges
        }

        if publish_mqtt_message(topic, payload, f"Order {instance.order_id}"):
            # Update status to SENT
            Order.objects.filter(pk=instance.pk).update(status='SENT')

# --- SIGNAL: SEND INSTANT ACTION ---
@receiver(post_save, sender=InstantAction)
def on_action_created(sender, instance, created, **kwargs):
    if created and not instance.is_sent:
        agv = instance.agv
        topic = f"uagv/v2/{agv.manufacturer}/{agv.serial_number}/instantActions"
        
        payload = {
            "headerId": instance.header_id,
            "timestamp": instance.timestamp.isoformat(),
            "version": "2.1.0",
            "manufacturer": agv.manufacturer,
            "serialNumber": agv.serial_number,
            "instantActions": [
                {
                    "actionType": instance.action_type,
                    "actionId": instance.action_id,
                    "actionParameters": instance.action_parameters,
                    "blockingType": "HARD"
                }
            ]
        }

        # If successfully sent, then update DB
        if publish_mqtt_message(topic, payload, f"Action {instance.action_type}"):
            # Use .update() to write directly to DB, avoiding race condition
            InstantAction.objects.filter(pk=instance.pk).update(is_sent=True)
            logger.info(f"Database updated: InstantAction {instance.action_id} marked as SENT")


@receiver(post_save, sender=AGVState)
def check_agv_battery_state(sender, instance, created, **kwargs):
    """Check AGV battery after each state save and trigger auto-charging when needed."""
    agv = instance.agv
    current_node_id = instance.last_node_id

    # AGVState stores battery data in JSON field `battery_state`.
    battery_data = instance.battery_state or {}
    current_battery = battery_data.get("charge")

    # Fallback keys for compatibility with different payload formats.
    if current_battery is None:
        current_battery = battery_data.get("batteryCharge")
    if current_battery is None:
        current_battery = battery_data.get("battery_charge")

    # If AGV is already charging, do not create any charging order.
    if battery_data.get("charging") is True:
        return

    # If battery value is unavailable or invalid, skip auto-charging safely.
    if current_battery is None:
        return

    try:
        current_battery = float(current_battery)
    except (TypeError, ValueError):
        return

    try:
        battery_mgr = BatteryManager()
        battery_mgr.check_and_charge(
            agv=agv,
            current_battery=current_battery,
            current_node_id=current_node_id,
        )
    except Exception as e:
        print(f"[SIGNALS] Lỗi khi check battery: {e}")