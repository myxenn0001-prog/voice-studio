#!/usr/bin/env bash
# Voice Studio first-launch setup for macOS and Linux.
# Installs Python and the libraries into a folder in your user account, then opens the app.
# Safe to run again: it just updates what is installed.
#
# Test switches (used by the project's own checks):
#   VOICESTUDIO_SETUP_LIGHT=1     skip the large voice libraries
#   VOICESTUDIO_SETUP_NOLAUNCH=1  do not open the app at the end
set -u
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
case "$(uname)" in
  Darwin) DEFAULT_HOME="$HOME/Library/Application Support/VoiceStudio" ;;
  *)      DEFAULT_HOME="${XDG_DATA_HOME:-$HOME/.local/share}/voice-studio" ;;
esac
HOME_DIR="${VOICESTUDIO_HOME:-$DEFAULT_HOME}"
mkdir -p "$HOME_DIR"
exec > >(tee -a "$HOME_DIR/setup.log") 2>&1

UV="$APP_DIR/bin/uv"; [ -x "$UV" ] || UV="$(command -v uv || true)"
VERSION="$(cat "$APP_DIR/app/VERSION" 2>/dev/null || echo dev)"
export UV_PYTHON_INSTALL_DIR="$HOME_DIR/python" UV_CACHE_DIR="$HOME_DIR/cache" UV_PYTHON_PREFERENCE=only-managed
PY="$HOME_DIR/venv/bin/python"

fail() {
  echo; echo "Setup did not finish: $1"
  echo "Check your internet connection, then open Voice Studio again to retry."
  echo "Details are saved in: $HOME_DIR/setup.log"
  read -r -p "Press Enter to close this window. " _ || true
  exit 1
}
optional() { "$@" || echo "WARNING: that part could not be installed. The rest of the app still works."; }

echo "================================================================"
echo " Setting up Voice Studio $VERSION"
echo " This needs internet and takes several minutes the first time."
echo " Nothing is uploaded; this only downloads the voice software."
echo "================================================================"
[ -n "$UV" ] || fail "the setup tool (uv) is missing from this copy of the app."

[ -x "$PY" ] || "$UV" venv --python 3.11 "$HOME_DIR/venv" || fail "could not create the Python environment."
PIP=("$UV" pip install --python "$PY")

if [ "${VOICESTUDIO_SETUP_LIGHT:-0}" != "1" ]; then
  echo; echo "[1/3] Installing PyTorch..."
  if [ "$(uname)" = "Linux" ]; then
    if command -v nvidia-smi >/dev/null 2>&1; then INDEX=cu124; echo "NVIDIA GPU found."; else INDEX=cpu; fi
    "${PIP[@]}" torch==2.6.0 torchaudio==2.6.0 --index-url "https://download.pytorch.org/whl/$INDEX" \
      --extra-index-url https://pypi.org/simple --index-strategy unsafe-best-match || fail "could not install PyTorch."
  else
    "${PIP[@]}" torch==2.6.0 torchaudio==2.6.0 || fail "could not install PyTorch."
  fi
fi

echo; echo "[2/3] Installing the app..."
"${PIP[@]}" -r "$APP_DIR/app/requirements.txt" || fail "could not install the app's libraries."

if [ "${VOICESTUDIO_SETUP_LIGHT:-0}" != "1" ]; then
  echo; echo "[3/3] Installing the voice engines (Clone, Fast, Captions)..."
  optional "${PIP[@]}" chatterbox-tts
  optional "${PIP[@]}" "kokoro>=0.9.4"
  optional "${PIP[@]}" faster-whisper
fi

if [ "${VOICESTUDIO_SETUP_LIGHT:-0}" != "1" ]; then
  echo; echo "Downloading the voice models so everything works offline..."
  ( cd "$APP_DIR/app" && VOICESTUDIO_DATA="$HOME_DIR/data" "$PY" -m app.prefetch ) \
    || echo "WARNING: some models were not downloaded. They download on first use instead, or use the 'This computer' tab."
fi

echo "$VERSION" > "$HOME_DIR/.installed"
echo; echo "Done."

if [ "${VOICESTUDIO_SETUP_NOLAUNCH:-0}" != "1" ]; then
  export VOICESTUDIO_DATA="$HOME_DIR/data" VOICESTUDIO_INSTALLED=1
  echo "Voice Studio is opening. You can close this window."
  if command -v setsid >/dev/null 2>&1; then
    setsid nohup "$PY" "$APP_DIR/app/launcher.py" >/dev/null 2>&1 &
  else
    nohup "$PY" "$APP_DIR/app/launcher.py" >/dev/null 2>&1 &
  fi
  sleep 3
fi
