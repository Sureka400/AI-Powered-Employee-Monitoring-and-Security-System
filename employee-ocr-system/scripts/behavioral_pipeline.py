import os
import sys
from datetime import datetime


BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(BASE_DIR)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django

django.setup()

from monitoring.models import EmployeeActivity
from monitoring.services import ingest_employee_activity, run_behavioral_prediction, train_all_employee_profiles


EXAMPLE_TRAINING_PAYLOADS = [
    {
        "employee_code": "EMP001",
        "employee_name": "Soniya Bhara",
        "department": "Security Operations",
        "application_name": "Chrome",
        "window_title": "Internal Dashboard",
        "workflow_label": "monitoring",
        "login_hour": 9,
        "active_minutes": 42,
        "idle_minutes": 5,
        "ocr_text": "Monitoring dashboard login activity firewall status and approved access.",
        "downloads": 0,
        "uploads": 0,
        "blocked_events": 0,
        "security_alerts": 0,
        "network_bytes": 180000,
        "risk_score": 8,
        "captured_at": datetime.now(),
    },
    {
        "employee_code": "EMP001",
        "employee_name": "Soniya Bhara",
        "department": "Security Operations",
        "application_name": "Excel",
        "window_title": "Shift Report",
        "workflow_label": "reporting",
        "login_hour": 10,
        "active_minutes": 37,
        "idle_minutes": 4,
        "ocr_text": "Security report spreadsheet daily incident summary and monitoring log export.",
        "downloads": 1,
        "uploads": 0,
        "blocked_events": 0,
        "security_alerts": 0,
        "network_bytes": 150000,
        "risk_score": 10,
        "captured_at": datetime.now(),
    },
]

EXAMPLE_PREDICTION_PAYLOAD = {
    "employee_code": "EMP001",
    "employee_name": "Soniya Bhara",
    "department": "Security Operations",
    "application_name": "UnknownTransferTool",
    "window_title": "Confidential Upload",
    "workflow_label": "data_transfer",
    "login_hour": 2,
    "active_minutes": 88,
    "idle_minutes": 1,
    "ocr_text": "password token confidential upload blocked unauthorized credentials export",
    "downloads": 7,
    "uploads": 9,
    "blocked_events": 4,
    "security_alerts": 3,
    "network_bytes": 2450000,
    "risk_score": 78,
    "captured_at": datetime.now(),
}


def run_example_training_pipeline():
    for payload in EXAMPLE_TRAINING_PAYLOADS:
        ingest_employee_activity(payload)
    return train_all_employee_profiles()


def run_example_prediction_pipeline():
    result = ingest_employee_activity(EXAMPLE_PREDICTION_PAYLOAD)
    activity = EmployeeActivity.objects.select_related("employee").get(id=result["activity_id"])
    prediction = run_behavioral_prediction(activity)
    return {
        "employee_code": activity.employee.employee_code,
        "risk_score": prediction["risk_profile"].score,
        "risk_level": prediction["risk_profile"].level,
        "alerts": [alert.title for alert in prediction["alerts"]],
        "anomaly_type": prediction["anomaly"].anomaly_type,
    }


if __name__ == "__main__":
    print("Training:", run_example_training_pipeline())
    print("Prediction:", run_example_prediction_pipeline())
