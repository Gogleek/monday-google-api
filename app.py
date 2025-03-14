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

# ✅ Monday.com API-დან მომხმარებლის Email-ის მიღება
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

# ✅ Google Calendar API ფუნქცია - ივენტის დამატება
def create_google_event(event_name, event_date, attendees, location=""):
    print(f"📝 Creating Google Event: {event_name}, Date: {event_date}, Attendees: {attendees}, Location: {location}")

    event = {
        "summary": event_name,
        "description": "This event was created from Monday.com\nClick the link below to join:\n",
        "start": {"dateTime": event_date, "timeZone": "UTC"},
        "end": {"dateTime": (datetime.datetime.fromisoformat(event_date) + datetime.timedelta(hours=1)).isoformat(), "timeZone": "UTC"},
        "attendees": [{"email": email} for email in attendees if email],
        "location": location,
        "reminders": {"useDefault": True}
    }

    try:
        event_result = service.events().insert(calendarId="primary", body=event).execute()
        print("✅ Event Created Successfully:", event_result)
        return event_result["htmlLink"]
    except Exception as e:
        print("❌ Google Calendar API Error:", str(e))
        return None

# ✅ Monday.com Webhook - იღებს მონაცემებს და აგზავნის Google Calendar-ში
@app.route("/monday-webhook", methods=["POST"])
def monday_webhook():
    data = request.get_json(force=True, silent=True)

    if not data:
        return jsonify({"status": "error", "message": "No JSON received"}), 400

    print("📩 Received Data:", json.dumps(data, indent=2))  # ✅ Debugging Log

    try:
        event = data.get("event", {})
        event_name = event.get("pulseName", "No Name")
        column_values = event.get("column_values", {})

        print("🛠️ Column Values Debug:", json.dumps(column_values, indent=2))

        column_value = event.get("value", {})
        event_date = column_value.get("date", None)
        event_time = column_value.get("time", "12:00:00")

        if event_time is None:
            event_time = "12:00:00"

        if not event_date:
            return jsonify({"status": "error", "message": "No date found"}), 400

        full_event_date = f"{event_date}T{event_time}"

        # ✅ 1. მოვძებნოთ მონიშნული პერსონები (Assigned Users)
        attendees = []
        assigned_users = column_value.get("personsAndTeams", [])

        if not assigned_users:
            # ვამოწმებთ, არის თუ არა column_values მონაცემებში `person` ველი
            if "person" in column_values and isinstance(column_values["person"], dict):
                person_data = column_values["person"].get("value", [])
                if isinstance(person_data, list):
                    for user in person_data:
                        if isinstance(user, dict) and "id" in user:
                            email = get_monday_user_email(user["id"])
                            if email:
                                attendees.append(email)
                            else:
                                print(f"⚠️ No email found for user ID: {user['id']}")

        else:
            for user in assigned_users:
                if isinstance(user, dict) and "id" in user:
                    email = get_monday_user_email(user["id"])
                    if email:
                        attendees.append(email)
                    else:
                        print(f"⚠️ No email found for user ID: {user['id']}")

        print("✅ Final Attendees Emails:", attendees)

        if not attendees:
            print("⚠️ No attendees found. Event will be created without guests.")

        # ✅ ივენტის შექმნა Google Calendar-ში
        event_link = create_google_event(event_name, full_event_date, attendees)

        if event_link:
            print(f"🔗 Google Calendar Event Link: {event_link}")
            return jsonify({"status": "ok", "message": "Event added to Google Calendar", "event_link": event_link}), 200
        else:
            return jsonify({"status": "error", "message": "Event creation failed"}), 500

    except Exception as e:
        print("❌ Error Processing Event:", str(e))
        return jsonify({"status": "error", "message": str(e)}), 400


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=10000)

