# --- Cost Calculation Constants ---
C_BASE = 0.05  # kJ/m (Năng lượng tiêu thụ cơ bản trên mỗi mét)
C_LOAD_COEFF = 0.002  # kJ/(kg·m) (Hệ số tiêu thụ thêm theo tải trọng)

# Weights cho hàm mục tiêu
K_ENERGY = 0.5  # Trọng số năng lượng
K_TIME = 0.5  # Trọng số thời gian

# Hybrid Objective Parameter (SSI-DMAS)
# epsilon = 1: Pure MiniSum (Tối ưu tổng thể)
# epsilon = 0: Pure MiniMax (Cân bằng tải)
EPSILON = 0.7

# System Default
DEFAULT_LOAD_KG = 50.0  # Giả sử tải trọng trung bình nếu không biết
AGV_SPEED_MPS = 1.0  # 1 m/s (Giả sử vận tốc trung bình để tính Time)

# Fallback Constants
FALLBACK_NORM_ENERGY_KJ = 1.0
FALLBACK_NORM_TFT_SEC = 1.0
