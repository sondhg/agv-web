"""
BidCalculator: Tính toán giá thầu (bid) cho AGV.
Chịu trách nhiệm tính marginal cost, scoring và các ràng buộc.
"""

import logging
from vda5050.models import AGVState, Order
from vda5050.graph_engine import GraphEngine
from .transport import TransportCalculator
from .baseline import BaselineCalculator
from ...constant import (
    DEFAULT_LOAD_KG,
    K_ENERGY, K_TIME, EPSILON
)

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
    
    def __init__(self, graph_engine=None, transport_calculator=None, baseline_calculator=None):
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
            self.graph_engine, 
            self.transport_calculator
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
            return {
                'is_acceptable': False,
                'penalty_factor': float('inf')
            }
        elif battery_percent < 30.0:
            # Pin dưới 30%: Chấp nhận nhưng phạt nặng
            penalty = 1.5
            logger.info(f"Low battery: {battery_percent}% - Penalty x{penalty}")
            return {
                'is_acceptable': True,
                'penalty_factor': penalty
            }
        else:
            # Pin đủ: Không phạt
            return {
                'is_acceptable': True,
                'penalty_factor': 1.0
            }

    def calculate_greedy_distance_bid(self, agv, pickup_node_id):
        """
        Baseline bid: Greedy Nearest Neighbor theo khoảng cách đến pickup.

        Rules:
        - Chỉ xét distance từ vị trí dự kiến của AGV tới pickup
        - Không cộng pickup->delivery
        - Bỏ qua penalty trừ khi pin < 10% thì loại AGV

        Args:
            agv: AGV instance
            pickup_node_id: Node lấy hàng

        Returns:
            dict | None: {
                'bid_final': float,
                'distance_to_pickup_m': float,
                'battery': float,
                'start_node': str,
                'is_valid': bool,
            }
        """
        state = self.get_agv_current_state(agv)
        if not state or not state['is_valid']:
            return None

        battery = state['battery']
        if battery < 10.0:
            logger.info(f"AGV {agv.serial_number}: Greedy reject (battery={battery}%)")
            return {
                'bid_final': float('inf'),
                'distance_to_pickup_m': float('inf'),
                'battery': battery,
                'start_node': state['current_node'],
                'is_valid': False,
            }

        # Use projected node after pending queue as the nearest-neighbor start point.
        wait_info = self.calculate_wait_cost(agv, state['current_node'], DEFAULT_LOAD_KG)
        start_node = wait_info.get('start_node', state['current_node'])

        try:
            distance = self.graph_engine.get_path_cost(start_node, pickup_node_id)
        except Exception as e:
            logger.error(f"Greedy distance error for {agv.serial_number}: {e}")
            return None

        if distance == float('inf'):
            return {
                'bid_final': float('inf'),
                'distance_to_pickup_m': float('inf'),
                'battery': battery,
                'start_node': start_node,
                'is_valid': False,
            }

        return {
            'bid_final': distance,
            'distance_to_pickup_m': distance,
            'battery': battery,
            'start_node': start_node,
            'is_valid': True,
        }
    
    def calculate_wait_cost(self, agv, current_node, load_kg):
        """
        Tính chi phí chờ tích lũy cho TẤT CẢ order đang pending (SENT/ACTIVE/QUEUED).

        Chain qua từng order theo thứ tự tạo để ước lượng:
        - Tổng thời gian AGV phải hoàn thành trước khi nhận task mới
        - Tổng năng lượng dự kiến cho các order đang chờ
        - Node cuối cùng AGV sẽ ở sau khi hoàn thành tất cả

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
            f"AGV {agv.serial_number} queue: {pending_orders.count()} pending, "
            f"wait={total_wait_time:.1f}s, energy={total_queue_energy:.2f}kJ, "
            f"will end at {chain_node}"
        )

        return {
            'start_node': chain_node,
            'wait_time_s': total_wait_time,
            'queue_energy_kj': total_queue_energy,
            'num_pending': pending_orders.count(),
        }
    
    def calculate_marginal_cost(self, agv, pickup_node_id, delivery_node_id=None, load_kg=DEFAULT_LOAD_KG):
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
        if not state or not state['is_valid']:
            return None
        
        current_node = state['current_node']
        battery = state['battery']
        
        # Bước 2: Kiểm tra ràng buộc pin
        battery_check = self.check_battery_constraint(battery)
        if not battery_check['is_acceptable']:
            return None
        
        # Bước 3: Tính wait cost (nếu AGV đang bận)
        wait_info = self.calculate_wait_cost(agv, current_node, load_kg)
        start_node = wait_info['start_node']
        wait_time = wait_info['wait_time_s']
        queue_energy = wait_info.get('queue_energy_kj', 0.0)
        num_pending = wait_info.get('num_pending', 0)
        
        # Bước 4: Tính chi phí cho từng chặng
        if delivery_node_id:
            # 2-leg trip: current -> pickup -> delivery
            # Leg 1: current -> pickup (không mang hàng)
            distance_leg1, turns_leg1 = self.graph_engine.get_path_info(start_node, pickup_node_id)
            if distance_leg1 == float('inf'):
                logger.warning(f"AGV {agv.serial_number}: No path {start_node}→{pickup_node_id}")
                return None
            
            energy_leg1, time_leg1 = self.transport_calculator.calculate_metrics(
                distance_leg1, 0, turns_leg1  # Không mang hàng
            )
            
            # Leg 2: pickup -> delivery (mang hàng)
            distance_leg2, turns_leg2 = self.graph_engine.get_path_info(pickup_node_id, delivery_node_id)
            if distance_leg2 == float('inf'):
                logger.warning(f"AGV {agv.serial_number}: No path {pickup_node_id}→{delivery_node_id}")
                return None
            
            energy_leg2, time_leg2 = self.transport_calculator.calculate_metrics(
                distance_leg2, load_kg, turns_leg2  # Mang hàng
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
            actual_distance, actual_turns = self.graph_engine.get_path_info(start_node, pickup_node_id)
            
            if actual_distance == float('inf'):
                logger.warning(f"AGV {agv.serial_number}: No path {start_node}→{pickup_node_id}")
                return None
            
            # Tính metrics thực tế
            energy_travel, time_travel = self.transport_calculator.calculate_metrics(
                actual_distance, load_kg, actual_turns
            )
            
            # Marginal time = wait time + travel time
            time_marginal = wait_time + time_travel
            energy_marginal = energy_travel  # Energy chỉ tính phần di chuyển
            
            # Bước 5: Chuẩn hóa với baseline
            baseline_result = self.baseline_calculator.calculate_and_normalize(
                start_node, pickup_node_id, actual_distance, load_kg
            )
        
        return {
            'energy_marginal': energy_marginal,
            'time_marginal': time_marginal,
            'norm_energy': baseline_result['norm_energy'],
            'norm_time': baseline_result['norm_time'],
            'battery': battery,
            'battery_penalty': battery_check['penalty_factor'],
            'queue_time_s': wait_time,
            'queue_energy_kj': queue_energy,
            'num_pending': num_pending,
            'is_valid': True
        }
    
    def calculate_bid_score(self, marginal_cost_result, epsilon=None):
        """
        Tính điểm bid từ marginal cost (Hybrid Objective / SSI-DMAS).

        - MiniSum: chi phí biên của task mới (xe nào rẻ nhất)
        - MiniMax: tổng tải tích lũy (queued + task mới, xe nào ít việc nhất)
        - Hybrid:  ε × MiniSum + (1−ε) × MiniMax

        Args:
            marginal_cost_result: dict from calculate_marginal_cost
            epsilon: Override hybrid parameter (None = use default from constant.py)

        Returns:
            float: Điểm bid (càng thấp càng tốt)
        """
        if not marginal_cost_result or not marginal_cost_result.get('is_valid'):
            return float('inf')

        norm_energy = marginal_cost_result['norm_energy']
        norm_time = marginal_cost_result['norm_time']
        battery_penalty = marginal_cost_result.get('battery_penalty', 1.0)
        queue_time = marginal_cost_result.get('queue_time_s', 0.0)
        queue_energy = marginal_cost_result.get('queue_energy_kj', 0.0)
        time_marginal = marginal_cost_result.get('time_marginal', 0.0)
        energy_marginal = marginal_cost_result.get('energy_marginal', 0.0)

        # Resolve epsilon: per-request override > constant.py default
        eps = epsilon if epsilon is not None else EPSILON

        # MiniSum: chi phí biên (chỉ task mới, normalized)
        bid_minisum = (K_ENERGY * norm_energy) + (K_TIME * norm_time)

        # MiniMax: tổng tải dự kiến (queued + task mới)
        # Tách travel_time thuần (không bao gồm queue wait) để tính baseline chính xác
        travel_time = time_marginal - queue_time  # pure travel time for new task

        # Normalize queue_time theo cùng thang đo với norm_time
        if travel_time > 0 and norm_time > 0:
            baseline_time_unit = travel_time / norm_time
            norm_queue_time = queue_time / baseline_time_unit
        else:
            norm_queue_time = 0.0

        # Normalize queue_energy theo cùng thang đo với norm_energy
        if energy_marginal > 0 and norm_energy > 0:
            baseline_energy_unit = energy_marginal / norm_energy
            norm_queue_energy = queue_energy / baseline_energy_unit
        else:
            norm_queue_energy = 0.0

        bid_minimax = (
            K_ENERGY * (norm_energy + norm_queue_energy)
            + K_TIME * (norm_time + norm_queue_time)
        )

        # Hybrid: kết hợp cả hai
        bid_final = (eps * bid_minisum) + ((1 - eps) * bid_minimax)

        # Áp dụng penalty từ pin
        bid_final *= battery_penalty

        logger.info(
            f"Bid score: MiniSum={bid_minisum:.4f}, MiniMax={bid_minimax:.4f}, "
            f"Hybrid={bid_final:.4f} (ε={eps}, penalty={battery_penalty}, "
            f"queue_time={queue_time:.1f}s, norm_qT={norm_queue_time:.2f}, "
            f"norm_qE={norm_queue_energy:.2f})"
        )

        return bid_final
    
    def calculate_full_bid(self, agv, pickup_node_id, delivery_node_id=None, load_kg=DEFAULT_LOAD_KG, epsilon=None):
        """
        Tính toán bid đầy đủ cho một AGV (all-in-one).
        
        Args:
            agv: AGV instance
            pickup_node_id: Node lấy hàng
            delivery_node_id: Node giao hàng (nếu None, chỉ đi đến pickup)
            load_kg: Tải trọng
            epsilon: Override hybrid parameter (None = use default)
            
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
        marginal_result = self.calculate_marginal_cost(agv, pickup_node_id, delivery_node_id, load_kg)
        
        if not marginal_result:
            logger.info(f"AGV {agv.serial_number}: Cannot bid (no valid marginal cost)")
            return None
        
        # Tính bid score
        bid_score = self.calculate_bid_score(marginal_result, epsilon=epsilon)
        
        if bid_score == float('inf'):
            logger.info(f"AGV {agv.serial_number}: Cannot bid (infinite score)")
            return None
        
        result = {
            'bid_final': bid_score,
            'energy_marginal': marginal_result['energy_marginal'],
            'time_marginal': marginal_result['time_marginal'],
            'battery': marginal_result['battery'],
            'details': marginal_result
        }
        
        logger.info(f"AGV {agv.serial_number}: Bid={bid_score:.4f} "
                   f"(E={marginal_result['energy_marginal']:.2f}kJ, "
                   f"T={marginal_result['time_marginal']:.2f}s, "
                   f"Bat={marginal_result['battery']}%)")
        
        return result
