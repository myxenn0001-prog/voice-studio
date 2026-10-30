"""Clone mode: Chatterbox (MIT). Zero-shot voice cloning from a short sample.
English uses the English model; every other language uses Chatterbox Multilingual
(23 languages, and a voice sample in one language can speak another).
Runs on CPU (slow), NVIDIA GPUs, and Apple Silicon. Output carries an inaudible
Perth watermark added by the model itself."""
import importlib
import importlib.util
import os

import numpy as np

from ..languages import CHATTERBOX_LANGS, language_list
from .base import Engine, VoiceRef


class ChatterboxEngine(Engine):
    id = "chatterbox"
    name = "Clone"
    tagline = "Copy any voice from a short sample, in many languages. Best with a GPU; works on CPU, slowly."
    license = "MIT (free for commercial use)"
    supports_cloning = True
    adds_watermark = True   # Chatterbox embeds the Perth watermark itself
    language_param = "language_id"
    params = [
        {"key": "exaggeration", "label": "Expressiveness", "type": "range",
         "min": 0.25, "max": 1.5, "step": 0.05, "default": 0.5},
        {"key": "cfg_weight", "label": "Pacing control", "type": "range",
         "min": 0.0, "max": 1.0, "step": 0.05, "default": 0.5},
    ]

    def __init__(self):
        super().__init__()
        self._en = None
        self._mtl = None

    # -- availability / languages -------------------------------------
    def available(self):
        if importlib.util.find_spec("chatterbox") is None:
            return False, "The 'chatterbox-tts' package is not installed."
        return True, ""

    def _has_multilingual(self):
        spec = importlib.util.find_spec("chatterbox")
        if not spec or not spec.submodule_search_locations:
            return False
        return any(os.path.exists(os.path.join(p, "mtl_tts.py")) for p in spec.submodule_search_locations)

    @property
    def languages(self):
        return language_list(CHATTERBOX_LANGS if self._has_multilingual() else ["en"])

    @staticmethod
    def _kind(options):
        return "en" if ((options or {}).get("language_id") or "en") == "en" else "mtl"

    # -- lifecycle ------------------------------------------------------
    def load(self, device):
        with self._lock:
            self._device = device
            self._en = self._mtl = None
            self._model = True  # real models load per language in prepare()

    def ready_for(self, options, voice):
        if not self.loaded:
            return False
        return (self._en if self._kind(options) == "en" else self._mtl) is not None

    def _from_pretrained(self, module, cls):
        import torch

        device = self._device
        original = torch.load

        def patched(*args, **kwargs):  # checkpoints were saved on CUDA; remap for CPU / Apple GPU
            kwargs.setdefault("map_location", torch.device(device))
            return original(*args, **kwargs)

        torch.load = patched
        try:
            return getattr(importlib.import_module(module), cls).from_pretrained(device=device)
        finally:
            torch.load = original

    def prepare(self, options, voice):
        kind = self._kind(options)
        with self._lock:
            if kind == "en":
                if self._en is None:
                    self._mtl = None  # free memory before loading the other model
                    print("[voice-studio] Loading Clone-mode model (first time downloads it)...", flush=True)
                    self._en = self._from_pretrained("chatterbox.tts", "ChatterboxTTS")
                model = self._en
            else:
                if not self._has_multilingual():
                    raise RuntimeError("This language needs a newer chatterbox-tts. "
                                       "Run the launcher with --update (Mac/Linux) or reinstall to upgrade it.")
                if self._mtl is None:
                    self._en = None
                    print("[voice-studio] Loading multilingual Clone-mode model "
                          "(first time downloads it)...", flush=True)
                    self._mtl = self._from_pretrained("chatterbox.mtl_tts", "ChatterboxMultilingualTTS")
                model = self._mtl
            self.sample_rate = int(getattr(model, "sr", 24000))

    def unload(self):
        self._en = self._mtl = None
        super().unload()

    # -- voices & synthesis ------------------------------------------
    def stock_voices(self):
        return [VoiceRef(id="default", name="Chatterbox default voice", kind="stock")]

    def synth(self, text, voice, options):
        import torch

        kind = self._kind(options)
        model = self._en if kind == "en" else self._mtl
        kwargs = {
            "exaggeration": float(options.get("exaggeration", 0.5)),
            "cfg_weight": float(options.get("cfg_weight", 0.5)),
        }
        if kind == "mtl":
            kwargs["language_id"] = options["language_id"]
        if voice.kind == "custom" and voice.path:
            kwargs["audio_prompt_path"] = voice.path
        with torch.inference_mode():
            wav = model.generate(text, **kwargs)
        return wav.detach().cpu().numpy().astype(np.float32).reshape(-1)
