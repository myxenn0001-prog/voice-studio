from __future__ import annotations

import os
import threading
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, HTMLResponse
from pydantic import BaseModel

from . import captions, importer, jobs, legal, models, shortcut, voices
from .config import APP_DIR, OUTPUTS_DIR, load_settings, record_terms, save_settings
from .engines import ENGINES
from .system import system_info

app = FastAPI(title="Voice Studio", docs_url=None, redoc_url=None)
STATIC = APP_DIR / "static"
ASSETS = APP_DIR.parent / "assets"


@app.on_event("startup")
def _startup():
    jobs.start_worker()


# -- pages ----------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def index():
    return (STATIC / "index.html").read_text(encoding="utf-8")


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    f = ASSETS / "voice-studio.ico"
    if not f.exists():
        raise HTTPException(404)
    return FileResponse(f, media_type="image/x-icon")


@app.get("/icon.png", include_in_schema=False)
def icon():
    f = ASSETS / "voice-studio.png"
    if not f.exists():
        raise HTTPException(404)
    return FileResponse(f, media_type="image/png")


# -- legal pages and acceptance of the Terms ------------------------------------
LEGAL_PAGES = {"terms", "privacy", "responsible-use", "licenses", "trademarks", "conduct", "license"}


@app.get("/legal/{name}", response_class=HTMLResponse, include_in_schema=False)
def legal_page(name: str):
    page = STATIC / "legal" / f"{name}.html"
    if name not in LEGAL_PAGES or not page.exists():
        raise HTTPException(404, "Page not found.")
    return page.read_text(encoding="utf-8")


class TermsAccept(BaseModel):
    version: str


@app.post("/api/terms/accept")
def api_accept_terms(body: TermsAccept):
    if body.version != legal.TERMS_VERSION:
        raise HTTPException(400, "These are not the current Terms. Reload the page and try again.")
    record_terms(legal.TERMS_VERSION)
    return {"accepted": True, "version": legal.TERMS_VERSION}


def need_terms():
    if not legal.accepted():
        raise HTTPException(403, "Please accept the Terms of Use first. They appear when you open Voice Studio.")


# -- script import, shortcut, quit ---------------------------------------------
@app.post("/api/import")
async def api_import(file: UploadFile = File(...)):
    raw = await file.read(importer.MAX_BYTES + 1)
    try:
        text = importer.extract_text(file.filename or "", raw)
    except importer.ImportFileError as exc:
        raise HTTPException(400, str(exc))
    return {"name": file.filename, "text": text}


@app.post("/api/shortcut")
def api_shortcut():
    if os.environ.get("VOICESTUDIO_INSTALLED") == "1":
        raise HTTPException(400, "The installer already added Voice Studio to your desktop and app menu.")
    if os.path.exists("/.dockerenv"):
        raise HTTPException(400, "Shortcuts cannot be created from inside Docker. "
                                 "Right-click docker-start.bat or docker-start.sh and create a shortcut to it instead.")
    try:
        return shortcut.create()
    except Exception as exc:
        raise HTTPException(500, f"Could not create the shortcut: {exc}")


@app.post("/api/quit")
def api_quit():
    if os.environ.get("VOICESTUDIO_ALLOW_QUIT") != "1":
        raise HTTPException(403, "Quit is only available when Voice Studio was started from its shortcut.")
    threading.Timer(0.5, lambda: os._exit(0)).start()
    return {"ok": True}


# -- system, engines, settings ---------------------------------------------
@app.get("/api/system")
def api_system():
    return system_info(load_settings())


@app.get("/api/engines")
def api_engines():
    return [e.info() for e in ENGINES.values()]


class SettingsPatch(BaseModel):
    device: str | None = None
    default_engine: str | None = None
    cpu_threads: int | None = None
    output_format: str | None = None


@app.get("/api/settings")
def api_settings():
    return load_settings()


@app.put("/api/settings")
def api_save_settings(patch: SettingsPatch):
    before = load_settings()
    try:
        after = save_settings(patch.model_dump(exclude_none=True))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    if before["device"] != after["device"] or before["cpu_threads"] != after["cpu_threads"]:
        jobs.unload_all()  # reload on the new device at next render
    return after


# -- voices ------------------------------------------------------------------
@app.get("/api/voices")
def api_voices():
    return voices.catalog()


@app.post("/api/voices")
async def api_add_voice(name: str = Form(...), consent: bool = Form(False), file: UploadFile = File(...)):
    need_terms()
    try:
        return voices.add_voice(name, await file.read(), consent)
    except voices.VoiceError as exc:
        raise HTTPException(400, str(exc))


class Rename(BaseModel):
    name: str


