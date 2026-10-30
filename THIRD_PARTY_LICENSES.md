# Third-party software

Voice Studio's own code is licensed under the Apache License 2.0 (see `LICENSE`).
It uses the open-source projects below. Licenses are listed to the best of our knowledge
and **were written from memory, so confirm them before each release**, for example with
`pip install pip-licenses && pip-licenses --format=markdown` inside the installed environment.

## Voice models (downloaded on first use, not shipped in the installers)

| Project | Used for | License |
|---|---|---|
| Kokoro-82M (code and weights) | Fast mode voices | Apache-2.0 |
| Chatterbox and Chatterbox Multilingual | Clone mode | MIT |
| OpenAI Whisper models, via faster-whisper | Captions | MIT |
| Perth watermarker (resemble-perth), installed with Chatterbox | Marks audio as AI-generated | MIT (confirm) |

## Libraries installed on first launch

| Project | License |
|---|---|
| PyTorch, torchaudio | BSD-3-Clause |
| faster-whisper, CTranslate2 | MIT |
| FastAPI, Pydantic | MIT |
| Starlette, Uvicorn | BSD-3-Clause |
| python-multipart | Apache-2.0 |
| NumPy, SoundFile, psutil | BSD-3-Clause |
| libsndfile (bundled inside SoundFile wheels) | LGPL-2.1-or-later |
| Hugging Face Hub, Transformers | Apache-2.0 |
| misaki (Kokoro's text front end) | Apache-2.0 |
| spaCy | MIT |
| ONNX Runtime | MIT |
| PyAV | BSD-3-Clause |

## Tools used by the installers

| Project | License |
|---|---|
| uv (sets up Python and the libraries on first launch) | MIT or Apache-2.0 |
| Python (downloaded by uv) | PSF License |
| Inno Setup (Windows installer builder) | Inno Setup License |
| Python-Markdown (builds the legal web pages; development only) | BSD-3-Clause |
| AppImageKit appimagetool (Linux package builder) | MIT |

## Browser edition (`docs/try/`)

| Project | License |
|---|---|
| kokoro-js | Apache-2.0 |
| Transformers.js (Hugging Face) | Apache-2.0 |

## One item that needs your attention: GPL components

Fast mode's pronunciation step relies on **espeak-ng** and **phonemizer**, which, to our knowledge,
are licensed under the **GPL-3.0**. Voice Studio's installers do **not** contain them: they are downloaded
from the Python Package Index onto the user's own computer on first launch, which is the user's own use of
those packages. Voice Studio's installers contain only our Apache-2.0 code and the small `uv` tool.

This reasoning stops applying if you (or anyone who forks the project) ever publish something that **includes**
those packages, for example a pre-built Docker image or a fully offline installer. In that case you must
comply with the GPL for those parts (include their license text and offer their source code), and you should
ask a lawyer how the combined work is licensed. This file is not legal advice.
