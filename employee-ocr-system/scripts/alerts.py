import pandas as pd

def trigger_alert(row):
    if row['risk_score'] > 5 or row['sensitive_data']:
        print(f"ALERT: High risk detected in {row['image_path']}\nRisk Score: {row['risk_score']}\nSensitive Data: {row['sensitive_data']}\nKeywords: {row['keywords']}")

def check_logs():
    logs_file = "../outputs/logs.csv"
    df = pd.read_csv(logs_file)

    for _, row in df.iterrows():
        trigger_alert(row)

if __name__ == "__main__":
    check_logs()