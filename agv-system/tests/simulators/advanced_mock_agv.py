"""
Advanced Mock AGV Simulator - VDA5050 Compliant.

Features:
- Kinematic model: velocity-based movement with rotation
- Energy model: battery consumption for moving, rotating, idle
- VDA5050 state publishing at 1 Hz
- Base/Horizon handling (released vs unreleased nodes)
- Order chaining support
- Battery constraints (critical/low thresholds)
- Pick/drop action simulation
"""

import json
import math
import time
import uuid
import logging
import threading
from datetime import datetime, timezone
from typing import Optional

import paho.mqtt.client as mqtt

from config_energy import ENERGY, EnergyConfig
from config_sim import (
    MQTT_BROKER,
    MQTT_PORT,
    VDA_VERSION,
    MANUFACTURER,
    MAP_ID,
    NODE_POSITIONS,
    STATE_PUBLISH_INTERVAL,
    MOVEMENT_TICK_INTERVAL,
)

logger = logging.getLogger(__name__)


class AdvancedMockAGV:
    """
    A single AGV simulator with kinematic movement, energy model,
    and full VDA5050 state/order compliance.
    """

    # AGV operating states
    STATE_IDLE = "IDLE"
    STATE_MOVING = "MOVING"
    STATE_ROTATING = "ROTATING"
    STATE_WAITING = "WAITING_FOR_PERMISSION"
    STATE_EXECUTING_ACTION = "EXECUTING_ACTION"
    STATE_CHARGING = "CHARGING"
    STATE_PAUSED = "PAUSED"
    STATE_ERROR = "ERROR"

    def __init__(
        self,
        serial_number: str,
        initial_node: str,
        initial_battery: float = 95.0,
        energy_config: Optional[EnergyConfig] = None,
        on_order_complete: Optional[callable] = None,
        on_state_change: Optional[callable] = None,
    ):
        self.serial_number = serial_number
        self.manufacturer = MANUFACTURER
        self.energy = energy_config or ENERGY

        # Callbacks for metrics collection
        self._on_order_complete = on_order_complete
        self._on_state_change = on_state_change

        # Position & kinematic state
        node_pos = NODE_POSITIONS.get(initial_node, {"x": 0, "y": 0})
        self.x: float = float(node_pos["x"])
        self.y: float = float(node_pos["y"])
        self.theta: float = 0.0  # degrees
        self.last_node_id: str = initial_node
        self.last_node_seq_id: int = 0

        # Battery
        self.battery: float = initial_battery
        self.is_charging: bool = False
        self.charge_rate_pct_per_s: float = 1.0

        # Operating state
        self.op_state: str = self.STATE_IDLE
        self.driving: bool = False
        self.paused: bool = False

        # Current order
        self.order_id: str = ""
        self.order_nodes: list = []
        self.order_edges: list = []
        self.current_node_index: int = 0
        self.current_load: Optional[dict] = None

        # Metrics for current order
        self._order_start_time: float = 0.0
        self._order_energy_start: float = 0.0
        self._total_wait_time: float = 0.0
        self._total_move_time: float = 0.0
        self._total_distance: float = 0.0

        # Movement interpolation state
        self._move_start_x: float = self.x
        self._move_start_y: float = self.y
        self._move_target_x: float = self.x
        self._move_target_y: float = self.y
        self._move_progress: float = 0.0
        self._move_distance: float = 0.0
        self._is_interpolating: bool = False

        # Errors
        self.errors: list = []

        # MQTT
        self._client = mqtt.Client(
            client_id=f"adv_mock_{serial_number}_{uuid.uuid4().hex[:4]}"
        )
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message

        # Topics
        self._topic_conn = f"uagv/v2/{self.manufacturer}/{self.serial_number}/connection"
        self._topic_state = f"uagv/v2/{self.manufacturer}/{self.serial_number}/state"
        self._topic_order = f"uagv/v2/{self.manufacturer}/{self.serial_number}/order"
        self._topic_action = f"uagv/v2/{self.manufacturer}/{self.serial_number}/instantActions"

        # Threading
        self._running = False
        self._header_counter = 0
        self._lock = threading.Lock()

        logger.info(
            f"[{self.serial_number}] Initialized at {initial_node} "
            f"({self.x}, {self.y}) battery={initial_battery}%"
        )

    # ==================== MQTT Callbacks ====================

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            logger.info(f"[{self.serial_number}] Connected to MQTT broker")
            client.subscribe([(self._topic_order, 1), (self._topic_action, 1)])
            self._publish_connection("ONLINE")
        else:
            logger.error(f"[{self.serial_number}] MQTT connection failed: rc={rc}")

    def _on_message(self, client, userdata, msg):
        try:
            payload = json.loads(msg.payload.decode())

            if msg.topic == self._topic_order and "nodes" in payload:
                self._handle_order(payload)
            elif msg.topic == self._topic_action and "instantActions" in payload:
                self._handle_instant_actions(payload)
        except Exception as e:
            logger.error(f"[{self.serial_number}] Message error: {e}")

    # ==================== Order Handling ====================

    def _handle_order(self, order: dict):
        order_id = order.get("orderId", "")
        nodes = order.get("nodes", [])
        edges = order.get("edges", [])

        logger.info(
            f"[{self.serial_number}] Received Order {order_id} "
            f"({len(nodes)} nodes, {len(edges)} edges)"
        )

        with self._lock:
            self.is_charging = False
            self.order_id = order_id
            self.order_nodes = nodes
            self.order_edges = edges
            self.current_node_index = 0
            self.driving = True
            self.paused = False
            self.op_state = self.STATE_MOVING
            self.errors = []

            # Reset order metrics
            self._order_start_time = time.time()
            self._order_energy_start = self.battery
            self._total_wait_time = 0.0
            self._total_move_time = 0.0
            self._total_distance = 0.0

            # Check battery constraint
            if self.battery < self.energy.BATTERY_CRITICAL:
                self._report_error(
                    "orderError", f"Battery critical: {self.battery:.1f}%"
                )
                self.driving = False
                self.op_state = self.STATE_ERROR
                return

            # Start processing first node
            self._advance_to_next_node()

    def _handle_instant_actions(self, message: dict):
        for action in message.get("instantActions", []):
            action_type = action.get("actionType", "")
            logger.info(f"[{self.serial_number}] InstantAction: {action_type}")

            with self._lock:
                if action_type == "startPause":
                    self.paused = True
                    self.driving = False
                    self.op_state = self.STATE_PAUSED
                elif action_type == "stopPause":
                    self.paused = False
                    if self.order_nodes and self.current_node_index < len(self.order_nodes):
                        self.driving = True
                        self.op_state = self.STATE_MOVING
                    else:
                        self.op_state = self.STATE_IDLE
                elif action_type == "cancelOrder":
                    self._cancel_current_order()

    def _cancel_current_order(self):
        self.order_id = ""
        self.order_nodes = []
        self.order_edges = []
        self.current_node_index = 0
        self.driving = False
        self.paused = False
        self.current_load = None
        self.op_state = self.STATE_IDLE
        self._is_interpolating = False
        logger.info(f"[{self.serial_number}] Order cancelled")

    # ==================== Movement Logic ====================

    def _advance_to_next_node(self):
        """Set up movement toward the next node in the order."""
        if self.current_node_index >= len(self.order_nodes):
            # Order complete
            self._complete_order()
            return

        target_node = self.order_nodes[self.current_node_index]
        node_id = target_node["nodeId"]
        released = target_node.get("released", True)

        if not released:
            # Horizon node - wait for update
            self.op_state = self.STATE_WAITING
            self.driving = False
            logger.info(f"[{self.serial_number}] Waiting for release: {node_id}")
            return

        # Get target position
        target_pos = target_node.get("nodePosition", {})
        tx = float(target_pos.get("x", self.x))
        ty = float(target_pos.get("y", self.y))

        # Compute distance to target
        dx = tx - self.x
        dy = ty - self.y
        distance = math.sqrt(dx * dx + dy * dy)

        if distance < 0.01:
            # Already at the node
            self._arrive_at_node(target_node)
            return

        # Compute required heading
        target_angle = math.degrees(math.atan2(dy, dx))

        # Start rotation if needed, then movement
        self._move_start_x = self.x
        self._move_start_y = self.y
        self._move_target_x = tx
        self._move_target_y = ty
        self._move_distance = distance
        self._move_progress = 0.0
        self._is_interpolating = True

        # Rotate first
        angle_diff = self._normalize_angle(target_angle - self.theta)
        if abs(angle_diff) > 1.0:
            t_rot, e_rot = self.energy.calculate_rotation_energy(angle_diff)
            self.op_state = self.STATE_ROTATING
            self.theta = target_angle
            self.battery -= e_rot
            self._total_move_time += t_rot

        self.op_state = self.STATE_MOVING
        self.driving = True

    def _tick_movement(self, dt: float):
        """Advance position by dt seconds of movement."""
        if not self._is_interpolating or self.paused:
            return

        if self._move_distance <= 0:
            self._is_interpolating = False
            return

        # Distance to travel this tick
        step = self.energy.VELOCITY * dt
        self._move_progress += step

        # Energy cost for this tick
        _, e_move = self.energy.calculate_move_energy(step)
        self.battery -= e_move
        self._total_move_time += dt
        self._total_distance += step

        # Check battery
        if self.battery <= 0:
            self.battery = 0
            self.driving = False
            self.op_state = self.STATE_ERROR
            self._is_interpolating = False
            self._report_error("batteryError", "Battery depleted during movement")
            return

        if self._move_progress >= self._move_distance:
            # Arrived at target
            self.x = self._move_target_x
            self.y = self._move_target_y
            self._is_interpolating = False

            target_node = self.order_nodes[self.current_node_index]
            self._arrive_at_node(target_node)
        else:
            # Interpolate position linearly from start to target
            ratio = self._move_progress / self._move_distance
            self.x = self._move_start_x + (self._move_target_x - self._move_start_x) * ratio
            self.y = self._move_start_y + (self._move_target_y - self._move_start_y) * ratio

    def _arrive_at_node(self, node: dict):
        """Handle arrival at a node."""
        node_id = node["nodeId"]
        seq_id = node.get("sequenceId", 0)

        self.last_node_id = node_id
        self.last_node_seq_id = seq_id

        # Update position to exact node position
        pos = node.get("nodePosition", {})
        if pos:
            self.x = float(pos.get("x", self.x))
            self.y = float(pos.get("y", self.y))

        logger.info(
            f"[{self.serial_number}] Arrived at {node_id} "
            f"({self.x}, {self.y}) battery={self.battery:.1f}%"
        )

        # Execute node actions
        self._execute_actions(node.get("actions", []))

        # Move to next node
        self.current_node_index += 1
        self._advance_to_next_node()

    def _execute_actions(self, actions: list):
        """Execute actions at a node (pick, drop, etc.)."""
        for action in actions:
            action_type = action.get("actionType", "")
            if action_type == "pick":
                self.current_load = {"type": "package", "weight": 50}
                logger.info(f"[{self.serial_number}] Picked up load")
            elif action_type == "drop":
                self.current_load = None
                logger.info(f"[{self.serial_number}] Dropped load")
            elif action_type == "startCharging":
                self.is_charging = True
                self.op_state = self.STATE_CHARGING
                self.driving = False
                logger.info(f"[{self.serial_number}] Started charging")

    def _complete_order(self):
        """Handle order completion."""
        order_id = self.order_id
        flow_time = time.time() - self._order_start_time
        energy_consumed = self._order_energy_start - self.battery

        logger.info(
            f"[{self.serial_number}] Order {order_id} COMPLETED | "
            f"Flow time: {flow_time:.1f}s | Energy: {energy_consumed:.2f}% | "
            f"Distance: {self._total_distance:.1f}m | Wait: {self._total_wait_time:.1f}s"
        )

        # Notify metrics collector via callback
        if self._on_order_complete:
            self._on_order_complete(
                {
                    "agv": self.serial_number,
                    "order_id": order_id,
                    "flow_time_s": round(flow_time, 2),
                    "energy_consumed_pct": round(energy_consumed, 3),
                    "distance_m": round(self._total_distance, 2),
                    "wait_time_s": round(self._total_wait_time, 2),
                    "move_time_s": round(self._total_move_time, 2),
                    "battery_remaining_pct": round(self.battery, 2),
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                }
            )

        # Mark as done but keep order_id so the server can detect completion
        # (server needs orderId + driving=False + lastNodeId == final node)
        self.driving = False
        self.op_state = self.STATE_CHARGING if self.is_charging else self.STATE_IDLE

        # Publish one final state WITH the order_id still set
        # so the server sees orderId + lastNodeId + driving=False → COMPLETED
        self._publish_state()

        # Now clear order state
        self.order_id = ""
        self.order_nodes = []
        self.order_edges = []
        self.current_node_index = 0
        self.current_load = None

    # ==================== Idle Energy ====================

    def _tick_idle(self, dt: float):
        """Apply idle energy drain when not moving."""
        if self.is_charging:
            self.battery = min(100.0, self.battery + self.charge_rate_pct_per_s * dt)
            if self.battery >= 99.9:
                self.is_charging = False
                if self.op_state == self.STATE_CHARGING:
                    self.op_state = self.STATE_IDLE
            return

        if self.op_state in (self.STATE_IDLE, self.STATE_WAITING, self.STATE_PAUSED):
            e_idle = self.energy.calculate_idle_energy(dt)
            self.battery -= e_idle
            if self.op_state == self.STATE_WAITING:
                self._total_wait_time += dt
            self.battery = max(0, self.battery)

    # ==================== State Publishing ====================

    def _build_state_message(self) -> dict:
        return {
            "headerId": self._header_counter,
            "timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%f"
            )[:-3]
            + "Z",
            "version": VDA_VERSION,
            "manufacturer": self.manufacturer,
            "serialNumber": self.serial_number,
            "orderId": self.order_id,
            "lastNodeId": self.last_node_id,
            "lastNodeSequenceId": self.last_node_seq_id,
            "driving": self.driving,
            "paused": self.paused,
            "operatingMode": "AUTOMATIC",
            "batteryState": {
                "batteryCharge": round(self.battery, 2),
                "batteryVoltage": 48.0,
                "charging": self.is_charging,
                "reach": max(0, int(self.battery / self.energy.POWER_MOVING)),
            },
            "agvPosition": {
                "x": round(self.x, 3),
                "y": round(self.y, 3),
                "theta": round(self.theta, 2),
                "mapId": MAP_ID,
                "positionInitialized": True,
            },
            "velocity": {
                "vx": round(self.energy.VELOCITY if self.driving else 0.0, 2),
                "vy": 0.0,
                "omega": 0.0,
            },
            "loads": [self.current_load] if self.current_load else [],
            "safetyState": {"eStop": "NONE", "fieldViolation": False},
            "errors": self.errors,
            "information": [],
        }

    def _publish_state(self):
        msg = self._build_state_message()
        self._client.publish(self._topic_state, json.dumps(msg), qos=0)
        self._header_counter += 1

        if self._on_state_change:
            self._on_state_change(self.serial_number, msg)

    def _publish_connection(self, status: str):
        payload = {
            "headerId": self._header_counter,
            "timestamp": datetime.now(timezone.utc).strftime(
                "%Y-%m-%dT%H:%M:%S.%f"
            )[:-3]
            + "Z",
            "version": VDA_VERSION,
            "manufacturer": self.manufacturer,
            "serialNumber": self.serial_number,
            "connectionState": status,
        }
        self._client.publish(self._topic_conn, json.dumps(payload), qos=1, retain=True)
        self._header_counter += 1

    # ==================== Error Handling ====================

    def _report_error(self, error_type: str, description: str):
        error = {
            "errorType": error_type,
            "errorDescription": description,
            "errorLevel": "FATAL" if "critical" in description.lower() else "WARNING",
        }
        self.errors.append(error)
        logger.error(f"[{self.serial_number}] ERROR: {error_type} - {description}")

    # ==================== Utility ====================

    @staticmethod
    def _normalize_angle(angle: float) -> float:
        """Normalize angle to [-180, 180] degrees."""
        while angle > 180:
            angle -= 360
        while angle < -180:
            angle += 360
        return angle

    # ==================== Main Loop ====================

    def start(self):
        """Connect to MQTT and start simulation loops."""
        self._running = True
        self._client.connect(MQTT_BROKER, MQTT_PORT, 60)
        self._client.loop_start()

        # Physics thread (fast tick)
        self._physics_thread = threading.Thread(
            target=self._physics_loop, daemon=True
        )
        self._physics_thread.start()

        # State publishing thread (1 Hz)
        self._state_thread = threading.Thread(
            target=self._state_publish_loop, daemon=True
        )
        self._state_thread.start()

    def _physics_loop(self):
        """Fast simulation loop for movement interpolation."""
        last_time = time.time()
        while self._running:
            now = time.time()
            dt = now - last_time
            last_time = now

            with self._lock:
                if self.driving and not self.paused:
                    self._tick_movement(dt)
                else:
                    self._tick_idle(dt)

            time.sleep(MOVEMENT_TICK_INTERVAL)

    def _state_publish_loop(self):
        """Publish VDA5050 state at configured frequency."""
        while self._running:
            with self._lock:
                self._publish_state()
            time.sleep(STATE_PUBLISH_INTERVAL)

    def stop(self):
        """Gracefully stop the AGV."""
        self._running = False
        try:
            self._publish_connection("OFFLINE")
            self._client.loop_stop()
            self._client.disconnect()
        except Exception:
            pass
        logger.info(f"[{self.serial_number}] Stopped")

    # ==================== Status Properties ====================

    @property
    def is_busy(self) -> bool:
        return self.driving or self.op_state not in (self.STATE_IDLE,)

    @property
    def status_summary(self) -> dict:
        return {
            "serial": self.serial_number,
            "state": self.op_state,
            "node": self.last_node_id,
            "battery": round(self.battery, 1),
            "order": self.order_id or "-",
            "load": "Yes" if self.current_load else "No",
            "pos": f"({self.x:.1f}, {self.y:.1f})",
        }
