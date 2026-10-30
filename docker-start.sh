#!/usr/bin/env bash
# Linux / macOS: start Voice Studio in Docker and open the browser.
set -e
cd "$(dirname "$0")"
FILES="-f docker-compose.yml"
if command -v nvidia-smi >/dev/null 2>&1 && [ "$(uname)" = "Linux" ]; then
  FILES="$FILES -f docker-compose.gpu.yml"; echo "NVIDIA GPU found, using it."
fi
docker compose $FILES up -d --build
echo "Voice Studio is starting at http://localhost:8000 (the first start downloads models once)."
sleep 3
(xdg-open http://localhost:8000 || open http://localhost:8000) >/dev/null 2>&1 || true
