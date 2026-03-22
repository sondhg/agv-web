# AGV Simulation System - Documentation

## 1. Overview

The simulation system provides a complete testing framework for the VDA5050-compliant AGV Management Server. It simulates multiple independent AGVs with realistic kinematic movement, energy consumption, and battery management, then collects scientific metrics for analysis.

### Architecture

```
tests/simulators/
├── config_energy.py         # Energy model constants (velocity, power consumption)
├── config_sim.py            # Simulation config (MQTT, fleet, API settings)
├── advanced_mock_agv.py     # AGV simulator with kinematics & battery
├── scenarios.py             # Pre-defined test scenarios
├── metrics_collector.py     # Metrics collection & CSV export
├── multi_agent_runner.py    # Main orchestrator (entry point)
├── run_simulation.bat       # Windows launcher script
└── results/                 # Output directory (created automatically)
    ├── *_orders.csv
    ├── *_agv_summary.csv
    ├── *_load_balance.csv
    ├── *_assignments.csv
    └── *_fleet_summary.csv
```

### Simulation Flow

```
┌─────────────────────┐     MQTT (orders)      ┌──────────────┐
│  multi_agent_runner  │ ──────────────────────► │  AGV Server  │
│  (orchestrator)      │                         │  (Django)    │
│                      │     HTTP POST /tasks/   │              │
│  - Start AGV fleet   │ ──────────────────────► │  - Bidding   │
│  - Dispatch tasks    │                         │  - Scheduler │
│  - Wait completion   │ ◄────────── MQTT ────── │  - MQTT pub  │
└─────────────────────┘                          └──────────────┘
         │                                              │
         ▼                                              │
┌─────────────────────┐     MQTT (state 1Hz)           │
│  advanced_mock_agv   │ ──────────────────────────────►│
│  (per AGV instance)  │                                │
│                      │ ◄──── MQTT (order/action) ─────┘
│  - Kinematic model   │
│  - Energy model      │
│  - VDA5050 states    │
└─────────────────────┘
         │
         ▼  (callbacks)
┌─────────────────────┐
│  metrics_collector   │
│                      │
│  - Per-order metrics │
│  - Load balance      │
│  - CSV export        │
└─────────────────────┘
```

---

## 2. Prerequisites

Before running the simulation, ensure:

1. **Server is running** (Docker):
   ```bash
   cd agv-system
   docker-compose up -d
   ```

2. **Test graph is loaded:**
   ```bash
   docker exec -it agv-system-web-1 python manage.py setup_test_graph
   ```

3. **Test AGVs are registered** (matching the scenario fleet):
   ```bash
   docker exec -it agv-system-web-1 python manage.py setup_test_agvs --count 7
   ```

4. **MQTT Listener is running** (typically started automatically by `mqtt_worker` container).

5. **Python dependencies** on the host:
   ```bash
   pip install paho-mqtt requests
   ```

---

## 3. Quick Start

### Run a single scenario

```bash
cd tests/simulators

# Using Python directly
python multi_agent_runner.py --scenario basic

# Using batch script (Windows)
run_simulation.bat basic
```

### List available scenarios

```bash
python multi_agent_runner.py --list
```

### Run all scenarios

```bash
python multi_agent_runner.py --scenario all
```

### Custom fleet size

```bash
python multi_agent_runner.py --scenario basic --agvs 5
```

### Custom API endpoint

```bash
python multi_agent_runner.py --scenario basic --api http://localhost:8000/api
```

---

## 4. Scenarios

### 4.1 `basic` - Basic Load Balancing

| Property | Value |
|----------|-------|
| AGVs | 3 |
| Tasks | 6 |
| Delay | 3s between tasks |
| Purpose | Test basic auction and even task distribution |

AGVs start at symmetric positions (Node_A, Node_C, Node_E) with equal battery (95%). Tasks are spaced evenly to allow the auction system to distribute work.

### 4.2 `burst` - Burst Task Injection

