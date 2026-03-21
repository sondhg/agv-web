from rest_framework import serializers
from .models import AGV, Order, AGVState, GraphNode, GraphEdge


class AGVSerializer(serializers.ModelSerializer):
    class Meta:
        model = AGV
        fields = "__all__"


class AGVStateSerializer(serializers.ModelSerializer):
    class Meta:
        model = AGVState
        fields = "__all__"


class OrderSerializer(serializers.ModelSerializer):
    """
    Serializer for Order.
    Note: nodes and edges are JSONFields, so the client can send raw JSON.
    """

    class Meta:
        model = Order
        fields = "__all__"
        read_only_fields = ("order_update_id", "status", "created_at", "updated_at")

    def validate(self, data):
        """
        Validate after save to DB
        """
        # Check that nodes and edges are lists
        if not isinstance(data.get("nodes", []), list):
            raise serializers.ValidationError({"nodes": "Must be a list of nodes."})
        if not isinstance(data.get("edges", []), list):
            raise serializers.ValidationError({"edges": "Must be a list of edges."})
        return data


class GraphNodeSerializer(serializers.ModelSerializer):
    """
    Serializer for GraphNode.
    Mandatory fields: node_id, map_id, x, y
    Optional fields: theta (default: 0.0), description (default: "")
    """

    class Meta:
        model = GraphNode
        fields = ["id", "node_id", "map_id", "x", "y", "theta", "description"]
        read_only_fields = ["id"]
        extra_kwargs = {
            "theta": {"required": False, "default": 0.0},
            "description": {"required": False, "default": ""},
        }

    def validate_node_id(self, value):
        """Ensure node_id is not empty."""
        if not value or not value.strip():
            raise serializers.ValidationError("node_id cannot be empty.")
        # Check for duplicate node_id on update
        if self.instance:
            if (
                GraphNode.objects.exclude(pk=self.instance.pk)
                .filter(node_id=value)
                .exists()
            ):
                raise serializers.ValidationError(
                    f"Node with node_id '{value}' already exists."
                )
        return value.strip()


class GraphEdgeSerializer(serializers.ModelSerializer):
    """
    Serializer for GraphEdge.
    Mandatory fields: start_node_id, end_node_id, map_id
    Optional fields: length (auto-calculated), max_velocity (default: 1.0), is_directed (default: True)
    """

    start_node_id = serializers.CharField(write_only=True)
    end_node_id = serializers.CharField(write_only=True)

    # Include full node objects in read operations
    start_node = GraphNodeSerializer(read_only=True)
    end_node = GraphNodeSerializer(read_only=True)

    class Meta:
        model = GraphEdge
        fields = [
            "id",
            "start_node",
            "end_node",
            "start_node_id",
            "end_node_id",
            "map_id",
            "length",
            "max_velocity",
            "is_directed",
        ]
        read_only_fields = ["id", "length"]  # length is auto-calculated
        extra_kwargs = {
            "max_velocity": {"required": False, "default": 1.0},
            "is_directed": {"required": False, "default": True},
        }

    def validate(self, data):
        """Validate edge data and resolve node references."""
        start_node_id = data.get("start_node_id")
        end_node_id = data.get("end_node_id")

        # Ensure start and end nodes are different
        if start_node_id == end_node_id:
            raise serializers.ValidationError(
                "Start node and end node cannot be the same."
            )

        # Validate that nodes exist
        try:
            start_node = GraphNode.objects.get(node_id=start_node_id)
            end_node = GraphNode.objects.get(node_id=end_node_id)
        except GraphNode.DoesNotExist:
            raise serializers.ValidationError(
                f"Node not found: {start_node_id or end_node_id}"
            )

        # Add resolved nodes to data
        data["start_node"] = start_node
        data["end_node"] = end_node

        # Check for duplicate edge (same start and end)
        if self.instance:
            # Update case: exclude current instance
            if (
                GraphEdge.objects.exclude(pk=self.instance.pk)
                .filter(start_node=start_node, end_node=end_node)
                .exists()
            ):
                raise serializers.ValidationError(
                    f"Edge from {start_node_id} to {end_node_id} already exists."
                )
        else:
            # Create case
            if GraphEdge.objects.filter(
                start_node=start_node, end_node=end_node
            ).exists():
                raise serializers.ValidationError(
                    f"Edge from {start_node_id} to {end_node_id} already exists."
                )

        return data

    def create(self, validated_data):
        """Create edge with proper node references. Length is auto-calculated by the model."""
        # Remove the string IDs, we already have the node objects
        validated_data.pop("start_node_id", None)
        validated_data.pop("end_node_id", None)
        # The model's save() method will auto-calculate length
        return super().create(validated_data)

    def update(self, instance, validated_data):
        """Update edge with proper node references."""
        validated_data.pop("start_node_id", None)
        validated_data.pop("end_node_id", None)
        return super().update(instance, validated_data)
