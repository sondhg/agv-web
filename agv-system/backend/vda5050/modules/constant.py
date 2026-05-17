import os

# --- Physics-Based Energy Model Constants ---
GRAVITY_MPS2 = 9.81  # Gravity acceleration (m/s²)
AGV_MASS_KG = 50.0  # Mass of the AGV (kg)
ROLLING_FRICTION = 0.02  # Rolling friction coefficient
ACCELERATION_MPS2 = 0.5  # Average acceleration (m/s²)
AGV_VELOCITY_MPS = 1.0  # Translational velocity of the AGV (m/s)
WHEELBASE_M = 0.6  # Distance between the wheels (m)
MOTOR_EFFICIENCY = 0.85  # Motor efficiency
TURN_TIME_AVG_SEC = 2.0  # Average turn time (s)

# Backward-compatible alias
AGV_SPEED_MPS = AGV_VELOCITY_MPS

# Weights for the objective function
K_ENERGY = 0.5  # Weight for energy cost
K_TIME = 0.5  # Weight for time cost

# Hybrid Objective Parameter (SSI-DMAS)
# epsilon = 1: Pure MiniSum (Tối ưu tổng thể)
# epsilon = 0: Pure MiniMax (Load balancing)
EPSILON = 0.5

# Reservation-aware waiting penalties (higher => avoid congested routes)
WAIT_CONFLICT_PENALTY = 1.25
UNREACHABLE_ROUTE_PENALTY = 10.0

# Queue depth soft penalty (normalized-score units) to discourage deep chaining
# on the same AGV when pending orders start to accumulate.
PENDING_ORDER_SOFT_PENALTY = 0.8

# Auction strategy feature flag
# - SSI_MARGINAL: main method (energy + time + fairness + congestion aware)
# - GREEDY_DISTANCE: nearest-neighbor by distance to pickup only
# - GREEDY_ETA: nearest estimated completion time (queue + pickup + delivery)
_DEFAULT_AUCTION_ALGORITHM = "SSI_MARGINAL"
_ALLOWED_AUCTION_ALGORITHMS = {
    "SSI_MARGINAL",
    "GREEDY_DISTANCE",
    "GREEDY_ETA",
}
AUCTION_ALGORITHM = os.getenv("AUCTION_ALGORITHM", _DEFAULT_AUCTION_ALGORITHM).upper()
if AUCTION_ALGORITHM not in _ALLOWED_AUCTION_ALGORITHMS:
    AUCTION_ALGORITHM = _DEFAULT_AUCTION_ALGORITHM

# System Default
DEFAULT_LOAD_KG = 50.0  # Assuming average load weight if not known

# Fallback Constants
FALLBACK_NORM_ENERGY_KJ = 1.0
FALLBACK_NORM_TFT_SEC = 1.0
