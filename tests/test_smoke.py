import io
import os
import time

os.environ["VOICESTUDIO_MOCK"] = "1"
os.environ["VOICESTUDIO_TERMS_ACCEPTED"] = "1"
os.environ["VOICESTUDIO_DATA"] = "/tmp/vs_test_data"

import numpy as np
import soundfile as sf
from fastapi.testclient import TestClient

from app.main import app
from app.textutil import make_chunks


def wav_bytes(seconds=4, sr=16000):
    buf = io.BytesIO()
    sf.write(buf, (0.3 * np.sin(np.arange(int(seconds * sr)) / 20)).astype("float32"), sr, format="WAV")
    return buf.getvalue()


def wait(client, job_id, timeout=20):
    end = time.time() + timeout
    while time.time() < end:
        j = client.get(f"/api/jobs/{job_id}").json()
        if j["status"] in ("done", "error", "cancelled"):
            return j
        time.sleep(0.1)
    raise AssertionError("timeout")


def test_chunking():
    text = "First sentence. Second one here!\n\nNew paragraph with a very long sentence, " + "word " * 120 + "end."
    chunks = make_chunks(text, 100)
    assert all(len(c["text"]) <= 100 for c in chunks)
    assert chunks[0]["paragraph_end"] is False or len(chunks) > 1
    assert sum(c["paragraph_end"] for c in chunks) == 2


def test_full_flow():
    with TestClient(app) as c:
        assert c.get("/").status_code == 200
        assert c.get("/api/system").json()["cores"] >= 1
        assert c.get("/api/engines").json()[0]["available"]

        # consent is required
        r = c.post("/api/voices", data={"name": "Me", "consent": "false"},
                   files={"file": ("a.wav", wav_bytes(), "audio/wav")})
        assert r.status_code == 400
        # too short
        r = c.post("/api/voices", data={"name": "Me", "consent": "true"},
                   files={"file": ("a.wav", wav_bytes(0.5), "audio/wav")})
        assert r.status_code == 400
        # good upload
        r = c.post("/api/voices", data={"name": "My voice", "consent": "true"},
                   files={"file": ("a.wav", wav_bytes(), "audio/wav")})
        assert r.status_code == 200, r.text
        vid = r.json()["id"]
        assert any(v["id"] == vid for v in c.get("/api/voices").json()["custom"])
        assert c.get(f"/api/voices/{vid}/audio").status_code == 200
        assert c.patch(f"/api/voices/{vid}", json={"name": "Renamed"}).json()["name"] == "Renamed"

        # render with the custom voice, two jobs back to back
        text = "Hello there. This is a test.\n\nA second paragraph follows here."
        n0 = len(c.get("/api/jobs").json())   # other tests may have left renders behind
        ids = [c.post("/api/jobs", json={"text": text, "engine": "mock", "voice": vid, "format": f}).json()["id"]
               for f in ("wav", "mp3")]
        for jid, ext in zip(ids, ("wav", "mp3")):
            j = wait(c, jid)
            assert j["status"] == "done", j
            assert j["file"].endswith(ext) or j["file"].endswith("wav")
            assert c.get(f"/api/jobs/{jid}/audio").status_code == 200
            assert "-->" in c.get(f"/api/jobs/{jid}/srt").text
        assert len(c.get("/api/jobs").json()) == n0 + 2

        # validation
        assert c.post("/api/jobs", json={"text": "", "engine": "mock", "voice": "tone"}).status_code == 400
        assert c.post("/api/jobs", json={"text": "hi", "engine": "nope", "voice": "tone"}).status_code == 400
        assert c.post("/api/jobs", json={"text": "hi", "engine": "mock", "voice": "../../etc"}).status_code == 400
        assert c.get("/api/jobs/../../etc/passwd").status_code in (404, 422)

        # preview jobs stay out of history
        p = c.post("/api/jobs", json={"engine": "mock", "voice": "tone", "preview": True}).json()
        assert wait(c, p["id"])["status"] == "done"
        assert len(c.get("/api/jobs").json()) == n0 + 2

        # settings
        assert c.put("/api/settings", json={"device": "cpu"}).json()["device"] == "cpu"
        assert c.put("/api/settings", json={"device": "bogus"}).status_code == 400

        # delete
        assert c.delete(f"/api/jobs/{ids[0]}").status_code == 200
        assert c.delete(f"/api/voices/{vid}").status_code == 200


def test_non_latin_chunking():
    hi = make_chunks("नमस्ते दोस्तों। आज हम एक नई चीज़ सीखेंगे। यह बहुत मज़ेदार है!", 30)
    ar = make_chunks("مرحبا بكم. هل أنتم جاهزون؟ لنبدأ الآن.", 20)
    zh = make_chunks("你好。今天我们来学习。很有趣！", 8)
    assert len(hi) == 3 and len(ar) == 3 and len(zh) == 3


