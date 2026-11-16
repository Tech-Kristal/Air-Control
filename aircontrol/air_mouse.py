import math
import time

from config import (
    CURSOR_SMOOTHING_MIN, CURSOR_SMOOTHING_MAX, CURSOR_MARGIN,
    CLICK_COOLDOWN_SECONDS, PINCH_CLOSE_RATIO, PINCH_OPEN_RATIO,
)
from aircontrol.gesture_recognizer import pinch_ratio


class AirMouse:
    """Optional pointer controller. It is never enabled automatically."""

    def __init__(self, screen_size=None, mover=None, clicker=None):
        if mover is None or clicker is None or screen_size is None:
            import pyautogui
            pyautogui.FAILSAFE = False   # reaching a screen corner must not raise
            pyautogui.PAUSE = 0
            screen_size = screen_size or tuple(pyautogui.size())
            mover = mover or (lambda x, y: pyautogui.moveTo(x, y, _pause=False))
            clicker = clicker or pyautogui.click
        self.screen_w, self.screen_h = screen_size
        self._move, self._click = mover, clicker
        self.cursor_x = self.cursor_y = None
        self.last_click_time = 0.0
        self.pinched = False

    def update(self, points, now=None):
        """Move the pointer to the index fingertip; pinch = click. Returns True on click."""
        now = time.monotonic() if now is None else now
        ratio = pinch_ratio(points)

        # Hysteresis: must open well past the close threshold before re-arming.
        was_pinched = self.pinched
        if self.pinched:
            self.pinched = ratio < PINCH_OPEN_RATIO
        else:
            self.pinched = ratio < PINCH_CLOSE_RATIO

        # Freeze the pointer while closing the pinch so the click lands where
        # the finger was, not where it ends up after the thumb moves it.
        if not self.pinched and not was_pinched:
            self._follow(points[8])

        if self.pinched and not was_pinched and now - self.last_click_time >= CLICK_COOLDOWN_SECONDS:
            self._click()
            self.last_click_time = now
            return True
        return False

    def _follow(self, tip):
        m = CURSOR_MARGIN
        x = min(max((tip[0] - m) / (1 - 2 * m), 0.0), 1.0)
        y = min(max((tip[1] - m) / (1 - 2 * m), 0.0), 1.0)
        tx = 1 + x * (self.screen_w - 3)
        ty = 1 + y * (self.screen_h - 3)

        if self.cursor_x is None:
            self.cursor_x, self.cursor_y = tx, ty
        else:
            # Slow hand = heavy smoothing (steady). Fast hand = light smoothing (responsive).
            speed = math.hypot(tx - self.cursor_x, ty - self.cursor_y) / self.screen_w
            alpha = min(CURSOR_SMOOTHING_MAX,
                        CURSOR_SMOOTHING_MIN + speed * 6.0)
            self.cursor_x += (tx - self.cursor_x) * alpha
            self.cursor_y += (ty - self.cursor_y) * alpha
        self._move(int(self.cursor_x), int(self.cursor_y))

    def reset(self):
        self.cursor_x = self.cursor_y = None
        self.pinched = False
