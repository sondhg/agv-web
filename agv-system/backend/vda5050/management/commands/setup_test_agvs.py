"""
Django management command to setup test AGVs for load balancing tests.
Usage: python manage.py setup_test_agvs
"""

from django.core.management.base import BaseCommand
from django.utils import timezone
from vda5050.models import AGV, AGVState


class Command(BaseCommand):
    help = 'Setup test AGVs with initial states for load balancing tests'

    def add_arguments(self, parser):
        parser.add_argument(
            '--count',
            type=int,
            default=7,
            help='Number of AGVs to create (default: 7)'
        )

    def handle(self, *args, **options):
        num_agvs = options['count']
        
        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*60}\n'
            f'🤖 Setting up {num_agvs} test AGVs\n'
            f'{"="*60}\n'
        ))

        # Available nodes for distribution
        available_nodes = [
            "Node_A", "Node_B", "Node_C", "Node_D"
        ]

        created_agvs = []
        
        for i in range(1, num_agvs + 1):
            serial_number = f"AGV_{i:02d}"
            
            # Create or update AGV
            agv, created = AGV.objects.update_or_create(
                manufacturer='TestManufacturer',
                serial_number=serial_number,
                defaults={
                    'is_online': True,
                    'description': f'Test AGV #{i} for load balancing tests',
                    'protocol_version': '2.1.0',
                }
            )
            
            # Create initial state
            current_node = available_nodes[i % len(available_nodes)]
            battery_percent = 100 - (i * 5)  # Đa dạng battery: 95%, 90%, 85%...
            
            state = AGVState.objects.create(
                agv=agv,
                timestamp=timezone.now(),
                header_id=0,
                last_node_id=current_node,
                last_node_sequence_id=0,
                driving=False,
                paused=False,
                operating_mode='AUTOMATIC',
                battery_state={
                    'batteryCharge': battery_percent,
                    'batteryVoltage': 48.0,
                    'charging': False
                },
                agv_position={
                    'x': 0.0,
                    'y': 0.0,
                    'theta': 0.0,
                    'mapId': 'default_map'
                },
                errors=[],
                safety_state={'eStop': 'NONE', 'fieldViolation': False},
                loads=[],
                information={}
            )
            
            action = "Created" if created else "Updated"
            self.stdout.write(
                f'  ✅ {action} {serial_number}: '
                f'Node={current_node}, Battery={battery_percent}%'
            )
            
            created_agvs.append(agv)

        self.stdout.write(self.style.SUCCESS(
            f'\n{"="*60}\n'
            f'✅ Successfully setup {len(created_agvs)} AGVs\n'
            f'{"="*60}\n'
        ))
        
        # Show summary
        self.stdout.write('\n📋 Summary:')
        for agv in created_agvs:
            state = AGVState.objects.filter(agv=agv).latest('timestamp')
            self.stdout.write(
                f'  🤖 {agv.serial_number}: '
                f'{state.last_node_id} | '
                f'{state.battery_state.get("batteryCharge", 0)}% | '
                f'{"🟢 Online" if agv.is_online else "🔴 Offline"}'
            )
        
        self.stdout.write(self.style.SUCCESS('\n✅ Ready for testing!\n'))
