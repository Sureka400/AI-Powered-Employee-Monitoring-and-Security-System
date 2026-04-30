import os
import pandas as pd
from paddleocr import PaddleOCR

# Get project root
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Paths
screenshots_folder = os.path.join(BASE_DIR, "screenshots")
outputs_folder = os.path.join(BASE_DIR, "outputs")
csv_file = os.path.join(outputs_folder, "logs.csv")

os.makedirs(outputs_folder, exist_ok=True)

# Find image automatically
valid_ext = (".png", ".jpg", ".jpeg")

images = [
    f for f in os.listdir(screenshots_folder)
    if f.lower().endswith(valid_ext)
]

if not images:
    print("❌ No image found in screenshots folder")
    exit()

image_name = images[0]
image_path = os.path.join(screenshots_folder, image_name)

print("📷 Using image:", image_name)

# Load OCR
ocr = PaddleOCR(lang="en")

# Run OCR (OLD API compatible)
result = ocr.ocr(image_path)

rows = []

# Correct parsing (OLD format)
for line in result[0]:
    text = line[1][0]
    score = line[1][1]
    rows.append([image_name, text, score])

# Save CSV
df = pd.DataFrame(rows, columns=["FileName", "Text", "Confidence"])
df.to_csv(csv_file, index=False)

print("\n✅ OCR Completed")
print(df)
print("\n📄 Saved:", csv_file)