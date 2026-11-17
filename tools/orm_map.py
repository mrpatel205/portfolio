"""Object relationship map (Teller · 'Learning the tellers' language first').

Source: FigJam B19PpeFSo8SA9INRfmaA7T, section 15:69 (neutral system names).
Writes:
  mockups/orm-demo/map.svg   – final state, for Figma import / still
  mockups/orm-demo/index.html – scroll-staged demo (circles → lines → labels)
Layout is fitted to the 1312 × 696 case-study image panel: circle positions keep their
relative placement from FigJam but are spread to fill the panel's width.
"""
import math, pathlib, html

ROOT = pathlib.Path(__file__).resolve().parent.parent / "mockups" / "orm-demo"

# FigJam: top-left x, y of 170 × 170 circles
NODES = {
    "holder":   ("Account holder",    651, 171),
    "sign":     ("Signatory",        1052, 114),
    "auth2":    ("Authority two",     460, 341),
    "auth1":    ("Authority one",     820, 353),
    "poa":      ("Power of attorney",1152, 353),
    "account":  ("Account",           630, 574),
    "platform": ("Banking platform",  882, 561),
    "records":  ("Customer records", 1210, 626),
    "business": ("Business account",  451, 712),
    "personal": ("Personal account",  849, 769),
    "joint":    ("Joint account",     607, 847),
}
# (from, to, label) – arrow points at "to"
EDGES = [
    ("holder", "sign", "is a"),
    ("holder", "auth2", "could be"),
    ("auth2", "auth1", "could be"),
    ("holder", "auth1", "could be"),
    ("auth1", "poa", "can be"),
    ("poa", "sign", "is"),
    ("holder", "poa", "can replace"),
    ("account", "auth1", "is listed under"),
    ("poa", "platform", "is not in"),
    ("account", "platform", "is in"),
    ("auth1", "platform", "is in"),
    ("poa", "records", "is in"),
    ("personal", "platform", "is in"),
    ("business", "personal", "cannot be"),
    ("joint", "personal", "can be"),
]

W, H, PAD, R = 1312, 696, 40, 58
src = {k: (x + 85, y + 85) for k, (_, x, y) in NODES.items()}
xs = [c[0] for c in src.values()]; ys = [c[1] for c in src.values()]
x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
def fit(p):
    x, y = p
    return (PAD + R + (x - x0) / (x1 - x0) * (W - 2 * (PAD + R)),
            PAD + R + (y - y0) / (y1 - y0) * (H - 2 * (PAD + R)))
pos = {k: fit(v) for k, v in src.items()}

def wrap(label):
    words = label.split()
    if len(words) == 1: return [label]
    if label == "Power of attorney": return ["Power of", "attorney"]
    return [" ".join(words[:-1]), words[-1]] if len(words) > 1 else [label]

BEND = 0.16   # curve sideways by 16% of the edge length, like FigJam's curved connectors
# per-edge bends where a label would otherwise sit on a circle (short edge, or a neighbour in the way)
BEND_FOR = {("personal", "platform"): 0.75, ("business", "personal"): -0.05}
def edge_geom(a, b):
    (ax, ay), (bx, by) = pos[a], pos[b]
    dx, dy = bx - ax, by - ay; L = math.hypot(dx, dy)
    nx, ny = -dy / L, dx / L
    k = BEND_FOR.get((a, b), BEND)
    cx, cy = (ax + bx) / 2 + nx * k * L, (ay + by) / 2 + ny * k * L
    def toward(px, py, qx, qy, d):
        vx, vy = qx - px, qy - py; m = math.hypot(vx, vy); return px + vx / m * d, py + vy / m * d
    sx, sy = toward(ax, ay, cx, cy, R + 4)          # leave the circle edge
    ex, ey = toward(bx, by, cx, cy, R + 6)          # stop just short of the target circle
    mx, my = 0.25 * sx + 0.5 * cx + 0.25 * ex, 0.25 * sy + 0.5 * cy + 0.25 * ey   # curve midpoint (t = .5)
    tx, ty = ex - cx, ey - cy; tm = math.hypot(tx, ty); tx, ty = tx / tm, ty / tm   # tangent at the end
    hx, hy = -ty, tx; s = 9
    head = f"M{ex - tx*s + hx*s*0.6:.1f},{ey - ty*s + hy*s*0.6:.1f} L{ex:.1f},{ey:.1f} L{ex - tx*s - hx*s*0.6:.1f},{ey - ty*s - hy*s*0.6:.1f}"
    return f"M{sx:.1f},{sy:.1f} Q{cx:.1f},{cy:.1f} {ex:.1f},{ey:.1f}", head, (mx, my)

def _curve_pts(a, b, k, n=40):
    (ax, ay), (bx, by) = pos[a], pos[b]
    dx, dy = bx - ax, by - ay; L = math.hypot(dx, dy); nx, ny = -dy / L, dx / L
    cx, cy = (ax + bx) / 2 + nx * k * L, (ay + by) / 2 + ny * k * L
    return [((1-t)**2*ax + 2*(1-t)*t*cx + t*t*bx, (1-t)**2*ay + 2*(1-t)*t*cy + t*t*by) for t in (i/n for i in range(n+1))]

