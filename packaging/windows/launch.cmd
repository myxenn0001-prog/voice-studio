@echo off
rem What the Voice Studio desktop icon runs. Sets the app up if needed, then opens it.
setlocal EnableExtensions
set "APP_DIR=%~dp0"
if not defined VOICESTUDIO_HOME set "VOICESTUDIO_HOME=%LOCALAPPDATA%\VoiceStudio"
set "HOME_DIR=%VOICESTUDIO_HOME%"
set "APPVER=dev" & set "INSTVER="
if exist "%APP_DIR%app\VERSION" set /p APPVER=<"%APP_DIR%app\VERSION"
if exist "%HOME_DIR%\.installed" set /p INSTVER=<"%HOME_DIR%\.installed"
if not exist "%HOME_DIR%\venv\Scripts\pythonw.exe" goto setup
if not "%APPVER%"=="%INSTVER%" goto setup
set "VOICESTUDIO_DATA=%HOME_DIR%\data"
set "VOICESTUDIO_INSTALLED=1"
start "" "%HOME_DIR%\venv\Scripts\pythonw.exe" "%APP_DIR%app\launcher.py"
exit /b 0
:setup
call "%APP_DIR%setup.cmd"
exit /b 0
