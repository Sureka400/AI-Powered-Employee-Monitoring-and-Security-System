from sklearn.linear_model import LinearRegression

from monitoring.models import AnomalyLog, BehavioralAlert, EmployeeRiskScore


def _threat_rank(level):
    order = {
        EmployeeRiskScore.LEVEL_LOW: 0,
        EmployeeRiskScore.LEVEL_MEDIUM: 1,
        EmployeeRiskScore.LEVEL_HIGH: 2,
        EmployeeRiskScore.LEVEL_CRITICAL: 3,
    }
    return order.get(level, 0)


def _score_to_level(score):
    if score >= 80:
        return EmployeeRiskScore.LEVEL_CRITICAL
    if score >= 60:
        return EmployeeRiskScore.LEVEL_HIGH
    if score >= 35:
        return EmployeeRiskScore.LEVEL_MEDIUM
    return EmployeeRiskScore.LEVEL_LOW


def _predicted_incident(signals):
    if "baseline_keyword_deviation" in signals or "repeated_password_exposure" in signals:
        return "credential_leak"
    if "baseline_network_deviation" in signals or "excessive_network_activity" in signals:
        return "data_exfiltration"
    if "baseline_login_deviation" in signals or "unusual_login_time" in signals:
        return "account_misuse"
    return "insider_threat"


def _trend_series(employee, current_activity, anomaly_result):
    recent_activities = list(
        employee.activities.exclude(id=current_activity.id).order_by("-captured_at")[:25]
    )
    recent_activities.reverse()

    anomaly_by_activity_id = {
        item["activity_id"]: item["anomaly_score"]
        for item in AnomalyLog.objects.filter(activity__in=recent_activities).values("activity_id", "anomaly_score")
    }

    series = []
    for activity in recent_activities:
        series.append(
            float(activity.risk_score)
            + float(anomaly_by_activity_id.get(activity.id, 0.0)) * 0.35
            + float(activity.blocked_events + activity.password_exposures) * 4
            + float(activity.downloads + activity.uploads) * 2
            + float(activity.security_alerts) * 3
        )

    current_value = (
        float(current_activity.risk_score)
        + float(anomaly_result["anomaly_score"]) * 0.35
        + float(current_activity.blocked_events + current_activity.password_exposures) * 4
        + float(current_activity.downloads + current_activity.uploads) * 2
        + float(current_activity.security_alerts) * 3
    )
    series.append(current_value)
    return series


def build_predictive_alert(employee, activity, anomaly_result, risk_profile):
    baseline = anomaly_result.get("baseline_comparison", {}) or {}
    series = _trend_series(employee, activity, anomaly_result)

    slope = 0.0
    predicted_next_score = float(risk_profile.score)
    fit_quality = 0.0
    if len(series) >= 5:
        x_values = [[index] for index in range(len(series))]
        model = LinearRegression()
        model.fit(x_values, series)
        slope = float(model.coef_[0])
        predicted_next_score = float(model.predict([[len(series)]])[0])
        fit_quality = float(model.score(x_values, series))

    deviation_score = float(baseline.get("score", 0.0))
    severity_index = max(
        _threat_rank(risk_profile.level),
        _threat_rank(_score_to_level(predicted_next_score)),
    )
    if slope >= 8 or deviation_score >= 65:
        severity_index = max(severity_index, _threat_rank(EmployeeRiskScore.LEVEL_CRITICAL))
    elif slope >= 4 or deviation_score >= 35:
        severity_index = max(severity_index, _threat_rank(EmployeeRiskScore.LEVEL_HIGH))

    ordered_levels = [
        EmployeeRiskScore.LEVEL_LOW,
        EmployeeRiskScore.LEVEL_MEDIUM,
        EmployeeRiskScore.LEVEL_HIGH,
        EmployeeRiskScore.LEVEL_CRITICAL,
    ]
    predicted_threat_level = ordered_levels[min(severity_index, len(ordered_levels) - 1)]

    sample_factor = min(len(series) / 12.0, 1.0)
    anomaly_factor = 0.2 if anomaly_result.get("is_anomalous") else 0.0
    deviation_factor = min(deviation_score / 100.0, 0.35)
    slope_factor = min(max(slope, 0.0) / 10.0, 0.35)
    confidence_score = round(min(0.98, 0.15 + sample_factor * 0.3 + fit_quality * 0.2 + anomaly_factor + deviation_factor + slope_factor), 2)

    should_alert = predicted_threat_level in {
        EmployeeRiskScore.LEVEL_HIGH,
        EmployeeRiskScore.LEVEL_CRITICAL,
    } or slope >= 3 or deviation_score >= 30

    baseline_flags = baseline.get("flags", [])
    signals = list(dict.fromkeys((anomaly_result.get("rule_alerts") or []) + baseline_flags))
    alert_message = (
        f"{employee.name} shows an increasing behavioral risk trend. "
        f"Predicted threat level is {predicted_threat_level} with {int(confidence_score * 100)}% confidence. "
        f"Current risk score is {risk_profile.score}, projected next score is {round(predicted_next_score, 2)}, "
        f"and baseline deviation score is {round(deviation_score, 2)}."
    )

    return {
        "should_alert": should_alert,
        "alert_message": alert_message,
        "predicted_threat_level": predicted_threat_level,
        "confidence_score": confidence_score,
        "predicted_incident": _predicted_incident(signals),
        "trend_slope": round(slope, 2),
        "predicted_next_score": round(predicted_next_score, 2),
        "historical_samples": len(series),
        "baseline_deviation_score": round(deviation_score, 2),
        "fit_quality": round(fit_quality, 2),
        "open_predictive_alerts": BehavioralAlert.objects.filter(
            employee=employee,
            alert_type="predictive_trend",
            status=BehavioralAlert.STATUS_OPEN,
        ).count(),
    }
