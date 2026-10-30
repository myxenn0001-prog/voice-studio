"""Fills in your name and links everywhere in the project, in one go.

Run it ONCE on your copy of the project, before you publish:

    python tools/set_identity.py --company "Your Company" --repo your-github-name/voice-studio \\
        --email you@example.com --jurisdiction "England and Wales"

--jurisdiction is whose law governs the Terms of Use (for example "the State of Delaware, USA"). Ask your lawyer.
Optional: --site https://your-site.example   (defaults to your GitHub Pages address)
          --company-url https://your-company.example   (links your name in the app's footer)
          --year 2026   --effective-date "1 January 2027"   (defaults to today)
Then check nothing is left over:  python tools/set_identity.py --check
"""
import argparse
import datetime
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SELF = Path(__file__).resolve()
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", "build", "dist", "data", ".pytest_cache"}
BINARY = {".png", ".ico", ".icns", ".dmg", ".zip", ".wav", ".mp3", ".pyc", ".exe", ".appimage", ".jpg", ".jpeg", ".gif"}


def token(name: str) -> str:
    return "@@" + name + "@@"   # built here so this file never contains a literal placeholder


TOKEN_RE = re.compile(r"@@[A-Z_]+@@")


def files():
    for p in sorted(ROOT.rglob("*")):
        if p.is_file() and p.resolve() != SELF and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS) \
                and p.suffix.lower() not in BINARY:
            yield p


def leftovers():
    found = []
    for p in files():
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        hits = sorted(set(TOKEN_RE.findall(text)))
        if hits:
            found.append((p.relative_to(ROOT), hits))
    for p in sorted(ROOT.rglob("*")):  # file names too
        if TOKEN_RE.search(p.name) and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS):
            found.append((p.relative_to(ROOT), ["(in the file name)"]))
    return found


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--company", help="your company or your own name, as it should appear")
    ap.add_argument("--repo", help="GitHub address as owner/name, for example acme-labs/voice-studio")
    ap.add_argument("--email", help="contact address for security and abuse reports")
    ap.add_argument("--site", help="website address (default: your GitHub Pages address)")
    ap.add_argument("--company-url", help="link for your name in the app footer (default: the website)")
    ap.add_argument("--jurisdiction", help='whose law governs the Terms, for example "England and Wales"')
    ap.add_argument("--effective-date", help='date the Terms take effect, for example "1 January 2027" (default: today)')
    ap.add_argument("--year", default=str(datetime.date.today().year))
    ap.add_argument("--check", action="store_true", help="only list placeholders that are still unfilled")
    ap.add_argument("--dry-run", action="store_true", help="show what would change without changing anything")
    a = ap.parse_args()

    if a.check:
        left = leftovers()
        for path, hits in left:
            print(f"  {path}: {', '.join(hits)}")
        print("Nothing left to fill in." if not left else f"{len(left)} place(s) still have placeholders.")
        return 1 if left else 0

    problems = []
    if not a.company or not a.company.strip():
        problems.append("--company is required")
    if not a.repo or not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", a.repo):
        problems.append("--repo must look like owner/name, for example acme-labs/voice-studio")
    if not a.email or not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", a.email):
        problems.append("--email must be a real address")
    if not a.jurisdiction or not a.jurisdiction.strip():
        problems.append('--jurisdiction is required, for example --jurisdiction "England and Wales"')
    if a.site and not a.site.startswith("https://"):
        problems.append("--site must start with https://")
    if problems:
        print("Cannot continue:\n  - " + "\n  - ".join(problems), file=sys.stderr)
        return 2

    owner, name = a.repo.split("/")
    site = (a.site or f"https://{owner.lower()}.github.io/{name}").rstrip("/")
    company = a.company.strip()
    values = {
        "COMPANY": company,
        "COMPANY_ID": re.sub(r"[^A-Za-z0-9]", "", company) or "Publisher",
        "REPO": a.repo,
        "REPO_OWNER": owner,
        "SITE": site,
        "EMAIL": a.email,
        "YEAR": a.year,
        "JURISDICTION": a.jurisdiction.strip(),
        "EFFECTIVE_DATE": a.effective_date or f"{datetime.date.today().day} {datetime.date.today():%B %Y}",
        "BUNDLE_ID": "io.github." + re.sub(r"[^a-z0-9]", "", owner.lower()) + ".voicestudio",
    }

    changed = 0
    for p in files():
        try:
            text = p.read_text(encoding="utf-8")
        except (UnicodeDecodeError, OSError):
            continue
        new = text
        for key, val in values.items():
            new = new.replace(token(key), val)
        if new != text:
            changed += 1
            print(f"  fill in: {p.relative_to(ROOT)}")
            if not a.dry_run:
                p.write_text(new, encoding="utf-8")
    renamed = 0
    for p in sorted(ROOT.rglob("*"), key=lambda q: len(q.parts), reverse=True):
        if TOKEN_RE.search(p.name) and not (set(p.relative_to(ROOT).parts) & SKIP_DIRS):
            new_name = p.name
            for key, val in values.items():
                new_name = new_name.replace(token(key), val)
            renamed += 1
            print(f"  rename:  {p.relative_to(ROOT)} -> {new_name}")
            if not a.dry_run:
                p.rename(p.with_name(new_name))

    if not a.dry_run:
        (ROOT / "branding.json").write_text(json.dumps({
            "company": company, "company_url": (a.company_url or site), "repo": a.repo,
            "site": site, "support_email": a.email}, indent=2) + "\n", encoding="utf-8")
    print(f"\n{'Would change' if a.dry_run else 'Changed'} {changed} file(s) and rename {renamed}.")
    left = [] if a.dry_run else leftovers()
    if left:
        print("Still has placeholders (fill these by hand):")
        for path, hits in left:
            print(f"  {path}: {', '.join(hits)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
