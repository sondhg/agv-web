from rest_framework import serializers
from .models import AGV, Order, AGVState


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
