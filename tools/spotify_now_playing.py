#!/usr/bin/env python3
"""Write public/spotify-test/now-playing.json from a Spotify get_currently_playing result.

Usage: python3 tools/spotify_now_playing.py < result.json   (use '{}' when nothing is playing)
Downloads the 300px cover into public/spotify-test/covers/ if it is not there yet.
"""
import json, re, sys, urllib.request
from pathlib import Path

out = Path(__file__).resolve().parent.parent / "public" / "spotify-test"
data = json.load(sys.stdin)
e = data.get("currently_playing_entity")
if not e:
    (out / "now-playing.json").write_text(json.dumps({"playing": False}))
    sys.exit(0)

covers = (e.get("display") or {}).get("covers") or []
url = next((c["url"] for c in covers if c.get("size") == "DEFAULT"), covers[0]["url"] if covers else "")
cover = ""
m = re.search(r"ab67616d[0-9a-f]{8}([0-9a-f]+)$", url)
if m:
    f = out / "covers" / f"{m.group(1)}.jpg"
    if not f.exists():
        urllib.request.urlretrieve(url, f)
    cover = f"covers/{f.name}"

parent = e.get("parent") or {}
(out / "now-playing.json").write_text(json.dumps({
    "playing": True,
    "id": parent.get("uri", e["uri"]).split(":")[-1],
    "track": e.get("name", ""),
    "artist": ", ".join(c["name"] for c in e.get("creators", [])),
    "album": parent.get("name", ""),
    "cover": cover,
}, ensure_ascii=False))
