import os
import pickle
from pathlib import Path

import numpy as np
from sklearn.ensemble import IsolationForest

from analytics.baseline import compare_activity_to_baseline
from analytics.feature_extraction import build_feature_vector
from monitoring.models import AnomalyLog, EmployeeActivity, EmployeeBehaviorProfile


MODEL_DIR = Path(__file__).resolve().parent / "trained_models"
MODEL_DIR.mkdir(parents=True, exist_ok=True)


def _model_path(employee_id):
    return MODEL_DIR / f"employee_{employee_id}_isolation_forest.pkl"


def train_employee_model(employee, activities):
    feature_matrix = np.array([build_feature_vector(activity) for activity in activities], dtype=float)
    if len(feature_matrix) < 5:
        return None

    model = IsolationForest(
        contamination=min(0.2, max(0.05, 1.0 / len(feature_matrix))),
        random_state=42,
        n_estimators=200,
    )
    model.fit(feature_matrix)

    with open(_model_path(employee.id), "wb") as handle:
        pickle.dump(model, handle)

    return model


def load_employee_model(employee_id):
    path = _model_path(employee_id)
    if not path.exists():
        return None
    with open(path, "rb") as handle:
        return pickle.load(handle)


def score_activity(employee, activity):
    profile = EmployeeBehaviorProfile.objects.filter(employee=employee).first()
    model = load_employee_model(employee.id)
    feature_vector = np.array([build_feature_vector(activity)], dtype=float)
    baseline_comparison = compare_activity_to_baseline(profile, activity)

    rule_alerts = []
    if profile:
        if activity.login_hour not in profile.normal_login_hours:
            rule_alerts.append("unusual_login_time")
        if profile.common_applications and activity.application_name and activity.application_name not in profile.common_applications:
            rule_alerts.append("abnormal_application_usage")
        if activity.risk_score > profile.average_risk_score * 1.5 and activity.risk_score > 25:
            rule_alerts.append("risk_score_spike")
        if activity.password_exposures >= 2:
            rule_alerts.append("repeated_password_exposure")
        if activity.network_bytes > max(profile.average_network_bytes * 2, 500000):
            rule_alerts.append("excessive_network_activity")
        if activity.blocked_events > max(profile.average_blocked_events * 2, 2):
            rule_alerts.append("repeated_blocked_security_events")
        rule_alerts.extend(baseline_comparison["flags"])

    if model is None:
        anomaly_score = baseline_comparison["score"]
        is_anomalous = bool(rule_alerts or baseline_comparison["is_deviating"])
    else:
        decision = float(model.decision_function(feature_vector)[0])
        anomaly_score = round((0.5 - decision) * 100, 2)
        anomaly_score = max(anomaly_score, baseline_comparison["score"])
        is_anomalous = bool(
            model.predict(feature_vector)[0] == -1
            or rule_alerts
            or baseline_comparison["is_deviating"]
        )

    rule_alerts = list(dict.fromkeys(rule_alerts))
    anomaly_type = rule_alerts[0] if rule_alerts else "behavioral_outlier"
    severity = "critical" if anomaly_score >= 80 else "high" if anomaly_score >= 60 else "medium" if anomaly_score >= 35 else "low"

    return {
        "anomaly_score": max(anomaly_score, 0.0),
        "is_anomalous": is_anomalous,
        "anomaly_type": anomaly_type,
        "severity": severity,
        "rule_alerts": rule_alerts,
        "baseline_comparison": baseline_comparison,
    }


def persist_anomaly(employee, activity, anomaly_result):
    return AnomalyLog.objects.create(
        employee=employee,
        activity=activity,
        anomaly_type=anomaly_result["anomaly_type"],
        anomaly_score=anomaly_result["anomaly_score"],
        severity=anomaly_result["severity"],
        is_anomalous=anomaly_result["is_anomalous"],
        explanation=", ".join(anomaly_result["rule_alerts"]) or "Isolation Forest score generated from baseline behavior.",
        feature_snapshot={
            "downloads": activity.downloads,
            "uploads": activity.uploads,
            "network_bytes": activity.network_bytes,
            "login_hour": activity.login_hour,
            "risk_score": activity.risk_score,
            "baseline_comparison": anomaly_result.get("baseline_comparison", {}),
        },
    )
