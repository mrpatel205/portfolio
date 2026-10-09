#!/usr/bin/env python3
"""Build the Approach <x-story> illustrations from Figma hero exports.

Sources: tools/approach-src/{teller,budgets,tal,bx}.svg (Figma SVG export of each hero on page
2320:16027 of file v2, layer names kept as ids, notes stripped). Each element is assigned a stage and
a unit; a unit becomes one <g class="story__fade|story__grow" data-stage style="--i">. Motion follows
the Teller story rule (fade, or scaleY grow from centre); see feedback_motion_rule.
Run: python3 tools/approach_svgs.py   ->  site-src/illustrations/<name>-approach.svg
"""
import html, re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC, OUT = ROOT / "tools" / "approach-src", ROOT / "site-src" / "illustrations"


def dec(s):
    s = html.unescape(s)
    for enc in ("latin1", "cp1252"):
        try:
            return s.encode(enc).decode("utf8")
        except Exception:
            pass
    return s


def rnd(m):
    v = round(float(m.group()), 1)
    return str(int(v)) if v == int(v) else str(v)


def elements(svg):
    out = []
    for m in re.finditer(r"<(circle|path|rect|text)\b([^>]*?)(?:/>|>(.*?)</text>)", svg, re.S):
        tag, attrs, inner = m.group(1), m.group(2), m.group(3)
        if tag == "rect" and ' id="' not in attrs:
            continue  # background
        i = re.search(r' id="([^"]*)"', attrs)
        ident = dec(i.group(1)) if i else ""
        out.append(dict(tag=tag, id=ident, base=re.sub(r"_\d+$", "", ident), attrs=attrs, inner=inner, bb=bbox(tag, attrs, inner)))
    return out


def bbox(tag, a, inner):
    g = lambda k: float(re.search(rf' {k}="([-\d.]+)"', a).group(1))
    if tag == "circle":
        return g("cx") - g("r"), g("cy") - g("r"), g("cx") + g("r"), g("cy") + g("r")
    if tag == "rect":
        return g("x"), g("y"), g("x") + g("width"), g("y") + g("height")
    if tag == "text":
        xs = [float(x) for x in re.findall(r'x="([-\d.]+)"', inner)]
        ys = [float(y) for y in re.findall(r'y="([-\d.]+)"', inner)]
        return min(xs), min(ys) - 22, max(xs) + 120, max(ys) + 8
    d = re.search(r' d="([^"]*)"', a).group(1)
    xs, ys, x, y = [], [], 0.0, 0.0
    for c, args in re.findall(r"([MLHVCZ])([^MLHVCZ]*)", d):
        n = [float(v) for v in re.findall(r"-?\d*\.?\d+", args)]
        if c == "H":
            x = n[-1]
        elif c == "V":
            y = n[-1]
        elif n:
            x, y = n[-2], n[-1]
            xs += n[0::2]; ys += n[1::2]
            continue
        xs.append(x); ys.append(y)
    return min(xs), min(ys), max(xs), max(ys)


def render(e):
    a = re.sub(r' (id|style|xml:space)="[^"]*"', "", e["attrs"]).replace(' fill="none"', "")
    a = re.sub(r"-?\d+\.\d+", rnd, a)
    if e["tag"] == "text":
        inner = e["inner"].replace("&#x2028;", "")
        inner = re.sub(r"-?\d+\.\d+", rnd, inner)
        return f"<text{a.rstrip('/')}>{inner}</text>"
    if e["base"] == "height marker":
        a += ' transform="translate(16 0)"'  # clear of the Height label pill
    return f"<{e['tag']}{a.rstrip('/')}/>"


# Measured Inter Bold 24px advance widths (browser getBBox) for the one-line header labels
MEASURED = {"WITHDRAWAL": 170, "DEPOSIT": 104, "PAYMENT": 119, "RELEASE": 106}
PILL = ("WITHDRAWAL", "DEPOSIT", "PAYMENT", "RELEASE", "label — one column", "label — height")


def pill(e):
    """Muted grey (#595959, white text = 7:1) pill behind a Teller label so the eye links it to the underlined copy (white text)."""
    size = float(re.search(r'font-size="([\d.]+)"', e["attrs"]).group(1))
    bold = "font-weight" in e["attrs"]
    k = 0.71 if bold else 0.49  # avg glyph width / em, Inter caps bold vs regular mixed case
    ts = re.findall(r'<tspan x="([-\d.]+)" y="([-\d.]+)">([^<]*)</tspan>', e["inner"])
    x0 = min(float(x) for x, _, _ in ts)
    if e["base"] in MEASURED:  # centre text in its pill with text-anchor, from the measured width
        w = MEASURED[e["base"]] * size / 24
        x0 = float(ts[0][0])
        x1 = x0 + w
    else:
        x1 = max(float(x) + len(re.sub(r"&#x?\w+;", "", t).strip()) * size * k for x, _, t in ts)
    y0 = float(ts[0][1]) - size * 0.95
    y1 = float(ts[-1][1]) + size * 0.3
    px, py = size * 0.55, size * 0.35
    r = f'<rect x="{x0 - px:.1f}" y="{y0 - py:.1f}" width="{x1 - x0 + 2 * px:.1f}" height="{y1 - y0 + 2 * py:.1f}" rx="{(y1 - y0 + 2 * py) / 2 if len(ts) == 1 else 12:.1f}" fill="#595959"/>'
    t = render(e).replace('fill="#737373"', 'fill="#fff"').replace('fill="black"', 'fill="#fff"')
    return r + "\n      " + t


