"""
Django management command to setup a large, realistic factory map.
Usage: python manage.py setup_test_graph
"""

import math
from django.core.management.base import BaseCommand
from vda5050.models import GraphNode, GraphEdge

class Command(BaseCommand):
    help = 'Setup a large, realistic factory map with diverse edge lengths and speeds'

    def handle(self, *args, **options):
        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*70}\n'
            f'📍 Setting up Large Realistic Factory Map (~60m x 85m)\n'
            f'{"="*70}\n'
        ))

        # Xóa dữ liệu cũ
        GraphNode.objects.all().delete()
        GraphEdge.objects.all().delete()
        
        # ĐỊNH NGHĨA CÁC ĐIỂM (Tọa độ tính bằng mét)
        nodes_data = [
            # 1. BÃI SẠC PIN (Depot / Charging Zone)
            {"node_id": "Charge_01", "x": 0, "y": 0, "type": GraphNode.NodeType.CHARGING},
            {"node_id": "Charge_02", "x": 0, "y": 8, "type": GraphNode.NodeType.CHARGING},
            {"node_id": "Depot_Gate", "x": 8, "y": 4, "type": GraphNode.NodeType.DEFAULT}, # Cổng bãi sạc

            # 2. HÀNH LANG CHÍNH (Main Hall - Dài và thoáng)
            {"node_id": "Main_S", "x": 8, "y": 25, "type": GraphNode.NodeType.DEFAULT}, # South
            {"node_id": "Main_C", "x": 8, "y": 55, "type": GraphNode.NodeType.DEFAULT}, # Center
            {"node_id": "Main_N", "x": 8, "y": 85, "type": GraphNode.NodeType.DEFAULT}, # North

            # 3. HÀNH LANG PHỤ (Aisles - Hẹp hơn)
            {"node_id": "Aisle_S", "x": 28, "y": 25, "type": GraphNode.NodeType.DEFAULT},
            {"node_id": "Aisle_C", "x": 28, "y": 55, "type": GraphNode.NodeType.DEFAULT},
            {"node_id": "Aisle_N", "x": 28, "y": 85, "type": GraphNode.NodeType.DEFAULT},

            # 4. KHU VỰC LẤY HÀNG (Warehouse - Pickup)
            {"node_id": "WH_Pick_1", "x": 45, "y": 25, "type": GraphNode.NodeType.PICKUP},
            {"node_id": "WH_Pick_2", "x": 45, "y": 55, "type": GraphNode.NodeType.PICKUP},
            {"node_id": "WH_Pick_3", "x": 45, "y": 85, "type": GraphNode.NodeType.PICKUP},

            # 5. KHU VỰC DÂY CHUYỀN SẢN XUẤT (Assembly Line - Delivery)
            {"node_id": "Assy_Drop_1", "x": -15, "y": 55, "type": GraphNode.NodeType.DELIVERY},
            {"node_id": "Assy_Drop_2", "x": -15, "y": 85, "type": GraphNode.NodeType.DELIVERY},
        ]
        
        # TẠO NODE TRONG DATABASE
        created_nodes = {}
        for node_data in nodes_data:
            node = GraphNode.objects.create(
                node_id=node_data["node_id"],
                x=node_data["x"],
                y=node_data["y"],
                theta=0,
                node_type=node_data["type"],
                map_id="map_1",
                description=f"[{node_data['type']}] Node at ({node_data['x']}, {node_data['y']})"
            )
            created_nodes[node_data["node_id"]] = node
            
            # In màu cho đẹp
            type_str = f"[{node_data['type']}]"
            if node_data["type"] == 'CHARGING':
                styled_type = self.style.WARNING(type_str)
            elif node_data["type"] in ['PICKUP', 'DELIVERY']:
                styled_type = self.style.SUCCESS(type_str)
            else:
                styled_type = type_str
            
            self.stdout.write(f'  ✅ Created: {styled_type.ljust(20)} {node_data["node_id"].ljust(15)} at ({node_data["x"]:>3}, {node_data["y"]:>3})')
        
        # ĐỊNH NGHĨA KẾT NỐI VÀ TỐC ĐỘ GIỚI HẠN (Node_A, Node_B, Max_Velocity)
        edges_list = [
            # Đi từ Trạm sạc ra Cổng (Tốc độ chậm: 1.0 m/s)
            ("Charge_01", "Depot_Gate", 1.0),
            ("Charge_02", "Depot_Gate", 1.0),
            
            # Nối Cổng bãi sạc với Hành lang chính (Tốc độ TB: 1.5 m/s)
            ("Depot_Gate", "Main_S", 1.5),

            # Dọc Hành lang chính (Khoảng cách cực dài, chạy max tốc: 2.0 m/s)
            ("Main_S", "Main_C", 2.0),
            ("Main_C", "Main_N", 2.0),

            # Dọc Hành lang phụ (Chạy chậm hơn hành lang chính: 1.5 m/s)
            ("Aisle_S", "Aisle_C", 1.5),
            ("Aisle_C", "Aisle_N", 1.5),

            # Đường cắt ngang nối Hành lang chính và phụ (1.5 m/s)
            ("Main_S", "Aisle_S", 1.5),
            ("Main_C", "Aisle_C", 1.5),
            ("Main_N", "Aisle_N", 1.5),

            # Rẽ từ Hành lang phụ vào Kho bốc hàng (Vào kho chạy chậm: 1.0 m/s)
            ("Aisle_S", "WH_Pick_1", 1.0),
            ("Aisle_C", "WH_Pick_2", 1.0),
            ("Aisle_N", "WH_Pick_3", 1.0),

            # Rẽ từ Hành lang chính vào Dây chuyền trả hàng (Chạy chậm: 1.0 m/s)
            ("Main_C", "Assy_Drop_1", 1.0),
            ("Main_N", "Assy_Drop_2", 1.0),
        ]
        
        # TẠO EDGE HAI CHIỀU (BIDIRECTIONAL) TỰ TÍNH KHOẢNG CÁCH
        edge_count = 0
        self.stdout.write('\n  Tính toán và tạo đường đi (Edges)...')
        for start_id, end_id, max_v in edges_list:
            node_start = created_nodes[start_id]
            node_end = created_nodes[end_id]
            
            # TỰ ĐỘNG Tính khoảng cách chim bay (Euclid) làm độ dài đường đi
            dist = math.hypot(node_end.x - node_start.x, node_end.y - node_start.y)
            dist = round(dist, 2)

            # Tạo chiều đi (Start -> End)
            GraphEdge.objects.create(
                start_node=node_start, end_node=node_end, map_id="map_1",
                length=dist, max_velocity=max_v, is_directed=True
            )
            # Tạo chiều về (End -> Start)
            GraphEdge.objects.create(
                start_node=node_end, end_node=node_start, map_id="map_1",
                length=dist, max_velocity=max_v, is_directed=True
            )
            edge_count += 2
            # self.stdout.write(f'     Nối {start_id} <-> {end_id}: Dài {dist}m, max speed {max_v}m/s')
        
        self.stdout.write(self.style.SUCCESS(f'  ✅ Created {edge_count} directed edges successfully.'))
        
        # IN SƠ ĐỒ TRỰC QUAN RA MÀN HÌNH
        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*70}\n'
            f'✅ Large Map Setup Complete!\n'
            f'{"="*70}\n'
        ))
        
        self.stdout.write('📊 Factory Map Topology:\n')
        self.stdout.write(f'  {self.style.SUCCESS("[Assy_Drop_2]")} ---- [Main_N] ====== [Aisle_N] ---- {self.style.SUCCESS("[WH_Pick_3]")}')
        self.stdout.write('                     ||              ||')
        self.stdout.write(f'  {self.style.SUCCESS("[Assy_Drop_1]")} ---- [Main_C] ====== [Aisle_C] ---- {self.style.SUCCESS("[WH_Pick_2]")}')
        self.stdout.write('                     ||              ||')
        self.stdout.write(f'                  [Main_S] ====== [Aisle_S] ---- {self.style.SUCCESS("[WH_Pick_1]")}')
        self.stdout.write('                     ||')
        self.stdout.write('                [Depot_Gate]')
        self.stdout.write('                 /        \\')
        self.stdout.write(f'      {self.style.WARNING("[Charge_01]")}        {self.style.WARNING("[Charge_02]")}\n')
        
        self.stdout.write(f'📈 Map Stats: {GraphNode.objects.count()} Nodes, {GraphEdge.objects.count()} Edges.')
        self.stdout.write('   * [===] = High Speed (2.0 m/s)  |  [---] = Normal/Low Speed (1.0 - 1.5 m/s)')
        self.stdout.write(self.style.SUCCESS('\n🚀 Sẵn sàng để test thuật toán Energy-Aware trên môi trường thực tế!\n'))