import os
import time
import csv
from datetime import datetime

import cv2

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

import django
django.setup()

from paddleocr import PaddleOCR
from monitoring.services import ingest_employee_activity, run_behavioral_prediction
from scripts.analysis import analyze_text

# ================= OCR INIT =================
OCR_LINE_CONFIDENCE = 0.6

ocr = PaddleOCR(
    lang='en',
    use_angle_cls=True,
    det_db_thresh=0.4,
    det_db_box_thresh=0.65,
    drop_score=OCR_LINE_CONFIDENCE,
)

# ================= PATHS =================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

watch_folder = os.path.join(BASE_DIR, "screenshots")
output_file = os.path.join(BASE_DIR, "outputs", "logs.csv")

os.makedirs(os.path.dirname(output_file), exist_ok=True)


def preprocess_image(path):
    image = cv2.imread(path)
    if image is None:
        return None

    height, width = image.shape[:2]
    scale = 2.0 if max(height, width) < 1400 else 1.5
    resized = cv2.resize(
        image,
        None,
        fx=scale,
        fy=scale,
        interpolation=cv2.INTER_CUBIC,
    )
    grayscale = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)

    return cv2.bilateralFilter(grayscale, 5, 35, 35)


def extract_confident_text(result):
    confident_lines = []

    if not result or not result[0]:
        return ""

    for line in result[0]:
        if not line or len(line) < 2:
            continue

        text_info = line[1]
        if not text_info or len(text_info) < 2:
            continue

        line_text, confidence = text_info
        if confidence <= OCR_LINE_CONFIDENCE:
            continue

        cleaned_text = " ".join(str(line_text).split()).strip()
        if cleaned_text:
            confident_lines.append(cleaned_text)

    return " ".join(confident_lines).strip()

# ================= CSV INIT =================
with open(output_file, "w", newline="", encoding="utf-8") as f:
    writer = csv.writer(f)
    writer.writerow([
        "image_path",
        "employee_code",
        "classification",
        "risk_score",
        "sensitive_data",
        "keywords",
        "text",
        "anomaly_status",
        "risk_level"
    ])

processed = set()

print("WATCHER STARTED")

# ================= MAIN LOOP =================
while True:

    for root, _, files in os.walk(watch_folder):

        for file in files:

            if not file.lower().endswith((".png", ".jpg", ".jpeg")):
                continue

            path = os.path.join(root, file)

            if path in processed:
                continue

            try:
                print("\nProcessing:", file)

                # ================= OCR =================
                preprocessed_image = preprocess_image(path)
                if preprocessed_image is None:
                    print("IMAGE LOAD FAILED -> SKIP")
                    processed.add(path)
                    continue

                result = ocr.ocr(preprocessed_image, cls=True)
                text = extract_confident_text(result)

                if not text:
                    print("EMPTY OCR → SKIP")
                    processed.add(path)
                    continue

                # ================= ANALYSIS =================
                analysis = analyze_text(text)

                classification = analysis.get("classification", "Neutral")

                # 🚨 HARD STOP FOR NOISE
                if classification == "Noise":
                    print("NOISE DETECTED → SKIPPING")
                    processed.add(path)
                    continue

                risk_score = analysis.get("risk_score", 0)
                sensitive = analysis.get("sensitive_data", [])
                keywords = analysis.get("keywords", [])

                employee_code = os.path.basename(os.path.dirname(path)) or "unknown"

                anomaly_status = "not_processed"
                risk_level = "low" if risk_score < 30 else "medium" if risk_score < 60 else "high"

                # ================= DJANGO =================
                try:
                    payload = {
                        "employee_code": employee_code,
                        "employee_name": employee_code,
                        "department": "Unknown",
                        "image_path": path,
                        "application_name": "OCR",
                        "window_title": file,
                        "workflow_label": "ocr",
                        "login_hour": datetime.now().hour,
                        "active_minutes": 10,
                        "idle_minutes": 1,
                        "ocr_text": text,
                        "downloads": 0,
                        "uploads": 0,
                        "blocked_events": 0,
                        "security_alerts": 1 if classification == "Suspicious" else 0,
                        "password_exposures": len([x for x in sensitive if x == "password"]),
                        "network_bytes": 0,
                        "risk_score": risk_score,
                        "metadata": {}
                    }

                    res = ingest_employee_activity(payload)

                    if res.get("status") == "stored":
                        from monitoring.models import EmployeeActivity

                        obj = EmployeeActivity.objects.get(id=res["activity_id"])
                        pred = run_behavioral_prediction(obj)

                        anomaly_status = "anomalous" if pred["anomaly"].is_anomalous else "normal"
                        risk_level = pred["risk_profile"].level

                except Exception as e:
                    print("DB ERROR:", e)

                # ================= CSV WRITE =================
                with open(output_file, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        path,
                        employee_code,
                        classification,
                        risk_score,
                        ",".join(sensitive),
                        ",".join(keywords),
                        text[:300],
                        anomaly_status,
                        risk_level
                    ])

                print("SAVED:", file)
                processed.add(path)

            except Exception as e:
                print("ERROR:", e)

    time.sleep(3)
