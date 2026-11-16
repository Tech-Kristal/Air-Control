import json
import tempfile
import unittest
from pathlib import Path

from aircontrol.mapping_store import (
    DEFAULT_MAPPINGS, load_mappings, save_mappings, validate_mappings
)


class MappingStoreTests(unittest.TestCase):
    def test_defaults_are_returned_for_missing_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_mappings(Path(tmp) / "missing.json"), DEFAULT_MAPPINGS)

    def test_save_and_reload_round_trip(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            expected = DEFAULT_MAPPINGS.copy()
            expected["OPEN_PALM"] = "switch_app"
            save_mappings(path, expected)
            self.assertEqual(load_mappings(path), expected)

    def test_invalid_action_is_rejected(self):
        data = DEFAULT_MAPPINGS.copy()
        data["FIST"] = "run_command"
        with self.assertRaises(ValueError):
            validate_mappings(data)

    def test_unknown_gesture_is_rejected(self):
        data = DEFAULT_MAPPINGS.copy()
        data["NOT_A_GESTURE"] = "none"
        with self.assertRaises(ValueError):
            validate_mappings(data)

    def test_non_string_action_is_rejected_cleanly(self):
        data = DEFAULT_MAPPINGS.copy()
        data["FIST"] = ["next_tab"]
        with self.assertRaises(ValueError):
            validate_mappings(data)

    def test_malformed_json_is_reported(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "settings.json"
            path.write_text("{bad json", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_mappings(path)


if __name__ == "__main__":
    unittest.main()