| Property | Value |
|----------|-------|
| AGVs | 3 |
| Tasks | 9 (3 bursts × 3) |
| Delay | Bursts at 0s, 10s, 20s |
| Purpose | Test order chaining and auction under contention |

Three tasks arrive nearly simultaneously in each burst. Tests how the bidding system handles multiple concurrent requests and order chaining.

### 4.3 `battery` - Battery Constraints

| Property | Value |
|----------|-------|
| AGVs | 5 (varied battery) |
| Tasks | 6 |
| Purpose | Test battery penalty and rejection |

Fleet includes:
- AGV_01: 95% (normal)
- AGV_02: 50% (normal)
- AGV_03: 25% (low → penalty ×1.5)
- AGV_04: 8% (critical → rejected from auction)
- AGV_05: 15% (low → penalty ×1.5)

Verifies that AGV_04 never receives tasks and low-battery AGVs receive fewer tasks due to bid penalties.

### 4.4 `sequential` - Sequential Tasks

| Property | Value |
|----------|-------|
| AGVs | 2 |
| Tasks | 6 |
| Delay | 30s between tasks |
| Purpose | Test basic point-to-point without contention |

Large delay between tasks ensures each task is assigned to a free AGV. Used as a baseline for comparison.

### 4.5 `stress` - Stress Test

| Property | Value |
|----------|-------|
| AGVs | 7 |
| Tasks | 21 |
| Delay | 1-2s between tasks |
| Purpose | Test scalability and load balance under heavy load |

Maximum fleet with rapid task injection. Tests order chaining depth, system throughput, and load distribution across all AGVs.

### 4.6 `cross_grid` - Cross-Grid Traffic

| Property | Value |
|----------|-------|
| AGVs | 4 |
| Tasks | 8 |
| Purpose | Test bidding with competing routes |

Tasks form crossing paths (A→H vs D→E, B→G vs G→B). Tests how the bidding system resolves route conflicts.

---

## 5. Energy Model

> Defined in `config_energy.py`

### Constants

| Parameter | Value | Unit | Purpose |
|-----------|-------|------|---------|
| `VELOCITY` | 1.0 | m/s | AGV translational speed |
| `ROTATION_SPEED` | 30.0 | deg/s | AGV rotation speed |
| `POWER_MOVING` | 0.05 | %/s | Battery drain while moving |
| `POWER_ROTATION` | 0.03 | %/s | Battery drain while rotating |
| `POWER_IDLE` | 0.005 | %/s | Battery drain while idle/waiting |

### Formulas

$$E_{total} = E_{moving} + E_{rotation} + E_{idle}$$

Where:
- $E_{moving} = (D / V) \times P_{moving}$
- $E_{rotation} = (|\theta| / \omega) \times P_{rotation}$
- $E_{idle} = T_{wait} \times P_{idle}$

### Battery Constraints

| Level | Threshold | Bidding Behavior |
|-------|-----------|-----------------|
| Normal | ≥ 30% | Full participation, no penalty |
| Low | 10% - 30% | Participates with ×1.5 penalty on marginal cost |
| Critical | < 10% | Rejected from all auctions, error reported |

---

## 6. AGV Simulator Details

> Implemented in `advanced_mock_agv.py`

### Operating States

```
IDLE ──► MOVING ──► ROTATING ──► MOVING ──► ... ──► IDLE
  │                                                    ▲
  ├── WAITING_FOR_PERMISSION (unreleased nodes)        │
  ├── EXECUTING_ACTION (pick/drop)                     │
  ├── PAUSED (instant action) ─────────────────────────┘
  └── ERROR (battery depleted / order error)
```

### VDA5050 Compliance

- **State messages** published at 1 Hz with full VDA5050 format
- **Connection messages** with retain flag on connect/disconnect
- **Order handling**: processes nodes sequentially, respects `released` flag
- **Instant actions**: supports `startPause`, `stopPause`, `cancelOrder`
- **batteryState** includes `batteryCharge`, `batteryVoltage`, `charging`, `reach`

### Threading Model

