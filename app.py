import json
import os
from flask import Flask, request, jsonify
import requests
import datetime
from google.oauth2 import service_account
from googleapiclient.discovery import build

app = Flask(__name__)

# ✅ JSON Key-ის წაკითხვა Environment Variable-დან
GOOGLE_CREDENTIALS = json.loads(os.getenv("GOOGLE_CREDENTIALS"))
MONDAY_API_KEY = os.getenv("MONDAY_API_KEY")  # Monday API KEY
SCOPES = ["https://www.googleapis.com/auth/calendar"]
creds = service_account.Credentials.from_service_account_info(GOOGLE_CREDENTIALS, scopes=SCOPES)
service = build("calendar", "v3", credentials=creds)

# Monday.com API-დან მომხმარებლის Email-ის მიღება
def get_monday_user_email(user_id):
    url = "https://api.monday.com/v2"
    headers = {
        "Authorization": MONDAY_API_KEY,
        "Content-Type": "application/json"
    }
    query = f'{{ users(ids: {user_id}) {{ email }} }}'
    response = requests.post(url, headers=headers, json={"query": query})

    if response.status_code == 200:
        data = response.json()
        users = data.get("data", {}).get("users", [])
        if users and "email" in users[0]:
            return users[0]["email"]
    return None

# Google Calendar API ფუნქცია - ივენტის დამატება
def create_google_event(event_name, event_date, attendees):
    print(f"Creating Google Event: {event_name}, Date: {event_date}, Attendees: {attendees}")

    event = {
        "summary": event_name,
        "start": {"dateTime": event_date, "timeZone": "UTC"},
        "end": {"dateTime": (datetime.datetime.fromisoformat(event_date) + datetime.timedelta(hours=1)).isoformat(), "timeZone": "UTC"},
        "attendees": [{"email": email} for email in attendees if email],  # მონიშნული პერსონები
    }

    try:
        event_result = service.events().insert(calendarId="primary", body=event).execute()
        print("Event Created Successfully:", event_result)
        return event_result
    except Exception as e:
        print("Google Calendar API Error:", str(e))
        return None

# Monday.com Webhook - იღებს მონაცემებს და აგზავნის Google Calendar-ში
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
        event_name = event.get("pulseName", "No Name")

        column_value = event.get("value", {})
        event_date = column_value.get("date", None)
        event_time = column_value.get("time", "12:00:00")  # Default 12:00 PM
        
        if event_time is None:  
            event_time = "12:00:00"  # Default დრო 12:00 PM

        if not event_date:
            return jsonify({"status": "error", "message": "No date found"}), 400

        full_event_date = f"{event_date}T{event_time}"  # 2025-03-16T12:00:00 Format

        # ✅ 1. მოვძებნოთ მონიშნული პერსონები (Assigned Users)
        attendees = []
        assigned_users = column_value.get("personsAndTeams", [])

        if not assigned_users:
            person_id = event.get("columnId")  # თუ `personsAndTeams` ველი არ არსებობს, მოვიძიოთ Column ID
            if person_id:
                email = get_monday_user_email(person_id)
                if email:
                    attendees.append(email)

        else:
            for user in assigned_users:
                if isinstance(user, dict) and "id" in user:
                    email = get_monday_user_email(user["id"])
                    if email:
                        attendees.append(email)

        print("Attendees Emails:", attendees)  # ✅ Debugging

        create_google_event(event_name, full_event_date, attendees)

    except Exception as e:
        print("Error Processing Event:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 400

    return jsonify({"status": "ok", "message": "Event added to Google Calendar"}), 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)
