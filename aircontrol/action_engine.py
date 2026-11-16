import time

from config import (
    GESTURE_HOLD_SECONDS, GESTURE_GRACE_SECONDS,
    ACTION_COOLDOWN_SECONDS, REPEAT_INTERVAL_SECONDS,
)

# What each action does. ("keys", combo) presses a shortcut; ("scroll", n) scrolls.
ACTION_SPECS = {
    "next_tab": ("keys", ("ctrl", "tab")),
    "previous_tab": ("keys", ("ctrl", "shift", "tab")),
    "new_tab": ("keys", ("ctrl", "t")),
    "close_tab": ("keys", ("ctrl", "w")),
    "switch_app": ("keys", ("alt", "tab")),
    "back": ("keys", ("alt", "left")),
    "forward": ("keys", ("alt", "right")),
    "show_desktop": ("keys", ("win", "d")),
    "play_pause": ("keys", ("playpause",)),
    "volume_up": ("keys", ("volumeup",)),
    "volume_down": ("keys", ("volumedown",)),
    "mute": ("keys", ("volumemute",)),
    "scroll_up": ("scroll", 500),
    "scroll_down": ("scroll", -500),
}

# These keep firing while the gesture is held; everything else fires once.
REPEATABLE = {"volume_up", "volume_down", "scroll_up", "scroll_down"}


def _pyautogui():
    import pyautogui
    pyautogui.FAILSAFE = False   # cursor in a screen corner must not abort actions
    pyautogui.PAUSE = 0
    return pyautogui


def send_action(spec):
    """Default executor. Uses explicit key-down/up so Alt+Tab and Win+D work."""
    kind, arg = spec
    gui = _pyautogui()
    if kind == "scroll":
        gui.scroll(arg)
        return
    *modifiers, key = arg
    pressed = []
    try:
        for mod in modifiers:
            gui.keyDown(mod)
            pressed.append(mod)
        if pressed:
            time.sleep(0.04)
        gui.press(key)
        if pressed:
            time.sleep(0.04)
    finally:
        for mod in reversed(pressed):
            gui.keyUp(mod)


class GestureActionEngine:
    """Fires a mapped action once a gesture has been held steadily."""

    def __init__(self, hold_seconds=GESTURE_HOLD_SECONDS,
                 cooldown_seconds=ACTION_COOLDOWN_SECONDS, executor=None,
                 grace_seconds=0.0, repeat_seconds=REPEAT_INTERVAL_SECONDS):
        self.hold_seconds = float(hold_seconds)
        self.cooldown_seconds = float(cooldown_seconds)
        self.grace_seconds = float(grace_seconds)
        self.repeat_seconds = float(repeat_seconds)
        self.executor = executor or send_action
        self.states = {}
        self.last_action_time = None

    def reset(self):
        self.states.clear()

    def forget(self, hand_id):
        self.states.pop(hand_id, None)

    def progress(self, hand_id, now=None):
        """0..1 hold progress for the hand's current gesture (1 = fired/ready)."""
        state = self.states.get(hand_id)
        if not state or state["gesture"] in (None, "UNKNOWN"):
            return 0.0
        if state["fired"]:
            return 1.0
        if self.hold_seconds <= 0:
            return 1.0
        now = time.monotonic() if now is None else now
        return max(0.0, min(1.0, (now - state["since"]) / self.hold_seconds))

    def execute(self, action):
        """Run an action immediately (used by the Test button)."""
        spec = ACTION_SPECS.get(action)
        if spec is None:
            return False
        self.executor(spec)
        return True

    def update(self, hand_id, gesture, mappings, now=None, enabled=False):
        """Return an action label only when an action is actually dispatched."""
        if now is None:
            now = time.monotonic()

        state = self.states.setdefault(hand_id, {
            "gesture": None, "since": now, "fired": False,
            "pending": None, "pending_since": now, "next_repeat": None,
        })

        if gesture != state["gesture"]:
            # Brief flicker to another gesture is ignored for grace_seconds.
            if state["gesture"] is not None and self.grace_seconds > 0:
                if state["pending"] != gesture:
                    state["pending"], state["pending_since"] = gesture, now
                if now - state["pending_since"] < self.grace_seconds:
                    return None
            state.update(gesture=gesture, since=now, fired=False,
                         pending=None, next_repeat=None)
            return None
        state["pending"] = None

        if gesture in (None, "UNKNOWN"):
            return None

        action = mappings.get(gesture, "none")

        # Held repeatable action (volume / scroll): keep firing at a fixed rate.
        if state["fired"] and state["next_repeat"] is not None:
            if not enabled or action not in REPEATABLE or now < state["next_repeat"]:
                return None
            return self._dispatch(state, action, now, repeating=True)

        if state["fired"] or now - state["since"] < self.hold_seconds:
            return None

        # Mark as fired even when disabled, so enabling actions while holding
        # a gesture does not unexpectedly execute it.
        state["fired"] = True
        if not enabled or action == "none":
            return None

        if (action not in REPEATABLE and self.last_action_time is not None
                and now - self.last_action_time < self.cooldown_seconds):
            return "Cooldown"

        return self._dispatch(state, action, now, repeating=False)

    def _dispatch(self, state, action, now, repeating):
        spec = ACTION_SPECS.get(action)
        if spec is None:
            return None
        try:
            self.executor(spec)
        except Exception as exc:
            return f"Action error: {type(exc).__name__}"
        self.last_action_time = now
        if action in REPEATABLE:
            state["next_repeat"] = now + self.repeat_seconds
        return action
