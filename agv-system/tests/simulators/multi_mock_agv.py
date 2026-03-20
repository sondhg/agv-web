"""
Multi-AGV Simulator
Mô phỏng nhiều AGV chạy đồng thời, mỗi xe:
- Giảm pin theo thời gian (idle drain)
- Giảm pin khi di chuyển (movement drain)
- Thực hiện task từ server
- Cập nhật state liên tục qua MQTT
"""

import json
import time
import uuid
import threading
from datetime import datetime, timezone
from typing import Dict, List
import paho.mqtt.client as mqtt

# ==================== CONFIGURATION ====================
BROKER = "127.0.0.1"
PORT = 1884
MANUFACTURER = "TestManufacturer"

# Battery drain configuration
IDLE_DRAIN_RATE = 0.05  # % per second when idle
MOVING_DRAIN_RATE = 0.15  # % per second when moving
MOVING_WITH_LOAD_DRAIN_RATE = 0.25  # % per second when moving with load
TIME_PER_EDGE = 3.0  # seconds to travel one edge

# AGV initial positions (matching setup_test_agvs.py)
INITIAL_POSITIONS = {
    "AGV_01": {"node": "Node_B", "x": 10, "y": 0, "battery": 95},
    "AGV_02": {"node": "Node_C", "x": 20, "y": 0, "battery": 90},
    "AGV_03": {"node": "Node_D", "x": 30, "y": 0, "battery": 85},
    "AGV_04": {"node": "Node_A", "x": 0, "y": 0, "battery": 80},
    "AGV_05": {"node": "Node_B", "x": 10, "y": 0, "battery": 75},
    "AGV_06": {"node": "Node_C", "x": 20, "y": 0, "battery": 70},
    "AGV_07": {"node": "Node_D", "x": 30, "y": 0, "battery": 65},
}