def _label_box(a, b, k):
    old = BEND_FOR.get((a, b)); BEND_FOR[(a, b)] = k
    _, _, (mx, my) = edge_geom(a, b)
    if old is None: del BEND_FOR[(a, b)]
    else: BEND_FOR[(a, b)] = old
    lab = next(l for x, y, l in EDGES if (x, y) == (a, b)); w = len(lab) * 7.4 + 14
    return (mx - w/2 - 4, my - 16, mx + w/2 + 4, my + 16)

def _score(edge, k, placed_boxes, placed_curves):
    a, b, _ = edge; pts = _curve_pts(a, b, k); score = abs(k - BEND) * 20
    for key, (x, y) in pos.items():                       # line must not run through another circle
        if key in (a, b): continue
        d = min(math.hypot(px - x, py - y) for px, py in pts)
        if d < R + 10: score += (R + 10 - d) * 10
    x0_, y0_, x1_, y1_ = _label_box(a, b, k)
    for key, (x, y) in pos.items():                       # label must not sit on a circle
        nx_, ny_ = max(x0_, min(x, x1_)), max(y0_, min(y, y1_))
        if math.hypot(x - nx_, y - ny_) < R + 4: score += 500
    for bx0, by0, bx1, by1 in placed_boxes:               # labels must not overlap each other
        if x0_ < bx1 and bx0 < x1_ and y0_ < by1 and by0 < y1_: score += 500
    for c in placed_curves:                               # label must not sit on another line
        if any(x0_ < px < x1_ and y0_ < py < y1_ for px, py in c): score += 120
    return score

def route():
    """Pick each edge's bend so lines clear other circles and labels clear circles, lines and each other."""
    boxes, curves = [], []
    for e in sorted(EDGES, key=lambda e: -math.dist(pos[e[0]], pos[e[1]])):
        a, b, _ = e
        best = min((_score(e, k / 100, boxes, curves), k / 100) for k in range(-80, 81, 2))
        BEND_FOR[(a, b)] = best[1]
        boxes.append(_label_box(a, b, best[1])); curves.append(_curve_pts(a, b, best[1]))
    return {f"{a}->{b}": BEND_FOR[(a, b)] for a, b, _ in EDGES}

GREY10, INK = "#e6e6e6", "#1e1e1e"
def svg(animated):
    out = [f'<svg class="orm" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="Object relationship map of the things tellers work with and the rules between them">']
    out.append('<g class="orm-lines">')
    labels = []
    for i, (a, b, lab) in enumerate(EDGES):
        d, head, (mx, my) = edge_geom(a, b)
        out.append(f'<g class="orm-line" style="--i:{i}"><path class="orm-curve" d="{d}" fill="none" stroke="{INK}" stroke-width="2" pathLength="1"/>'
                   f'<path class="orm-head" d="{head}" fill="none" stroke="{INK}" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></g>')
        wpx = len(lab) * 7.4 + 14
        labels.append(f'<g class="orm-label" style="--i:{i}"><rect x="{mx - wpx/2:.1f}" y="{my - 12:.1f}" width="{wpx:.1f}" height="24" rx="12" fill="{GREY10}"/>'
                      f'<text x="{mx:.1f}" y="{my + 5:.1f}" text-anchor="middle" font-family="Inter, Helvetica, Arial, sans-serif" font-size="14" fill="#000">{html.escape(lab)}</text></g>')
    out.append('</g><g class="orm-nodes">')
    for i, (k, (label, _, _)) in enumerate(NODES.items()):
        x, y = pos[k]; lines = wrap(label); lh = 19
        ty = y - (len(lines) - 1) * lh / 2 + 6
        tspans = "".join(f'<tspan x="{x:.1f}" y="{ty + j*lh:.1f}">{html.escape(t)}</tspan>' for j, t in enumerate(lines))
        out.append(f'<g class="orm-node" style="--i:{i}"><circle cx="{x:.1f}" cy="{y:.1f}" r="{R}" fill="{INK}"/>'
                   f'<text text-anchor="middle" font-family="Inter, Helvetica, Arial, sans-serif" font-size="16" font-weight="500" fill="#fff">{tspans}</text></g>')
    out.append('</g><g class="orm-labels">' + "".join(labels) + '</g></svg>')
    return "\n".join(out)

