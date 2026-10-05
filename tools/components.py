"""Case study components: build-time <x-*> tags expanded into the site's markup.

A case study page is written as a short outline of components, with the prose kept as
plain HTML inside them. Each tag below becomes the markup the CSS and site.js expect,
so every case study shares one structure and a fix in one place fixes all four.

  <x-case-study slug page title description> … </x-case-study>
      The whole page: head, nav, <main><article>, footer.

  <x-hero image width height alt [back-href back-label]>   back-href adds a Back link above everything
    <x-notice>Confidentiality line, shown above the title</x-notice>   optional
    <x-title>Heading, may contain <br></x-title>
    <x-meta><x-item label="Company">NAB</x-item> …</x-meta>   first group (left)
    <x-meta> … </x-meta>                                       second group (right)
  </x-hero>

  <x-scene id heading [subheading]>                 Situation / Task: copy pins, image rises
    <p>…</p>
    <x-visual …/>
  </x-scene>

  <x-skills [heading]>                              Skills panel, held mid-screen
    <x-skill icon="search">Research &amp; Synthesis</x-skill>
  </x-skills>

  <x-pause id heading> <p>…</p> </x-pause>          Text-only reading pause (Approach)

  <x-story id heading [subheading] svg stages>      Pinned copy + illustration that builds up
    <p>… <span data-from="2">…</span></p>           in stages as the visitor scrolls (Teller
    <p data-from="4">…</p>                          Approach). data-from = stage the copy fades
    … <span class="story-mark" data-stage="1">…</span>   in at; story-mark = underlined while
  </x-story>                                        its stage is current. svg = file name in
                                                    site-src/illustrations/ (inlined; its parts
                                                    carry data-stage + --i, see site.css)

  <x-metrics id heading subheading eyebrow>        Research metrics on a dark panel that pins and
    <p>Lead…</p>                                    builds in 4 stages (Teller Research): header,
    <x-headline value label [note]/>                headline number counts up, then each group
    <x-group heading>                               rises with its numbers counting. The first
      <x-stat value label [note] [callout]/>        group lands in stage 3, the second (and the
    </x-group>                                      headline note) in stage 4.
  </x-metrics>

  <x-challenges [heading]>                          Key challenges: title pins for the section
    <x-topic id heading>                            subtitle pins for the topic
      <x-stage> <p>…</p> <x-visual …/> </x-stage>   stages swap in place; no visual = text stage
    </x-topic>
  </x-challenges>

  <x-accordion [id] [heading]>                      Key challenges as a numbered accordion
    <p>Intro…</p>                                   (alternative to x-challenges; Teller)
    <x-panel id heading>                            one challenge: closed by default
      <p><strong>Lead.</strong> …</p>
      <x-visual …/>                                 optional, any number, stacked right of the
    </x-panel>                                      copy; the copy pins while they scroll past
  </x-accordion>

  <x-accordion variant="read-more" [thumbnail]>     same, as Figma Accordion/Read more: a
    <p>Intro…</p>                                   "Read more" link under a short context
    <x-panel id heading [subtitle]>                 opens the panel. thumbnail = the first
      <x-skill icon="workflow">Label</x-skill>      x-visual also shows beside the closed row
      <x-context>~40 words, shown when closed</x-context>
      <p><strong>Label.</strong> …</p>
      <x-visual …/>
    </x-panel>
  </x-accordion>

  <x-visual src width height alt [caption] [centred]/>    image in a grey frame
  <x-visual placeholder/>                                 "[Image to come]"

  <x-final-visuals src width height alt [heading]>  one flow image on desktop …
    <x-screen src width height alt/>                … its screens stacked on small screens
  </x-final-visuals>

  <x-impact [heading] lead [stamp]> <p>…</p> <x-metric label value/>
    <x-signal heading>Text</x-signal> </x-impact>      signals = qualitative notes; stamp = "as of" line

  <x-next href title target [label]/>               link to the next case study

Attribute values are used as written (write &amp; and &quot; yourself); they may contain
inline HTML such as <br> or <strong>.
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

TAG = re.compile(
    r'<(/?)x-([\w-]+)((?:\s+[\w-]+(?:="[^"]*")?)*)\s*(/?)>'
)
ATTR = re.compile(r'([\w-]+)(="[^"]*")?')


class Node:
    def __init__(self, name, attrs):
        self.name, self.attrs, self.children = name, attrs, []

    def kids(self, name):
        return [c for c in self.children if isinstance(c, Node) and c.name == name]

    def kid(self, name):
        found = self.kids(name)
        return found[0] if found else None

    def text(self):
        """Everything that isn't a child component, as HTML."""
        return "".join(c for c in self.children if isinstance(c, str)).strip()

    def req(self, key):
        if key not in self.attrs:
            raise ValueError(f"<x-{self.name}> needs a {key}= attribute")
        return self.attrs[key]


