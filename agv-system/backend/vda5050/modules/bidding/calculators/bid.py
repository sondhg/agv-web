"""
BidCalculator: Tính toán giá thầu (bid) cho AGV.
Chịu trách nhiệm tính marginal cost, scoring và các ràng buộc.
"""

import logging
from vda5050.models import AGVState, Order
from vda5050.graph_engine import GraphEngine
from .transport import TransportCalculator
from .baseline import BaselineCalculator
from ...constant import DEFAULT_LOAD_KG, K_ENERGY, K_TIME, EPSILON

logger = logging.getLogger(__name__)


class BidCalculator:
    """
    Class tính toán giá thầu cho AGV.

    Áp dụng logic:
    - Marginal Cost: Chi phí biên (chỉ tính phần công việc thêm vào)
    - Baseline Normalization: Chuẩn hóa so với chi phí lý tưởng
    - Hybrid Objective: Kết hợp MiniSum (hiệu quả) và MiniMax (cân bằng tải)
    - Battery Constraints: Ràng buộc và phạt về pin

    Attributes:
        graph_engine (GraphEngine): Engine để tính đường đi
        transport_calculator (TransportCalculator): Calculator cho metrics vật lý
        baseline_calculator (BaselineCalculator): Calculator cho baseline normalization
    """

    def __init__(
        self, graph_engine=None, transport_calculator=None, baseline_calculator=None
    ):
        """
        Khởi tạo calculator với dependencies.

        Args:
            graph_engine: GraphEngine instance
            transport_calculator: TransportCalculator instance
            baseline_calculator: BaselineCalculator instance
        """
        self.graph_engine = graph_engine or GraphEngine()
        self.transport_calculator = transport_calculator or TransportCalculator()
        self.baseline_calculator = baseline_calculator or BaselineCalculator(
            self.graph_engine, self.transport_calculator
        )

        logger.debug("BidCalculator initialized")

    def get_agv_current_state(self, agv):
        """
        Lấy trạng thái hiện tại của AGV.

        Args:
            agv: AGV instance

        Returns:
            dict: {
                'current_node': str,
                'battery': float,
                'is_valid': bool
            } hoặc None nếu không có state
        """
        last_state = AGVState.objects.filter(agv=agv).order_by("-timestamp").first()

        if not last_state:
            logger.warning(f"AGV {agv.serial_number}: No state data available")
            return None

        current_node = last_state.last_node_id
        current_battery = last_state.battery_state.get("batteryCharge", 0)

        logger.debug(
            f"AGV {agv.serial_number}: Node={current_node}, Battery={current_battery}%"
        )

        return {
            "current_node": current_node,
            "battery": current_battery,
            "is_valid": True,
        }

    def check_battery_constraint(self, battery_percent):
        """
        Kiểm tra ràng buộc pin.

        Args:
            battery_percent: Phần trăm pin hiện tại

        Returns:
            dict: {
                'is_acceptable': bool,  # Có thể tham gia đấu giá không
                'penalty_factor': float # Hệ số phạt (1.0 = không phạt, >1.0 = phạt)
            }
        """
        if battery_percent < 10.0:
            # Pin dưới 10%: Từ chối hoàn toàn
            logger.warning(f"Critical battery: {battery_percent}% - REJECTED")
            return {"is_acceptable": False, "penalty_factor": float("inf")}
        elif battery_percent < 30.0:
            # Pin dưới 30%: Chấp nhận nhưng phạt nặng
            penalty = 1.5
            logger.info(f"Low battery: {battery_percent}% - Penalty x{penalty}")
            return {"is_acceptable": True, "penalty_factor": penalty}
        else:
            # Pin đủ: Không phạt
            return {"is_acceptable": True, "penalty_factor": 1.0}

    def calculate_wait_cost(self, agv, current_node, load_kg):
        """
        Tính chi phí chờ (wait cost) nếu AGV đang bận.

        Args:
            agv: AGV instance
            current_node: Node hiện tại của AGV
            load_kg: Tải trọng dự kiến

        Returns:
            dict: {
                'start_node': str,  # Node mà AGV sẽ bắt đầu task mới
                'wait_time_s': float  # Thời gian phải chờ AGV rảnh
            }
        """
        # Kiểm tra xem AGV có đang làm việc không
        active_order = Order.objects.filter(
            agv=agv, status__in=["SENT", "ACTIVE", "QUEUED"]
        ).last()

        start_node = current_node
        wait_time = 0.0

        if active_order:
            try:
                # AGV đang bận: Phải đợi đến khi hoàn thành task cũ
                end_node = active_order.nodes[-1]["nodeId"]
                start_node = end_node

                # Ước tính thời gian còn lại để hoàn thành task cũ
                remaining_distance = self.graph_engine.get_path_cost(
                    current_node, end_node
                )

                if remaining_distance != float("inf"):
                    _, wait_time = self.transport_calculator.calculate_metrics(
                        remaining_distance, load_kg
                    )
                    logger.debug(
                        f"AGV {agv.serial_number} busy: wait_time={wait_time:.2f}s "
                        f"to complete {current_node}→{end_node}"
                    )
                else:
                    logger.warning(
                        f"AGV {agv.serial_number}: Cannot calculate wait time "
                        f"(no path {current_node}→{end_node})"
                    )
            except Exception as e:
                logger.error(
                    f"Error calculating wait cost for {agv.serial_number}: {e}"
                )
                start_node = current_node

        return {"start_node": start_node, "wait_time_s": wait_time}

    def calculate_marginal_cost(
        self, agv, pickup_node_id, delivery_node_id=None, load_kg=DEFAULT_LOAD_KG
    ):
        """
        Tính marginal cost (chi phí biên) cho một AGV.

        Args:
            agv: AGV instance
            pickup_node_id: Node lấy hàng
            delivery_node_id: Node giao hàng (nếu None, chỉ đi đến pickup)
            load_kg: Tải trọng

        Returns:
            dict: {
                'energy_marginal': float,
                'time_marginal': float,
                'norm_energy': float,
                'norm_time': float,
                'is_valid': bool
            } hoặc None nếu không thể bid
        """
        # Bước 1: Lấy trạng thái hiện tại
        state = self.get_agv_current_state(agv)
        if not state or not state["is_valid"]:
            return None

        current_node = state["current_node"]
        battery = state["battery"]

        # Bước 2: Kiểm tra ràng buộc pin
        battery_check = self.check_battery_constraint(battery)
        if not battery_check["is_acceptable"]:
            return None

        # Bước 3: Tính wait cost (nếu AGV đang bận)
        wait_info = self.calculate_wait_cost(agv, current_node, load_kg)
        start_node = wait_info["start_node"]
        wait_time = wait_info["wait_time_s"]

        # Bước 4: Tính chi phí cho từng chặng
        if delivery_node_id:
            # 2-leg trip: current -> pickup -> delivery
            # Leg 1: current -> pickup (không mang hàng)
            distance_leg1 = self.graph_engine.get_path_cost(start_node, pickup_node_id)
            if distance_leg1 == float("inf"):
                logger.warning(
                    f"AGV {agv.serial_number}: No path {start_node}→{pickup_node_id}"
                )
                return None

            energy_leg1, time_leg1 = self.transport_calculator.calculate_metrics(
                distance_leg1,
                0,  # Không mang hàng
            )

            # Leg 2: pickup -> delivery (mang hàng)
            distance_leg2 = self.graph_engine.get_path_cost(
                pickup_node_id, delivery_node_id
            )
            if distance_leg2 == float("inf"):
                logger.warning(
                    f"AGV {agv.serial_number}: No path {pickup_node_id}→{delivery_node_id}"
                )
                return None

            energy_leg2, time_leg2 = self.transport_calculator.calculate_metrics(
                distance_leg2,
                load_kg,  # Mang hàng
            )

            # Tổng chi phí
            energy_marginal = energy_leg1 + energy_leg2
            time_marginal = wait_time + time_leg1 + time_leg2
            total_distance = distance_leg1 + distance_leg2

            # Chuẩn hóa với baseline (sử dụng khoảng cách trực tiếp từ start đến delivery)
            baseline_result = self.baseline_calculator.calculate_and_normalize(
                start_node, delivery_node_id, total_distance, load_kg
            )
        else:
            # Single-leg trip: current -> pickup
            actual_distance = self.graph_engine.get_path_cost(
                start_node, pickup_node_id
            )

            if actual_distance == float("inf"):
                logger.warning(
                    f"AGV {agv.serial_number}: No path {start_node}→{pickup_node_id}"
                )
                return None

            # Tính metrics thực tế
            energy_travel, time_travel = self.transport_calculator.calculate_metrics(
                actual_distance, load_kg
            )

            # Marginal time = wait time + travel time
            time_marginal = wait_time + time_travel
            energy_marginal = energy_travel  # Energy chỉ tính phần di chuyển

            # Bước 5: Chuẩn hóa với baseline
            baseline_result = self.baseline_calculator.calculate_and_normalize(
                start_node, pickup_node_id, actual_distance, load_kg
            )

        return {
            "energy_marginal": energy_marginal,
            "time_marginal": time_marginal,
            "norm_energy": baseline_result["norm_energy"],
            "norm_time": baseline_result["norm_time"],
            "battery": battery,
            "battery_penalty": battery_check["penalty_factor"],
            "is_valid": True,
        }

    def calculate_bid_score(self, marginal_cost_result):
        """
        Tính điểm bid từ marginal cost (Hybrid Objective).

        Args:
            marginal_cost_result: Kết quả từ calculate_marginal_cost()

        Returns:
            float: Điểm bid (càng thấp càng tốt)
        """
        if not marginal_cost_result or not marginal_cost_result.get("is_valid"):
            return float("inf")

        norm_energy = marginal_cost_result["norm_energy"]
        norm_time = marginal_cost_result["norm_time"]
        battery_penalty = marginal_cost_result.get("battery_penalty", 1.0)

        # MiniSum: Ưu tiên hiệu quả biên (xe tốn ít công sức nhất)
        bid_minisum = (K_ENERGY * norm_energy) + (K_TIME * norm_time)

        # MiniMax: Ưu tiên cân bằng tải (xe đang ít việc nhất)
        # Đơn giản hóa: Dùng chính bid_minisum làm đại diện
        # (Logic chuẩn sẽ cần tổng energy tích lũy của xe)
        bid_minimax = bid_minisum

        # Hybrid: Kết hợp cả hai
        bid_final = (EPSILON * bid_minisum) + ((1 - EPSILON) * bid_minimax)

        # Áp dụng penalty từ pin
        bid_final *= battery_penalty

        logger.debug(
            f"Bid score: MiniSum={bid_minisum:.4f}, MiniMax={bid_minimax:.4f}, "
            f"Hybrid={bid_final:.4f} (penalty={battery_penalty})"
        )

        return bid_final

    def calculate_full_bid(
        self, agv, pickup_node_id, delivery_node_id=None, load_kg=DEFAULT_LOAD_KG
    ):
        """
        Tính toán bid đầy đủ cho một AGV (all-in-one).

        Args:
            agv: AGV instance
            pickup_node_id: Node lấy hàng
            delivery_node_id: Node giao hàng (nếu None, chỉ đi đến pickup)
            load_kg: Tải trọng

        Returns:
            dict: {
                'bid_final': float,
                'energy_marginal': float,
                'time_marginal': float,
                'battery': float,
                'details': dict
            } hoặc None nếu không thể bid
        """
        # Tính marginal cost
        marginal_result = self.calculate_marginal_cost(
            agv, pickup_node_id, delivery_node_id, load_kg
        )

        if not marginal_result:
            logger.info(f"AGV {agv.serial_number}: Cannot bid (no valid marginal cost)")
            return None

        # Tính bid score
        bid_score = self.calculate_bid_score(marginal_result)

        if bid_score == float("inf"):
            logger.info(f"AGV {agv.serial_number}: Cannot bid (infinite score)")
            return None

        result = {
            "bid_final": bid_score,
            "energy_marginal": marginal_result["energy_marginal"],
            "time_marginal": marginal_result["time_marginal"],
            "battery": marginal_result["battery"],
            "details": marginal_result,
        }

        logger.info(
            f"AGV {agv.serial_number}: Bid={bid_score:.4f} "
            f"(E={marginal_result['energy_marginal']:.2f}kJ, "
            f"T={marginal_result['time_marginal']:.2f}s, "
            f"Bat={marginal_result['battery']}%)"
        )

        return result