Each AGV runs two daemon threads:
1. **Physics loop** (10 Hz): position interpolation, energy consumption
2. **State publisher** (1 Hz): MQTT state message broadcast

---

## 7. Metrics Output

The simulation captures **4 groups of metrics** designed for research paper evaluation:

### Group 1: Time & Efficiency

| Metric | CSV Column | File | Description |
|--------|-----------|------|-------------|
| Makespan | `makespan_s` | fleet_summary | Wall-clock time from first task dispatch to last order completion |
| Total Flow Time | `total_flow_time_s` | fleet_summary | Sum of all individual order flow times (MiniSum objective) |
| Avg Flow Time/Task | `avg_flow_time_s` | fleet_summary | Mean flow time across all completed tasks |
| Total Wait Time | `total_wait_time_s` | fleet_summary | Total time AGVs spent idle/waiting |
| Throughput | `throughput_tasks_per_min` | fleet_summary | Tasks completed per minute |
| Per-Order Flow Time | `flow_time_s` | orders | Individual order flow time |
| Per-Order Wait Time | `wait_time_s` | orders | Individual order wait time |

### Group 2: Energy

| Metric | CSV Column | File | Description |
|--------|-----------|------|-------------|
| Total Energy | `total_energy_consumed_pct` | fleet_summary | Fleet-wide battery consumption |
| Energy per Task | `energy_per_task_pct` | fleet_summary | Average battery cost per completed task |
| Per-Order Energy | `energy_consumed_pct` | orders | Battery consumed for a single order |
| Battery Remaining | `battery_remaining_pct` | orders | AGV battery after completing each order |
| Per-AGV Total Energy | `total_energy_pct` | agv_summary | Aggregate energy per AGV |

### Group 3: Load Balance & Robustness

| Metric | CSV Column | File | Description |
|--------|-----------|------|-------------|
| CV (Tasks) | `cv_tasks` | load_balance | Coefficient of variation of task counts across AGVs |
| CV (Distance) | `cv_distance` | load_balance | Coefficient of variation of distances traveled |
| Deadlock Count | `deadlock_count` | load_balance, fleet_summary | Number of detected deadlock events (AGV stuck >60s) |
| Per-AGV Tasks | `{agv}_tasks` | load_balance | Task count per individual AGV |
| Per-AGV Distance | `{agv}_distance` | load_balance | Distance traveled per individual AGV |

### Group 4: Algorithm Overhead

| Metric | CSV Column | File | Description |
|--------|-----------|------|-------------|
| Avg Bidding Time | `avg_bidding_time_ms` | fleet_summary | Mean time for server to complete auction (ms) |
| Max Bidding Time | `max_bidding_time_ms` | fleet_summary | Worst-case auction latency |
| Min Bidding Time | `min_bidding_time_ms` | fleet_summary | Best-case auction latency |
| Per-Task Bidding Time | `bidding_time_ms` | assignments | Auction latency for each individual task |

### CSV Files Generated

After each scenario, 5 CSV files are exported to `results/`:

1. **`*_orders.csv`** — Per-order metrics (flow time, energy, distance, wait time, battery remaining)
2. **`*_agv_summary.csv`** — Per-AGV aggregates (tasks, flow time, energy, avg flow)
3. **`*_load_balance.csv`** — CV of tasks, CV of distance, deadlock count, per-AGV breakdown
4. **`*_assignments.csv`** — Task assignment log with bidding time per task
5. **`*_fleet_summary.csv`** — Fleet-level summary with all 4 metric groups

---

## 8. Sample Test Results

The following results were collected from the `basic` scenario (3 AGVs, 6 tasks, ε=0.7):

### Console Output

