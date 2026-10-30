# Builds dist\VoiceStudio-Setup.exe on Windows.  Usage:  powershell -File packaging\windows\build.ps1 -Version 1.0.0
# Needs Python 3 and Inno Setup 6 (choco install innosetup).
param([string]$Version = "0.0.0")
$ErrorActionPreference = "Stop"
$root = Resolve-Path (Join-Path $PSScriptRoot "..\..")
$stage = Join-Path $root "build\windows\stage"
if (Test-Path (Join-Path $root "build\windows")) { Remove-Item -Recurse -Force (Join-Path $root "build\windows") }
New-Item -ItemType Directory -Force (Join-Path $stage "bin") | Out-Null

python (Join-Path $root "packaging\stage.py") (Join-Path $stage "app") --version $Version

$zip = Join-Path $root "build\windows\uv.zip"
Invoke-WebRequest "https://github.com/astral-sh/uv/releases/latest/download/uv-x86_64-pc-windows-msvc.zip" -OutFile $zip
Expand-Archive $zip -DestinationPath (Join-Path $root "build\windows\uv") -Force
$uv = Get-ChildItem -Recurse (Join-Path $root "build\windows\uv") -Filter uv.exe | Select-Object -First 1
Copy-Item $uv.FullName (Join-Path $stage "bin\uv.exe")

Copy-Item (Join-Path $PSScriptRoot "setup.cmd") $stage
Copy-Item (Join-Path $PSScriptRoot "launch.cmd") $stage

$iscc = @("$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe", "$env:ProgramFiles\Inno Setup 6\ISCC.exe") | Where-Object { Test-Path $_ } | Select-Object -First 1
if (-not $iscc) { throw "Inno Setup 6 was not found. Install it with: choco install innosetup" }
& $iscc "/DAppVersion=$Version" (Join-Path $PSScriptRoot "voice-studio.iss")
if ($LASTEXITCODE -ne 0) { throw "Inno Setup failed" }
Write-Host "Built dist\VoiceStudio-Setup.exe"
