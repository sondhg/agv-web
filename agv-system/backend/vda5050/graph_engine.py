import networkx as nx
from .models import GraphNode, GraphEdge

class GraphEngine:
    def __init__(self):
        self.graph = nx.DiGraph() 
        self.load_graph()

    def load_graph(self):
        """Load data from DB into NetworkX"""
        self.graph.clear()
        
        # 1. Add Nodes
        nodes = GraphNode.objects.all()
        for n in nodes:
            self.graph.add_node(n.node_id, x=n.x, y=n.y, map_id=n.map_id)
            
        # 2. Add Edges
        edges = GraphEdge.objects.all()
        for e in edges:
            u = e.start_node.node_id
            v = e.end_node.node_id
            
            # Add forward edge
            self.graph.add_edge(u, v, weight=e.length, obj=e)
            
            # If the edge is bidirectional, add the reverse edge
            if not e.is_directed:
                self.graph.add_edge(v, u, weight=e.length, obj=e)

    def get_path_cost(self, start_node, end_node):
        """
        Calculate the cost of the shortest path between two nodes.
        """
        try:
            # Calculate the length of the shortest path (with 'weight' as the edge length)
            length = nx.shortest_path_length(
                self.graph, 
                source=start_node, 
                target=end_node, 
                weight='weight'
            )
            return length
        except nx.NetworkXNoPath:
            return float('inf') # Infinite cost if no path exists
        except Exception as e:
            print(f"Error calculating cost: {e}")
            return float('inf')

    def get_path_info(self, start_node, end_node):
        """
        Return (distance, num_turns) for the shortest path.
        num_turns = number of intermediate nodes (direction-change points).
        """
        try:
            path_nodes = nx.shortest_path(
                self.graph, source=start_node, target=end_node, weight='weight'
            )
            distance = nx.shortest_path_length(
                self.graph, source=start_node, target=end_node, weight='weight'
            )
            num_turns = max(0, len(path_nodes) - 2)
            return distance, num_turns
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return float('inf'), 0
        except Exception as e:
            print(f"Error in get_path_info: {e}")
            return float('inf'), 0

    def get_path(self, start_node_id, end_node_id):
        """
        Algorithm 1: Calculate Baseline (using Dijkstra).
        """
        try:
            # 1. Find the list of nodes in the path (e.g., ['Node_A', 'Node_B', 'Node_C'])
            path_nodes = nx.shortest_path(self.graph, source=start_node_id, target=end_node_id, weight='weight')
            
            # 2. Build JSON structure for Order
            vda_nodes = []
            vda_edges = []
            sequence_id = 0

            for i, node_id in enumerate(path_nodes):
                # --- Process Node ---
                node_obj = self.graph.nodes[node_id]
                vda_nodes.append({
                    "nodeId": node_id,
                    "sequenceId": sequence_id,
                    "released": True, # Default to released
                    "actions": [],
                    "nodePosition": {
                        "x": node_obj['x'],
                        "y": node_obj['y'],
                        "mapId": node_obj['map_id']
                    }
                })
                
                # --- Process Edge (Connect current node to next node) ---
                if i < len(path_nodes) - 1:
                    next_node_id = path_nodes[i+1]
                    # Get edge information from the graph
                    edge_data = self.graph.get_edge_data(node_id, next_node_id)
                    edge_obj = edge_data['obj'] # Get original GraphEdge model
                    
                    sequence_id += 1 # Increase seq for edge
                    vda_edges.append({
                        "edgeId": f"{node_id}_{next_node_id}",
                        "sequenceId": sequence_id,
                        "startNodeId": node_id,
                        "endNodeId": next_node_id,
                        "released": True,
                        "maxSpeed": edge_obj.max_velocity,
                        # "trajectory": {} # If you want to draw a curve, add it later
                    })
                    
                    sequence_id += 1 # Increase seq for next node

            return vda_nodes, vda_edges

        except nx.NetworkXNoPath:
            print(f"No path found from {start_node_id} to {end_node_id}")
            return None, None
        except Exception as e:
            print(f"Error finding path: {e}")
            return None, None