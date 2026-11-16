CAMERA_INDEX = 0
CAMERA_WIDTH = 1280
CAMERA_HEIGHT = 720
MAX_HANDS = 2
MIN_DETECTION_CONFIDENCE = 0.60
MIN_TRACKING_CONFIDENCE = 0.55

# --- Gesture actions -------------------------------------------------------
GESTURE_HOLD_SECONDS = 0.45      # how long a gesture must be held before it fires
GESTURE_GRACE_SECONDS = 0.20     # ignore brief recognition flicker (< this long)
ACTION_COOLDOWN_SECONDS = 0.80   # minimum gap between two one-shot actions
REPEAT_INTERVAL_SECONDS = 0.35   # repeat rate for volume / scroll while held

# --- Air mouse -------------------------------------------------------------
CURSOR_SMOOTHING_MIN = 0.12      # smoothing when the hand is slow (steady)
CURSOR_SMOOTHING_MAX = 0.65      # smoothing when the hand moves fast (responsive)
CURSOR_MARGIN = 0.12             # unused border of the camera frame
CLICK_COOLDOWN_SECONDS = 0.45

# Pinch is measured relative to hand size so it works at any distance.
PINCH_CLOSE_RATIO = 0.28         # thumb-index gap / palm size below this = pinched
PINCH_OPEN_RATIO = 0.42          # must open past this before the next pinch counts

APP_TITLE = "AirControl"

# MediaPipe Tasks needs a hand landmark model file (downloaded once by setup.bat).
MODEL_FILENAME = "hand_landmarker.task"
MODEL_URL = (
    "https://storage.googleapis.com/mediapipe-models/hand_landmarker/"
    "hand_landmarker/float16/1/hand_landmarker.task"
)
