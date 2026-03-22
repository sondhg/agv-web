# Physics-Based Energy Model Implementation

## Overview
Update the energy cost calculation in `backend/vda5050/modules/bidding/calculators/transport.py` to accurately implement physics-based formulas for energy consumption.

## Mathematical Formulas

### Translational Mechanical Power
$$P_{m,trans} = (m_{agv} + m_{load}) \cdot (\mu_r g + a) \cdot v_{AGV}$$

### Rotational Mechanical Power
$$P_{m,rot} = \frac{(m_{agv} + m_{load}) \cdot (\mu_r g + a) \cdot l_{AGV}}{2}$$

### Electrical Power and Total Energy
$$P_e = \frac{P_{m,trans} + P_{m,rot}}{\eta_{motor}}$$
$$E_{total} = E_{trans} + E_{rot}$$

### Travel Time Model
$$T_{travel} = \frac{d_{task}}{v_{avg}} + N_{turns} \cdot t_{turn\_avg}$$

## Implementation Tasks

1. **Update `constant.py`** with physical parameters:
    - `AGV_MASS_KG = 50.0`
    - `ROLLING_FRICTION = 0.02`
    - `ACCELERATION_MPS2 = 0.5`
    - `AGV_VELOCITY_MPS = 1.0`
    - `WHEELBASE_M = 0.6`
    - `MOTOR_EFFICIENCY = 0.85`
    - `TURN_TIME_AVG_SEC = 2.0`

2. **Refactor `TransportCalculator` class**:
    - Load all constants in `__init__`
    - Implement `calculate_travel_time(distance_m, num_turns=0)`
    - Implement `calculate_energy_consumption(distance_m, num_turns=0, load_kg=0)` computing $E_{trans}$, $E_{rot}$, and total energy
    - Add debug logging for all intermediate power/energy values

3. **Integration check**: Verify `auction.py` and `bid.py` pass `num_turns` parameter to calculator.

