"""
Django management command to setup test graph for AGV navigation.
Usage: python manage.py setup_test_graph
"""

from django.core.management.base import BaseCommand
from vda5050.models import GraphNode, GraphEdge


class Command(BaseCommand):
    help = "Setup test graph with nodes and edges for AGV navigation"

    def handle(self, *args, **options):
        self.stdout.write(
            self.style.SUCCESS(f"\n{'=' * 60}\n📍 Setting up test graph\n{'=' * 60}\n")
        )

        # Clear existing graph
        GraphNode.objects.all().delete()
        GraphEdge.objects.all().delete()

        # Define nodes (8x8 grid-like structure)
        nodes_data = [
            # Row 1
            {"node_id": "Node_A", "x": 0, "y": 0},
            {"node_id": "Node_B", "x": 10, "y": 0},
            {"node_id": "Node_C", "x": 20, "y": 0},
            {"node_id": "Node_D", "x": 30, "y": 0},
            # Row 2
            {"node_id": "Node_E", "x": 0, "y": 10},
            {"node_id": "Node_F", "x": 10, "y": 10},
            {"node_id": "Node_G", "x": 20, "y": 10},
            {"node_id": "Node_H", "x": 30, "y": 10},
        ]

        # Create nodes
        created_nodes = {}
        for node_data in nodes_data:
            node = GraphNode.objects.create(
                node_id=node_data["node_id"],
                x=node_data["x"],
                y=node_data["y"],
                theta=0,
                map_id="default_map",
                description=f"Test node {node_data['node_id']}",
            )
            created_nodes[node_data["node_id"]] = node
            self.stdout.write(
                f"  ✅ Created node: {node_data['node_id']} at ({node_data['x']}, {node_data['y']})"
            )

        # Define edges (bidirectional connections)
        edges_data = [
            # Horizontal connections - Row 1
            ("Node_A", "Node_B", 10),
            ("Node_B", "Node_A", 10),
            ("Node_B", "Node_C", 10),
            ("Node_C", "Node_B", 10),
            ("Node_C", "Node_D", 10),
            ("Node_D", "Node_C", 10),
            # Horizontal connections - Row 2
            ("Node_E", "Node_F", 10),
            ("Node_F", "Node_E", 10),
            ("Node_F", "Node_G", 10),
            ("Node_G", "Node_F", 10),
            ("Node_G", "Node_H", 10),
            ("Node_H", "Node_G", 10),
            # Vertical connections - Column 1
            ("Node_A", "Node_E", 10),
            ("Node_E", "Node_A", 10),
            # Vertical connections - Column 2
            ("Node_B", "Node_F", 10),
            ("Node_F", "Node_B", 10),
            # Vertical connections - Column 3
            ("Node_C", "Node_G", 10),
            ("Node_G", "Node_C", 10),
            # Vertical connections - Column 4
            ("Node_D", "Node_H", 10),
            ("Node_H", "Node_D", 10),
        ]

        # Create edges
        edge_count = 0
        for start_id, end_id, distance in edges_data:
            edge = GraphEdge.objects.create(
                start_node=created_nodes[start_id],
                end_node=created_nodes[end_id],
                map_id="default_map",
                length=distance,
                max_velocity=2.0,
                is_directed=True,
            )
            edge_count += 1

        self.stdout.write(f"\n  ✅ Created {edge_count} edges")

        # Show graph structure
        self.stdout.write(
            self.style.SUCCESS(f"\n{'=' * 60}\n✅ Graph setup complete\n{'=' * 60}\n")
        )

        self.stdout.write("\n📊 Graph Structure:")
        self.stdout.write("  Row 1: Node_A -- Node_B -- Node_C -- Node_D")
        self.stdout.write("           |         |         |         |")
        self.stdout.write("  Row 2: Node_E -- Node_F -- Node_G -- Node_H")

        self.stdout.write("\n📈 Statistics:")
        self.stdout.write(f"  Total nodes: {GraphNode.objects.count()}")
        self.stdout.write(f"  Total edges: {GraphEdge.objects.count()}")
        self.stdout.write(
            f"  Avg connections per node: {GraphEdge.objects.count() / GraphNode.objects.count():.1f}"
        )

        self.stdout.write(self.style.SUCCESS("\n✅ Ready for testing!\n"))
