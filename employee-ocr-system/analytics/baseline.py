from collections import Counter

from django.utils import timezone

from monitoring.models import EmployeeBehaviorProfile


def update_behavior_profile(employee, activities):
    activity_list = list(activities)
    if not activity_list:
        return None

    count = len(activity_list)
    app_counter = Counter(activity.application_name for activity in activity_list if activity.application_name)
    login_hours = [activity.login_hour for activity in activity_list]
    workflows = Counter(activity.workflow_label for activity in activity_list if activity.workflow_label)

    profile, _ = EmployeeBehaviorProfile.objects.get_or_create(employee=employee)
    profile.average_active_hour = sum(activity.active_minutes for activity in activity_list) / count
    profile.common_applications = [name for name, _ in app_counter.most_common(5)]
    profile.normal_login_hours = sorted(set(login_hours))
    profile.average_keyword_frequency = sum(len(activity.ocr_keyword_hits) for activity in activity_list) / count
    profile.average_risk_score = sum(activity.risk_score for activity in activity_list) / count
    profile.average_downloads = sum(activity.downloads for activity in activity_list) / count
    profile.average_uploads = sum(activity.uploads for activity in activity_list) / count
    profile.average_blocked_events = sum(activity.blocked_events for activity in activity_list) / count
    profile.average_network_bytes = sum(activity.network_bytes for activity in activity_list) / count
    profile.average_idle_minutes = sum(activity.idle_minutes for activity in activity_list) / count
    profile.baseline_workflow = dict(workflows.most_common(10))
    profile.trained_samples = count
    profile.last_trained_at = timezone.now()
    profile.save()
    return profile
