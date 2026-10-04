#!/usr/bin/env python3
"""Build static pages into public/.

No dependencies. Pages in site-src/pages/ are copied to public/ with:
  {{> name}}             replaced by site-src/partials/name.html
  {{icon:name}}          replaced by the inline Lucide SVG from public/assets/icons/name.svg
                         (20px, 2px stroke at 20px, aria-hidden)
  {{current:key}}        replaced by aria-current="page" when the page's `current` matches key
  {{v}}                  replaced by a build stamp, used to cache-bust CSS/JS URLs
  <x-*> components       case study building blocks, expanded first (see tools/components.py)
A page may start with a comment `<!-- current: work -->` to set its current nav item.

Usage: python3 tools/build.py
"""
import pathlib
import re
import time

import components

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "site-src"
OUT = ROOT / "public"
ICONS = OUT / "assets" / "icons"
BUILD = str(int(time.time()))


def icon(name: str) -> str:
    svg = (ICONS / f"{name}.svg").read_text()
    inner = re.search(r"<svg[^>]*>(.*)</svg>", svg, re.S).group(1)
    inner = re.sub(r"\s+", " ", inner).strip()
    return (
        '<svg class="icon" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" '
        'fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" '
        f'stroke-linejoin="round" aria-hidden="true" focusable="false">{inner}</svg>'
    )


def render(text: str, current: str) -> str:
    for _ in range(3):  # partials may contain partials
        text = re.sub(r"\{\{>\s*([\w-]+)\s*\}\}",
                      lambda m: (SRC / "partials" / f"{m.group(1)}.html").read_text().rstrip("\n"), text)
    text = re.sub(r"\{\{icon:([\w-]+)\}\}", lambda m: icon(m.group(1)), text)
    text = text.replace("{{v}}", BUILD)
    text = re.sub(r"\{\{current:([\w-]+)\}\}",
                  lambda m: 'aria-current="page"' if m.group(1) == current else "", text)
    return text


def main() -> None:
    for page in sorted((SRC / "pages").rglob("*.html")):
        raw = page.read_text()
        m = re.match(r"\s*<!--\s*current:\s*([\w-]+)\s*-->\s*", raw)
        current = m.group(1) if m else ""
        if m:
            raw = raw[m.end():]
        rel = page.relative_to(SRC / "pages")
        target = OUT / rel if rel.name == "index.html" else OUT / rel.with_suffix("") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(render(components.expand(raw), current))
        print(f"built {target.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
