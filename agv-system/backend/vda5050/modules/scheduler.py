import uuid
import time
from django.utils import timezone
from vda5050.models import AGV, AGVState, Order
from vda5050.graph_engine import GraphEngine
from vda5050.modules.reservation import ReservationService
from vda5050.modules.constant import DEFAULT_LOAD_KG


class Scheduler:
    def __init__(self):
        self.graph_engine = GraphEngine()
        self.reservation_service = ReservationService()

    @staticmethod
    def _append_action(
        node: dict, action_type: str, weight: float | None = None
    ) -> None:
        action = {
            "actionType": action_type,
            "actionId": f"{action_type}_{int(time.time())}",
            "blockingType": "HARD",
            "actionParameters": [],
        }
        if weight is not None:
            action["weight"] = weight
            action["actionParameters"].append({"key": "weight", "value": weight})
        node.setdefault("actions", []).append(action)

    @staticmethod
    def _merge_legs(nodes_leg1, edges_leg1, nodes_leg2, edges_leg2):
        all_nodes = nodes_leg1 + nodes_leg2[1:]
        all_edges = edges_leg1 + edges_leg2
        return all_nodes, all_edges

    def _compute_two_leg_path(
        self,
        start_node_id,
        pickup_node_id,
        delivery_node_id,
        banned_nodes=None,
        banned_edges=None,
    ):
        nodes_leg1, edges_leg1 = self.graph_engine.get_path(
            start_node_id,
            pickup_node_id,
            banned_nodes=banned_nodes,
            banned_edges=banned_edges,
        )
        if not nodes_leg1:
            return (
                None,
                None,
                f"Path not found from {start_node_id} to {pickup_node_id}",
            )

        nodes_leg2, edges_leg2 = self.graph_engine.get_path(
            pickup_node_id,
            delivery_node_id,
            banned_nodes=banned_nodes,
            banned_edges=banned_edges,
        )
        if not nodes_leg2:
            return (
                None,
                None,
                f"Path not found from {pickup_node_id} to {delivery_node_id}",
            )

        all_nodes, all_edges = self._merge_legs(
            nodes_leg1, edges_leg1, nodes_leg2, edges_leg2
        )
        return all_nodes, all_edges, None

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

            if agv.is_charging_locked():
                return {
                    "success": False,
                    "error": (
                        f"AGV {serial_number} is locked for charging and cannot accept "
                        "a new transport order"
                    ),
                }

        except AGV.DoesNotExist:
            return {"success": False, "error": "AGV does not exist"}

        # 2. Define start node for the order:
        # Define if the AGV is currently busy with an active order.
        # If yes, chain the new order to start from the last node of the current order.
        last_active_order = (
            Order.objects.filter(agv=agv, status__in=["SENT", "ACTIVE", "QUEUED"])
            .order_by("-created_at")
            .first()
        )

        if last_active_order:
            try:
                last_actions = (last_active_order.nodes or [])[-1].get("actions", [])
            except (IndexError, AttributeError, TypeError):
                return {
                    "success": False,
                    "error": "Malformed nodes data in previous order",
                }

            if any(
                action.get("actionType") == "startCharging" for action in last_actions
            ):
                return {
                    "success": False,
                    "error": (
                        f"AGV {serial_number} is already heading to or waiting at a "
                        "charging station"
                    ),
                }

            # Chaining: Start from the last node of the current active order instead of current position
            try:
                start_node_id = last_active_order.nodes[-1]["nodeId"]
                initial_status = "QUEUED"
                print(
                    f"Chaining order: Start from {start_node_id} (End of Order {last_active_order.order_id})"
                )
            except (IndexError, KeyError, TypeError):
                # Fallback if the order's nodes data is malformed
                return {
                    "success": False,
                    "error": "Malformed nodes data in previous order",
                }
        else:
            # If no active order, start from current position
            last_state = AGVState.objects.filter(agv=agv).order_by("-timestamp").first()
            if not last_state:
                return {"success": False, "error": "AGV has no position data (State)"}

            start_node_id = last_state.last_node_id
            initial_status = "CREATED"

        # 3. Calculate path with 2 legs: current -> pickup -> delivery
        all_nodes, all_edges, path_error = self._compute_two_leg_path(
            start_node_id=start_node_id,
            pickup_node_id=pickup_node_id,
            delivery_node_id=delivery_node_id,
        )
        if path_error:
            return {"success": False, "error": path_error}

        # Phase 2: reservation check before creating the order.
        self.reservation_service.expire_old_reservations()
        conflict_result = self.reservation_service.detect_conflicts(
            agv=agv,
            nodes=all_nodes,
            edges=all_edges,
        )

        used_replan = False
        used_horizon_release = False
        release_cut_sequence = None
        final_conflict_result = conflict_result

        if conflict_result.has_conflict:
            replanned_nodes, replanned_edges, path_error = self._compute_two_leg_path(
                start_node_id=start_node_id,
                pickup_node_id=pickup_node_id,
                delivery_node_id=delivery_node_id,
                banned_nodes=conflict_result.node_ids,
                banned_edges=conflict_result.edge_ids,
            )
            if path_error:
                used_horizon_release = True
                all_nodes, all_edges, release_cut_sequence = (
                    self.reservation_service.apply_horizon_release(
                        nodes=all_nodes,
                        edges=all_edges,
                        conflict_node_ids=conflict_result.node_ids,
                        conflict_edge_ids=conflict_result.edge_ids,
                    )
                )
            else:
                all_nodes, all_edges = replanned_nodes, replanned_edges
                used_replan = True
                final_conflict_result = self.reservation_service.detect_conflicts(
                    agv=agv,
                    nodes=all_nodes,
                    edges=all_edges,
                )
                if final_conflict_result.has_conflict:
                    used_horizon_release = True
                    all_nodes, all_edges, release_cut_sequence = (
                        self.reservation_service.apply_horizon_release(
                            nodes=all_nodes,
                            edges=all_edges,
                            conflict_node_ids=final_conflict_result.node_ids,
                            conflict_edge_ids=final_conflict_result.edge_ids,
                        )
                    )

        # Mark transport phase boundaries for simulator metrics.
        for node in all_nodes:
            node_id = node.get("nodeId")
            if node_id == pickup_node_id:
                self._append_action(node, "pick", weight=DEFAULT_LOAD_KG)
            elif node_id == delivery_node_id:
                self._append_action(node, "drop")

        # 4. Create new Order in Database
        # (Signal post_save will automatically send MQTT)
        new_order_id = f"ORD_{uuid.uuid4().hex[:8].upper()}"

        new_order = Order.objects.create(
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
        self.reservation_service.persist_reservations(new_order)

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
            "reservation_conflict_detected": conflict_result.has_conflict,
            "reservation_replan_used": used_replan,
            "reservation_horizon_release_used": used_horizon_release,
            "release_cut_sequence": release_cut_sequence,
        }

    def create_charging_order(
        self, serial_number: str, start_node_id: str, charging_node_id: str
    ):
        """Create an auto-charging order and append a VDA5050 startCharging action.

        This method finds a path from the AGV current node to a charging node,
        injects a startCharging action into the final node, stores the order,
        and returns a structured result.
        """
        # 1. Get AGV by serial number.
        try:
            agv = AGV.objects.get(serial_number=serial_number)
        except AGV.DoesNotExist:
            return {"success": False, "error": "AGV does not exist"}

        # 1b. If AGV already has in-flight work, chain charging after the last
        # pending order and keep it QUEUED instead of dispatching immediately.
        initial_status = "CREATED"
        effective_start_node = start_node_id
        last_active_order = (
            Order.objects.filter(
                agv=agv,
                status__in=["SENT", "ACTIVE", "QUEUED"],
            )
            .order_by("-created_at")
            .first()
        )

        if last_active_order:
            try:
                effective_start_node = last_active_order.nodes[-1]["nodeId"]
                initial_status = "QUEUED"
            except (IndexError, KeyError, TypeError):
                return {
                    "success": False,
                    "error": "Malformed nodes data in previous order",
                }

        # 2. Calculate path to charging station.
        nodes, edges = self.graph_engine.get_path(
            effective_start_node, charging_node_id
        )
        if not nodes:
            return {
                "success": False,
                "error": (
                    f"Path not found from {effective_start_node} to {charging_node_id}"
                ),
            }

        self.reservation_service.expire_old_reservations()
        conflict_result = self.reservation_service.detect_conflicts(
            agv=agv, nodes=nodes, edges=edges
        )
        used_horizon_release = False
        release_cut_sequence = None
        if conflict_result.has_conflict:
            nodes, edges, release_cut_sequence = (
                self.reservation_service.apply_horizon_release(
                    nodes=nodes,
                    edges=edges,
                    conflict_node_ids=conflict_result.node_ids,
                    conflict_edge_ids=conflict_result.edge_ids,
                )
            )
            used_horizon_release = True

        # 3. Inject VDA 5050 startCharging action to the final node.
        final_node = nodes[-1]
        final_node.setdefault("actions", []).append(
            {
                "actionType": "startCharging",
                "actionId": f"charge_{int(time.time())}",
                "blockingType": "HARD",
                "actionParameters": [],
            }
        )

        # 4. Persist charging order in DB.
        new_order_id = f"ORD_{uuid.uuid4().hex[:8].upper()}"
        new_order = Order.objects.create(
            header_id=0,
            timestamp=timezone.now(),
            order_id=new_order_id,
            order_update_id=0,
            zone_set_id="zone_1",
            agv=agv,
            status=initial_status,
            nodes=nodes,
            edges=edges,
        )
        self.reservation_service.persist_reservations(new_order)

        # 5. Return structured result.
        return {
            "success": True,
            "order_id": new_order_id,
            "status": initial_status,
            "message": (
                "Charging order created and sent"
                if initial_status == "CREATED"
                else f"Charging order queued (start from {effective_start_node})"
            ),
            "reservation_conflict_detected": conflict_result.has_conflict,
            "reservation_horizon_release_used": used_horizon_release,
            "release_cut_sequence": release_cut_sequence,
        }
