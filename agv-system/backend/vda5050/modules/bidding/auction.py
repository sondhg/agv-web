"""
AuctionCoordinator: Coordinator for managing the auction process and selecting the winning AGV.
"""

import logging
from vda5050.models import AGV
from .calculators.bid import BidCalculator
from ..constant import DEFAULT_LOAD_KG, AUCTION_ALGORITHM

logger = logging.getLogger(__name__)


class AuctionCoordinator:
    """
    Class for coordinating the auction process and selecting the winning AGV.
    
    Responsibilities:
    - Collecting bids from all available AGVs
    - Calling bids from each AGV
    - Comparing and selecting the winner
    - Logging detailed auction process
    
    Attributes:
        bid_calculator (BidCalculator): Bid calculator for each AGV
    """
    
    def __init__(self, bid_calculator=None):
        """
        Initialize coordinator with dependencies.
        
        Args:
            bid_calculator: BidCalculator instance
        """
        self.bid_calculator = bid_calculator or BidCalculator()
        logger.debug("AuctionCoordinator initialized")
    
    def get_available_agvs(self):
        """
        Get the list of available AGVs to participate in the auction.
        
        Returns:
            QuerySet: List of online AGVs
        """
        agvs = AGV.objects.filter(is_online=True)
        logger.debug(f"Found {agvs.count()} available AGVs")
        return agvs
    
    def collect_bids(self, agvs, pickup_node_id, delivery_node_id=None, load_kg=DEFAULT_LOAD_KG, epsilon=None):
        """
        Collect bids from all available AGVs.
        
        Args:
            agvs: QuerySet or AGV instances list
            pickup_node_id: Pickup node
            delivery_node_id: Delivery node (if None, only go to pickup)
            load_kg: Load weight
            epsilon: Override hybrid parameter (None = use default)
            
        Returns:
            list: [(bid_score, agv, bid_details), ...]
        """
        bids = []

        algorithm = AUCTION_ALGORITHM
        
        if delivery_node_id:
            logger.info(
                f"Collecting bids for Pickup={pickup_node_id} -> Delivery={delivery_node_id}, "
                f"Load={load_kg}kg, ε={epsilon}, Algorithm={algorithm}"
            )
        else:
            logger.info(
                f"Collecting bids for Target={pickup_node_id}, Load={load_kg}kg, "
                f"ε={epsilon}, Algorithm={algorithm}"
            )
        
        for agv in agvs:
            if algorithm == 'SSI_MARGINAL':
                bid_result = self.bid_calculator.calculate_full_bid(
                    agv, pickup_node_id, delivery_node_id, load_kg, epsilon=epsilon
                )
            elif algorithm == 'GREEDY_DISTANCE':
                bid_result = self.bid_calculator.calculate_greedy_distance_bid(
                    agv, pickup_node_id
                )
            else:
                raise ValueError(f"Unknown AUCTION_ALGORITHM: {algorithm}")
            
            if bid_result and bid_result.get('is_valid', True):
                bid_score = bid_result['bid_final']
                bids.append((bid_score, agv, bid_result))

                if algorithm == 'SSI_MARGINAL':
                    logger.info(
                        f"   🤖 {agv.serial_number}: "
                        f"Bid={bid_score:.4f} "
                        f"(E={bid_result['energy_marginal']:.2f}kJ, "
                        f"T={bid_result['time_marginal']:.2f}s, "
                        f"Bat={bid_result['battery']}%)"
                    )
                else:
                    logger.info(
                        f"   🤖 {agv.serial_number}: "
                        f"Bid={bid_score:.4f} "
                        f"(Dist={bid_result['distance_to_pickup_m']:.2f}m, "
                        f"Start={bid_result['start_node']}, "
                        f"Bat={bid_result['battery']}%)"
                    )
            else:
                logger.info(f"   🤖 {agv.serial_number}: Cannot bid (Inf cost / Constraints)")
        
        return bids
    
    def select_winner(self, bids):
        """
        Select the winning AGV from the list of bids.
        
        Args:
            bids: List of (bid_score, agv, bid_details) from collect_bids()
            
        Returns:
            tuple: (winner_agv, winner_details) or (None, None) if no winner
        """
        if not bids:
            logger.warning("No valid bids received")
            return None, None
        
        # Sort bids by score (ascending)
        bids.sort(key=lambda x: x[0])
        
        winner_score, winner_agv, winner_details = bids[0]
        
        logger.info(f"WINNER: {winner_agv.serial_number} (Score: {winner_score:.4f})")
        
        return winner_agv, winner_details
    
    def run_auction(self, pickup_node_id, delivery_node_id=None, load_kg=DEFAULT_LOAD_KG, epsilon=None):
        """
        Run the entire auction process (main entry point).
        
        Args:
            pickup_node_id: Pickup node
            delivery_node_id: Delivery node (if None, only go to pickup)
            load_kg: Load weight
            epsilon: Override hybrid parameter (None = use default)
            
        Returns:
            tuple: (winner_agv, error_message)
                - winner_agv: AGV instance, or None if failed
                - error_message: None if successful, string describing the error if failed
        """
        logger.info("========== START AUCTION ==========")
        if delivery_node_id:
            logger.info(f"Pickup: {pickup_node_id}, Delivery: {delivery_node_id}")
        else:
            logger.info(f"Target: {pickup_node_id}")
        logger.info(
            f"Load: {load_kg}kg, ε={epsilon if epsilon is not None else 'default'}, "
            f"Algorithm={AUCTION_ALGORITHM}"
        )
        logger.info("======================================")
        
        # Step 1: Get list of available AGVs
        agvs = self.get_available_agvs()
        
        if not agvs.exists():
            error_msg = "No AGVs online"
            logger.error(f"AUCTION FAILED: {error_msg}")
            return None, error_msg
        
        # Step 2: Collect bids
        bids = self.collect_bids(agvs, pickup_node_id, delivery_node_id, load_kg, epsilon=epsilon)
        
        if not bids:
            error_msg = "No reachable AGV"
            logger.error(f"AUCTION FAILED: {error_msg}")
            return None, error_msg
        
        # Step 3: Select winner
        winner_agv, winner_details = self.select_winner(bids)
        
        if not winner_agv:
            error_msg = "Failed to select winner"
            logger.error(f"AUCTION FAILED: {error_msg}")
            return None, error_msg
        
        # Log detailed results
        logger.info("======================================")
        logger.info(f"   Auction Result: {winner_agv.serial_number}")
        logger.info(f"   Bid Score: {winner_details['bid_final']:.4f}")
        if AUCTION_ALGORITHM == 'SSI_MARGINAL':
            logger.info(f"   Energy: {winner_details['energy_marginal']:.2f}kJ")
            logger.info(f"   Time: {winner_details['time_marginal']:.2f}s")
        elif AUCTION_ALGORITHM == 'GREEDY_DISTANCE':
            logger.info(f"   Distance to Pickup: {winner_details['distance_to_pickup_m']:.2f}m")
        logger.info(f"   Battery: {winner_details['battery']}%")
        logger.info("========== END AUCTION ==========")
        
        return winner_agv, None
    
    def run_auction_with_details(self, pickup_node_id, delivery_node_id=None, load_kg=DEFAULT_LOAD_KG):
        """
        Run the auction and return detailed results (including all bids).
        
        Args:
            pickup_node_id: Pickup node
            delivery_node_id: Delivery node (if None, only go to pickup)
            load_kg: Load weight
            
        Returns:
            dict: {
                'winner_agv': AGV instance or None,
                'winner_details': dict or None,
                'all_bids': list of (score, agv, details),
                'error': string or None
            }
        """
        agvs = self.get_available_agvs()
        
        if not agvs.exists():
            return {
                'winner_agv': None,
                'winner_details': None,
                'all_bids': [],
                'error': 'No AGVs online'
            }
        
        bids = self.collect_bids(agvs, pickup_node_id, delivery_node_id, load_kg)
        
        if not bids:
            return {
                'winner_agv': None,
                'winner_details': None,
                'all_bids': [],
                'error': 'No reachable AGV'
            }
        
        winner_agv, winner_details = self.select_winner(bids)
        
        return {
            'winner_agv': winner_agv,
            'winner_details': winner_details,
            'all_bids': bids,
            'error': None if winner_agv else 'Failed to select winner'
        }
