from django.core.management.base import BaseCommand

from vda5050.models import DeadlockEvent


class Command(BaseCommand):
    help = "List AGVs with open potential stuck/deadlock events"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Maximum number of events to print",
        )

    def handle(self, *args, **options):
        limit = max(1, int(options.get("limit", 20)))
        events = (
            DeadlockEvent.objects.filter(status=DeadlockEvent.Status.POTENTIAL)
            .select_related("agv")
            .order_by("-detected_at")[:limit]
        )

        if not events:
            self.stdout.write(self.style.SUCCESS("No potential stuck events."))
            return

        self.stdout.write(self.style.WARNING(f"Potential stuck events: {len(events)}"))
        for ev in events:
            self.stdout.write(
                (
                    f"- event_id={ev.event_id} agv={ev.agv.serial_number} "
                    f"order={ev.order_id or '-'} node={ev.node_id or '-'} "
                    f"seq={ev.sequence_id} stuck={ev.stuck_duration_s:.2f}s "
                    f"detected_at={ev.detected_at.isoformat()}"
                )
            )
