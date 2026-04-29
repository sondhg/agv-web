"""
Scenario Definitions for AGV Simulation.

Each scenario defines:
- Fleet configuration (number of AGVs, positions, battery levels)
- Task list (pickup/delivery pairs with timing)
- Description for documentation
"""

import os
import random


def _make_task(pickup: str, delivery: str, delay: float = 0.0) -> dict:
    return {"pickup_node_id": pickup, "delivery_node_id": delivery, "delay_s": delay}


# ==================== Scenario 1: Continuous Shift (Endurance) ====================
def generate_continuous_shift_scenario(
    duration_hours=0.5,
    min_task_interval_s=3,
    max_task_interval_s=6,
    seed=None,
):
    """
    Sinh continuous shift theo kiểu bursty để tạo queueing, contention,
    và áp lực pin đủ lớn cho SSI_MARGINAL thể hiện ưu thế.
    """
    total_seconds = int(duration_hours * 3600)
    rng = random.Random(seed) if seed is not None else random

    # Task templates focus on the central corridor and reverse directions often.
    burst_templates = [
        [
            ("WH_Pick_2", "Assy_Drop_1"),
            ("Assy_Drop_1", "WH_Pick_2"),
            ("WH_Pick_3", "Assy_Drop_2"),
            ("Assy_Drop_2", "WH_Pick_3"),
        ],
        [
            ("WH_Pick_2", "Assy_Drop_2"),
            ("Assy_Drop_2", "WH_Pick_2"),
            ("WH_Pick_1", "Assy_Drop_1"),
            ("Assy_Drop_1", "WH_Pick_1"),
        ],
        [
            ("WH_Pick_3", "Assy_Drop_1"),
            ("Assy_Drop_1", "WH_Pick_3"),
            ("WH_Pick_2", "Assy_Drop_2"),
            ("Assy_Drop_2", "WH_Pick_2"),
        ],
    ]

    # Fleet deliberately mixes healthy and weak batteries to make the battery
    # penalty / rejection logic matter in SSI more than in Greedy ETA.
    fleet = {
        "AGV_01": {"node": "Charge_01", "battery": 100.0},
        "AGV_02": {"node": "Charge_02", "battery": 100.0},
        "AGV_03": {"node": "Depot_Gate", "battery": 85.0},
        "AGV_04": {"node": "Main_S", "battery": 62.0},
        "AGV_05": {"node": "Main_N", "battery": 48.0},
        "AGV_06": {"node": "Main_C", "battery": 38.0},
        "AGV_07": {"node": "Aisle_C", "battery": 58.0},
        "AGV_08": {"node": "Aisle_S", "battery": 72.0},
        "AGV_09": {"node": "Aisle_N", "battery": 22.0},
    }
    
    tasks = []
    current_delay = 0.0
    burst_index = 0
    
    # Generate bursty arrivals with short gaps between tasks and moderate gaps
    # between bursts to create repeated queue buildup.
    while current_delay < total_seconds:
        burst_pattern = burst_templates[burst_index % len(burst_templates)]
        burst_index += 1

        for pickup, delivery in burst_pattern:
            if current_delay >= total_seconds:
                break

            tasks.append(_make_task(pickup, delivery, delay=current_delay))
            current_delay += rng.randint(min_task_interval_s, max_task_interval_s)

        # A short pause between bursts keeps the workload intense but not flat.
        current_delay += rng.randint(10, 18)
        
    return {
        "name": "continuous_shift",
        "description": (
            f"Endurance + congestion test: {duration_hours} hours continuous operation. "
            f"Generates ~{len(tasks)} bursty tasks with central-corridor contention. "
            f"Seed={seed if seed is not None else 'runtime-random'}. "
            f"Tests queueing, fairness, battery cycling, and system stability."
        ),
        "fleet": fleet,
        "tasks": tasks,
        "timeout_s": total_seconds + 300,
    }

# Gọi hàm để sinh ra dictionary scenario (ở đây set mặc định là 2 tiếng)
CONTINUOUS_SHIFT_SEED = int(os.getenv("SIM_SCENARIO_SEED", "42"))
SCENARIO_CONTINUOUS_SHIFT = generate_continuous_shift_scenario(
    duration_hours=0.5,
    seed=CONTINUOUS_SHIFT_SEED,
)


