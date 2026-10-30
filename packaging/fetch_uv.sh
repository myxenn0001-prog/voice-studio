#!/usr/bin/env bash
# Downloads the small `uv` tool that sets up Python and the libraries on first launch.
# Usage: fetch_uv.sh <target-triple> <destination-folder>
#   e.g. fetch_uv.sh aarch64-apple-darwin  build/bin      (Mac, Apple Silicon)
#        fetch_uv.sh x86_64-unknown-linux-gnu build/bin   (Linux)
set -euo pipefail
TRIPLE="$1"; DEST="$2"
mkdir -p "$DEST"
TMP="$(mktemp -d)"
curl -fsSL "https://github.com/astral-sh/uv/releases/latest/download/uv-${TRIPLE}.tar.gz" -o "$TMP/uv.tar.gz"
tar -xzf "$TMP/uv.tar.gz" -C "$TMP"
cp "$(find "$TMP" -type f -name uv | head -1)" "$DEST/uv"
chmod +x "$DEST/uv"
"$DEST/uv" --version
