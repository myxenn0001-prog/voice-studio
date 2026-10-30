#!/usr/bin/env bash
# Builds dist/VoiceStudio-macOS.dmg. Run on an Apple Silicon Mac:  bash packaging/macos/build_dmg.sh 1.0.0
# Optional signing and notarization (needs a paid Apple Developer account), via environment variables:
#   MACOS_SIGN_IDENTITY   e.g. "Developer ID Application: Your Company (TEAMID)"
#   APPLE_ID, APPLE_TEAM_ID, APPLE_APP_PASSWORD   for notarization
set -euo pipefail
VERSION="${1:-0.0.0}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
BUILD="$ROOT/build/macos"
APP="$BUILD/Voice Studio.app"
RES="$APP/Contents/Resources"
rm -rf "$BUILD"; mkdir -p "$APP/Contents/MacOS" "$RES/bin" "$ROOT/dist"

python3 "$ROOT/packaging/stage.py" "$RES/app" --version "$VERSION"
case "$(uname -m)" in arm64) TRIPLE=aarch64-apple-darwin ;; *) TRIPLE=x86_64-apple-darwin ;; esac
bash "$ROOT/packaging/fetch_uv.sh" "$TRIPLE" "$RES/bin"
cp "$ROOT/packaging/common/setup.sh" "$RES/setup.sh"; chmod +x "$RES/setup.sh"

cat > "$APP/Contents/MacOS/VoiceStudio" <<'EOS'
#!/bin/bash
# What the Voice Studio icon runs: sets the app up the first time (in a Terminal window so you can see progress), then opens it.
RES="$(cd "$(dirname "$0")/../Resources" && pwd)"
HOME_DIR="${VOICESTUDIO_HOME:-$HOME/Library/Application Support/VoiceStudio}"
APPVER="$(cat "$RES/app/VERSION" 2>/dev/null)"
INSTVER="$(cat "$HOME_DIR/.installed" 2>/dev/null)"
if [ ! -x "$HOME_DIR/venv/bin/python" ] || [ "$APPVER" != "$INSTVER" ]; then
  osascript -e 'tell application "Terminal" to activate' \
            -e "tell application \"Terminal\" to do script \"bash '$RES/setup.sh'\""
  exit 0
fi
export VOICESTUDIO_DATA="$HOME_DIR/data" VOICESTUDIO_INSTALLED=1
exec "$HOME_DIR/venv/bin/python" "$RES/app/launcher.py"
EOS
chmod +x "$APP/Contents/MacOS/VoiceStudio"

cat > "$APP/Contents/Info.plist" <<EOS
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
<key>CFBundleName</key><string>Voice Studio</string>
<key>CFBundleDisplayName</key><string>Voice Studio</string>
<key>CFBundleExecutable</key><string>VoiceStudio</string>
<key>CFBundleIdentifier</key><string>io.github.myxenn0001prog.voicestudio</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleShortVersionString</key><string>$VERSION</string>
<key>CFBundleVersion</key><string>$VERSION</string>
<key>CFBundleIconFile</key><string>icon</string>
<key>LSMinimumSystemVersion</key><string>12.0</string>
<key>NSHighResolutionCapable</key><true/>
</dict></plist>
EOS

# icon: build an .icns from the 1024px PNG
ICONSET="$BUILD/icon.iconset"; mkdir -p "$ICONSET"
for size in 16 32 128 256 512; do
  sips -z $size $size "$ROOT/assets/voice-studio.png" --out "$ICONSET/icon_${size}x${size}.png" >/dev/null
  sips -z $((size*2)) $((size*2)) "$ROOT/assets/voice-studio.png" --out "$ICONSET/icon_${size}x${size}@2x.png" >/dev/null
done
iconutil -c icns "$ICONSET" -o "$RES/icon.icns"

if [ -n "${MACOS_SIGN_IDENTITY:-}" ]; then
  codesign --force --deep --options runtime --sign "$MACOS_SIGN_IDENTITY" "$APP"
fi

DMGROOT="$BUILD/dmg"; mkdir -p "$DMGROOT"
cp -R "$APP" "$DMGROOT/"; ln -s /Applications "$DMGROOT/Applications"
cat > "$DMGROOT/READ ME FIRST.txt" <<'EOS'
1. Drag "Voice Studio" onto "Applications".
2. Open it from Applications. The first time, macOS may say it cannot verify the app:
   right-click (or Control-click) the app, choose Open, then press Open again.
3. A window shows the one-time setup (it downloads the voice software and takes several minutes).
   Voice Studio then opens by itself.
EOS
OUT="$ROOT/dist/VoiceStudio-macOS.dmg"; rm -f "$OUT"
hdiutil create -volname "Voice Studio" -srcfolder "$DMGROOT" -ov -format UDZO "$OUT"

if [ -n "${MACOS_SIGN_IDENTITY:-}" ] && [ -n "${APPLE_ID:-}" ]; then
  xcrun notarytool submit "$OUT" --apple-id "$APPLE_ID" --team-id "$APPLE_TEAM_ID" --password "$APPLE_APP_PASSWORD" --wait
  xcrun stapler staple "$OUT"
fi
echo "Built $OUT"