def stage_by_x(x, bounds):
    return 1 + sum(x >= b for b in bounds)


# rule(e, state) -> (stage, kind, unit) ; kind is 'fade' or 'grow'
def teller(e, st):
    b, who = e["base"], re.search(r"WITHDRAWAL|DEPOSIT|PAYMENT", e["base"])
    who = who.group() if who else None
    if b == "arrow":
        st["a"] = st.get("a", 0) + 1
        return 1, "fade", f"arr{st['a']}"
    if b in ("halo", "focus — release", "RELEASE"):
        return 1, "fade", "release"
    if b.startswith("circle —") or b in ("WITHDRAWAL", "DEPOSIT", "PAYMENT"):
        return 1, "fade", "c" + who
    stg = 2  # every column (withdrawals, deposits, payments) stacks in together
    if b.startswith("floor"):
        return stg, "fade", "floor" + who
    if b.startswith("dot"):
        return stg, "dot", e["id"]
    if b in ("label — one column", "pointer — one column"):
        return 2, "fade", "ann1"
    return 3, "fade", "ann2"


def budgets(e, st):
    b, (x0, _, x1, _) = e["base"], e["bb"]
    T = [600, 1230, 1860]
    m = re.match(r"0(\d)\s", e["attrs"] and (re.sub(r"<[^>]+>", "", e["inner"] or "") if e["tag"] == "text" else ""))
    if m:
        return int(m.group(1)), "fade", "title"
    if b == "arrow":
        return stage_by_x(x1 + 100, T), "fade", e["id"]
    cx = (x0 + x1) / 2
    s = stage_by_x(cx, T)
    unit = {"hub — Round 1": "hub1", "Define": "hub1", "hub — Round 2": "hub2", "Refine": "hub2",
            "band — settled slice": "band", "halo": "end", "focus — handoff to engineering": "end",
            "line": "oneway", "arrowhead": "oneway", "pill": "loop", "arrowhead — out (A → B)": "loop",
            "arrowhead — back (B → A)": "loop", "dot — BA": "ba", "BA": "ba", "dot — Accessibility": "acc",
            "Accessibility": "acc", "dot — Ash": "ash", "Design": "ash"}.get(b)
    if unit is None:
        unit = f"col{round(cx)}"
    return s, "fade", unit


def tal(e, st):
    b, (x0, _, x1, _) = e["base"], e["bb"]
    T = [640, 1260]
    t = re.sub(r"<[^>]+>", "", e["inner"] or "") if e["tag"] == "text" else ""
    m = re.match(r"0(\d)\s", t)
    if m:
        return int(m.group(1)), "fade", "title"
    if b.startswith("arrow"):
        return stage_by_x(x1 + 100, T), "fade", e["id"]
    if b == "scope — insurance landscape" or b == "open dot — unknown":
        return 1, "fade", "scope"
    if b == "dot — known":
        return 1, "fade", "known"
    if b.startswith("spoke"):
        return 2, "grow", e["id"]
    if b in ("link — TAL funnel", "dot — TAL step", "TAL"):
        return 2, "fade", "tal"
    if b in ("link — Suncorp funnel", "dot — Suncorp step", "Suncorp"):
        return 2, "fade", "sun"
    if b.startswith("dot — weekly") or b == "weekly showcases":
        return 3, "fade", "weekly"
    name = re.sub(r"^(hub outline|dot|focus|halo) — ", "", b)
    if b == "halo":
        name = "Eligibility"
    return 3, "fade", "hub" + name


def bx(e, st):
    b, (x0, _, x1, _) = e["base"], e["bb"]
    T = [700, 1340]
    t = re.sub(r"<[^>]+>", "", e["inner"] or "") if e["tag"] == "text" else ""
    m = re.match(r"0(\d)\s", t)
    if m:
        return int(m.group(1)), "fade", "title"
    if b == "arrow":
        return stage_by_x(x1 + 100, T), "fade", e["id"]
    if b in ("floor", "circle — scope", "Top tasks · audit"):
        return 1, "fade", "pile"
    if b == "ellipse":
        return 1, "fade", f"pile{round(((x0 + x1) / 2 - 185) / 90)}"
    if b == "leader — Strategy":
        n = re.search(r"_(\d)$", e["id"])
        return 2, "fade", "pl" + ["Strategy", "Scope", "Structure", "Skeleton"][int(n.group(1)) - 1 if n else 0]
    pl = re.match(r"(?:plane — )?(Strategy|Scope|Structure|Skeleton)$", b)
    if pl:
        return 2, "fade", "pl" + pl.group(1)
    if b in ("halo", "focus — vision", "Vision"):
        return 3, "fade", "vision"
    p = re.search(r"(Simplified|Personalised|Supported|Connected)", b)
    return 3, "fade", "pr" + p.group(1)


