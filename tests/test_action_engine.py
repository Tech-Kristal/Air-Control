import unittest
from aircontrol.action_engine import GestureActionEngine


class ActionEngineTests(unittest.TestCase):
    def setUp(self):
        self.calls = []
        self.engine = GestureActionEngine(
            hold_seconds=0.5,
            cooldown_seconds=0.8,
            executor=lambda hotkey: self.calls.append(hotkey),
        )
        self.mappings = {"PEACE": "next_tab"}

    def test_requires_stable_gesture(self):
        self.assertIsNone(self.engine.update("Left", "PEACE", self.mappings, 1.0, True))
        self.assertIsNone(self.engine.update("Left", "PEACE", self.mappings, 1.2, True))
        self.assertEqual(self.engine.update("Left", "PEACE", self.mappings, 1.6, True), "next_tab")
        self.assertEqual(len(self.calls), 1)

    def test_fires_only_once_while_held(self):
        self.engine.update("Left", "PEACE", self.mappings, 1.0, True)
        self.engine.update("Left", "PEACE", self.mappings, 1.6, True)
        self.engine.update("Left", "PEACE", self.mappings, 2.0, True)
        self.assertEqual(len(self.calls), 1)

    def test_disabled_action_does_not_fire_later_while_held(self):
        self.engine.update("Left", "PEACE", self.mappings, 1.0, False)
        self.assertIsNone(self.engine.update("Left", "PEACE", self.mappings, 1.6, False))
        self.assertIsNone(self.engine.update("Left", "PEACE", self.mappings, 2.0, True))
        self.assertEqual(self.calls, [])

    def test_new_gesture_rearms_engine(self):
        self.engine.update("Left", "PEACE", self.mappings, 1.0, True)
        self.engine.update("Left", "PEACE", self.mappings, 1.6, True)
        self.engine.update("Left", "FIST", self.mappings, 2.0, True)
        self.engine.update("Left", "PEACE", self.mappings, 2.1, True)
        self.engine.update("Left", "PEACE", self.mappings, 2.7, True)
        self.assertEqual(len(self.calls), 2)

    def test_first_action_is_not_blocked_when_clock_starts_at_zero(self):
        engine = GestureActionEngine(
            hold_seconds=0,
            cooldown_seconds=1,
            executor=lambda hotkey: self.calls.append(hotkey),
        )
        engine.update("Left", "PEACE", self.mappings, 0.0, True)
        self.assertEqual(engine.update("Left", "PEACE", self.mappings, 0.1, True), "next_tab")

    def test_executor_error_is_reported(self):
        engine = GestureActionEngine(
            hold_seconds=0,
            cooldown_seconds=0,
            executor=lambda hotkey: (_ for _ in ()).throw(RuntimeError("test")),
        )
        engine.update("Right", "PEACE", self.mappings, 1.0, True)
        self.assertEqual(
            engine.update("Right", "PEACE", self.mappings, 1.1, True),
            "Action error: RuntimeError",
        )


if __name__ == "__main__":
    unittest.main()
