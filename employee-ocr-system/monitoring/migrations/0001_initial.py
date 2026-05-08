from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Employee",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("employee_code", models.CharField(max_length=64, unique=True)),
                ("name", models.CharField(max_length=255)),
                ("department", models.CharField(blank=True, max_length=128)),
                ("email", models.EmailField(blank=True, max_length=254)),
                ("is_active", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="EmployeeActivity",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("captured_at", models.DateTimeField(db_index=True, default=django.utils.timezone.now)),
                ("image_path", models.CharField(blank=True, max_length=512)),
                ("source", models.CharField(default="ocr_watcher", max_length=64)),
                ("application_name", models.CharField(blank=True, max_length=128)),
                ("window_title", models.CharField(blank=True, max_length=255)),
                ("workflow_label", models.CharField(blank=True, max_length=128)),
                ("login_hour", models.PositiveSmallIntegerField(default=0)),
                ("active_minutes", models.FloatField(default=0.0)),
                ("idle_minutes", models.FloatField(default=0.0)),
                ("ocr_text", models.TextField(blank=True)),
                ("ocr_keyword_hits", models.JSONField(blank=True, default=list)),
                ("sensitive_findings", models.JSONField(blank=True, default=list)),
                ("suspicious_keywords", models.JSONField(blank=True, default=list)),
                ("downloads", models.PositiveIntegerField(default=0)),
                ("uploads", models.PositiveIntegerField(default=0)),
                ("blocked_events", models.PositiveIntegerField(default=0)),
                ("security_alerts", models.PositiveIntegerField(default=0)),
                ("password_exposures", models.PositiveIntegerField(default=0)),
                ("network_bytes", models.BigIntegerField(default=0)),
                ("risk_score", models.FloatField(default=0.0)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                (
                    "employee",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="activities", to="monitoring.employee"),
                ),
            ],
            options={"ordering": ["-captured_at"]},
        ),
        migrations.CreateModel(
            name="EmployeeBehaviorProfile",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("average_active_hour", models.FloatField(default=0.0)),
                ("common_applications", models.JSONField(blank=True, default=list)),
                ("normal_login_hours", models.JSONField(blank=True, default=list)),
                ("average_keyword_frequency", models.FloatField(default=0.0)),
                ("average_risk_score", models.FloatField(default=0.0)),
                ("average_downloads", models.FloatField(default=0.0)),
                ("average_uploads", models.FloatField(default=0.0)),
                ("average_blocked_events", models.FloatField(default=0.0)),
                ("average_network_bytes", models.FloatField(default=0.0)),
                ("average_idle_minutes", models.FloatField(default=0.0)),
                ("baseline_workflow", models.JSONField(blank=True, default=dict)),
                ("model_version", models.CharField(default="v1", max_length=32)),
                ("trained_samples", models.PositiveIntegerField(default=0)),
                ("last_trained_at", models.DateTimeField(blank=True, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "employee",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="behavior_profile", to="monitoring.employee"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="BehavioralAlert",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=255)),
                ("message", models.TextField()),
                ("severity", models.CharField(max_length=16)),
                ("status", models.CharField(choices=[("open", "Open"), ("acknowledged", "Acknowledged"), ("resolved", "Resolved")], default="open", max_length=16)),
                ("alert_type", models.CharField(default="predictive", max_length=64)),
                ("trigger", models.CharField(blank=True, max_length=128)),
                ("predicted_incident", models.CharField(blank=True, max_length=128)),
                ("metadata", models.JSONField(blank=True, default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "employee",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alerts", to="monitoring.employee"),
                ),
            ],
        ),
        migrations.CreateModel(
            name="AnomalyLog",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("anomaly_type", models.CharField(max_length=64)),
                ("anomaly_score", models.FloatField()),
                ("severity", models.CharField(max_length=16)),
                ("is_anomalous", models.BooleanField(default=False)),
                ("explanation", models.TextField(blank=True)),
                ("feature_snapshot", models.JSONField(blank=True, default=dict)),
                ("detected_at", models.DateTimeField(default=django.utils.timezone.now)),
                (
                    "activity",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name="anomalies", to="monitoring.employeeactivity"),
                ),
                (
                    "employee",
                    models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="anomalies", to="monitoring.employee"),
                ),
            ],
            options={"ordering": ["-detected_at"]},
        ),
        migrations.CreateModel(
            name="EmployeeRiskScore",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("score", models.PositiveSmallIntegerField(default=0)),
                ("level", models.CharField(choices=[("low", "Low"), ("medium", "Medium"), ("high", "High"), ("critical", "Critical")], default="low", max_length=16)),
                ("anomaly_score", models.FloatField(default=0.0)),
                ("incident_frequency", models.FloatField(default=0.0)),
                ("repeated_violations", models.PositiveIntegerField(default=0)),
                ("factors", models.JSONField(blank=True, default=dict)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "employee",
                    models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name="risk_profile", to="monitoring.employee"),
                ),
                (
                    "last_activity",
                    models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="risk_snapshots", to="monitoring.employeeactivity"),
                ),
            ],
        ),
    ]
