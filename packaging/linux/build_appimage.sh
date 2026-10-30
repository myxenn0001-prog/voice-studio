#!/usr/bin/env bash
# Builds dist/VoiceStudio-Linux.AppImage (x86_64). Run on Linux:  bash packaging/linux/build_appimage.sh 1.0.0
set -euo pipefail
VERSION="${1:-0.0.0}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUILD="$ROOT/build/linux"
APPDIR="$BUILD/VoiceStudio.AppDir"
SHARE="$APPDIR/usr/share/voice-studio"
rm -rf "$BUILD"; mkdir -p "$SHARE/bin" "$ROOT/dist"

python3 "$ROOT/packaging/stage.py" "$SHARE/app" --version "$VERSION"
bash "$ROOT/packaging/fetch_uv.sh" x86_64-unknown-linux-gnu "$SHARE/bin"
cp "$ROOT/packaging/common/setup.sh" "$SHARE/setup.sh"; chmod +x "$SHARE/setup.sh"
cp "$ROOT/packaging/linux/AppRun" "$APPDIR/AppRun"; chmod +x "$APPDIR/AppRun"
cp "$ROOT/assets/voice-studio.png" "$APPDIR/voice-studio.png"
cat > "$APPDIR/voice-studio.desktop" <<EOS
[Desktop Entry]
Type=Application
Name=Voice Studio
Comment=Free offline voiceovers and captions
Exec=AppRun
Icon=voice-studio
Terminal=false
Categories=AudioVideo;Audio;
EOS

curl -fsSL -o "$BUILD/appimagetool" "https://github.com/AppImage/appimagetool/releases/download/continuous/appimagetool-x86_64.AppImage"
chmod +x "$BUILD/appimagetool"
ARCH=x86_64 "$BUILD/appimagetool" --appimage-extract-and-run "$APPDIR" "$ROOT/dist/VoiceStudio-Linux.AppImage"
echo "Built $ROOT/dist/VoiceStudio-Linux.AppImage"
