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
# Large factory layout: roughly 60m x 85m, with a long main corridor and
# dedicated charging, pickup, and delivery zones.
NODE_POSITIONS = {
    "Charge_01": {"x": 0, "y": 0},
    "Charge_02": {"x": 0, "y": 8},
    "Depot_Gate": {"x": 8, "y": 4},
    "Depot_Buffer": {"x": 16, "y": 10},
    "Main_S": {"x": 8, "y": 25},
    "Main_C": {"x": 8, "y": 55},
    "Main_N": {"x": 8, "y": 85},
    "West_S": {"x": -8, "y": 25},
    "West_C": {"x": -8, "y": 55},
    "West_N": {"x": -8, "y": 85},
    "Aisle_S": {"x": 28, "y": 25},
    "Aisle_C": {"x": 28, "y": 55},
    "Aisle_N": {"x": 28, "y": 85},
    "Aisle2_S": {"x": 36, "y": 25},
    "Aisle2_C": {"x": 36, "y": 55},
    "Aisle2_N": {"x": 36, "y": 85},
    "WH_Pick_1": {"x": 45, "y": 25},
    "WH_Pick_2": {"x": 45, "y": 55},
    "WH_Pick_3": {"x": 45, "y": 85},
    "Assy_Drop_1": {"x": -15, "y": 55},
    "Assy_Drop_2": {"x": -15, "y": 85},
}

# ==================== Default AGV Fleet ====================
# Format: serial_number -> {node, battery}
# Easy to change fleet size by editing this dict
DEFAULT_AGV_FLEET = {
    "AGV_01": {"node": "Charge_01", "battery": 95.0},
    "AGV_02": {"node": "Depot_Gate", "battery": 90.0},
    "AGV_03": {"node": "Main_S", "battery": 85.0},
}

# Larger fleet for stress testing
LARGE_AGV_FLEET = {
    "AGV_01": {"node": "Charge_01", "battery": 95.0},
    "AGV_02": {"node": "Charge_02", "battery": 90.0},
    "AGV_03": {"node": "Depot_Gate", "battery": 85.0},
    "AGV_04": {"node": "Main_S", "battery": 80.0},
    "AGV_05": {"node": "Main_C", "battery": 75.0},
    "AGV_06": {"node": "Aisle_S", "battery": 70.0},
    "AGV_07": {"node": "Aisle_C", "battery": 65.0},
}

# Fleet with mixed battery levels for battery constraint testing
MIXED_BATTERY_FLEET = {
    "AGV_01": {"node": "Charge_01", "battery": 95.0},
    "AGV_02": {"node": "Depot_Gate", "battery": 50.0},
    "AGV_03": {"node": "Main_C", "battery": 25.0},  # Low battery - penalty
    "AGV_04": {"node": "Aisle_C", "battery": 8.0},  # Critical - rejected
    "AGV_05": {"node": "West_C", "battery": 15.0},  # Low battery - penalty
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
    start_nodes = [
        "Charge_01",
        "Charge_02",
        "Depot_Gate",
        "Depot_Buffer",
        "Main_S",
        "Main_C",
        "Main_N",
        "West_S",
        "West_C",
        "West_N",
        "Aisle_S",
        "Aisle_C",
        "Aisle_N",
    ]
    fleet = {}
    for i in range(1, min(count + 1, 21)):
        serial = f"AGV_{i:02d}"
        node = start_nodes[(i - 1) % len(start_nodes)]
        battery = max(20.0, start_battery - (i - 1) * battery_step)
        fleet[serial] = {"node": node, "battery": battery}
    return fleet
