import math
import re
from collections import Counter

from .noise_filter import is_meaningful_activity


SENSITIVE_PATTERNS = {
    "email": r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}",
    "phone": r"\b\d{10}\b",
    "ip_address": r"\b\d{1,3}(?:\.\d{1,3}){3}\b",
    "password": r"(password|pwd|pass)\s*[:=]?\s*\S+",
    "api_key": r"\b(?:sk|pk|api)[-_][a-z0-9]{8,}\b",
}

SUSPICIOUS_KEYWORDS = [
    "password",
    "credentials",
    "secret",
    "blocked",
    "download",
    "upload",
    "unauthorized",
    "firewall",
    "token",
    "vpn",
    "confidential",
    "exfiltration",
]

WORKFLOW_KEYWORDS = [
    "dashboard",
    "database",
    "spreadsheet",
    "crm",
    "ticket",
    "email",
    "repository",
    "deployment",
    "monitoring",
    "finance",
    "hr",
]


def detect_sensitive_data(text):
    normalized = text.lower()
    return [name for name, pattern in SENSITIVE_PATTERNS.items() if re.search(pattern, normalized)]


def detect_keywords(text):
    normalized = text.lower()
    return [keyword for keyword in SUSPICIOUS_KEYWORDS if keyword in normalized]


def detect_workflow_behaviors(text):
    normalized = text.lower()
    return [keyword for keyword in WORKFLOW_KEYWORDS if keyword in normalized]


def derive_behavioral_metrics(payload):
    text = payload.get("ocr_text", "") or ""
    keyword_hits = detect_keywords(text)
    sensitive_findings = detect_sensitive_data(text)
    workflow_hits = detect_workflow_behaviors(text)
    total_words = max(len(text.split()), 1)

    return {
        "is_meaningful": is_meaningful_activity(text),
        "keyword_hits": keyword_hits,
        "keyword_frequency": round(len(keyword_hits) / total_words, 4),
        "sensitive_findings": sensitive_findings,
        "workflow_hits": workflow_hits,
        "password_exposures": len([item for item in sensitive_findings if item == "password"]),
    }


def build_feature_vector(activity):
    metadata = activity.metadata or {}
    known_app_frequency = 1.0 if metadata.get("is_known_application") else 0.0

    return [
        float(activity.login_hour),
        float(activity.active_minutes),
        float(activity.idle_minutes),
        float(len(activity.ocr_keyword_hits)),
        float(len(activity.sensitive_findings)),
        float(activity.downloads),
        float(activity.uploads),
        float(activity.blocked_events),
        float(activity.security_alerts),
        float(activity.password_exposures),
        float(activity.network_bytes),
        float(activity.risk_score),
        float(known_app_frequency),
        float(metadata.get("inactive_to_active_spike", 0)),
        float(math.log1p(len(activity.ocr_text or ""))),
    ]
