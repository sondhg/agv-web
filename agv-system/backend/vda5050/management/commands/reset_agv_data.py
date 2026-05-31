import sys
from django.core.management.base import BaseCommand
from django.db import transaction
from vda5050.models import (
    AGV,
    Order,
    AGVState,
    DeadlockEvent,
    NodeReservation,
    EdgeReservation,
    InstantAction,
    GraphNode,
    GraphEdge,
)

class Command(BaseCommand):
    help = "Safely deletes all AGV and map data to provide a clean state without deleting users."

    def handle(self, *args, **options):
        self.stdout.write(self.style.WARNING("Starting database cleanup for AGV and Map data..."))
        
        try:
            with transaction.atomic():
                # Delete operational data
                Order.objects.all().delete()
                AGVState.objects.all().delete()
                DeadlockEvent.objects.all().delete()
                NodeReservation.objects.all().delete()
                EdgeReservation.objects.all().delete()
                InstantAction.objects.all().delete()
                AGV.objects.all().delete()
                
                # Delete map data
                GraphEdge.objects.all().delete()
                GraphNode.objects.all().delete()
                
            self.stdout.write(self.style.SUCCESS("Successfully cleared all AGV and Map data! Your user accounts are safe."))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error occurred during cleanup: {e}"))
            sys.exit(1)
