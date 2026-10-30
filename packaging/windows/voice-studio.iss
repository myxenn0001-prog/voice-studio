; Inno Setup script for the Voice Studio installer.
; Build with:  ISCC.exe /DAppVersion=1.0.0 packaging\windows\voice-studio.iss   (see build.ps1)
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
; Keep this GUID the same in every release so updates replace the old install.
AppId={{6F1D2C5E-3A47-4B8E-9C0A-5B7E2D41A9F3}
AppName=Voice Studio
AppVersion={#AppVersion}
AppPublisher=TechFlow
AppPublisherURL=https://myxenn0001-prog.github.io/voice-studio
AppSupportURL=https://github.com/myxenn0001-prog/voice-studio/issues
DefaultDirName={localappdata}\Programs\Voice Studio
DefaultGroupName=Voice Studio
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesInstallIn64BitMode=x64compatible
OutputDir=..\..\dist
OutputBaseFilename=VoiceStudio-Setup
SetupIconFile=..\..\build\windows\stage\app\assets\voice-studio.ico
UninstallDisplayIcon={app}\app\assets\voice-studio.ico
LicenseFile=..\..\TERMS_OF_USE.md
Compression=lzma2
SolidCompression=yes
WizardStyle=modern

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Icons:"

[Files]
Source: "..\..\build\windows\stage\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[Icons]
Name: "{autoprograms}\Voice Studio"; Filename: "{app}\launch.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\app\assets\voice-studio.ico"; Flags: runminimized
Name: "{autodesktop}\Voice Studio"; Filename: "{app}\launch.cmd"; WorkingDir: "{app}"; IconFilename: "{app}\app\assets\voice-studio.ico"; Flags: runminimized; Tasks: desktopicon

[Run]
Filename: "{app}\setup.cmd"; Description: "Download and set up the voice engine now (needs internet, takes several minutes)"; Flags: postinstall waituntilterminated skipifsilent

[UninstallDelete]
; Your voices and renders live in {localappdata}\VoiceStudio\data and are kept on purpose.
Type: filesandordirs; Name: "{localappdata}\VoiceStudio\venv"
Type: filesandordirs; Name: "{localappdata}\VoiceStudio\python"
Type: filesandordirs; Name: "{localappdata}\VoiceStudio\cache"
