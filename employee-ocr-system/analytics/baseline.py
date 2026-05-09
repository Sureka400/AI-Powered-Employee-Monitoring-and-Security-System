from collections import Counter
from statistics import mean, pstdev

from django.utils import timezone

from monitoring.models import EmployeeBehaviorProfile


def _safe_mean(values):
    return mean(values) if values else 0.0


def _safe_stddev(values):
    return pstdev(values) if len(values) > 1 else 0.0


def _flatten_keywords(activity):
    values = []
    values.extend(activity.ocr_keyword_hits or [])
    values.extend(activity.suspicious_keywords or [])
    values.extend(activity.sensitive_findings or [])
    return [value for value in values if value]


def update_behavior_profile(employee, activities):
    activity_list = list(activities)
    if not activity_list:
        return None

    count = len(activity_list)
    app_counter = Counter(activity.application_name for activity in activity_list if activity.application_name)
    keyword_counter = Counter()
    login_hours = [activity.login_hour for activity in activity_list]
    risk_scores = [activity.risk_score for activity in activity_list]
    transfer_counts = [activity.downloads + activity.uploads for activity in activity_list]
    workflows = Counter(activity.workflow_label for activity in activity_list if activity.workflow_label)
    activity_hours = Counter(activity.captured_at.hour for activity in activity_list)

    for activity in activity_list:
        keyword_counter.update(_flatten_keywords(activity))

    profile, _ = EmployeeBehaviorProfile.objects.get_or_create(employee=employee)
    profile.average_active_hour = _safe_mean([activity.active_minutes for activity in activity_list])
    profile.average_login_hour = _safe_mean(login_hours)
    profile.common_applications = [name for name, _ in app_counter.most_common(5)]
    profile.common_keywords = [name for name, _ in keyword_counter.most_common(10)]
    profile.normal_login_hours = sorted(set(login_hours))
    profile.average_keyword_frequency = _safe_mean([len(activity.ocr_keyword_hits) for activity in activity_list])
    profile.average_risk_score = _safe_mean(risk_scores)
    profile.average_downloads = _safe_mean([activity.downloads for activity in activity_list])
    profile.average_uploads = _safe_mean([activity.uploads for activity in activity_list])
    profile.average_blocked_events = _safe_mean([activity.blocked_events for activity in activity_list])
    profile.average_network_bytes = _safe_mean([activity.network_bytes for activity in activity_list])
    profile.average_idle_minutes = _safe_mean([activity.idle_minutes for activity in activity_list])
    profile.baseline_workflow = dict(workflows.most_common(10))
    profile.normal_activity_patterns = {
        "top_workflows": dict(workflows.most_common(5)),
        "peak_hours": [hour for hour, _ in activity_hours.most_common(5)],
        "login_hour_stddev": round(_safe_stddev(login_hours), 2),
        "risk_score_stddev": round(_safe_stddev(risk_scores), 2),
        "average_transfer_count": round(_safe_mean(transfer_counts), 2),
        "transfer_count_stddev": round(_safe_stddev(transfer_counts), 2),
        "network_bytes_stddev": round(_safe_stddev([activity.network_bytes for activity in activity_list]), 2),
        "idle_minutes_stddev": round(_safe_stddev([activity.idle_minutes for activity in activity_list]), 2),
    }
    profile.trained_samples = count
    profile.last_trained_at = timezone.now()
    profile.save()
    return profile


def compare_activity_to_baseline(profile, activity):
    if not profile:
        return {
            "is_deviating": False,
            "score": 0.0,
            "flags": [],
            "details": {},
        }

    flags = []
    details = {}
    patterns = profile.normal_activity_patterns or {}

    login_hour_delta = abs(float(activity.login_hour) - float(profile.average_login_hour))
    login_hour_threshold = max(2.0, float(patterns.get("login_hour_stddev", 0.0)) * 1.5)
    if login_hour_delta > login_hour_threshold:
        flags.append("baseline_login_deviation")
    details["login_hour_delta"] = round(login_hour_delta, 2)

    risk_score_delta = float(activity.risk_score) - float(profile.average_risk_score)
    risk_threshold = max(10.0, float(patterns.get("risk_score_stddev", 0.0)) * 1.5)
    if risk_score_delta > risk_threshold:
        flags.append("baseline_risk_deviation")
    details["risk_score_delta"] = round(risk_score_delta, 2)

    if (
        profile.common_applications
        and activity.application_name
        and activity.application_name not in profile.common_applications
    ):
        flags.append("baseline_application_deviation")

    if activity.workflow_label and activity.workflow_label not in (profile.baseline_workflow or {}):
        flags.append("baseline_workflow_deviation")

    baseline_keywords = set(profile.common_keywords or [])
    current_keywords = set(_flatten_keywords(activity))
    new_keywords = sorted(keyword for keyword in current_keywords if keyword not in baseline_keywords)
    if new_keywords:
        flags.append("baseline_keyword_deviation")
    details["new_keywords"] = new_keywords

    transfer_count = activity.downloads + activity.uploads
    avg_transfer = float(patterns.get("average_transfer_count", 0.0))
    transfer_threshold = max(avg_transfer + 2.0, avg_transfer + float(patterns.get("transfer_count_stddev", 0.0)) * 2)
    if transfer_count > transfer_threshold:
        flags.append("baseline_transfer_deviation")
    details["transfer_delta"] = round(transfer_count - avg_transfer, 2)

    network_threshold = max(profile.average_network_bytes * 2, 500000)
    if activity.network_bytes > network_threshold:
        flags.append("baseline_network_deviation")
    details["network_delta"] = round(float(activity.network_bytes) - float(profile.average_network_bytes), 2)

    score = min(
        100.0,
        (login_hour_delta * 8)
        + max(risk_score_delta, 0.0) * 1.6
        + (len(new_keywords) * 8)
        + (12 if "baseline_application_deviation" in flags else 0)
        + (10 if "baseline_workflow_deviation" in flags else 0)
        + (10 if "baseline_transfer_deviation" in flags else 0)
        + (10 if "baseline_network_deviation" in flags else 0),
    )

    return {
        "is_deviating": bool(flags),
        "score": round(score, 2),
        "flags": flags,
        "details": details,
    }