def parse(src):
    root = Node("root", {})
    stack = [root]
    pos = 0
    for m in TAG.finditer(src):
        stack[-1].children.append(src[pos:m.start()])
        pos = m.end()
        closing, name, attrs, selfclose = m.groups()
        if closing:
            if stack[-1].name != name:
                raise ValueError(f"</x-{name}> closes <x-{stack[-1].name}>")
            stack.pop()
            continue
        node = Node(name, {k: (v[2:-1] if v else True) for k, v in ATTR.findall(attrs)})
        stack[-1].children.append(node)
        if not selfclose:
            stack.append(node)
    if len(stack) != 1:
        raise ValueError(f"<x-{stack[-1].name}> is never closed")
    root.children.append(src[pos:])
    return root


def render(node):
    if isinstance(node, str):
        return node
    if node.name == "root":
        return "".join(render(c) for c in node.children)
    fn = COMPONENTS.get(node.name)
    if fn is None:
        raise ValueError(f"unknown component <x-{node.name}>")
    return fn(node)


def expand(src):
    """Expand every <x-*> component in a page. Pages without components pass through."""
    return render(parse(src)) if "<x-" in src else src


def indent(html, spaces):
    pad = " " * spaces
    return "\n".join(pad + line if line.strip() else line for line in html.strip("\n").split("\n"))


def prose(node):
    return f'<div class="prose t-body-lg">\n{indent(node.text(), 2)}\n</div>'


# ---------- Components ----------

def case_study(n):
    body = "\n\n".join(render(c).strip("\n") for c in n.children if isinstance(c, Node))
    return f"""<!doctype html>
<html lang="en-AU">
<head>
{{{{> head}}}}
<title>{n.req('title')}</title>
<meta name="description" content="{n.req('description')}">
</head>
<body data-page="{n.req('page')}" data-case-study="{n.req('slug')}">
{{{{> nav}}}}

<main id="main">
  <article class="container">

{indent(body, 4)}

  </article>
</main>

{{{{> footer}}}}
</body>
</html>
"""


def back_link(href, label):
    return (f'<a class="back-link link link--small" href="{href}" data-track="back" data-track-target="{href}">'
            f'{{{{icon:arrow-left}}}}{label}</a>')


def hero(n):
    groups = []
    for i, meta in enumerate(n.kids("meta")):
        items = "\n".join(
            f'<div class="cs-meta__item"><dt>{it.req("label")}</dt><dd>{it.text()}</dd></div>'
            for it in meta.kids("item"))
        cls = "cs-meta__group" + (" cs-meta__group--right" if i else "")
        groups.append(f'<div class="{cls}">\n{indent(items, 2)}\n</div>')
    back = back_link(n.attrs["back-href"], n.attrs.get("back-label", "Back")) + "\n  " if n.attrs.get("back-href") else ""
    notice = n.kid("notice")
    notice_html = f'\n  <p class="cs-notice t-caption">{notice.text()}</p>' if notice else ""
    return f"""<header class="cs-hero" data-section="hero">\n  {back}{notice_html.lstrip()}
  <h1 class="t-h1 cs-hero__title">{n.kid('title').text()}</h1>
  <dl class="cs-meta t-caption">
{indent(chr(10).join(groups), 4)}
  </dl>
  {hero_image(n)}
</header>"""


