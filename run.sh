#!/usr/bin/env bash
# Linux / macOS: run Voice Studio directly (no Docker). Uses your GPU if you have one:
# NVIDIA on Linux, Apple Silicon (Metal) on Mac. First run installs everything (~5-10 min).
set -e
cd "$(dirname "$0")"

PY=""
for c in python3.11 python3.10 python3.12 python3; do
  if command -v $c >/dev/null 2>&1; then PY=$c; break; fi
done
[ -z "$PY" ] && { echo "Python 3.10 or newer is required. Install it from https://www.python.org/downloads/"; exit 1; }

if [ ! -d .venv ]; then "$PY" -m venv .venv; fi
source .venv/bin/activate

if [ ! -f .venv/.installed ] || [ "$1" = "--update" ]; then
  echo "Installing Voice Studio (first run only)..."
  pip install --upgrade pip
  if [ "$(uname)" = "Linux" ] && ! command -v nvidia-smi >/dev/null 2>&1; then
    pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu \
      || pip install torch==2.6.0 torchaudio==2.6.0
  else
    pip install torch==2.6.0 torchaudio==2.6.0
  fi
  pip install -r requirements.txt
  pip install chatterbox-tts || echo "WARNING: Clone mode could not be installed."
  pip install "kokoro>=0.9.4" || echo "WARNING: Fast mode could not be installed."
  pip install faster-whisper || echo "WARNING: Captions could not be installed."
  python -m app.prefetch || echo "(Some models were not downloaded now. They download on first use instead.)"
  touch .venv/.installed
  python create_shortcut.py || echo "(Could not add a desktop shortcut. You can add one later from the This computer tab.)"
fi

export VOICESTUDIO_DATA="$PWD/data"
python run_server.py