# ==================== Scenario 1b: Continuous Shift Stress (30m) ====================
def generate_continuous_shift_stress_scenario(
    duration_minutes=30,
    burst_size=4,
    burst_interval_s=30,
    intra_burst_min_s=2,
    intra_burst_max_s=4,
    time_scale=1.0,
    seed=None,
):
    """
    Tao mot kịch bản 30 phut co do tranh chap cao:
    - Task den theo tung burst ngan, tao queue va tranh chap ngan han.
    - Task tap trung vao hanh lang trung tam va hai chieu nguoc nhau.
    - Fleet co pin khac nhau de lam ro thanh phan penalty/fairness cua SSI.

    Scenario nay phu hop de stress-test SSI_MARGINAL so voi GREEDY_ETA.
    """
    total_seconds = int(duration_minutes * 60 * time_scale)
    rng = random.Random(seed) if seed is not None else random

    # Task templates co xu huong cat qua hanh lang trung tam va dao chieu lien tuc.
    burst_templates = [
        [
            ("WH_Pick_2", "Assy_Drop_1"),
            ("Assy_Drop_1", "WH_Pick_2"),
            ("WH_Pick_3", "Assy_Drop_2"),
            ("Assy_Drop_2", "WH_Pick_3"),
        ],
        [
            ("WH_Pick_2", "Assy_Drop_2"),
            ("Assy_Drop_2", "WH_Pick_2"),
            ("WH_Pick_1", "Assy_Drop_1"),
            ("Assy_Drop_1", "WH_Pick_1"),
        ],
    ]

    # Fleet co nhieu AGV o muc pin trung binh/thap de lam ro tac dong pin penalty.
    fleet = {
        "AGV_01": {"node": "Charge_01", "battery": 95.0},
        "AGV_02": {"node": "Charge_02", "battery": 90.0},
        "AGV_03": {"node": "Depot_Gate", "battery": 80.0},
        "AGV_04": {"node": "Main_S", "battery": 55.0},
        "AGV_05": {"node": "Main_C", "battery": 35.0},
        "AGV_06": {"node": "Main_N", "battery": 30.0},
        "AGV_07": {"node": "Aisle_S", "battery": 70.0},
        "AGV_08": {"node": "Aisle_C", "battery": 45.0},
        "AGV_09": {"node": "Aisle_N", "battery": 25.0},
    }

    tasks = []
    current_delay = 0.0
    burst_index = 0

    while current_delay < total_seconds:
        burst_pattern = burst_templates[burst_index % len(burst_templates)]
        burst_index += 1

        for pickup, delivery in burst_pattern[:burst_size]:
            if current_delay >= total_seconds:
                break
            tasks.append(_make_task(pickup, delivery, delay=current_delay))
            current_delay += rng.randint(intra_burst_min_s, intra_burst_max_s) * time_scale

        # Khoang cach giua cac burst de tao nhung dot tranh chap ro rang.
        current_delay += rng.randint(max(1, burst_interval_s - 5), burst_interval_s + 5) * time_scale

    return {
        "name": "continuous_shift_stress_30m",
        "description": (
            f"30-minute congestion stress test with bursty task arrivals. "
            f"Tasks alternate across the central corridors to create queueing, "
            f"route contention, and battery-pressure effects. Seed={seed if seed is not None else 'runtime-random'}. "
            f"TimeScale={time_scale}. "
            f"Designed to reveal SSI fairness and congestion awareness versus Greedy ETA."
        ),
        "fleet": fleet,
        "tasks": tasks,
        "timeout_s": total_seconds + int(600 * time_scale),
    }


CONTINUOUS_SHIFT_STRESS_SEED = int(os.getenv("SIM_SCENARIO_SEED", "42"))
CONTINUOUS_SHIFT_STRESS_TIME_SCALE = float(os.getenv("SIM_TIME_SCALE", "1.0"))
SCENARIO_CONTINUOUS_SHIFT_STRESS_30M = generate_continuous_shift_stress_scenario(
    duration_minutes=30,
    time_scale=CONTINUOUS_SHIFT_STRESS_TIME_SCALE,
    seed=CONTINUOUS_SHIFT_STRESS_SEED,
)

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
    "continuous_shift_stress_30m": SCENARIO_CONTINUOUS_SHIFT_STRESS_30M,
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
