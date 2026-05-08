from django.urls import path

from .views import (
    alert_timeline_view,
    anomaly_history_view,
    employee_behavior_trends_view,
    ingest_activity_view,
    risk_score_chart_view,
    suspicious_activity_summary_view,
)

urlpatterns = [
    path("activities/ingest/", ingest_activity_view),
    path("dashboard/behavior-trends/", employee_behavior_trends_view),
    path("dashboard/anomalies/", anomaly_history_view),
    path("dashboard/risk-scores/", risk_score_chart_view),
    path("dashboard/alerts/", alert_timeline_view),
    path("dashboard/suspicious-summary/", suspicious_activity_summary_view),
]