```
  SIMULATION RESULTS - Scenario: basic_load_balance
======================================================================
  [Time & Efficiency]
    Makespan:           ~144s
    Total Flow Time:    270.7s
    Avg Flow/Task:      45.1s
    Total Wait Time:    aggregated across fleet
    Throughput:         ~2.5 tasks/min

  [Energy]
    Total Energy:       15.4%
    Energy/Task:        2.6%

  [Algorithm Overhead]
    Avg Bidding Time:   measured per POST /tasks/ call

──────────────────────────────────────────────────────────────────────
  AGV        Tasks   FlowTime   Energy    Distance     Wait
  ──────────────────────────────────────────────────────
  AGV_01         2      82.8s    4.02%      80.0m     2.8s
  AGV_02         1      43.2s    2.09%      40.0m     3.2s
  AGV_03         3     144.7s    9.26%     180.0m     4.7s
──────────────────────────────────────────────────────────────────────
  [Load Balance & Robustness]
    CV (Tasks):    0.4082  (0=perfect, <0.3=good, >0.5=poor)
    CV (Distance): ~0.54
    Deadlock Count: 0
======================================================================
```

### Interpretation

- **CV=0.41** is expected at ε=0.7 (MiniSum-biased): the system optimizes total flow time rather than perfect task balance.
- **AGV_03** received 3 tasks because it was closest to multiple pickup locations — this is MiniSum-optimal.
- **No deadlocks** were detected.
- Setting ε closer to 0 would improve load balance (MiniMax) at the cost of higher total flow time.

---

## 9. Customization Guide

### 9.1 Changing the Hybrid Objective Parameter (ε / Epsilon)

> **File:** `backend/vda5050/modules/constant.py`, line 12

```python
# Hybrid Objective Parameter (SSI-DMAS)
# epsilon = 1: Pure MiniSum (Optimize total flow time)
# epsilon = 0: Pure MiniMax (Balance load across AGVs)
EPSILON = 0.7   # <── Change this value
```

| ε Value | Strategy | Expected Behavior |
|---------|----------|-------------------|
| 1.0 | Pure MiniSum | Minimize total flow time; some AGVs may be heavily loaded |
| 0.7 | MiniSum-biased (default) | Good efficiency with moderate balance |
| 0.5 | Balanced | Equal weight to efficiency and fairness |
| 0.3 | MiniMax-biased | Prioritize even task distribution |
| 0.0 | Pure MiniMax | Maximize fairness; total flow time may increase |

**Experiment tip:** Run the same scenario with ε = {0.0, 0.3, 0.5, 0.7, 1.0} and compare CV (load balance) vs Total Flow Time (efficiency) to generate a Pareto curve.

After changing ε, **restart the server** for the change to take effect:
```bash
docker-compose restart web mqtt_worker
```

### 9.2 Changing Fleet Size

**Method 1:** Command line (quickest):
```bash
python multi_agent_runner.py --scenario basic --agvs 5
```

**Method 2:** Edit the scenario definition in `tests/simulators/scenarios.py`:
```python
SCENARIO_BASIC = {
    "fleet": {
        "AGV_01": {"node": "Node_A", "battery": 95.0},
        "AGV_02": {"node": "Node_C", "battery": 95.0},
        "AGV_03": {"node": "Node_E", "battery": 95.0},
        "AGV_04": {"node": "Node_B", "battery": 90.0},  # add more AGVs
    },
    ...
}
```

**Method 3:** Use the `generate_fleet()` helper from `config_sim.py`:
```python
from config_sim import generate_fleet
fleet = generate_fleet(count=10, start_battery=95.0, battery_step=3.0)
```

**Important:** Ensure the server has enough AGVs registered:
```bash
docker exec -it agv-system-web-1 python manage.py setup_test_agvs --count <N>
```

### 9.3 Changing Battery Levels

Edit the `"fleet"` dictionary in any scenario in `tests/simulators/scenarios.py`:

```python
"fleet": {
    "AGV_01": {"node": "Node_A", "battery": 95.0},   # normal (≥30%)
    "AGV_02": {"node": "Node_C", "battery": 25.0},   # low (10%-30%) → 1.5× bid penalty
    "AGV_03": {"node": "Node_E", "battery": 8.0},    # critical (<10%) → rejected
},
```

Use the `battery` scenario as a reference — it already tests a mixed-battery fleet.

### 9.4 Adding / Modifying Tasks

