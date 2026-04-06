"""
Scenario Definitions for AGV Simulation.

Each scenario defines:
- Fleet configuration (number of AGVs, positions, battery levels)
- Task list (pickup/delivery pairs with timing)
- Description for documentation
"""

from config_sim import NODE_POSITIONS
import random


# Available nodes for task generation
ALL_NODES = list(NODE_POSITIONS.keys())
# Separate rows for structured task generation
ROW_1 = ["Node_A", "Node_B", "Node_C", "Node_D"]
ROW_2 = ["Node_E", "Node_F", "Node_G", "Node_H"]


def _make_task(pickup: str, delivery: str, delay: float = 0.0) -> dict:
    return {"pickup_node_id": pickup, "delivery_node_id": delivery, "delay_s": delay}


# ==================== Scenario 1: Basic Load Balancing ====================
SCENARIO_BASIC = {
    "name": "basic_load_balance",
    "description": (
        "3 AGVs, 6 tasks distributed evenly. Tests basic auction and "
        "load balancing with uniform battery and symmetric positions."
    ),
    "fleet": {
        "AGV_01": {"node": "Node_A", "battery": 95.0},
        "AGV_02": {"node": "Node_C", "battery": 95.0},
        "AGV_03": {"node": "Node_E", "battery": 95.0},
    },
    "tasks": [
        _make_task("Node_B", "Node_D", delay=0),
        _make_task("Node_F", "Node_H", delay=3),
        _make_task("Node_A", "Node_G", delay=6),
        _make_task("Node_D", "Node_E", delay=9),
        _make_task("Node_C", "Node_F", delay=12),
        _make_task("Node_H", "Node_B", delay=15),
    ],
    "timeout_s": 180,
}

# ==================== Scenario 2: Burst Tasks ====================
SCENARIO_BURST = {
    "name": "burst_tasks",
    "description": (
        "3 AGVs, 9 tasks sent in rapid bursts. Tests order chaining "
        "and auction under contention."
    ),
    "fleet": {
        "AGV_01": {"node": "Node_B", "battery": 90.0},
        "AGV_02": {"node": "Node_D", "battery": 90.0},
        "AGV_03": {"node": "Node_F", "battery": 90.0},
    },
    "tasks": [
        # Burst 1 - 3 tasks at once
        _make_task("Node_A", "Node_D", delay=0),
        _make_task("Node_E", "Node_H", delay=0.5),
        _make_task("Node_C", "Node_F", delay=1.0),
        # Burst 2 - 3 more after 10s
        _make_task("Node_B", "Node_G", delay=10),
        _make_task("Node_H", "Node_A", delay=10.5),
        _make_task("Node_D", "Node_E", delay=11),
        # Burst 3 - 3 more after 20s
        _make_task("Node_F", "Node_C", delay=20),
        _make_task("Node_G", "Node_B", delay=20.5),
        _make_task("Node_A", "Node_H", delay=21),
    ],
    "timeout_s": 240,
}

# ==================== Scenario 3: Battery Constraints ====================
SCENARIO_BATTERY = {
    "name": "battery_constraints",
    "description": (
        "5 AGVs with varying battery levels including critical (<10%) and "
        "low (<30%). Tests battery penalty and rejection in bidding."
    ),
    "fleet": {
        "AGV_01": {"node": "Node_A", "battery": 95.0},
        "AGV_02": {"node": "Node_B", "battery": 50.0},
        "AGV_03": {"node": "Node_C", "battery": 25.0},  # Low - penalty
        "AGV_04": {"node": "Node_D", "battery": 8.0},   # Critical - rejected
        "AGV_05": {"node": "Node_E", "battery": 15.0},  # Low - penalty
    },
    "tasks": [
        _make_task("Node_F", "Node_D", delay=0),
        _make_task("Node_G", "Node_A", delay=5),
        _make_task("Node_H", "Node_B", delay=10),
        _make_task("Node_C", "Node_E", delay=15),
        _make_task("Node_B", "Node_H", delay=20),
        _make_task("Node_A", "Node_G", delay=25),
    ],
    "timeout_s": 240,
}

