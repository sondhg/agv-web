from django.db import models, transaction
from django.utils import timezone
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.decorators import action
import networkx as nx

from .models import AGV, Order, GraphNode, GraphEdge
from .serializers import (
    AGVSerializer,
    OrderSerializer,
    AGVStateSerializer,
    GraphNodeSerializer,
    GraphEdgeSerializer,
)
from .modules.scheduler import Scheduler
from .modules.bidding import BiddingEngine
from .graph_engine import GraphEngine


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


class GraphNodeViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for managing graph nodes.

    Endpoints:
    - GET /api/graph/nodes/ - List all nodes
    - POST /api/graph/nodes/ - Create a new node
    - GET /api/graph/nodes/{id}/ - Retrieve a specific node
    - PUT /api/graph/nodes/{id}/ - Update a node
    - PATCH /api/graph/nodes/{id}/ - Partial update
    - DELETE /api/graph/nodes/{id}/ - Delete a node
    - POST /api/graph/nodes/bulk_create/ - Create multiple nodes
    - DELETE /api/graph/nodes/bulk_delete/ - Delete multiple nodes
    """

    queryset = GraphNode.objects.all().order_by("node_id")
    serializer_class = GraphNodeSerializer

    def get_queryset(self):
        """Filter nodes by map_id if provided."""
        queryset = super().get_queryset()
        map_id = self.request.query_params.get("map_id")
        if map_id:
            queryset = queryset.filter(map_id=map_id)
        return queryset

    def destroy(self, request, *args, **kwargs):
        """
        Delete a node. Check if it's used in any edges first.
        """
        instance = self.get_object()

        # Check if node is used in any edges
        outgoing_edges = instance.outgoing_edges.count()
        incoming_edges = instance.incoming_edges.count()

        if outgoing_edges > 0 or incoming_edges > 0:
            return Response(
                {
                    "error": f"Cannot delete node {instance.node_id}. "
                    f"It is connected to {outgoing_edges + incoming_edges} edge(s). "
                    f"Delete the edges first."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        return super().destroy(request, *args, **kwargs)

    @action(detail=False, methods=["post"])
    def bulk_create(self, request):
        """
        Create multiple nodes at once.

        POST /api/graph/nodes/bulk_create/
        Body: {
            "nodes": [
                {"node_id": "Node_A", "x": 0, "y": 0, "map_id": "map_1"},
                {"node_id": "Node_B", "x": 10, "y": 0, "map_id": "map_1"}
            ]
        }
        """
        nodes_data = request.data.get("nodes", [])

        if not isinstance(nodes_data, list) or len(nodes_data) == 0:
            return Response(
                {"error": "Provide a list of nodes to create"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_nodes = []
        errors = []

        with transaction.atomic():
            for idx, node_data in enumerate(nodes_data):
                serializer = GraphNodeSerializer(data=node_data)
                if serializer.is_valid():
                    serializer.save()
                    created_nodes.append(serializer.data)
                else:
                    errors.append({"index": idx, "errors": serializer.errors})

        if errors:
            return Response(
                {
                    "message": f"Created {len(created_nodes)} nodes with {len(errors)} errors",
                    "created": created_nodes,
                    "errors": errors,
                },
                status=status.HTTP_207_MULTI_STATUS,
            )

        return Response(
            {
                "message": f"Successfully created {len(created_nodes)} nodes",
                "nodes": created_nodes,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        """
        Delete multiple nodes by their IDs.

        POST /api/graph/nodes/bulk_delete/
        Body: {
            "node_ids": [1, 2, 3]
        }
        """
        node_ids = request.data.get("node_ids", [])

        if not isinstance(node_ids, list) or len(node_ids) == 0:
            return Response(
                {"error": "Provide a list of node IDs to delete"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        nodes = GraphNode.objects.filter(id__in=node_ids)
        count = nodes.count()

        if count == 0:
            return Response(
                {"error": "No nodes found with the provided IDs"},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Check for edges connected to these nodes
        nodes_with_edges = []
        for node in nodes:
            edge_count = node.outgoing_edges.count() + node.incoming_edges.count()
            if edge_count > 0:
                nodes_with_edges.append(node.node_id)

        if nodes_with_edges:
            return Response(
                {
                    "error": f"Cannot delete nodes with existing edges: {', '.join(nodes_with_edges)}. "
                    "Delete the edges first."
                },
                status=status.HTTP_400_BAD_REQUEST,
            )

        nodes.delete()
        return Response(
            {"message": f"Successfully deleted {count} node(s)"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """
        Get statistics about the graph nodes.

        GET /api/graph/nodes/statistics/
        """
        total_nodes = GraphNode.objects.count()
        maps = (
            GraphNode.objects.values("map_id")
            .distinct()
            .values_list("map_id", flat=True)
        )

        stats = {
            "total_nodes": total_nodes,
            "maps": list(maps),
            "nodes_per_map": {
                map_id: GraphNode.objects.filter(map_id=map_id).count()
                for map_id in maps
            },
        }

        return Response(stats)


class GraphEdgeViewSet(viewsets.ModelViewSet):
    """
    API ViewSet for managing graph edges.

    Endpoints:
    - GET /api/graph/edges/ - List all edges
    - POST /api/graph/edges/ - Create a new edge
    - GET /api/graph/edges/{id}/ - Retrieve a specific edge
    - PUT /api/graph/edges/{id}/ - Update an edge
    - PATCH /api/graph/edges/{id}/ - Partial update
    - DELETE /api/graph/edges/{id}/ - Delete an edge
    - POST /api/graph/edges/bulk_create/ - Create multiple edges
    - DELETE /api/graph/edges/bulk_delete/ - Delete multiple edges
    """

    queryset = GraphEdge.objects.all().select_related("start_node", "end_node")
    serializer_class = GraphEdgeSerializer

    def get_queryset(self):
        """Filter edges by map_id or node if provided."""
        queryset = super().get_queryset()
        map_id = self.request.query_params.get("map_id")
        node_id = self.request.query_params.get("node_id")

        if map_id:
            queryset = queryset.filter(map_id=map_id)

        if node_id:
            # Find edges connected to this node (either start or end)
            queryset = queryset.filter(start_node__node_id=node_id) | queryset.filter(
                end_node__node_id=node_id
            )

        return queryset

    @action(detail=False, methods=["post"])
    def bulk_create(self, request):
        """
        Create multiple edges at once.

        POST /api/graph/edges/bulk_create/
        Body: {
            "edges": [
                {
                    "start_node_id": "Node_A",
                    "end_node_id": "Node_B",
                    "map_id": "map_1",
                    "length": 10.0,
                    "max_velocity": 2.0,
                    "is_directed": true
                }
            ]
        }
        """
        edges_data = request.data.get("edges", [])

        if not isinstance(edges_data, list) or len(edges_data) == 0:
            return Response(
                {"error": "Provide a list of edges to create"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        created_edges = []
        errors = []

        with transaction.atomic():
            for idx, edge_data in enumerate(edges_data):
                serializer = GraphEdgeSerializer(data=edge_data)
                if serializer.is_valid():
                    serializer.save()
                    created_edges.append(serializer.data)
                else:
                    errors.append({"index": idx, "errors": serializer.errors})

        if errors:
            return Response(
                {
                    "message": f"Created {len(created_edges)} edges with {len(errors)} errors",
                    "created": created_edges,
                    "errors": errors,
                },
                status=status.HTTP_207_MULTI_STATUS,
            )

        return Response(
            {
                "message": f"Successfully created {len(created_edges)} edges",
                "edges": created_edges,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=False, methods=["post"])
    def bulk_delete(self, request):
        """
        Delete multiple edges by their IDs.

        POST /api/graph/edges/bulk_delete/
        Body: {
            "edge_ids": [1, 2, 3]
        }
        """
        edge_ids = request.data.get("edge_ids", [])

        if not isinstance(edge_ids, list) or len(edge_ids) == 0:
            return Response(
                {"error": "Provide a list of edge IDs to delete"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        edges = GraphEdge.objects.filter(id__in=edge_ids)
        count = edges.count()

        if count == 0:
            return Response(
                {"error": "No edges found with the provided IDs"},
                status=status.HTTP_404_NOT_FOUND,
            )

        edges.delete()
        return Response(
            {"message": f"Successfully deleted {count} edge(s)"},
            status=status.HTTP_200_OK,
        )

    @action(detail=False, methods=["get"])
    def statistics(self, request):
        """
        Get statistics about the graph edges.

        GET /api/graph/edges/statistics/
        """
        total_edges = GraphEdge.objects.count()
        directed_edges = GraphEdge.objects.filter(is_directed=True).count()
        bidirectional_edges = GraphEdge.objects.filter(is_directed=False).count()

        stats = {
            "total_edges": total_edges,
            "directed_edges": directed_edges,
            "bidirectional_edges": bidirectional_edges,
            "average_length": (
                GraphEdge.objects.aggregate(avg_length=models.Avg("length"))[
                    "avg_length"
                ]
                or 0
            ),
            "average_max_velocity": (
                GraphEdge.objects.aggregate(avg_velocity=models.Avg("max_velocity"))[
                    "avg_velocity"
                ]
                or 0
            ),
        }

        return Response(stats)


class GraphViewSet(viewsets.ViewSet):
    """
    ViewSet for graph-level operations (validation, export, import).
    """

    @action(detail=False, methods=["get"])
    def validate(self, request):
        """
        Validate the graph structure for issues.

        GET /api/graph/validate/
        """
        issues = []
        warnings = []

        # Check for isolated nodes (nodes with no edges)
        all_nodes = GraphNode.objects.all()
        for node in all_nodes:
            edge_count = node.outgoing_edges.count() + node.incoming_edges.count()
            if edge_count == 0:
                warnings.append(f"Node {node.node_id} is isolated (no connections)")

        # Check for unreachable nodes (using NetworkX)
        try:
            graph_engine = GraphEngine()
            graph = graph_engine.graph

            if len(graph.nodes) > 0:
                # Check connectivity (for directed graphs, use weak connectivity)
                if not nx.is_weakly_connected(graph):
                    warnings.append(
                        "Graph is not fully connected. Some nodes may be unreachable."
                    )

                # Check for nodes with only incoming or only outgoing edges
                for node_id in graph.nodes:
                    in_degree = graph.in_degree(node_id)
                    out_degree = graph.out_degree(node_id)

                    if in_degree == 0 and out_degree > 0:
                        warnings.append(
                            f"Node {node_id} has no incoming edges (dead end)"
                        )
                    elif out_degree == 0 and in_degree > 0:
                        warnings.append(
                            f"Node {node_id} has no outgoing edges (cannot leave)"
                        )

        except Exception as e:
            issues.append(f"Error validating graph connectivity: {str(e)}")

        is_valid = len(issues) == 0

        return Response(
            {
                "valid": is_valid,
                "issues": issues,
                "warnings": warnings,
                "total_nodes": GraphNode.objects.count(),
                "total_edges": GraphEdge.objects.count(),
            }
        )

    @action(detail=False, methods=["get"])
    def export(self, request):
        """
        Export the entire graph as JSON.

        GET /api/graph/export/?map_id=map_1
        """
        map_id = request.query_params.get("map_id")

        nodes_qs = GraphNode.objects.all()
        edges_qs = GraphEdge.objects.all().select_related("start_node", "end_node")

        if map_id:
            nodes_qs = nodes_qs.filter(map_id=map_id)
            edges_qs = edges_qs.filter(map_id=map_id)

        nodes = GraphNodeSerializer(nodes_qs, many=True).data
        edges = GraphEdgeSerializer(edges_qs, many=True).data

        return Response(
            {
                "map_id": map_id or "all",
                "nodes": nodes,
                "edges": edges,
                "metadata": {
                    "total_nodes": len(nodes),
                    "total_edges": len(edges),
                    "exported_at": timezone.now().isoformat(),
                },
            }
        )

    @action(detail=False, methods=["post"])
    def import_graph(self, request):
        """
        Import a graph from JSON (bulk create nodes and edges).

        POST /api/graph/import/
        Body: {
            "nodes": [...],
            "edges": [...],
            "clear_existing": false  # Optional: clear existing data first
        }
        """
        nodes_data = request.data.get("nodes", [])
        edges_data = request.data.get("edges", [])
        clear_existing = request.data.get("clear_existing", False)

        if clear_existing:
            GraphEdge.objects.all().delete()
            GraphNode.objects.all().delete()

        created_nodes = []
        created_edges = []
        errors = []

        with transaction.atomic():
            # Create nodes first
            for idx, node_data in enumerate(nodes_data):
                serializer = GraphNodeSerializer(data=node_data)
                if serializer.is_valid():
                    serializer.save()
                    created_nodes.append(serializer.data)
                else:
                    errors.append(
                        {"type": "node", "index": idx, "errors": serializer.errors}
                    )

            # Then create edges
            for idx, edge_data in enumerate(edges_data):
                serializer = GraphEdgeSerializer(data=edge_data)
                if serializer.is_valid():
                    serializer.save()
                    created_edges.append(serializer.data)
                else:
                    errors.append(
                        {"type": "edge", "index": idx, "errors": serializer.errors}
                    )

        return Response(
            {
                "message": f"Import completed: {len(created_nodes)} nodes, {len(created_edges)} edges",
                "created_nodes": len(created_nodes),
                "created_edges": len(created_edges),
                "errors": errors,
            },
            status=status.HTTP_201_CREATED
            if not errors
            else status.HTTP_207_MULTI_STATUS,
        )
