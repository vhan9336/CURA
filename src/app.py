import os
import re
import threading
import time
from collections import defaultdict, deque
from datetime import datetime

from flask import Flask, jsonify, request
from openai import APIError, OpenAI

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
ASSISTANT_REQUESTS_PER_MINUTE = 10
HELP_ALERTS_PER_HOUR = 3
_assistant_request_lock = threading.Lock()
_assistant_request_times: dict[str, deque[float]] = defaultdict(deque)
_help_request_lock = threading.Lock()
_help_request_times: dict[str, deque[float]] = defaultdict(deque)
_help_recipient_times: dict[str, deque[float]] = defaultdict(deque)

SYSTEM_PROMPT = """
You are an embedded digital health companion for this Safety and Check-Up Application.
Your ONLY purpose is to help the user with tasks relevant to this app's purpose:
1. Explain the app's features, including routine check-ups, background monitoring, and schedule settings.
2. Guide users on updating their wake-up/bedtime schedule or emergency contacts.
3. Help users locate nearby pharmacies or urgent care centers when requested.
4. Offer supportive mental-health information when appropriate.

Politely decline unrelated requests. Keep replies supportive, clear, and concise.
"""


def _allow_assistant_request(client_id: str) -> bool:
    current_time = time.monotonic()
    with _assistant_request_lock:
        request_times = _assistant_request_times[client_id]
        while request_times and current_time - request_times[0] >= 60:
            request_times.popleft()
        if len(request_times) >= ASSISTANT_REQUESTS_PER_MINUTE:
            return False
        request_times.append(current_time)
        return True


def _allow_help_request(client_id: str, recipients: list[str]) -> bool:
    current_time = time.monotonic()
    with _help_request_lock:
        request_times = _help_request_times[client_id]
        while request_times and current_time - request_times[0] >= 3600:
            request_times.popleft()
        if len(request_times) >= HELP_ALERTS_PER_HOUR:
            return False
        recipient_queues = [_help_recipient_times[number] for number in recipients]
        for queue in recipient_queues:
            while queue and current_time - queue[0] >= 3600:
                queue.popleft()
        if any(len(queue) >= HELP_ALERTS_PER_HOUR for queue in recipient_queues):
            return False
        request_times.append(current_time)
        for queue in recipient_queues:
            queue.append(current_time)
        return True

user_status = {
    "last_check_in": datetime.now(),
    "last_location": None,
    "status": "SAFE",
    "grace_period_minutes": 60,
    "emergency_contact": "+1234567890",
}

@app.route("/check-in", methods=["POST"])
def check_in():
    global user_status
    data = request.json or {}
    current_location = data.get("location")
    if current_location and current_location != user_status["last_location"]:
        user_status["last_location"] = current_location
    user_status["last_check_in"] = datetime.now()
    user_status["status"] = "SAFE"
    return jsonify({"message": "Check-in received successfully", "status": "SAFE"})


@app.get("/health")
def health():
    return jsonify({"status": "ok"})


@app.post("/notifications/help")
def send_help_notification():
    client_id = request.remote_addr or "unknown"
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400
    username = data.get("username")
    event_kind = data.get("event")
    contacts = data.get("contacts")
    if not isinstance(username, str) or not username.strip() or len(username) > 64:
        return jsonify({"error": "A valid username is required."}), 400
    event_labels = {"routine": "routine check-in", "sound": "sound alert"}
    if not isinstance(event_kind, str) or event_kind not in event_labels:
        return jsonify({"error": "A valid alert type is required."}), 400
    if not isinstance(contacts, list) or not 1 <= len(contacts) <= 2:
        return jsonify({"error": "Provide one or two saved emergency contacts."}), 400
    if any(
        not isinstance(number, str)
        or not re.fullmatch(r"\+[1-9]\d{7,14}", number)
        for number in contacts
    ):
        return jsonify({"error": "Emergency contacts must use international format, such as +14155550123."}), 400
    if len(set(contacts)) != len(contacts):
        contacts = list(dict.fromkeys(contacts))
    if not _allow_help_request(client_id, contacts):
        return jsonify({"error": "Help alert limit reached. Try again later."}), 429

    account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
    auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
    from_number = os.environ.get("TWILIO_FROM_NUMBER")
    if not account_sid or not auth_token or not from_number:
        app.logger.error("Twilio SMS credentials are not configured.")
        return jsonify({"error": "CURA's SMS service isn't configured yet."}), 503

    try:
        from twilio.rest import Client

        client = Client(account_sid, auth_token)
        event_label = event_labels[event_kind]
        message_body = (
            f"CURA alert: {username.strip()} tapped ‘I need help’ during a "
            f"{event_label}. Please check on them as soon as possible. "
            "If there is immediate danger, contact local emergency services."
        )
        sent = 0
        for number in contacts:
            try:
                client.messages.create(body=message_body, from_=from_number, to=number)
                sent += 1
            except Exception:
                app.logger.exception("Twilio failed to send a help alert.")
        if sent == 0:
            return jsonify({"error": "The SMS alert could not be sent."}), 502
        return jsonify({"sent": sent, "total": len(contacts)}), 200
    except ImportError:
        app.logger.exception("Twilio SDK is not installed.")
        return jsonify({"error": "CURA's SMS service isn't configured yet."}), 503


@app.route("/assistant/chat", methods=["POST"])
def assistant_chat():
    if not _allow_assistant_request(request.remote_addr or "unknown"):
        return jsonify({"error": "Too many assistant requests. Try again shortly."}), 429

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"error": "Request body must be a JSON object."}), 400

    messages = data.get("messages")
    if not isinstance(messages, list) or not messages or len(messages) > 12:
        return jsonify({"error": "Provide between 1 and 12 chat messages."}), 400

    validated_messages = []
    for message in messages:
        if not isinstance(message, dict):
            return jsonify({"error": "Each message must be an object."}), 400
        role = message.get("role")
        content = message.get("content")
        if not isinstance(role, str) or role not in {"user", "assistant"}:
            return jsonify({"error": "Message role must be user or assistant."}), 400
        if not isinstance(content, str) or not content.strip() or len(content) > 4000:
            return jsonify({"error": "Message content must be 1–4000 characters."}), 400
        validated_messages.append({"role": role, "content": content.strip()})

    api_key = os.environ.get("GROQ_API_KEY")
    if not api_key:
        app.logger.error("GROQ_API_KEY is not configured on the assistant server.")
        return jsonify({"error": "The assistant is temporarily unavailable."}), 503

    client = OpenAI(
        base_url="https://api.groq.com/openai/v1",
        api_key=api_key,
        timeout=30.0,
        max_retries=1,
    )
    try:
        completion = client.chat.completions.create(
            model="openai/gpt-oss-20b",
            messages=[{"role": "system", "content": SYSTEM_PROMPT}]
            + validated_messages,
            temperature=0.3,
        )
    except APIError:
        app.logger.exception("Assistant provider request failed.")
        return jsonify({"error": "The assistant could not complete that request."}), 502

    reply = completion.choices[0].message.content
    if not isinstance(reply, str) or not reply.strip():
        app.logger.error("Assistant provider returned an empty response.")
        return jsonify({"error": "The assistant returned an empty response."}), 502
    return jsonify({"reply": reply.strip()})


if __name__ == "__main__":
    app.run(debug=False, port=5001)
