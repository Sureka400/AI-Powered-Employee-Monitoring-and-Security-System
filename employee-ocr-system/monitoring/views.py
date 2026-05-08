import json

from django.db.models import Count
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .models import AnomalyLog, BehavioralAlert, Employee, EmployeeActivity, EmployeeRiskScore
from .services import ingest_employee_activity, run_behavioral_prediction


def _read_json_body(request):
    return json.loads(request.body.decode("utf-8") or "{}")


@csrf_exempt
@require_POST
def ingest_activity_view(request):
    payload = _read_json_body(request)
    result = ingest_employee_activity(payload)
    if result["status"] != "stored":
        return JsonResponse(result, status=202)

    activity = EmployeeActivity.objects.select_related("employee").get(id=result["activity_id"])
    prediction = run_behavioral_prediction(activity)
    return JsonResponse(
        {
            "status": "processed",
            "activity_id": activity.id,
            "employee_code": activity.employee.employee_code,
            "risk_score": prediction["risk_profile"].score,
            "risk_level": prediction["risk_profile"].level,
            "alerts_created": len(prediction["alerts"]),
        }
    )


@require_GET
def employee_behavior_trends_view(request):
    data = []
    for employee in Employee.objects.filter(is_active=True).select_related("behavior_profile"):
        profile = getattr(employee, "behavior_profile", None)
        if not profile:
            continue
        data.append(
            {
                "employee_code": employee.employee_code,
                "employee_name": employee.name,
                "department": employee.department,
                "average_active_hour": round(profile.average_active_hour, 2),
                "normal_login_hours": profile.normal_login_hours,
                "common_applications": profile.common_applications,
                "average_keyword_frequency": round(profile.average_keyword_frequency, 2),
                "average_risk_score": round(profile.average_risk_score, 2),
                "baseline_workflow": profile.baseline_workflow,
            }
        )
    return JsonResponse({"employees": data})


@require_GET
def anomaly_history_view(request):
    items = [
        {
            "employee_code": anomaly.employee.employee_code,
            "anomaly_type": anomaly.anomaly_type,
            "anomaly_score": anomaly.anomaly_score,
            "severity": anomaly.severity,
            "is_anomalous": anomaly.is_anomalous,
            "detected_at": anomaly.detected_at.isoformat(),
            "explanation": anomaly.explanation,
        }
        for anomaly in AnomalyLog.objects.select_related("employee")[:100]
    ]
    return JsonResponse({"anomalies": items})


@require_GET
def risk_score_chart_view(request):
    items = [
        {
            "employee_code": score.employee.employee_code,
            "employee_name": score.employee.name,
            "score": score.score,
            "level": score.level,
            "anomaly_score": score.anomaly_score,
            "updated_at": score.updated_at.isoformat(),
            "factors": score.factors,
        }
        for score in EmployeeRiskScore.objects.select_related("employee")
    ]
    return JsonResponse({"risk_scores": items})


@require_GET
def alert_timeline_view(request):
    items = [
        {
            "employee_code": alert.employee.employee_code,
            "title": alert.title,
            "severity": alert.severity,
            "status": alert.status,
            "predicted_incident": alert.predicted_incident,
            "created_at": alert.created_at.isoformat(),
        }
        for alert in BehavioralAlert.objects.select_related("employee")[:100]
    ]
    return JsonResponse({"alerts": items})


@require_GET
def suspicious_activity_summary_view(request):
    high_risk = EmployeeRiskScore.objects.filter(level__in=["high", "critical"]).count()
    alert_counts = BehavioralAlert.objects.values("severity").annotate(total=Count("id")).order_by("-total")
    anomaly_counts = AnomalyLog.objects.values("anomaly_type").annotate(total=Count("id")).order_by("-total")[:10]

    return JsonResponse(
        {
            "high_risk_employees": high_risk,
            "open_alerts": BehavioralAlert.objects.filter(status="open").count(),
            "critical_alerts": BehavioralAlert.objects.filter(severity="critical", status="open").count(),
            "top_alert_categories": list(alert_counts),
            "top_anomalies": list(anomaly_counts),
            "example_dashboard_response": {
                "trend": "elevated insider risk",
                "summary": "Repeated risky actions and abnormal login patterns are clustered around a small employee subset.",
            },
        }
    )