# ==================== Scenario 4: Sequential Single-AGV ====================
SCENARIO_SEQUENTIAL = {
    "name": "sequential_tasks",
    "description": (
        "2 AGVs, 6 tasks sent one-by-one with large delay. "
        "Tests basic point-to-point assignment without contention."
    ),
    "fleet": {
        "AGV_01": {"node": "Node_A", "battery": 95.0},
        "AGV_02": {"node": "Node_H", "battery": 95.0},
    },
    "tasks": [
        _make_task("Node_B", "Node_D", delay=0),
        _make_task("Node_E", "Node_G", delay=30),
        _make_task("Node_C", "Node_F", delay=60),
        _make_task("Node_H", "Node_A", delay=90),
        _make_task("Node_D", "Node_E", delay=120),
        _make_task("Node_F", "Node_B", delay=150),
    ],
    "timeout_s": 360,
}

# ==================== Scenario 5: Stress Test (Large Fleet) ====================
SCENARIO_STRESS = {
    "name": "stress_test",
    "description": (
        "7 AGVs, 21 tasks in rapid succession. "
        "Tests scalability, order chaining, and load balance under heavy load."
    ),
    "fleet": {
        "AGV_01": {"node": "Node_A", "battery": 95.0},
        "AGV_02": {"node": "Node_B", "battery": 90.0},
        "AGV_03": {"node": "Node_C", "battery": 85.0},
        "AGV_04": {"node": "Node_D", "battery": 80.0},
        "AGV_05": {"node": "Node_E", "battery": 75.0},
        "AGV_06": {"node": "Node_F", "battery": 70.0},
        "AGV_07": {"node": "Node_G", "battery": 65.0},
    },
    "tasks": [
        _make_task("Node_A", "Node_H", delay=0),
        _make_task("Node_B", "Node_G", delay=1),
        _make_task("Node_C", "Node_F", delay=2),
        _make_task("Node_D", "Node_E", delay=3),
        _make_task("Node_E", "Node_D", delay=4),
        _make_task("Node_F", "Node_C", delay=5),
        _make_task("Node_G", "Node_B", delay=6),
        _make_task("Node_H", "Node_A", delay=10),
        _make_task("Node_A", "Node_D", delay=11),
        _make_task("Node_B", "Node_E", delay=12),
        _make_task("Node_C", "Node_H", delay=13),
        _make_task("Node_D", "Node_F", delay=14),
        _make_task("Node_E", "Node_G", delay=15),
        _make_task("Node_F", "Node_A", delay=20),
        _make_task("Node_G", "Node_D", delay=21),
        _make_task("Node_H", "Node_B", delay=22),
        _make_task("Node_A", "Node_F", delay=23),
        _make_task("Node_B", "Node_H", delay=24),
        _make_task("Node_C", "Node_E", delay=30),
        _make_task("Node_D", "Node_G", delay=31),
        _make_task("Node_E", "Node_A", delay=32),
    ],
    "timeout_s": 360,
}

# ==================== Scenario 6: Cross-Grid Traffic ====================
SCENARIO_CROSS_GRID = {
    "name": "cross_grid_traffic",
    "description": (
        "4 AGVs with tasks that cross grid paths. "
        "Tests how the bidding system handles competing routes."
    ),
    "fleet": {
        "AGV_01": {"node": "Node_A", "battery": 90.0},
        "AGV_02": {"node": "Node_D", "battery": 90.0},
        "AGV_03": {"node": "Node_E", "battery": 90.0},
        "AGV_04": {"node": "Node_H", "battery": 90.0},
    },
    "tasks": [
        # Cross-diagonal tasks
        _make_task("Node_A", "Node_H", delay=0),
        _make_task("Node_D", "Node_E", delay=0.5),
        _make_task("Node_E", "Node_D", delay=1),
        _make_task("Node_H", "Node_A", delay=1.5),
        # Second wave
        _make_task("Node_B", "Node_G", delay=15),
        _make_task("Node_G", "Node_B", delay=15.5),
        _make_task("Node_C", "Node_F", delay=16),
        _make_task("Node_F", "Node_C", delay=16.5),
    ],
    "timeout_s": 240,
}