class MockAGV:
    """Mô phỏng một AGV độc lập"""

    def __init__(self, serial_number: str, initial_config: Dict):
        self.serial_number = serial_number
        self.manufacturer = MANUFACTURER

        # MQTT setup
        self.client = mqtt.Client(
            client_id=f"mock_{serial_number}_{uuid.uuid4().hex[:4]}"
        )
        self.client.on_connect = self._on_connect
        self.client.on_message = self._on_message

        # Topics
        self.topic_connection = (
            f"uagv/v2/{self.manufacturer}/{self.serial_number}/connection"
        )
        self.topic_state = f"uagv/v2/{self.manufacturer}/{self.serial_number}/state"
        self.topic_order = f"uagv/v2/{self.manufacturer}/{self.serial_number}/order"
        self.topic_instant_action = (
            f"uagv/v2/{self.manufacturer}/{self.serial_number}/instantActions"
        )

        # State
        self.state = {
            "orderId": "",
            "lastNodeId": initial_config["node"],
            "lastNodeSequenceId": 0,
            "driving": False,
            "paused": False,
            "battery": initial_config["battery"],
            "x": initial_config["x"],
            "y": initial_config["y"],
            "nodes_to_visit": [],
            "edges_to_travel": [],
            "current_load": None,  # Track if carrying load
            "header_counter": 0,
        }

        self.running = False
        self.last_update_time = time.time()

        print(
            f"🤖 Initialized {self.serial_number} at {self.state['lastNodeId']} (Battery: {self.state['battery']}%)"
        )

    def _on_connect(self, client, userdata, flags, rc):
        """Callback when connected to MQTT broker"""
        if rc == 0:
            print(f"✅ {self.serial_number}: Connected to broker")
            # Subscribe to order and instant action topics
            client.subscribe([(self.topic_order, 1), (self.topic_instant_action, 1)])
            self._send_connection_message("ONLINE")
        else:
            print(f"❌ {self.serial_number}: Connection failed with code {rc}")

    def _on_message(self, client, userdata, msg):
        """Callback when receiving MQTT message"""
        try:
            payload = json.loads(msg.payload.decode())

            # Handle Order
            if msg.topic == self.topic_order and "nodes" in payload:
                self._handle_order(payload)

            # Handle Instant Actions
            elif msg.topic == self.topic_instant_action and "instantActions" in payload:
                self._handle_instant_actions(payload)

        except Exception as e:
            print(f"❌ {self.serial_number}: Error processing message - {e}")

    def _handle_order(self, order: Dict):
        """Process incoming order"""
        order_id = order.get("orderId", "")
        nodes = order.get("nodes", [])
        edges = order.get("edges", [])

        print(f"\n📦 {self.serial_number}: Received Order {order_id}")
        print(f"   Path: {[n['nodeId'] for n in nodes]}")

        # Update state
        self.state["orderId"] = order_id
        self.state["nodes_to_visit"] = nodes.copy()
        self.state["edges_to_travel"] = edges.copy()
        self.state["driving"] = True
        self.state["paused"] = False

        # Check if this is a pickup-delivery task
        # Simplified: assume load is picked up after first node
        if len(nodes) > 2:
            self.state["current_load"] = {
                "type": "package",
                "weight": 10,
            }  # Placeholder

    def _handle_instant_actions(self, message: Dict):
        """Process instant actions (pause, resume, cancel)"""
        actions = message.get("instantActions", [])

        for action in actions:
            action_type = action.get("actionType", "")
            action_id = action.get("actionId", "")

            print(f"\n⚡ {self.serial_number}: Instant Action - {action_type}")

            if action_type == "startPause":
                self.state["paused"] = True
                self.state["driving"] = False
                print(f"   🛑 {self.serial_number}: PAUSED")

            elif action_type == "stopPause":
                self.state["paused"] = False
                if self.state["nodes_to_visit"]:
                    self.state["driving"] = True
                print(f"   ▶️  {self.serial_number}: RESUMED")

            elif action_type == "cancelOrder":
                self.state["nodes_to_visit"] = []
                self.state["edges_to_travel"] = []
                self.state["driving"] = False
                self.state["paused"] = False
                self.state["orderId"] = ""
                self.state["current_load"] = None
                print(f"   🗑️  {self.serial_number}: ORDER CANCELLED")

    def _send_connection_message(self, status: str):
        """Send connection state to server"""
        payload = {
            "headerId": self.state["header_counter"],
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[
                :-3
            ]
            + "Z",
            "version": "2.1.0",
            "manufacturer": self.manufacturer,
            "serialNumber": self.serial_number,
            "connectionState": status,
        }
        self.client.publish(
            self.topic_connection, json.dumps(payload), qos=1, retain=True
        )
        self.state["header_counter"] += 1

    def _send_state_message(self):
        """Send current state to server"""
        payload = {
            "headerId": self.state["header_counter"],
            "timestamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[
                :-3
            ]
            + "Z",
            "version": "2.1.0",
            "manufacturer": self.manufacturer,
            "serialNumber": self.serial_number,
            "orderId": self.state["orderId"],
            "lastNodeId": self.state["lastNodeId"],
            "lastNodeSequenceId": self.state["lastNodeSequenceId"],
            "driving": self.state["driving"],
            "paused": self.state["paused"],
            "operatingMode": "AUTOMATIC",
            "batteryState": {
                "batteryCharge": round(self.state["battery"], 2),
                "batteryVoltage": 48.0,
                "charging": False,
                "reach": 100 - self.state["battery"],  # Simple reach estimation
            },
            "agvPosition": {
                "x": self.state["x"],
                "y": self.state["y"],
                "theta": 0.0,
                "mapId": "default_map",
                "positionInitialized": True,
            },
            "velocity": {
                "vx": 1.0 if self.state["driving"] else 0.0,
                "vy": 0.0,
                "omega": 0.0,
            },
            "loads": [self.state["current_load"]] if self.state["current_load"] else [],
            "safetyState": {"eStop": "NONE", "fieldViolation": False},
            "errors": [],
            "information": [],
        }

        self.client.publish(self.topic_state, json.dumps(payload), qos=0)
        self.state["header_counter"] += 1

    def _update_battery(self, delta_time: float):
        """Update battery based on current activity"""
        if self.state["battery"] <= 0:
            self.state["battery"] = 0
            self.state["driving"] = False
            print(f"🔋 {self.serial_number}: BATTERY DEPLETED!")
            return

        # Calculate drain rate
        if self.state["driving"]:
            if self.state["current_load"]:
                drain_rate = MOVING_WITH_LOAD_DRAIN_RATE
            else:
                drain_rate = MOVING_DRAIN_RATE
        else:
            drain_rate = IDLE_DRAIN_RATE

        # Apply drain
        drain = drain_rate * delta_time
        self.state["battery"] = max(0, self.state["battery"] - drain)

    def _simulate_movement(self):
        """Simulate AGV movement along path"""
        if not self.state["driving"] or self.state["paused"]:
            return

        if not self.state["nodes_to_visit"]:
            # Completed all nodes
            self.state["driving"] = False
            self.state["current_load"] = None
            print(
                f"🏁 {self.serial_number}: Reached destination at {self.state['lastNodeId']}"
            )
            return

        # Move to next node
        next_node = self.state["nodes_to_visit"][0]
        node_id = next_node["nodeId"]

        # Update position
        if "nodePosition" in next_node:
            self.state["x"] = next_node["nodePosition"].get("x", self.state["x"])
            self.state["y"] = next_node["nodePosition"].get("y", self.state["y"])

        self.state["lastNodeId"] = node_id
        self.state["lastNodeSequenceId"] = next_node.get("sequenceId", 0)

        # Remove visited node
        self.state["nodes_to_visit"].pop(0)

        # Remove traveled edge if exists
        if self.state["edges_to_travel"]:
            self.state["edges_to_travel"].pop(0)

        print(
            f"🚚 {self.serial_number}: Arrived at {node_id} (Battery: {self.state['battery']:.1f}%)"
        )

        # Execute actions at node
        actions = next_node.get("actions", [])
        for action in actions:
            action_type = action.get("actionType", "")
            if action_type == "pick":
                self.state["current_load"] = {"type": "package", "weight": 10}
                print(f"   📦 {self.serial_number}: Picked up load at {node_id}")
            elif action_type == "drop":
                self.state["current_load"] = None
                print(f"   📭 {self.serial_number}: Dropped load at {node_id}")

    def start(self):
        """Start AGV simulation"""
        self.running = True
        self.client.connect(BROKER, PORT, 60)
        self.client.loop_start()

        # Simulation loop
        thread = threading.Thread(target=self._simulation_loop, daemon=True)
        thread.start()

    def _simulation_loop(self):
        """Main simulation loop"""
        while self.running:
            current_time = time.time()
            delta_time = current_time - self.last_update_time
            self.last_update_time = current_time

            # Update battery
            self._update_battery(delta_time)

            # Simulate movement
            if self.state["driving"] and not self.state["paused"]:
                # Wait appropriate time before moving to next node
                time.sleep(TIME_PER_EDGE)
                self._simulate_movement()

            # Send state update
            self._send_state_message()

            # Sleep for a bit (send state every 2 seconds)
            time.sleep(2)

    def stop(self):
        """Stop AGV simulation"""
        self.running = False
        self._send_connection_message("OFFLINE")
        self.client.loop_stop()
        self.client.disconnect()
        print(f"🛑 {self.serial_number}: Stopped")


