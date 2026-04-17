# Generated manually for Phase 1 deadlock monitor support.

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ("vda5050", "0009_merge_20260417_1222"),
    ]

    operations = [
        migrations.CreateModel(
            name="DeadlockEvent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("event_id", models.CharField(max_length=100, unique=True)),
                ("order_id", models.CharField(blank=True, max_length=100, null=True)),
                ("node_id", models.CharField(blank=True, max_length=100, null=True)),
                ("sequence_id", models.IntegerField(default=0)),
                ("position", models.JSONField(default=dict)),
                ("agv_set", models.JSONField(default=list)),
                ("conflicted_resources", models.JSONField(default=list)),
                ("stuck_duration_s", models.FloatField(default=0.0)),
                ("details", models.JSONField(default=dict)),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("POTENTIAL", "Potential"),
                            ("RESOLVED", "Resolved"),
                            ("IGNORED", "Ignored"),
                        ],
                        default="POTENTIAL",
                        max_length=20,
                    ),
                ),
                ("detected_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(blank=True, default=None, null=True)),
                ("resolved_at", models.DateTimeField(blank=True, null=True)),
                (
                    "agv",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="deadlock_events",
                        to="vda5050.agv",
                    ),
                ),
            ],
            options={
                "ordering": ["-detected_at"],
            },
        ),
        migrations.AddIndex(
            model_name="deadlockevent",
            index=models.Index(fields=["agv", "status"], name="vda5050_dea_agv_id_08e273_idx"),
        ),
        migrations.AddIndex(
            model_name="deadlockevent",
            index=models.Index(fields=["status", "detected_at"], name="vda5050_dea_status_0f5df0_idx"),
        ),
    ]
