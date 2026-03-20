import uuid
from django.utils import timezone
from vda5050.models import AGV, AGVState, Order
from vda5050.graph_engine import GraphEngine


class Scheduler:
    def __init__(self):
        self.graph_engine = GraphEngine()

    def create_transport_order(self, serial_number, pickup_node_id, delivery_node_id):
        """
        Create transport order for AGV: current -> pickup -> delivery.

        Args:
            serial_number: AGV serial number
            pickup_node_id: Node to pick up the load
            delivery_node_id: Node to deliver the load
        """
        # 1. Get AGV info and current position
        try:
            agv = AGV.objects.get(serial_number=serial_number)
            # Get the latest state to know where the AGV is
            last_state = AGVState.objects.filter(agv=agv).order_by("-timestamp").first()

            if not last_state:
                return {"success": False, "error": "AGV has no position data (State)"}

            start_node_id = last_state.last_node_id

        except AGV.DoesNotExist:
            return {"success": False, "error": "AGV does not exist"}

        # 2. Xác định điểm xuất phát (Start Node)
        # Tìm xem có lệnh nào đang chạy hoặc đang chờ không?
        last_active_order = (
            Order.objects.filter(agv=agv, status__in=["SENT", "ACTIVE", "QUEUED"])
            .order_by("-created_at")
            .first()
        )

        if last_active_order:
            # --- LOGIC MỚI: NỐI ĐUÔI ---
            # Nếu xe đang bận, điểm xuất phát là điểm cuối của lệnh trước đó
            try:
                start_node_id = last_active_order.nodes[-1]["nodeId"]
                initial_status = "QUEUED"
                print(
                    f"Chaining order: Start from {start_node_id} (End of Order {last_active_order.order_id})"
                )
            except (IndexError, KeyError, TypeError):
                # Fallback nếu dữ liệu lệnh cũ bị lỗi
                return {
                    "success": False,
                    "error": "Lỗi dữ liệu Nodes của lệnh trước đó",
                }
        else:
            # Nếu xe rảnh, lấy vị trí hiện tại từ State
            last_state = AGVState.objects.filter(agv=agv).order_by("-timestamp").first()
            if not last_state:
                return {"success": False, "error": "AGV chưa có dữ liệu vị trí (State)"}

            start_node_id = last_state.last_node_id
            initial_status = "CREATED"  # Sẽ được gửi đi ngay

        # 3. Calculate path with 2 legs: current -> pickup -> delivery
        # Leg 1: current position -> pickup node
        nodes_leg1, edges_leg1 = self.graph_engine.get_path(
            start_node_id, pickup_node_id
        )
        if not nodes_leg1:
            return {
                "success": False,
                "error": f"Path not found from {start_node_id} to {pickup_node_id}",
            }

        # Leg 2: pickup node -> delivery node
        nodes_leg2, edges_leg2 = self.graph_engine.get_path(
            pickup_node_id, delivery_node_id
        )
        if not nodes_leg2:
            return {
                "success": False,
                "error": f"Path not found from {pickup_node_id} to {delivery_node_id}",
            }

        # Merge paths (remove duplicate pickup node)
        all_nodes = nodes_leg1 + nodes_leg2[1:]  # Skip first node of leg2 (duplicate)
        all_edges = edges_leg1 + edges_leg2

        # 4. Create new Order in Database
        # (Signal post_save will automatically send MQTT)
        new_order_id = f"ORD_{uuid.uuid4().hex[:8].upper()}"

        order = Order.objects.create(
            header_id=0,
            timestamp=timezone.now(),
            order_id=new_order_id,
            order_update_id=0,
            zone_set_id="zone_1",
            agv=agv,
            status=initial_status,
            nodes=all_nodes,  # Combined path: current -> pickup -> delivery
            edges=all_edges,  # Combined edges
        )

        msg = (
            "Order sent to AGV"
            if initial_status == "CREATED"
            else f"Order added to Queue (Start from {start_node_id})"
        )

        return {
            "success": True,
            "order_id": new_order_id,
            "status": initial_status,
            "message": msg,
            "pickup_node": pickup_node_id,
            "delivery_node": delivery_node_id,
            "path": [n["nodeId"] for n in all_nodes],
        }
