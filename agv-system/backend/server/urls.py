from django.contrib import admin
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from vda5050.views import AGVViewSet, OrderViewSet, TaskViewSet

# Tạo Router tự động sinh URL
router = DefaultRouter()
router.register(r"agvs", AGVViewSet)
router.register(r"orders", OrderViewSet)
router.register(r"tasks", TaskViewSet, basename="tasks")

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/", include(router.urls)),
]
