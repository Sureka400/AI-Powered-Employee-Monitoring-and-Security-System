import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import time
import csv
from paddleocr import PaddleOCR
from scripts.analysis import detect_sensitive_data, detect_keywords, classify_text, calculate_risk_score

# Initialize OCR
ocr = PaddleOCR(lang='en')

# Base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

watch_folder = os.path.join(BASE_DIR, "screenshots")
output_file = os.path.join(BASE_DIR, "outputs", "logs.csv")

# Create folders if not exist
os.makedirs(watch_folder, exist_ok=True)
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Create CSV with header if not exists
if not os.path.exists(output_file):
    with open(output_file, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow([
            "image_path", "category", "risk_score",
            "sensitive_data", "keywords", "text"
        ])

processed = set()

print(f"👀 Watching folder: {watch_folder}")

while True:
    try:
        # Scan all subfolders
        files = []
        for root, dirs, filenames in os.walk(watch_folder):
            for f in filenames:
                files.append(os.path.join(root, f))

    except Exception as e:
        print("❌ Folder error:", e)
        break

    for path in files:
        file = os.path.basename(path)

        # Process only image files
        if not file.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        if path not in processed:
            try:
                result = ocr.ocr(path, cls=True)

                # Safe OCR extraction
                if result and result[0]:
                    text = " ".join([line[1][0] for line in result[0]])
                else:
                    text = ""

                # Content analysis
                sensitive_data = detect_sensitive_data(text)
                keywords = detect_keywords(text)
                category = classify_text(text)
                risk_score = calculate_risk_score(sensitive_data, keywords)

                # Write to CSV safely
                with open(output_file, "a", newline="", encoding="utf-8") as f:
                    writer = csv.writer(f)
                    writer.writerow([
                        path,
                        category,
                        risk_score,
                        ",".join(sensitive_data),
                        ",".join(keywords),
                        text
                    ])

                print(f"Processed: {file}")

                processed.add(path)

            except Exception as e:
                print("❌ OCR error:", e)

    time.sleep(5)