def test_kokoro_voice_catalogue():
    from app.engines.kokoro_engine import KokoroEngine

    eng = KokoroEngine()
    voices = eng.stock_voices()
    langs = {v.lang for v in voices}
    assert {"en", "es", "fr", "hi", "it", "pt"} <= langs
    assert all(v.id[0] in "abefhip" for v in voices)
    assert {l["code"] for l in eng.info()["languages"]} == langs
    assert not any(l["code"] == "ar" for l in eng.info()["languages"])  # Arabic is Clone-mode only


def test_language_previews_and_cache():
    from app.languages import CHATTERBOX_LANGS, LANGUAGES

    assert all(code in LANGUAGES for code in CHATTERBOX_LANGS)
    assert "ar" in CHATTERBOX_LANGS and "hi" in CHATTERBOX_LANGS
    with TestClient(app) as c:
        body = {"engine": "mock", "voice": "tone", "preview": True, "options": {"language_id": "hi"}}
        first = c.post("/api/jobs", json=body).json()
        assert wait(c, first["id"])["status"] == "done"
        second = c.post("/api/jobs", json=body).json()
        assert second["status"] == "done"            # served from the preview cache instantly
        assert c.get(f"/api/jobs/{second['id']}/audio").status_code == 200
        # a different language is a different preview
        other = c.post("/api/jobs", json=dict(body, options={"language_id": "ar"})).json()
        assert other["status"] in ("queued", "running", "done") and other["id"] != second["id"]
        # engines advertise languages and the option that carries them
        eng = c.get("/api/engines").json()[0]
        assert eng["language_param"] == "language_id" and len(eng["languages"]) >= 2


def _docx(paragraphs):
    import zipfile

    body = "".join(f"<w:p><w:r><w:t>{p}</w:t></w:r></w:p>" for p in paragraphs)
    xml = ('<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
           f"<w:body>{body}<w:p/></w:body></w:document>")
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as z:
        z.writestr("word/document.xml", xml)
    return buf.getvalue()


import zipfile  # noqa: E402


def test_import_files():
    with TestClient(app) as c:
        post = lambda name, data: c.post("/api/import", files={"file": (name, data)})
        r = post("script.txt", "Hello there.\r\nSecond line.".encode("utf-8-sig"))
        assert r.status_code == 200 and r.json()["text"] == "Hello there.\nSecond line."
        r = post("utf16.txt", "Hola señor".encode("utf-16"))
        assert r.json()["text"] == "Hola señor"
        r = post("hindi.txt", "नमस्ते दोस्तों।".encode("utf-8"))
        assert r.json()["text"] == "नमस्ते दोस्तों।"
        r = post("script.docx", _docx(["First paragraph.", "مرحبا بكم", "Third."]))
        assert r.status_code == 200
        assert r.json()["text"] == "First paragraph.\n\nمرحبا بكم\n\nThird."
        assert post("old.doc", b"x").status_code == 400
        assert post("notes.pdf", b"x").status_code == 400
        assert post("broken.docx", b"not a zip").status_code == 400
        assert post("empty.txt", b"   \n ").status_code == 400


def test_quit_shortcut_and_icons(tmp_path, monkeypatch):
    with TestClient(app) as c:
        assert c.get("/favicon.ico").status_code == 200
        assert c.get("/icon.png").status_code == 200
        monkeypatch.delenv("VOICESTUDIO_ALLOW_QUIT", raising=False)
        assert c.post("/api/quit").status_code == 403
        assert c.get("/api/system").json()["quit_allowed"] is False


import sys  # noqa: E402
import pytest  # noqa: E402


@pytest.mark.skipif(sys.platform == "win32", reason="checks Unix file permissions")
def test_linux_shortcut(tmp_path, monkeypatch):
    import platform

    from app import shortcut

    monkeypatch.setattr(platform, "system", lambda: "Linux")
    monkeypatch.setattr(shortcut.Path, "home", classmethod(lambda cls: tmp_path))
    (tmp_path / "Desktop").mkdir()
    monkeypatch.setattr(shortcut, "_linux_desktop_dir", lambda: tmp_path / "Desktop")
    result = shortcut.create()
    desktop_file = tmp_path / "Desktop" / "voice-studio.desktop"
    assert desktop_file.exists() and (tmp_path / ".local/share/applications/voice-studio.desktop").exists()
    text = desktop_file.read_text()
    assert "Terminal=false" in text and "launcher.py" in text and "voice-studio.png" in text
    assert desktop_file.stat().st_mode & 0o111
    assert len(result["created"]) == 2