@app.patch("/api/voices/{voice_id}")
def api_rename_voice(voice_id: str, body: Rename):
    try:
        return voices.rename_voice(voice_id, body.name)
    except voices.VoiceError as exc:
        raise HTTPException(404, str(exc))


@app.delete("/api/voices/{voice_id}")
def api_delete_voice(voice_id: str):
    try:
        voices.delete_voice(voice_id)
    except voices.VoiceError as exc:
        raise HTTPException(404, str(exc))
    return {"ok": True}


@app.get("/api/voices/{voice_id}/audio")
def api_voice_audio(voice_id: str):
    path = voices.ref_audio_path(voice_id)
    if path is None:
        raise HTTPException(404, "Voice not found.")
    return FileResponse(path, media_type="audio/wav")


# -- jobs ---------------------------------------------------------------------
class JobRequest(BaseModel):
    text: str = ""
    engine: str
    voice: str
    options: dict = {}
    format: str | None = None
    pause_ms: int = 250
    paragraph_pause_ms: int = 700
    preview: bool = False
    captions: dict | None = None


class CaptionOptions(BaseModel):
    model: str = "base"
    max_width: int = 18
    max_lines: int = 1
    language: str | None = None


class ModelDownload(BaseModel):
    packs: list[str]


@app.get("/api/models")
def api_models():
    return models.status()


@app.post("/api/models/download")
def api_models_download(req: ModelDownload):
    try:
        return models.start(req.packs)
    except ValueError as exc:
        raise HTTPException(400, str(exc))


@app.get("/api/captions/info")
def api_captions_info():
    return captions.info()


@app.post("/api/captions")
async def api_caption_file(file: UploadFile = File(...), model: str = Form("base"), max_width: int = Form(18),
                           max_lines: int = Form(1), language: str = Form("")):
    need_terms()
    try:
        job = jobs.create_caption_job(file.filename or "", file.file,
                                      {"model": model, "max_width": max_width, "max_lines": max_lines,
                                       "language": language or None})
    except voices.VoiceError as exc:
        raise HTTPException(400, str(exc))
    return {k: v for k, v in job.items() if k != "text"}


@app.post("/api/jobs/{job_id}/captions")
def api_recaption(job_id: str, opts: CaptionOptions):
    need_terms()
    try:
        job = jobs.recaption_job(job_id, opts.model_dump())
    except voices.VoiceError as exc:
        raise HTTPException(400, str(exc))
    return {k: v for k, v in job.items() if k != "text"}


@app.get("/api/jobs/{job_id}/caption-file/{kind}")
def api_caption_file_download(job_id: str, kind: str):
    attr = {"srt": "cap_srt", "txt": "cap_txt"}.get(kind)
    if not attr:
        raise HTTPException(404, "Unknown file.")
    path = _job_file(job_id, attr)
    return FileResponse(path, media_type="text/plain",
                        filename="captions.srt" if kind == "srt" else "timestamps.txt")


@app.post("/api/jobs")
def api_create_job(req: JobRequest):
    need_terms()
    try:
        return jobs.create_job(req.model_dump())
    except voices.VoiceError as exc:
        raise HTTPException(400, str(exc))


@app.get("/api/jobs")
def api_list_jobs():
    return [{k: v for k, v in j.items() if k != "text"} | {"excerpt": j["text"][:140]}
            for j in jobs.list_jobs()]


@app.get("/api/jobs/{job_id}")
def api_get_job(job_id: str):
    job = jobs.get_job(job_id)
    if not job:
        raise HTTPException(404, "Render not found.")
    return {k: v for k, v in job.items() if k != "text"}


@app.post("/api/jobs/{job_id}/cancel")
def api_cancel_job(job_id: str):
    if not jobs.cancel_job(job_id):
        raise HTTPException(404, "Render not found.")
    return {"ok": True}


@app.delete("/api/jobs/{job_id}")
def api_delete_job(job_id: str):
    if not jobs.delete_job(job_id):
        raise HTTPException(404, "Render not found.")
    return {"ok": True}


def _job_file(job_id: str, attr: str) -> Path:
    job = jobs.get_job(job_id)
    if not job or not job.get(attr):
        raise HTTPException(404, "File not ready.")
    return OUTPUTS_DIR / job_id / job[attr]


@app.get("/api/jobs/{job_id}/audio")
def api_job_audio(job_id: str, download: bool = False):
    path = _job_file(job_id, "file")
    media = {"wav": "audio/wav", "flac": "audio/flac", "mp3": "audio/mpeg"}[path.suffix[1:]]
    return FileResponse(path, media_type=media,
                        filename=f"voiceover-{job_id}{path.suffix}" if download else None)


@app.get("/api/jobs/{job_id}/srt")
def api_job_srt(job_id: str):
    return FileResponse(_job_file(job_id, "srt"), media_type="text/plain",
                        filename=f"voiceover-{job_id}.srt")