Edit the `"tasks"` list in any scenario in `tests/simulators/scenarios.py`:

```python
"tasks": [
    # {"pickup_node_id", "delivery_node_id", "delay_s"}
    _make_task("Node_A", "Node_D", delay=0),     # dispatched immediately
    _make_task("Node_B", "Node_G", delay=5),     # dispatched 5s after start
    _make_task("Node_H", "Node_C", delay=5),     # dispatched at same 5s (burst)
    _make_task("Node_E", "Node_F", delay=30),    # dispatched 30s after start
],
```

- `delay_s` is relative to the start of the dispatch phase.
- Set the same `delay_s` for multiple tasks to simulate burst arrivals.
- Use larger delays (30s+) to test sequential assignment without contention.

Available nodes: `Node_A` through `Node_H` (4×2 grid, 10m edges).

### 9.5 Creating a Completely New Scenario

Add a new dictionary to `tests/simulators/scenarios.py` and register it in the `SCENARIOS` dict at the bottom of the file:

```python
SCENARIO_MY_TEST = {
    "name": "my_test",
    "description": "My custom experiment",
    "fleet": {
        "AGV_01": {"node": "Node_A", "battery": 95.0},
        "AGV_02": {"node": "Node_H", "battery": 50.0},
    },
    "tasks": [
        _make_task("Node_B", "Node_G", delay=0),
        _make_task("Node_D", "Node_E", delay=10),
    ],
    "timeout_s": 120,
}

# Then add to the SCENARIOS dict:
SCENARIOS = {
    ...
    "my_test": SCENARIO_MY_TEST,
}
```

Then run it:
```bash
python multi_agent_runner.py --scenario my_test
```

---

## 10. Interpreting Results

### Load Balance Quality

The **Coefficient of Variation (CV)** measures how evenly tasks/distances are distributed:

| CV Value | Quality |
|----------|---------|
| 0.0 | Perfect balance |
| < 0.15 | Excellent |
| 0.15 - 0.30 | Good |
| 0.30 - 0.50 | Fair |
| > 0.50 | Poor |

### Flow Time Analysis

- **Total Flow Time** (MiniSum): Measures system efficiency. Lower = better overall.
- **Makespan**: Wall-clock time from first dispatch to last completion. Lower = faster throughput.
- The hybrid objective ($\varepsilon = 0.7$) biases toward MiniSum (efficiency over fairness).

### Energy Efficiency

Compare `energy_per_task_pct` across scenarios to evaluate:
- Impact of fleet size on per-AGV energy
- Effect of battery penalties on task allocation
- Idle energy waste during waiting periods

### Bidding Overhead

- Typical bidding time for a fleet of 3-7 AGVs should be under 100ms.
- If `max_bidding_time_ms` spikes, it may indicate server overload or database contention.

### Deadlock Detection

- The collector monitors AGV states; if an AGV remains stuck (not IDLE, no progress) for >60 seconds, a deadlock event is recorded.
- A non-zero `deadlock_count` warrants investigation into route conflicts or server scheduling.

---

## 11. Troubleshooting

| Issue | Solution |
|-------|----------|
| "Server not reachable" | Ensure `docker-compose up -d` is running |
| AGVs not receiving orders | Check MQTT listener: `docker logs agv-system-web-1` |
| "No suitable AGV found" | Ensure `setup_test_agvs` matches the fleet config manufacturer |
| Tasks timeout | Increase `timeout_s` in scenario or check server logs |
| No results generated | Check that at least some orders completed before timeout |
| MQTT connection refused | Verify broker on port 1884 (host) maps to 1883 (container) |

### Verify Server Health

```bash
# Check AGVs registered
curl http://localhost:8000/api/agvs/

# Check graph loaded
curl http://localhost:8000/api/agvs/AGV_01/states/

# Manual task test
curl -X POST http://localhost:8000/api/tasks/ ^
  -H "Content-Type: application/json" ^
  -d "{\"pickup_node_id\": \"Node_A\", \"delivery_node_id\": \"Node_D\"}"
```
