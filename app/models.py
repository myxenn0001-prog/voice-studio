"""Voice model "packs": what is downloaded for offline use, and downloading them on request."""
from __future__ import annotations

import importlib.util
import json
import threading

from .config import MODELS_DIR

PACKS = [
    {"id": "fast", "name": "Fast mode voices", "detail": "All built-in voices and languages. A few hundred MB."},
    {"id": "captions", "name": "Captions", "detail": "The Whisper Base model. About 150 MB."},
    {"id": "clone", "name": "Clone mode (voice cloning)", "detail": "Several GB, including the multilingual model."},
]
_IDS = {p["id"] for p in PACKS}
_MARKS = MODELS_DIR / ".ready.json"
_lock = threading.Lock()
_state = {"running": [], "message": "", "error": None}


def _marks() -> dict:
    try:
        return json.loads(_MARKS.read_text())
    except Exception:
        return {}


def mark_ready(pack: str) -> None:
    marks = _marks()
    marks[pack] = True
    _MARKS.write_text(json.dumps(marks))


def _cached(repo: str) -> bool:
    try:
        from huggingface_hub import snapshot_download

        snapshot_download(repo, local_files_only=True)
        return True
    except Exception:
        return False


def is_ready(pack: str) -> bool:
    marked = bool(_marks().get(pack))
    if pack == "fast":
        return marked or (_cached("hexgrad/Kokoro-82M") and importlib.util.find_spec("en_core_web_sm") is not None)
    if pack == "captions":
        return marked or _cached("Systran/faster-whisper-base")
    return marked  # clone: only counted once it was downloaded through Voice Studio


def status() -> dict:
    return {
        "packs": [dict(p, ready=is_ready(p["id"]), running=p["id"] in _state["running"]) for p in PACKS],
        "running": bool(_state["running"]),
        "message": _state["message"],
        "error": _state["error"],
    }


def _worker(packs: list[str]) -> None:
    from . import prefetch

    try:
        for pack in packs:
            _state["message"] = f"Downloading: {next(p['name'] for p in PACKS if p['id'] == pack)}…"
            prefetch.PACKS[pack]()
            mark_ready(pack)
            _state["running"].remove(pack)
        _state["message"] = "Done. These models now work without internet."
    except Exception as exc:
        _state["error"] = f"{exc}"
        _state["message"] = ""
    finally:
        _state["running"].clear()


def start(packs: list[str]) -> dict:
    packs = [p for p in packs if p in _IDS]
    if not packs:
        raise ValueError("Choose something to download.")
    with _lock:
        if _state["running"]:
            raise ValueError("A download is already running.")
        _state.update(running=list(packs), message="Starting…", error=None)
    threading.Thread(target=_worker, args=(packs,), daemon=True, name="model-download").start()
    return status()
