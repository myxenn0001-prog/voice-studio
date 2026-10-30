"""Entry point used by the launchers and the Docker image."""
import os
import threading
import webbrowser

import uvicorn

HOST = os.environ.get("VOICESTUDIO_HOST", "127.0.0.1")
PORT = int(os.environ.get("VOICESTUDIO_PORT", "8000"))

if __name__ == "__main__":
    if os.environ.get("VOICESTUDIO_OPEN_BROWSER", "1") == "1":
        threading.Timer(1.5, lambda: webbrowser.open(f"http://localhost:{PORT}")).start()
    uvicorn.run("app.main:app", host=HOST, port=PORT, log_level="info")
