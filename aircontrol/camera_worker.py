import time
import traceback
import aircontrol.py315_compat  # noqa: F401  (must precede mediapipe)
import cv2
import mediapipe as mp
from mediapipe.tasks.python import BaseOptions
from mediapipe.tasks.python import vision as mp_vision
from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QImage

from config import (
    CAMERA_INDEX, CAMERA_WIDTH, CAMERA_HEIGHT, MAX_HANDS,
    MIN_DETECTION_CONFIDENCE, MIN_TRACKING_CONFIDENCE,
)
from aircontrol.gesture_recognizer import GestureRecognizer
from aircontrol.model_manager import ensure_model

CONNECTIONS = [
    (0, 1), (1, 2), (2, 3), (3, 4),
    (0, 5), (5, 6), (6, 7), (7, 8),
    (5, 9), (9, 10), (10, 11), (11, 12),
    (9, 13), (13, 14), (14, 15), (15, 16),
    (13, 17), (17, 18), (18, 19), (19, 20),
    (0, 17),
]


def open_camera():
    """Try the configured camera and common Windows capture backends."""
    # Try the configured index first, then other common camera indices.
    indices = [CAMERA_INDEX] + [i for i in range(5) if i != CAMERA_INDEX]
    backends = [
        ("DirectShow", cv2.CAP_DSHOW),
        ("Media Foundation", cv2.CAP_MSMF),
        ("OpenCV default", cv2.CAP_ANY),
    ]
    attempts = []
    for index in indices:
        for backend_name, backend in backends:
            cap = None
            try:
                cap = cv2.VideoCapture(index, backend)
                if cap is not None and cap.isOpened():
                    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter_fourcc(*"MJPG"))
                    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA_WIDTH)
                    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA_HEIGHT)
                    cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)
                    # Some drivers report opened before delivering a frame.
                    ok, frame = cap.read()
                    if ok and frame is not None and frame.size:
                        return cap, index, backend_name
                attempts.append(f"camera {index}/{backend_name}: no frame")
            except Exception as exc:
                attempts.append(f"camera {index}/{backend_name}: {type(exc).__name__}")
            if cap is not None:
                cap.release()
    return None, None, "; ".join(attempts[-6:])


def draw_hand(frame, points):
    """Draw the hand skeleton (the old mp.solutions.drawing_utils is gone)."""
    h, w = frame.shape[:2]
    pixels = [(int(x * w), int(y * h)) for x, y, _ in points]
    for a, b in CONNECTIONS:
        cv2.line(frame, pixels[a], pixels[b], (235, 235, 235), 2, cv2.LINE_AA)
    for p in pixels:
        cv2.circle(frame, p, 4, (255, 141, 91), -1, cv2.LINE_AA)


class CameraWorker(QThread):
    frame_ready = Signal(QImage, object, float)
    status_changed = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._running = True
        self.recognizer = GestureRecognizer()

    def stop(self):
        self._running = False
        # Do not destroy a running QThread. Wait for the capture loop's
        # finally block to release MediaPipe and the camera cleanly.
        self.wait()

    def run(self):
        camera, camera_index, backend_name = open_camera()
        if camera is None:
            self.status_changed.emit(
                "No webcam could be opened. Close Camera/Zoom/Teams/browser tabs, "
                "allow desktop apps under Windows Settings > Privacy & security > Camera, "
                f"then retry. Probe results: {backend_name}"
            )
            return

        landmarker = None
        error_message = None
        try:
            self.status_changed.emit("Preparing hand model…")
            model_path = ensure_model()
            options = mp_vision.HandLandmarkerOptions(
                base_options=BaseOptions(model_asset_path=str(model_path)),
                running_mode=mp_vision.RunningMode.VIDEO,
                num_hands=MAX_HANDS,
                min_hand_detection_confidence=MIN_DETECTION_CONFIDENCE,
                min_hand_presence_confidence=MIN_DETECTION_CONFIDENCE,
                min_tracking_confidence=MIN_TRACKING_CONFIDENCE,
            )
            landmarker = mp_vision.HandLandmarker.create_from_options(options)

            self.status_changed.emit(f"Camera {camera_index} running ({backend_name}) — show one or both hands.")
            previous = time.perf_counter()
            start = previous
            last_ts_ms = -1
            failures = 0
            fps = 0.0

            while self._running:
                ok, frame = camera.read()
                if not ok or frame is None:
                    failures += 1
                    if failures > 30:
                        self.status_changed.emit("Camera stopped delivering frames.")
                        break
                    time.sleep(0.03)
                    continue
                failures = 0

                frame = cv2.flip(frame, 1)
                rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                mp_image = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)

                # VIDEO mode requires strictly increasing timestamps.
                ts_ms = int((time.perf_counter() - start) * 1000)
                if ts_ms <= last_ts_ms:
                    ts_ms = last_ts_ms + 1
                last_ts_ms = ts_ms

                results = landmarker.detect_for_video(mp_image, ts_ms)
                found = []

                used = set()
                for index, hand_landmarks in enumerate(results.hand_landmarks):
                    points = [(p.x, p.y, p.z) for p in hand_landmarks]
                    label = "Hand " + str(index + 1)
                    if index < len(results.handedness) and results.handedness[index]:
                        # The frame is flipped *before* detection, so MediaPipe's
                        # label already matches what the user sees.
                        label = results.handedness[index][0].category_name
                    if label in used:           # two hands labelled the same
                        label = "Hand " + str(index + 1)
                    used.add(label)
                    draw_hand(frame, points)
                    gesture = self.recognizer.recognize(points)
                    found.append({
                        "id": label,
                        "gesture": gesture,
                        "landmarks": points,
                    })

                    px = int(points[0][0] * frame.shape[1])
                    py = min(frame.shape[0] - 12, int(points[0][1] * frame.shape[0]) + 28)
                    text = f"{label}  {gesture.replace('_', ' ').title()}"
                    (tw, th), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.6, 1)
                    cv2.rectangle(frame, (px - 8, py - th - 8), (px + tw + 8, py + 8),
                                  (30, 28, 26), -1)
                    cv2.putText(frame, text, (px, py), cv2.FONT_HERSHEY_SIMPLEX,
                                0.6, (240, 240, 240), 1, cv2.LINE_AA)

                now = time.perf_counter()
                fps = 0.9 * fps + 0.1 * (1.0 / max(now - previous, 1e-6)) if fps else 30.0
                previous = now

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                h, w, channels = rgb_frame.shape
                image = QImage(
                    rgb_frame.data, w, h, channels * w, QImage.Format.Format_RGB888
                ).copy()
                self.frame_ready.emit(image, found, float(fps))

        except Exception as exc:
            error_message = f"Camera error: {type(exc).__name__}: {exc}"
            print("\n[AIRCONTROL CAMERA ERROR]", flush=True)
            traceback.print_exc()
            self.status_changed.emit(error_message)
        finally:
            try:
                if landmarker is not None:
                    landmarker.close()
            except Exception:
                print("[AIRCONTROL] Error while closing MediaPipe:", flush=True)
                traceback.print_exc()
            try:
                camera.release()
            except Exception:
                print("[AIRCONTROL] Error while releasing camera:", flush=True)
                traceback.print_exc()
            # Do not overwrite the useful exception with a generic stop message.
            if error_message is None:
                self.status_changed.emit("Camera stopped.")
            else:
                self.status_changed.emit(error_message)
