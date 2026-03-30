"""
TransportCalculator: Calculator for transport metrics (energy, time) based on physics.

Using a physics-based energy model:
  P_m,trans = (m_agv + m_load) · (μ_r·g + a) · v
  P_m,rot   = (m_agv + m_load) · (μ_r·g + a) · l / 2
  P_e       = (P_m,trans + P_m,rot) / η
  T_travel  = d / v + N_turns · t_turn_avg
  E_total   = E_trans + E_rot
"""

import logging
from ...constant import (
    AGV_VELOCITY_MPS, AGV_MASS_KG, ROLLING_FRICTION,
    ACCELERATION_MPS2, GRAVITY_MPS2, WHEELBASE_M,
    MOTOR_EFFICIENCY, TURN_TIME_AVG_SEC,
    FALLBACK_NORM_ENERGY_KJ, FALLBACK_NORM_TFT_SEC
)

logger = logging.getLogger(__name__)


class TransportCalculator:
    """
    Calculator for transport metrics (energy, time) based on physics.
    """

    def __init__(
        self,
        speed_mps=AGV_VELOCITY_MPS,
        agv_mass_kg=AGV_MASS_KG,
        rolling_friction=ROLLING_FRICTION,
        acceleration=ACCELERATION_MPS2,
        gravity=GRAVITY_MPS2,
        wheelbase_m=WHEELBASE_M,
        motor_efficiency=MOTOR_EFFICIENCY,
        turn_time_avg=TURN_TIME_AVG_SEC,
    ):
        self.speed_mps = speed_mps
        self.agv_mass_kg = agv_mass_kg
        self.rolling_friction = rolling_friction
        self.acceleration = acceleration
        self.gravity = gravity
        self.wheelbase_m = wheelbase_m
        self.motor_efficiency = motor_efficiency
        self.turn_time_avg = turn_time_avg

        logger.debug(
            f"TransportCalculator initialized: v={speed_mps}m/s, "
            f"m_agv={agv_mass_kg}kg, μ={rolling_friction}, a={acceleration}m/s², "
            f"l={wheelbase_m}m, η={motor_efficiency}, t_turn={turn_time_avg}s"
        )

    # ---------- internal helpers ----------

    def _force_factor(self, load_kg: float) -> float:
        """(m_agv + m_load) · (μ_r·g + a)"""
        total_mass = self.agv_mass_kg + load_kg
        return total_mass * (self.rolling_friction * self.gravity + self.acceleration)

    def _power_translational(self, load_kg: float) -> float:
        """P_m,trans = force_factor · v  [W]"""
        return self._force_factor(load_kg) * self.speed_mps

    def _power_rotational(self, load_kg: float) -> float:
        """P_m,rot = force_factor · l / 2  [W]"""
        return self._force_factor(load_kg) * self.wheelbase_m / 2.0

    # ---------- public API ----------

    def calculate_travel_time(self, distance_m: float, num_turns: int = 0) -> float:
        """
        T_travel = d / v + N_turns · t_turn_avg
        """
        if distance_m < 0:
            logger.warning(f"Negative distance received: {distance_m}m, returning 0")
            return 0.0
        if distance_m == float('inf'):
            return float('inf')

        t_trans = distance_m / self.speed_mps
        t_rot = num_turns * self.turn_time_avg
        time_s = t_trans + t_rot

        logger.debug(
            f"Travel time: {distance_m}m @ {self.speed_mps}m/s = {t_trans:.2f}s "
            f"+ {num_turns} turns × {self.turn_time_avg}s = {time_s:.2f}s"
        )
        return time_s

    def calculate_energy_consumption(
        self, distance_m: float, num_turns: int = 0, load_kg: float = 0
    ) -> float:
        """
        Physics-based energy calculation (kJ).

        E_trans = (P_m,trans / η) · (d / v)
        E_rot   = (P_m,rot  / η) · (N_turns · t_turn)
        E_total = E_trans + E_rot   (Joules → kJ)
        """
        if distance_m < 0:
            logger.warning(f"Negative distance received: {distance_m}m, returning 0")
            return 0.0
        if distance_m == float('inf'):
            return float('inf')

        p_trans = self._power_translational(load_kg)
        p_rot = self._power_rotational(load_kg)

        t_trans = distance_m / self.speed_mps          # seconds
        t_rot = num_turns * self.turn_time_avg          # seconds

        e_trans_j = (p_trans / self.motor_efficiency) * t_trans
        e_rot_j = (p_rot / self.motor_efficiency) * t_rot
        energy_kj = (e_trans_j + e_rot_j) / 1000.0     # J → kJ

        logger.debug(
            f"Energy: P_trans={p_trans:.2f}W, P_rot={p_rot:.2f}W | "
            f"E_trans={e_trans_j:.2f}J, E_rot={e_rot_j:.2f}J | "
            f"Total={energy_kj:.4f}kJ (load={load_kg}kg, d={distance_m}m, turns={num_turns})"
        )
        return energy_kj

    def calculate_metrics(
        self, distance_m: float, load_kg: float = 0, num_turns: int = 0
    ) -> tuple:
        """
        Calculate both energy and time metrics.

        Returns:
            tuple: (energy_kj, time_s)
        """
        energy_kj = self.calculate_energy_consumption(distance_m, num_turns, load_kg)
        time_s = self.calculate_travel_time(distance_m, num_turns)
        return energy_kj, time_s

    def validate_metrics(self, energy_kj: float, time_s: float) -> tuple:
        """
        Validate and adjust metrics to avoid invalid values.
        """
        validated_energy = energy_kj if energy_kj > 0 else FALLBACK_NORM_ENERGY_KJ
        validated_time = time_s if time_s > 0 else FALLBACK_NORM_TFT_SEC

        if energy_kj <= 0 or time_s <= 0:
            logger.warning(
                f"Invalid metrics detected (E={energy_kj}, T={time_s}). "
                f"Using fallback values (E={validated_energy}, T={validated_time})"
            )
        return validated_energy, validated_time
