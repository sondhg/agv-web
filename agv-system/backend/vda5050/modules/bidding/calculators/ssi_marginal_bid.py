"""SSI marginal bidding strategy."""

import logging

from ...constant import DEFAULT_LOAD_KG, K_ENERGY, K_TIME, EPSILON

logger = logging.getLogger(__name__)


class SsiMarginalBidStrategy:
    """Strategy implementing SSI-marginal objective and hybrid scoring."""

    def __init__(self, calculator):
        """Keep a reference to BidCalculator for shared helpers and dependencies."""
        self.calculator = calculator

    def _calculate_single_leg_marginal(self, agv, start_node, pickup_node_id, load_kg, wait_time):
        """Calculate marginal metrics for single-leg trip: start -> pickup."""
        actual_distance, actual_turns = self.calculator.graph_engine.get_path_info(start_node, pickup_node_id)

        if actual_distance == float('inf'):
            logger.warning(f"AGV {agv.serial_number}: No path {start_node}→{pickup_node_id}")
            return None

        energy_travel, time_travel = self.calculator.transport_calculator.calculate_metrics(
            actual_distance, load_kg, actual_turns
        )

        return {
            'energy_marginal': energy_travel,
            'time_marginal': wait_time + time_travel,
            'baseline_result': self.calculator.baseline_calculator.calculate_and_normalize(
                start_node, pickup_node_id, actual_distance, load_kg
            )
        }

    def _calculate_two_leg_marginal(
        self,
        agv,
        start_node,
        pickup_node_id,
        delivery_node_id,
        load_kg,
        wait_time,
    ):
        """Calculate marginal metrics for two-leg trip: start -> pickup -> delivery."""
        distance_leg1, turns_leg1 = self.calculator.graph_engine.get_path_info(start_node, pickup_node_id)
        if distance_leg1 == float('inf'):
            logger.warning(f"AGV {agv.serial_number}: No path {start_node}→{pickup_node_id}")
            return None

        energy_leg1, time_leg1 = self.calculator.transport_calculator.calculate_metrics(
            distance_leg1, 0, turns_leg1
        )

        distance_leg2, turns_leg2 = self.calculator.graph_engine.get_path_info(
            pickup_node_id, delivery_node_id
        )
        if distance_leg2 == float('inf'):
            logger.warning(f"AGV {agv.serial_number}: No path {pickup_node_id}→{delivery_node_id}")
            return None

        energy_leg2, time_leg2 = self.calculator.transport_calculator.calculate_metrics(
            distance_leg2, load_kg, turns_leg2
        )

        total_distance = distance_leg1 + distance_leg2

        return {
            'energy_marginal': energy_leg1 + energy_leg2,
            'time_marginal': wait_time + time_leg1 + time_leg2,
            'baseline_result': self.calculator.baseline_calculator.calculate_and_normalize(
                start_node, delivery_node_id, total_distance, load_kg
            )
        }

    @staticmethod
    def _normalize_queue_components(
        queue_time,
        queue_energy,
        time_marginal,
        energy_marginal,
        norm_time,
        norm_energy,
    ):
        """Normalize queue terms onto the same scale as normalized marginal metrics."""
        travel_time = time_marginal - queue_time

        if travel_time > 0 and norm_time > 0:
            baseline_time_unit = travel_time / norm_time
            norm_queue_time = queue_time / baseline_time_unit
        else:
            norm_queue_time = 0.0

        if energy_marginal > 0 and norm_energy > 0:
            baseline_energy_unit = energy_marginal / norm_energy
            norm_queue_energy = queue_energy / baseline_energy_unit
        else:
            norm_queue_energy = 0.0

        return norm_queue_time, norm_queue_energy

    def calculate_marginal_cost(self, agv, pickup_node_id, delivery_node_id=None, load_kg=DEFAULT_LOAD_KG):
        """Calculate marginal cost for one AGV."""
        state = self.calculator.get_agv_current_state(agv)
        if not state or not state['is_valid']:
            return None

        current_node = state['current_node']
        battery = state['battery']
        is_charging = state.get('is_charging', False)

        battery_check = self.calculator.check_battery_constraint(
            battery,
            is_charging=is_charging,
        )
        if not battery_check['is_acceptable']:
            return None

        wait_info = self.calculator.calculate_wait_cost(agv, current_node, load_kg)
        start_node = wait_info['start_node']
        wait_time = wait_info['wait_time_s']
        queue_energy = wait_info.get('queue_energy_kj', 0.0)
        num_pending = wait_info.get('num_pending', 0)

        if delivery_node_id:
            trip_result = self._calculate_two_leg_marginal(
                agv,
                start_node,
                pickup_node_id,
                delivery_node_id,
                load_kg,
                wait_time,
            )
        else:
            trip_result = self._calculate_single_leg_marginal(
                agv,
                start_node,
                pickup_node_id,
                load_kg,
                wait_time,
            )

        if not trip_result:
            return None

        energy_marginal = trip_result['energy_marginal']
        time_marginal = trip_result['time_marginal']
        baseline_result = trip_result['baseline_result']

        return {
            'energy_marginal': energy_marginal,
            'time_marginal': time_marginal,
            'norm_energy': baseline_result['norm_energy'],
            'norm_time': baseline_result['norm_time'],
            'battery': battery,
            'battery_penalty': battery_check['penalty_factor'],
            'queue_time_s': wait_time,
            'queue_energy_kj': queue_energy,
            'num_pending': num_pending,
            'is_valid': True
        }

    def calculate_bid_score(self, marginal_cost_result, epsilon=None):
        """Compute bid score from marginal cost (Hybrid Objective / SSI-DMAS)."""
        if not marginal_cost_result or not marginal_cost_result.get('is_valid'):
            return float('inf')

        norm_energy = marginal_cost_result['norm_energy']
        norm_time = marginal_cost_result['norm_time']
        battery_penalty = marginal_cost_result.get('battery_penalty', 1.0)
        queue_time = marginal_cost_result.get('queue_time_s', 0.0)
        queue_energy = marginal_cost_result.get('queue_energy_kj', 0.0)
        time_marginal = marginal_cost_result.get('time_marginal', 0.0)
        energy_marginal = marginal_cost_result.get('energy_marginal', 0.0)

        eps = epsilon if epsilon is not None else EPSILON
        bid_minisum = (K_ENERGY * norm_energy) + (K_TIME * norm_time)

        norm_queue_time, norm_queue_energy = self._normalize_queue_components(
            queue_time,
            queue_energy,
            time_marginal,
            energy_marginal,
            norm_time,
            norm_energy,
        )

        bid_minimax = (
            K_ENERGY * (norm_energy + norm_queue_energy)
            + K_TIME * (norm_time + norm_queue_time)
        )

        bid_final = (eps * bid_minisum) + ((1 - eps) * bid_minimax)
        bid_final *= battery_penalty

        logger.info(
            f"Bid score: MiniSum={bid_minisum:.4f}, MiniMax={bid_minimax:.4f}, "
            f"Hybrid={bid_final:.4f} (ε={eps}, penalty={battery_penalty}, "
            f"queue_time={queue_time:.1f}s, norm_qT={norm_queue_time:.2f}, "
            f"norm_qE={norm_queue_energy:.2f})"
        )

        return bid_final

    def calculate_full_bid(
        self,
        agv,
        pickup_node_id,
        delivery_node_id=None,
        load_kg=DEFAULT_LOAD_KG,
        epsilon=None,
    ):
        """Calculate the full bid for one AGV (all-in-one)."""
        marginal_result = self.calculate_marginal_cost(
            agv, pickup_node_id, delivery_node_id, load_kg
        )

        if not marginal_result:
            logger.info(f"AGV {agv.serial_number}: Cannot bid (no valid marginal cost)")
            return None

        bid_score = self.calculate_bid_score(marginal_result, epsilon=epsilon)

        if bid_score == float('inf'):
            logger.info(f"AGV {agv.serial_number}: Cannot bid (infinite score)")
            return None

        result = {
            'bid_final': bid_score,
            'energy_marginal': marginal_result['energy_marginal'],
            'time_marginal': marginal_result['time_marginal'],
            'battery': marginal_result['battery'],
            'details': marginal_result
        }

        logger.info(
            f"AGV {agv.serial_number}: Bid={bid_score:.4f} "
            f"(E={marginal_result['energy_marginal']:.2f}kJ, "
            f"T={marginal_result['time_marginal']:.2f}s, "
            f"Bat={marginal_result['battery']}%)"
        )

        return result
