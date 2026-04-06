import math
from datetime import timedelta
from typing import Optional

from django.utils import timezone

from vda5050.models import AGV, GraphNode, Order
from vda5050.modules.scheduler import Scheduler


class BatteryManager:
    """Handle low-battery monitoring and charging-order trigger for AGVs."""

    BATTERY_LOW_THRESHOLD: float = 20.0
    CHARGING_RETRY_COOLDOWN_SECONDS: int = 60

    @staticmethod
    def _is_charging_order(order: Order) -> bool:
        """Return True when an order contains VDA5050 startCharging action."""
        nodes = order.nodes or []
        if not nodes:
            return False

        last_node = nodes[-1]
        actions = last_node.get("actions", [])
        for action in actions:
            if action.get("actionType") == "startCharging":
                return True
        return False

    def check_and_charge(
        self, agv: AGV, current_battery: float, current_node_id: str
    ) -> None:
        """Check battery level and create a charging order when required.

        Steps:
        1. Exit when battery is still above the configured low threshold.
        2. Exit when AGV is busy with ACTIVE/SENT orders.
        3. Find all charging stations on the AGV's current map.
        4. Compute nearest charging station by Euclidean distance.
        5. Trigger Scheduler.create_charging_order for the closest station.
        """
        # Step 1: Battery is not low yet, no charging action needed.
        if current_battery > self.BATTERY_LOW_THRESHOLD:
            print(
                f"🔋 AGV {agv.serial_number}: battery {current_battery:.2f}% > "
                f"threshold {self.BATTERY_LOW_THRESHOLD:.2f}%, skip charging."
            )
            return

        if not current_node_id:
            print(f"⚠️ AGV {agv.serial_number}: missing current_node_id, skip charging check.")
            return

        # Step 2: If AGV has any ACTIVE/SENT order, it is considered busy.
        is_busy = agv.orders.filter(
            status__in=[
                Order.OrderStatus.ACTIVE,
                Order.OrderStatus.SENT,
                Order.OrderStatus.QUEUED,
            ]
        ).exists()
        if is_busy:
            print(
                f"⏳ AGV {agv.serial_number}: low battery ({current_battery:.2f}%) "
                "but AGV is busy (ACTIVE/SENT order exists), skip charging order."
            )
            return

        # Step 3: Find all charging stations on the same map as AGV.
        charging_stations = GraphNode.objects.filter(
            map_id=agv.current_map_id,
            node_type=GraphNode.NodeType.CHARGING,
        )
        if not charging_stations.exists():
            print(
                f"⚠️ AGV {agv.serial_number}: no charging station found on map "
                f"'{agv.current_map_id}'."
            )
            return

        # Find current node coordinates for distance computation.
        try:
            current_node = GraphNode.objects.get(
                map_id=agv.current_map_id,
                node_id=current_node_id,
            )
        except GraphNode.DoesNotExist:
            print(
                f"⚠️ AGV {agv.serial_number}: current node '{current_node_id}' "
                f"not found on map '{agv.current_map_id}', cannot compute nearest charger."
            )
            return

        # If AGV is already at a charging node, avoid creating duplicate charging orders.
        if current_node.node_type == GraphNode.NodeType.CHARGING:
            print(
                f"⚡ AGV {agv.serial_number}: already at charging node "
                f"'{current_node.node_id}', skip creating new charging order."
            )
            return

        # Prevent duplicate charging orders when one is already in-flight.
        recent_orders = agv.orders.order_by("-created_at")[:10]
        for order in recent_orders:
            if not self._is_charging_order(order):
                continue

            if order.status in {
                Order.OrderStatus.CREATED,
                Order.OrderStatus.SENT,
                Order.OrderStatus.ACTIVE,
                Order.OrderStatus.QUEUED,
            }:
                print(
                    f"⏳ AGV {agv.serial_number}: charging order {order.order_id} "
                    f"is {order.status}, skip creating duplicate."
                )
                return

            if order.status in {Order.OrderStatus.REJECTED, Order.OrderStatus.FAILED}:
                cooldown_at = timezone.now() - timedelta(
                    seconds=self.CHARGING_RETRY_COOLDOWN_SECONDS
                )
                if order.created_at and order.created_at >= cooldown_at:
                    print(
                        f"🛑 AGV {agv.serial_number}: latest charging order "
                        f"{order.order_id} was {order.status}, retry after cooldown."
                    )
                    return

        # Step 4: Scan all charging stations and pick the nearest one.
        closest_station: Optional[GraphNode] = None
        min_distance: float = float("inf")

        for station in charging_stations:
            distance = math.hypot(station.x - current_node.x, station.y - current_node.y)
            if distance < min_distance:
                min_distance = distance
                closest_station = station

        # Step 5: Create charging order for the nearest charging station.
        if closest_station is not None:
            scheduler = Scheduler()
            result = scheduler.create_charging_order(
                agv.serial_number,
                current_node_id,
                closest_station.node_id,
            )
            if not result.get("success"):
                print(
                    f"⚠️ AGV {agv.serial_number}: failed to create charging order: "
                    f"{result.get('error', 'unknown error')}"
                )
                return
            print(
                f"✅ AGV {agv.serial_number}: selected charging station "
                f"'{closest_station.node_id}' (distance={min_distance:.2f}), "
                "charging order requested."
            )
