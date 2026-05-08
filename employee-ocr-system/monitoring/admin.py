from django.contrib import admin

from .models import (
    AnomalyLog,
    BehavioralAlert,
    Employee,
    EmployeeActivity,
    EmployeeBehaviorProfile,
    EmployeeRiskScore,
)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ("employee_code", "name", "department", "is_active")
    search_fields = ("employee_code", "name", "department")


@admin.register(EmployeeActivity)
class EmployeeActivityAdmin(admin.ModelAdmin):
    list_display = ("employee", "captured_at", "application_name", "risk_score", "blocked_events")
    list_filter = ("application_name", "captured_at")
    search_fields = ("employee__name", "window_title", "application_name", "ocr_text")


@admin.register(EmployeeBehaviorProfile)
class EmployeeBehaviorProfileAdmin(admin.ModelAdmin):
    list_display = ("employee", "last_trained_at", "average_active_hour", "average_risk_score")


@admin.register(EmployeeRiskScore)
class EmployeeRiskScoreAdmin(admin.ModelAdmin):
    list_display = ("employee", "score", "level", "updated_at")
    list_filter = ("level",)


@admin.register(BehavioralAlert)
class BehavioralAlertAdmin(admin.ModelAdmin):
    list_display = ("employee", "title", "severity", "status", "created_at")
    list_filter = ("severity", "status", "created_at")


@admin.register(AnomalyLog)
class AnomalyLogAdmin(admin.ModelAdmin):
    list_display = ("employee", "anomaly_type", "severity", "anomaly_score", "detected_at")
    list_filter = ("anomaly_type", "severity", "detected_at")
