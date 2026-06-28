#!/usr/bin/env python3
"""
Convert resume Markdown files -> styled, print-ready HTML.
Open the .html in a browser and Ctrl+P -> "Save as PDF" (one click, ATS-clean).
No external dependencies.

Run:
    python make_html.py            # converts master.md + all of resume/tailored/
"""
import re
from pathlib import Path

ROOT = Path(__file__).parent
OUT = ROOT / "resume" / "html"
OUT.mkdir(parents=True, exist_ok=True)

CSS = """
<style>
  @page { margin: 14mm; }
  body { font-family: Georgia, 'Times New Roman', serif; color:#1a1a1a;
         max-width: 820px; margin: 24px auto; line-height: 1.4; font-size: 11pt; }
  h1 { font-size: 20pt; margin: 0 0 2px; }
  h2 { font-size: 12.5pt; border-bottom: 1.5px solid #333; padding-bottom: 2px;
       margin: 16px 0 6px; text-transform: uppercase; letter-spacing: .5px; }
  h3 { font-size: 11.5pt; margin: 10px 0 2px; }
  p { margin: 4px 0; }
  ul { margin: 4px 0 8px; padding-left: 18px; }
  li { margin: 2px 0; }
  blockquote { color:#555; font-style: italic; border-left: 3px solid #bbb;
               margin: 6px 0; padding: 2px 10px; font-size: 10pt; }
  hr { display:none; }
  a { color:#1a1a1a; text-decoration: none; }
  strong { color:#000; }
</style>
"""


def md_to_html(md):
    out, in_ul = [], False
    for line in md.splitlines():
        s = line.rstrip()
        # inline: bold, links
        def inline(t):
            t = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", t)
            t = re.sub(r"\*(.+?)\*", r"<em>\1</em>", t)
            t = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', t)
            return t
        if not s.strip() or s.strip() == "---":
            if in_ul: out.append("</ul>"); in_ul = False
            continue
        if s.startswith("### "): h = f"<h3>{inline(s[4:])}</h3>"
        elif s.startswith("## "): h = f"<h2>{inline(s[3:])}</h2>"
        elif s.startswith("# "): h = f"<h1>{inline(s[2:])}</h1>"
        elif s.startswith("> "): h = f"<blockquote>{inline(s[2:])}</blockquote>"
        elif s.lstrip().startswith(("- ", "* ")):
            if not in_ul: out.append("<ul>"); in_ul = True
            out.append(f"<li>{inline(s.lstrip()[2:])}</li>"); continue
        elif s.startswith("<!--"): continue
        else: h = f"<p>{inline(s)}</p>"
        if in_ul: out.append("</ul>"); in_ul = False
        out.append(h)
    if in_ul: out.append("</ul>")
    return "\n".join(out)


def convert(md_path):
    html = (f"<!doctype html><html><head><meta charset='utf-8'>{CSS}</head>"
            f"<body>{md_to_html(md_path.read_text(encoding='utf-8'))}</body></html>")
    dest = OUT / (md_path.stem + ".html")
    dest.write_text(html, encoding="utf-8")
    return dest


def main():
    files = [ROOT / "resume" / "master.md"] + sorted((ROOT / "resume" / "tailored").glob("*.md"))
    for f in files:
        if f.exists():
            print("->", convert(f))
    print(f"\nDone. Open any file in {OUT} and press Ctrl+P -> Save as PDF.")


if __name__ == "__main__":
    main()
