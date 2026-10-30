# Packaging

How Voice Studio reaches people who do not use a terminal.

| Folder / file | What it makes | Built on |
|---|---|---|
| `windows/` | `VoiceStudio-Setup.exe` (Inno Setup installer with desktop and Start menu icons) | Windows |
| `macos/` | `VoiceStudio-macOS.dmg` (drag-to-Applications app, Apple Silicon) | a Mac |
| `linux/` | `VoiceStudio-Linux.AppImage` (one file that runs on most x86_64 distributions) | Linux |
| `winget/`, `homebrew/` | Templates for `winget install` and `brew install --cask` | after a release exists |
| `../pinokio.js`, `install.js`, `start.js` | One-click install through Pinokio | n/a |

GitHub Actions builds all three installers automatically when you publish a release (`.github/workflows/release.yml`).

## How the installers work

Each installer is small. It contains only Voice Studio's own files and a tiny tool called
[uv](https://github.com/astral-sh/uv). The first time someone opens the app, `uv` downloads Python and the
voice libraries into a folder in their own user account (nothing needs administrator rights), then the app opens.
Later launches are instant.

Why not bundle everything with PyInstaller? PyTorch and the voice libraries are several gigabytes and are hard to
freeze reliably, and a bundled installer would redistribute other projects' packages, including some GPL ones.
Setting up on first launch keeps installers small and the licensing simple. The trade-off is that the first launch
needs internet and takes several minutes.

Where things end up on the user's computer:

| System | App files | Environment, models, voices and renders |
|---|---|---|
| Windows | `%LOCALAPPDATA%\Programs\Voice Studio` | `%LOCALAPPDATA%\VoiceStudio` |
| macOS | `/Applications/Voice Studio.app` | `~/Library/Application Support/VoiceStudio` |
| Linux | wherever the AppImage is | `~/.local/share/voice-studio` |

Uninstalling removes the program and its libraries but keeps the `data` folder (voices and renders) on purpose.

## Updating

Installing a newer version over the old one is enough: the app notices the version changed and refreshes its libraries on next launch.

## Test switches

`VOICESTUDIO_SETUP_LIGHT=1` skips the large voice libraries, and `VOICESTUDIO_SETUP_NOLAUNCH=1` skips opening the app.
The project's own checks use them to test the setup quickly.
