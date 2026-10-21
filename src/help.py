"""Client for requesting a Twilio help alert through CURA's API."""

import os
from collections.abc import Sequence

import requests


def help(username: str, event_kind: str, contacts: Sequence[str]) -> str:
    """Request an SMS to the user's saved emergency contacts."""
    api_url = os.environ.get(
        "CURA_API_URL", "https://cura-assistant-api.onrender.com"
    ).strip().rstrip("/")
    if not api_url:
        return "CURA's alert service is not configured. Contact emergency services if needed."

    recipients = [contact.strip() for contact in contacts if contact.strip()]
    if not recipients:
        return "Add an emergency contact with a country code (for example, +14155550123) to send an alert."

    try:
        response = requests.post(
            f"{api_url}/notifications/help",
            json={"username": username, "event": event_kind, "contacts": recipients},
            timeout=20,
        )
    except requests.RequestException:
        return "Couldn't reach CURA's alert service. If you need immediate help, contact local emergency services."

    if response.status_code == 404:
        return "CURA's SMS alert endpoint isn't deployed yet. Please try again later. If you need immediate help, contact local emergency services."
    if response.status_code == 429:
        return "Too many help alerts were sent recently. If you need immediate help, contact local emergency services."
    if response.status_code == 503:
        return "CURA's SMS service isn't configured yet. If you need immediate help, contact local emergency services."
    try:
        data = response.json() if response.content else {}
    except ValueError:
        data = {}
    sent = data.get("sent", 0) if isinstance(data, dict) else 0
    total = data.get("total", len(recipients)) if isinstance(data, dict) else len(recipients)
    if response.ok and sent == total:
        return f"SMS alert sent to {sent} emergency contact{'s' if sent != 1 else ''}. If you are in immediate danger, contact local emergency services."
    if response.ok and sent:
        return f"SMS alert reached {sent} of {total} emergency contacts. If you are in immediate danger, contact local emergency services."
    message = data.get("error") if isinstance(data, dict) else None
    if not isinstance(message, str) or not message:
        message = "The SMS alert could not be sent."
    return f"{message} If you need immediate help, contact local emergency services."
