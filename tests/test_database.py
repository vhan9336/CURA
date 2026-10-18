import tempfile
import unittest
from datetime import time
from pathlib import Path
from unittest.mock import patch

from src import database
from src.database import hash_password, load_users_db, save_users_db, verify_password


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


if __name__ == "__main__":
    unittest.main()
