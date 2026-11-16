import os
import sys

# Hide Qt's harmless "SetProcessDpiAwarenessContext() failed" notice on Windows.
os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.window=false")

# Must run before MediaPipe is imported (Python 3.15 lazy-import workaround).
import aircontrol.py315_compat  # noqa: F401,E402

from PySide6.QtWidgets import QApplication
from aircontrol.main_window import MainWindow, apply_dark_theme


def main():
    app = QApplication(sys.argv)
    app.setApplicationName("AirControl")
    apply_dark_theme(app)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
