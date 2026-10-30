import io
import json
import os
import re
from pathlib import Path

os.environ["VOICESTUDIO_MOCK"] = "1"
os.environ.setdefault("VOICESTUDIO_DATA", "/tmp/vs_test_data")

import numpy as np
import pytest
import soundfile as sf
from fastapi.testclient import TestClient

from app import config, legal
from app.main import app

ROOT = Path(__file__).resolve().parent.parent


def wav(seconds=4, sr=16000):
    buf = io.BytesIO()
    sf.write(buf, (0.3 * np.sin(np.arange(int(seconds * sr)) / 20)).astype("float32"), sr, format="WAV")
    return buf.getvalue()


@pytest.fixture
def fresh(monkeypatch, tmp_path):
    """A first-time user: the Terms have not been accepted yet."""
    monkeypatch.delenv("VOICESTUDIO_TERMS_ACCEPTED", raising=False)
    monkeypatch.setattr(config, "SETTINGS_FILE", tmp_path / "settings.json")
    with TestClient(app) as c:
        yield c


def test_terms_must_be_accepted_first(fresh):
    c = fresh
    s = c.get("/api/system").json()
    assert s["terms"] == {"version": legal.TERMS_VERSION, "accepted": False}
    job = {"text": "Hello.", "engine": "mock", "voice": "tone"}
    assert c.post("/api/jobs", json=job).status_code == 403
    assert c.post("/api/voices", data={"name": "A", "consent": "true"}, files={"file": ("a.wav", wav())}).status_code == 403
    assert c.post("/api/captions", data={}, files={"file": ("a.wav", wav())}).status_code == 403
    assert c.post("/api/terms/accept", json={"version": "0.0"}).status_code == 400

    assert c.post("/api/terms/accept", json={"version": legal.TERMS_VERSION}).json()["accepted"] is True
    assert c.get("/api/system").json()["terms"]["accepted"] is True
    saved = json.loads(config.SETTINGS_FILE.read_text())
    assert saved["terms_accepted"] == legal.TERMS_VERSION and saved["terms_accepted_at"] > 0
    made = c.post("/api/jobs", json=job)
    assert made.status_code == 200
    c.delete(f"/api/jobs/{made.json()['id']}")      # leave nothing behind for other tests


def test_voice_consent_is_recorded(fresh):
    c = fresh
    c.post("/api/terms/accept", json={"version": legal.TERMS_VERSION})
    meta = c.post("/api/voices", data={"name": "Narrator", "consent": "true"}, files={"file": ("a.wav", wav())}).json()
    consent = meta["consent"]
    assert consent["confirmed"] is True and consent["terms_version"] == legal.TERMS_VERSION
    assert "permission" in consent["statement"] and re.fullmatch(r"\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ", consent["at"])
    assert c.post("/api/voices", data={"name": "B", "consent": "false"}, files={"file": ("a.wav", wav())}).status_code == 400
    c.delete(f"/api/voices/{meta['id']}")


def test_legal_pages_are_served_and_current(fresh):
    c = fresh
    for slug in ("terms", "privacy", "responsible-use", "licenses", "trademarks", "conduct", "license"):
        r = c.get(f"/legal/{slug}")
        assert r.status_code == 200 and "Voice Studio" in r.text, slug
    assert "No warranty" in c.get("/legal/terms").text and "Apache License" in c.get("/legal/license").text
    assert c.get("/legal/secret").status_code == 404 and c.get("/legal/..%2Fmain").status_code in (404, 422)


def test_documents_match_the_code():
    terms = (ROOT / "TERMS_OF_USE.md").read_text()
    assert f"**Version {legal.TERMS_VERSION} " in terms                   # code and document versions agree
    assert legal.CONSENT_STATEMENT.split(".")[0] in (ROOT / "app/static/index.html").read_text()
    for needed in ("No warranty", "Limit of liability", "Governing law", "Export and sanctions", "AI-generated markings"):
        assert needed in terms or needed.lower() in terms.lower(), needed
    import subprocess
    import sys

    r = subprocess.run([sys.executable, "tools/build_legal.py", "--check"], cwd=ROOT, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout           # the web pages are rebuilt after every edit to the documents
