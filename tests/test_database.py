import json
import tempfile
import unittest
from datetime import time
from pathlib import Path
from unittest.mock import patch

from src import database
from src.database import (
    hash_password,
    load_users_db,
    record_checkin,
    save_users_db,
    verify_password,
)


class UserStoreTests(unittest.TestCase):
    def test_android_uses_writable_application_data_directory(self):
        with patch.dict(
            "os.environ",
            {"ANDROID_DATA": "/data", "LOCALAPPDATA": ""},
            clear=True,
        ):
            data_path = database._default_data_path()

        self.assertEqual(data_path, Path.cwd() / "CURA" / "users.json")

    def test_windows_uses_local_app_data_directory(self):
        with patch.dict(
            "os.environ",
            {"LOCALAPPDATA": "C:/Users/Test/AppData/Local"},
            clear=True,
        ):
            data_path = database._default_data_path()

        self.assertEqual(
            data_path,
            Path("C:/Users/Test/AppData/Local") / "CURA" / "users.json",
        )

    def test_accounts_and_times_survive_store_round_trip(self):
        users = {
            "Alex": {
                "password": hash_password("secret123"),
                "wakeup_time": time(7, 30),
                "bedtime_time": time(22),
                "dark_mode": True,
            }
        }

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "users.json"
            save_users_db(users, path)
            restored = load_users_db(path)

        self.assertEqual(restored["Alex"]["wakeup_time"], time(7, 30))
        self.assertEqual(restored["Alex"]["bedtime_time"], time(22))
        self.assertTrue(restored["Alex"]["dark_mode"])
        self.assertTrue(verify_password("secret123", restored["Alex"]["password"]))
        self.assertFalse(verify_password("wrong", restored["Alex"]["password"]))

    def test_missing_store_starts_empty(self):
        with tempfile.TemporaryDirectory() as directory:
            restored = load_users_db(Path(directory) / "missing.json")

        self.assertEqual(restored, {})

    def test_plaintext_password_is_not_accepted(self):
        self.assertFalse(verify_password("secret123", "secret123"))

    def test_checkins_are_recorded_and_persisted_locally(self):
        users = {"Alex": {"password": hash_password("secret123")}}
        with (
            patch.object(database, "users_db", users),
            patch.object(database, "save_users_db") as save,
        ):
            record_checkin("Alex", "routine")
            record_checkin("Alex", "sound")

        events = json.loads(users["Alex"]["checkin_history"])
        self.assertEqual([event["kind"] for event in events], ["routine", "sound"])
        self.assertTrue(all(event["at"] for event in events))
        self.assertEqual(save.call_count, 2)

    def test_checkin_history_rejects_invalid_kinds(self):
        with self.assertRaises(ValueError):
            record_checkin("Alex", "unknown")

    def test_checkin_history_survives_database_round_trip(self):
        users = {"Alex": {"password": hash_password("secret123")}}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "users.json"
            with (
                patch.object(database, "users_db", users),
                patch.object(
                    database,
                    "save_users_db",
                    side_effect=lambda records: save_users_db(records, path),
                ),
            ):
                record_checkin("Alex", "sound")
            restored_users = load_users_db(path)
            with patch.object(database, "users_db", restored_users):
                history = database.get_checkin_history("Alex")

        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]["kind"], "sound")

    def test_failed_checkin_save_restores_previous_history(self):
        user = {"password": "hashed"}
        with (
            patch.object(database, "users_db", {"Alex": user}),
            patch.object(
                database, "save_users_db", side_effect=OSError("disk unavailable")
            ),
        ):
            with self.assertRaises(OSError):
                record_checkin("Alex", "routine")

        self.assertNotIn("checkin_history", user)


if __name__ == "__main__":
    unittest.main()
