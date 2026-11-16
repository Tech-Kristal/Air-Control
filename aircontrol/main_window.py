from pathlib import Path
import time

from PySide6.QtCore import Qt, Slot, QTimer, QRectF, QSize
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPalette, QPixmap
from PySide6.QtWidgets import (
    QAbstractButton, QApplication, QComboBox, QFrame, QHBoxLayout, QLabel,
    QMainWindow, QMessageBox, QPlainTextEdit, QProgressBar, QPushButton,
    QSizePolicy, QVBoxLayout, QWidget,
)

from config import APP_TITLE, GESTURE_HOLD_SECONDS, GESTURE_GRACE_SECONDS, ACTION_COOLDOWN_SECONDS
from aircontrol.mapping_store import (
    GESTURES, ACTIONS, DEFAULT_MAPPINGS, load_mappings, save_mappings,
)
from aircontrol.action_engine import GestureActionEngine, ACTION_SPECS
from aircontrol.air_mouse import AirMouse

ROOT = Path(__file__).resolve().parents[1]
MAPPING_PATH = ROOT / "gesture_mappings.json"

# One neutral palette, one accent. No gradients, no glow.
BG, SURFACE, SURFACE_2 = "#17181b", "#1f2024", "#26282d"
BORDER, TEXT, MUTED = "#2d3036", "#e8e9ec", "#8c919b"
ACCENT, WARN = "#5b8dff", "#d6a24a"

GESTURE_LABELS = {
    "OPEN_PALM": "Open palm", "FIST": "Fist", "THUMBS_UP": "Thumbs up",
    "PEACE": "Peace sign", "THREE_FINGERS": "Three fingers",
    "POINT": "Point", "PINCH": "Pinch",
}

STYLE = f"""
QMainWindow, QWidget#Root {{ background: {BG}; }}
QWidget {{ color: {TEXT}; font-family: "Segoe UI Variable", "Segoe UI", "Helvetica Neue", sans-serif; font-size: 10pt; }}
QFrame#Panel {{ background: {SURFACE}; border: 1px solid {BORDER}; border-radius: 10px; }}
QLabel {{ background: transparent; }}
QLabel#Title {{ font-size: 14pt; font-weight: 600; }}
QLabel#Section {{ color: {MUTED}; font-size: 9pt; font-weight: 600; }}
QLabel#Muted {{ color: {MUTED}; }}
QLabel#Hint {{ color: {MUTED}; font-size: 9pt; }}
QLabel#Banner {{ color: {WARN}; background: #2a2418; border: 1px solid #4a3d1f; border-radius: 8px; padding: 8px 10px; }}
QFrame#Row {{ background: transparent; border-radius: 8px; }}
QFrame#Row[active="true"] {{ background: {SURFACE_2}; }}
QPushButton {{ background: {SURFACE_2}; border: 1px solid {BORDER}; border-radius: 6px; padding: 5px 12px; }}
QPushButton:hover {{ border-color: #444851; }}
QPushButton:pressed {{ background: {BG}; }}
QPushButton:disabled {{ color: #5d616a; }}
QPushButton#Link {{ background: transparent; border: none; color: {MUTED}; padding: 2px 4px; }}
QPushButton#Link:hover {{ color: {TEXT}; }}
QPlainTextEdit {{ background: {BG}; border: 1px solid {BORDER}; border-radius: 8px; padding: 6px;
                  color: {MUTED}; font-family: "Cascadia Mono", Consolas, monospace; font-size: 9pt; }}
QProgressBar {{ background: transparent; border: none; max-height: 2px; min-height: 2px; }}
QProgressBar::chunk {{ background: {ACCENT}; border-radius: 1px; }}
"""


def apply_dark_theme(app: QApplication):
    """Fusion + a dark palette keeps native widgets (combo boxes etc.) consistent."""
    app.setStyle("Fusion")
    p = QPalette()
    for role, color in {
        QPalette.Window: BG, QPalette.WindowText: TEXT, QPalette.Base: SURFACE_2,
        QPalette.AlternateBase: SURFACE, QPalette.Text: TEXT, QPalette.Button: SURFACE_2,
        QPalette.ButtonText: TEXT, QPalette.ToolTipBase: SURFACE_2, QPalette.ToolTipText: TEXT,
        QPalette.Highlight: ACCENT, QPalette.HighlightedText: "#ffffff",
        QPalette.PlaceholderText: MUTED,
    }.items():
        p.setColor(role, QColor(color))
    p.setColor(QPalette.Disabled, QPalette.Text, QColor("#5d616a"))
    p.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#5d616a"))
    app.setPalette(p)


