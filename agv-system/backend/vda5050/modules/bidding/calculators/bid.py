"""BidCalculator for AGV bidding.

Responsible for marginal-cost estimation, bid scoring, and constraints.
"""

import logging
from vda5050.models import AGVState, Order
from vda5050.graph_engine import GraphEngine
from .transport import TransportCalculator
from .baseline import BaselineCalculator
from .greedy_bid import GreedyBidStrategy
from .ssi_marginal_bid import SsiMarginalBidStrategy
from ...constant import (
    DEFAULT_LOAD_KG
)

logger = logging.getLogger(__name__)


class BidCalculator:
    """
    Bid calculation class for AGVs.

    Applied logic:
    - Marginal Cost: Cost added by the new task only
    - Baseline Normalization: Normalize against ideal baseline cost
    - Hybrid Objective: Combine MiniSum (efficiency) and MiniMax (load balancing)
    - Battery Constraints: Eligibility and battery-based penalty
    
    Attributes:
        graph_engine (GraphEngine): Engine for path computation
        transport_calculator (TransportCalculator): Calculator for physical metrics
        baseline_calculator (BaselineCalculator): Calculator for baseline normalization
    """
    
    def __init__(self, graph_engine=None, transport_calculator=None, baseline_calculator=None):
        """
        Initialize calculator with dependencies.
        
        Args:
            graph_engine: GraphEngine instance
            transport_calculator: TransportCalculator instance
            baseline_calculator: BaselineCalculator instance
        """
        self.graph_engine = graph_engine or GraphEngine()
        self.transport_calculator = transport_calculator or TransportCalculator()
        self.baseline_calculator = baseline_calculator or BaselineCalculator(
            self.graph_engine, 
            self.transport_calculator
        )
        self.greedy_strategy = GreedyBidStrategy(self)
        self.ssi_strategy = SsiMarginalBidStrategy(self)
        
        logger.debug("BidCalculator initialized")

    @staticmethod
    def _build_greedy_invalid_result(battery, start_node):
        """Build a standardized invalid result for greedy-distance bidding."""
        return {
            'bid_final': float('inf'),
            'distance_to_pickup_m': float('inf'),
            'battery': battery,
            'start_node': start_node,
            'is_valid': False,
        }

    def get_agv_current_state(self, agv):
        """
        Get the AGV's latest runtime state.
        
        Args:
            agv: AGV instance
            
        Returns:
            dict: {
                'current_node': str,
                'battery': float,
                'is_valid': bool
            } or None if no state exists
        """
        last_state = AGVState.objects.filter(agv=agv).order_by('-timestamp').first()
        
        if not last_state:
            logger.warning(f"AGV {agv.serial_number}: No state data available")
            return None
        
        current_node = last_state.last_node_id
        current_battery = last_state.battery_state.get('batteryCharge', 0)
        
        logger.debug(f"AGV {agv.serial_number}: Node={current_node}, Battery={current_battery}%")
        
        return {
            'current_node': current_node,
            'battery': current_battery,
            'is_valid': True
        }
    
    @staticmethod
    def check_battery_constraint(battery_percent):
        """
        Check battery constraints.
        
        Args:
            battery_percent: Current battery percentage
            
        Returns:
            dict: {
                'is_acceptable': bool,  # Whether the AGV can participate
                'penalty_factor': float # Penalty multiplier (1.0 = none, >1.0 = penalized)
            }
        """
        if battery_percent < 10.0:
            # Below 10%: hard reject.
            logger.warning(f"Critical battery: {battery_percent}% - REJECTED")
            return {
                'is_acceptable': False,
                'penalty_factor': float('inf')
            }
        elif battery_percent < 30.0:
            # Below 30%: accepted with strong penalty.
            penalty = 1.5
            logger.info(f"Low battery: {battery_percent}% - Penalty x{penalty}")
            return {
                'is_acceptable': True,
                'penalty_factor': penalty
            }
        else:
            # Healthy battery: no penalty.
            return {
                'is_acceptable': True,
                'penalty_factor': 1.0
            }

    def calculate_greedy_distance_bid(self, agv, pickup_node_id):
        """
        Baseline bid: greedy nearest-neighbor by distance to pickup.

        Rules:
        - Only use distance from projected AGV start to pickup
        - Exclude pickup->delivery leg from scoring
        - Ignore battery penalty except hard rejection when battery < 10%

        Args:
            agv: AGV instance
            pickup_node_id: Pickup node

        Returns:
            dict | None: {
                'bid_final': float,
                'distance_to_pickup_m': float,
                'battery': float,
                'start_node': str,
                'is_valid': bool,
            }
        """
        return self.greedy_strategy.calculate_bid(agv, pickup_node_id)
    
    def calculate_wait_cost(self, agv, current_node, load_kg):
        """
        Estimate queue cost from all pending orders (SENT/ACTIVE/QUEUED).

        Chains orders by creation order to estimate:
        - Total wait time before the AGV can take a new task
        - Total queue energy for pending orders
        - End node after finishing all pending work

        Returns:
            dict: {
                'start_node': str,
                'wait_time_s': float,
                'queue_energy_kj': float,
                'num_pending': int,
            }
        """
        pending_orders = Order.objects.filter(
            agv=agv,
            status__in=['SENT', 'ACTIVE', 'QUEUED']
        ).order_by('created_at')

        if not pending_orders.exists():
            return {
                'start_node': current_node,
                'wait_time_s': 0.0,
                'queue_energy_kj': 0.0,
                'num_pending': 0,
            }

        pending_count = pending_orders.count()

        chain_node = current_node
        total_wait_time = 0.0
        total_queue_energy = 0.0

        for order in pending_orders:
            try:
                if not order.nodes:
                    continue

                end_node = order.nodes[-1]['nodeId']

                if chain_node == end_node:
                    continue

                distance, turns = self.graph_engine.get_path_info(chain_node, end_node)

                if distance != float('inf') and distance > 0:
                    energy, travel_time = self.transport_calculator.calculate_metrics(
                        distance, load_kg, turns
                    )
                    total_wait_time += travel_time
                    total_queue_energy += energy

                chain_node = end_node

            except Exception as e:
                logger.error(f"Error calculating queue cost for {agv.serial_number}: {e}")
                continue

        logger.debug(
            f"AGV {agv.serial_number} queue: {pending_count} pending, "
            f"wait={total_wait_time:.1f}s, energy={total_queue_energy:.2f}kJ, "
            f"will end at {chain_node}"
        )

        return {
            'start_node': chain_node,
            'wait_time_s': total_wait_time,
            'queue_energy_kj': total_queue_energy,
            'num_pending': pending_count,
        }
    
    def calculate_marginal_cost(self, agv, pickup_node_id, delivery_node_id=None, load_kg=DEFAULT_LOAD_KG):
        """
        Calculate marginal cost for one AGV.
        
        Args:
            agv: AGV instance
            pickup_node_id: Pickup node
            delivery_node_id: Delivery node (if None, only travel to pickup)
            load_kg: Payload weight (kg)
            
        Returns:
            dict: {
                'energy_marginal': float,
                'time_marginal': float,
                'norm_energy': float,
                'norm_time': float,
                'is_valid': bool
            } or None if bidding is not possible
        """
        return self.ssi_strategy.calculate_marginal_cost(
            agv, pickup_node_id, delivery_node_id=delivery_node_id, load_kg=load_kg
        )
    
    def calculate_bid_score(self, marginal_cost_result, epsilon=None):
        """
        Compute bid score from marginal cost (Hybrid Objective / SSI-DMAS).

        - MiniSum: marginal cost of the new task (pure efficiency)
        - MiniMax: accumulated load (queued + new task, fairness)
        - Hybrid:  ε × MiniSum + (1−ε) × MiniMax

        Args:
            marginal_cost_result: dict from calculate_marginal_cost
            epsilon: Override hybrid parameter (None = use default from constant.py)

        Returns:
            float: Bid score (lower is better)
        """
        return self.ssi_strategy.calculate_bid_score(marginal_cost_result, epsilon=epsilon)
    
    def calculate_full_bid(self, agv, pickup_node_id, delivery_node_id=None, load_kg=DEFAULT_LOAD_KG, epsilon=None):
        """
        Calculate the full bid for one AGV (all-in-one).
        
        Args:
            agv: AGV instance
            pickup_node_id: Pickup node
            delivery_node_id: Delivery node (if None, only travel to pickup)
            load_kg: Payload weight (kg)
            epsilon: Override hybrid parameter (None = use default)
            
        Returns:
            dict: {
                'bid_final': float,
                'energy_marginal': float,
                'time_marginal': float,
                'battery': float,
                'details': dict
            } or None if bidding is not possible
        """
        return self.ssi_strategy.calculate_full_bid(
            agv,
            pickup_node_id,
            delivery_node_id=delivery_node_id,
            load_kg=load_kg,
            epsilon=epsilon,
        )
