from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
from .models import AGV, Order
from .serializers import AGVSerializer, OrderSerializer, AGVStateSerializer
from .modules.scheduler import Scheduler
from .modules.bidding import BiddingEngine


class AGVViewSet(viewsets.ModelViewSet):
    queryset = AGV.objects.all()
    serializer_class = AGVSerializer
    lookup_field = "serial_number"  # Find AGV by serial number (e.g: /api/agvs/AGV_01/)

    @action(detail=True, methods=["get"])
    def states(self, request, serial_number=None):
        """Get the latest states for this AGV"""
        agv = self.get_object()
        states = agv.states.all()[:100]  # Get the latest 100 states
        serializer = AGVStateSerializer(states, many=True)
        return Response(serializer.data)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().order_by("-created_at")
    serializer_class = OrderSerializer


class TaskViewSet(viewsets.ViewSet):
    """
    API endpoint to create transport tasks for AGVs.
    """

    def create(self, request):
        """
        POST /api/tasks/
        Body: {
            "pickup_node_id": "Node_A",   # Điểm lấy hàng
            "delivery_node_id": "Node_C"  # Điểm giao hàng
        }
        """
        pickup_node_id = request.data.get("pickup_node_id")
        delivery_node_id = request.data.get("delivery_node_id")

        if not pickup_node_id or not delivery_node_id:
            return Response(
                {"error": "Missing pickup_node_id or delivery_node_id"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Run Bidding Engine to select the best AGV
        bid_engine = BiddingEngine()
        winner_agv, error = bid_engine.run_auction(pickup_node_id, delivery_node_id)

        if not winner_agv:
            return Response(
                {"error": f"No suitable AGV found: {error}"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # Call Scheduler to process
        scheduler = Scheduler()
        result = scheduler.create_transport_order(
            winner_agv.serial_number, pickup_node_id, delivery_node_id
        )

        if result["success"]:
            result["winner_agv"] = winner_agv.serial_number
            return Response(result, status=status.HTTP_201_CREATED)
        else:
            return Response(result, status=status.HTTP_400_BAD_REQUEST)
