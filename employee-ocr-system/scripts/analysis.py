from analytics.feature_extraction import detect_keywords, detect_sensitive_data


# ================= CLEAN OCR (NO FILTERING) =================
def clean_ocr_text(text):
    return text or ""   # KEEP RAW TEXT


# ================= CLASSIFICATION =================
def classify_text(text):
    text = (text or "").lower()

    suspicious_keywords = [
        "password", "blocked", "unauthorized",
        "firewall", "credential", "token",
        "hack", "bypass"
    ]

    work_keywords = [
        "monitoring", "database", "api",
        "network", "report", "service",
        "dashboard", "download", "vpn",
        "server", "auth"
    ]

    if any(k in text for k in suspicious_keywords):
        return "Suspicious"

    if any(k in text for k in work_keywords):
        return "Work"

    return "Neutral"


# ================= RISK SCORE =================
def calculate_risk_score(sensitive_data, keywords):
    weights = {
        "email": 15,
        "phone": 15,
        "ip_address": 20,
        "password": 35,
        "api_key": 35,
    }

    score = sum(weights.get(i, 5) for i in sensitive_data)
    score += len(keywords) * 4

    return min(score, 100)


# ================= ANALYSIS =================
def analyze_text(text):

    cleaned_text = clean_ocr_text(text)

    sensitive = detect_sensitive_data(cleaned_text) or []
    keywords = detect_keywords(cleaned_text) or []

    classification = classify_text(cleaned_text)
    risk_score = calculate_risk_score(sensitive, keywords)

    return {
        "classification": classification,
        "sensitive_data": sensitive,
        "keywords": keywords,
        "risk_score": risk_score,
    }