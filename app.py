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
    data = request.get_json(force=True, silent=True)

    if not data:
        return jsonify({"status": "error", "message": "No JSON received"}), 400

    print("Received Data:", data)  # ✅ Debugging Log

    # ✅ Challenge Verification
    if "challenge" in data:
        return jsonify({"challenge": data["challenge"]})

    try:
        event = data.get("event", {})

        # ✅ 1. ივენტის სახელი (Item Name)
        event_name = event.get("pulseName", "No Name")

        # ✅ 2. თარიღის გადმოწერა (New Date)
        column_value = event.get("value", {})
        event_date = column_value.get("date", None)
        event_time = column_value.get("time", "12:00:00")  # Default 12:00 PM

        if not event_date:
            return jsonify({"status": "error", "message": "No date found"}), 400

        full_event_date = f"{event_date}T{event_time}"  # 2025-03-16T05:00:00 Format

        # ✅ 3. მონაწილეები (Currently Not Available in Request)
        attendees = []  # No Person Data Available in Webhook JSON

        # ✅ 4. Google Calendar API Event Creation
        create_google_event(event_name, full_event_date, attendees)

    except Exception as e:
        print("Error Processing Event:", str(e))  # ❌ Error Log
        return jsonify({"status": "error", "message": str(e)}), 400

    return jsonify({"status": "ok", "message": "Event added to Google Calendar"}), 200



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
