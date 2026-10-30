import os

from .chatterbox_engine import ChatterboxEngine
from .kokoro_engine import KokoroEngine

ENGINES = {e.id: e for e in (KokoroEngine(), ChatterboxEngine())}

if os.environ.get("VOICESTUDIO_MOCK") == "1":
    from .mock_engine import MockEngine

    ENGINES = {"mock": MockEngine()}
