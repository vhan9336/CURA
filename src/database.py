import hashlib
import hmac
import json
import os
import secrets
import threading
from datetime import datetime, time
from pathlib import Path
from typing import Mapping, cast


def _default_data_path() -> Path:
    if os.environ.get("ANDROID_DATA"):
        return Path.cwd() / "CURA" / "users.json"

    local_app_data = os.environ.get("LOCALAPPDATA")
    root = Path(local_app_data) if local_app_data else Path.home() / ".local" / "share"
    return root / "CURA" / "users.json"


USER_DATA_PATH = _default_data_path()
_store_lock = threading.RLock()
_PBKDF2_ROUNDS = 310_000


def hash_password(password: str) -> str:
    salt = secrets.token_bytes(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, _PBKDF2_ROUNDS
    )
    return f"pbkdf2_sha256${_PBKDF2_ROUNDS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored_hash: object) -> bool:
    if not isinstance(stored_hash, str):
        return False
    try:
        algorithm, rounds_text, salt_hex, expected_hex = stored_hash.split("$")
        if algorithm != "pbkdf2_sha256":
            return False
        rounds = int(rounds_text)
        if rounds <= 0:
            return False
        salt = bytes.fromhex(salt_hex)
        expected = bytes.fromhex(expected_hex)
    except (ValueError, TypeError):
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, rounds)
    return hmac.compare_digest(actual, expected)


def _encode_value(value: object) -> object:
    if isinstance(value, time):
        return {"__time__": value.isoformat()}
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    raise TypeError(f"Unsupported account value type: {type(value).__name__}")


def _decode_value(value: object) -> object:
    if isinstance(value, dict) and set(value) == {"__time__"}:
        time_text = value["__time__"]
        if not isinstance(time_text, str):
            raise ValueError("Invalid saved time value.")
        return time.fromisoformat(time_text)
    return value


def load_users_db(path: Path = USER_DATA_PATH) -> dict[str, dict[str, object]]:
    with _store_lock:
        try:
            with path.open("r", encoding="utf-8") as store_file:
                raw_users = json.load(store_file)
        except FileNotFoundError:
            return {}

    if not isinstance(raw_users, dict):
        raise ValueError("The saved user database must contain a JSON object.")

    users: dict[str, dict[str, object]] = {}
    for username, raw_info in raw_users.items():
        if not isinstance(username, str) or not isinstance(raw_info, dict):
            raise ValueError("The saved user database contains an invalid account.")
        users[username] = {
            key: _decode_value(value) for key, value in raw_info.items()
        }
    return users


def save_users_db(
    users: Mapping[str, Mapping[str, object]],
    path: Path = USER_DATA_PATH,
) -> None:
    payload = {
        username: {key: _encode_value(value) for key, value in info.items()}
        for username, info in users.items()
    }
    with _store_lock:
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary_path = path.with_name(path.name + ".tmp")
        with temporary_path.open("w", encoding="utf-8") as store_file:
            json.dump(payload, store_file, indent=2)
            store_file.flush()
            os.fsync(store_file.fileno())
        temporary_path.replace(path)


def get_checkin_history(username: str) -> list[dict[str, str]]:
    user_info = users_db.get(username)
    if not isinstance(user_info, dict):
        raise ValueError("Cannot read check-in history for an unknown account.")
    raw_history = user_info.get("checkin_history", "[]")
    if not isinstance(raw_history, str):
        raise ValueError("Saved check-in history has an invalid format.")
    try:
        decoded_history: object = json.loads(raw_history)
    except json.JSONDecodeError as error:
        raise ValueError("Saved check-in history contains invalid JSON.") from error
    if not isinstance(decoded_history, list):
        raise ValueError("Saved check-in history must contain a list of events.")

    valid_history: list[dict[str, str]] = []
    events = cast(list[object], decoded_history)
    for raw_event in events:
        if not isinstance(raw_event, dict):
            raise ValueError("Saved check-in history contains an invalid event.")
        event = cast(dict[str, object], raw_event)
        event_at = event.get("at")
        event_kind = event.get("kind")
        if (
            not isinstance(event_at, str)
            or not isinstance(event_kind, str)
            or event_kind not in {"routine", "sound"}
        ):
            raise ValueError("Saved check-in history contains an invalid event.")
        try:
            datetime.fromisoformat(event_at)
        except ValueError as error:
            raise ValueError("Saved check-in history contains an invalid date.") from error
        valid_history.append({"at": event_at, "kind": event_kind})
    return valid_history


def record_checkin(username: str, kind: str) -> None:
    if kind not in {"routine", "sound"}:
        raise ValueError("Check-in kind must be 'routine' or 'sound'.")
    with _store_lock:
        user_info = users_db.get(username)
        if not isinstance(user_info, dict):
            raise ValueError("Cannot record a check-in for an unknown account.")

        had_history = "checkin_history" in user_info
        previous_history = user_info.get("checkin_history", "[]")
        history = get_checkin_history(username)
        history.append(
            {
                "at": datetime.now().astimezone().isoformat(timespec="seconds"),
                "kind": kind,
            }
        )
        user_info["checkin_history"] = json.dumps(history, separators=(",", ":"))
        try:
            save_users_db(users_db)
        except OSError:
            if not had_history:
                user_info.pop("checkin_history", None)
            else:
                user_info["checkin_history"] = previous_history
            raise


users_db = load_users_db()
