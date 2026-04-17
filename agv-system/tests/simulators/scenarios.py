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


# ==================== Scenario 1: Continuous Shift (Endurance) ====================
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

# ==================== Scenario 2: Deadlock Contention ====================
SCENARIO_DEADLOCK = {
    "name": "deadlock_contention",
    "description": (
        "9 AGVs on the large factory map. Tasks are concentrated around the "
        "central corridor (Main_C / Aisle_C) and alternate in opposite directions "
        "to stress wait-cost, queueing, and any deadlock or stuck-node handling."
    ),
    "fleet": {
        "AGV_01": {"node": "Charge_01", "battery": 100.0},
        "AGV_02": {"node": "Charge_02", "battery": 100.0},
        "AGV_03": {"node": "Depot_Gate", "battery": 90.0},
        "AGV_04": {"node": "Main_S", "battery": 80.0},
        "AGV_05": {"node": "Main_N", "battery": 75.0},
        "AGV_06": {"node": "Main_C", "battery": 65.0},
        "AGV_07": {"node": "Aisle_C", "battery": 85.0},
        "AGV_08": {"node": "Aisle_S", "battery": 95.0},
        "AGV_09": {"node": "Aisle_N", "battery": 20.0},
    },
    "tasks": [
        _make_task("WH_Pick_2", "Assy_Drop_1", delay=0),
        _make_task("Assy_Drop_1", "WH_Pick_2", delay=0.5),
        _make_task("WH_Pick_2", "Assy_Drop_2", delay=1),
        _make_task("Assy_Drop_2", "WH_Pick_2", delay=1.5),
        _make_task("WH_Pick_3", "Assy_Drop_1", delay=20),
        _make_task("Assy_Drop_1", "WH_Pick_3", delay=20.5),
        _make_task("WH_Pick_3", "Assy_Drop_2", delay=21),
        _make_task("Assy_Drop_2", "WH_Pick_3", delay=21.5),
        _make_task("WH_Pick_2", "Assy_Drop_1", delay=45),
        _make_task("Assy_Drop_1", "WH_Pick_2", delay=45.5),
        _make_task("WH_Pick_2", "Assy_Drop_2", delay=46),
        _make_task("Assy_Drop_2", "WH_Pick_2", delay=46.5),
    ],
    "timeout_s": 900,
}

# ==================== Registry ====================
ALL_SCENARIOS = {
    "deadlock": SCENARIO_DEADLOCK,
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
