"""Engine interface. To add a new TTS model, subclass Engine and register it
in engines/__init__.py. The rest of the app needs no changes."""
from __future__ import annotations

import threading
from dataclasses import dataclass

import numpy as np


@dataclass
class VoiceRef:
    id: str
    name: str
    kind: str                 # "stock" or "custom"
    path: str | None = None   # reference audio for custom voices
    lang: str = ""            # language code for stock voices ("" = any)


class Engine:
    id = "base"
    name = "Base engine"
    tagline = ""
    license = ""
    supports_cloning = False
    sample_rate = 24000
    # Extra controls the UI should show for this engine.
    params: list = []
    languages: list = []          # [{'code': 'es', 'name': 'Spanish'}]
    language_param = None         # option key that carries the language, or None if the voice decides
    adds_watermark = False        # True if the model already watermarks its own output

    def __init__(self):
        self._model = None
        self._device = None
        self._lock = threading.Lock()

    # -- availability -------------------------------------------------
    def available(self) -> tuple[bool, str]:
        """(ok, reason). Must not import heavy libraries at module import time."""
        raise NotImplementedError

    def pick_device(self, requested: str) -> str:
        return requested

    # -- lifecycle ----------------------------------------------------
    @property
    def loaded(self) -> bool:
        return self._model is not None

    def load(self, device: str) -> None:
        raise NotImplementedError

    def ready_for(self, options: dict, voice: VoiceRef) -> bool:
        """True if no further (slow) model loading is needed for this request."""
        return self.loaded

    def prepare(self, options: dict, voice: VoiceRef) -> None:
        """Load or download whatever this request needs. Called before rendering."""

    def unload(self) -> None:
        with self._lock:
            self._model = None
            self._device = None
        try:
            import gc

            import torch

            gc.collect()
            if torch.cuda.is_available():
                torch.cuda.empty_cache()
        except Exception:
            pass

    # -- voices & synthesis ------------------------------------------
    def stock_voices(self) -> list[VoiceRef]:
        return []

    def synth(self, text: str, voice: VoiceRef, options: dict) -> np.ndarray:
        """Return mono float32 audio at self.sample_rate."""
        raise NotImplementedError

    def info(self) -> dict:
        ok, reason = self.available()
        return {
            "id": self.id,
            "name": self.name,
            "tagline": self.tagline,
            "license": self.license,
            "supports_cloning": self.supports_cloning,
            "available": ok,
            "unavailable_reason": "" if ok else reason,
            "loaded": self.loaded,
            "device": self._device,
            "params": self.params,
            "languages": self.languages,
            "language_param": self.language_param,
        }
