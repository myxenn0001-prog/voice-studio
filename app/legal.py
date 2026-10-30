"""The Terms of Use the user accepts the first time they open the app."""
from __future__ import annotations

import os

from .config import load_settings

TERMS_VERSION = "1.0"   # must match "Version" at the top of TERMS_OF_USE.md; bump both when the Terms change materially
CONSENT_STATEMENT = "I own this voice or have permission from the speaker to clone it."


def accepted() -> bool:
    """True once this version of the Terms was accepted. Automated installs and tests can set
    VOICESTUDIO_TERMS_ACCEPTED=1, which means the person installing has already accepted them."""
    if os.environ.get("VOICESTUDIO_TERMS_ACCEPTED") == "1":
        return True
    return load_settings().get("terms_accepted") == TERMS_VERSION