def hero_image(n):
    if n.attrs.get("placeholder"):
        return ('<figure class="cs-hero__image" data-reveal><div class="cs-visual__frame '
                'cs-visual__frame--placeholder cs-hero__placeholder t-caption">[Image to come]</div></figure>')
    return f"""<figure class="cs-hero__image" data-reveal>
    <img src="{n.req('image')}" width="{n.req('width')}" height="{n.req('height')}"
         alt="{n.req('alt')}">
  </figure>"""


def visual(n):
    if n.attrs.get("placeholder"):
        frame = '<div class="cs-visual__frame cs-visual__frame--placeholder t-caption">[Image to come]</div>'
    else:
        cls = "cs-visual__frame" + (" cs-visual__frame--centred" if n.attrs.get("centred") else "")
        frame = (f'<div class="{cls}"><img src="{n.req("src")}" width="{n.req("width")}" '
                 f'height="{n.req("height")}" loading="lazy" alt="{n.req("alt")}"></div>')
    cap = f'\n  <figcaption class="t-caption">{n.attrs["caption"]}</figcaption>' if n.attrs.get("caption") else ""
    return f'<figure class="cs-visual">\n  {frame}{cap}\n</figure>'


def scene_visual(n):
    v = n.kid("visual")
    return f'\n  <div class="scene__visual">\n{indent(visual(v), 4)}\n  </div>' if v else ""


def heading_block(n):
    """Figma V4 titles: eyebrow pill (heading) + H3 title (subheading). With no subheading the
    pill is the heading. A scene with only a subheading (no pill) is a bare H3."""
    id_ = n.req("id")
    h, sub = n.attrs.get("heading"), n.attrs.get("subheading")
    if h and sub:
        return (f'<div class="cs-heading">\n  <p class="cs-pill">{h}</p>\n'
                f'  <h2 class="t-h3" id="{id_}">{sub}</h2>\n</div>')
    if h:
        return f'<div class="cs-heading">\n  <h2 class="cs-pill" id="{id_}">{h}</h2>\n</div>'
    if sub:
        return f'<h2 class="t-h3 cs-heading" id="{id_}">{sub}</h2>'
    return ""


def scene(n):
    """Copy pins first, then its image rises to meet it (Situation, Task)."""
    id_ = n.req("id")
    label = f' aria-labelledby="{id_}"' if "heading" in n.attrs or "subheading" in n.attrs else ""
    return f"""<section class="scene"{label} data-section="{n.attrs.get('section', id_)}">
  <div class="scene__copy">
{indent(heading_block(n), 4)}
{indent(prose(n), 4)}
  </div>{scene_visual(n)}
</section>"""


def skills(n):
    """Pins in the middle of the viewport and holds for 1.5 screens of scroll."""
    id_ = n.attrs.get("id", "skills")
    items = "\n".join(
        f'<li class="skill"><span class="skill__tile">{{{{icon:{s.req("icon")}}}}}</span>{s.text()}</li>'
        for s in n.kids("skill"))
    return f"""<div class="cs-section cs-hold" data-section="{id_}">
  <div class="cs-hold__frame">
    <section class="panel skills" aria-labelledby="{id_}">
      <h2 class="t-h3" id="{id_}">{n.attrs.get('heading', 'Skills used')}</h2>
      <ul class="skills__list t-body-lg">
{indent(items, 8)}
      </ul>
    </section>
  </div>
</div>"""


def pause(n):
    """Text-only block: pins centred with white space all round, holds, scrolls on."""
    id_ = n.req("id")
    return f"""<section class="cs-pause" aria-labelledby="{id_}" data-section="{n.attrs.get('section', id_)}">
  <div class="cs-pause__inner cs-block">
    <div class="cs-block__copy">
{indent(heading_block(n), 6)}
{indent(prose(n), 6)}
    </div>
  </div>
</section>"""


