# winget (Windows Package Manager)

Lets people install with `winget install TechFlow.VoiceStudio`.

Easiest route: after you publish a release, use Microsoft's `wingetcreate` tool, which fills in the hashes for you:

```powershell
winget install wingetcreate
wingetcreate new https://github.com/myxenn0001-prog/voice-studio/releases/download/v1.0.0/VoiceStudio-Setup.exe
```

It asks a few questions, then offers to open the pull request to the community repository. For each later release:

```powershell
wingetcreate update TechFlow.VoiceStudio --version 1.0.1 --urls https://github.com/myxenn0001-prog/voice-studio/releases/download/v1.0.1/VoiceStudio-Setup.exe --submit
```

The three files here show what a manifest looks like. winget needs a **versioned** download link, which is why
the release workflow keeps the same file names under each tag.
