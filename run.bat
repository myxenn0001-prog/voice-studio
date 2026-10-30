@echo off
title Voice Studio
cd /d "%~dp0"

set PY=
for %%V in (3.11 3.10 3.12) do (
  if not defined PY (py -%%V --version >nul 2>&1 && set PY=py -%%V)
)
if not defined PY (
  echo Python 3.10 or newer is required. Install it from https://www.python.org/downloads/
  echo Tick "Add python.exe to PATH" during setup, then run this file again.
  pause & exit /b 1
)

if not exist .venv (%PY% -m venv .venv)
call .venv\Scripts\activate.bat

if not exist .venv\.installed (
  echo Installing Voice Studio - first run only, this takes 5 to 10 minutes...
  python -m pip install --upgrade pip
  where nvidia-smi >nul 2>&1
  if errorlevel 1 (
    pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cpu
  ) else (
    echo NVIDIA GPU found, installing GPU build.
    pip install torch==2.6.0 torchaudio==2.6.0 --index-url https://download.pytorch.org/whl/cu124
  )
  pip install -r requirements.txt
  pip install chatterbox-tts || echo WARNING: Clone mode could not be installed.
  pip install "kokoro>=0.9.4" || echo WARNING: Fast mode could not be installed.
  pip install faster-whisper || echo WARNING: Captions could not be installed.
  python -m app.prefetch || echo Some models were not downloaded now. They download on first use instead.
  echo done> .venv\.installed
  python create_shortcut.py || echo Could not add a desktop shortcut. You can add one later from the This computer tab.
)

set VOICESTUDIO_DATA=%CD%\data
python run_server.py
pause
