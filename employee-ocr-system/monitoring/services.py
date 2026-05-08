from django.db.models import Avg
from django.utils import timezone

from alerts.generator import generate_predictive_alerts
from analytics.baseline import update_behavior_profile
from analytics.feature_extraction import derive_behavioral_metrics
from anomaly_detection.engine import persist_anomaly, score_activity, train_employee_model
from monitoring.models import Employee, EmployeeActivity
from risk_engine.scoring import calculate_dynamic_risk, persist_risk_score


def ingest_employee_activity(payload):
    employee, _ = Employee.objects.get_or_create(
        employee_code=payload["employee_code"],
        defaults={
            "name": payload.get("employee_name", payload["employee_code"]),
            "department": payload.get("department", ""),
            "email": payload.get("email", ""),
        },
    )

    metrics = derive_behavioral_metrics(payload)
    if not metrics["is_meaningful"]:
        return {"status": "skipped", "reason": "system_noise_detected"}

    activity = EmployeeActivity.objects.create(
        employee=employee,
        captured_at=payload.get("captured_at", timezone.now()),
        image_path=payload.get("image_path", ""),
        source=payload.get("source", "ocr_watcher"),
        application_name=payload.get("application_name", ""),
        window_title=payload.get("window_title", ""),
        workflow_label=payload.get("workflow_label", ""),
        login_hour=payload.get("login_hour", timezone.localtime().hour),
        active_minutes=payload.get("active_minutes", 0.0),
        idle_minutes=payload.get("idle_minutes", 0.0),
        ocr_text=payload.get("ocr_text", ""),
        ocr_keyword_hits=metrics["workflow_hits"],
        sensitive_findings=metrics["sensitive_findings"],
        suspicious_keywords=metrics["keyword_hits"],
        downloads=payload.get("downloads", 0),
        uploads=payload.get("uploads", 0),
        blocked_events=payload.get("blocked_events", 0),
        security_alerts=payload.get("security_alerts", 0),
        password_exposures=max(payload.get("password_exposures", 0), metrics["password_exposures"]),
        network_bytes=payload.get("network_bytes", 0),
        risk_score=payload.get("risk_score", 0.0),
        metadata=payload.get("metadata", {}),
    )

    return {"status": "stored", "employee_id": employee.id, "activity_id": activity.id}


def train_behavioral_baseline(employee):
    activities = list(employee.activities.order_by("-captured_at")[:200])
    if not activities:
        return None

    profile = update_behavior_profile(employee, activities)
    train_employee_model(employee, activities)
    return profile


def run_behavioral_prediction(activity):
    employee = activity.employee
    if not hasattr(employee, "behavior_profile"):
        train_behavioral_baseline(employee)

    anomaly_result = score_activity(employee, activity)
    anomaly_log = persist_anomaly(employee, activity, anomaly_result)
    risk_result = calculate_dynamic_risk(activity, anomaly_result)
    risk_profile = persist_risk_score(employee, activity, anomaly_result, risk_result)
    alerts = generate_predictive_alerts(employee, activity, anomaly_result, risk_profile)

    return {
        "anomaly": anomaly_log,
        "risk_profile": risk_profile,
        "alerts": alerts,
    }


def train_all_employee_profiles():
    results = []
    for employee in Employee.objects.filter(is_active=True):
        profile = train_behavioral_baseline(employee)
        if profile:
            results.append({"employee_code": employee.employee_code, "trained_samples": profile.trained_samples})
    return results
