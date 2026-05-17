from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from vda5050.views import (
    AGVViewSet,
    OrderViewSet,
    TaskViewSet,
    GraphNodeViewSet,
    GraphEdgeViewSet,
    GraphViewSet,
    DashboardViewSet,
)

# Create Router to automatically generate URLs
router = DefaultRouter()
router.register(r"agvs", AGVViewSet)
router.register(r"orders", OrderViewSet)
router.register(r"tasks", TaskViewSet, basename="tasks")

# Graph management endpoints
router.register(r"graph/nodes", GraphNodeViewSet, basename="graph-nodes")
router.register(r"graph/edges", GraphEdgeViewSet, basename="graph-edges")
router.register(r"graph", GraphViewSet, basename="graph")

# Dashboard endpoints
router.register(r"dashboard", DashboardViewSet, basename="dashboard")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
]
