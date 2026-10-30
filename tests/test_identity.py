import datetime
import json
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IGNORE = shutil.ignore_patterns(".git", "__pycache__", "data", "build", "dist", ".venv", ".pytest_cache")


def run(cwd, *args):
    return subprocess.run([sys.executable, "tools/set_identity.py", *args], cwd=cwd, capture_output=True, text=True)


def test_set_identity(tmp_path):
    repo = tmp_path / "copy"
    shutil.copytree(ROOT, repo, ignore=IGNORE)
    assert run(repo, "--check").returncode == 1                      # fresh project has placeholders

    bad = run(repo, "--company", "Acme Labs", "--repo", "not-a-repo", "--email", "nope")
    assert bad.returncode == 2 and "owner/name" in bad.stderr and "real address" in bad.stderr

    assert "jurisdiction" in bad.stderr
    ok = run(repo, "--company", "Acme Labs", "--repo", "Acme-Labs/voice-studio", "--email", "hello@acme.dev",
             "--jurisdiction", "England and Wales", "--effective-date", "1 January 2027")
    assert ok.returncode == 0, ok.stdout + ok.stderr
    assert run(repo, "--check").returncode == 0                       # nothing left over

    year = str(datetime.date.today().year)
    assert f"Copyright {year} Acme Labs" in (repo / "NOTICE").read_text()
    b = json.loads((repo / "branding.json").read_text())
    assert b["company"] == "Acme Labs" and b["repo"] == "Acme-Labs/voice-studio"
    assert b["site"] == "https://acme-labs.github.io/voice-studio" and b["support_email"] == "hello@acme.dev"
    assert (repo / "packaging/winget/AcmeLabs.VoiceStudio.installer.yaml").exists()
    assert not list((repo / "packaging/winget").glob("*@@*"))
    page = (repo / "docs/index.html").read_text()
    assert "github.com/Acme-Labs/voice-studio/releases/latest/download/VoiceStudio-Setup.exe" in page
    assert "Built by Acme Labs" in page
    assert "io.github.acmelabs.voicestudio" in (repo / "packaging/macos/build_dmg.sh").read_text()
    terms = (repo / "TERMS_OF_USE.md").read_text()
    assert "laws of England and Wales" in terms and "Effective 1 January 2027" in terms and "hello@acme.dev" in terms
    assert "England and Wales" in (repo / "app/static/legal/terms.html").read_text()    # the in-app page is filled in too
    assert "England and Wales" in (repo / "docs/legal/terms.html").read_text()          # and the website's
    assert (repo / "LICENSE").read_bytes() == (ROOT / "LICENSE").read_bytes()   # license text is never touched
