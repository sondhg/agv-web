"""
BiddingEngine: Main facade for bidding system.
This is the main interface for other modules to use the bidding algorithm.
Internally, it uses a modular OOP architecture with separate components.
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
    Facade class for bidding system.
    
    Attributes:
        graph_engine (GraphEngine): Shared graph engine
        transport_calculator (TransportCalculator): Calculates transport metrics (energy, time)
        baseline_calculator (BaselineCalculator): Calculates baseline normalization
        bid_calculator (BidCalculator): Calculates bid scores
        auction_coordinator (AuctionCoordinator): Coordinates the auction
    """
    
    def __init__(self, graph_engine=None):
        """
        Initialize BiddingEngine with dependency injection.
        
        Args:
            graph_engine: GraphEngine instance (create new if None)
        """
        # Shared components
        self.graph_engine = graph_engine or GraphEngine()
        
        # Initialize modular components
        self.transport_calculator = TransportCalculator()
        self.baseline_calculator = BaselineCalculator(
            graph_engine=self.graph_engine,
            transport_calculator=self.transport_calculator
        )
        self.bid_calculator = BidCalculator(
            graph_engine=self.graph_engine,
            transport_calculator=self.transport_calculator,
            baseline_calculator=self.baseline_calculator
        )
        self.auction_coordinator = AuctionCoordinator(
            bid_calculator=self.bid_calculator
        )
        
        logger.info("BiddingEngine initialized with modular OOP architecture")
    
    # ==================== PRIMARY PUBLIC METHODS ====================
    
    def run_auction(self, pickup_node_id, delivery_node_id=None, load_kg=DEFAULT_LOAD_KG, epsilon=None):
        """
        Run auction and select the winning AGV (Main entry point).
        
        Args:
            pickup_node_id: Node to pick up the load (pickup)
            delivery_node_id: Node to deliver the load (delivery). If None, only go to pickup_node_id
            load_kg: Load weight (kg)
            epsilon: Override hybrid parameter (None = use default from constant.py)
            
        Returns:
            tuple: (winner_agv, error_message)
                - winner_agv: Winning AGV instance, or None if failed
                - error_message: None if successful, string if there is an error
        """
        return self.auction_coordinator.run_auction(pickup_node_id, delivery_node_id, load_kg, epsilon=epsilon)
    
    def run_auction_with_details(self, target_node_id, load_kg=DEFAULT_LOAD_KG):
        """
        Run auction and return detailed results.
        
        Args:
            target_node_id: Pickup/target node
            load_kg: Load weight
            
        Returns:
            dict: {
                'winner_agv': Winning AGV instance or None,
                'winner_details': dict,
                'all_bids': list of (score, agv, details),
                'error': string or None
            }
        """
        return self.auction_coordinator.run_auction_with_details(
            target_node_id, load_kg=load_kg
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