class Toggle(QAbstractButton):
    """Small on/off switch."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setCursor(Qt.PointingHandCursor)
        self.setFixedSize(38, 22)

    def sizeHint(self):
        return QSize(38, 22)

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHint(QPainter.Antialiasing)
        p.setPen(Qt.NoPen)
        p.setBrush(QColor(ACCENT if self.isChecked() else "#3a3d45"))
        p.drawRoundedRect(QRectF(0, 0, 38, 22), 11, 11)
        p.setBrush(QColor("#ffffff"))
        x = 19 if self.isChecked() else 3
        p.drawEllipse(QRectF(x, 3, 16, 16))


class VideoView(QWidget):
    """Camera image, aspect-fit, rounded corners, drawn directly (no QLabel rescale)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.pixmap = None
        self.message = "Starting camera…"
        self.setMinimumSize(520, 340)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

    def set_image(self, image):
        self.pixmap = QPixmap.fromImage(image)
        self.update()

    def set_message(self, text):
        if self.pixmap is None:
            self.message = text
            self.update()

    def paintEvent(self, _):
        p = QPainter(self)
        p.setRenderHints(QPainter.Antialiasing | QPainter.SmoothPixmapTransform)
        outer = QRectF(self.rect())
        clip = QPainterPath()
        clip.addRoundedRect(outer, 10, 10)
        p.setClipPath(clip)
        p.fillRect(outer, QColor("#0e0f11"))
        if self.pixmap is None:
            p.setPen(QColor(MUTED))
            p.drawText(outer.adjusted(24, 0, -24, 0), Qt.AlignCenter | Qt.TextWordWrap, self.message)
            return
        pw, ph = self.pixmap.width(), self.pixmap.height()
        scale = min(outer.width() / pw, outer.height() / ph)
        w, h = pw * scale, ph * scale
        target = QRectF(outer.x() + (outer.width() - w) / 2, outer.y() + (outer.height() - h) / 2, w, h)
        p.drawPixmap(target, self.pixmap, QRectF(self.pixmap.rect()))


class GestureRow(QFrame):
    def __init__(self, gesture, on_change, on_test):
        super().__init__()
        self.gesture = gesture
        self.setObjectName("Row")
        self.setProperty("active", False)

        outer = QVBoxLayout(self)
        outer.setContentsMargins(10, 3, 10, 1)
        outer.setSpacing(2)
        line = QHBoxLayout()
        line.setSpacing(8)
        name = QLabel(GESTURE_LABELS[gesture])
        name.setMinimumWidth(96)
        self.combo = QComboBox()
        for key, label in ACTIONS.items():
            self.combo.addItem(label, key)
        self.combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo.currentIndexChanged.connect(lambda _=None: on_change())
        self.test = QPushButton("Test")
        self.test.setToolTip("Runs this action in 3 seconds, so you can click the target app first.")
        self.test.clicked.connect(lambda: on_test(self.action()))
        line.addWidget(name)
        line.addWidget(self.combo, 1)
        line.addWidget(self.test)
        outer.addLayout(line)
        self.bar = QProgressBar()
        self.bar.setRange(0, 100)
        self.bar.setTextVisible(False)
        outer.addWidget(self.bar)

    def action(self):
        return self.combo.currentData()

    def set_action(self, action):
        self.combo.blockSignals(True)
        self.combo.setCurrentIndex(max(self.combo.findData(action), 0))
        self.combo.blockSignals(False)

    def set_live(self, active, progress):
        if self.property("active") != active:
            self.setProperty("active", active)
            self.style().unpolish(self)
            self.style().polish(self)
        self.bar.setValue(int(progress * 100) if active else 0)


class SwitchRow(QWidget):
    def __init__(self, title, caption):
        super().__init__()
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        col = QVBoxLayout()
        col.setSpacing(1)
        col.addWidget(QLabel(title))
        hint = QLabel(caption)
        hint.setObjectName("Hint")
        hint.setWordWrap(True)
        col.addWidget(hint)
        lay.addLayout(col, 1)
        self.toggle = Toggle()
        lay.addWidget(self.toggle, 0, Qt.AlignVCenter)