def story(n):
    """Copy + illustration pin together; scrolling steps through `stages`. Each stage's
    parts animate in once when it is reached (triggered, not scrubbed) and reverse on the
    way back up. The scroll distance per stage is --story-step in site.css."""
    id_, stages = n.req("id"), int(n.req("stages"))
    svg = (ROOT / "site-src" / "illustrations" / f"{n.req('svg')}.svg").read_text().strip()
    vb = re.search(r'viewBox="[-\d.]+ [-\d.]+ ([\d.]+) ([\d.]+)"', svg)
    ratio = round(float(vb.group(1)) / float(vb.group(2)), 3)
    return f"""<section class="story" aria-labelledby="{id_}" data-section="{n.attrs.get('section', id_)}"
         data-stages="{stages}" style="--stages: {stages}; --story-ratio: {ratio}">
  <div class="story__pin">
    <div class="story__copy">
{indent(heading_block(n), 6)}
{indent(prose(n), 6)}
    </div>
    <figure class="story__figure">
{indent(svg, 6)}
    </figure>
  </div>
</section>"""


def metrics(n):
    """Research metrics: a dark panel that pins like x-story and steps through 4 stages.
    Numbers carry data-count-stage and count up from 0 when their stage is reached
    (site.js); the real value is in the HTML, so no-JS and reduced motion see it as is."""
    id_ = n.req("id")

    def num(value, stage, ms, cls):
        return (f'<span class="{cls}" aria-hidden="true" data-count-stage="{stage}" '
                f'data-count-ms="{ms}">{value}</span><span class="visually-hidden">{value}</span>')

    h = n.kid("headline")
    note = h.attrs.get("note")
    note_html = f'\n    <p class="metrics__note" data-from="4">{note}</p>' if note else ""
    groups = []
    for gi, g in enumerate(n.kids("group")):
        stage = 3 + gi
        rows = []
        for si, st in enumerate(g.kids("stat")):
            call = bool(st.attrs.get("callout"))
            sub = f'<span class="metrics__sub">{st.attrs["note"]}</span>' if st.attrs.get("note") else ""
            rows.append(
                f'<li class="metrics__stat{" metrics__stat--callout" if call else ""}" data-from="{stage}" style="--i: {si + 1}">'
                f'{num(st.req("value"), stage, 800, "metrics__value")}'
                f'<span class="metrics__text"><span class="metrics__label">{st.req("label")}</span>{sub}</span></li>')
        groups.append(f"""<div class="metrics__group">
  <h3 class="metrics__group-head" data-from="{stage}" style="--i: 0">{g.req('heading')}</h3>
  <ul class="metrics__list">
{indent(chr(10).join(rows), 4)}
  </ul>
</div>""")
    return f"""<section class="story story--metrics" aria-labelledby="{id_}" data-section="{n.attrs.get('section', id_)}"
         data-stages="4" style="--stages: 4">
  <div class="story__pin">
    <div class="panel metrics" data-play-target>
      <div class="metrics__left">
        <div class="metrics__header" data-from="1">
          <h2 class="t-h3 metrics__subheading" id="{id_}">{n.attrs.get('subheading') or n.req('heading')}</h2>
{indent(n.text().replace('<p>', '<p class="t-body-lg metrics__lead">'), 10)}
        </div>
        <div class="metrics__headline">
          <p class="metrics__big" data-from="2">{num(h.req('value'), 2, 1400, 'metrics__big-value')}</p>
          <p class="metrics__big-label" data-from="2">{h.req('label')}</p>{indent(note_html, 6)}
        </div>
      </div>
      <div class="metrics__right">
{indent(chr(10).join(groups), 8)}
      </div>
    </div>
  </div>
</section>"""


def challenges(n):
    """The title pins for the whole section and each topic's subtitle pins for the whole
    topic. Stages within a topic swap in place (paragraph + image fade out, next paragraph
    fades in on the same spot, its image rises to meet it); a new topic scrolls in from below."""
    id_ = n.attrs.get("id", "challenges")
    topics = "\n\n".join(topic(t) for t in n.kids("topic"))
    return f"""<section class="cs-challenges" aria-labelledby="{id_}">
  <div class="cs-challenges__title-track">
    <div class="cs-challenges__title"><h2 class="cs-pill" id="{id_}">{n.attrs.get('heading', 'Key challenges')}</h2></div>
  </div>

{indent(topics, 2)}
</section>"""


