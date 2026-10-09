"""Render the /how-this-was-built prompt index from site-src/data/how-built.json.

Used by build.py for the {{prompt-index}} and {{prompt-scope}} markers. Data comes from
tools/prepare_prompts.py. Rows are plain text (escaped): prompts are never links.

Markup contract with public/assets/js/prompt-index.js and the .hb block in site.css:
  .hb[data-hb]            track; its height gives the scroll distance (--hb-n rows)
    .hb__stage            sticky on wide screens
      .hb__viewport > ol.hb__list > li.hb__item[data-n][data-image]
      .hb__aside          sticky image panel + caption (aria-hidden: the same images sit inline in the list)
      .hb__rail (drag track), .hb__legend (pill key for Claude rows), .hb__marks (milestone buttons, scroll to a prompt), .hb__cue, .hb__hint
Below 700px, and without JS, the stage is a plain list with each image inline.
"""
import html
import json
import pathlib
import re

DATA = pathlib.Path(__file__).resolve().parent.parent / "site-src" / "data" / "how-built.json"
ARROW_UP = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 19V5M5 12l7-7 7 7"/></svg>'
ARROW_DOWN = '<svg class="icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.4" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false"><path d="M12 5v14M19 12l-7 7-7-7"/></svg>'


def esc(s: str) -> str:
    return html.escape(s, quote=True)


def short_date(d: str) -> str:
    return re.sub(r"(\d+)(st|nd|rd|th)", r"\1", d)


def load() -> dict:
    return json.loads(DATA.read_text())


def scope() -> str:
    d = load()
    first, last = short_date(d["items"][0]["date"]), short_date(d["items"][-1]["date"])
    span = first if first == last else f"{first} to {last}"
    return f"{d['count']:,} prompts, {span}"


SOON = "Images coming soon"


def image_figure(key: str, img: dict) -> str:
    inner = f'<img src="{esc(img["src"])}" alt="{esc(img["alt"])}" loading="lazy">' if img.get("src") else \
        f'<div class="hb__ph placeholder-mark" role="img" aria-label="{esc(img["alt"])}"><span>{esc(img["label"])}</span></div>'
    return f'<figure class="hb__inline">{inner}<figcaption class="t-caption">{esc(img["label"])}</figcaption></figure>'


def render() -> str:
    d = load()
    images = d.get("images", {})
    rows, n = [], 0
    soon_ids = {m["at"] for m in d.get("milestones", [])}  # milestone prompts get a text note until their image exists
    soon = []
    for i, it in enumerate(d["items"]):
        when = f'<p class="hb__when t-caption"><time datetime="{esc(it.get("iso", it["id"]))}">{esc(it["date"])} {esc(it["time"])}</time></p>'
        if "group" in it:
            n += len(it["group"])
            members = "".join(f'<li>{esc(g["text"])}</li>' for g in it["group"])
            body = (f'<details class="hb__group"><summary class="t-caption">{len(it["group"])} handoff prompts '
                    f'(“Continue from memory note…”)</summary><ol>{members}</ol></details>')
            rows.append(f'<li class="hb__item hb__item--group" data-n="{n}">{when}<div class="hb__body">{body}</div></li>')
            continue
        claude = it.get("role") == "claude"
        if not claude:
            n += 1
        key = it.get("image")
        if not key and it["id"] in soon_ids and not claude:
            key = f'soon-{it["id"]}'
            soon.append(key)
            fig = f'<p class="hb__soon t-caption">{SOON}</p>'
        attrs = f' data-image="{esc(key)}"' if key else ""
        fig = image_figure(key, images[key]) if key in images else (fig if key in soon else "")
        nxt = d["items"][i + 1] if i + 1 < len(d["items"]) else {}
        cls = "hb__item hb__item--claude" if claude else ("hb__item hb__item--asked" if nxt.get("role") == "claude" else "hb__item")
        rows.append(f'<li class="{cls}" data-n="{n}"{attrs}>{when}<div class="hb__body"><p class="hb__text">{esc(it["text"])}</p>{fig}</div></li>')

    shots = "".join(
        f'<div class="hb__shot" data-image="{esc(k)}">'
        + (f'<img src="{esc(v["src"])}" alt="">' if v.get("src") else f'<div class="hb__ph placeholder-mark"><span>{esc(v["label"])}</span></div>')
        + f'<span class="hb__label" hidden>{esc(v["label"])}</span></div>'
        for k, v in images.items())
    shots += "".join(f'<div class="hb__shot hb__shot--soon" data-image="{k}"><p class="hb__soon t-caption">{SOON}</p><span class="hb__label" hidden></span></div>' for k in soon)
    first, last = short_date(d["items"][0]["date"]), short_date(d["items"][-1]["date"])
    ids = [it["id"] for it in d["items"]]
    span = max(len(ids) - 1, 1)
    marks = "".join(
        f'<li><button type="button" class="hb__mark{" hb__mark--accent" if m.get("accent") else ""}" data-index="{ids.index(m["at"])}" style="--at:{ids.index(m["at"]) / span:.4f}"><span class="hb__mark-label t-caption">{esc(m["label"])}</span></button></li>'
        for m in d.get("milestones", []) if m["at"] in ids)
    milestones = f'<nav class="hb__marks" aria-label="Milestones"><ol>{marks}</ol></nav>' if marks else ""
    return f'''<section class="hb" data-hb data-total="{d["count"]}" style="--hb-n:{len(d["items"])}" aria-label="Prompts, in order">
  <div class="hb__stage">
    <div class="hb__viewport"><ol class="hb__list">{"".join(rows)}</ol></div>
    <div class="hb__aside" aria-hidden="true">
      <div class="hb__panel">{shots}</div>
      <p class="hb__caption t-caption"><span class="hb__caption-label"></span><span class="hb__caption-count"></span></p>
    </div>
    <div class="hb__rail" aria-hidden="true"><span class="hb__rail-date hb__rail-date--start t-caption">{esc(first)}</span><span class="hb__rail-line"><span class="hb__thumb"></span></span><span class="hb__rail-date hb__rail-date--end t-caption">{esc(last)}</span></div>
    {milestones}
    <p class="hb__cue hb__cue--older t-caption" aria-hidden="true">{ARROW_UP}Older prompts</p>
    <p class="hb__legend t-caption" aria-hidden="true"><span class="hb__pill"></span>Claude</p>
    <p class="hb__cue hb__cue--newer t-caption" aria-hidden="true">{ARROW_DOWN}Newer prompts</p>
    <p class="hb__hint t-caption" aria-hidden="true"><span class="hb__mouse"></span>Scroll to step through the prompts</p>
  </div>
</section>'''
