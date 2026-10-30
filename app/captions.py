"""Short, timed captions from any audio or video file, using Whisper (via faster-whisper, MIT).

Same idea as:
    whisper file.wav --word_timestamps True --max_line_width 18 --max_line_count 1 --output_format srt
but built in: it needs no ffmpeg install, runs well on a CPU, and also writes a timestamp text file.
"""
from __future__ import annotations

import importlib.util
import re
import threading
from datetime import timedelta
from pathlib import Path

from .languages import LANGUAGES

MODELS = [
    {"id": "tiny", "name": "Tiny (fastest)"},
    {"id": "base", "name": "Base (recommended)"},
    {"id": "small", "name": "Small (more accurate, slower)"},
]
_MODEL_IDS = {m["id"] for m in MODELS}
NO_SPACE = {"zh", "ja", "th", "lo", "my", "km"}  # scripts written without spaces between words
_SENT_END = re.compile(r"[.!?…।॥؟۔。！？]['\"”’)\]]*$")

_state = {"name": None, "device": None, "obj": None}
_lock = threading.Lock()


# -- availability ---------------------------------------------------------
def available() -> tuple[bool, str]:
    if importlib.util.find_spec("faster_whisper") is None:
        return False, ("Captions need the 'faster-whisper' package. Mac/Linux: run ./run.sh --update. "
                       "Windows: delete .venv\\.installed and run run.bat again.")
    return True, ""


def info() -> dict:
    ok, reason = available()
    return {
        "available": ok, "reason": reason, "models": MODELS,
        "languages": [{"code": c, "name": v[0]} for c, v in sorted(LANGUAGES.items(), key=lambda kv: kv[1][0])],
        "defaults": {"model": "base", "max_width": 18, "max_lines": 1},
    }


def normalize(opts: dict | None) -> dict:
    opts = opts or {}
    model = opts.get("model") if opts.get("model") in _MODEL_IDS else "base"
    try:
        width = max(8, min(int(opts.get("max_width", 18)), 60))
        lines = max(1, min(int(opts.get("max_lines", 1)), 2))
    except (TypeError, ValueError):
        width, lines = 18, 1
    lang = opts.get("language") if opts.get("language") in LANGUAGES else None
    return {"model": model, "max_width": width, "max_lines": lines, "language": lang}


def unload() -> None:
    with _lock:
        _state.update(name=None, device=None, obj=None)


# -- Whisper ---------------------------------------------------------------
def _get_model(name: str, device: str, status=None):
    with _lock:
        if _state["obj"] is not None and _state["name"] == name and _state["device"] == device:
            return _state["obj"]
        from faster_whisper import WhisperModel

        if status:
            status("Loading the caption model. The first time, it downloads once.")
        print(f"[voice-studio] Loading caption model '{name}' on {device} (first time downloads it)...", flush=True)
        _state.update(name=None, device=None, obj=None)
        compute = "float16" if device == "cuda" else "int8"
        obj = WhisperModel(name, device=device, compute_type=compute)
        _state.update(name=name, device=device, obj=obj)
        return obj


def transcribe_words(path, model_name: str, language: str | None, device: str, status=None, progress=None):
    """Returns ([{'start','end','text'}...], detected_language_code)."""
    attempts = [device] + (["cpu"] if device == "cuda" else [])
    last = None
    for dev in attempts:
        try:
            model = _get_model(model_name, dev, status)
            try:
                segments, meta = model.transcribe(str(path), word_timestamps=True, language=language, beam_size=5)
            except ValueError:  # language code the model does not know: let it detect instead
                segments, meta = model.transcribe(str(path), word_timestamps=True, language=None, beam_size=5)
            total = max(float(getattr(meta, "duration", 0) or 0), 0.001)
            words = []
            for seg in segments:
                for w in (seg.words or []):
                    text = (w.word or "").strip()
                    if text:
                        words.append({"start": float(w.start), "end": float(w.end), "text": text})
                if progress:
                    progress(min(float(seg.end) / total, 1.0))
            return words, getattr(meta, "language", language) or language or "en"
        except Exception as exc:
            last = exc
            if dev == "cuda":
                print(f"[voice-studio] Caption model failed on the GPU ({exc}); retrying on the CPU.", flush=True)
                with _lock:
                    _state.update(name=None, device=None, obj=None)
                continue
            raise
    raise last  # pragma: no cover


# -- grouping words into short captions ------------------------------------
def build_cues(words: list[dict], max_width: int = 18, max_lines: int = 1, no_space: bool = False) -> list[dict]:
    """Group timed words into caption cues. A line holds at most `max_width` characters,
    a cue at most `max_lines` lines, and a cue always ends at the end of a sentence."""
    sep = "" if no_space else " "

    def line_text(ws):
        return sep.join(w["text"] for w in ws)

    cues, lines, cur = [], [], []

    def close_line():
        nonlocal cur
        if cur:
            lines.append(cur)
            cur = []

    def close_cue():
        nonlocal lines
        close_line()
        if lines:
            flat = [w for line in lines for w in line]
            cues.append({"start": flat[0]["start"], "end": flat[-1]["end"],
                         "text": "\n".join(line_text(line) for line in lines)})
            lines = []

    for w in words:
        if cur and len(line_text(cur + [w])) > max_width:
            close_line()
            if len(lines) >= max_lines:
                close_cue()
        cur.append(w)
        if _SENT_END.search(w["text"]):
            close_cue()
    close_cue()

    # tidy timing: a minimum on-screen time, and no overlap with the next caption
    for i, cue in enumerate(cues):
        if cue["end"] < cue["start"] + 0.3:
            cue["end"] = cue["start"] + 0.3
        if i + 1 < len(cues) and cue["end"] > cues[i + 1]["start"]:
            cue["end"] = max(cue["start"] + 0.05, cues[i + 1]["start"])
    return cues


def srt_time(t: float) -> str:
    ms = int(round(max(t, 0) * 1000))
    h, ms = divmod(ms, 3_600_000)
    m, ms = divmod(ms, 60_000)
    s, ms = divmod(ms, 1000)
    return f"{h:02}:{m:02}:{s:02},{ms:03}"


def to_srt(cues: list[dict]) -> str:
    return "\n".join(f"{i}\n{srt_time(c['start'])} --> {srt_time(c['end'])}\n{c['text']}\n"
                     for i, c in enumerate(cues, 1))


def to_txt(cues: list[dict]) -> str:
    return "".join(f"[{timedelta(seconds=int(c['start']))}] {c['text'].replace(chr(10), ' ')}\n" for c in cues)


def make_captions(path, opts: dict, device: str, status=None, progress=None):
    """Returns (cues, language_code). Raises RuntimeError if nothing was spoken."""
    o = normalize(opts)
    words, lang = transcribe_words(path, o["model"], o["language"], device, status, progress)
    if not words:
        raise RuntimeError("No speech was found in that audio.")
    return build_cues(words, o["max_width"], o["max_lines"], no_space=lang in NO_SPACE), lang


def write_files(folder: Path, cues: list[dict]) -> None:
    (folder / "captions.srt").write_text(to_srt(cues), encoding="utf-8")
    (folder / "timestamps.txt").write_text(to_txt(cues), encoding="utf-8")
