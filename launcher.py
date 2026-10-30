"""Starts Voice Studio and opens it in its own app window (no terminal, no address bar).
Closing the window stops the app. Uses only the standard library so it can run windowless."""
from __future__ import annotations

import os
import platform
import shutil
import socket
import subprocess
import sys
import time
import urllib.request
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DATA = Path(os.environ.get("VOICESTUDIO_DATA", ROOT / "data"))
DATA.mkdir(parents=True, exist_ok=True)
LOG = DATA / "server.log"
SYSTEM = platform.system()
PREFERRED_PORT = int(os.environ.get("VOICESTUDIO_PORT", "8000"))


def show_error(message: str) -> None:
    print(message, file=sys.stderr)
    try:
        if SYSTEM == "Windows":
            import ctypes

            ctypes.windll.user32.MessageBoxW(0, message, "Voice Studio", 0x10)
        elif SYSTEM == "Darwin":
            safe = message.replace('"', "'")
            subprocess.run(["osascript", "-e", f'display dialog "{safe}" with title "Voice Studio" buttons {{"OK"}}'])
        elif shutil.which("zenity"):
            subprocess.run(["zenity", "--error", "--title=Voice Studio", f"--text={message}"])
        elif shutil.which("notify-send"):
            subprocess.run(["notify-send", "Voice Studio", message])
    except Exception:
        pass


def is_ours(port: int) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/system", timeout=2) as r:
            return r.status == 200 and b"recommended_engine" in r.read()
    except Exception:
        return False


def port_free(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) != 0


def choose_port() -> tuple[int, bool]:
    """Returns (port, already_running)."""
    if is_ours(PREFERRED_PORT):
        return PREFERRED_PORT, True
    for port in range(PREFERRED_PORT, PREFERRED_PORT + 20):
        if port_free(port):
            return port, False
    raise RuntimeError("No free port was found. Close other programs and try again.")


def start_server(port: int) -> subprocess.Popen:
    env = dict(os.environ, VOICESTUDIO_PORT=str(port), VOICESTUDIO_OPEN_BROWSER="0",
               VOICESTUDIO_DATA=str(DATA), VOICESTUDIO_ALLOW_QUIT="1", PYTHONUNBUFFERED="1")
    py = Path(sys.executable)
    kwargs = {}
    if SYSTEM == "Windows":
        if py.name.lower() == "pythonw.exe" and py.with_name("python.exe").exists():
            py = py.with_name("python.exe")
        kwargs["creationflags"] = 0x08000000  # CREATE_NO_WINDOW
    log = open(LOG, "ab")
    return subprocess.Popen([str(py), str(ROOT / "run_server.py")], cwd=str(ROOT), env=env,
                            stdout=log, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL, **kwargs)


def wait_ready(port: int, proc: subprocess.Popen | None, timeout: float = 180) -> bool:
    end = time.time() + timeout
    while time.time() < end:
        if proc is not None and proc.poll() is not None:
            return False
        if is_ours(port):
            return True
        time.sleep(0.4)
    return False


def find_browser() -> str | None:
    override = os.environ.get("VOICESTUDIO_BROWSER")
    if override and Path(override).exists():
        return override
    candidates: list[str] = []
    if SYSTEM == "Windows":
        for base in filter(None, (os.environ.get("ProgramFiles(x86)"), os.environ.get("ProgramFiles"),
                                  os.environ.get("LOCALAPPDATA"))):
            candidates += [
                rf"{base}\Microsoft\Edge\Application\msedge.exe",
                rf"{base}\Google\Chrome\Application\chrome.exe",
                rf"{base}\BraveSoftware\Brave-Browser\Application\brave.exe",
            ]
    elif SYSTEM == "Darwin":
        candidates += [
            "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
            "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
            "/Applications/Brave Browser.app/Contents/MacOS/Brave Browser",
            "/Applications/Chromium.app/Contents/MacOS/Chromium",
        ]
    else:
        for name in ("google-chrome", "google-chrome-stable", "chromium", "chromium-browser",
                     "microsoft-edge", "microsoft-edge-stable", "brave-browser"):
            found = shutil.which(name)
            if found:
                candidates.append(found)
    return next((c for c in candidates if c and Path(c).exists()), None)


def open_window(url: str, browser: str) -> subprocess.Popen:
    profile = DATA / "browser-profile"  # its own profile, so this process lasts as long as the window
    return subprocess.Popen([browser, f"--app={url}", f"--user-data-dir={profile}", "--no-first-run",
                             "--no-default-browser-check", "--window-size=1280,880"])


def stop(proc: subprocess.Popen) -> None:
    proc.terminate()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()


def main() -> int:
    try:
        port, running = choose_port()
    except RuntimeError as exc:
        show_error(str(exc))
        return 1
    proc = None if running else start_server(port)
    if not wait_ready(port, proc):
        tail = ""
        try:
            tail = "\n".join(LOG.read_text(errors="replace").splitlines()[-6:])
        except Exception:
            pass
        if proc:
            stop(proc)
        show_error(f"Voice Studio could not start.\n\nDetails are saved in:\n{LOG}\n\n{tail}")
        return 1
    url = f"http://127.0.0.1:{port}"
    browser = find_browser()
    if browser is None:
        webbrowser.open(url)  # no Chrome/Edge/Brave: open the default browser; use Quit in the app to stop it
        return 0
    window = open_window(url, browser)
    if proc is None:      # the app was already running somewhere else: leave it running
        return 0
    window.wait()         # closing the window ends the app
    stop(proc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
