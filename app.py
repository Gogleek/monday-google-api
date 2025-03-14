from flask import Flask, request, jsonify
import requests
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

# Service Account JSON ფაილი
SERVICE_ACCOUNT_FILE = "credentials.json"
SCOPES = ["https://www.googleapis.com/auth/calendar"]

# Google Calendar API ფუნქცია - ივენტის დამატება
def create_google_event(event_name, event_date, attendees):
    creds = service_account.Credentials.from_service_account_file(SERVICE_ACCOUNT_FILE, scopes=SCOPES)
    service = build("calendar", "v3", credentials=creds)

    event = {
        "summary": event_name,
        "start": {"dateTime": event_date, "timeZone": "UTC"},
        "end": {"dateTime": (datetime.datetime.fromisoformat(event_date) + datetime.timedelta(hours=1)).isoformat(), "timeZone": "UTC"},
        "attendees": [{"email": email} for email in attendees],  # მონიშნული პერსონები
    }

    event_result = service.events().insert(calendarId="primary", body=event).execute()
    return event_result

# Monday.com Webhook Verification (Challenge Response)
@app.route("/monday-webhook", methods=["POST"])
def monday_webhook():
    data = request.get_json(force=True, silent=True)  # ✅ Force JSON Parsing
    
    if not data:
        return jsonify({"status": "error", "message": "No JSON received"}), 400

    print("Received Data:", data)  # ✅ Debugging Log

    # Challenge Verification
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    return jsonify({"status": "ok", "message": "Processing started"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
