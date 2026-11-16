import math

from config import PINCH_CLOSE_RATIO


def _dist(a, b):
    return math.hypot(a[0] - b[0], a[1] - b[1])


def palm_size(points):
    """Wrist -> middle-finger knuckle. Used to make every threshold scale-free."""
    return max(_dist(points[0], points[9]), 1e-6)


def pinch_ratio(points):
    """Thumb-tip / index-tip gap divided by palm size (small = pinching)."""
    return _dist(points[4], points[8]) / palm_size(points)


class GestureRecognizer:
    """Rule-based recognizer for MediaPipe's 21 normalized hand landmarks.

    Fingers are judged by distance from the wrist rather than by "tip above
    knuckle", so the hand can be tilted or rotated and still be recognized.
    """

    @staticmethod
    def _finger_extended(points, tip, pip):
        return _dist(points[0], points[tip]) > _dist(points[0], points[pip]) * 1.12

    @staticmethod
    def _thumb_extended(points):
        # Tip is clearly farther from the pinky knuckle than the thumb's own joint.
        return _dist(points[4], points[17]) > _dist(points[3], points[17]) * 1.15

    def recognize(self, points):
        if points is None or len(points) != 21:
            return "UNKNOWN"

        if pinch_ratio(points) < PINCH_CLOSE_RATIO:
            return "PINCH"

        index = self._finger_extended(points, 8, 6)
        middle = self._finger_extended(points, 12, 10)
        ring = self._finger_extended(points, 16, 14)
        pinky = self._finger_extended(points, 20, 18)
        thumb = self._thumb_extended(points)
        count = index + middle + ring + pinky

        if count == 4:
            return "OPEN_PALM"
        if count == 0:
            palm = palm_size(points)
            thumb_is_up = points[4][1] < points[5][1] - palm * 0.5
            if thumb and thumb_is_up:
                return "THUMBS_UP"
            return "FIST"
        if index and middle and not ring and not pinky:
            return "PEACE"
        if index and middle and ring and not pinky:
            return "THREE_FINGERS"
        if index and not middle and not ring and not pinky:
            return "POINT"
        return "UNKNOWN"
