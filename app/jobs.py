"""Render queue. One worker thread runs jobs in order so a small machine is
never asked to do two renders at once. Every job gets its own folder, so
nothing is ever overwritten."""
from __future__ import annotations

import hashlib
import itertools
import json
import queue
import re
import shutil
import threading
import time
import traceback
import uuid
from pathlib import Path

import numpy as np
import soundfile as sf

from . import captions, marking, voices
from .config import OUTPUTS_DIR, PREVIEWS_DIR, load_settings
from .engines import ENGINES
from .languages import preview_text
from .system import resolve_device
from .textutil import make_chunks

JOB_ID_RE = re.compile(r"^[a-f0-9]{12}$")
MAX_CHARS = 200_000

ACTIVE = ("queued", "loading_model", "running", "captioning")
CAPTION_EXT = {".wav", ".mp3", ".m4a", ".flac", ".ogg", ".opus", ".aac", ".wma",
               ".mp4", ".mov", ".mkv", ".webm", ".avi", ".m4v"}
MAX_CAPTION_UPLOAD = 500 * 1024 * 1024

_jobs: dict[str, dict] = {}
_jobs_lock = threading.Lock()
_queue: "queue.PriorityQueue" = queue.PriorityQueue()  # previews (0) run before renders (1)
_seq = itertools.count()
_current = {"id": None}
_cancel: set[str] = set()


# -- persistence --------------------------------------------------------
def _job_dir(job_id):
    return OUTPUTS_DIR / job_id


def _save(job):
    _job_dir(job["id"]).mkdir(exist_ok=True)
    (_job_dir(job["id"]) / "job.json").write_text(json.dumps(job, indent=2))


def _update(job, **fields):
    with _jobs_lock:
        job.update(fields)
    _save(job)


def load_history():
    for folder in OUTPUTS_DIR.iterdir():
        jp = folder / "job.json"
        if not jp.exists():
            continue
        try:
            job = json.loads(jp.read_text())
        except Exception:
            continue
        if job.get("preview"):
            shutil.rmtree(folder, ignore_errors=True)
            continue
        if job["status"] in ACTIVE:
            job["status"], job["error"] = "error", "The app was closed before this render finished."
            jp.write_text(json.dumps(job, indent=2))
        _jobs[job["id"]] = job


# -- engine management --------------------------------------------------
def _ensure_loaded(engine_id):
    engine = ENGINES[engine_id]
    settings = load_settings()
    device = engine.pick_device(resolve_device(settings["device"]))
    if engine.loaded and engine._device == device:
        return engine
    ok, reason = engine.available()
    if not ok:
        raise RuntimeError(reason)
    if engine.loaded:
        engine.unload()
    try:
        import torch

        threads = settings["cpu_threads"] or 0
        if threads:
            torch.set_num_threads(threads)
    except Exception:
        pass
    engine.load(device)
    return engine


def unload_all():
    captions.unload()
    for e in ENGINES.values():
        if e.loaded:
            e.unload()


# -- public API ---------------------------------------------------------
def _wait_message():
    cur = _jobs.get(_current["id"]) if _current["id"] else None
    if cur and cur["status"] == "loading_model":
        return "Waiting for the voice model to finish loading. The first time, it downloads (a few minutes)."
    return "Waiting for the previous render to finish…" if cur else "Starting…"


def create_job(payload: dict) -> dict:
    text = (payload.get("text") or "").strip()
    preview = bool(payload.get("preview"))
    options = payload.get("options") or {}
    if not preview and not text:
        raise voices.VoiceError("Write or paste a script first.")
    if len(text) > MAX_CHARS:
        raise voices.VoiceError(f"Scripts are limited to {MAX_CHARS:,} characters. Split it into parts.")
    engine_id = payload.get("engine") or ""
    if engine_id not in ENGINES:
        raise voices.VoiceError("Choose a mode first.")
    voice = voices.resolve(engine_id, payload.get("voice") or "")  # validate now, fail fast
    lang = voice.lang or options.get("language_id") or "en"
    if preview:
        text = preview_text(lang)

    fmt = "wav" if preview else (payload.get("format") or load_settings()["output_format"])
    if fmt not in ("wav", "flac", "mp3"):
        fmt = "wav"
    cache_key = None
    if preview:
        raw = json.dumps([engine_id, voice.id, lang, options], sort_keys=True)
        cache_key = hashlib.sha1(raw.encode()).hexdigest()[:20]
    chunks = make_chunks(text)
    job = {
        "id": uuid.uuid4().hex[:12],
        "created": int(time.time()),
        "status": "queued",
        "message": _wait_message(),
        "engine": engine_id,
        "voice": payload["voice"],
        "voice_name": voice.name,
        "options": options,
        "task": "render",
        "captions": captions.normalize(payload.get("captions")) if payload.get("captions") and not preview else None,
        "lang": lang,
        "cache_key": cache_key,
        "format": fmt,
        "pause_ms": int(max(0, min(payload.get("pause_ms", 250), 3000))),
        "paragraph_pause_ms": int(max(0, min(payload.get("paragraph_pause_ms", 700), 5000))),
        "preview": preview,
        "text": text,
        "chunks_total": len(chunks),
        "chunks_done": 0,
        "eta_seconds": None,
        "duration": None,
        "error": None,
        "file": None,
        "srt": None,
    }
    cached = PREVIEWS_DIR / f"{cache_key}.wav" if cache_key else None
    if cached and cached.exists():  # instant preview, no model needed
        _job_dir(job["id"]).mkdir(exist_ok=True)
        shutil.copy(cached, _job_dir(job["id"]) / "voiceover.wav")
        job.update(status="done", message="Done.", file="voiceover.wav", chunks_done=len(chunks), duration=None)
        with _jobs_lock:
            _jobs[job["id"]] = job
        _save(job)
        return job
    with _jobs_lock:
        _jobs[job["id"]] = job
    _save(job)
    _queue.put((0 if preview else 1, next(_seq), job["id"]))
    return job


