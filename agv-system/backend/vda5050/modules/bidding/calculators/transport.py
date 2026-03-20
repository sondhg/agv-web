"""
TransportCalculator: Tính toán các chỉ số vật lý của việc vận chuyển.
Chịu trách nhiệm tính Energy (kJ) và Time (s) dựa trên khoảng cách và tải trọng.
"""

import logging
from ...constant import (
    C_BASE,
    C_LOAD_COEFF,
    AGV_SPEED_MPS,
    FALLBACK_NORM_ENERGY_KJ,
    FALLBACK_NORM_TFT_SEC,
)

logger = logging.getLogger(__name__)


class TransportCalculator:
    """
    Class tính toán các metrics cơ bản của việc vận chuyển.

    Attributes:
        speed_mps (float): Tốc độ trung bình của AGV (m/s)
        c_base (float): Hệ số năng lượng cơ bản
        c_load_coeff (float): Hệ số năng lượng theo tải trọng
    """

    def __init__(
        self, speed_mps=AGV_SPEED_MPS, c_base=C_BASE, c_load_coeff=C_LOAD_COEFF
    ):
        """
        Khởi tạo calculator với các thông số vật lý.

        Args:
            speed_mps: Tốc độ trung bình AGV (m/s)
            c_base: Hệ số năng lượng cơ bản
            c_load_coeff: Hệ số năng lượng theo tải trọng
        """
        self.speed_mps = speed_mps
        self.c_base = c_base
        self.c_load_coeff = c_load_coeff

        logger.debug(
            f"TransportCalculator initialized: speed={speed_mps}m/s, "
            f"c_base={c_base}, c_load={c_load_coeff}"
        )

    def calculate_travel_time(self, distance_m):
        """
        Tính thời gian di chuyển dựa trên khoảng cách.

        Args:
            distance_m (float): Khoảng cách (mét)

        Returns:
            float: Thời gian di chuyển (giây)
        """
        if distance_m < 0:
            logger.warning(f"Negative distance received: {distance_m}m, returning 0")
            return 0.0

        if distance_m == float("inf"):
            return float("inf")

        time_s = distance_m / self.speed_mps
        logger.debug(
            f"Travel time: {distance_m}m @ {self.speed_mps}m/s = {time_s:.2f}s"
        )
        return time_s

    def calculate_energy_consumption(self, distance_m, load_kg=0):
        """
        Tính năng lượng tiêu thụ dựa trên công thức vật lý.
        E = (C_base + C_load * m_load) * distance

        Args:
            distance_m (float): Khoảng cách (mét)
            load_kg (float): Tải trọng (kg)

        Returns:
            float: Năng lượng tiêu thụ (kJ)
        """
        if distance_m < 0:
            logger.warning(f"Negative distance received: {distance_m}m, returning 0")
            return 0.0

        if distance_m == float("inf"):
            return float("inf")

        energy_kj = (self.c_base + (self.c_load_coeff * load_kg)) * distance_m
        logger.debug(
            f"Energy consumption: ({self.c_base} + {self.c_load_coeff}*{load_kg}kg) * {distance_m}m = {energy_kj:.2f}kJ"
        )
        return energy_kj

    def calculate_metrics(self, distance_m, load_kg=0):
        """
        Tính toán đồng thời cả energy và time.

        Args:
            distance_m (float): Khoảng cách (mét)
            load_kg (float): Tải trọng (kg)

        Returns:
            tuple: (energy_kj, time_s)
        """
        energy_kj = self.calculate_energy_consumption(distance_m, load_kg)
        time_s = self.calculate_travel_time(distance_m)

        return energy_kj, time_s

    def validate_metrics(self, energy_kj, time_s):
        """
        Kiểm tra và điều chỉnh metrics để tránh giá trị không hợp lệ.

        Args:
            energy_kj (float): Năng lượng (kJ)
            time_s (float): Thời gian (s)

        Returns:
            tuple: (validated_energy_kj, validated_time_s)
        """
        validated_energy = energy_kj if energy_kj > 0 else FALLBACK_NORM_ENERGY_KJ
        validated_time = time_s if time_s > 0 else FALLBACK_NORM_TFT_SEC

        if energy_kj <= 0 or time_s <= 0:
            logger.warning(
                f"Invalid metrics detected (E={energy_kj}, T={time_s}). "
                f"Using fallback values (E={validated_energy}, T={validated_time})"
            )

        return validated_energy, validated_time
