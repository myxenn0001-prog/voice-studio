"""Paths and persisted user settings."""
import json
import os
import threading
import time
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = Path(os.environ.get("VOICESTUDIO_DATA", APP_DIR.parent / "data")).resolve()
VOICES_DIR = DATA_DIR / "voices"
OUTPUTS_DIR = DATA_DIR / "outputs"
PREVIEWS_DIR = DATA_DIR / "previews"
MODELS_DIR = Path(os.environ.get("HF_HOME", DATA_DIR / "models")).resolve()

for _d in (DATA_DIR, VOICES_DIR, OUTPUTS_DIR, PREVIEWS_DIR, MODELS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# Models are downloaded once into MODELS_DIR, then run fully offline.
os.environ.setdefault("HF_HOME", str(MODELS_DIR))
# Lets Apple Silicon fall back to CPU for ops MPS doesn't support yet.
os.environ.setdefault("PYTORCH_ENABLE_MPS_FALLBACK", "1")

SETTINGS_FILE = DATA_DIR / "settings.json"
DEFAULT_SETTINGS = {
    "device": "auto",          # auto | cpu | cuda | mps
    "default_engine": "auto",  # auto | kokoro | chatterbox
    "cpu_threads": 0,          # 0 = use all cores
    "output_format": "wav",    # wav | flac | mp3
    "terms_accepted": "",      # version of the Terms of Use the user accepted
    "terms_accepted_at": 0,
}
_lock = threading.Lock()


def load_settings() -> dict:
    with _lock:
        data = dict(DEFAULT_SETTINGS)
        if SETTINGS_FILE.exists():
            try:
                data.update(json.loads(SETTINGS_FILE.read_text()))
            except Exception:
                pass
        return data


def save_settings(patch: dict) -> dict:
    allowed = {
        "device": {"auto", "cpu", "cuda", "mps"},
        "default_engine": None,
        "cpu_threads": None,
        "output_format": {"wav", "flac", "mp3"},
    }
    current = load_settings()
    for key, value in patch.items():
        if key not in allowed:
            continue
        if allowed[key] is not None and value not in allowed[key]:
            raise ValueError(f"Invalid value for {key}: {value}")
        if key == "cpu_threads":
            value = max(0, min(int(value), 256))
        current[key] = value
    with _lock:
        SETTINGS_FILE.write_text(json.dumps(current, indent=2))
    return current


def record_terms(version: str) -> None:
    current = load_settings()
    current["terms_accepted"] = version
    current["terms_accepted_at"] = int(time.time())
    with _lock:
        SETTINGS_FILE.write_text(json.dumps(current, indent=2))
