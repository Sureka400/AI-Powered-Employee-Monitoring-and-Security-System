import os
import time
import pandas as pd
from datetime import datetime
from paddleocr import PaddleOCR

# Initialize OCR
ocr = PaddleOCR(lang='en')

# Base directory
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

watch_folder = os.path.join(BASE_DIR, "screenshots")
output_file = os.path.join(BASE_DIR, "outputs", "logs.csv")

# Create folders if not exist
os.makedirs(watch_folder, exist_ok=True)
os.makedirs(os.path.dirname(output_file), exist_ok=True)

# Create CSV if not exists
if not os.path.exists(output_file):
    pd.DataFrame(columns=[
        "Timestamp", "File", "Text", "Confidence"
    ]).to_csv(output_file, index=False)

processed = set()

print(f"👀 Watching folder: {watch_folder}")

while True:
    try:
        # ✅ Scan ALL subfolders
        files = []
        for root, dirs, filenames in os.walk(watch_folder):
            for f in filenames:
                files.append(os.path.join(root, f))

    except Exception as e:
        print("❌ Folder error:", e)
        break

    for path in files:
        file = os.path.basename(path)

        # ✅ Process only images
        if not file.lower().endswith((".png", ".jpg", ".jpeg")):
            continue

        # ✅ FIX: use path instead of file
        if path not in processed:
            print(f"Processing: {path}")

            try:
                result = ocr.ocr(path)

                if result is None or len(result) == 0:
                    continue

                rows = []

                for line in result[0]:
                    try:
                        text = line[1][0]
                        conf = line[1][1]
                    except:
                        continue

                    rows.append([
                        datetime.now(),
                        file,
                        text,
                        conf
                    ])

                if rows:
                    df = pd.DataFrame(rows, columns=[
                        "Timestamp", "File", "Text", "Confidence"
                    ])

                    df.to_csv(output_file, mode="a", header=False, index=False)

                    print(f"✅ Processed: {file}")

                # ✅ FIX: store full path
                processed.add(path)

            except Exception as e:
                print(f"❌ Error processing {file}: {e}")

    time.sleep(5)