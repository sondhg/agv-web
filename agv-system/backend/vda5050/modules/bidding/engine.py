"""
BiddingEngine: Main facade cho bidding system.
Đây là interface chính để các module khác sử dụng bidding algorithm.
Nội bộ sử dụng các component OOP đã được tách riêng.
"""

import logging
from vda5050.graph_engine import GraphEngine
from .calculators.transport import TransportCalculator
from .calculators.baseline import BaselineCalculator
from .calculators.bid import BidCalculator
from .auction import AuctionCoordinator
from ..constant import DEFAULT_LOAD_KG

logger = logging.getLogger(__name__)


class BiddingEngine:
    """
    Facade class cho bidding system.

    Cung cấp interface đơn giản cho các module khác sử dụng,
    trong khi nội bộ sử dụng kiến trúc OOP modular.

    Attributes:
        graph_engine (GraphEngine): Shared graph engine
        transport_calculator (TransportCalculator): Tính toán metrics vật lý
        baseline_calculator (BaselineCalculator): Tính toán baseline normalization
        bid_calculator (BidCalculator): Tính toán bid scores
        auction_coordinator (AuctionCoordinator): Điều phối đấu giá
    """

    def __init__(self, graph_engine=None):
        """
        Khởi tạo BiddingEngine với dependency injection.

        Args:
            graph_engine: GraphEngine instance (tạo mới nếu None)
        """
        # Shared components
        self.graph_engine = graph_engine or GraphEngine()

        # Initialize modular components
        self.transport_calculator = TransportCalculator()
        self.baseline_calculator = BaselineCalculator(
            graph_engine=self.graph_engine,
            transport_calculator=self.transport_calculator,
        )
        self.bid_calculator = BidCalculator(
            graph_engine=self.graph_engine,
            transport_calculator=self.transport_calculator,
            baseline_calculator=self.baseline_calculator,
        )
        self.auction_coordinator = AuctionCoordinator(
            bid_calculator=self.bid_calculator
        )

        logger.info("BiddingEngine initialized with modular OOP architecture")

    # ==================== BACKWARD COMPATIBILITY METHODS ====================
    # These methods maintain the old interface for existing code

    def _calculate_transport_metrics(self, distance_m, load_kg=0):
        """
        Legacy method: Tính toán Energy (kJ) và Time (s).
        Giờ delegate sang TransportCalculator.

        DEPRECATED: Use self.transport_calculator.calculate_metrics() directly.
        """
        return self.transport_calculator.calculate_metrics(distance_m, load_kg)

    def _get_baseline(self, start_node_id, target_node_id, load_kg):
        """
        Legacy method: Tính chi phí Baseline.
        Giờ delegate sang BaselineCalculator.

        DEPRECATED: Use self.baseline_calculator.calculate_baseline_metrics() directly.
        """
        return self.baseline_calculator.calculate_baseline_metrics(
            start_node_id, target_node_id, load_kg
        )

    def calculate_marginal_cost(self, agv, target_node_id, load_kg=DEFAULT_LOAD_KG):
        """
        Legacy method: Tính giá thầu chi tiết cho một AGV.
        Giờ delegate sang BidCalculator.

        DEPRECATED: Use self.bid_calculator.calculate_full_bid() directly.
        """
        return self.bid_calculator.calculate_full_bid(agv, target_node_id, load_kg)

    # ==================== PRIMARY PUBLIC METHODS ====================

    def run_auction(
        self, pickup_node_id, delivery_node_id=None, load_kg=DEFAULT_LOAD_KG
    ):
        """
        Tổ chức đấu giá và chọn xe thắng cuộc (Main entry point).

        Args:
            pickup_node_id: Node lấy hàng (pickup)
            delivery_node_id: Node giao hàng (delivery). Nếu None, chỉ đi đến pickup_node_id
            load_kg: Tải trọng (kg)

        Returns:
            tuple: (winner_agv, error_message)
                - winner_agv: AGV instance thắng cuộc, hoặc None nếu thất bại
                - error_message: None nếu thành công, string nếu có lỗi
        """
        return self.auction_coordinator.run_auction(
            pickup_node_id, delivery_node_id, load_kg
        )

    def run_auction_with_details(self, target_node_id, load_kg=DEFAULT_LOAD_KG):
        """
        Chạy auction và trả về kết quả chi tiết.

        Args:
            target_node_id: Node đích
            load_kg: Tải trọng

        Returns:
            dict: {
                'winner_agv': AGV instance hoặc None,
                'winner_details': dict,
                'all_bids': list of (score, agv, details),
                'error': string hoặc None
            }
        """
        return self.auction_coordinator.run_auction_with_details(
            target_node_id, load_kg
        )

    # ==================== COMPONENT ACCESS METHODS ====================
    # For advanced usage: direct access to internal components

    def get_transport_calculator(self):
        """Get TransportCalculator instance."""
        return self.transport_calculator

    def get_baseline_calculator(self):
        """Get BaselineCalculator instance."""
        return self.baseline_calculator

    def get_bid_calculator(self):
        """Get BidCalculator instance."""
        return self.bid_calculator

    def get_auction_coordinator(self):
        """Get AuctionCoordinator instance."""
        return self.auction_coordinator
