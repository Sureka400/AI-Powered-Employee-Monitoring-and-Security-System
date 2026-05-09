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
    "baseline_login_deviation": {
        "title": "Login pattern deviates from baseline",
        "severity": "medium",
        "predicted_incident": "account_misuse",
    },
    "baseline_risk_deviation": {
        "title": "Risk behavior exceeds learned baseline",
        "severity": "high",
        "predicted_incident": "insider_threat",
    },
    "baseline_application_deviation": {
        "title": "Unrecognized application pattern detected",
        "severity": "high",
        "predicted_incident": "policy_violation",
    },
    "baseline_workflow_deviation": {
        "title": "Workflow pattern deviates from normal activity",
        "severity": "high",
        "predicted_incident": "insider_threat",
    },
    "baseline_keyword_deviation": {
        "title": "New high-risk keywords detected against baseline",
        "severity": "high",
        "predicted_incident": "credential_leak",
    },
    "baseline_transfer_deviation": {
        "title": "Transfer activity exceeds learned baseline",
        "severity": "high",
        "predicted_incident": "data_exfiltration",
    },
    "baseline_network_deviation": {
        "title": "Network usage exceeds learned baseline",
        "severity": "high",
        "predicted_incident": "data_exfiltration",
    },
}


def generate_predictive_alerts(employee, activity, anomaly_result, risk_profile, predictive_result):
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
                predicted_threat_level=predictive_result["predicted_threat_level"],
                confidence_score=predictive_result["confidence_score"],
                metadata={
                    "activity_id": activity.id,
                    "risk_level": risk_profile.level,
                    "dashboard_notification": True,
                    "email_integration_ready": True,
                    "baseline_comparison": anomaly_result.get("baseline_comparison", {}),
                },
            )
        )

    if predictive_result["should_alert"]:
        created_alerts.append(
            BehavioralAlert.objects.create(
                employee=employee,
                title="Predictive insider threat alert",
                message=predictive_result["alert_message"],
                severity=predictive_result["predicted_threat_level"],
                alert_type="predictive_trend",
                trigger="risk_trend_forecast",
                predicted_incident=predictive_result["predicted_incident"],
                predicted_threat_level=predictive_result["predicted_threat_level"],
                confidence_score=predictive_result["confidence_score"],
                metadata={
                    "activity_id": activity.id,
                    "risk_level": risk_profile.level,
                    "trend_slope": predictive_result["trend_slope"],
                    "predicted_next_score": predictive_result["predicted_next_score"],
                    "historical_samples": predictive_result["historical_samples"],
                    "baseline_deviation_score": predictive_result["baseline_deviation_score"],
                    "fit_quality": predictive_result["fit_quality"],
                    "open_predictive_alerts": predictive_result["open_predictive_alerts"],
                    "dashboard_notification": True,
                    "email_integration_ready": True,
                },
            )
        )

    return created_alerts
