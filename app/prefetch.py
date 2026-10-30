"""Downloads voice models ahead of time so Voice Studio works with no internet.

    python -m app.prefetch              Fast mode voices + captions (what the installers do)
    python -m app.prefetch --clone      also the voice-cloning models (several GB)
    python -m app.prefetch --all

Also used by `docker build --build-arg PREFETCH=1` and by the "Use offline" panel in the app.
"""
from __future__ import annotations

import argparse
import importlib
import sys

from . import config  # noqa: F401  (sets HF_HOME so files land where the app looks for them)


def say(msg: str) -> None:
    print(f"[voice-studio] {msg}", flush=True)


def fetch_fast() -> None:
    from huggingface_hub import snapshot_download

    say("Downloading the Fast-mode voices…")
    snapshot_download("hexgrad/Kokoro-82M")
    say("Preparing pronunciation data (the English front end downloads a small language model once)…")
    from kokoro import KPipeline

    pipe = KPipeline(lang_code="a", repo_id="hexgrad/Kokoro-82M", device="cpu")
    for _ in pipe("Hello.", voice="af_heart"):
        break


def fetch_captions(model: str = "base") -> None:
    from faster_whisper import WhisperModel

    say(f"Downloading the caption model ({model})…")
    WhisperModel(model, device="cpu", compute_type="int8")


def fetch_clone() -> None:
    import torch

    for label, module, cls in (("Clone mode (English)", "chatterbox.tts", "ChatterboxTTS"),
                               ("Clone mode (multilingual)", "chatterbox.mtl_tts", "ChatterboxMultilingualTTS")):
        say(f"Downloading {label}…")
        original = torch.load
        torch.load = lambda *a, **k: original(*a, **{**k, "map_location": k.get("map_location", "cpu")})
        try:
            getattr(importlib.import_module(module), cls).from_pretrained(device="cpu")
        finally:
            torch.load = original


PACKS = {"fast": fetch_fast, "captions": fetch_captions, "clone": fetch_clone}


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--fast", action="store_true")
    ap.add_argument("--captions", action="store_true")
    ap.add_argument("--clone", action="store_true")
    ap.add_argument("--all", action="store_true")
    a = ap.parse_args(argv)
    chosen = [p for p in PACKS if getattr(a, p) or a.all] or ["fast", "captions"]
    from .models import mark_ready

    failed = []
    for pack in chosen:
        try:
            PACKS[pack]()
            mark_ready(pack)
        except Exception as exc:  # one failing pack must not stop the others
            say(f"Could not download '{pack}': {exc}")
            failed.append(pack)
    say("Done." if not failed else f"Finished, but these could not be downloaded: {', '.join(failed)}. "
        "You can try again later from the 'This computer' tab.")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