HEROES = {
    "teller": dict(rule=teller, over={}, title="Three design processes run one after another, ending in one release",
                   desc="Three large circles in a row, Withdrawal, Deposit and Payment, joined by arrows that lead to a single release point. Each column of dots inside a circle is one transaction type, and the column's height is the rigour of its design process."),
    "budgets": dict(rule=budgets, over={"hub1": 0, "hub2": 1}, title="Four stages from a framed problem to a handoff to engineering",
                    desc="A problem space with one dot, then two rounds of options narrowing to a settled slice, then the detailed stage where design, business analysis and accessibility work together, ending in a handoff."),
    "tal": dict(rule=tal, over={"weekly": 1e6, "tal": 779.5, "sun": 779.6}, title="From an open insurance landscape to five phases shipped in sprints",
                desc="A landscape of unknowns becoming known, the TAL and Suncorp funnels compared step by step, then five phases from Eligibility to Confirm and Pay with weekly showcases along the bottom."),
    "bx": dict(rule=bx, over={"plStrategy": 800, "plScope": 801, "plStructure": 802, "plSkeleton": 803,
                              "prSimplified": 2000, "prPersonalised": 2001, "prSupported": 2002, "prConnected": 2003},
               title="Evidence, five planes of design, and four principles around one vision",
               desc="A pile of evidence in a circle, then four stacked planes from Strategy to Skeleton, then a vision at the centre with four principles around it: Simplified, Personalised, Supported and Connected."),
}
NAMES = {"teller": "teller", "budgets": "budgets", "tal": "tal", "bx": "buildxact"}


def build(key):
    h = HEROES[key]
    els = elements((SRC / f"{key}.svg").read_text(encoding="utf8"))
    units, st = {}, {}
    for e in els:
        stage, kind, uid = h["rule"](e, st)
        u = units.setdefault((stage, uid), dict(kind=kind, els=[]))
        u["els"].append(e)
    # Dots drop in one by one, bottom of each column first, columns left to right (--d, ms)
    dots = [(uid, u["els"][0]["bb"]) for (_, uid), u in units.items() if u["kind"] == "dot"]
    cols = sorted({round(bb[0]) for _, bb in dots})
    dot_delay = {}
    for c in cols:
        for r, (uid, _) in enumerate(sorted((d for d in dots if round(d[1][0]) == c), key=lambda d: -d[1][3])):
            dot_delay[uid] = cols.index(c) * 60 + r * 30
    stages = sorted({s for s, _ in units})
    parts = []
    for s in stages:
        us = []
        for (stg, uid), u in units.items():
            if stg != s:
                continue
            solid = [e for e in u["els"] if e["tag"] != "text"] or u["els"]
            left = -1 if uid == "title" else h["over"].get(uid, min(e["bb"][0] for e in solid))
            us.append((left, u["kind"] != "fade", uid, u))
        us.sort(key=lambda t: t[:2])
        parts.append(f"    <!-- Stage {s} -->")
        for i, (_, _, uid, u) in enumerate(us):
            body = "\n".join("      " + (pill(e) if key == "teller" and e["base"] in PILL and e["tag"] == "text" else render(e)) for e in u["els"])
            style = f"--i:{i}"
            if u["kind"] == "dot":
                style = f"--i:{i};--d:{dot_delay[uid]}"
            parts.append(f'    <g class="story__{"fade" if u["kind"] == "dot" else u["kind"]}" data-stage="{s}" style="{style}">\n{body}\n    </g>')
    xs0 = min(e["bb"][0] for e in els); ys0 = min(e["bb"][1] for e in els)
    xs1 = max(e["bb"][2] for e in els); ys1 = max(e["bb"][3] for e in els)
    x, y, w, hh = round(xs0 - 40), round(ys0 - 40), round(xs1 - xs0 + 80), round(ys1 - ys0 + 80)
    name = NAMES[key]
    svg = (f'<svg class="story__svg" viewBox="{x} {y} {w} {hh}" xmlns="http://www.w3.org/2000/svg" role="img" aria-labelledby="{name}-approach-title {name}-approach-desc">\n'
           f'  <title id="{name}-approach-title">{h["title"]}</title>\n  <desc id="{name}-approach-desc">{h["desc"]}</desc>\n'
           f'  <!-- Generated by tools/approach_svgs.py from the Figma hero. Stage groups are revealed by site.js. -->\n'
           f'  <g font-family="Inter, sans-serif" fill="none">\n' + "\n".join(parts) + "\n  </g>\n</svg>\n")
    (OUT / f"{name}-approach.svg").write_text(svg)
    return name, len(svg), (x, y, w, hh), stages


if __name__ == "__main__":
    for k in HEROES:
        print(build(k))
