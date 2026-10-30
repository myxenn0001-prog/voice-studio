"""Copies the files an installed copy of Voice Studio needs into a folder.
Usage: python packaging/stage.py DEST [--version 1.2.3]"""
import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
INCLUDE_DIRS = ["app", "assets"]
INCLUDE_FILES = ["launcher.py", "run_server.py", "requirements.txt", "VERSION", "branding.json",
                 "LICENSE", "NOTICE", "THIRD_PARTY_LICENSES.md", "RESPONSIBLE_USE.md", "TERMS_OF_USE.md", "PRIVACY.md",
                 "TRADEMARKS.md"]


def stage(dest: Path, version: str | None = None) -> None:
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True)
    for name in INCLUDE_DIRS:
        shutil.copytree(ROOT / name, dest / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    for name in INCLUDE_FILES:
        shutil.copy2(ROOT / name, dest / name)
    if version:
        (dest / "VERSION").write_text(version.strip() + "\n")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("dest")
    p.add_argument("--version")
    a = p.parse_args()
    stage(Path(a.dest), a.version)
    print(f"Staged Voice Studio into {a.dest}", file=sys.stderr)
