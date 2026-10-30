"""Turns the legal documents (the .md files in the project root) into web pages, so they can be read inside the
app (offline) and on the website. Run it after editing any of them:

    python tools/build_legal.py            writes app/static/legal/*.html and docs/legal/*.html
    python tools/build_legal.py --check    fails if the pages are out of date

Needs: pip install markdown
"""
import html
import sys
from pathlib import Path

import markdown

ROOT = Path(__file__).resolve().parent.parent
PAGES = [  # slug, source file, title
    ("terms", "TERMS_OF_USE.md", "Terms of Use"),
    ("privacy", "PRIVACY.md", "Privacy Notice"),
    ("responsible-use", "RESPONSIBLE_USE.md", "Responsible use"),
    ("licenses", "THIRD_PARTY_LICENSES.md", "Third-party licenses"),
    ("trademarks", "TRADEMARKS.md", "Name and logo policy"),
    ("conduct", "CODE_OF_CONDUCT.md", "Code of Conduct"),
    ("license", "LICENSE", "Apache License 2.0"),
]
TARGETS = {  # folder, link style for sibling pages, link back to the product
    "app": (ROOT / "app" / "static" / "legal", "/legal/{slug}", "/"),
    "site": (ROOT / "docs" / "legal", "{slug}.html", "../"),
}
MD_LINKS = {"RESPONSIBLE_USE.md": "responsible-use", "TERMS_OF_USE.md": "terms", "PRIVACY.md": "privacy",
            "THIRD_PARTY_LICENSES.md": "licenses", "TRADEMARKS.md": "trademarks", "CODE_OF_CONDUCT.md": "conduct",
            "LICENSE": "license"}

CSS = """
:root{--bg:#ECEEF2;--panel:#fff;--ink:#1B2330;--muted:#4A5566;--line:#D3D9E1;--accent:#2447E8;
--ui:"Segoe UI Variable Text","Segoe UI",system-ui,-apple-system,"Helvetica Neue",Roboto,sans-serif;--page:"Iowan Old Style","Palatino Linotype",Palatino,Georgia,serif}
@media (prefers-color-scheme:dark){:root{--bg:#13171E;--panel:#1B212A;--ink:#E7EBF1;--muted:#A9B4C4;--line:#2D3541;--accent:#8499FF}}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.65 var(--ui)}
a{color:var(--accent)}header,footer,main{max-width:820px;margin:0 auto;padding:0 24px}
header{display:flex;flex-wrap:wrap;gap:8px 20px;align-items:center;padding-top:20px;padding-bottom:12px;border-bottom:1px solid var(--line)}
header .brand{font:600 20px/1 var(--page);color:inherit;text-decoration:none}header nav{display:flex;flex-wrap:wrap;gap:6px 16px;margin-left:auto;font-size:14px}
main{background:var(--panel);margin-top:24px;margin-bottom:24px;padding:12px 40px 36px;border:1px solid var(--line);border-radius:6px}
h1{font:600 32px/1.2 var(--page)}h2{font:600 21px/1.3 var(--page);margin-top:2em}h3{font-size:17px}
table{border-collapse:collapse;display:block;overflow-x:auto;width:100%}th,td{border:1px solid var(--line);padding:6px 10px;text-align:left;vertical-align:top}
pre{white-space:pre-wrap;font:13px/1.5 ui-monospace,Menlo,Consolas,monospace}code{font-size:.92em}
footer{color:var(--muted);font-size:13px;padding-bottom:36px}
@media (max-width:640px){main{padding:4px 18px 28px}}
"""


def render(slug, src, title, link_fmt, back):
    text = (ROOT / src).read_text(encoding="utf-8")
    if src == "LICENSE":
        body = f"<h1>{html.escape(title)}</h1><pre>{html.escape(text)}</pre>"
    else:
        body = markdown.markdown(text, extensions=["tables", "sane_lists"])
        for md, target in MD_LINKS.items():  # links between the documents become links between the pages
            body = body.replace(f'href="{md}"', f'href="{link_fmt.format(slug=target)}"')
    nav = " ".join(f'<a href="{link_fmt.format(slug=s)}">{html.escape(t)}</a>' for s, _, t in PAGES if s != slug)
    return f"""<!DOCTYPE html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>{html.escape(title)} - Voice Studio</title><style>{CSS}</style></head>
<body><header><a class="brand" href="{back}">Voice Studio</a><nav>{nav}</nav></header>
<main>
{body}
</main>
<footer>Voice Studio is free and open-source software, provided as is. This page is not legal advice.</footer></body></html>
"""


def main(check=False):
    stale = []
    for _, (folder, link_fmt, back) in TARGETS.items():
        folder.mkdir(parents=True, exist_ok=True)
        for slug, src, title in PAGES:
            out = folder / f"{slug}.html"
            new = render(slug, src, title, link_fmt, back)
            if check:
                if not out.exists() or out.read_text(encoding="utf-8") != new:
                    stale.append(str(out.relative_to(ROOT)))
            else:
                out.write_text(new, encoding="utf-8")
    if check:
        if stale:
            print("Out of date (run: python tools/build_legal.py):\n  " + "\n  ".join(stale))
            return 1
        print("Legal pages are up to date.")
        return 0
    print("Legal pages written to app/static/legal and docs/legal.")
    return 0


if __name__ == "__main__":
    sys.exit(main("--check" in sys.argv))
