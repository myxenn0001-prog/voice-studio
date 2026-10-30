"""Fast mode: Kokoro-82M (Apache-2.0). Small, quick on plain CPUs, ships many
built-in voices in several languages. It does not clone voices.

Language support is per voice: the first letter of a voice id is its language
(a/b = English, e = Spanish, f = French, h = Hindi, i = Italian, p = Portuguese).
Japanese (j) and Mandarin (z) also exist but need extra packages (misaki[ja], misaki[zh])."""
import importlib.util

import numpy as np

from ..languages import KOKORO_LANGS, language_list
from .base import Engine, VoiceRef

# id -> (display name, language code)
_VOICES = {
    # English (US)
    "af_heart": ("Heart (US, female)", "en"), "af_bella": ("Bella (US, female)", "en"),
    "af_nicole": ("Nicole (US, female)", "en"), "af_sarah": ("Sarah (US, female)", "en"),
    "af_sky": ("Sky (US, female)", "en"), "af_nova": ("Nova (US, female)", "en"),
    "af_aoede": ("Aoede (US, female)", "en"), "af_kore": ("Kore (US, female)", "en"),
    "af_jessica": ("Jessica (US, female)", "en"), "af_river": ("River (US, female)", "en"),
    "am_adam": ("Adam (US, male)", "en"), "am_michael": ("Michael (US, male)", "en"),
    "am_eric": ("Eric (US, male)", "en"), "am_liam": ("Liam (US, male)", "en"),
    "am_onyx": ("Onyx (US, male)", "en"), "am_fenrir": ("Fenrir (US, male)", "en"),
    "am_puck": ("Puck (US, male)", "en"), "am_echo": ("Echo (US, male)", "en"),
    # English (UK)
    "bf_emma": ("Emma (UK, female)", "en"), "bf_isabella": ("Isabella (UK, female)", "en"),
    "bf_alice": ("Alice (UK, female)", "en"), "bf_lily": ("Lily (UK, female)", "en"),
    "bm_george": ("George (UK, male)", "en"), "bm_daniel": ("Daniel (UK, male)", "en"),
    "bm_lewis": ("Lewis (UK, male)", "en"), "bm_fable": ("Fable (UK, male)", "en"),
    # Spanish
    "ef_dora": ("Dora (female)", "es"), "em_alex": ("Alex (male)", "es"), "em_santa": ("Santa (male)", "es"),
    # French
    "ff_siwis": ("Siwis (female)", "fr"),
    # Hindi
    "hf_alpha": ("Alpha (female)", "hi"), "hf_beta": ("Beta (female)", "hi"),
    "hm_omega": ("Omega (male)", "hi"), "hm_psi": ("Psi (male)", "hi"),
    # Italian
    "if_sara": ("Sara (female)", "it"), "im_nicola": ("Nicola (male)", "it"),
    # Brazilian Portuguese
    "pf_dora": ("Dora (female)", "pt"), "pm_alex": ("Alex (male)", "pt"), "pm_santa": ("Santa (male)", "pt"),
}
_PIPELINE_LANG = set("abefhip")


class KokoroEngine(Engine):
    id = "kokoro"
    name = "Fast"
    tagline = "Built-in voices in 6 languages. Quick on any computer, no GPU needed."
    license = "Apache-2.0 (free for commercial use)"
    supports_cloning = False
    languages = language_list(KOKORO_LANGS)
    language_param = None  # the chosen voice decides the language
    params = [
        {"key": "speed", "label": "Speaking speed", "type": "range",
         "min": 0.6, "max": 1.4, "step": 0.05, "default": 1.0},
    ]

    def __init__(self):
        super().__init__()
        self._pipelines = {}

    def available(self):
        if importlib.util.find_spec("kokoro") is None:
            return False, "The 'kokoro' package is not installed."
        return True, ""

    def pick_device(self, requested):
        # 82M parameters: CPU is already fast, and CUDA is the only GPU path worth using.
        return "cuda" if requested == "cuda" else "cpu"

    def load(self, device):
        from kokoro import KPipeline

        with self._lock:
            self._device = device
            self._pipelines = {}
            self._model = True  # real models load per language in prepare()
            self._KPipeline = KPipeline

    @staticmethod
    def _lang_code(voice):
        c = voice.id[:1]
        return c if c in _PIPELINE_LANG else "a"

    def ready_for(self, options, voice):
        return self.loaded and self._lang_code(voice) in self._pipelines

    def prepare(self, options, voice):
        self._pipeline(self._lang_code(voice))

    def _pipeline(self, lang_code):
        if lang_code not in self._pipelines:
            print(f"[voice-studio] Loading Fast-mode model for language '{lang_code}' "
                  "(first time downloads it)...", flush=True)
            self._pipelines[lang_code] = self._KPipeline(
                lang_code=lang_code, device=self._device, repo_id="hexgrad/Kokoro-82M")
        return self._pipelines[lang_code]

    def unload(self):
        self._pipelines = {}
        super().unload()

    def stock_voices(self):
        return [VoiceRef(id=k, name=v[0], kind="stock", lang=v[1]) for k, v in _VOICES.items()]

    def synth(self, text, voice, options):
        speed = float(options.get("speed", 1.0))
        pipe = self._pipeline(self._lang_code(voice))
        parts = []
        for _, _, audio in pipe(text, voice=voice.id, speed=speed):
            if audio is not None:
                parts.append(np.asarray(audio, dtype=np.float32).reshape(-1))
        if not parts:
            raise RuntimeError("The model returned no audio for this text.")
        return np.concatenate(parts)