def topic(n):
    id_ = n.req("id")
    stages = n.kids("stage")
    out = []
    for i, st in enumerate(stages, 1):
        cls = "scene" + (" scene--text" if not st.kid("visual") else "") + (" scene--first" if i == 1 else "")
        section = f"challenge-{id_}" + (f"-{i}" if len(stages) > 1 else "")
        out.append(f"""<div class="{cls}" data-section="{section}">
  <div class="scene__copy prose t-paragraph">
{indent(st.text(), 4)}
  </div>{scene_visual(st)}
</div>""")
    # site.js measures the subtitle; until it runs, a <br> means two lines
    style = ' style="--sub-h: 5rem"' if "<br" in n.req("heading") else ""
    return f"""<div class="topic" data-topic="{id_}"{style}>
  <div class="topic__subtitle-track">
    <h3 class="t-h3 topic__subtitle">{n.req('heading')}</h3>
  </div>
{indent(chr(10).join(out), 2)}
</div>"""


def accordion_visuals(visuals):
    """The panel's visuals, stacked; they scroll past the sticky copy."""
    return "\n".join(visual(v) for v in visuals)


def accordion(n):
    """Key challenges as a disclosure list. All panels start closed; any number can be open;
    "Expand all" toggles every panel. Without JS every panel stays open, so nothing is lost.
    While a panel is open its copy pins under the nav and its visuals scroll past (not on
    small screens).
      default            Figma Accordion/Challenge, Style=Numbered: the whole row is the button
      variant=read-more  Figma Accordion/Read more: title, subtitle, skills and context show
                         when closed; a "Read more" link opens the rest in place
      thumbnail          (read-more only) the first visual shows beside the row when closed"""
    id_ = n.attrs.get("id", "challenges")
    read_more = n.attrs.get("variant") == "read-more"
    thumb = read_more and bool(n.attrs.get("thumbnail"))
    item = read_more_item if read_more else numbered_item
    items = [item(p, i, thumb) for i, p in enumerate(n.kids("panel"), 1)]
    expand_all = "" if read_more else '    <button type="button" class="btn btn--outlined accordion__all" hidden data-track="accordion_expand_all">Expand all</button>\n'
    cls = "cs-section accordion" + (" accordion--read-more" if read_more else "") + (" accordion--thumbnail" if thumb else "")
    return f"""<section class="{cls}" aria-labelledby="{id_}" data-section="{id_}" data-accordion>
  <div class="accordion__intro">
    <div class="cs-heading">
      <p class="cs-pill">{n.attrs.get('heading', 'Key challenges')}</p>
      <h2 class="t-h3" id="{id_}">{n.attrs.get('heading', 'Key challenges')}</h2>
    </div>
    <div class="prose t-paragraph">
{indent(n.text(), 6)}
    </div>
{expand_all}  </div>
  <ol class="accordion__list">
{indent(chr(10).join(items), 4)}
  </ol>
</section>"""


def numbered_item(p, i, _thumb):
    pid = p.req("id")
    visuals = p.kids("visual")
    visuals_html = (f'\n        <div class="accordion__visuals">\n{indent(accordion_visuals(visuals), 10)}\n        </div>'
                    if visuals else "")
    return f"""<li class="accordion__item" data-reveal data-section="challenge-{pid}">
  <h3 class="accordion__heading">
    <button type="button" class="accordion__trigger" id="{pid}-trigger" aria-expanded="true" aria-controls="{pid}-panel"
            data-track="accordion_toggle" data-track-target="{pid}">
      <span class="accordion__number t-h3" aria-hidden="true">{i:02d}</span>
      <span class="accordion__title t-h3">{p.req('heading')}</span>
      <span class="accordion__icon">{{{{icon:plus}}}}{{{{icon:minus}}}}</span>
    </button>
  </h3>
  <div class="accordion__panel" id="{pid}-panel" role="region" aria-labelledby="{pid}-trigger">
    <div class="accordion__clip">
      <div class="accordion__body">
        <div class="accordion__copy prose t-paragraph">
{indent(p.text(), 10)}
        </div>{visuals_html}
      </div>
    </div>
  </div>
</li>"""


