"""
Energy Model Configuration for AGV Simulation.
Constants defined per ENERGY-INSTRUCTIONS.md for the bidding/task allocation research.
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class EnergyConfig:
    """Physical constants for AGV energy calculations."""

    # Kinematic parameters
    VELOCITY: float = 10.0            # m/s  - Translational velocity
    ROTATION_SPEED: float = 30.0     # deg/s - Rotation speed

    # Power consumption rates (battery % per second)
    POWER_MOVING: float = 0.05       # %/s while translating
    POWER_ROTATION: float = 0.03     # %/s while rotating
    POWER_IDLE: float = 0.005        # %/s while idle/waiting

    # Battery thresholds
    BATTERY_CRITICAL: float = 10.0   # % - Stop all operations
    BATTERY_LOW: float = 30.0        # % - Restricted, penalty applied
    BATTERY_LOW_PENALTY: float = 1.5 # Penalty coefficient for marginal cost

    def calculate_move_energy(self, distance_m: float) -> tuple[float, float]:
        """
        Calculate translational energy cost.

        Returns:
            (time_s, energy_percent)
        """
        t_move = distance_m / self.VELOCITY
        e_move = t_move * self.POWER_MOVING
        return t_move, e_move

    def calculate_rotation_energy(self, angle_deg: float) -> tuple[float, float]:
        """
        Calculate rotational energy cost.

        Returns:
            (time_s, energy_percent)
        """
        t_turn = abs(angle_deg) / self.ROTATION_SPEED
        e_turn = t_turn * self.POWER_ROTATION
        return t_turn, e_turn

    def calculate_idle_energy(self, wait_time_s: float) -> float:
        """
        Calculate idle energy cost.

        Returns:
            energy_percent
        """
        return wait_time_s * self.POWER_IDLE

    def calculate_total_energy(
        self, distance_m: float, turn_angle_deg: float = 0.0, wait_time_s: float = 0.0
    ) -> dict:
        """
        Calculate total energy for a movement segment.

        Returns:
            dict with time and energy breakdowns
        """
        t_move, e_move = self.calculate_move_energy(distance_m)
        t_turn, e_turn = self.calculate_rotation_energy(turn_angle_deg)
        e_idle = self.calculate_idle_energy(wait_time_s)

        return {
            "time_move_s": t_move,
            "time_turn_s": t_turn,
            "time_wait_s": wait_time_s,
            "time_total_s": t_move + t_turn + wait_time_s,
            "energy_move_pct": e_move,
            "energy_turn_pct": e_turn,
            "energy_idle_pct": e_idle,
            "energy_total_pct": e_move + e_turn + e_idle,
        }


# Singleton instance
ENERGY = EnergyConfig()
