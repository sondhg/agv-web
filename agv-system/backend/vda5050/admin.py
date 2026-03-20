from django.contrib import admin
from .models import AGV, Order, AGVState, InstantAction, GraphEdge, GraphNode


# 1. AGV Admin Configuration
@admin.register(AGV)
class AGVAdmin(admin.ModelAdmin):
    list_display = (
        "manufacturer",
        "serial_number",
        "is_online",
        "last_seen",
        "current_map_id",
    )
    list_filter = ("manufacturer", "is_online")  # Create filters on the right
    search_fields = ("serial_number", "manufacturer")  # Search bar
    readonly_fields = ("last_seen",)  # Prevent manual editing of the timestamp


# 2. Order Admin Configuration
@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("order_id", "agv", "status", "created_at", "timestamp")
    list_filter = ("status", "agv", "created_at")
    search_fields = ("order_id", "agv__serial_number")

    # Display JSON more nicely (if Django version supports it)
    readonly_fields = ("created_at", "updated_at")


# 3. AGVState Admin Configuration (Logs)
@admin.register(AGVState)
class AGVStateAdmin(admin.ModelAdmin):
    list_display = ("agv", "timestamp", "order_id", "driving", "battery_level_display")
    list_filter = ("agv", "driving", "paused", "timestamp")
    search_fields = ("order_id", "agv__serial_number")

    # Display battery level from JSONField
    @admin.display(description="Battery %")
    def battery_level_display(self, obj):
        # Get value from JSONField battery_state
        return obj.battery_state.get("batteryCharge", "N/A")

    # Because there are many logs, set read-only to avoid accidental edits
    def has_add_permission(self, request):
        return False  # Do not allow manual log creation

    def has_change_permission(self, request, obj=None):
        return False  # Do not allow log editing


# 4. InstantAction Admin Configuration
@admin.register(InstantAction)
class InstantActionAdmin(admin.ModelAdmin):
    list_display = ("action_type", "agv", "is_sent", "timestamp")
    list_filter = ("action_type", "agv")
    fields = ("agv", "action_type")


# 5. Map Admin Configuration
@admin.register(GraphNode)
class GraphNodeAdmin(admin.ModelAdmin):
    list_display = ("node_id", "x", "y", "map_id")
    search_fields = ("node_id",)


@admin.register(GraphEdge)
class GraphEdgeAdmin(admin.ModelAdmin):
    list_display = ("start_node", "end_node", "length")
    list_filter = ("map_id",)