def read_more_item(p, i, thumb):
    """Figma Accordion/Read more. The trigger is a "Read more" link under the context; its
    hidden suffix names the challenge, so six identical links still read apart."""
    pid = p.req("id")
    title = p.req("heading")
    plain_title = re.sub(r"<[^>]+>", "", title).strip()
    visuals = p.kids("visual")
    panels = f"{pid}-panel" + (f" {pid}-visuals" if thumb and len(visuals) > 1 else "")

    skills = p.kids("skill")
    skills_html = ""
    if skills:
        tags = "\n".join(f'<li class="accordion__skill">{{{{icon:{s.req("icon")}}}}}{s.text()}</li>' for s in skills)
        skills_html = f"""
  <div class="accordion__skills t-caption">
    <p class="accordion__skills-label">Skills used:</p>
    <ul class="accordion__skill-list">
{indent(tags, 6)}
    </ul>
  </div>"""
    subtitle = (f'\n  <p class="accordion__subtitle t-body-lg">{p.attrs["subtitle"]}</p>'
                if p.attrs.get("subtitle") else "")
    context = p.kid("context")
    context_html = f'\n  <p class="accordion__context t-paragraph-bold">{context.text()}</p>' if context else ""

    row = f"""<div class="accordion__row">
  <span class="accordion__number t-h3" aria-hidden="true">{i:02d}</span>
  <div class="accordion__summary">
    <h3 class="accordion__title t-h3" id="{pid}-title">{title}</h3>{indent(subtitle + skills_html + context_html, 2)}
    <button type="button" class="accordion__trigger accordion__more link" id="{pid}-trigger" aria-expanded="true"
            aria-controls="{panels}" data-track="accordion_toggle" data-track-target="{pid}"><span
            class="accordion__more-label">Read less</span><span class="visually-hidden">: {plain_title}</span></button>
  </div>
</div>"""
    copy = f"""<div class="accordion__copy prose t-paragraph">
{indent(p.text(), 2)}
</div>"""

    if not thumb:
        visuals_html = (f'\n<div class="accordion__visuals">\n{indent(accordion_visuals(visuals), 2)}\n</div>'
                        if visuals else "")
        return f"""<li class="accordion__item" data-reveal data-section="challenge-{pid}">
{indent(row, 2)}
  <div class="accordion__panel" id="{pid}-panel" role="region" aria-labelledby="{pid}-title">
    <div class="accordion__clip">
      <div class="accordion__body">
{indent(copy + visuals_html, 8)}
      </div>
    </div>
  </div>
</li>"""

    # Thumbnail: the first visual sits beside the row when closed and stays put when open,
    # as Visual 1 of the stack (never shown twice). The copy column pins; the rest of the
    # visuals open beneath the thumbnail.
    first = visual(visuals[0]) if visuals else visual(Node("visual", {"placeholder": True}))
    rest = accordion_visuals(visuals[1:])
    rest_html = f"""
    <div class="accordion__panel" id="{pid}-visuals">
      <div class="accordion__clip">
        <div class="accordion__visuals">
{indent(rest, 10)}
        </div>
      </div>
    </div>""" if rest else ""
    return f"""<li class="accordion__item" data-reveal data-section="challenge-{pid}">
  <div class="accordion__body">
    <div class="accordion__lead">
{indent(row, 6)}
      <div class="accordion__panel" id="{pid}-panel" role="region" aria-labelledby="{pid}-title">
        <div class="accordion__clip">
{indent(copy, 10)}
        </div>
      </div>
    </div>
    <div class="accordion__visuals">
      <div class="accordion__thumb">
{indent(first, 8)}
      </div>{rest_html}
    </div>
  </div>
</li>"""