class MainWindow(QMainWindow):
    def __init__(self, start_camera=True):
        super().__init__()
        self.setWindowTitle(APP_TITLE)
        self.resize(1180, 760)
        self.setMinimumSize(1000, 700)
        self.setStyleSheet(STYLE)

        self.worker = None
        self.actions_enabled = False
        self.mouse_enabled = False
        self.engine = GestureActionEngine(
            hold_seconds=GESTURE_HOLD_SECONDS,
            cooldown_seconds=ACTION_COOLDOWN_SECONDS,
            grace_seconds=GESTURE_GRACE_SECONDS,
        )
        self.air_mouse = None
        self._pending_test = None

        try:
            self.mappings = load_mappings(MAPPING_PATH)
        except ValueError as exc:
            self.mappings = DEFAULT_MAPPINGS.copy()
            QMessageBox.warning(self, "Mapping file issue",
                                f"{exc}\n\nDefaults were loaded. Changing any mapping replaces the file.")

        self._build_ui()
        self._load_rows()
        self._refresh_banner()
        self.log("Ready. Turn on “Gesture actions” when recognition looks right.")
        if start_camera:
            self._start_camera()

    # ------------------------------------------------------------------ UI
    def _build_ui(self):
        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(20)

        # Left: camera
        left = QVBoxLayout()
        left.setSpacing(10)
        top = QHBoxLayout()
        title = QLabel(APP_TITLE)
        title.setObjectName("Title")
        top.addWidget(title)
        top.addStretch()
        self.stats_label = QLabel("")
        self.stats_label.setObjectName("Muted")
        top.addWidget(self.stats_label)
        left.addLayout(top)

        self.video = VideoView()
        left.addWidget(self.video, 1)

        self.banner = QLabel()
        self.banner.setObjectName("Banner")
        self.banner.setWordWrap(True)
        left.addWidget(self.banner)

        self.status_label = QLabel("Starting camera…")
        self.status_label.setObjectName("Muted")
        self.status_label.setWordWrap(True)
        left.addWidget(self.status_label)
        layout.addLayout(left, 1)

        # Right: controls
        panel = QFrame()
        panel.setObjectName("Panel")
        panel.setFixedWidth(380)
        side = QVBoxLayout(panel)
        side.setContentsMargins(16, 16, 16, 16)
        side.setSpacing(8)

        side.addWidget(self._section("CONTROL"))
        self.actions_row = SwitchRow("Gesture actions", "Send the mapped shortcuts to the app you’re using.")
        self.actions_row.toggle.toggled.connect(self._toggle_actions)
        side.addWidget(self.actions_row)
        self.mouse_row = SwitchRow("Air mouse", "Point to move the cursor, pinch to click.")
        self.mouse_row.toggle.toggled.connect(self._toggle_mouse)
        side.addWidget(self.mouse_row)
        self.top_row = SwitchRow("Keep on top", "So you can see feedback while another app is focused.")
        self.top_row.toggle.toggled.connect(self._toggle_on_top)
        side.addWidget(self.top_row)

        head = QHBoxLayout()
        head.addWidget(self._section("GESTURES"))
        head.addStretch()
        reset = QPushButton("Reset")
        reset.setObjectName("Link")
        reset.setCursor(Qt.PointingHandCursor)
        reset.clicked.connect(self._reset_mappings)
        head.addWidget(reset)
        side.addLayout(head)

        self.rows = {}
        for gesture in GESTURES:
            row = GestureRow(gesture, self._save_mappings, self._schedule_test)
            self.rows[gesture] = row
            side.addWidget(row)

        side.addWidget(self._section("ACTIVITY"))
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(60)
        self.log_view.setFixedHeight(96)
        side.addWidget(self.log_view)
        side.addStretch()
        layout.addWidget(panel)

    @staticmethod
    def _section(text):
        label = QLabel(text)
        label.setObjectName("Section")
        return label

    def _load_rows(self):
        for gesture, row in self.rows.items():
            row.set_action(self.mappings.get(gesture, "none"))

    def log(self, text):
        self.log_view.appendPlainText(f"{time.strftime('%H:%M:%S')}  {text}")

    def _set_status(self, text):
        self.status_label.setText(text)
        self.video.set_message(text)

    def _refresh_banner(self):
        focused = self.isActiveWindow()
        show = self.actions_enabled and focused
        self.banner.setVisible(show)
        if show:
            self.banner.setText(
                "AirControl is the focused window, so shortcuts are held back. "
                "Click the app you want to control (turn on “Keep on top” to keep this window visible)."
            )

    # ------------------------------------------------------------ mappings
    def _save_mappings(self):
        data = {g: r.action() for g, r in self.rows.items()}
        try:
            self.mappings = save_mappings(MAPPING_PATH, data)
            self.engine.reset()
        except (OSError, ValueError) as exc:
            QMessageBox.critical(self, "Could not save mappings", str(exc))

    def _reset_mappings(self):
        self.mappings = DEFAULT_MAPPINGS.copy()
        self._load_rows()
        self._save_mappings()
        self.log("Mappings reset to defaults.")

    def _schedule_test(self, action):
        if action == "none":
            self.log("Nothing to test: this gesture is set to “Do nothing”.")
            return
        self.log(f"Running “{ACTIONS[action]}” in 3 s. Click the target app now.")
        QTimer.singleShot(3000, lambda: self._run_test(action))

    def _run_test(self, action):
        try:
            self.engine.execute(action)
            self.log(f"Test ran: {ACTIONS[action]}")
        except Exception as exc:
            self.log(f"Test failed: {type(exc).__name__}: {exc}")

    # ------------------------------------------------------------- toggles
    def _toggle_actions(self, checked):
        self.actions_enabled = checked
        self.engine.reset()
        self.log("Gesture actions on." if checked else "Gesture actions off.")
        self._refresh_banner()

    def _toggle_mouse(self, checked):
        self.engine.reset()
        if not checked:
            self.mouse_enabled = False
            self.air_mouse = None
            self.log("Air mouse off.")
            return
        try:
            self.air_mouse = AirMouse()
            self.mouse_enabled = True
            self.log("Air mouse on: point with your index finger, pinch to click.")
        except Exception as exc:
            self.mouse_enabled = False
            self.mouse_row.toggle.blockSignals(True)
            self.mouse_row.toggle.setChecked(False)
            self.mouse_row.toggle.blockSignals(False)
            QMessageBox.warning(self, "Air mouse unavailable", f"{type(exc).__name__}: {exc}")

    def _toggle_on_top(self, checked):
        self.setWindowFlag(Qt.WindowStaysOnTopHint, checked)
        self.show()   # changing window flags hides the window

    # -------------------------------------------------------------- camera
    def _start_camera(self):
        from aircontrol.camera_worker import CameraWorker
        self.worker = CameraWorker(self)
        self.worker.frame_ready.connect(self._on_frame)
        self.worker.status_changed.connect(self._on_worker_status)
        self.worker.start()

    @Slot(str)
    def _on_worker_status(self, text):
        self._set_status(text)

    @Slot(object, object, float)
    def _on_frame(self, image, hands, fps):
        self.video.set_image(image)
        self._refresh_banner()
        now = time.monotonic()
        self.stats_label.setText(f"{len(hands)} hand{'s' if len(hands) != 1 else ''}   ·   {fps:.0f} fps")

        # The hand that drives the cursor: first one pointing or pinching.
        mouse_hand = None
        if self.mouse_enabled and self.air_mouse:
            mouse_hand = next((h for h in hands if h["gesture"] in ("POINT", "PINCH")), None)
            if mouse_hand is None:
                self.air_mouse.reset()
            else:
                try:
                    if self.air_mouse.update(mouse_hand["landmarks"], now):
                        self.log("Click")
                except Exception as exc:
                    self.log(f"Air mouse error: {type(exc).__name__}: {exc}")

        can_send = self.actions_enabled and not self.isActiveWindow()
        live = {}
        present = set()
        for hand in hands:
            hid, gesture = hand["id"], hand["gesture"]
            present.add(hid)
            if hand is mouse_hand:
                self.engine.forget(hid)
                live[gesture] = max(live.get(gesture, 0.0), 1.0)
                continue
            action = self.engine.update(hid, gesture, self.mappings, now=now, enabled=can_send)
            if gesture in self.rows:
                live[gesture] = max(live.get(gesture, 0.0), self.engine.progress(hid, now))
            if action:
                self.log(f"{hid} · {GESTURE_LABELS.get(gesture, gesture)} → "
                         f"{ACTIONS.get(action, action)}")

        for stale in set(self.engine.states) - present:
            self.engine.forget(stale)
        for gesture, row in self.rows.items():
            row.set_live(gesture in live, live.get(gesture, 0.0))

    def closeEvent(self, event):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        event.accept()