# ==================== Scenario 7: Continuous Shift (Endurance) ====================
def generate_continuous_shift_scenario(duration_hours=2):
    """
    Sinh tự động hàng trăm tasks rải đều trong khoảng thời gian duration_hours.
    Phù hợp với bản đồ large_factory_1 để test Battery Cycling và Endurance.
    """
    total_seconds = int(duration_hours * 3600)
    
    # 1. Định nghĩa các điểm bốc/dỡ hàng theo đúng Large Factory Map
    pickup_nodes = ["WH_Pick_1", "WH_Pick_2", "WH_Pick_3"]
    delivery_nodes = ["Assy_Drop_1", "Assy_Drop_2"]
    
    # 2. Bố trí đội xe (9 xe) xuất phát từ các điểm khác nhau với 100% pin
    fleet = {
        "AGV_01": {"node": "Charge_01", "battery": 100.0},
        "AGV_02": {"node": "Charge_02", "battery": 100.0},
        "AGV_03": {"node": "Depot_Gate", "battery": 90.0},
        "AGV_04": {"node": "Main_S", "battery": 80.0},
        "AGV_05": {"node": "Main_N", "battery": 75.0},
        "AGV_06": {"node": "Main_C", "battery": 65.0},
        "AGV_07": {"node": "Aisle_C", "battery": 85.0},
        "AGV_08": {"node": "Aisle_S", "battery": 95.0},
        "AGV_09": {"node": "Aisle_N", "battery": 20.0},
    }
    
    tasks = []
    current_delay = 0.0
    
    # 3. Vòng lặp sinh Task liên tục cho đến khi hết ca làm việc
    while current_delay < total_seconds:
        pickup = random.choice(pickup_nodes)
        delivery = random.choice(delivery_nodes)
        
        # Thêm task vào danh sách với thời gian trễ tương ứng
        tasks.append(_make_task(pickup, delivery, delay=current_delay))
        
        # Thời gian giữa các order mới (Random từ 15 giây đến 45 giây có 1 order)
        # Bạn có thể giảm con số này xuống nếu muốn test nhà máy công suất cao (vd: 10, 20)
        current_delay += random.randint(15, 45)
        
    return {
        "name": "continuous_shift",
        "description": (
            f"Endurance test: {duration_hours} hours continuous operation. "
            f"Generates ~{len(tasks)} random tasks. Tests battery cycling, "
            f"auto-charging capability, and system stability."
        ),
        "fleet": fleet,
        "tasks": tasks,
        "timeout_s": total_seconds + 300, # Cộng dư 5 phút để hoàn thành các task cuối cùng
    }

# Gọi hàm để sinh ra dictionary scenario (ở đây set mặc định là 2 tiếng)
SCENARIO_CONTINUOUS_SHIFT = generate_continuous_shift_scenario(duration_hours=2)

# ==================== Registry ====================
ALL_SCENARIOS = {
    "basic": SCENARIO_BASIC,
    "burst": SCENARIO_BURST,
    "battery": SCENARIO_BATTERY,
    "sequential": SCENARIO_SEQUENTIAL,
    "stress": SCENARIO_STRESS,
    "cross_grid": SCENARIO_CROSS_GRID,
    "continuous_shift": SCENARIO_CONTINUOUS_SHIFT,
}


def get_scenario(name: str) -> dict:
    """Get scenario by name. Raises KeyError if not found."""
    if name not in ALL_SCENARIOS:
        available = ", ".join(ALL_SCENARIOS.keys())
        raise KeyError(f"Unknown scenario '{name}'. Available: {available}")
    return ALL_SCENARIOS[name]


def list_scenarios() -> list[str]:
    """Return list of available scenario names."""
    return list(ALL_SCENARIOS.keys())
