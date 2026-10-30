"""Marks everything Voice Studio makes as AI-generated, in a machine-readable way.

Two layers (see RESPONSIBLE_USE.md and the Terms of Use):
  1. File metadata (a comment and software tag inside the WAV / FLAC / MP3 file).
  2. An inaudible watermark. The Clone-mode model (Chatterbox) adds its own. For other engines we apply the same
     open-source watermarker (Resemble's "Perth") when it is installed.
Metadata is easy to strip and a watermark can be weakened by editing, so neither is a guarantee. They are
reasonable, standard measures; whether they satisfy the rules that apply to you is a question for your lawyer.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import soundfile as sf

from .system import _read

DISCLOSURE = "AI-generated speech. Made with Voice Studio."


def version() -> str:
    return _read("VERSION", "dev")


def watermark(audio: np.ndarray, sr: int) -> tuple[np.ndarray, str | None]:
    """Returns (audio, method). method is None when no watermarker is available."""
    try:
        import perth

        marked = perth.PerthImplicitWatermarker().apply_watermark(audio, sample_rate=sr)
        marked = np.asarray(marked, dtype=np.float32).reshape(-1)
        if marked.shape == audio.shape:
            return marked, "perth"
    except Exception:
        pass
    return audio, None


_FORMATS = {"wav": ("WAV", "PCM_16"), "flac": ("FLAC", "PCM_16"), "mp3": ("MP3", None)}


def write_audio(path: Path, audio: np.ndarray, sr: int, fmt: str) -> str:
    """Writes the file with the AI-generated tags inside it. Returns the file name actually written."""
    fmt = fmt if fmt in _FORMATS else "wav"
    target = path.with_suffix("." + fmt)
    kind, subtype = _FORMATS[fmt]
    try:
        kwargs = {"subtype": subtype} if subtype else {}
        with sf.SoundFile(str(target), "w", samplerate=sr, channels=1, format=kind, **kwargs) as f:
            f.software = f"Voice Studio {version()}"
            f.comment = DISCLOSURE
            f.write(audio)
        return target.name
    except Exception:  # an unusual system without MP3 support, for example: fall back to WAV
        target.unlink(missing_ok=True)
        fallback = path.with_suffix(".wav")
        with sf.SoundFile(str(fallback), "w", samplerate=sr, channels=1, format="WAV", subtype="PCM_16") as f:
            f.software = f"Voice Studio {version()}"
            f.comment = DISCLOSURE
            f.write(audio)
        return fallback.name
