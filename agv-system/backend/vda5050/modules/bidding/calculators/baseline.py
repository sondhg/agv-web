"""
BaselineCalculator: Tính toán chi phí baseline (lý tưởng) để chuẩn hóa giá thầu.
Chịu trách nhiệm tính toán baseline normalization factors.
"""

import logging
from vda5050.graph_engine import GraphEngine
from .transport import TransportCalculator
from ...constant import (
    DEFAULT_LOAD_KG,
    FALLBACK_NORM_ENERGY_KJ, 
    FALLBACK_NORM_TFT_SEC
)

logger = logging.getLogger(__name__)


class BaselineCalculator:
    """
    Class tính toán baseline (chi phí lý tưởng) cho việc chuẩn hóa.
    
    Baseline được dùng để normalize các giá trị energy và time,
    giúp so sánh công bằng giữa các AGV ở vị trí khác nhau.
    
    Attributes:
        graph_engine (GraphEngine): Engine để tính đường đi
        transport_calculator (TransportCalculator): Calculator cho metrics vật lý
    """
    
    def __init__(self, graph_engine=None, transport_calculator=None):
        """
        Khởi tạo calculator với dependencies.
        
        Args:
            graph_engine: GraphEngine instance (tạo mới nếu None)
            transport_calculator: TransportCalculator instance (tạo mới nếu None)
        """
        self.graph_engine = graph_engine or GraphEngine()
        self.transport_calculator = transport_calculator or TransportCalculator()
        
        logger.debug("BaselineCalculator initialized")
    
    def calculate_baseline_distance(self, start_node_id, target_node_id):
        """
        Tính khoảng cách baseline và số lượt rẽ.
        
        Returns:
            tuple: (distance_m, num_turns)
        """
        distance, num_turns = self.graph_engine.get_path_info(start_node_id, target_node_id)
        
        if distance == float('inf'):
            logger.warning(f"No path from {start_node_id} to {target_node_id}")
        else:
            logger.debug(f"Baseline {start_node_id}→{target_node_id}: {distance:.2f}m, {num_turns} turns")
        
        return distance, num_turns
    
    def calculate_baseline_metrics(self, start_node_id, target_node_id, load_kg=DEFAULT_LOAD_KG):
        """
        Tính toán energy và time baseline cho một đoạn đường.
        
        Args:
            start_node_id: Node xuất phát
            target_node_id: Node đích
            load_kg: Tải trọng (kg)
            
        Returns:
            tuple: (baseline_energy_kj, baseline_time_s)
        """
        distance, num_turns = self.calculate_baseline_distance(start_node_id, target_node_id)
        
        if distance == float('inf'):
            logger.warning(f"Using fallback baseline values for {start_node_id}→{target_node_id}")
            return FALLBACK_NORM_ENERGY_KJ, FALLBACK_NORM_TFT_SEC
        
        energy_kj, time_s = self.transport_calculator.calculate_metrics(distance, load_kg, num_turns)
        
        validated_energy, validated_time = self.transport_calculator.validate_metrics(energy_kj, time_s)
        
        logger.debug(f"Baseline metrics {start_node_id}→{target_node_id}: "
                    f"E={validated_energy:.2f}kJ, T={validated_time:.2f}s")
        
        return validated_energy, validated_time
    
    def normalize_metrics(self, actual_energy_kj, actual_time_s, 
                         baseline_energy_kj, baseline_time_s):
        """
        Chuẩn hóa metrics thực tế so với baseline.
        
        Args:
            actual_energy_kj: Năng lượng thực tế
            actual_time_s: Thời gian thực tế
            baseline_energy_kj: Năng lượng baseline
            baseline_time_s: Thời gian baseline
            
        Returns:
            tuple: (normalized_energy, normalized_time)
        """
        # Tránh chia cho 0
        safe_baseline_energy = baseline_energy_kj if baseline_energy_kj > 0 else FALLBACK_NORM_ENERGY_KJ
        safe_baseline_time = baseline_time_s if baseline_time_s > 0 else FALLBACK_NORM_TFT_SEC
        
        norm_energy = actual_energy_kj / safe_baseline_energy
        norm_time = actual_time_s / safe_baseline_time
        
        logger.debug(f"Normalized metrics: E_norm={norm_energy:.4f}, T_norm={norm_time:.4f}")
        
        return norm_energy, norm_time
    
    def calculate_and_normalize(self, start_node_id, target_node_id, 
                               actual_distance_m, load_kg=DEFAULT_LOAD_KG):
        """
        Tính toán và chuẩn hóa metrics trong một bước.
        
        Args:
            start_node_id: Node xuất phát
            target_node_id: Node đích
            actual_distance_m: Khoảng cách thực tế AGV phải đi
            load_kg: Tải trọng
            
        Returns:
            dict: {
                'actual_energy_kj': float,
                'actual_time_s': float,
                'baseline_energy_kj': float,
                'baseline_time_s': float,
                'norm_energy': float,
                'norm_time': float
            }
        """
        # Tính metrics thực tế (num_turns=0 vì actual_distance_m là tổng đã tính sẵn)
        actual_energy, actual_time = self.transport_calculator.calculate_metrics(
            actual_distance_m, load_kg, num_turns=0
        )
        
        # Tính baseline
        baseline_energy, baseline_time = self.calculate_baseline_metrics(
            start_node_id, target_node_id, load_kg
        )
        
        # Chuẩn hóa
        norm_energy, norm_time = self.normalize_metrics(
            actual_energy, actual_time,
            baseline_energy, baseline_time
        )
        
        result = {
            'actual_energy_kj': actual_energy,
            'actual_time_s': actual_time,
            'baseline_energy_kj': baseline_energy,
            'baseline_time_s': baseline_time,
            'norm_energy': norm_energy,
            'norm_time': norm_time
        }
        
        logger.debug(f"Full baseline calculation result: {result}")
        
        return result
