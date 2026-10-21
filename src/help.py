"""Build the user-reviewed SMS draft used by CURA's help actions."""


def help_message(username: str, event_kind: str) -> str:
    event_labels = {"routine": "routine check-in", "sound": "sound alert"}
    event_label = event_labels.get(event_kind, "safety check-in")
    name = username.strip() or "A CURA user"
    return (
        f"CURA alert: {name} tapped ‘I need help’ during a {event_label}. "
        "Please check on them as soon as possible. If there is immediate danger, "
        "contact local emergency services."
    )
