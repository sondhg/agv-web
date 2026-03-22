"""
Simulation Configuration for AGV System.
Central config for MQTT, physical parameters, and AGV fleet setup.
"""

import os

# ==================== MQTT Configuration ====================
MQTT_BROKER = os.environ.get("MQTT_BROKER", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1884"))

# ==================== VDA5050 Protocol ====================
VDA_VERSION = "2.1.0"
MANUFACTURER = "TestManufacturer"
MAP_ID = "map_1"

# ==================== Server API ====================
API_BASE_URL = os.environ.get("API_BASE_URL", "http://127.0.0.1:8000/api")

# ==================== Timing ====================
STATE_PUBLISH_INTERVAL = 1.0    # seconds - VDA5050 recommends 1 Hz
MOVEMENT_TICK_INTERVAL = 0.1    # seconds - physics simulation step
STATUS_PRINT_INTERVAL = 10.0    # seconds - fleet status display

# ==================== Graph Node Positions ====================
# Must match backend/vda5050/management/commands/setup_test_graph.py
NODE_POSITIONS = {
    "Node_A": {"x": 0,  "y": 0},
    "Node_B": {"x": 10, "y": 0},
    "Node_C": {"x": 20, "y": 0},
    "Node_D": {"x": 30, "y": 0},
    "Node_E": {"x": 0,  "y": 10},
    "Node_F": {"x": 10, "y": 10},
    "Node_G": {"x": 20, "y": 10},
    "Node_H": {"x": 30, "y": 10},
}

# ==================== Default AGV Fleet ====================
# Format: serial_number -> {node, battery}
# Easy to change fleet size by editing this dict
DEFAULT_AGV_FLEET = {
    "AGV_01": {"node": "Node_B", "battery": 95.0},
    "AGV_02": {"node": "Node_C", "battery": 90.0},
    "AGV_03": {"node": "Node_D", "battery": 85.0},
}

# Larger fleet for stress testing
LARGE_AGV_FLEET = {
    "AGV_01": {"node": "Node_A", "battery": 95.0},
    "AGV_02": {"node": "Node_B", "battery": 90.0},
    "AGV_03": {"node": "Node_C", "battery": 85.0},
    "AGV_04": {"node": "Node_D", "battery": 80.0},
    "AGV_05": {"node": "Node_E", "battery": 75.0},
    "AGV_06": {"node": "Node_F", "battery": 70.0},
    "AGV_07": {"node": "Node_G", "battery": 65.0},
}

# Fleet with mixed battery levels for battery constraint testing
MIXED_BATTERY_FLEET = {
    "AGV_01": {"node": "Node_A", "battery": 95.0},
    "AGV_02": {"node": "Node_B", "battery": 50.0},
    "AGV_03": {"node": "Node_C", "battery": 25.0},  # Low battery - penalty
    "AGV_04": {"node": "Node_D", "battery": 8.0},   # Critical - rejected
    "AGV_05": {"node": "Node_E", "battery": 15.0},   # Low battery - penalty
}


def generate_fleet(count: int, start_battery: float = 95.0, battery_step: float = 5.0) -> dict:
    """
    Generate a fleet configuration with the specified number of AGVs.

    Args:
        count: Number of AGVs to create (1-20)
        start_battery: Starting battery for AGV_01
        battery_step: Battery decrease per subsequent AGV

    Returns:
        dict of serial_number -> config
    """
    nodes = list(NODE_POSITIONS.keys())
    fleet = {}
    for i in range(1, min(count + 1, 21)):
        serial = f"AGV_{i:02d}"
        node = nodes[(i - 1) % len(nodes)]
        battery = max(20.0, start_battery - (i - 1) * battery_step)
        fleet[serial] = {"node": node, "battery": battery}
    return fleet
