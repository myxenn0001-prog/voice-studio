"""Development/test engine: returns a short tone instead of speech.
Enabled only when VOICESTUDIO_MOCK=1."""
import time

import numpy as np

from ..languages import language_list
from .base import Engine, VoiceRef


class MockEngine(Engine):
    id = "mock"
    name = "Mock"
    tagline = "Test engine"
    license = "n/a"
    supports_cloning = True
    languages = language_list(["en", "es", "hi", "ar"])
    language_param = "language_id"
    params = []

    def available(self):
        return True, ""

    def load(self, device):
        self._model, self._device = True, device

    def stock_voices(self):
        return [VoiceRef(id="tone", name="Test tone", kind="stock")]

    def synth(self, text, voice, options):
        time.sleep(0.02)
        n = int(self.sample_rate * min(0.05 * len(text), 4))
        t = np.arange(n) / self.sample_rate
        return (0.2 * np.sin(2 * np.pi * 220 * t)).astype(np.float32)
