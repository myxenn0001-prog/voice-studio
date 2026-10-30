"""Voice library: built-in voices come from engines; custom voices live on disk.

Add voices three ways:
  1. Upload in the app (Voices tab).
  2. Drop an audio file into data/voices/ and it is imported on next refresh.
  3. Copy a finished voice folder (ref.wav + meta.json) into data/voices/.
"""
from __future__ import annotations

import io
import json
import re
import shutil
import time
import uuid
from pathlib import Path

import numpy as np
import soundfile as sf

from . import legal
from .config import VOICES_DIR
from .engines import ENGINES
from .engines.base import VoiceRef

ID_RE = re.compile(r"^[a-f0-9]{12}$")
AUDIO_EXT = {".wav", ".mp3", ".flac", ".ogg", ".m4a"}
MIN_SECONDS, IDEAL_SECONDS, MAX_SECONDS = 2.0, 5.0, 30.0
MAX_UPLOAD_BYTES = 60 * 1024 * 1024


class VoiceError(ValueError):
    pass


def _meta_path(voice_id: str) -> Path:
    return VOICES_DIR / voice_id / "meta.json"


def _ref_path(voice_id: str) -> Path:
    return VOICES_DIR / voice_id / "ref.wav"


def _prepare_audio(data: np.ndarray, sr: int) -> tuple[np.ndarray, float]:
    if data.ndim > 1:
        data = data.mean(axis=1)
    data = data.astype(np.float32)
    seconds = len(data) / sr
    if seconds < MIN_SECONDS:
        raise VoiceError(f"The sample is {seconds:.1f}s long. Use at least {MIN_SECONDS:.0f} seconds of clear speech.")
    if seconds > MAX_SECONDS:
        data = data[: int(MAX_SECONDS * sr)]
        seconds = MAX_SECONDS
    peak = float(np.max(np.abs(data))) or 1.0
    if peak < 0.05 or peak > 0.95:
        data = data / peak * 0.9
    return data, seconds


def _store(name: str, data: np.ndarray, sr: int, note: str, consent: dict | None = None) -> dict:
    data, seconds = _prepare_audio(data, sr)
    voice_id = uuid.uuid4().hex[:12]
    folder = VOICES_DIR / voice_id
    folder.mkdir(parents=True)
    sf.write(str(folder / "ref.wav"), data, sr, subtype="PCM_16")
    meta = {
        "id": voice_id,
        "name": name.strip()[:60] or "Untitled voice",
        "created": int(time.time()),
        "seconds": round(seconds, 1),
        "note": note,
        "short_sample": seconds < IDEAL_SECONDS,
        "consent": consent or {"confirmed": False, "note": "added without the in-app confirmation (imported from the voices folder)"},
    }
    _meta_path(voice_id).write_text(json.dumps(meta, indent=2))
    return meta


def add_voice(name: str, raw: bytes, consent: bool) -> dict:
    if not consent:
        raise VoiceError("Confirm that you have the right to use this voice before adding it.")
    if len(raw) > MAX_UPLOAD_BYTES:
        raise VoiceError("That file is larger than 60 MB. Trim it to under 30 seconds.")
    try:
        data, sr = sf.read(io.BytesIO(raw), dtype="float32", always_2d=False)
    except Exception:
        raise VoiceError("Could not read that audio file. Use WAV, MP3, FLAC or OGG.")
    consent = {"confirmed": True, "statement": legal.CONSENT_STATEMENT, "terms_version": legal.TERMS_VERSION,
               "at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
    return _store(name, data, sr, "uploaded; consent confirmed", consent)


def import_dropped_files() -> None:
    """Import loose audio files dropped straight into data/voices/."""
    for f in VOICES_DIR.iterdir():
        if f.is_file() and f.suffix.lower() in AUDIO_EXT:
            try:
                data, sr = sf.read(str(f), dtype="float32")
                _store(f.stem.replace("_", " "), data, sr, "imported from voices folder")
                f.unlink()
            except Exception:
                f.rename(f.with_suffix(f.suffix + ".unreadable"))


def list_custom() -> list[dict]:
    import_dropped_files()
    out = []
    for folder in sorted(VOICES_DIR.iterdir()):
        mp = folder / "meta.json"
        if folder.is_dir() and mp.exists() and (folder / "ref.wav").exists():
            try:
                out.append(json.loads(mp.read_text()))
            except Exception:
                continue
    return sorted(out, key=lambda m: m.get("created", 0), reverse=True)


def rename_voice(voice_id: str, name: str) -> dict:
    if not ID_RE.match(voice_id) or not _meta_path(voice_id).exists():
        raise VoiceError("Voice not found.")
    meta = json.loads(_meta_path(voice_id).read_text())
    meta["name"] = name.strip()[:60] or meta["name"]
    _meta_path(voice_id).write_text(json.dumps(meta, indent=2))
    return meta


def delete_voice(voice_id: str) -> None:
    if not ID_RE.match(voice_id) or not (VOICES_DIR / voice_id).is_dir():
        raise VoiceError("Voice not found.")
    shutil.rmtree(VOICES_DIR / voice_id)


def ref_audio_path(voice_id: str) -> Path | None:
    if ID_RE.match(voice_id) and _ref_path(voice_id).exists():
        return _ref_path(voice_id)
    return None


def catalog() -> dict:
    """Everything the UI needs to populate voice pickers."""
    stock = []
    for eng in ENGINES.values():
        for v in eng.stock_voices():
            stock.append({"id": v.id, "name": v.name, "engine": eng.id, "kind": "stock", "lang": v.lang})
    custom = [dict(m, kind="custom") for m in list_custom()]
    return {"stock": stock, "custom": custom}


def resolve(engine_id: str, voice_id: str) -> VoiceRef:
    engine = ENGINES.get(engine_id)
    if engine is None:
        raise VoiceError("Unknown engine.")
    if ID_RE.match(voice_id or ""):
        path = ref_audio_path(voice_id)
        if path is None:
            raise VoiceError("That voice no longer exists.")
        if not engine.supports_cloning:
            raise VoiceError(f"{engine.name} mode uses the built-in voices. Switch to Clone mode to use your own voices.")
        meta = json.loads(_meta_path(voice_id).read_text())
        return VoiceRef(id=voice_id, name=meta["name"], kind="custom", path=str(path))
    for v in engine.stock_voices():
        if v.id == voice_id:
            return v
    raise VoiceError("That voice is not available in the selected mode.")
