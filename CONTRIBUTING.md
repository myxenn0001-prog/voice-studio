# Contributing

Thank you for helping make free voiceovers available to everyone. Every kind of help is welcome:
bug reports, translations of the interface, voice and language testing, documentation, and code.

Be kind and patient. Assume good intent, give specific and respectful feedback, and keep discussions
about the work, not the person.

## Run it from source

```bash
python -m venv .venv && source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install torch==2.6.0 torchaudio==2.6.0                # add --index-url https://download.pytorch.org/whl/cpu on Linux/Windows without a GPU
pip install -r requirements.txt -r requirements-dev.txt
pip install chatterbox-tts "kokoro>=0.9.4" faster-whisper  # engines are optional: the app runs with whichever installs
python run_server.py
```

## Run the tests (no models needed)

```bash
VOICESTUDIO_MOCK=1 python -m pytest tests          # Windows PowerShell: $env:VOICESTUDIO_MOCK=1; python -m pytest tests
```

The tests use a fake voice engine and a fake Whisper, so they run in a few seconds on any computer.

## Where things live

| Folder | What |
|---|---|
| `app/engines/` | One file per voice engine. To add an engine, copy `kokoro_engine.py` and register it in `__init__.py`. |
| `app/languages.py` | Language names, preview sentences, and which engine speaks which language. |
| `app/captions.py` | Whisper captions and the caption-grouping logic. |
| `app/static/index.html` | The whole interface (plain HTML, CSS and JavaScript, no build step). |
| `docs/` | The website, including the in-browser edition in `docs/try/`. |
| `packaging/` | Installers for Windows, macOS and Linux, plus Pinokio, winget and Homebrew files. |

## Pull requests

- Keep each pull request to one change, and say what you tested and on which system.
- Add or update a test when you change behavior.
- Do not add dependencies lightly: each one has to install cleanly on Windows, macOS and Linux.
- Do not add a model unless its license allows free, commercial and redistributed use.
  Say which license in the pull request.
- By contributing, you agree that your contribution is licensed under the Apache License 2.0.