def get_job(job_id):
    return _jobs.get(job_id) if JOB_ID_RE.match(job_id or "") else None


def list_jobs():
    jobs = [j for j in _jobs.values() if not j.get("preview")]
    return sorted(jobs, key=lambda j: j["created"], reverse=True)


def cancel_job(job_id):
    job = get_job(job_id)
    if job and job["status"] in ACTIVE:
        _cancel.add(job_id)
        if job["status"] == "queued":
            _update(job, status="cancelled", message="Cancelled.")
    return job


def delete_job(job_id):
    job = get_job(job_id)
    if not job:
        return False
    if job["status"] in ACTIVE:
        cancel_job(job_id)
    with _jobs_lock:
        _jobs.pop(job_id, None)
    shutil.rmtree(_job_dir(job_id), ignore_errors=True)
    return True


# -- worker -------------------------------------------------------------
_fmt_srt_time = captions.srt_time


_write_audio = marking.write_audio


def _caption_device():
    device = resolve_device(load_settings()["device"])
    return "cuda" if device == "cuda" else "cpu"  # Whisper has no Apple-GPU path; CPU is fast enough


def _caption_into(job, source_path):
    """Make short captions for an audio/video file. Returns the job fields to store."""
    ok, reason = captions.available()
    if not ok:
        return {"cap_error": reason}
    opts = captions.normalize(job.get("captions"))
    last = {"pct": -1}

    def status(msg):
        _update(job, message=msg)

    def progress(frac):
        pct = int(frac * 100)
        if pct >= last["pct"] + 5:
            last["pct"] = pct
            _update(job, message=f"Making captions… {pct}%")

    try:
        cues, lang = captions.make_captions(source_path, {**opts, "language": opts["language"] or job.get("lang")},
                                            _caption_device(), status, progress)
    except Exception as exc:
        traceback.print_exc()
        return {"cap_error": str(exc)}
    captions.write_files(_job_dir(job["id"]), cues)
    return {"cap_srt": "captions.srt", "cap_txt": "timestamps.txt", "cap_cues": len(cues),
            "cap_language": lang, "cap_error": None}


def _run_captions(job):
    """Caption-only work: an uploaded file, or a finished render being captioned again."""
    source = _job_dir(job["id"]) / (job.get("source") or job.get("file") or "")
    if not source.is_file():
        raise RuntimeError("The audio file for this job is missing.")
    _update(job, status="captioning", message="Getting the caption model ready…", cap_error=None)
    fields = _caption_into(job, source)
    if fields.get("cap_error") and not job.get("file"):
        raise RuntimeError(fields["cap_error"])  # caption-only job: nothing else to show
    _update(job, status="done", message="Done.", chunks_done=job.get("chunks_total", 1),
            task="render" if job.get("file") else "captions", **fields)


def create_caption_job(filename: str, stream, opts: dict) -> dict:
    ok, reason = captions.available()
    if not ok:
        raise voices.VoiceError(reason)
    ext = Path(filename or "").suffix.lower()
    if ext not in CAPTION_EXT:
        raise voices.VoiceError("Use an audio or video file: WAV, MP3, M4A, FLAC, OGG, MP4, MOV, MKV or WEBM.")
    job_id = uuid.uuid4().hex[:12]
    folder = _job_dir(job_id)
    folder.mkdir()
    size = 0
    with open(folder / f"source{ext}", "wb") as out:
        while chunk := stream.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_CAPTION_UPLOAD:
                out.close()
                shutil.rmtree(folder, ignore_errors=True)
                raise voices.VoiceError("That file is larger than 500 MB.")
            out.write(chunk)
    safe_name = Path(filename).name[:120]
    job = {
        "id": job_id, "created": int(time.time()), "status": "queued", "message": _wait_message(),
        "task": "captions", "engine": "whisper", "voice": "", "voice_name": safe_name,
        "options": {}, "captions": captions.normalize(opts), "lang": None, "format": "",
        "preview": False, "text": f"Captions for {safe_name}", "chunks_total": 1, "chunks_done": 0,
        "eta_seconds": None, "duration": None, "error": None, "file": None, "srt": None,
        "source": f"source{ext}",
    }
    with _jobs_lock:
        _jobs[job_id] = job
    _save(job)
    _queue.put((1, next(_seq), job_id))
    return job


