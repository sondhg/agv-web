from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import gettext_lazy as _


# ============================================
# FLEET MANAGEMENT
# ============================================
class AGV(models.Model):
    """
    Represent a physical AGV.
    Topic MQTT: uagv/v2/{manufacturer}/{serial_number}/...
    """

    manufacturer = models.CharField(
        max_length=100, help_text="Manufacturer (e.g., KUKA)"
    )
    serial_number = models.CharField(
        max_length=100, help_text="Unique serial number of the AGV"
    )
    description = models.TextField(blank=True, null=True)

    # Connection & Status Information
    is_online = models.BooleanField(default=False, help_text="MQTT connection status")
    last_seen = models.DateTimeField(auto_now=True)
    protocol_version = models.CharField(
        max_length=20,
        blank=True,
        null=True,
        help_text="Supported VDA version (e.g., 2.1.0)",
    )
    current_map_id = models.CharField(
        max_length=100, blank=True, null=True, help_text="Current map in use by the AGV"
    )

    class Meta:
        unique_together = ("manufacturer", "serial_number")  # This pair must be unique
        verbose_name = "AGV"
        verbose_name_plural = "AGV Fleet"

    def __str__(self):
        return f"{self.manufacturer} - {self.serial_number}"


# ============================================
# ORDER MANAGEMENT
# ============================================
class Order(models.Model):
    """
    Store transport orders.
    Nodes/edges data is stored in JSONB format to ensure performance and compliance with VDA5050 standards.
    """

    # Link to the AGV
    agv = models.ForeignKey(AGV, on_delete=models.CASCADE, related_name="orders")

    # --- VDA 5050 Identifiers ---
    header_id = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)
    order_id = models.CharField(
        max_length=100, unique=True, help_text="Unique order ID from VDA"
    )
    order_update_id = models.IntegerField(
        default=0, help_text="Used for updating/extending orders"
    )
    zone_set_id = models.CharField(max_length=100, blank=True, null=True)

    # --- CORE DATA (JSONB Power) ---
    # Storing the entire Node/Edge arrays as JSONB
    nodes = models.JSONField(default=list, help_text="List of Nodes (with Actions)")
    edges = models.JSONField(default=list, help_text="List of Edges")

    # --- Internal Management ---
    class OrderStatus(models.TextChoices):
        CREATED = "CREATED", _("Newly Created")
        SENT = "SENT", _("Sent to AGV")
        ACTIVE = "ACTIVE", _("Active")
        COMPLETED = "COMPLETED", _("Completed")
        REJECTED = "REJECTED", _("Rejected by AGV")
        CANCELLED = "CANCELLED", _("Cancelled")
        FAILED = "FAILED", _("Failed")
        QUEUED = "QUEUED", _("Queued for Sending")

    status = models.CharField(
        max_length=20, choices=OrderStatus.choices, default=OrderStatus.CREATED
    )

    # Rejection reason (Taken from state.errors)
    rejection_reason = models.TextField(
        blank=True, null=True, help_text="Reason why the AGV rejected this order"
    )

    # Management metadata
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.order_id} -> {self.agv}"


# ============================================
# STATE & TELEMETRY
# ============================================
class AGVState(models.Model):
    """
    Track the entire history of states sent by the AGV.
    Used for plotting graphs and investigating incidents.
    """

    agv = models.ForeignKey(AGV, on_delete=models.CASCADE, related_name="states")

    # --- VDA Context ---
    header_id = models.IntegerField()
    timestamp = models.DateTimeField(help_text="Time when the AGV created the packet")
    received_at = models.DateTimeField(
        auto_now_add=True, help_text="Time when the Server received it"
    )

    order_id = models.CharField(max_length=100, blank=True, null=True)
    last_node_id = models.CharField(max_length=100, blank=True, null=True)
    last_node_sequence_id = models.IntegerField(default=0)
    driving = models.BooleanField(default=False)
    paused = models.BooleanField(default=False)
    operating_mode = models.CharField(max_length=20, blank=True, null=True)

    # --- COMPONENT STATUS (JSONB) ---
    # Storing various component states as JSONB for flexibility
    battery_state = models.JSONField(
        default=dict, help_text="{charge, voltage, health...}"
    )
    agv_position = models.JSONField(
        default=dict, null=True, help_text="{x, y, theta, mapId...}"
    )
    velocity = models.JSONField(default=dict, null=True, help_text="{vx, vy, omega}")

    # --- SAFETY & ERRORS ---
    safety_state = models.JSONField(default=dict, help_text="{eStop, fieldViolation}")
    errors = models.JSONField(default=list, help_text="List of current errors")

    # --- LOGISTICS ---
    loads = models.JSONField(default=list, help_text="Current loads being carried")
    information = models.JSONField(
        default=dict, null=True, help_text="Other debug information"
    )

    class Meta:
        ordering = ["-timestamp"]  # Newest first
        indexes = [
            models.Index(fields=["agv", "timestamp"]),  # Optimize search by time
        ]

    def __str__(self):
        return f"State {self.agv} @ {self.timestamp}"


