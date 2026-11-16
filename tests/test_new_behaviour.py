import math
import unittest

from aircontrol.action_engine import GestureActionEngine, ACTION_SPECS, REPEATABLE
from aircontrol.air_mouse import AirMouse
from aircontrol.gesture_recognizer import GestureRecognizer
from aircontrol.mapping_store import ACTIONS
from tests.test_gesture_recognizer import make_hand


def rotate(points, degrees):
    a = math.radians(degrees)
    cx, cy = 0.5, 0.5
    out = []
    for x, y, z in points:
        dx, dy = x - cx, y - cy
        out.append((cx + dx * math.cos(a) - dy * math.sin(a),
                    cy + dx * math.sin(a) + dy * math.cos(a), z))
    return out


class ActionCoverage(unittest.TestCase):
    def test_every_selectable_action_has_a_spec(self):
        for key in ACTIONS:
            if key != "none":
                self.assertIn(key, ACTION_SPECS, key)

    def test_repeatable_actions_exist(self):
        self.assertTrue(REPEATABLE <= set(ACTION_SPECS))


class EngineBehaviour(unittest.TestCase):
    def test_flicker_is_ignored_with_grace(self):
        calls = []
        e = GestureActionEngine(hold_seconds=0.5, cooldown_seconds=0,
                                grace_seconds=0.2, executor=calls.append)
        m = {"PEACE": "next_tab"}
        e.update("L", "PEACE", m, 0.0, True)
        e.update("L", "UNKNOWN", m, 0.2, True)   # one bad frame
        e.update("L", "PEACE", m, 0.25, True)
        self.assertEqual(e.update("L", "PEACE", m, 0.6, True), "next_tab")

    def test_volume_repeats_while_held(self):
        calls = []
        e = GestureActionEngine(hold_seconds=0.1, cooldown_seconds=5,
                                repeat_seconds=0.3, executor=calls.append)
        m = {"FIST": "volume_up"}
        for t in (0.0, 0.2, 0.5, 0.9, 1.3):
            e.update("L", "FIST", m, t, True)
        self.assertGreaterEqual(len(calls), 3)

    def test_progress_reaches_one(self):
        e = GestureActionEngine(hold_seconds=1.0, executor=lambda s: None)
        e.update("L", "FIST", {}, 0.0, True)
        self.assertAlmostEqual(e.progress("L", 0.5), 0.5)
        self.assertEqual(e.progress("L", 2.0), 1.0)


class RecognizerRotation(unittest.TestCase):
    def test_peace_when_hand_is_tilted(self):
        r = GestureRecognizer()
        hand = rotate(make_hand({"index", "middle"}), 35)
        self.assertEqual(r.recognize(hand), "PEACE")

    def test_open_palm_without_thumb(self):
        r = GestureRecognizer()
        self.assertEqual(r.recognize(make_hand({"index", "middle", "ring", "pinky"})), "OPEN_PALM")


class AirMouseBehaviour(unittest.TestCase):
    def setUp(self):
        self.moves, self.clicks = [], []
        self.mouse = AirMouse((1920, 1080), lambda x, y: self.moves.append((x, y)),
                              lambda: self.clicks.append(1))

    def test_never_touches_screen_corner(self):
        pts = make_hand({"index"})
        pts[8] = (0.0, 0.0, 0.0)
        self.mouse.update(pts, 0.0)
        self.assertGreaterEqual(min(self.moves[-1]), 1)
        pts[8] = (1.0, 1.0, 0.0)
        for t in range(40):
            self.mouse.update(pts, t)
        self.assertLessEqual(self.moves[-1][0], 1918)
        self.assertLessEqual(self.moves[-1][1], 1078)

    def test_single_click_per_pinch(self):
        open_hand = make_hand({"index"})
        pinch = make_hand({"index"}, pinch=True)
        self.mouse.update(open_hand, 0.0)
        for t in (1.0, 1.1, 1.2):
            self.mouse.update(pinch, t)
        self.assertEqual(len(self.clicks), 1)
        self.mouse.update(open_hand, 2.0)
        self.mouse.update(pinch, 3.0)
        self.assertEqual(len(self.clicks), 2)

    def test_cursor_frozen_during_pinch(self):
        open_hand = make_hand({"index"})
        self.mouse.update(open_hand, 0.0)
        n = len(self.moves)
        self.mouse.update(make_hand({"index"}, pinch=True), 1.0)
        self.assertEqual(len(self.moves), n)


if __name__ == "__main__":
    unittest.main()
