import hashlib
import hmac
import json
import os
import secrets
import threading
from datetime import time
from pathlib import Path
from typing import Mapping


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


users_db = load_users_db()
