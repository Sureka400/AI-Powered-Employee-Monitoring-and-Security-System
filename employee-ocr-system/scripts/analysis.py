import re

# ----------------------------
# 1. CLEAN SYSTEM NOISE FILTER
# ----------------------------
def is_system_noise(text):
    noise_keywords = [
        "websocket",
        "migration",
        "django",
        "apply all migrations",
        "server starting",
        "http://127.0.0.1",
        "agent is online",
        "monitoring active",
        "sessions.",
        "auth.",
        "status",
        "group: monitoring",
        "ceo_server"
    ]

    text_lower = text.lower()
    return any(k in text_lower for k in noise_keywords)


# ----------------------------
# 2. DETECT SENSITIVE DATA
# ----------------------------
def detect_sensitive_data(text):
    text = text.lower()

    patterns = {
        "email": r"[a-z0-9._%+-]+@[a-z0-9.-]+\.[a-z]{2,}",
        "phone": r"\b\d{10}\b",
        "ip_address": r"\b\d{1,3}(\.\d{1,3}){3}\b",
        "password": r"(password|pwd|pass)\s*[:=]?\s*\S+",
    }

    detected = []

    for key, pattern in patterns.items():
        if re.search(pattern, text):
            detected.append(key)

    return detected


# ----------------------------
# 3. DETECT WORK KEYWORDS
# ----------------------------
def detect_keywords(text):
    text = text.lower()

    keywords = [
        "server", "admin", "database", "backend", "api",
        "firewall", "security", "authentication", "login",
        "password", "access", "permission", "blocked",
        "monitoring", "tracking", "activity", "log", "logs",
        "network", "ip", "dns", "websocket", "connection",
        "download", "upload", "process", "running", "service"
    ]

    return [k for k in keywords if k in text]


# ----------------------------
# 4. CLASSIFICATION LOGIC
# ----------------------------
def classify_text(text):
    text = text.lower()

    work_keywords = [
        "server", "admin", "monitoring", "database", "api",
        "network", "log", "process", "service"
    ]

    suspicious_keywords = [
        "password", "blocked", "unauthorized", "access denied",
        "firewall", "attack", "malware", "ip_address"
    ]

    work_count = sum(k in text for k in work_keywords)
    suspicious_count = sum(k in text for k in suspicious_keywords)

    if suspicious_count > 0:
        return "Suspicious"
    elif work_count > 0:
        return "Work"
    else:
        return "Neutral"


# ----------------------------
# 5. RISK SCORE (IMPROVED)
# ----------------------------
def calculate_risk_score(sensitive_data, keywords):

    weights = {
        "email": 20,
        "phone": 15,
        "ip_address": 25,
        "password": 40
    }

    score = sum(weights.get(i, 0) for i in sensitive_data)
    score += len(keywords) * 2

    return min(score, 100)


# ----------------------------
# 6. MASTER ANALYSIS FUNCTION
# ----------------------------
def analyze_text(text):

    # STEP 1: skip system logs
    if is_system_noise(text):
        return {
            "status": "SKIPPED",
            "reason": "system_noise_detected"
        }

    # STEP 2: analysis
    sensitive = detect_sensitive_data(text)
    keywords = detect_keywords(text)
    classification = classify_text(text)
    risk = calculate_risk_score(sensitive, keywords)

    return {
        "classification": classification,
        "sensitive_data": sensitive,
        "keywords": keywords,
        "risk_score": risk
    }