# ---------------------------------------------------------------- captions
def _words(text, step=0.4):
    return [{"start": i * step, "end": i * step + 0.35, "text": t} for i, t in enumerate(text.split())]


def test_caption_grouping():
    from app import captions as cap

    words = _words("Welcome back to the channel. Today we talk about voiceovers and why they matter so much!")
    one = cap.build_cues(words, 18, 1)
    assert all(len(c["text"]) <= 18 and "\n" not in c["text"] for c in one)
    assert one[0]["text"] == "Welcome back to" and one[1]["text"] == "the channel."   # cue ends at the sentence end
    two = cap.build_cues(words, 30, 2)
    assert all(c["text"].count("\n") <= 1 for c in two) and len(two) < len(one)
    assert all(len(line) <= 30 for c in two for line in c["text"].split("\n"))
    # nothing lost, nothing overlapping, a minimum on-screen time
    assert " ".join(c["text"].replace("\n", " ") for c in one) == " ".join(w["text"] for w in words)
    assert all(a["end"] <= b["start"] + 1e-9 for a, b in zip(one, one[1:]))
    assert all(c["end"] - c["start"] >= 0.05 for c in one)
    srt = cap.to_srt(one)
    assert srt.startswith("1\n00:00:00,000 --> 00:00:01,150\nWelcome back to\n")
    assert cap.to_txt(one).splitlines()[1] == "[0:00:01] the channel."
    # languages written without spaces
    zh = [{"start": i * 0.3, "end": i * 0.3 + 0.25, "text": t} for i, t in enumerate(["你好", "今天", "我们", "来学习。"])]
    assert cap.build_cues(zh, 4, 1, no_space=True)[0]["text"] == "你好今天"
    # settings are clamped to sane values
    assert cap.normalize({"max_width": 999, "max_lines": 9, "model": "huge"}) == {
        "model": "base", "max_width": 60, "max_lines": 2, "language": None}


def _fake_whisper(monkeypatch, seen):
    from app import captions

    monkeypatch.setattr(captions, "available", lambda: (True, ""))

    def fake(path, model_name, language, device, status=None, progress=None):
        assert os.path.isfile(path)
        seen.append((model_name, language))
        if progress:
            progress(1.0)
        return _words("Hello there and welcome. This is the second sentence of the test."), language or "en"

    monkeypatch.setattr(captions, "transcribe_words", fake)


def test_captions_with_render_upload_and_recaption(monkeypatch):
    seen = []
    _fake_whisper(monkeypatch, seen)
    with TestClient(app) as c:
        info = c.get("/api/captions/info").json()
        assert info["available"] and info["defaults"]["max_width"] == 18

        # 1. a render that also makes short captions (voice language is passed to Whisper)
        job = c.post("/api/jobs", json={"text": "Hola amigos. Esto es una prueba.", "engine": "mock", "voice": "tone",
                                        "options": {"language_id": "es"},
                                        "captions": {"model": "tiny", "max_width": 18, "max_lines": 1}}).json()
        j = wait(c, job["id"])
        assert j["status"] == "done" and j["cap_srt"] and j["cap_cues"] >= 2 and not j["cap_error"], j
        assert seen[-1] == ("tiny", "es")
        srt = c.get(f"/api/jobs/{job['id']}/caption-file/srt")
        assert srt.status_code == 200 and "-->" in srt.text
        assert all(len(line) <= 18 for line in srt.text.splitlines() if line and not line[0].isdigit())
        assert c.get(f"/api/jobs/{job['id']}/caption-file/txt").text.startswith("[0:00:")
        assert c.get(f"/api/jobs/{job['id']}/caption-file/exe").status_code == 404
        assert c.get(f"/api/jobs/{job['id']}/audio").status_code == 200   # the audio is still there

        # 2. any uploaded audio file
        r = c.post("/api/captions", data={"model": "base", "max_width": "30", "max_lines": "2", "language": "hi"},
                   files={"file": ("my talk.wav", wav_bytes(), "audio/wav")})
        assert r.status_code == 200, r.text
        up = wait(c, r.json()["id"])
        assert up["status"] == "done" and up["file"] is None and up["cap_srt"] and up["task"] == "captions"
        assert seen[-1] == ("base", "hi")
        assert c.post("/api/captions", data={}, files={"file": ("notes.pdf", b"x")}).status_code == 400

        # 3. captions for a finished render, with different settings, without re-rendering the audio
        plain = c.post("/api/jobs", json={"text": "One. Two. Three.", "engine": "mock", "voice": "tone"}).json()
        first = wait(c, plain["id"])
        assert first["status"] == "done" and not first.get("cap_srt")
        assert c.post(f"/api/jobs/{plain['id']}/captions", json={"max_width": 30, "max_lines": 2}).status_code == 200
        again = wait(c, plain["id"])
        assert again["status"] == "done" and again["cap_srt"] and again["file"] and again["task"] == "render"
        assert c.post("/api/jobs/aaaaaaaaaaaa/captions", json={}).status_code == 400

        # captions show up in the history list with their downloads
        listed = {j["id"]: j for j in c.get("/api/jobs").json()}
        assert listed[job["id"]]["cap_srt"] and listed[up["id"]]["excerpt"].startswith("Captions for")


