from monitoring.models import BehavioralAlert


ALERT_PATTERNS = {
    "repeated_password_exposure": {
        "title": "Employee likely to leak credentials",
        "severity": "critical",
        "predicted_incident": "credential_leak",
    },
    "risk_score_spike": {
        "title": "Suspicious insider behavior trend",
        "severity": "high",
        "predicted_incident": "insider_threat",
    },
    "excessive_network_activity": {
        "title": "Elevated anomaly trend",
        "severity": "high",
        "predicted_incident": "data_exfiltration",
    },
    "repeated_blocked_security_events": {
        "title": "Repeated risky actions detected",
        "severity": "high",
        "predicted_incident": "policy_violation",
    },
    "unusual_login_time": {
        "title": "Unusual login behavior detected",
        "severity": "medium",
        "predicted_incident": "account_misuse",
    },
}


def generate_predictive_alerts(employee, activity, anomaly_result, risk_profile):
    created_alerts = []
    triggers = anomaly_result["rule_alerts"] or []

    if risk_profile.level == "critical" and "risk_score_spike" not in triggers:
        triggers.append("risk_score_spike")

    for trigger in triggers:
        pattern = ALERT_PATTERNS.get(trigger)
        if not pattern:
            continue

        created_alerts.append(
            BehavioralAlert.objects.create(
                employee=employee,
                title=pattern["title"],
                message=(
                    f"{employee.name} shows {trigger.replace('_', ' ')}. "
                    f"Current risk score is {risk_profile.score} with anomaly score {risk_profile.anomaly_score}."
                ),
                severity=pattern["severity"],
                trigger=trigger,
                predicted_incident=pattern["predicted_incident"],
                metadata={
                    "activity_id": activity.id,
                    "risk_level": risk_profile.level,
                    "dashboard_notification": True,
                    "email_integration_ready": True,
                },
            )
        )

    return created_alerts
