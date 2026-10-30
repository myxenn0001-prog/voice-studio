@echo off
rem Voice Studio first-launch setup for Windows. Safe to run again: it updates what is installed.
rem Test switches: VOICESTUDIO_SETUP_LIGHT=1 skips the big voice libraries, VOICESTUDIO_SETUP_NOLAUNCH=1 does not open the app.
setlocal EnableExtensions
title Setting up Voice Studio
set "APP_DIR=%~dp0"
if not defined VOICESTUDIO_HOME set "VOICESTUDIO_HOME=%LOCALAPPDATA%\VoiceStudio"
set "HOME_DIR=%VOICESTUDIO_HOME%"
set "UV=%APP_DIR%bin\uv.exe"
set "UV_PYTHON_INSTALL_DIR=%HOME_DIR%\python"
set "UV_CACHE_DIR=%HOME_DIR%\cache"
set "UV_PYTHON_PREFERENCE=only-managed"
set "PY=%HOME_DIR%\venv\Scripts\python.exe"
if not exist "%HOME_DIR%" mkdir "%HOME_DIR%"
set "VERSION=dev"
if exist "%APP_DIR%app\VERSION" set /p VERSION=<"%APP_DIR%app\VERSION"

echo ================================================================
echo  Setting up Voice Studio %VERSION%
echo  This needs internet and takes several minutes the first time.
echo  Nothing is uploaded; this only downloads the voice software.
echo ================================================================
if not exist "%UV%" ( set "MSG=the setup tool (uv) is missing from this copy of the app." & goto fail )

if not exist "%PY%" "%UV%" venv --python 3.11 "%HOME_DIR%\venv"
if errorlevel 1 ( set "MSG=could not create the Python environment." & goto fail )

if "%VOICESTUDIO_SETUP_LIGHT%"=="1" goto core
echo.
echo [1/3] Installing PyTorch...
where nvidia-smi >nul 2>&1
if errorlevel 1 (
  set "TORCH_INDEX=https://download.pytorch.org/whl/cpu"
) else (
  echo NVIDIA GPU found.
  set "TORCH_INDEX=https://download.pytorch.org/whl/cu124"
)
"%UV%" pip install --python "%PY%" torch==2.6.0 torchaudio==2.6.0 --index-url %TORCH_INDEX% --extra-index-url https://pypi.org/simple --index-strategy unsafe-best-match
if errorlevel 1 ( set "MSG=could not install PyTorch." & goto fail )

:core
echo.
echo [2/3] Installing the app...
"%UV%" pip install --python "%PY%" -r "%APP_DIR%app\requirements.txt"
if errorlevel 1 ( set "MSG=could not install the app's libraries." & goto fail )

if "%VOICESTUDIO_SETUP_LIGHT%"=="1" goto done
echo.
echo [3/3] Installing the voice engines (Clone, Fast, Captions)...
"%UV%" pip install --python "%PY%" chatterbox-tts || echo WARNING: Clone mode could not be installed. The rest of the app still works.
"%UV%" pip install --python "%PY%" "kokoro>=0.9.4" || echo WARNING: Fast mode could not be installed. The rest of the app still works.
"%UV%" pip install --python "%PY%" faster-whisper || echo WARNING: Captions could not be installed. The rest of the app still works.

echo.
echo Downloading the voice models so everything works offline...
pushd "%APP_DIR%app"
set "VOICESTUDIO_DATA=%HOME_DIR%\data"
"%PY%" -m app.prefetch || echo WARNING: some models were not downloaded. They download on first use instead, or use the "This computer" tab.
popd

:done
> "%HOME_DIR%\.installed" echo %VERSION%
echo.
echo Done.
if "%VOICESTUDIO_SETUP_NOLAUNCH%"=="1" exit /b 0
set "VOICESTUDIO_DATA=%HOME_DIR%\data"
set "VOICESTUDIO_INSTALLED=1"
echo Voice Studio is opening. You can close this window.
start "" "%HOME_DIR%\venv\Scripts\pythonw.exe" "%APP_DIR%app\launcher.py"
timeout /t 3 >nul
exit /b 0

:fail
echo.
echo Setup did not finish: %MSG%
echo Check your internet connection, then open Voice Studio again to retry.
pause
exit /b 1
