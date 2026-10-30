"""Create desktop / start-menu shortcuts that start Voice Studio in its own window
(no terminal, no browser tab). Works on Windows, macOS and Linux."""
from __future__ import annotations

import os
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ASSETS = ROOT / "assets"
LAUNCHER = ROOT / "launcher.py"
NAME = "Voice Studio"


def _python(windowless: bool = False) -> Path:
    exe = Path(sys.executable)
    if windowless and platform.system() == "Windows":
        pyw = exe.with_name("pythonw.exe")
        if pyw.exists():
            return pyw
    return exe


def _ps(value: object) -> str:
    return str(value).replace("'", "''")


def _windows() -> list[str]:
    script = f"""
$ErrorActionPreference = 'Stop'
$ws = New-Object -ComObject WScript.Shell
$dirs = @([Environment]::GetFolderPath('Desktop'), (Join-Path $env:APPDATA 'Microsoft\\Windows\\Start Menu\\Programs'))
foreach ($d in $dirs) {{
  $path = Join-Path $d '{NAME}.lnk'
  $l = $ws.CreateShortcut($path)
  $l.TargetPath = '{_ps(_python(True))}'
  $l.Arguments = '"{_ps(LAUNCHER)}"'
  $l.WorkingDirectory = '{_ps(ROOT)}'
  $l.IconLocation = '{_ps(ASSETS / "voice-studio.ico")}'
  $l.Description = 'Offline voiceovers on your own computer'
  $l.Save()
  Write-Output $path
}}
"""
    done = subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
                          capture_output=True, text=True)
    if done.returncode != 0:
        raise RuntimeError(done.stderr.strip() or "PowerShell could not create the shortcut.")
    return [line.strip() for line in done.stdout.splitlines() if line.strip()]


def _linux_desktop_dir() -> Path:
    try:
        out = subprocess.run(["xdg-user-dir", "DESKTOP"], capture_output=True, text=True, timeout=5).stdout.strip()
        if out and Path(out).is_dir():
            return Path(out)
    except Exception:
        pass
    return Path.home() / "Desktop"


def _linux() -> list[str]:
    entry = (
        "[Desktop Entry]\nType=Application\n"
        f"Name={NAME}\nComment=Offline voiceovers on your own computer\n"
        f'Exec="{_python()}" "{LAUNCHER}"\nPath={ROOT}\n'
        f"Icon={ASSETS / 'voice-studio.png'}\nTerminal=false\nCategories=AudioVideo;Audio;\n"
    )
    made = []
    menu = Path.home() / ".local" / "share" / "applications"
    targets = [menu]
    desktop = _linux_desktop_dir()
    if desktop.is_dir():
        targets.append(desktop)
    for folder in targets:
        folder.mkdir(parents=True, exist_ok=True)
        f = folder / "voice-studio.desktop"
        f.write_text(entry, encoding="utf-8")
        f.chmod(0o755)
        if folder == desktop and shutil.which("gio"):  # GNOME: mark the launcher as trusted
            subprocess.run(["gio", "set", str(f), "metadata::trusted", "true"], capture_output=True)
        made.append(str(f))
    return made


def _icns(png: Path, out: Path) -> bool:
    if not (shutil.which("iconutil") and shutil.which("sips")):
        return False
    try:
        with tempfile.TemporaryDirectory() as tmp:
            iconset = Path(tmp) / "icon.iconset"
            iconset.mkdir()
            for size in (16, 32, 128, 256, 512):
                for scale in (1, 2):
                    px = size * scale
                    name = f"icon_{size}x{size}{'@2x' if scale == 2 else ''}.png"
                    subprocess.run(["sips", "-z", str(px), str(px), str(png), "--out", str(iconset / name)],
                                   check=True, capture_output=True)
            subprocess.run(["iconutil", "-c", "icns", str(iconset), "-o", str(out)], check=True, capture_output=True)
        return True
    except Exception:
        return False


def _mac() -> list[str]:
    app = Path.home() / "Applications" / f"{NAME}.app"
    shutil.rmtree(app, ignore_errors=True)
    (app / "Contents" / "MacOS").mkdir(parents=True)
    (app / "Contents" / "Resources").mkdir(parents=True)
    exe = app / "Contents" / "MacOS" / "VoiceStudio"
    exe.write_text(f'#!/bin/bash\ncd "{ROOT}"\nexec "{_python()}" "{LAUNCHER}"\n')
    exe.chmod(0o755)
    has_icon = _icns(ASSETS / "voice-studio.png", app / "Contents" / "Resources" / "icon.icns")
    (app / "Contents" / "Info.plist").write_text(f"""<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>{NAME}</string>
<key>CFBundleDisplayName</key><string>{NAME}</string>
<key>CFBundleExecutable</key><string>VoiceStudio</string>
<key>CFBundleIdentifier</key><string>com.voicestudio.app</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleVersion</key><string>1.0</string>
{'<key>CFBundleIconFile</key><string>icon</string>' if has_icon else ''}
</dict></plist>
""")
    made = [str(app)]
    desktop = Path.home() / "Desktop"
    if desktop.is_dir():
        dest = desktop / f"{NAME}.app"
        shutil.rmtree(dest, ignore_errors=True)
        shutil.copytree(app, dest, symlinks=True)
        made.append(str(dest))
    return made


def create() -> dict:
    system = platform.system()
    if not LAUNCHER.exists():
        raise RuntimeError("launcher.py was not found next to the app.")
    if system == "Windows":
        made = _windows()
    elif system == "Darwin":
        made = _mac()
    elif system == "Linux":
        made = _linux()
    else:
        raise RuntimeError(f"Shortcuts are not supported on {system}.")
    return {"platform": system, "created": made}