def test_captions_unavailable(monkeypatch):
    from app import captions

    monkeypatch.setattr(captions, "available", lambda: (False, "Captions need the 'faster-whisper' package."))
    with TestClient(app) as c:
        assert c.get("/api/captions/info").json()["available"] is False
        r = c.post("/api/captions", data={}, files={"file": ("a.wav", wav_bytes(), "audio/wav")})
        assert r.status_code == 400 and "faster-whisper" in r.json()["detail"]
        # a render that asked for captions still delivers the audio, and says why captions are missing
        job = c.post("/api/jobs", json={"text": "Hello there.", "engine": "mock", "voice": "tone",
                                        "captions": {"max_width": 18}}).json()
        j = wait(c, job["id"])
        assert j["status"] == "done" and j["file"] and not j.get("cap_srt") and "faster-whisper" in j["cap_error"]


# ---------------------------------------------------------------- offline model packs
def test_offline_packs(monkeypatch):
    from app import models, prefetch

    monkeypatch.setattr(models, "_cached", lambda repo: False)
    calls = []
    monkeypatch.setattr(prefetch, "PACKS", {"fast": lambda: calls.append("fast"), "captions": lambda: calls.append("captions"),
                                           "clone": lambda: (_ for _ in ()).throw(RuntimeError("no network"))})
    monkeypatch.setattr(models, "_MARKS", models.MODELS_DIR / ".ready-test.json")
    models._MARKS.unlink(missing_ok=True)
    with TestClient(app) as c:
        before = {p["id"]: p["ready"] for p in c.get("/api/models").json()["packs"]}
        assert before == {"fast": False, "captions": False, "clone": False}
        assert c.post("/api/models/download", json={"packs": ["bogus"]}).status_code == 400
        assert c.post("/api/models/download", json={"packs": ["fast", "captions"]}).status_code == 200
        for _ in range(100):
            st = c.get("/api/models").json()
            if not st["running"]:
                break
            time.sleep(0.05)
        assert calls == ["fast", "captions"] and not st["error"]
        assert {p["id"]: p["ready"] for p in st["packs"]} == {"fast": True, "captions": True, "clone": False}
        # a failing download is reported, not hidden
        assert c.post("/api/models/download", json={"packs": ["clone"]}).status_code == 200
        for _ in range(100):
            st = c.get("/api/models").json()
            if not st["running"]:
                break
            time.sleep(0.05)
        assert "no network" in st["error"] and not st["packs"][2]["ready"]
    models._MARKS.unlink(missing_ok=True)


# ---------------------------------------------------------------- AI-generated marking
def test_audio_is_marked(monkeypatch):
    import sys
    import types

    class FakePerth:
        def apply_watermark(self, wav, watermark=None, sample_rate=24000):
            return wav * 0.99   # same length, as the real one

    fake = types.ModuleType("perth")
    fake.PerthImplicitWatermarker = FakePerth
    monkeypatch.setitem(sys.modules, "perth", fake)
    with TestClient(app) as c:
        for fmt in ("wav", "flac"):
            job = c.post("/api/jobs", json={"text": "Hello there. This is a test.", "engine": "mock", "voice": "tone", "format": fmt}).json()
            j = wait(c, job["id"])
            assert j["status"] == "done" and j["marking"] == "perth" and j["file"].endswith(fmt)
            path = os.path.join(os.environ["VOICESTUDIO_DATA"], "outputs", job["id"], j["file"])
            with sf.SoundFile(path) as f:
                assert "AI-generated" in f.comment and f.software.startswith("Voice Studio")
        # without a watermarker the metadata marking still happens, and the job says so
        monkeypatch.setitem(sys.modules, "perth", None)
        job = c.post("/api/jobs", json={"text": "Another test.", "engine": "mock", "voice": "tone"}).json()
        j = wait(c, job["id"])
        assert j["marking"] == "metadata"
        mp3 = c.post("/api/jobs", json={"text": "An mp3 test.", "engine": "mock", "voice": "tone", "format": "mp3"}).json()
        done = wait(c, mp3["id"])
        assert done["status"] == "done" and done["file"].endswith(("mp3", "wav"))
