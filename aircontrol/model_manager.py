import ssl
import urllib.request
from pathlib import Path

from config import MODEL_FILENAME, MODEL_URL

ROOT = Path(__file__).resolve().parents[1]
MODELS_DIR = ROOT / "models"
MODEL_PATH = MODELS_DIR / MODEL_FILENAME
MIN_VALID_BYTES = 1_000_000  # the real model is ~7.8 MB


def _ssl_context():
    try:
        import certifi  # installed as a MediaPipe dependency
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        return ssl.create_default_context()


def ensure_model():
    """Return the model path, downloading it once if it is missing."""
    if MODEL_PATH.exists() and MODEL_PATH.stat().st_size >= MIN_VALID_BYTES:
        return MODEL_PATH

    MODELS_DIR.mkdir(parents=True, exist_ok=True)
    partial = MODEL_PATH.with_suffix(".tmp")
    try:
        with urllib.request.urlopen(MODEL_URL, timeout=60, context=_ssl_context()) as resp, \
                open(partial, "wb") as out:
            while True:
                chunk = resp.read(1 << 16)
                if not chunk:
                    break
                out.write(chunk)
        if partial.stat().st_size < MIN_VALID_BYTES:
            raise OSError("Downloaded model file is too small; the download was incomplete.")
        partial.replace(MODEL_PATH)
    finally:
        if partial.exists():
            partial.unlink()
    return MODEL_PATH


if __name__ == "__main__":
    print("Model ready:", ensure_model())
