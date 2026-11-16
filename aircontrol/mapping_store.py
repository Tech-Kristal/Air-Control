import json
import os
import tempfile
from pathlib import Path

GESTURES = (
    "OPEN_PALM", "FIST", "THUMBS_UP", "PEACE",
    "THREE_FINGERS", "POINT", "PINCH",
)

ACTIONS = {
    "none": "Do nothing",
    "next_tab": "Next tab",
    "previous_tab": "Previous tab",
    "new_tab": "New tab",
    "close_tab": "Close tab",
    "switch_app": "Switch window",
    "back": "Browser back",
    "forward": "Browser forward",
    "show_desktop": "Show desktop",
    "play_pause": "Play / pause",
    "volume_up": "Volume up",
    "volume_down": "Volume down",
    "mute": "Mute",
    "scroll_up": "Scroll up",
    "scroll_down": "Scroll down",
}

DEFAULT_MAPPINGS = {
    "OPEN_PALM": "none",
    "FIST": "none",
    "THUMBS_UP": "new_tab",
    "PEACE": "next_tab",
    "THREE_FINGERS": "previous_tab",
    "POINT": "none",
    "PINCH": "none",
}


def validate_mappings(data):
    if not isinstance(data, dict):
        raise ValueError("Gesture mappings must be a JSON object.")

    cleaned = {}
    for gesture in GESTURES:
        action = data.get(gesture, DEFAULT_MAPPINGS[gesture])
        if not isinstance(action, str) or action not in ACTIONS:
            raise ValueError(f"Unsupported action for {gesture}: {action!r}")
        cleaned[gesture] = action

    unknown = set(data) - set(GESTURES)
    if unknown:
        raise ValueError(f"Unknown gesture names: {', '.join(sorted(unknown))}")
    return cleaned


def load_mappings(path):
    path = Path(path)
    if not path.exists():
        return DEFAULT_MAPPINGS.copy()
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return validate_mappings(data)
    except (json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Could not load {path.name}: {exc}") from exc


def save_mappings(path, mappings):
    path = Path(path)
    cleaned = validate_mappings(mappings)
    path.parent.mkdir(parents=True, exist_ok=True)

    # Write to a temporary file and atomically replace the target to avoid
    # leaving a truncated settings file if the process is interrupted.
    temp_name = None
    try:
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=path.parent,
            delete=False, suffix=".tmp"
        ) as handle:
            temp_name = handle.name
            json.dump(cleaned, handle, indent=2)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        if temp_name and os.path.exists(temp_name):
            os.unlink(temp_name)
    return cleaned
