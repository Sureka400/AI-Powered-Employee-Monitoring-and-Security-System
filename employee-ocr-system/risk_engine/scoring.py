from django.conf import settings

from monitoring.models import EmployeeRiskScore


def _risk_level(score):
    thresholds = settings.BEHAVIORAL_ANALYTICS["risk_thresholds"]
    if score >= thresholds["critical"]:
        return EmployeeRiskScore.LEVEL_CRITICAL
    if score >= thresholds["high"]:
        return EmployeeRiskScore.LEVEL_HIGH
    if score >= thresholds["medium"]:
        return EmployeeRiskScore.LEVEL_MEDIUM
    return EmployeeRiskScore.LEVEL_LOW


def calculate_dynamic_risk(activity, anomaly_result):
    keyword_weights = settings.BEHAVIORAL_ANALYTICS["high_risk_keyword_weights"]
    sensitive_component = len(activity.sensitive_findings) * 12
    suspicious_component = sum(keyword_weights.get(keyword, 3) for keyword in activity.suspicious_keywords)
    anomaly_component = min(anomaly_result["anomaly_score"] * 0.35, 35)
    alerts_component = min(activity.security_alerts * 6, 18)
    incidents_component = min((activity.blocked_events + activity.password_exposures) * 5, 20)
    transfer_component = min((activity.downloads + activity.uploads) * 2, 12)

    score = round(
        min(
            100,
            sensitive_component
            + suspicious_component
            + anomaly_component
            + alerts_component
            + incidents_component
            + transfer_component,
        )
    )

    return {
        "score": score,
        "level": _risk_level(score),
        "factors": {
            "sensitive_data": sensitive_component,
            "suspicious_keywords": suspicious_component,
            "anomaly_score": round(anomaly_component, 2),
            "security_alerts": alerts_component,
            "incident_frequency": incidents_component,
            "network_transfer": transfer_component,
        },
    }


def persist_risk_score(employee, activity, anomaly_result, risk_result):
    repeated_violations = activity.password_exposures + activity.blocked_events
    incident_frequency = activity.security_alerts + activity.downloads + activity.uploads

    risk_profile, _ = EmployeeRiskScore.objects.get_or_create(employee=employee)
    risk_profile.score = risk_result["score"]
    risk_profile.level = risk_result["level"]
    risk_profile.anomaly_score = anomaly_result["anomaly_score"]
    risk_profile.incident_frequency = incident_frequency
    risk_profile.repeated_violations = repeated_violations
    risk_profile.last_activity = activity
    risk_profile.factors = risk_result["factors"]
    risk_profile.save()
    return risk_profile
