# --- Physics-Based Energy Model Constants ---
GRAVITY_MPS2 = 9.81          # Gravity acceleration (m/s²)
AGV_MASS_KG = 50.0           # Mass of the AGV (kg)
ROLLING_FRICTION = 0.02      # Rolling friction coefficient
ACCELERATION_MPS2 = 0.5      # Average acceleration (m/s²)
AGV_VELOCITY_MPS = 1.0       # Translational velocity of the AGV (m/s)
WHEELBASE_M = 0.6            # Distance between the wheels (m)
MOTOR_EFFICIENCY = 0.85      # Motor efficiency
TURN_TIME_AVG_SEC = 2.0      # Average turn time (s)

# Backward-compatible alias
AGV_SPEED_MPS = AGV_VELOCITY_MPS

# Weights for the objective function
K_ENERGY = 0.5          # Weight for energy cost
K_TIME = 0.5            # Weight for time cost

# Hybrid Objective Parameter (SSI-DMAS)
# epsilon = 1: Pure MiniSum (Tối ưu tổng thể)
# epsilon = 0: Pure MiniMax (Load balancing)
EPSILON = 0.5

# Auction strategy feature flag
# 'SSI_MARGINAL': Existing SSI marginal-cost algorithm (default)
# 'GREEDY_DISTANCE': Baseline nearest-neighbor by distance to pickup
AUCTION_ALGORITHM = 'SSI_MARGINAL'

# System Default
DEFAULT_LOAD_KG = 50.0  # Assuming average load weight if not known

# Fallback Constants
FALLBACK_NORM_ENERGY_KJ = 1.0 
FALLBACK_NORM_TFT_SEC = 1.0