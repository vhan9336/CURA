import os
import threading
import time
from collections import defaultdict, deque
from datetime import datetime

from flask import Flask, jsonify, request
from openai import APIError, OpenAI

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 32 * 1024
ASSISTANT_REQUESTS_PER_MINUTE = 10
_assistant_request_lock = threading.Lock()
_assistant_request_times: dict[str, deque[float]] = defaultdict(deque)

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