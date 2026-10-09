#!/usr/bin/env python3
"""Turn the raw Claude Code prompt log into the data behind /how-this-was-built.

  python3 tools/prepare_prompts.py --day 2026-09-20      # first day only (current scope)
  python3 tools/prepare_prompts.py --from 2026-09-20 --to 2026-10-07   # a range

Reads   archive/how-this-was-built/prompts.json         raw log (never committed: archive/ is ignored)
        archive/how-this-was-built/redact.json          optional [[regex, replacement], ...] (also ignored,
                                                        so client names never reach the repo)
        archive/how-this-was-built/overrides.json       optional per-prompt edits, see below
Writes  site-src/data/how-built.json                    the reviewed, redacted data the build uses

Raw prompts come from archive/how-this-was-built/extract_prompts.py (run it from that folder).

Cleaning rules (the page only shows prompts a reader can understand on their own)
  - dropped: system-reminder noise, skill bodies, attachment-only prompts, terminal output (<bash-input>, <local-command...>),
    bare slash commands ("/design-sync"), prompts that lean on a screenshot sent with them ("what next" + image),
    and prompts under 4 words ("A", "yes go ahead")
  - "keep": true in overrides.json rescues a prompt the rules above would drop; "hide": true removes any prompt
  - "Continue from memory note" handoff prompts collapse into a group
  - times are shown in Australia/Sydney, 24 hour, e.g. "5th Oct" / "02.34"

overrides.json, keyed by the prompt's UTC timestamp (first 19 chars, e.g. "2026-09-20T07:18:09"):
  {"2026-09-20T07:18:09": {"image": "design-extractor", "text": "replacement text", "hide": true, "keep": true}}
  a top-level "milestones": [{"at": "2026-09-20T07:23:47", "label": "Short name shown on the timeline"}]
  and a top-level "images": {"design-extractor": {"label": "...", "alt": "...", "src": "/assets/img/how-built/x.png"}}
"""
import argparse
import json
import pathlib
import re
from datetime import datetime
from zoneinfo import ZoneInfo

ROOT = pathlib.Path(__file__).resolve().parent.parent
ARCH = ROOT / "archive" / "how-this-was-built"
OUT = ROOT / "site-src" / "data" / "how-built.json"
TZ = ZoneInfo("Australia/Sydney")

HANDOFF = re.compile(r"^\s*(Continue from memory note|/handoff)", re.I)
SKILL_BODY = re.compile(r"^\s*(Base directory for this skill|This session is being continued|<task-notification|<system-reminder)")
BIG_BODY = 5000  # pasted skill bodies and summaries run to tens of thousands of characters
PASTED = re.compile(r"</?pasted_content[^>]*>")
MAX_CHARS = 900
ATTACHMENT = re.compile(r"\[Image[^\]]*\]")
PRIVATE_URL = re.compile(r"@?https?://(?:[\w-]+\.)*(?:figma\.com|evernote\.com|claude\.ai|localhost|127\.0\.0\.1)\S*", re.I)
TERMINAL = re.compile(r"^\s*<(bash-input|bash-stdout|local-command|command-message|command-name)", re.I)
MIN_WORDS = 4
COMMAND = re.compile(r"<command-name>\s*(/[^<\s]+)\s*</command-name>")


def ordinal(n: int) -> str:
    if 10 <= n % 100 <= 20:
        return f"{n}th"
    return f"{n}{ {1: 'st', 2: 'nd', 3: 'rd'}.get(n % 10, 'th') }"


def when(ts: str):
    dt = datetime.fromisoformat(ts.replace("Z", "+00:00")).astimezone(TZ)
    return dt, f"{ordinal(dt.day)} {dt:%b}", f"{dt:%H.%M}"


def load(path, default):
    return json.loads(path.read_text()) if path.exists() else default


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--day")
    ap.add_argument("--from", dest="start")
    ap.add_argument("--to", dest="end")
    ap.add_argument("--out", default=str(OUT))
    a = ap.parse_args()
    start = a.day or a.start or "0000-00-00"
    end = a.day or a.end or "9999-99-99"

    raw = json.loads((ARCH / "prompts.json").read_text())
    redact = [(re.compile(p, re.I), r) for p, r in load(ARCH / "redact.json", [])]
    ov = load(ARCH / "overrides.json", {})
    images = ov.get("images", {})

    # a prompt sent with a screenshot in the same second leans on that screenshot
    with_image = {p["ts"][:19] for p in raw if ATTACHMENT.sub("", p["text"]).strip() == ""}

    items, dropped = [], {"noise": 0, "attachment": 0, "hidden": 0, "unclear": 0}
    for p in raw:
        dt, date, time = when(p["ts"])
        if not (start <= dt.strftime("%Y-%m-%d") <= end):
            continue
        key = p["ts"][:19]
        text = p["text"].strip()
        o = ov.get(key, {})
        if len(text) > BIG_BODY:
            dropped["noise"] += 1
            continue
        if COMMAND.search(text) or TERMINAL.match(text) or SKILL_BODY.match(text):
            dropped["noise"] += 1
            continue
        text = PRIVATE_URL.sub("[link]", PASTED.sub("", ATTACHMENT.sub("", text))).strip()
        if not text:
            dropped["attachment"] += 1
            continue
        if not o.get("keep") and (key in with_image or len(text.split()) < MIN_WORDS):
            dropped["unclear"] += 1
            continue
        if o.get("hide"):
            dropped["hidden"] += 1
            continue
        text = o.get("text", text)
        if len(text) > MAX_CHARS:  # long briefs: keep the opening, cut at a word boundary
            text = text[:MAX_CHARS].rsplit(None, 1)[0].rstrip(".,;:") + " …"
        for rx, rep in redact:
            text = rx.sub(rep, text)
        item = {"id": key, "iso": dt.isoformat(timespec="minutes"), "date": date, "time": time, "text": text}
        if HANDOFF.match(p["text"]):
            item["handoff"] = True
        if o.get("image"):
            item["image"] = o["image"]
        if o.get("response"):
            item["response"] = o["response"]
        items.append(item)

    # collapse runs of handoff prompts into one group
    out, run = [], []
    for it in items + [None]:
        if it and it.get("handoff"):
            run.append(it)
            continue
        if run:
            out.append({"group": run, "date": run[0]["date"], "time": run[0]["time"], "id": run[0]["id"]})
            run = []
        if it:
            resp = it.pop("response", None)
            out.append(it)
            if resp:
                out.append({"role": "claude", "id": it["id"] + "-r", "iso": it["iso"], "date": it["date"],
                            "time": it["time"], **resp})

    used = {i["image"] for i in items if i.get("image")}
    missing = used - set(images)
    ids = {i["id"] for i in items}
    marks = [m for m in ov.get("milestones", []) if m["at"] in ids]
    for m in ov.get("milestones", []):
        if m["at"] not in ids and start <= m["at"][:10] <= end:
            print("WARNING: milestone not in the shown prompts:", m)
    data = {"scope": a.day or f"{start} to {end}", "count": len(items),
            "images": {k: v for k, v in images.items() if k in used}, "milestones": marks, "items": out}
    pathlib.Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    pathlib.Path(a.out).write_text(json.dumps(data, indent=1, ensure_ascii=False) + "\n")
    print(f"{len(items)} prompts ({sum(1 for o in out if 'group' in o)} handoff groups) -> {a.out}; dropped {dropped}")
    if missing:
        print("WARNING: overrides reference unknown images:", sorted(missing))


if __name__ == "__main__":
    main()