def final_visuals(n):
    """One flow image on desktop; on small screens the same flow as stacked screens
    (the unused set is display:none, so its lazy images never load)."""
    id_ = n.attrs.get("id", "final-visuals")
    screens = "\n".join(
        f'<li><img src="{s.req("src")}" width="{s.req("width")}" height="{s.req("height")}" '
        f'loading="lazy" alt="{s.req("alt")}"></li>'
        for s in n.kids("screen"))
    steps = ""
    if screens:
        steps = f"""
  <ol class="final-visuals__steps" aria-label="{n.attrs.get('steps-label', n.req('alt'))}">
{indent(screens, 4)}
  </ol>"""
    return f"""<section class="cs-section final-visuals" aria-labelledby="{id_}" data-section="{id_}">
  <h2 class="visually-hidden" id="{id_}">{n.attrs.get('heading', 'Final designs')}</h2>
  <img class="final-visuals__full" data-reveal src="{n.req('src')}" width="{n.req('width')}" height="{n.req('height')}" loading="lazy"
       alt="{n.req('alt')}">{steps}
</section>"""


def impact(n):
    """Dark panel; metrics count up from 0 when seen. Marks the end of the reading progress bar."""
    id_ = n.attrs.get("id", "impact")
    metrics = "\n".join(
        f'<div class="impact__metric"><dt class="t-paragraph-bold">{m.req("label")}</dt>'
        f'<dd class="t-metric-xl" data-count-to="{m.req("value").replace(",", "")}" '
        f'aria-label="{m.req("value")}">{m.req("value")}</dd></div>'
        for m in n.kids("metric"))
    signals = "\n".join(
        f'<li class="impact__signal"><span class="impact__dot" aria-hidden="true"></span>'
        f'<div><p class="t-paragraph-bold">{g.req("heading")}</p>'
        f'<p class="t-paragraph impact__muted">{g.text()}</p></div></li>' for g in n.kids("signal"))
    signals_html = f'\n    <ul class="impact__signals">\n{indent(signals, 6)}\n    </ul>' if signals else ""
    stamp_html = (f'\n    <p class="impact__stamp t-caption"><span class="impact__stamp-dot" aria-hidden="true"></span>'
                  f'{n.attrs["stamp"]}</p>') if n.attrs.get("stamp") else ""
    return f"""<section class="cs-section cs-section--dark-gap panel impact" aria-labelledby="{id_}" data-section="{id_}" data-progress-end>
  <div class="impact__copy">
    <div class="impact__heading">
      <h2 class="t-h3" id="{id_}">{n.attrs.get('heading', 'Impact')}</h2>
      <p class="t-body-lg impact__lead impact__muted">{n.req('lead')}</p>
{indent(n.text().replace('<p>', '<p class="t-paragraph">'), 6)}
    </div>{stamp_html}
  </div>
  <div class="impact__right">
    <dl class="impact__metrics">
{indent(metrics, 6)}
    </dl>{signals_html}
  </div>
</section>"""


def next_link(n):
    """One link (Next by default). With next-href/next-title/next-target, a second link
    on the right: the main one then reads as Previous (set label="Previous case study")."""
    second = ""
    if n.attrs.get("next-href"):
        second = f"""
  <a class="seq seq--next" href="{n.attrs['next-href']}" data-track="next_case_study" data-track-target="{n.req('next-target')}">
    <span class="seq__text">
      <span class="seq__label">Next case study</span>
      <span class="t-body-lg">{n.req('next-title')}</span>
    </span>
    {{{{icon:arrow-right}}}}
  </a>"""
    first_cls = "seq--prev" if second else "seq--next"
    arrow_l = "{{icon:arrow-left}}" if second else ""
    arrow_r = "" if second else "{{icon:arrow-right}}"
    return f"""<nav class="cs-section cs-section--tight seq-nav" aria-label="More case studies" data-section="next-prev">
  <a class="seq {first_cls}" href="{n.req('href')}" data-track="{'prev' if second else 'next'}_case_study" data-track-target="{n.req('target')}">
    {arrow_l}<span class="seq__text">
      <span class="seq__label">{n.attrs.get('label', 'Next case study')}</span>
      <span class="t-body-lg">{n.req('title')}</span>
    </span>
    {arrow_r}
  </a>{second}
</nav>"""


COMPONENTS = {
    "case-study": case_study,
    "hero": hero,
    "scene": scene,
    "skills": skills,
    "pause": pause,
    "story": story,
    "metrics": metrics,
    "challenges": challenges,
    "accordion": accordion,
    "final-visuals": final_visuals,
    "impact": impact,
    "next": next_link,
    "visual": visual,
}