class MultiAGVSimulator:
    """Manage multiple mock AGVs"""

    def __init__(self, agv_configs: Dict[str, Dict]):
        self.agvs: List[MockAGV] = []

        for serial_number, config in agv_configs.items():
            agv = MockAGV(serial_number, config)
            self.agvs.append(agv)

    def start_all(self):
        """Start all AGVs"""
        print(f"\n{'=' * 60}")
        print(f"🚀 Starting {len(self.agvs)} AGVs...")
        print(f"{'=' * 60}\n")

        for agv in self.agvs:
            agv.start()
            time.sleep(0.2)  # Small delay between starts

        print("\n✅ All AGVs started successfully!")
        print("📊 Monitoring... (Press Ctrl+C to stop)\n")

    def stop_all(self):
        """Stop all AGVs"""
        print(f"\n{'=' * 60}")
        print("🛑 Stopping all AGVs...")
        print(f"{'=' * 60}\n")

        for agv in self.agvs:
            agv.stop()

        print("\n✅ All AGVs stopped")

    def print_status(self):
        """Print status of all AGVs"""
        print(f"\n{'=' * 60}")
        print("📊 AGV FLEET STATUS")
        print(f"{'=' * 60}")

        for agv in self.agvs:
            status = "🚚 Moving" if agv.state["driving"] else "⏸️  Idle"
            load = "📦 Loaded" if agv.state["current_load"] else "⬜ Empty"
            battery = agv.state["battery"]
            battery_icon = "🔋" if battery > 50 else "🪫" if battery > 20 else "⚠️ "

            print(
                f"  {agv.serial_number}: {status} | {load} | "
                f"{battery_icon} {battery:.1f}% | "
                f"@ {agv.state['lastNodeId']}"
            )

        print(f"{'=' * 60}\n")


def main():
    """Main entry point"""
    print(f"\n{'=' * 60}")
    print("🤖 Multi-AGV Simulator")
    print(f"{'=' * 60}")
    print("Configuration:")
    print(f"  - MQTT Broker: {BROKER}:{PORT}")
    print(f"  - Number of AGVs: {len(INITIAL_POSITIONS)}")
    print(f"  - Idle drain: {IDLE_DRAIN_RATE}%/s")
    print(f"  - Moving drain: {MOVING_DRAIN_RATE}%/s")
    print(f"  - Moving with load drain: {MOVING_WITH_LOAD_DRAIN_RATE}%/s")
    print(f"{'=' * 60}\n")

    # Create simulator
    simulator = MultiAGVSimulator(INITIAL_POSITIONS)

    try:
        # Start all AGVs
        simulator.start_all()

        # Monitor status periodically
        while True:
            time.sleep(30)  # Print status every 30 seconds
            simulator.print_status()

    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupt received...")
        simulator.stop_all()
        print("\n👋 Goodbye!\n")


if __name__ == "__main__":
    main()