PAGE = """<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Object relationship map demo</title>
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500&display=swap" rel="stylesheet">
<style>
  :root { --grey-10:#e6e6e6; --grey-70:#4d4d4d; --ease: cubic-bezier(0.16, 1, 0.3, 1); }
  * { box-sizing: border-box; }
  body { margin:0; font-family:"Inter","Helvetica Neue",Arial,sans-serif; color:#000; background:#fff; }
  main { max-width:1320px; margin:0 auto; padding:64px 16px 0; }
  .copy { max-width:640px; margin:0 auto 32px; }
  h1 { font-size:24px; line-height:32px; font-weight:400; margin:0 0 16px; }
  .copy p { font-size:16px; line-height:24px; margin:0; }
  .after { height: 60vh; }

  /* Staged like <x-story>: block pins, each 70vh of scroll triggers the next stage; stages reverse on scroll up */
  .orm-story { position: relative; height: calc(100vh + 3 * 70vh); }
  .orm-pin { position: sticky; top: 0; height: 100vh; display: grid; place-items: center; }
  .orm-panel { width: 100%; aspect-ratio: 1312 / 696; background: var(--grey-10); }   /* map sits straight on grey/10 */
  .orm { display: block; width: 100%; height: 100%; }

  /* Stage 1: circles + labels fade in (0.5s, 140ms stagger) */
  .js .orm-node { opacity: 0; transition: opacity .5s var(--ease); }
  .orm-story[data-stage="1"] .orm-node, .orm-story[data-stage="2"] .orm-node, .orm-story[data-stage="3"] .orm-node { opacity: 1; transition-delay: calc(var(--i) * 140ms); }
  /* Stage 2: lines connect – each curve draws from its source to its target (0.6s, 90ms stagger), arrowhead follows */
  .js .orm-curve { stroke-dasharray: 1; stroke-dashoffset: 1; transition: stroke-dashoffset .6s var(--ease); }
  .js .orm-head { opacity: 0; transition: opacity .2s linear; }
  .orm-story[data-stage="2"] .orm-curve, .orm-story[data-stage="3"] .orm-curve { stroke-dashoffset: 0; transition-delay: calc(var(--i) * 90ms); }
  .orm-story[data-stage="2"] .orm-head, .orm-story[data-stage="3"] .orm-head { opacity: 1; transition-delay: calc(var(--i) * 90ms + .45s); }
  /* Stage 3: rule labels fade in on the connectors (0.5s, 90ms stagger) */
  .js .orm-label { opacity: 0; transition: opacity .5s var(--ease); }
  .orm-story[data-stage="3"] .orm-label { opacity: 1; transition-delay: calc(var(--i) * 90ms); }

  /* Mobile: hidden – at phone width the map's text drops to ~4px; the paragraph carries the point (Ash, 2026-11-17) */
  @media (max-width: 699px) {
    .orm-story { display: none; }
  }
  @media (prefers-reduced-motion: reduce) {
    .orm-story { height: auto; } .orm-pin { position: static; height: auto; }
    .js .orm-node, .js .orm-head, .js .orm-label { opacity: 1; transition: none; }
    .js .orm-curve { stroke-dashoffset: 0; transition: none; }
  }
</style></head>
<body><script>document.documentElement.classList.add('js')</script>
<main>
  <div class="copy">
    <h1>Learning the tellers’ language first</h1>
    <p>Tellers used terms I did not know: cash recyclers, authorisations, policy thresholds. Requirements alone would have put my assumptions between them and their work. So I mapped their vocabulary: each circle is something tellers handle, each arrow a rule, like ‘a power of attorney can replace an authority’. That let me design flows where each screen showed what tellers expected next.</p>
  </div>
  <section class="orm-story" data-stage="0">
    <div class="orm-pin"><div class="orm-panel">__SVG__</div></div>
  </section>
  <div class="after"></div>
</main>
<script>
(() => {
  const story = document.querySelector('.orm-story');
  const reduce = matchMedia('(prefers-reduced-motion: reduce)').matches;
  if (reduce) { story.dataset.stage = 3; return; }

  const update = () => {
    const r = story.getBoundingClientRect(), step = innerHeight * .7;
    const past = -r.top;                                   // px scrolled since the block reached the top
    const s = past < -innerHeight * .2 ? 0 : Math.min(3, 1 + Math.max(0, Math.floor(past / step)));
    if (String(s) !== story.dataset.stage) story.dataset.stage = s;
  };
  addEventListener('scroll', update, { passive: true }); addEventListener('resize', update); update();
})();
</script>
</body></html>
"""

if __name__ == "__main__":
    BEND_FOR.clear(); print("bends:", route())
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "map.svg").write_text(svg(animated=False))
    (ROOT / "index.html").write_text(PAGE.replace("__SVG__", svg(animated=True)))
    # quick overlap report: closest circle gap and label/circle collisions
    ks = list(pos); gaps = []
    for i in range(len(ks)):
        for j in range(i + 1, len(ks)):
            (ax, ay), (bx, by) = pos[ks[i]], pos[ks[j]]
            gaps.append((math.hypot(bx - ax, by - ay) - 2 * R, ks[i], ks[j]))
    print("closest circle gaps:", sorted(gaps)[:3])
    hits = []
    for a, b, lab in EDGES:
        _, _, (mx, my) = edge_geom(a, b); wpx = len(lab) * 7.4 + 14
        for k, (x, y) in pos.items():
            nx_, ny_ = max(mx - wpx/2, min(x, mx + wpx/2)), max(my - 12, min(y, my + 12))
            if math.hypot(x - nx_, y - ny_) < R: hits.append((lab, a, b, "overlaps", k))
    print("label/circle overlaps:", hits)
