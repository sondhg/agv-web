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
        if self.calculator.is_agv_locked_for_charging(agv):
            logger.info(
                f"AGV {agv.serial_number}: Greedy reject (charging mission active or charging state)"
            )
            state = self.calculator.get_agv_current_state(agv)
            battery = state["battery"] if state and state.get("is_valid") else 0.0
            start_node = state["current_node"] if state and state.get("is_valid") else None
            return self.calculator._build_greedy_invalid_result(battery, start_node)

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
            'queue_time_s': wait_info.get('wait_time_s', 0.0),
            'queue_energy_kj': wait_info.get('queue_energy_kj', 0.0),
            'is_valid': True,
        }

    def calculate_eta_bid(
        self,
        agv,
        pickup_node_id,
        delivery_node_id=None,
        load_kg=DEFAULT_LOAD_KG,
    ):
        """Greedy ETA baseline: minimize projected completion time only."""
        if self.calculator.is_agv_locked_for_charging(agv):
            logger.info(
                f"AGV {agv.serial_number}: Greedy ETA reject (charging mission active or charging state)"
            )
            state = self.calculator.get_agv_current_state(agv)
            battery = state["battery"] if state and state.get("is_valid") else 0.0
            start_node = state["current_node"] if state and state.get("is_valid") else None
            return self.calculator._build_greedy_invalid_result(battery, start_node)

        state = self.calculator.get_agv_current_state(agv)
        if not state or not state.get("is_valid"):
            return None

        battery = state["battery"]
        battery_check = self.calculator.check_battery_constraint(
            battery,
            is_charging=state.get("is_charging", False),
        )
        if not battery_check["is_acceptable"]:
            logger.info(
                f"AGV {agv.serial_number}: Greedy ETA reject (battery={battery}%)"
            )
            return self.calculator._build_greedy_invalid_result(
                battery,
                state["current_node"],
            )

        wait_info = self.calculator.calculate_wait_cost(
            agv,
            state["current_node"],
            load_kg,
        )
        start_node = wait_info.get("start_node", state["current_node"])
        queue_time_s = wait_info.get("wait_time_s", 0.0)
        queue_energy_kj = wait_info.get("queue_energy_kj", 0.0)

        try:
            distance_leg1, turns_leg1 = self.calculator.graph_engine.get_path_info(
                start_node,
                pickup_node_id,
            )
        except Exception as exc:
            logger.error(f"Greedy ETA leg1 error for {agv.serial_number}: {exc}")
            return None

        if distance_leg1 == float("inf"):
            return self.calculator._build_greedy_invalid_result(battery, start_node)

        # Empty travel to pickup.
        energy_leg1, time_leg1 = self.calculator.transport_calculator.calculate_metrics(
            distance_leg1,
            0,
            turns_leg1,
        )

        distance_leg2 = 0.0
        turns_leg2 = 0
        energy_leg2 = 0.0
        time_leg2 = 0.0
        if delivery_node_id:
            try:
                distance_leg2, turns_leg2 = self.calculator.graph_engine.get_path_info(
                    pickup_node_id,
                    delivery_node_id,
                )
            except Exception as exc:
                logger.error(f"Greedy ETA leg2 error for {agv.serial_number}: {exc}")
                return None

            if distance_leg2 == float("inf"):
                return self.calculator._build_greedy_invalid_result(battery, start_node)

            # Loaded travel from pickup to delivery.
            energy_leg2, time_leg2 = self.calculator.transport_calculator.calculate_metrics(
                distance_leg2,
                load_kg,
                turns_leg2,
            )

        eta_seconds = queue_time_s + time_leg1 + time_leg2
        total_distance = distance_leg1 + distance_leg2
        total_energy_kj = queue_energy_kj + energy_leg1 + energy_leg2

        return {
            "bid_final": eta_seconds,
            "eta_s": eta_seconds,
            "distance_to_pickup_m": distance_leg1,
            "distance_total_m": total_distance,
            "time_to_pickup_s": time_leg1,
            "time_loaded_s": time_leg2,
            "energy_kj": total_energy_kj,
            "queue_time_s": queue_time_s,
            "queue_energy_kj": queue_energy_kj,
            "battery": battery,
            "start_node": start_node,
            "is_valid": True,
        }
