#!/usr/bin/env python3
"""Build static pages into public/.

No dependencies. Pages in site-src/pages/ are copied to public/ with:
  {{> name}}             replaced by site-src/partials/name.html
  {{icon:name}}          replaced by the inline Lucide SVG from public/assets/icons/name.svg
                         (20px, 2px stroke at 20px, aria-hidden)
  {{current:key}}        replaced by aria-current="page" when the page's `current` matches key
  {{v}}                  replaced by a build stamp, used to cache-bust CSS/JS URLs
  {{prompt-index}}       the /how-this-was-built prompt list, from site-src/data/how-built.json (tools/prompt_index.py)
  {{prompt-scope}}       e.g. "12 prompts, 20th Sep"
  <x-*> components       case study building blocks, expanded first (see tools/components.py)
A page may start with a comment `<!-- current: work -->` to set its current nav item.

Usage: python3 tools/build.py
"""
import pathlib
import re
import time

import components
import prompt_index

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = ROOT / "site-src"
OUT = ROOT / "public"
ICONS = OUT / "assets" / "icons"
BUILD = str(int(time.time()))
SITE = "https://mrpatel.com"
OG_IMAGES = {  # page URL path -> share image
    "/": "/assets/img/work/teller.png",
    "/work/": "/assets/img/work/teller.png",
    "/work/teller/": "/assets/img/teller/hero.png",
    "/work/teller/summary/": "/assets/img/teller/hero.png",
    "/work/budgets/": "/assets/img/budgets/hero.png",
    "/work/budgets/summary/": "/assets/img/budgets/hero.png",
    "/work/tal/summary/": "/assets/img/work/tal-card.png",
    "/work/buildxact/summary/": "/assets/img/work/buildxact.png",
}


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
    if "{{prompt-index}}" in text:
        text = text.replace("{{prompt-index}}", prompt_index.render()).replace("{{prompt-scope}}", prompt_index.scope())
    text = re.sub(r"\{\{current:([\w-]+)\}\}",
                  lambda m: 'aria-current="page"' if m.group(1) == current else "", text)
    return text


def share_meta(html: str, url: str) -> str:
    """Add favicon, canonical and Open Graph/Twitter tags derived from the page's title and description."""
    title = re.search(r"<title>(.*?)</title>", html, re.S).group(1)
    desc = re.search(r'<meta name="description" content="([^"]*)"', html)
    tags = [
        '<link rel="icon" href="/favicon.svg" type="image/svg+xml">',
        f'<link rel="canonical" href="{SITE}{url}">',
        '<meta property="og:type" content="website">',
        '<meta property="og:site_name" content="MRPATEL">',
        f'<meta property="og:title" content="{title}">',
        f'<meta property="og:url" content="{SITE}{url}">',
        '<meta name="twitter:card" content="summary_large_image">',
    ]
    if desc:
        tags.append(f'<meta property="og:description" content="{desc.group(1)}">')
    if url in OG_IMAGES:
        tags.append(f'<meta property="og:image" content="{SITE}{OG_IMAGES[url]}">')
    return html.replace("</head>", "\n".join(tags) + "\n</head>", 1)


def main() -> None:
    urls = []
    for page in sorted((SRC / "pages").rglob("*.html")):
        raw = page.read_text()
        m = re.match(r"\s*<!--\s*current:\s*([\w-]+)\s*-->\s*", raw)
        current = m.group(1) if m else ""
        if m:
            raw = raw[m.end():]
        rel = page.relative_to(SRC / "pages")
        target = OUT / rel if rel.name == "index.html" else OUT / rel.with_suffix("") / "index.html"
        target.parent.mkdir(parents=True, exist_ok=True)
        url = "/" + ("" if rel.name == "index.html" and rel.parent == pathlib.Path(".") else str(rel.parent) + "/")
        if rel.name != "index.html":
            url = "/" + str(rel.with_suffix("")) + "/"
        built = share_meta(render(components.expand(raw), current), url)
        if not re.search(r'<meta name="robots" content="[^"]*noindex', built):  # noindex pages stay out of the sitemap
            urls.append(url)
        target.write_text(built)
        print(f"built {target.relative_to(ROOT)}")
    (OUT / "sitemap.xml").write_text(
        '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + "".join(f"  <url><loc>{SITE}{u}</loc></url>\n" for u in sorted(urls)) + "</urlset>\n")


if __name__ == "__main__":
    main()
