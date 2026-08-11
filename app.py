from datetime import datetime
from flask import Flask, jsonify, request

app = Flask(__name__)

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

if __name__ == "__main__":
    app.run(debug=True, port=5001)