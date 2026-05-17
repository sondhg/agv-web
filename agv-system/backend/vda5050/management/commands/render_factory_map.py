from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
from django.core.management.base import BaseCommand, CommandError

from vda5050.models import GraphEdge, GraphNode


class Command(BaseCommand):
    help = "Render factory graph from DB to a PNG image."

    def add_arguments(self, parser):
        parser.add_argument(
            "--map-id",
            type=str,
            default="map_1",
            help="Map ID to render (default: map_1)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="outputs/factory_map.png",
            help="Output PNG path, relative to backend/manage.py cwd or absolute path",
        )
        parser.add_argument(
            "--label-nodes",
            action="store_true",
            help="Draw node_id labels on the map",
        )

    def handle(self, *args, **options):
        map_id = options["map_id"]
        output_arg = options["output"]
        label_nodes = options["label_nodes"]

        nodes = list(GraphNode.objects.filter(map_id=map_id).order_by("node_id"))
        edges = list(
            GraphEdge.objects.filter(map_id=map_id).select_related(
                "start_node", "end_node"
            )
        )

        if not nodes:
            raise CommandError(f"No nodes found for map_id='{map_id}'.")

        # Position dictionary for drawing
        pos = {n.node_id: (n.x, n.y) for n in nodes}

        # Node colors by type
        color_by_type = {
            GraphNode.NodeType.CHARGING: "#1f77b4",  # blue
            GraphNode.NodeType.PICKUP: "#2ca02c",  # green
            GraphNode.NodeType.DELIVERY: "#d62728",  # red
            GraphNode.NodeType.DEFAULT: "#7f7f7f",  # gray
        }

        # Draw figure
        fig, ax = plt.subplots(figsize=(14, 10))
        ax.set_title(f"Factory Map Visualization ({map_id})")
        ax.set_xlabel("X (m)")
        ax.set_ylabel("Y (m)")
        ax.grid(True, linestyle="--", alpha=0.35)

        # Draw unique corridors once (many systems store both directions)
        seen_pairs = set()
        for e in edges:
            u = e.start_node.node_id
            v = e.end_node.node_id
            if u not in pos or v not in pos:
                continue

            pair = tuple(sorted((u, v)))
            if pair in seen_pairs:
                continue
            seen_pairs.add(pair)

            x1, y1 = pos[u]
            x2, y2 = pos[v]

            # Visual cue by speed
            # Fast edges -> thicker and darker
            width = 1.0 + min(max(e.max_velocity, 0.5), 3.0) * 0.9
            alpha = 0.45 + min(max(e.max_velocity, 0.5), 3.0) * 0.12
            ax.plot(
                [x1, x2],
                [y1, y2],
                color="#4c4c4c",
                linewidth=width,
                alpha=min(alpha, 0.9),
            )

        # Draw nodes by type
        for node_type in [
            GraphNode.NodeType.DEFAULT,
            GraphNode.NodeType.CHARGING,
            GraphNode.NodeType.PICKUP,
            GraphNode.NodeType.DELIVERY,
        ]:
            type_nodes = [n for n in nodes if n.node_type == node_type]
            if not type_nodes:
                continue

            xs = [n.x for n in type_nodes]
            ys = [n.y for n in type_nodes]
            ax.scatter(
                xs,
                ys,
                s=140,
                c=color_by_type.get(node_type, "#7f7f7f"),
                edgecolors="black",
                linewidths=0.8,
                label=node_type,
                zorder=3,
            )

        if label_nodes:
            for n in nodes:
                ax.text(
                    n.x + 0.6,
                    n.y + 0.6,
                    n.node_id,
                    fontsize=8,
                    color="#222222",
                    zorder=4,
                )

        # Equal scale keeps geometry true to meter coordinates
        ax.set_aspect("equal", adjustable="box")
        ax.legend(title="Node Type", loc="best")

        output_path = Path(output_arg)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        fig.tight_layout()
        fig.savefig(output_path, dpi=180)
        plt.close(fig)

        self.stdout.write(
            self.style.SUCCESS(f"Map image saved to: {output_path.resolve()}")
        )
        self.stdout.write(
            f"Rendered {len(nodes)} nodes and {len(seen_pairs)} unique corridors "
            f"(from {len(edges)} directed edges)."
        )
