"""GREEDY_ETA bidding strategy - Estimated Time of Arrival."""

import logging

from ...constant import DEFAULT_LOAD_KG

logger = logging.getLogger(__name__)


class GreedyEtaBidStrategy:
    """
    GREEDY_ETA: Tham lam theo Thời gian dự kiến đến
    
    Thuật toán này đại diện cho các hệ thống điều phối công nghiệp tiêu chuẩn hiện nay.
    Nó thông minh hơn Distance vì quan tâm đến thời gian: 
    "Xe nào có khả năng đến điểm lấy hàng sớm nhất thì giao cho xe đó".
    
    Đặc điểm:
    - CÓ tính đến thời gian chờ (hàng đợi) - T_queue_clearance
    - KHÔNG quan tâm đến năng lượng tiêu thụ (K_E = 0)
    - KHÔNG quan tâm đến mức pin yếu (P_bat = 1.0)
    - KHÔNG tính toán độ trễ do tắc nghẽn giao thông (Conflict_Penalty = 0)
    - CHỈ ước lượng queue theo độ dài hàng đợi, không mô phỏng đầy đủ đường đi của từng task nợ
    
    Hàm giá thầu (Bidding Function):
    Bid_ETA = T_queue_clearance + T_travel(N_last_node → N_pickup)
    
    Giải thích: Giá thầu là Tổng thời gian để AGV giải quyết xong các task đang nợ 
    cộng với thời gian di chuyển từ điểm trả hàng cuối cùng đến điểm lấy hàng mới.
    """

    def __init__(self, calculator):
        """Keep a reference to BidCalculator for shared helpers and dependencies."""
        self.calculator = calculator

    def calculate_eta_bid(
        self,
        agv,
        pickup_node_id,
        delivery_node_id=None,
        load_kg=DEFAULT_LOAD_KG,
    ):
        """
        Calculate GREEDY_ETA bid based on queue delay + travel time to pickup.
        
        This baseline intentionally stays simpler than SSI:
        - queue delay is approximated from pending order count
        - travel time uses the current node, not the queue end node
        - delivery leg is ignored in the bid score
        
        Args:
            agv: AGV instance
            pickup_node_id: Pickup node ID
            delivery_node_id: Delivery node ID (if None, only travel to pickup)
            load_kg: Payload weight (kg)
            
        Returns:
            dict | None: {
                'bid_final': float (ETA in seconds),
                'eta_s': float,
                'queue_time_s': float,
                'time_to_pickup_s': float,
                'distance_to_pickup_m': float,
                'battery': float,
                'start_node': str,
                'is_valid': bool,
            }
        """
        # Check if AGV is locked for charging
        if self.calculator.is_agv_locked_for_charging(agv):
            logger.info(
                f"AGV {agv.serial_number}: GREEDY_ETA reject "
                f"(charging mission active or charging state)"
            )
            state = self.calculator.get_agv_current_state(agv)
            battery = state["battery"] if state and state.get("is_valid") else 0.0
            current_node = state["current_node"] if state and state.get("is_valid") else None
            return self._build_invalid_result(battery, current_node)

        # Get AGV state
        state = self.calculator.get_agv_current_state(agv)
        if not state or not state.get("is_valid"):
            return None

        battery = state["battery"]
        current_node = state["current_node"]
        
        # Check battery constraint (hard reject if < 10%)
        # GREEDY_ETA does NOT apply soft penalty for low battery
        battery_check = self.calculator.check_battery_constraint(
            battery,
            is_charging=state.get("is_charging", False),
        )
        if not battery_check["is_acceptable"]:
            logger.info(
                f"AGV {agv.serial_number}: GREEDY_ETA reject (battery={battery}%)"
            )
            return self._build_invalid_result(battery, current_node)

        # Approximate queue delay from pending order count instead of simulating the full backlog.
        queue_time_s = self._estimate_queue_delay(agv)

        # Keep the baseline local: use current position directly.
        start_node = current_node

        # Calculate travel time from queue end to pickup
        try:
            distance_leg1, turns_leg1 = self.calculator.graph_engine.get_path_info(
                start_node,
                pickup_node_id,
            )
        except Exception as exc:
            logger.error(f"GREEDY_ETA leg1 error for {agv.serial_number}: {exc}")
            return None

        if distance_leg1 == float("inf"):
            logger.info(
                f"AGV {agv.serial_number}: GREEDY_ETA - No path to pickup "
                f"({start_node}→{pickup_node_id})"
            )
            return self._build_invalid_result(battery, start_node)

        # Empty travel to pickup (unloaded)
        energy_leg1, time_leg1 = self.calculator.transport_calculator.calculate_metrics(
            distance_leg1,
            0,  # empty
            turns_leg1,
        )

        # Delivery leg is intentionally ignored to keep GREEDY_ETA as a simpler baseline.
        time_leg2 = 0.0
        total_distance = distance_leg1

        # Total ETA = queue time + travel time to pickup only (NO energy component)
        eta_seconds = queue_time_s + time_leg1

        logger.debug(
            f"AGV {agv.serial_number}: GREEDY_ETA bid calculated "
            f"(ETA={eta_seconds:.2f}s = queue={queue_time_s:.2f}s + travel={time_leg1:.2f}s)"
        )

        return {
            "bid_final": eta_seconds,
            "eta_s": eta_seconds,
            "distance_to_pickup_m": distance_leg1,
            "distance_total_m": total_distance,
            "time_to_pickup_s": time_leg1,
            "time_loaded_s": time_leg2,
            "queue_time_s": queue_time_s,
            "battery": battery,
            "start_node": start_node,
            "is_valid": True,
        }

    def _estimate_queue_delay(self, agv):
        """
        Estimate queue delay from the number of pending orders.
        
        This is intentionally coarser than SSI: one fixed delay per pending order.
        """
        from vda5050.models import Order
        
        pending_orders = Order.objects.filter(
            agv=agv,
            status__in=['SENT', 'ACTIVE', 'QUEUED']
        ).order_by('created_at')

        if not pending_orders.exists():
            return 0.0

        pending_count = pending_orders.count()
        fixed_delay_per_order_s = 20.0
        return pending_count * fixed_delay_per_order_s

    @staticmethod
    def _build_invalid_result(battery, start_node):
        """Build a standardized invalid result."""
        return {
            'bid_final': float('inf'),
            'eta_s': float('inf'),
            'queue_time_s': 0.0,
            'time_to_pickup_s': 0.0,
            'distance_to_pickup_m': float('inf'),
            'battery': battery,
            'start_node': start_node,
            'is_valid': False,
        }
