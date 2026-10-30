"""Takes the screenshots used in the README and on the website (docs/screenshots/).

It runs the REAL interface, but swaps the voice models for a test tone so no models are needed,
and reports a typical computer's hardware so the pictures look like a normal install.
Developer tool only: pip install playwright && playwright install chromium
Usage: python tools/make_screenshots.py
"""
import asyncio
import io
import os
import shutil
import sys
import tempfile
import threading
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "screenshots"
DATA = tempfile.mkdtemp(prefix="vs-shots-")
os.environ["VOICESTUDIO_DATA"] = DATA
os.environ["VOICESTUDIO_TERMS_ACCEPTED"] = "1"
sys.path.insert(0, str(ROOT))

import numpy as np  # noqa: E402
import soundfile as sf  # noqa: E402
import uvicorn  # noqa: E402

from app import captions, system  # noqa: E402
from app.engines.chatterbox_engine import ChatterboxEngine  # noqa: E402
from app.engines.kokoro_engine import KokoroEngine  # noqa: E402

# --- stand-ins: tones instead of speech, a canned Whisper, and typical hardware -----------------
for cls in (KokoroEngine, ChatterboxEngine):
    cls.available = lambda self: (True, "")
    cls.load = lambda self, device: setattr(self, "_model", True) or setattr(self, "_device", device)
    cls.ready_for = lambda self, options, voice: True
    cls.synth = lambda self, text, voice, options: (0.2 * np.sin(2 * np.pi * 220 * np.arange(int(24000 * min(0.05 * len(text), 3))) / 24000)).astype("float32")
captions.available = lambda: (True, "")
captions.transcribe_words = lambda path, model, lang, device, status=None, progress=None: (
    [{"start": i * 0.4, "end": i * 0.4 + 0.35, "text": w} for i, w in enumerate(
        "Welcome back to the channel. Today we are making a voiceover for free.".split())], lang or "en")
_real_info = system.system_info
def _typical(settings):
    info = _real_info(settings)
    info.update(os="Windows 11", arch="AMD64", ram_gb=16.0, cores=8, devices=[{"id": "cpu", "label": "CPU (8 cores)"}],
                best_device="cpu", tier="cpu", recommended_engine="kokoro",
                advice="No GPU found, which is fine. Fast mode is quick on this CPU. Voice cloning works too, "
                       "but expect it to be several times slower than real time.",
                version="1.0.0", branding={"company": "", "company_url": "", "repo": "", "site": "", "support_email": ""})
    return info
import app.main as main  # noqa: E402
main.system_info = _typical

PORT = 8799
server = uvicorn.Server(uvicorn.Config(main.app, host="127.0.0.1", port=PORT, log_level="warning"))
threading.Thread(target=server.run, daemon=True).start()
for _ in range(60):
    try:
        urllib.request.urlopen(f"http://127.0.0.1:{PORT}/api/system", timeout=1)
        break
    except Exception:
        time.sleep(0.25)

SCRIPT = ("Welcome back to the channel. Today we are looking at how a small team can make professional "
          "voiceovers without paying for a subscription.\n\nFirst, paste your script. Then pick a voice, "
          "press one button, and download the audio.")


def wav(seconds=8, freq=180):
    t = np.arange(int(16000 * seconds)) / 16000
    buf = io.BytesIO()
    sf.write(buf, (0.25 * np.sin(2 * np.pi * freq * t)).astype("float32"), 16000, format="WAV")
    return buf.getvalue()


async def main_async():
    from playwright.async_api import async_playwright
    OUT.mkdir(parents=True, exist_ok=True)
    async with async_playwright() as p:
        b = await p.chromium.launch()
        pg = await b.new_page(viewport={"width": 1280, "height": 940}, color_scheme="light")

        async def shot(name):  # top of the page, no leftover notifications
            await pg.evaluate("window.scrollTo(0, 0); document.querySelectorAll('.toast').forEach(t => t.remove())")
            await pg.wait_for_timeout(150)
            await pg.screenshot(path=str(OUT / name))

        await pg.goto(f"http://127.0.0.1:{PORT}")
        await pg.wait_for_timeout(700)

        # two sample voices of "your own"
        await pg.click("[data-tab=voices]")
        for name, f in (("Narrator", 150), ("Sam (podcast)", 210)):
            open(f"{DATA}/v.wav", "wb").write(wav(12, f))
            await pg.set_input_files("#voiceFile", f"{DATA}/v.wav")
            await pg.fill("#voiceName", name)
            await pg.check("#consent")
            await pg.click("#addVoiceBtn")
            await pg.wait_for_timeout(500)
        await shot("voices.png")

        # studio: a finished render with short captions
        await pg.click("[data-tab=studio]")
        await pg.fill("#script", SCRIPT)
        await pg.check("#capOn")
        await pg.click("#capStudio button:has-text('Short-form')")
        await pg.click("#renderBtn")
        await pg.wait_for_selector("#job a:has-text('Short captions')", timeout=20000)
        await pg.wait_for_timeout(300)
        await shot("studio.png")

        # captions tab with a finished file
        await pg.click("[data-tab=captions]")
        open(f"{DATA}/interview.wav", "wb").write(wav(10, 190))
        await pg.set_input_files("#capFile", f"{DATA}/interview.wav")
        await pg.click("#capGo")
        await pg.wait_for_selector("#capJob a:has-text('Short captions')", timeout=20000)
        await pg.wait_for_timeout(300)
        await shot("captions.png")
        await b.close()


try:
    asyncio.run(main_async())
    print("Screenshots written to", OUT)
finally:
    server.should_exit = True
    shutil.rmtree(DATA, ignore_errors=True)
