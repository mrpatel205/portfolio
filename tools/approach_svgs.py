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
    return f"<{e['tag']}{a.rstrip('/')}/>"


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
    stg = 2 if who == "WITHDRAWAL" else 4
    if b.startswith("floor"):
        return stg, "fade", "floor" + who
    if b.startswith("dot"):
        return stg, "grow", "col" + b
    if b in ("label — one column", "pointer — one column"):
        return 3, "fade", "ann1"
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
    stages = sorted({s for s, _ in units})
    parts = []
    for s in stages:
        us = []
        for (stg, uid), u in units.items():
            if stg != s:
                continue
            solid = [e for e in u["els"] if e["tag"] != "text"] or u["els"]
            left = -1 if uid == "title" else h["over"].get(uid, min(e["bb"][0] for e in solid))
            us.append((left, u["kind"] == "grow", uid, u))
        us.sort(key=lambda t: t[:2])
        parts.append(f"    <!-- Stage {s} -->")
        for i, (_, _, uid, u) in enumerate(us):
            body = "\n".join("      " + render(e) for e in u["els"])
            parts.append(f'    <g class="story__{u["kind"]}" data-stage="{s}" style="--i:{i}">\n{body}\n    </g>')
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
