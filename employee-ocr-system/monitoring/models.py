from django.db import models
from django.utils import timezone


class Employee(models.Model):
    employee_code = models.CharField(max_length=64, unique=True)
    name = models.CharField(max_length=255)
    department = models.CharField(max_length=128, blank=True)
    email = models.EmailField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.employee_code} - {self.name}"


class EmployeeActivity(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="activities")
    captured_at = models.DateTimeField(default=timezone.now, db_index=True)
    image_path = models.CharField(max_length=512, blank=True)
    source = models.CharField(max_length=64, default="ocr_watcher")
    application_name = models.CharField(max_length=128, blank=True)
    window_title = models.CharField(max_length=255, blank=True)
    workflow_label = models.CharField(max_length=128, blank=True)
    login_hour = models.PositiveSmallIntegerField(default=0)
    active_minutes = models.FloatField(default=0.0)
    idle_minutes = models.FloatField(default=0.0)
    ocr_text = models.TextField(blank=True)
    ocr_keyword_hits = models.JSONField(default=list, blank=True)
    sensitive_findings = models.JSONField(default=list, blank=True)
    suspicious_keywords = models.JSONField(default=list, blank=True)
    downloads = models.PositiveIntegerField(default=0)
    uploads = models.PositiveIntegerField(default=0)
    blocked_events = models.PositiveIntegerField(default=0)
    security_alerts = models.PositiveIntegerField(default=0)
    password_exposures = models.PositiveIntegerField(default=0)
    network_bytes = models.BigIntegerField(default=0)
    risk_score = models.FloatField(default=0.0)
    metadata = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-captured_at"]


class EmployeeBehaviorProfile(models.Model):
    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="behavior_profile")
    average_active_hour = models.FloatField(default=0.0)
    average_login_hour = models.FloatField(default=0.0)
    common_applications = models.JSONField(default=list, blank=True)
    common_keywords = models.JSONField(default=list, blank=True)
    normal_login_hours = models.JSONField(default=list, blank=True)
    average_keyword_frequency = models.FloatField(default=0.0)
    average_risk_score = models.FloatField(default=0.0)
    average_downloads = models.FloatField(default=0.0)
    average_uploads = models.FloatField(default=0.0)
    average_blocked_events = models.FloatField(default=0.0)
    average_network_bytes = models.FloatField(default=0.0)
    average_idle_minutes = models.FloatField(default=0.0)
    baseline_workflow = models.JSONField(default=dict, blank=True)
    normal_activity_patterns = models.JSONField(default=dict, blank=True)
    model_version = models.CharField(max_length=32, default="v1")
    trained_samples = models.PositiveIntegerField(default=0)
    last_trained_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class EmployeeRiskScore(models.Model):
    LEVEL_LOW = "low"
    LEVEL_MEDIUM = "medium"
    LEVEL_HIGH = "high"
    LEVEL_CRITICAL = "critical"
    LEVEL_CHOICES = [
        (LEVEL_LOW, "Low"),
        (LEVEL_MEDIUM, "Medium"),
        (LEVEL_HIGH, "High"),
        (LEVEL_CRITICAL, "Critical"),
    ]

    employee = models.OneToOneField(Employee, on_delete=models.CASCADE, related_name="risk_profile")
    score = models.PositiveSmallIntegerField(default=0)
    level = models.CharField(max_length=16, choices=LEVEL_CHOICES, default=LEVEL_LOW)
    anomaly_score = models.FloatField(default=0.0)
    incident_frequency = models.FloatField(default=0.0)
    repeated_violations = models.PositiveIntegerField(default=0)
    last_activity = models.ForeignKey(
        EmployeeActivity,
        on_delete=models.SET_NULL,
        related_name="risk_snapshots",
        null=True,
        blank=True,
    )
    factors = models.JSONField(default=dict, blank=True)
    updated_at = models.DateTimeField(auto_now=True)


class BehavioralAlert(models.Model):
    STATUS_OPEN = "open"
    STATUS_ACKNOWLEDGED = "acknowledged"
    STATUS_RESOLVED = "resolved"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Open"),
        (STATUS_ACKNOWLEDGED, "Acknowledged"),
        (STATUS_RESOLVED, "Resolved"),
    ]

    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="alerts")
    title = models.CharField(max_length=255)
    message = models.TextField()
    severity = models.CharField(max_length=16)
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=STATUS_OPEN)
    alert_type = models.CharField(max_length=64, default="predictive")
    trigger = models.CharField(max_length=128, blank=True)
    predicted_incident = models.CharField(max_length=128, blank=True)
    predicted_threat_level = models.CharField(max_length=16, blank=True)
    confidence_score = models.FloatField(default=0.0)
    metadata = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)


class AnomalyLog(models.Model):
    employee = models.ForeignKey(Employee, on_delete=models.CASCADE, related_name="anomalies")
    activity = models.ForeignKey(
        EmployeeActivity,
        on_delete=models.CASCADE,
        related_name="anomalies",
        null=True,
        blank=True,
    )
    anomaly_type = models.CharField(max_length=64)
    anomaly_score = models.FloatField()
    severity = models.CharField(max_length=16)
    is_anomalous = models.BooleanField(default=False)
    explanation = models.TextField(blank=True)
    feature_snapshot = models.JSONField(default=dict, blank=True)
    detected_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-detected_at"]
