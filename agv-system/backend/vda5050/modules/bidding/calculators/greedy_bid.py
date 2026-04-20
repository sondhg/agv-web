"""Greedy distance bidding strategy."""

import logging

from ...constant import DEFAULT_LOAD_KG

logger = logging.getLogger(__name__)


class GreedyBidStrategy:
    """Strategy for nearest-neighbor greedy bidding."""

    def __init__(self, calculator):
        """Keep a reference to BidCalculator for shared helpers and dependencies."""
        self.calculator = calculator

    def calculate_bid(self, agv, pickup_node_id):
        """Calculate greedy bid using projected start node and pickup distance only."""
        state = self.calculator.get_agv_current_state(agv)
        if not state or not state['is_valid']:
            return None

        battery = state['battery']
        battery_check = self.calculator.check_battery_constraint(
            battery,
            is_charging=state.get('is_charging', False),
        )
        if not battery_check['is_acceptable']:
            logger.info(f"AGV {agv.serial_number}: Greedy reject (battery={battery}%)")
            return self.calculator._build_greedy_invalid_result(battery, state['current_node'])

        wait_info = self.calculator.calculate_wait_cost(
            agv, state['current_node'], DEFAULT_LOAD_KG
        )
        start_node = wait_info.get('start_node', state['current_node'])

        try:
            distance = self.calculator.graph_engine.get_path_cost(start_node, pickup_node_id)
        except Exception as exc:
            logger.error(f"Greedy distance error for {agv.serial_number}: {exc}")
            return None

        if distance == float('inf'):
            return self.calculator._build_greedy_invalid_result(battery, start_node)

        return {
            'bid_final': distance,
            'distance_to_pickup_m': distance,
            'battery': battery,
            'start_node': start_node,
            'is_valid': True,
        }