def recaption_job(job_id: str, opts: dict):
    job = get_job(job_id)
    if not job or job["status"] != "done" or not job.get("file"):
        raise voices.VoiceError("Only a finished render can be captioned.")
    ok, reason = captions.available()
    if not ok:
        raise voices.VoiceError(reason)
    _update(job, task="captions", captions=captions.normalize(opts), status="queued",
            message=_wait_message(), cap_error=None)
    _queue.put((1, next(_seq), job_id))
    return job


def _run(job):
    if job["id"] in _cancel:
        return
    if job.get("task") == "captions":
        return _run_captions(job)
    engine = _ensure_loaded(job["engine"])
    voice = voices.resolve(job["engine"], job["voice"])
    if not engine.ready_for(job["options"], voice):
        _update(job, status="loading_model",
                message="Loading the voice model. The first time, it downloads (a few minutes). Progress shows in the terminal window.")
        engine.prepare(job["options"], voice)
        if job["id"] in _cancel:
            _update(job, status="cancelled", message="Cancelled.")
            return
    chunks = make_chunks(job["text"])
    sr = engine.sample_rate
    pieces, srt, cursor = [], [], 0.0
    started = time.time()
    _update(job, status="running", message="Rendering…")

    for i, chunk in enumerate(chunks):
        if job["id"] in _cancel:
            _update(job, status="cancelled", message="Cancelled.")
            return
        t0 = time.time()
        audio = engine.synth(chunk["text"], voice, job["options"])
        dur = len(audio) / sr
        print(f"[voice-studio] part {i + 1}/{len(chunks)} done in {time.time() - t0:.1f}s", flush=True)
        srt.append((cursor, cursor + dur, chunk["text"]))
        pause = job["paragraph_pause_ms"] if chunk["paragraph_end"] else job["pause_ms"]
        gap = np.zeros(int(sr * pause / 1000), dtype=np.float32)
        pieces += [audio, gap]
        cursor += dur + pause / 1000

        done = i + 1
        per_chunk = (time.time() - started) / done
        _update(job, chunks_done=done,
                eta_seconds=int(per_chunk * (len(chunks) - done)),
                message=f"Rendering part {done} of {len(chunks)}…")

    full = np.concatenate(pieces)[: -len(gap)] if len(gap) else np.concatenate(pieces)
    method = "engine" if engine.adds_watermark else None
    if not engine.adds_watermark:
        full, method = marking.watermark(full, sr)
    base = _job_dir(job["id"]) / "voiceover"
    name = _write_audio(base, full, sr, job["format"])
    srt_lines = []
    for n, (a, b, t) in enumerate(srt, 1):
        srt_lines.append(f"{n}\n{_fmt_srt_time(a)} --> {_fmt_srt_time(b)}\n{t}\n")
    (_job_dir(job["id"]) / "voiceover.srt").write_text("\n".join(srt_lines), encoding="utf-8")
    if job.get("cache_key") and name.endswith(".wav"):
        shutil.copy(_job_dir(job["id"]) / name, PREVIEWS_DIR / f"{job['cache_key']}.wav")
    render_seconds = round(time.time() - started, 1)
    extra = {}
    if job.get("captions"):
        _update(job, status="captioning", message="Audio is ready. Making captions…", file=name, srt="voiceover.srt",
                duration=round(len(full) / sr, 1), render_seconds=render_seconds)
        extra = _caption_into(job, _job_dir(job["id"]) / name)
    _update(job, status="done", message="Done.", file=name, srt="voiceover.srt", marking=method or "metadata",
            duration=round(len(full) / sr, 1), eta_seconds=0, render_seconds=render_seconds, **extra)


def _worker():
    while True:
        _, _, job_id = _queue.get()
        job = _jobs.get(job_id)
        if job is None or job["status"] == "cancelled":
            continue
        _current["id"] = job_id
        try:
            _run(job)
        except Exception as exc:  # report to the UI, keep the worker alive
            traceback.print_exc()
            _update(job, status="error", message="Render failed.", error=str(exc))
        finally:
            _cancel.discard(job_id)
            _current["id"] = None


def start_worker():
    load_history()
    threading.Thread(target=_worker, daemon=True, name="render-worker").start()