# ============================================
# INSTANT ACTIONS
# ============================================
class InstantAction(models.Model):
    """
    Represent instant actions sent to the AGV outside of orders.
    Topic: uagv/v2/{manufacturer}/{serial_number}/instantActions
    """

    ACTION_CHOICES = [
        ("startPause", "Pause"),
        ("stopPause", "Resume"),
        ("cancelOrder", "Cancel"),
    ]

    agv = models.ForeignKey(
        AGV, on_delete=models.CASCADE, related_name="instant_actions"
    )
    header_id = models.IntegerField(default=0)
    timestamp = models.DateTimeField(auto_now_add=True)

    # Action Type using VDA5050 standard
    action_type = models.CharField(max_length=50, choices=ACTION_CHOICES)
    action_id = models.CharField(
        max_length=100, unique=True, help_text="Unique action ID"
    )

    # Parameters (if any, e.g., reason)
    action_parameters = models.JSONField(default=list, blank=True)

    # Sent status
    is_sent = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        User, on_delete=models.SET_NULL, null=True, blank=True
    )

    def __str__(self):
        return f"{self.action_type} -> {self.agv}"

    def save(self, *args, **kwargs):
        # Auto-generate action_id if not provided
        if not self.action_id:
            import uuid

            self.action_id = f"ACT_{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)


# ============================================
# TOPOLOGY & MAP
# ============================================
class GraphNode(models.Model):
    """Store landmark points on the map (e.g., Charging Station, Warehouse A, Warehouse B...)"""

    node_id = models.CharField(
        max_length=100, unique=True, help_text="Unique identifier for the point"
    )
    map_id = models.CharField(max_length=100, default="map_1")
    x = models.FloatField()
    y = models.FloatField()
    theta = models.FloatField(
        default=0.0, help_text="Orientation angle of the vehicle at this point"
    )
    description = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f"{self.node_id} ({self.x}, {self.y})"


class GraphEdge(models.Model):
    """Store edges between two points (Vehicle can travel along these edges)"""

    start_node = models.ForeignKey(
        GraphNode, related_name="outgoing_edges", on_delete=models.CASCADE
    )
    end_node = models.ForeignKey(
        GraphNode, related_name="incoming_edges", on_delete=models.CASCADE
    )
    map_id = models.CharField(max_length=100, default="map_1")

    # Weight (for shortest path calculation)
    length = models.FloatField(
        null=True,
        blank=True,
        help_text="Length of the edge (m) - auto-calculated if not provided",
    )
    max_velocity = models.FloatField(
        default=1.0, help_text="Maximum allowed velocity (m/s)"
    )

    # Direction (True: one-way, False: two-way)
    is_directed = models.BooleanField(default=True)

    class Meta:
        unique_together = ("start_node", "end_node")

    def save(self, *args, **kwargs):
        # Auto-calculate Euclidean distance if not provided
        if self.length is None:
            import math

            dx = self.end_node.x - self.start_node.x
            dy = self.end_node.y - self.start_node.y
            self.length = math.sqrt(dx * dx + dy * dy)
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.start_node.node_id} -> {self.end_node.node_id}"
