"""
AuctionCoordinator: Điều phối đấu giá và chọn AGV thắng cuộc.
Chịu trách nhiệm tổ chức auction process và quyết định winner.
"""

import logging
from vda5050.models import AGV
from .calculators.bid import BidCalculator
from ..constant import DEFAULT_LOAD_KG

logger = logging.getLogger(__name__)


class AuctionCoordinator:
    """
    Class điều phối quá trình đấu giá.

    Responsibilities:
    - Thu thập danh sách AGV khả dụng
    - Gọi bid từ mỗi AGV
    - So sánh và chọn winner
    - Log chi tiết quá trình đấu giá

    Attributes:
        bid_calculator (BidCalculator): Calculator để tính bid cho từng AGV
    """

    def __init__(self, bid_calculator=None):
        """
        Khởi tạo coordinator với dependencies.

        Args:
            bid_calculator: BidCalculator instance
        """
        self.bid_calculator = bid_calculator or BidCalculator()
        logger.debug("AuctionCoordinator initialized")

    def get_available_agvs(self):
        """
        Lấy danh sách AGV khả dụng để tham gia đấu giá.

        Returns:
            QuerySet: Danh sách AGV online
        """
        agvs = AGV.objects.filter(is_online=True)
        logger.debug(f"Found {agvs.count()} available AGVs")
        return agvs

    def collect_bids(
        self, agvs, pickup_node_id, delivery_node_id=None, load_kg=DEFAULT_LOAD_KG
    ):
        """
        Thu thập bid từ tất cả AGV.

        Args:
            agvs: QuerySet hoặc list của AGV instances
            pickup_node_id: Node lấy hàng
            delivery_node_id: Node giao hàng (nếu None, chỉ đi đến pickup)
            load_kg: Tải trọng

        Returns:
            list: [(bid_score, agv, bid_details), ...]
        """
        bids = []

        if delivery_node_id:
            logger.info(
                f"Collecting bids for Pickup={pickup_node_id} -> Delivery={delivery_node_id}, Load={load_kg}kg"
            )
        else:
            logger.info(
                f"Collecting bids for Target={pickup_node_id}, Load={load_kg}kg"
            )

        for agv in agvs:
            bid_result = self.bid_calculator.calculate_full_bid(
                agv, pickup_node_id, delivery_node_id, load_kg
            )

            if bid_result:
                bid_score = bid_result["bid_final"]
                bids.append((bid_score, agv, bid_result))

                logger.info(
                    f"   🤖 {agv.serial_number}: "
                    f"Bid={bid_score:.4f} "
                    f"(E={bid_result['energy_marginal']:.2f}kJ, "
                    f"T={bid_result['time_marginal']:.2f}s, "
                    f"Bat={bid_result['battery']}%)"
                )
            else:
                logger.info(
                    f"   🤖 {agv.serial_number}: Cannot bid (Inf cost / Constraints)"
                )

        return bids

    def select_winner(self, bids):
        """
        Chọn AGV thắng cuộc từ danh sách bids.

        Args:
            bids: List of (bid_score, agv, bid_details) từ collect_bids()

        Returns:
            tuple: (winner_agv, winner_details) hoặc (None, None) nếu không có winner
        """
        if not bids:
            logger.warning("No valid bids received")
            return None, None

        # Sắp xếp theo bid score (thấp nhất thắng)
        bids.sort(key=lambda x: x[0])

        winner_score, winner_agv, winner_details = bids[0]

        logger.info(f"WINNER: {winner_agv.serial_number} (Score: {winner_score:.4f})")

        return winner_agv, winner_details

    def run_auction(
        self, pickup_node_id, delivery_node_id=None, load_kg=DEFAULT_LOAD_KG
    ):
        """
        Chạy toàn bộ quy trình đấu giá (main entry point).

        Args:
            pickup_node_id: Node lấy hàng
            delivery_node_id: Node giao hàng (nếu None, chỉ đi đến pickup)
            load_kg: Tải trọng

        Returns:
            tuple: (winner_agv, error_message)
                - winner_agv: AGV instance thắng cuộc, hoặc None nếu thất bại
                - error_message: None nếu thành công, string mô tả lỗi nếu thất bại
        """
        logger.info("========== START AUCTION ==========")
        if delivery_node_id:
            logger.info(f"Pickup: {pickup_node_id}, Delivery: {delivery_node_id}")
        else:
            logger.info(f"Target: {pickup_node_id}")
        logger.info(f"Load: {load_kg}kg")
        logger.info("======================================")

        # Bước 1: Lấy danh sách AGV
        agvs = self.get_available_agvs()

        if not agvs.exists():
            error_msg = "No AGVs online"
            logger.error(f"AUCTION FAILED: {error_msg}")
            return None, error_msg

        # Bước 2: Thu thập bids
        bids = self.collect_bids(agvs, pickup_node_id, delivery_node_id, load_kg)

        if not bids:
            error_msg = "No reachable AGV"
            logger.error(f"AUCTION FAILED: {error_msg}")
            return None, error_msg

        # Bước 3: Chọn winner
        winner_agv, winner_details = self.select_winner(bids)

        if not winner_agv:
            error_msg = "Failed to select winner"
            logger.error(f"AUCTION FAILED: {error_msg}")
            return None, error_msg

        # Log kết quả chi tiết
        logger.info("======================================")
        logger.info(f"   Auction Result: {winner_agv.serial_number}")
        logger.info(f"   Bid Score: {winner_details['bid_final']:.4f}")
        logger.info(f"   Energy: {winner_details['energy_marginal']:.2f}kJ")
        logger.info(f"   Time: {winner_details['time_marginal']:.2f}s")
        logger.info(f"   Battery: {winner_details['battery']}%")
        logger.info("========== END AUCTION ==========")

        return winner_agv, None

    def run_auction_with_details(
        self, pickup_node_id, delivery_node_id=None, load_kg=DEFAULT_LOAD_KG
    ):
        """
        Chạy auction và trả về kết quả chi tiết (bao gồm cả tất cả bids).

        Args:
            pickup_node_id: Node lấy hàng
            delivery_node_id: Node giao hàng (nếu None, chỉ đi đến pickup)
            load_kg: Tải trọng

        Returns:
            dict: {
                'winner_agv': AGV instance hoặc None,
                'winner_details': dict hoặc None,
                'all_bids': list of (score, agv, details),
                'error': string hoặc None
            }
        """
        agvs = self.get_available_agvs()

        if not agvs.exists():
            return {
                "winner_agv": None,
                "winner_details": None,
                "all_bids": [],
                "error": "No AGVs online",
            }

        bids = self.collect_bids(agvs, pickup_node_id, delivery_node_id, load_kg)

        if not bids:
            return {
                "winner_agv": None,
                "winner_details": None,
                "all_bids": [],
                "error": "No reachable AGV",
            }

        winner_agv, winner_details = self.select_winner(bids)

        return {
            "winner_agv": winner_agv,
            "winner_details": winner_details,
            "all_bids": bids,
            "error": None if winner_agv else "Failed to select winner",
        }
