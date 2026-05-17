"""GREEDY_DISTANCE bidding strategy - Nearest neighbor by distance."""

import logging

logger = logging.getLogger(__name__)


class GreedyDistanceBidStrategy:
    """
    GREEDY_DISTANCE: Tham lam theo Không gian

    Thuật toán này đại diện cho các hệ thống AGV thế hệ cũ.
    Chỉ quan tâm: "Xe nào đang đứng gần điểm lấy hàng nhất thì giao cho xe đó".

    Đặc điểm:
    - KHÔNG quan tâm đến thời gian chờ (hàng đợi)
    - KHÔNG quan tâm xe đang rảnh hay bận
    - KHÔNG quan tâm năng lượng
    - KHÔNG phạt pin (chỉ hard reject khi < 10%)

    Hàm giá thầu (Bidding Function):
    Bid_GD = D(N_current → N_pickup)

    Giải thích: Giá thầu chỉ đơn thuần là khoảng cách hình học ngắn nhất
    từ vị trí vật lý hiện tại của AGV (N_current) đến điểm lấy hàng (N_pickup).
    """

    def __init__(self, calculator):
        """Keep a reference to BidCalculator for shared helpers and dependencies."""
        self.calculator = calculator

    def calculate_bid(self, agv, pickup_node_id):
        """
        Calculate GREEDY_DISTANCE bid using only current position and pickup distance.

        Pure distance-based bidding with no queue awareness.

        Args:
            agv: AGV instance
            pickup_node_id: Pickup node ID

        Returns:
            dict | None: {
                'bid_final': float (distance in meters),
                'distance_to_pickup_m': float,
                'battery': float,
                'current_node': str,
                'is_valid': bool,
            }
        """
        # Check if AGV is locked for charging
        if self.calculator.is_agv_locked_for_charging(agv):
            logger.info(
                f"AGV {agv.serial_number}: GREEDY_DISTANCE reject "
                f"(charging mission active or charging state)"
            )
            state = self.calculator.get_agv_current_state(agv)
            battery = state["battery"] if state and state.get("is_valid") else 0.0
            current_node = (
                state["current_node"] if state and state.get("is_valid") else None
            )
            return self._build_invalid_result(battery, current_node)

        # Get AGV state
        state = self.calculator.get_agv_current_state(agv)
        if not state or not state["is_valid"]:
            return None

        battery = state["battery"]
        current_node = state["current_node"]

        # Check battery constraint (hard reject if < 10%)
        battery_check = self.calculator.check_battery_constraint(
            battery,
            is_charging=state.get("is_charging", False),
        )
        if not battery_check["is_acceptable"]:
            logger.info(
                f"AGV {agv.serial_number}: GREEDY_DISTANCE reject (battery={battery}%)"
            )
            return self._build_invalid_result(battery, current_node)

        # Calculate distance from CURRENT position to pickup
        # NO queue consideration, NO wait_cost calculation
        try:
            distance = self.calculator.graph_engine.get_path_cost(
                current_node, pickup_node_id
            )
        except Exception as exc:
            logger.error(f"GREEDY_DISTANCE error for {agv.serial_number}: {exc}")
            return None

        if distance == float("inf"):
            logger.info(
                f"AGV {agv.serial_number}: GREEDY_DISTANCE - No path to pickup "
                f"({current_node}→{pickup_node_id})"
            )
            return self._build_invalid_result(battery, current_node)

        logger.debug(
            f"AGV {agv.serial_number}: GREEDY_DISTANCE bid calculated "
            f"(distance={distance:.2f}m from {current_node} to {pickup_node_id})"
        )

        return {
            "bid_final": distance,
            "distance_to_pickup_m": distance,
            "battery": battery,
            "current_node": current_node,
            "is_valid": True,
        }

    @staticmethod
    def _build_invalid_result(battery, current_node):
        """Build a standardized invalid result."""
        return {
            "bid_final": float("inf"),
            "distance_to_pickup_m": float("inf"),
            "battery": battery,
            "current_node": current_node,
            "is_valid": False,
        }
