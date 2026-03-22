# --- Physics-Based Energy Model Constants ---
GRAVITY_MPS2 = 9.81          # Gia tốc trọng trường (m/s²)
AGV_MASS_KG = 50.0           # Khối lượng AGV không tải (kg)
ROLLING_FRICTION = 0.02      # Hệ số ma sát lăn
ACCELERATION_MPS2 = 0.5      # Gia tốc trung bình (m/s²)
AGV_VELOCITY_MPS = 1.0       # Vận tốc tịnh tiến AGV (m/s)
WHEELBASE_M = 0.6            # Khoảng cách giữa hai bánh (m)
MOTOR_EFFICIENCY = 0.85      # Hiệu suất motor
TURN_TIME_AVG_SEC = 2.0      # Thời gian quay đầu trung bình (s)

# Backward-compatible alias
AGV_SPEED_MPS = AGV_VELOCITY_MPS

# Weights cho hàm mục tiêu
K_ENERGY = 0.5          # Trọng số năng lượng
K_TIME = 0.5            # Trọng số thời gian

# Hybrid Objective Parameter (SSI-DMAS)
# epsilon = 1: Pure MiniSum (Tối ưu tổng thể)
# epsilon = 0: Pure MiniMax (Cân bằng tải)
EPSILON = 0.5

# Auction strategy feature flag
# 'SSI_MARGINAL': Existing SSI marginal-cost algorithm (default)
# 'GREEDY_DISTANCE': Baseline nearest-neighbor by distance to pickup
AUCTION_ALGORITHM = 'SSI_MARGINAL'

# System Default
DEFAULT_LOAD_KG = 50.0  # Giả sử tải trọng trung bình nếu không biết

# Fallback Constants
FALLBACK_NORM_ENERGY_KJ = 1.0 
FALLBACK_NORM_TFT_SEC = 1.0