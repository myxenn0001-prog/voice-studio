"""Hardware detection and engine recommendation."""
import json
import os
import platform
from pathlib import Path

import psutil

from . import legal


def detect_devices() -> list[dict]:
    devices = [{"id": "cpu", "label": f"CPU ({os.cpu_count()} cores)"}]
    try:
        import torch

        if torch.cuda.is_available():
            devices.append({"id": "cuda", "label": torch.cuda.get_device_name(0)})
        mps = getattr(torch.backends, "mps", None)
        if mps is not None and mps.is_available():
            devices.append({"id": "mps", "label": "Apple GPU (Metal)"})
    except Exception:
        pass
    return devices


def resolve_device(preference: str) -> str:
    available = {d["id"] for d in detect_devices()}
    if preference != "auto" and preference in available:
        return preference
    for candidate in ("cuda", "mps"):
        if candidate in available:
            return candidate
    return "cpu"


_ROOT = Path(__file__).resolve().parent.parent


def _read(name: str, default: str = "") -> str:
    try:
        return (_ROOT / name).read_text(encoding="utf-8").strip()
    except Exception:
        return default


def branding() -> dict:
    try:
        data = json.loads(_read("branding.json", "{}"))
    except Exception:
        data = {}
    return {k: str(data.get(k, "") or "") for k in ("company", "company_url", "repo", "site", "support_email")}


def system_info(settings: dict) -> dict:
    ram_gb = round(psutil.virtual_memory().total / 1024**3, 1)
    cores = os.cpu_count() or 1
    devices = detect_devices()
    best = resolve_device("auto")
    if best in ("cuda", "mps"):
        tier, advice = "gpu", "A GPU was found. Voice cloning will run at a comfortable speed."
        recommended = "chatterbox"
    elif ram_gb < 8 or cores < 4:
        tier = "light"
        advice = ("This machine is on the lighter side. Use Fast mode with the built-in voices; "
                  "voice cloning will work but each clip can take a few minutes.")
        recommended = "kokoro"
    else:
        tier = "cpu"
        advice = ("No GPU found, which is fine. Fast mode is quick on this CPU. "
                  "Voice cloning works too, but expect it to be several times slower than real time.")
        recommended = "kokoro"
    return {
        "os": f"{platform.system()} {platform.release()}",
        "arch": platform.machine(),
        "ram_gb": ram_gb,
        "cores": cores,
        "devices": devices,
        "best_device": best,
        "tier": tier,
        "advice": advice,
        "recommended_engine": recommended,
        "in_docker": os.path.exists("/.dockerenv"),
        "quit_allowed": os.environ.get("VOICESTUDIO_ALLOW_QUIT") == "1",
        "installed": os.environ.get("VOICESTUDIO_INSTALLED") == "1",
        "terms": {"version": legal.TERMS_VERSION, "accepted": legal.accepted()},
        "version": _read("VERSION", "dev"),
        "branding": branding(),
    }
