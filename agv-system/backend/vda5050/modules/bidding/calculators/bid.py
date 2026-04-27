"""BidCalculator for AGV bidding.

Responsible for marginal-cost estimation, bid scoring, and constraints.
"""

import logging
from vda5050.models import AGVState, Order
from vda5050.graph_engine import GraphEngine
from vda5050.modules.reservation import ReservationService
from .transport import TransportCalculator
from .baseline import BaselineCalculator
from .greedy_bid import GreedyBidStrategy
from .ssi_marginal_bid import SsiMarginalBidStrategy
from ...constant import (
    DEFAULT_LOAD_KG,
    WAIT_CONFLICT_PENALTY,
    UNREACHABLE_ROUTE_PENALTY,
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
        self.reservation_service = ReservationService()
        self.greedy_strategy = GreedyBidStrategy(self)
        self.ssi_strategy = SsiMarginalBidStrategy(self)
        
        logger.debug("BidCalculator initialized")

    CHARGING_RELEASE_THRESHOLD = 80.0
    SOC_SAFE_THRESHOLD = 30.0
    SOC_CRITICAL_THRESHOLD = 10.0
    BATTERY_PENALTY_ALPHA = 0.05

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
        battery_state = last_state.battery_state or {}

        current_battery = battery_state.get('batteryCharge')
        if current_battery is None:
            current_battery = battery_state.get('charge', 0)

        is_charging = bool(battery_state.get('charging', False))
        
        logger.debug(f"AGV {agv.serial_number}: Node={current_node}, Battery={current_battery}%")
        
        return {
            'current_node': current_node,
            'battery': current_battery,
            'is_charging': is_charging,
            'is_valid': True
        }
    
    @classmethod
    def check_battery_constraint(cls, battery_percent, is_charging=False):
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
        # AGV at charging station stays locked for task allocation until >80%.
        if is_charging and battery_percent < cls.CHARGING_RELEASE_THRESHOLD:
            logger.info(
                f"AGV charging lock: {battery_percent}% < "
                f"{cls.CHARGING_RELEASE_THRESHOLD}% - REJECTED"
            )
            return {
                'is_acceptable': False,
                'penalty_factor': float('inf')
            }

        if battery_percent < cls.SOC_CRITICAL_THRESHOLD:
            # Below 10%: hard reject.
            logger.warning(f"Critical battery: {battery_percent}% - REJECTED")
            return {
                'is_acceptable': False,
                'penalty_factor': float('inf')
            }
        elif battery_percent <= cls.SOC_SAFE_THRESHOLD:
            # 10% - 30%: accepted with linear SoC-aware penalty.
            # penalty = 1 + alpha * (SoC_safe - SoC)
            penalty = 1.0 + cls.BATTERY_PENALTY_ALPHA * (
                cls.SOC_SAFE_THRESHOLD - battery_percent
            )
            logger.info(
                f"Low battery: {battery_percent}% - Penalty x{penalty:.3f} "
                f"(alpha={cls.BATTERY_PENALTY_ALPHA})"
            )
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

    def calculate_greedy_eta_bid(
        self,
        agv,
        pickup_node_id,
        delivery_node_id=None,
        load_kg=DEFAULT_LOAD_KG,
    ):
        """Baseline bid: greedy by projected completion time (ETA)."""
        return self.greedy_strategy.calculate_eta_bid(
            agv,
            pickup_node_id,
            delivery_node_id=delivery_node_id,
            load_kg=load_kg,
        )
    
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

                # Estimate remaining queue workload by following the pending order route
                # rather than a direct shortest-path shortcut to the final node.
                route_energy, route_time = self._estimate_order_route_metrics(
                    order=order,
                    from_node=chain_node,
                    load_kg=load_kg,
                )

                total_wait_time += route_time
                total_queue_energy += route_energy

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

    def _estimate_order_route_metrics(self, order, from_node, load_kg):
        """Estimate route metrics from current chain node through order nodes."""
        nodes = order.nodes or []
        if not nodes:
            return 0.0, 0.0

        node_ids = [node.get('nodeId') for node in nodes if node.get('nodeId')]
        if not node_ids:
            return 0.0, 0.0

        total_energy = 0.0
        total_time = 0.0

        # Align chain start with route start.
        if from_node != node_ids[0]:
            lead_distance, lead_turns = self.graph_engine.get_path_info(from_node, node_ids[0])
            if lead_distance != float('inf') and lead_distance > 0:
                lead_energy, lead_time = self.transport_calculator.calculate_metrics(
                    lead_distance,
                    load_kg,
                    lead_turns,
                )
                total_energy += lead_energy
                total_time += lead_time

        start_idx = 0
        if from_node in node_ids:
            start_idx = node_ids.index(from_node)

        for idx in range(start_idx, len(node_ids) - 1):
            start = node_ids[idx]
            end = node_ids[idx + 1]
            if start == end:
                continue

            distance, turns = self.graph_engine.get_path_info(start, end)
            if distance == float('inf') or distance <= 0:
                continue

            energy, travel_time = self.transport_calculator.calculate_metrics(
                distance,
                load_kg,
                turns,
            )
            total_energy += energy
            total_time += travel_time

        return total_energy, total_time
    
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

    def is_agv_locked_for_charging(self, agv):
        """Return True when the AGV must not receive new transport tasks."""
        try:
            return agv.is_charging_locked()
        except Exception as exc:
            logger.warning(f"AGV {agv.serial_number}: charging lock check failed: {exc}")
            return False

    def estimate_conflict_penalty(self, agv, start_node, pickup_node_id, delivery_node_id=None):
        """Estimate waiting/deadlock risk from active reservations for candidate route."""
        leg1_nodes, leg1_edges = self.graph_engine.get_path(start_node, pickup_node_id)
        if not leg1_nodes:
            return {
                "conflict_count": 999,
                "conflict_penalty": UNREACHABLE_ROUTE_PENALTY,
            }

        all_nodes = leg1_nodes
        all_edges = leg1_edges

        if delivery_node_id:
            leg2_nodes, leg2_edges = self.graph_engine.get_path(pickup_node_id, delivery_node_id)
            if not leg2_nodes:
                return {
                    "conflict_count": 999,
                    "conflict_penalty": UNREACHABLE_ROUTE_PENALTY,
                }
            all_nodes = leg1_nodes + leg2_nodes[1:]
            all_edges = leg1_edges + leg2_edges

        conflict_result = self.reservation_service.detect_conflicts(
            agv=agv,
            nodes=all_nodes,
            edges=all_edges,
        )
        conflict_count = len(conflict_result.node_conflicts) + len(conflict_result.edge_conflicts)
        return {
            "conflict_count": conflict_count,
            "conflict_penalty": conflict_count * WAIT_CONFLICT_PENALTY,
        }
    
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
        if self.is_agv_locked_for_charging(agv):
            logger.info(
                f"AGV {agv.serial_number}: Cannot bid (charging mission active or charging state)"
            )
            return None

        return self.ssi_strategy.calculate_full_bid(
            agv,
            pickup_node_id,
            delivery_node_id=delivery_node_id,
            load_kg=load_kg,
            epsilon=epsilon,
        )
