# AI-Powered-Employee-Monitoring-and-Security-System

This repository now includes a Django-based behavioral analytics backend on top of the OCR monitoring flow.

## Setup

1. Open a terminal in the project folder.
2. Change into `employee-ocr-system`.
3. Install dependencies:
   `pip install -r requirements.txt`
4. Run database migrations:
   `python manage.py migrate`
5. Start the API:
   `python manage.py runserver`
6. Start OCR monitoring:
`python -m scripts.watcher`
7. for storing in csv
python scripts/process_logs.py

   ``

## Behavioral Analytics Modules

- `analytics/`: noise filtering, OCR feature extraction, baseline profile learning
- `anomaly_detection/`: Isolation Forest training and anomaly scoring
- `risk_engine/`: dynamic risk score calculation and risk level assignment
- `alerts/`: predictive alert generation for insider threat patterns
- `monitoring/`: Django models, services, and analytics API endpoints

## Training And Prediction Pipeline

- Example baseline training:
  `python -m scripts.behavioral_pipeline`
- Manual activity ingestion endpoint:
  `POST /api/activities/ingest/`

## Dashboard APIs

- `GET /api/dashboard/behavior-trends/`
- `GET /api/dashboard/anomalies/`
- `GET /api/dashboard/risk-scores/`
- `GET /api/dashboard/alerts/`
- `GET /api/dashboard/suspicious-summary/`

## OCR Noise Exclusions

Behavioral analysis ignores non-employee noise such as:

- websocket logs
- Django migration logs
- localhost and startup logs
- runserver output

## Output

- Raw OCR event rows continue to be written to `employee-ocr-system/outputs/logs.csv`
- Structured behavioral records, baselines, anomaly logs, risk scores, and alerts are stored in Django models
## Django Admin Access

Create admin account:

python manage.py createsuperuser

Run server:

python manage.py runserver

Open admin panel:

http://127.0.0.1:8000/admin

Login using the superuser credentials created above.

The admin dashboard provides access to:

- Employee Activities
- Behavioral Alerts
- Anomaly Logs
- Risk Scores
- Employee Behavior Profiles
- Predictive Threat Analytics
