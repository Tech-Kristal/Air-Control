import unittest
from aircontrol.gesture_recognizer import GestureRecognizer


def make_hand(raised=(), thumb_extended=False, thumbs_up=False, pinch=False):
    # Synthetic normalized landmarks. This validates classifier rules,
    # not the accuracy of real webcam landmark estimation.
    points = [(0.50, 0.80, 0.0) for _ in range(21)]
    finger_parts = {
        "index": (5, 6, 8),
        "middle": (9, 10, 12),
        "ring": (13, 14, 16),
        "pinky": (17, 18, 20),
    }
    for name, (mcp, pip, tip) in finger_parts.items():
        points[mcp] = (0.50, 0.65, 0.0)
        points[pip] = (0.50, 0.58, 0.0)
        points[tip] = (0.50, 0.40 if name in raised else 0.78, 0.0)

    points[2] = (0.42, 0.70, 0.0)
    points[3] = (0.36, 0.65, 0.0)
    if thumb_extended:
        points[4] = (0.20, 0.60 if not thumbs_up else 0.25, 0.0)
    else:
        points[4] = (0.48, 0.70, 0.0)
    if pinch:
        points[4] = points[8]
    return points


class GestureRecognizerTests(unittest.TestCase):
    def setUp(self):
        self.recognizer = GestureRecognizer()

    def test_rejects_invalid_landmark_count(self):
        self.assertEqual(self.recognizer.recognize([]), "UNKNOWN")

    def test_peace(self):
        self.assertEqual(
            self.recognizer.recognize(make_hand({"index", "middle"})),
            "PEACE",
        )

    def test_three_fingers(self):
        self.assertEqual(
            self.recognizer.recognize(make_hand({"index", "middle", "ring"})),
            "THREE_FINGERS",
        )

    def test_point(self):
        self.assertEqual(
            self.recognizer.recognize(make_hand({"index"})),
            "POINT",
        )

    def test_open_palm(self):
        self.assertEqual(
            self.recognizer.recognize(
                make_hand({"index", "middle", "ring", "pinky"}, True)
            ),
            "OPEN_PALM",
        )

    def test_fist(self):
        self.assertEqual(self.recognizer.recognize(make_hand()), "FIST")

    def test_thumbs_up(self):
        self.assertEqual(
            self.recognizer.recognize(make_hand(thumb_extended=True, thumbs_up=True)),
            "THUMBS_UP",
        )

    def test_pinch(self):
        self.assertEqual(
            self.recognizer.recognize(make_hand({"index"}, pinch=True)),
            "PINCH",
        )


if __name__ == "__main__":
    unittest.main()
