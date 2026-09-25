"""HTML stubs + static assets for the edition.

Every stub is a complete, readable document with JavaScript OFF — the meeting's
transcript is real HTML, the issue's timeline is a real list of links, and the
head carries OG/Twitter tags so a link unfurls in a group chat with the
meeting's name, date, and thumbnail (specs/16 §P0.2). app.js then hydrates the
same DOM (adds the player facade, cite, search, the language menu) without
tearing the transcript down — progressive enhancement, so JS-off passes the
acceptance click-paths natively.

CSP is machine-enforced via a <meta http-equiv> tag on every page: default-src
'self', frames only to youtube-nocookie, images 'self' + i.ytimg.com. No
third-party script, font, or beacon rides in.
"""

from __future__ import annotations

import html
import re
import shutil
from pathlib import Path
from urllib.parse import quote

from web import tools

REPO = Path(__file__).resolve().parents[1]
BRAND = REPO / "brand"
DMG_LATEST = "https://github.com/amateurmenace/control-z/releases/latest"   # every release
# The desktop app itself — Civic Media Studio, the desk that renders a reel,
# cuts a kit and burns captions. Wherever the record says a step "needs the
# desk", it hands over the desk (specs/28 §3.5): a direct download, one
# click. The reader's twin is app.js DESK_DMG; a test holds them equal.
DESK_VERSION = "2.1.0"
DESK_DMG = ("https://github.com/amateurmenace/control-z/releases/download/"
            f"v{DESK_VERSION}/civicmedia-studio-{DESK_VERSION}-macos-arm64.dmg")


def desk_button(label: str = "↓ Get the desktop app — macOS", primary: bool = False) -> str:
    """The desk, as a pressed link — an anchor, content in the paper."""
    return (f'<a class="btn{" primary" if primary else ""} deskdl" href="{DESK_DMG}" rel="noopener" '
            f'title="Civic Media Studio {DESK_VERSION} for macOS (Apple silicon)">{esc(label)}</a>')
COMMUNITYAI = "https://communityai.studio"

# Where a reader goes to read the program that pressed what they are reading.
# The covenant page promises the source is published; a promise with a dead
# link behind it is worse than no promise, so these are constants and a test
# asserts the covenant page carries them.
# the record's own home (specs/23 D1): this repository, extracted from the
# control-z monorepo 2026-09-23 — every prompt, gate and fallback the
# constitution points at lives here now, and the releases are tagged here
SOURCE_REPO = "https://github.com/amateurmenace/publicrecord-studio"
LICENSING_DOC = SOURCE_REPO + "/blob/main/LICENSING.md"
_CSP_BASE = ("default-src 'self'; base-uri 'self'; form-action 'self'; "
             "frame-src https://www.youtube-nocookie.com; "
             "img-src 'self' https://i.ytimg.com data:; "
             "font-src 'self'; "
             "style-src 'self' 'unsafe-inline'; script-src 'self'; "
             "connect-src 'self'{extra}; object-src 'none'")
CSP = _CSP_BASE.format(extra="")

# The record's own API, when this pressing has one. Empty for a desk edition,
# which is the case that must never change: press without --api and the bytes
# are identical to yesterday's.
#
# This is the one place the reader is allowed to reach past its own origin, and
# it is worth being exact about why that is not a hole in the covenant. The
# promise on the covenant page is that no THIRD PARTY can load a script, a font
# or a beacon — and that still holds, because default-src, script-src and
# img-src are untouched. What widens is connect-src, by exactly one first-party
# host: the record's own service, named in full, on the same project and the
# same bill. A reader who blocks it loses meaning-search and keeps everything
# else, which is the whole design.
#
# When the edition and the API eventually share an origin behind one load
# balancer, this exception disappears on its own and nothing else changes.
_API = {"base": ""}


def set_api(base: str = "") -> None:
    """Point this pressing at its Studio, or at nothing."""
    _API["base"] = (base or "").rstrip("/")


def api() -> str:
    """This pressing's Studio, or "" for a desk edition."""
    return _API["base"]


def csp() -> str:
    """The policy for this pressing. Identical to CSP when there is no API."""
    base = _API["base"]
    if not base:
        return CSP
    origin = "/".join(base.split("/")[:3])       # scheme://host, never a path
    return _CSP_BASE.format(extra=" " + origin)


def _api_meta() -> str:
    """The address the reader may call, next to the policy that permits it.

    A meta tag rather than a fetch of `manifest.json`, for two reasons. It is
    available when the parser reaches it, so the first keystroke in the search
    box does not race a round trip; and it sits in the same `<head>` as the
    `connect-src` that authorises it, so the permission and the address are one
    thing to read and one thing to change. The reader treats its absence as
    "this is a desk edition" — which is exactly what it means."""
    base = _API["base"]
    return f'\n<meta name="record-api" content="{esc(base)}">' if base else ""


# What this pressing serves, set once per bake by emit_stubs().
#
# Module state rather than a parameter because the scope bar lives in the
# shared chrome, and ten page functions call shell() — threading an eleventh
# argument through a page function so a folio can name a town would be
# ceremony that buys nothing. A bake is one process pressing one edition; this
# is written before the first stub renders and never again.
_EDITION = {"towns": [], "bodies": [], "untowned": 0, "meetings": 0}


def set_edition(towns_plane) -> None:
    """Tell the chrome which towns and bodies this edition actually holds."""
    _EDITION.update({"towns": [], "bodies": [], "untowned": 0, "meetings": 0})
    _EDITION.update(towns_plane or {})


# The search spine's "try" words (specs/29) — the record's own widest issues
# and recurring topics, set once per bake beside the edition; the masthead
# presses them on the front page.
_SPINE = {"tries": []}


def set_spine(tries) -> None:
    _SPINE["tries"] = [str(x) for x in (tries or [])][:6]


def esc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def xesc(s) -> str:
    return html.escape(str(s or ""), quote=True)


def n_of(n, noun) -> str:
    """A counted noun that stays English at one — "1 meeting", "3 meetings".
    The re-review's catch: the featured card learned this while the front
    page's own rail still pressed "1 meetings" one screen away."""
    n = int(n or 0)
    return f"{n} {noun}" + ("" if n == 1 else "s")


def hms(t) -> str:
    t = max(0, float(t or 0))
    h, m, s = int(t // 3600), int((t % 3600) // 60), int(t % 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def _brand_mark() -> str:
    """The publicrecord keycap — the minutes on the record — read byte-equal
    from brand/logos and never redrawn (specs/20 §4, branding law). One read,
    used for both the masthead and the favicon, so the two can never drift."""
    return (BRAND / "logos" / "publicrecord-mark.svg").read_text(
        encoding="utf-8").strip()


# --------------------------------------------------------------------------
# shared chrome
# --------------------------------------------------------------------------

def _feed_link(feed) -> str:
    """A page's own RSS feed, advertised in the head for reader auto-discovery
    (specs/20 §7.9 C). An issue page carries its own long-view feed; it sits
    before the firehose so a reader who subscribes from an issue gets that
    issue, not the whole record."""
    if not feed:
        return ""
    return (f'<link rel="alternate" type="application/rss+xml" '
            f'title="{esc(feed["title"])}" href="{esc(feed["href"])}">')


def head(title, desc, canonical, og_image="", version="0", feed=None):
    og = (f'<meta property="og:image" content="{esc(og_image)}">'
          f'<meta name="twitter:card" content="summary_large_image">'
          if og_image else
          '<meta name="twitter:card" content="summary">')
    # preload only the two faces first paint needs (Inter body, mono headline);
    # the rest swap in. crossorigin is required on a font preload even for a
    # same-origin fetch, or the browser fetches the face twice.
    preload = "".join(
        f'<link rel="preload" href="/app/fonts/{f}.woff2" as="font" '
        f'type="font/woff2" crossorigin>' for f in _PRELOAD_FONTS)
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{csp()}">{_api_meta()}
<title>{esc(title)}</title>
<meta name="description" content="{esc(desc)}">
<link rel="canonical" href="{esc(canonical)}">
<meta property="og:type" content="website">
<meta property="og:title" content="{esc(title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:url" content="{esc(canonical)}">{og}
<meta name="theme-color" content="#F3EEE3">
<link rel="icon" href="/app/favicon.svg">
<link rel="manifest" href="/app/manifest.webmanifest">
{_feed_link(feed)}<link rel="alternate" type="application/rss+xml" title="The record — new meetings and resurfacings" href="/app/feeds/firehose.xml">
{preload}<link rel="stylesheet" href="/app/app.css?v={esc(version)}">
</head><body>"""




# The record's own surfaces, as a newspaper's section line. The thirteen desk
# tools that used to share this rail are gone from it — they live on /app/press
# now (specs/20 §5). What is left is the paper's own sections, and nothing
# borrows a masthead it did not earn.
NAV = [("home", "The record", "/app/"),
       ("search", "Search", "/app/s"),
       ("glossary", "The glossary", "/app/glossary/"),
       ("officials", "The votes", "/app/officials"),
       ("analytics", "The record drawn", "/app/analytics"),
       ("graph", "The issue graph", "/app/graph"),
       ("watching", "Still watching", "/app/watching"),
       ("press", "The press", "/app/press")]


def section_nav(current):
    items = "".join(
        f'<a class="navlink{" active" if k == current else ""}" href="{href}">'
        f'{esc(label)}</a>'
        for k, label, href in NAV)
    return f'<nav class="sectionnav" aria-label="Sections">{items}</nav>'




def masthead(current, manifest):
    """The broadsheet's chrome (specs/29): the thin top bar — the site's
    name with the keycap (byte-equal from brand/logos, never redrawn), the
    edition line, the READ stamp — then, on the front page, the nameplate
    with the municipality switch and the search spine; then the section
    line with its five reading words and one rust writing word. Off the
    front page the top bar's name is the way back and the spine stays on
    the search page."""
    from . import broadsheet as _bs
    top = _bs.topbar(manifest, current, _brand_mark())
    if current == "home":
        plate = _bs.nameplate(manifest, _EDITION.get("towns") or [], _bs.spine(_SPINE["tries"]))
    else:
        plate = ""
    return f"""<header class="masthead bs-masthead">
  {top}
  {plate}
  {_bs.primary_nav(current, _EDITION.get("towns") or [])}
</header>"""


def footer(manifest):
    ed = manifest.get("edition_date") or ""
    # The second way back to the picker. specs/17 §8 asks for re-choosable "at
    # any time", and a reader who has scrolled to the bottom of a four-hour
    # transcript should not have to scroll back up to leave a town. The anchor
    # works with JavaScript off, because it is only an anchor.
    again = ('<a class="scopelink" href="#scope">municipality — change</a>'
             if len(_EDITION.get("towns") or []) > 1 else "")
    return f"""<footer class="foot bs-foot">
  <span class="bs-footline"><span class="foot-mark">{_brand_mark()}</span>publicrecord.studio · designed and developed by Stephen Walter with
    <a href="https://brooklineinteractive.org">Brookline Interactive Group</a> &amp; Neighborhood AI</span>
  <span class="bs-footline">readers are never logged in, counted or followed ·
    <a class="cov" href="/app/covenant">the covenant</a> ·
    <a class="cov" href="/app/ai">Our AI Constitution</a> ·
    <a class="cov" href="/app/analytics">the record drawn</a> ·
    <a class="cov" href="/app/watching">still watching</a> ·
    <a class="cov" href="/app/press">the press · get the desktop app</a>
    {(" · " + again) if again else ""} · CC BY-SA 4.0
    <span class="ed">edition {esc(ed)} · v{esc(manifest.get('version',''))}</span></span>
</footer>"""


def shell(title, desc, canonical, body, current, manifest,
          og_image="", version="0", feed=None):
    # The banner slot rides in the markup rather than being minted by script so
    # it lands in one known place on every page — top of the main column, above
    # whatever the reader came for, which is the only position that can honestly
    # claim to have warned them before they read.
    slot = '<div class="scopebanner" id="scopebanner" hidden></div>'
    return (head(title, desc, canonical, og_image, version, feed)
            + masthead(current, manifest)
            + f'<main class="main paper" id="app">{slot}{body}</main>'
            + footer(manifest)
            + f'<script src="/app/app.js?v={esc(version)}"></script></body></html>')


# --------------------------------------------------------------------------
# pages
# --------------------------------------------------------------------------

def body_strip():
    """The public bodies this edition holds, as a filter — and, underneath it,
    as a plain sentence.

    Two renderings of one fact, and both ship. The chips are minted by app.js
    into the empty rail (they are stateful, so markup cannot honestly bake
    them); the sentence is real HTML and is what a reader with JavaScript off
    gets — not a dead control, but the same information in the form that still
    works. The counts come from the pressed meetings, so every body named here
    has at least one meeting behind it."""
    bodies = _EDITION.get("bodies") or []
    if not bodies:
        return ""
    named = " · ".join(
        f'{esc(b["body"] or "no body recorded")} <b>{b["meetings"]}</b>'
        for b in bodies)
    return f"""
  <section class="card bodycard">
    <span class="tag">the bodies on the record — filter what you see</span>
    <div class="bodyfilter" id="bodyfilter" role="group"
         aria-label="Filter by public body" hidden></div>
    <p class="bodylist" id="bodylist">{named}</p>
    <p class="hint">Filtering runs in your browser and touches nothing else.
      With JavaScript off this page lists the whole record — every meeting
      below stays readable either way.</p>
  </section>"""


def _brief_card(m):
    """A brief — a recent meeting as a small still + a one-line deck, in the
    briefs column. Same .mcard the scope filter already knows how to hide."""
    thumb = m.get("thumb") or ""
    return (f'<a class="mcard" href="/app/m/{m["pid"]}" '
            f'data-town="{esc(m.get("town", ""))}" data-body="{esc(m["body"])}">'
            + (f'<img loading="lazy" src="{esc(thumb)}" alt="" width="96" height="54">'
               if thumb else "")
            + f'<div class="mc-body"><span class="chip">{esc(m["body"] or "meeting")}</span>'
              f'<b>{esc(m["title"])}</b>'
              f'<span class="mc-meta">{esc(m["date"] or "undated")} · '
              f'{int(round((m.get("duration") or 0)/60))} min</span></div></a>')


def _start_label(m):
    """A start's label: the body and the day, never the whole title (a
    Brookline title runs to fifty characters and a button is not a headline)."""
    who = " ".join(x for x in (m.get("town", ""), m.get("body", "")) if x) or "meeting"
    return f'{who} · {m.get("date") or "undated"}'


def _story_paths(ms, stats, featured):
    """The front door to the making half (specs/24, after specs/23 A1): the
    two paths into a data story, side by side, as baked CONTENT in the paper
    palette — the record inviting, like the covenant line. Every start is an
    ordinary `/app/p#edit&tpl=…&ref=…` link the editor reads from the hash
    (JS-off follows it to the stub's honest hint); no button, no script, no
    studio class or hue (the byte-clean guard sweeps this page). Path one —
    one meeting, what happened — starts from the latest four meetings; path
    two — over time, how it moved — from the four issues with the longest
    reach. The roll-calls start and the papers the press built keep their
    place beneath."""
    loud = (stats or {}).get("loud") or []
    m_starts = "".join(
        f'<a class="btn sp-start" href="/app/p#edit&amp;tpl=meeting&amp;ref={_js_euc(m["pid"])}">'
        f'{esc(_start_label(m))}</a>' for m in ms[:4])
    i_starts = "".join(
        f'<a class="btn sp-start" href="/app/p#edit&amp;tpl=issue&amp;ref={_js_euc(i["slug"])}">'
        f'{esc(i["name"][:48])} · {n_of(i["n_meetings"], "meeting")}</a>' for i in loud[:4])
    cards = "".join(
        f'<a class="pf-card" href="/app/p?{esc(f["qs"])}">'
        f'<b>{esc(f["title"])}</b>'
        f'<span class="pf-sub">{esc(f["sub"])}</span></a>'
        for f in (featured or []))
    pressed = (f'''
    <div class="sp-pressed">
      <span class="kicker">or read {n_of(len(featured), "paper")} the press built from the record, each the shape of a path</span>
      <div class="pf-cards">{cards}</div>
    </div>''' if cards else "")
    return f'''  <section class="sp-paths" id="yourpaper" aria-labelledby="sp-hl">
    <span class="kicker sp-kick">your paper — be the editor</span>
    <h2 class="sp-hl" id="sp-hl">Now tell yours. Two ways in.</h2>
    <p class="sp-copy">The two stories above are the two ways into the record:
      one meeting, or one thread over time. Start from either, or from any
      meeting or issue, and the record drafts the story — the numbers, the
      moments, the votes, the pictures — with a receipt on every line. You
      write the note that says what it means. No account. Nothing uploaded.
      Your paper lives in your browser and in the link you send.</p>
    <div class="sp-two">
      <article class="sp-path">
        <span class="sp-num">path one — one meeting</span>
        <h3>What happened</h3>
        <p>One night, told whole: the lede, the meeting in numbers, the shape
          of the tape with its moments marked, the three moments that decided
          it, the roll calls, how it was framed, the filings — and your note.</p>
        <div class="sp-starts"><span class="sp-or">start from</span>{m_starts or '<span class="hint">no meeting pressed yet</span>'}</div>
      </article>
      <article class="sp-path">
        <span class="sp-num">path two — over time</span>
        <h3>How it moved</h3>
        <p>One issue, followed across every meeting it touched: its reach,
          what changed each time it came back, every roll call along the way,
          its first word and its latest — and your note.</p>
        <div class="sp-starts"><span class="sp-or">start from</span>{i_starts or '<span class="hint">the long view needs two read meetings</span>'}</div>
      </article>
    </div>
    <div class="sp-more">
      <a class="btn primary sp-blank" href="/app/p#edit">or start a blank paper →</a>
      <a class="btn" href="/app/p#edit&amp;tpl=rolls">the roll calls, watched</a>
    </div>{pressed}
  </section>
'''


def _examples(analytics, issues, n=6):
    """A few words worth trying: the record's widest issues first (the issue
    engine's names read as words a person would type — "Vision Zero",
    "Warrant Articles"), then the recurring transcript topics to fill, with
    the artifacts out. Short names only; a search box is not a headline."""
    from .charts import ARTIFACTS
    out = []
    have = lambda name: name.lower() in {o.lower() for o in out}
    for i in sorted(issues or [], key=lambda i: (-int(i.get("n_meetings") or 0), str(i.get("slug") or ""))):
        if len(out) >= n:
            break
        name = str(i.get("name") or "").strip()
        if name and len(name) <= 26 and name.lower() not in ARTIFACTS and not have(name):
            out.append(name)
    for t in ((analytics or {}).get("topics") or []):
        if len(out) >= n:
            break
        name = str(t.get("topic") or "").strip()
        if name and len(name) <= 26 and name.lower() not in ARTIFACTS and not have(name):
            out.append(name)
    return out[:n]


def page_topic(t, issues, manifest, base, analytics=None):
    """A topic story's own page — /app/topic/<slug>/ (specs/25 §2.3): the
    same story the front page leads with, at an address of its own, so the
    story travels as a link."""
    from . import story
    body = story.topic(t, base="/app", issues=issues,
                       examples=_examples(analytics, issues), own_page=False)
    title = f'How {t["town"]} talks about {t["name"]} — publicrecord.studio'
    desc = (f'“{t["q"]}” on {t["town"]}’s public record: {t["mentions"]} mentions across '
            f'{t["n_meetings"]} of {t["n_town_meetings"]} meetings — month by month, night by night, '
            f'with a supercut of every moment. Counted from the transcripts; no model wrote a line of it.')
    return shell(title, desc, f'{base}/app/topic/{t["slug"]}/', body, "home", manifest,
                 version=manifest["version"])


def page_home(meetings, issues, stats, manifest, base, featured=None, analytics=None, topics=None,
              stills=None, frontpages=None):
    """The front page — the civic broadsheet (specs/29 P0).

    In the order of board 1: the masthead with the municipality switch and
    the READ stamp and the search spine (both the shell's, on this page);
    tonight's tape — the frame large, the score of the night, the counted
    headline and lede, money named on the tape, the filmstrip; the year in
    tapes with its four chapters; four columns to delve into; how the talk
    flowed; the front pages the press built; this week; the threads; and
    the three doors into writing. Every picture is pressed SVG with its
    numbers beside it; every control is an anchor; with scripts off the page
    reads whole. web/broadsheet.py lays it out; web/story.py writes the
    words; web/charts.py draws."""
    from . import broadsheet as _bs
    body = _bs.page_body(meetings, issues, stats, base="/app", featured=featured,
                         analytics=analytics, topics=topics, stills=stills,
                         bodies_html=body_strip(), shared=frontpages)
    c = stats["counts"]
    return shell("The Public Record — publicrecord.studio",
                 f"{c['meetings']} meetings, {c['hours']} hours, {c['issues']} issues "
                 "tracked across the record — open in any browser.",
                 f"{base}/app/", body, "home", manifest, version=manifest["version"])


def page_glossary(meetings, manifest, base, counts=None):
    """The words the record uses, explained — /app/glossary/ (specs/27 §3.4).
    Content in the paper: every entry a plain definition, its sources, and
    the record's own count of it; the page says which half a model wrote."""
    from . import glossary
    return shell("The glossary — publicrecord.studio",
                 "The words the record uses — warrant article, free cash, override, docket — "
                 "in plain language, with their sources and how often the record says them.",
                 f"{base}/app/glossary/", glossary.body(meetings, "/app", counts), "glossary", manifest,
                 version=manifest["version"])


def page_meeting(m, manifest, base, terms=None):
    # where the tape ends — a link past it names no line (rowAt, app.js)
    tape_end = int(max([float(m.get("duration") or 0)]
                       + [float(s.get("end") or s.get("start") or 0) for s in m["segments"]]))
    # the transcript as a real document (JS-off complete)
    rows = []
    last_spk = None
    anchored = set()   # a second's anchor goes on its first line only: an id is one element's
    for i, s in enumerate(m["segments"]):
        t = float(s.get("start") or 0)
        spk = s.get("speaker") or ""
        head_spk = (f'<span class="spk">{esc(spk)}</span>'
                    if spk and spk != last_spk else "")
        last_spk = spk or last_spk
        # anchor id and data-t must floor to the SAME whole second, or a
        # deep-link's #t<sec> won't match its row. data-t carries the exact
        # start (for precise seek + Math.floor()==int(t)); NEVER the rounded
        # form — round(t,1) can cross an integer and break ~5% of deep-links.
        # (two lines that start in one second shared its id — a sweep of the
        # live pages found t116 four times; #t<sec> and rowAt land on the
        # second's first line either way, as a browser always did)
        anchor = "" if int(t) in anchored else f' id="t{int(t)}"'
        anchored.add(int(t))
        rows.append(
            f'<p class="seg"{anchor} data-t="{t}" data-i="{i}">'
            f'<a class="ts" href="#t{int(t)}">{hms(t)}</a> '
            f'{head_spk}<span class="sx">{esc(s.get("text"))}</span></p>')
    transcript = "\n".join(rows)
    # the tape's poster is the edition's own still when the press pressed
    # one (specs/29 §P0.2) — the page loads nothing from a third party;
    # a still-less press shows the town's colour and the play button
    thumb = m.get("still") or ""
    player = ""
    if m["source_kind"] == "youtube" and m["video_id"]:
        player = (f'<div class="player facade" data-video="{esc(m["video_id"])}" style="--town:{_charts_town_light(m.get("town"))}">'
                  + (f'<img src="{esc(thumb)}" alt="" class="pfacade-img">' if thumb else "")
                  + '<button class="playbtn" type="button" aria-label="Play (loads YouTube)">▶</button>'
                  '<span class="phint">tap to load the tape · nothing plays until you do</span></div>')
    else:
        player = ('<div class="player local"><p class="phint">the tape lives at '
                  'the station — this page is the meeting as a document.</p></div>')
    # the night, cut (specs/26 §2.1): the press's reels from this meeting's
    # moments — the loudest five, and one per kind — as the viewer's own
    # links; content in the paper palette, no button, no script
    from . import cuts as _cuts
    cut = _cuts.meeting_cuts(m)
    cut_html = ""
    if cut:
        kinds = ""
        for k in cut["kinds"]:
            count = str(k["n"]) if k["n"] == k["total"] else f'the first {k["n"]} of {k["total"]}'
            kinds += (f'<a class="btn mp-kind" href="{esc(k["url"])}">{esc(k["label"])} '
                      f'<span class="mp-kn">{count} · {hms(k["runtime"])}</span></a>')
        cut_html = (
            f'<section class="card mp-cut" id="cut"><span class="tag">the night, cut — reels the press made from this meeting’s moments</span>'
            f'<div class="tp-cut"><a class="btn primary tp-play" href="{esc(cut["loudest"]["url"])}">▶ the night in {hms(cut["loudest"]["runtime"])}</a>'
            f'<span class="tp-cutmeta">its {n_of(cut["loudest"]["n"], "loudest moment")}, in order · plays clip to clip · the link is the share</span></div>'
            + (f'<div class="mp-kinds"><span class="kicker">or one kind of moment</span>{kinds}</div>' if kinds else "")
            + '<p class="hint">Cut from the analyzer’s scored moments — a measurement, not a choice made for you. '
              'Open a reel and press <b>make this reel yours</b> to re-cut it; tick any moment or transcript line below to cut your own.</p></section>')
    # the meeting in words (specs/26 §2.3): the highlighter's word cloud, pressed
    # — each word a deep link to its first mention; with the script on, a
    # word finds every line that says it
    from highlighter import insight as _insight
    from . import charts as _charts
    words = _insight.word_freq(m.get("segments") or [], top=80) if m.get("segments") else []
    words_html = ""
    if words:
        from . import pictures as _pictures
        cloud = _charts.word_cloud(words, base="/app", href=lambda w: f'#t{int(float(w.get("t") or 0))}',
                                   each="each opens the tape at its first mention; with the script on, it finds every line that says it")
        words_html = (
            f'<section class="card mp-words" id="words"><span class="tag">the meeting in words — what was said most; '
            'press a word to find every line that says it</span>'
            + cloud
            + _pictures.take(f'm-{_pictures.key(m["pid"])}-words', cloud, f'The meeting in words — {m["title"]}',
                             f'/app/m/{m["pid"]}', hash_page=f'/app/m/{m["pid"]}', legend=_pictures.LEGEND["cloud"])
            + f'<p class="hint">“{esc(words[0]["word"])}” came up {n_of(int(words[0]["count"]), "time")}. Sized by how often; '
              'civic stopwords out. With JavaScript off, a word opens the tape at its first mention.</p></section>')
    langs = ""
    if m["tracks"]:
        opts = "".join(f'<option value="{esc(t["code"])}">{esc(t["name"])}</option>'
                       for t in m["tracks"])
        langs = ('<label class="langmenu">captions '
                 f'<select id="langsel"><option value="en">English</option>{opts}'
                 + ('<option value="ad">Described (AD)</option>' if m["ad"] else "")
                 + '</select></label>')
    summ = ""
    if m["summary"]:
        origin = ("AI summary" if (m["summary_origin"] or "").startswith("ai:")
                  else "summary")
        # a model's summary is rendered as a model's prose (receipts linked,
        # its Markdown read, never shown); an extractive one is the tape's own
        # sentences and reads the same way — plain, every receipt a link
        from . import charts as _charts
        said = _charts.receipt_paras(m["summary"], "", plain=not (m["summary_origin"] or "").startswith("ai:"))
        # a summary that renders to nothing (only syntax) presses no labeled box
        if said:
            summ = (f'<section class="card summary" id="summary"><span class="tag">{origin} — '
                    'supplements the official record</span>' + said + '</section>')
    # the reading, drafted (specs/24 §4): a model's three paragraphs — what
    # it meant, who moved it, what to watch — under the model's own name,
    # every receipt a link into the tape below; pressed only when a model
    # wrote them, beside the counted read, never instead of it
    draft = (m.get("analysis") or {}).get("draft") or None
    drafted = ""
    if draft and draft.get("text"):
        from . import charts as _charts
        drafted = _charts.receipt_paras(draft["text"], "")
    if drafted:
        # the jump bar's "the summary" lands here when no summary card stands
        # (the piece is built first: an f-string expression holds no backslash)
        draft_id = "" if summ else ' id="summary"'
        summ += (f'<section class="card summary draft"{draft_id}><span class="tag">the reading, drafted by a '
                 f'model — {esc(draft.get("origin") or "")}, labeled · what it meant, who moved it, '
                 'what to watch · check it against the tape</span>'
                 + drafted + '</section>')
    # the roll calls — who voted how, read from the record (officials only)
    votes_html = ""
    if m.get("votes"):
        vrows = []
        for v in m["votes"]:
            roll = "".join(
                f'<span class="rollent"><a href="#t{int(r.get("t", v["t"]))}">'
                f'{esc(r.get("name",""))}</a> {_rollcell(r.get("vote",""))}</span>'
                for r in (v.get("roll") or []))
            vrows.append(
                f'<div class="vrow"><a class="vhead" href="#t{int(v["t"])}">'
                f'<span class="ts">{hms(v["t"])}</span> {esc((v["motion"] or "")[:110])} '
                f'<span class="tally">{esc(v.get("tally",""))}</span> '
                f'<span class="outcome">{esc(v.get("outcome",""))}</span></a>'
                f'<div class="roll">{roll}</div></div>')
        votes_html = (
            '<section class="card ledger" id="votes"><span class="tag">the vote ledger — '
            'roll calls read from this meeting</span>'
            f'<div class="vledger">{"".join(vrows)}</div>'
            '<p class="hint">Read from the transcript; a name may be misheard — '
            'verify against the official minutes.</p></section>')
    # the analyzer's read — framing lenses (with drift), questions, tension
    an = m.get("analysis") or {}
    framing = (an.get("framing") or {})
    framing_html = ""
    if framing.get("lenses"):
        mx = max((l["count"] for l in framing["lenses"]), default=1) or 1
        DRIFT = {"rising": "↑ rising", "fading": "↓ fading", "steady": "· steady"}
        # no per-lens hue: publicrecord takes deep green only, so the bars are
        # the accent and the labels are ink — the lens is named, not colour-coded
        # (specs/20 §5). The counts and drift carry the difference.
        rows = "".join(
            f'<div class="lensrow"><span class="lenslabel">{esc(l["lens"])}</span>'
            f'<span class="lensbar"><i style="width:{round(100*l["count"]/mx)}%"></i></span>'
            f'<span class="lensn">{l["count"]}</span>'
            f'<span class="lensdrift">{DRIFT.get(l["drift"],"")}</span></div>'
            for l in framing["lenses"])
        framing_html = ('<section class="card" id="framing"><span class="tag">how the meeting '
                        'framed it — eight civic lenses, counted from its own '
                        'words</span>'
                        f'<div class="lenses">{rows}</div>'
                        '<p class="hint">Counted, not modeled — each lens is a '
                        'word list; drift compares the first half to the '
                        'second.</p></section>')
    questions_html = ""
    if an.get("questions"):
        byt = {}
        for q in an["questions"]:
            byt.setdefault(q.get("type", "information"), []).append(q)
        blocks = "".join(
            f'<div class="qgroup"><span class="qtype">{esc(t)}</span>'
            + "".join(f'<a class="qrow" href="#t{int(q["t"])}">'
                      f'<span class="ts">{hms(q["t"])}</span> {esc(q["text"])}</a>'
                      for q in qs[:8]) + '</div>'
            for t, qs in sorted(byt.items()))
        questions_html = ('<section class="card" id="questions"><span class="tag">the questions '
                          'asked — typed by what they ask about</span>'
                          f'<div class="qgroups">{blocks}</div></section>')
    # the town's paper for this meeting
    docs_html = ""
    if m.get("documents"):
        drows = "".join(
            (f'<a class="docrow" href="{esc(d["url"])}" target="_blank" rel="noopener">'
             if d.get("url") else '<div class="docrow">')
            + f'📄 <b>{esc(d.get("kind","document"))}</b> {esc((d.get("title") or "")[:70])}'
            + f' <span class="lmeta">{d.get("pages",0)} pp</span>'
            + ("</a>" if d.get("url") else "</div>")
            for d in m["documents"])
        docs_html = ('<section class="card" id="paper"><span class="tag">the town’s paper — '
                     'agendas, minutes, and packets for this meeting</span>'
                     f'<div class="docrows">{drows}</div></section>')
    # the Moments panel (specs/20 §6) — the analyzer's scored moments as cards,
    # each a deep link into the tape. Baked into the stub so it reads with
    # JavaScript off; app.js turns a click into a seek. The kinds differ by
    # their mono kicker, never by colour (the record takes deep green only).
    moments_html = ""
    if m.get("moments"):
        cards = ""
        for mo in m["moments"]:
            score = max(0.0, min(1.0, float(mo.get("score") or 0)))
            reason = mo.get("reason") or ""
            # the anchor carries the whole moment (end, kind, quote) so the reel
            # composer (specs/20 §6, P1) can build a clip from a tick without a
            # second fetch — and the card stays a plain deep link with JS off.
            cards += (
                '<div class="mo-card">'
                f'<a class="moment" href="#t{int(mo["t"])}" data-t="{mo["t"]}" '
                f'data-start="{mo.get("start", mo["t"])}" '
                f'data-end="{mo.get("end") or mo["t"]}" data-kind="{esc(mo["kind"])}" '
                f'data-quote="{esc(mo["quote"])}">'
                f'<div class="mo-head"><span class="ts">{hms(mo["t"])}</span>'
                f'<span class="mo-kind">{esc(mo["kind"])}</span></div>'
                f'<p class="mo-quote">{esc(mo["quote"])}</p>'
                + (f'<div class="mo-foot"><span class="mo-reason">{esc(reason)}</span>'
                   f'<span class="mo-score" title="salience {round(score*100)}%">'
                   f'<i style="width:{round(score*100)}%"></i></span></div>'
                   if reason or score else "")
                + '</a></div>')
        # a meeting with a tape has a publish kit (web/kit.py's gate); link it
        # from the moments it was cut from, so a producer can find it.
        kitlink = (
            f'<p class="hint"><a class="liveshere" href="/app/k/{esc(m["pid"])}">'
            '→ the publish kit for this meeting</a> — the clips worth cutting and '
            'draft copy, for a producer.</p>'
            if m.get("video_id") else "")
        moments_html = (
            '<section class="card moments" id="moments"><span class="tag">the moments — the '
            'analyzer’s scored read of this meeting; click one to jump the '
            'tape</span>'
            f'<div class="mo-grid">{cards}</div>'
            '<p class="hint">Scored, not chosen for you — the salience bar is a '
            'measurement, and every moment is a receipt into the transcript '
            'below. With JavaScript on, tick moments to compose a reel — and tick '
            'moments on other meetings too; a reel can span the record.</p>'
            f'{kitlink}'
            '</section>')
    meta = " · ".join([x for x in (m["body"], m["town"], m["date"] or "undated",
                                   f'{m["n_speakers"]} speakers' if m["n_speakers"] else "")
                       if x])
    # english is served from the transcript itself; per-language tracks below.
    # esc() the code into the href too — a local sidecar filename is
    # operator-controlled and the track-code regex ([^.]+) permits quotes/angle
    # brackets, so match the escaping the <option value> already does.
    tdl = "".join(f'<a class="dl" href="/app/tracks/{m["pid"]}/{esc(t["code"])}.vtt" download>{esc(t["name"])} .vtt</a>'
                  for t in m["tracks"])
    addl = (f'<a class="dl" href="/app/ad/{m["pid"]}.vtt" download>described .vtt</a>' if m["ad"] else "")
    # on this page (specs/26 §2.4): a jump bar of the sections this meeting
    # actually has — a four-hour tape is a long page, and orientation is
    # pressed prose, not chrome
    jumps = [("tape", "the tape", True), ("summary", "the summary" if 'class="card summary" id="summary"' in summ else "the reading", bool(summ)),
             ("cut", "the night, cut", bool(cut_html)), ("moments", "the moments", bool(moments_html)),
             ("votes", "the votes", bool(votes_html)), ("paper", "the town’s paper", bool(docs_html)),
             ("framing", "the framing", bool(framing_html)), ("questions", "the questions", bool(questions_html)),
             ("words", "in words", bool(words_html)), ("transcript", "the transcript", True),
             ("downloads", "downloads", True)]
    jumps.insert(1, ("score", "the shape of the tape", True))
    jump = ('<nav class="mp-jump" aria-label="on this page"><span class="kicker">on this page</span>'
            + "".join(f'<a href="#{k}">{esc(label)}</a>' for k, label, have in jumps if have) + '</nav>')
    # the words this meeting uses that the glossary explains (specs/27 §3.4) —
    # "what is a warrant article?" answered one press from the page
    if terms:
        jump += ('<p class="mp-terms"><span class="kicker">words this meeting uses</span> '
                 + " · ".join(f'<a href="/app/glossary/#{esc(t["slug"])}">{esc(t["term"])}</a>' for t in terms)
                 + ' — <a href="/app/glossary/">the glossary</a> says what they mean</p>')
    # the score as the jump bar (specs/29 board 4): the tape as a timeline —
    # decisions as dots, questions as ticks, tension in rust, the lens lanes —
    # click to seek with the script on, an anchor into the tape without it
    from . import charts as _charts
    score_html = (f'<section class="card bs-scorecard mp-score" id="score"><div class="bs-scorehead">'
                  f'<span class="kicker">the shape of the tape — click anywhere to jump</span>'
                  f'<span class="bs-legend">● a decision, sized by weight · | a question · ▮ tension · $ money named · the eight lanes: where each lens’s words fell</span></div>'
                  + _score_pic(m) + '</section>') if m.get("duration") else ""
    # find in this meeting (specs/26 §2.2, on the broadsheet): a real form
    # that searches the record without the script; with it, the transcript
    # folds to the lines that say the word (app.js wireFind adopts this form)
    find_html = ('<form class="mp-find bs-find" id="find" role="search" action="/app/s" method="get">'
                 '<label for="mp-q">Find in this meeting</label>'
                 '<input id="mp-q" type="search" name="q" placeholder="a word, a name, a street — every hit becomes a jump" autocomplete="off">'
                 '<button class="btn" type="submit">Find</button>'
                 '<span class="mp-findn" aria-live="polite"></span><div class="mp-found" hidden></div></form>')
    kick = " · ".join(x for x in (m["town"], m["body"]) if x)
    body = f"""
  <article class="meeting" data-pid="{esc(m["pid"])}" data-town="{esc(m["town"])}" data-body="{esc(m["body"])}" data-end="{tape_end}">
    <div class="mhead bs-mhead" style="--town:{_charts_town_color(m.get("town"))}">
      <span class="kicker bs-mkick">{esc(kick or "meeting")}</span>
      <h1>{esc(m["title"])}</h1>
      <div class="mmeta">{esc(meta)}</div>
      <div class="chips">{langs}
        <button class="btn cite-all" type="button" data-cite="all">⧉ Cite this meeting</button></div>
    </div>
    {jump}
    <div id="tape">{player}</div>
    {score_html}
    {find_html}
    {cut_html}
    {summ}
    {moments_html}
    {votes_html}
    {docs_html}
    {framing_html}
    {questions_html}
    {words_html}
    <div class="tbar" id="downloads">
      <span class="tag">transcript — select any line to Cite it, click a time to jump; ＋ on a line cuts it into your reel</span>
      <span class="dls">{tdl}{addl}
        <a class="dl" href="/app/m/{m["pid"]}/transcript.txt" download>transcript .txt</a>{f'<a class="dl" href="/app/kits/{esc(m["pid"])}.json" download>kit .json</a>' if (m.get("video_id") and cut) else ""}</span>
    </div>
    <div class="transcript" id="transcript">{transcript}</div>
    <p class="disclose">AI-touched surfaces are labeled; verify against the official record.
      The tape is embedded from YouTube, never rehosted.</p>
  </article>
"""
    desc = (f'{m["body"]} · {m["date"] or "undated"} · '
            f'{int(round((m["duration"] or 0)/60))} min · read on the record')
    og = f'{base}{thumb}' if thumb else ""
    return shell(m["title"], desc, f"{base}/app/m/{m['pid']}", body,
                 "memory", manifest, og_image=og, version=manifest["version"])


def _score_pic(m) -> str:
    """The meeting page's score, with its picture as a file (specs/28 §3.3)."""
    from . import charts as _charts
    from . import pictures as _pictures
    pic = _charts.score(m, base="/app", questions=True)
    return pic + _pictures.take(f'm-{_pictures.key(m["pid"])}-shape', pic, f'The shape of the tape — {m["title"]}',
                                f'/app/m/{m["pid"]}',
                                legend="a dot is a decision, sized by its weight; rust, pushback · a tick above, a question · $ a dollar figure · the eight lanes: where each lens’s words fell")


def _charts_town_color(town) -> str:
    from .charts import town_color
    return town_color(town)


def _charts_town_light(town) -> str:
    from .charts import town_light
    return town_light(town)


def page_meeting_txt(m):
    lines = [m["title"], m.get("date", ""), ""]
    for s in m["segments"]:
        spk = (s.get("speaker") + ": ") if s.get("speaker") else ""
        lines.append(f"[{hms(s.get('start') or 0)}] {spk}{s.get('text','')}")
    return "\n".join(lines)


def _milestone_html(pid, mm):
    """One milestone row — a roll-call vote (with its tally) or a decision."""
    if mm.get("kind") == "vote":
        tally = f' <span class="tally">{esc(mm.get("tally",""))}</span>' if mm.get("tally") else ""
        out = (f' <span class="outcome">{esc(mm["outcome"])}</span>'
               if mm.get("outcome") else "")
        return (f'<a class="milestone vote" href="/app/m/{pid}#t{int(mm["t"])}">'
                f'⬡ <span class="ts">{hms(mm["t"])}</span> {esc(mm["text"][:70])}'
                f'{tally}{out}</a>')
    return (f'<a class="milestone" href="/app/m/{pid}#t{int(mm["t"])}">'
            f'◆ <span class="ts">{hms(mm["t"])}</span> {esc(mm["text"][:70])}'
            + (f' <span class="outcome">{esc(mm["outcome"])}</span>' if mm.get("outcome") else "")
            + '</a>')


def _docs_html(pid, docs):
    """The document lane on a timeline node — the town's paper for this meeting,
    each cite page-numbered and linking to the portal PDF."""
    if not docs:
        return ""
    rows = []
    for d in docs:
        cites = "".join(
            f'<span class="cite">p.{c.get("page",0)} · {esc(c.get("text","")[:80])}</span>'
            for c in (d.get("cites") or [])[:2])
        link = (f'<a class="docn" href="{esc(d["url"])}" target="_blank" rel="noopener">'
                if d.get("url") else '<span class="docn">')
        end = "</a>" if d.get("url") else "</span>"
        rows.append(f'{link}📄 {esc(d.get("kind","document"))} — '
                    f'{esc((d.get("title") or "")[:60])}{end}{cites}')
    return f'<div class="docs">{"".join(rows)}</div>'


def _rollcell(v):
    cls = {"yes": "y", "no": "n", "abstain": "a"}.get(v, "")
    label = {"yes": "aye", "no": "no", "abstain": "abs"}.get(v, esc(v))
    return f'<span class="rc {cls}">{label}</span>'


def _ledger_html(ledger):
    """The roll-call ledger for an issue — who voted how, each a receipt into
    the tape. Officials only (a roll call is the board voting)."""
    if not ledger:
        return ""
    rows = []
    for v in ledger:
        roll = "".join(
            f'<span class="rollent"><a href="/app/m/{v["pid"]}#t{int(r.get("t",v["t"]))}">'
            f'{esc(r.get("name",""))}</a> {_rollcell(r.get("vote",""))}</span>'
            for r in v.get("roll", []))
        rows.append(
            f'<div class="vrow"><a class="vhead" href="/app/m/{v["pid"]}#t{int(v["t"])}">'
            f'<span class="ts">{esc(v["date"] or "")}</span> {esc((v["motion"] or "")[:100])} '
            f'<span class="tally">{esc(v.get("tally",""))}</span> '
            f'<span class="outcome">{esc(v.get("outcome",""))}</span></a>'
            f'<div class="roll">{roll}</div></div>')
    return (f'<section class="card ledger"><span class="tag">the vote ledger — '
            f'roll calls on this issue, read from the record</span>'
            f'<div class="vledger">{"".join(rows)}</div>'
            f'<p class="hint">Roll calls are read from the transcript and may '
            f'mishear a name — verify against the official minutes.</p></section>')


def page_issue(i, manifest, base):
    nodes = []
    for n in i["timeline"]:
        beads = "".join(
            f'<a class="bead" href="/app/m/{n["pid"]}#t{int(b["t"])}">'
            f'<span class="ts">{hms(b["t"])}</span> {esc(b["text"][:90])}</a>'
            for b in n["beads"][:6])
        miles = "".join(_milestone_html(n["pid"], mm)
                        for mm in n.get("milestones", []))
        docs = _docs_html(n["pid"], n.get("documents", []))
        nodes.append(
            f'<div class="tnode"><div class="tdot"></div>'
            f'<div class="thead"><span class="tdate">{esc(n["date"] or "undated")}</span>'
            f'<a class="ttitle" href="/app/m/{n["pid"]}">{esc(n["body"] or n["title"])}</a>'
            f'<span class="tn">{n["n"]} moment(s)</span></div>'
            f'<div class="beads">{beads}{miles}</div>{docs}</div>')
    origin = ("Named by a model" if (i["name_origin"] or "").startswith("ai:")
              else "Named from the record's own words")
    aliases = "".join(f'<span class="alias">{esc(a)}</span>' for a in i["aliases"])
    related = "".join(f'<span class="rel">{esc(r)}</span>' for r in i["related"])
    ledger = _ledger_html(i.get("ledger", []))
    # said alongside it (specs/29 board 6): the press's count, each phrase a
    # search within the issue's own meetings — web/beside.py, the reader's twin
    from . import charts as _charts
    chips = _charts.beside_chips(i.get("beside") or [], [n["pid"] for n in i["timeline"]], base="/app")
    beside = (f'<section class="card pb-beside-card"><span class="tag">said alongside it — the phrases in the same breath</span>{chips}'
              f'<p class="hint">counted in every line the record filed under this issue and the line either side; '
              f'its own names are left out, and so is any other name the record does not already list — a name is '
              f'known by its capitals, so one made only of everyday words can slip through, and a phrase with a word '
              f'the record has rarely heard is held back too; each opens the record’s search for the phrase within '
              f'the issue’s own meetings</p></section>'
              if chips else "")
    body = f"""
  <article class="issue">
    <a class="back" href="/app/">← the record</a>
    <h1>{esc(i["name"])}</h1>
    <div class="idisclose">{origin} · tracked across {n_of(i["n_meetings"], "meeting")} ·
      officials-only aggregation · supplements the official record</div>
    <div class="ichips">{aliases}{related}</div>
    <p class="feedlink"><a href="/app/feeds/{i["slug"]}.xml">☉ follow by RSS</a></p>
    <section class="card"><span class="tag">the long view — every meeting this issue touched</span>
      <div class="timeline">{nodes and "".join(nodes) or '<p class="hint">no appearances</p>'}</div>
    </section>
    {beside}
    {ledger}
  </article>
"""
    desc = (f'“{i["name"]}” — {n_of(i["n_meetings"], "meeting")}, {n_of(i["n_segments"], "moment")} '
            f'on the record, {(i["first_seen"] or "")[:4]}–{(i["last_seen"] or "")[:4]}')
    return shell(f'{i["name"]} — the long view', desc,
                 f"{base}/app/i/{i['slug']}", body, "memory", manifest,
                 version=manifest["version"],
                 feed={"href": f"/app/feeds/{i['slug']}.xml",
                       "title": f'“{i["name"]}” — the long view (RSS)'})


def page_tombstone(slug, name, date, manifest, base):
    """A citation to an issue a steward curated away resolves to an explanation,
    never a bare 404 (specs/20 §6). The date is stored audit state, pressed
    idempotently — never a wall clock. This pays the debt specs/19 R1.7 named:
    control-z.org/app still carries a page publicrecord correctly dropped."""
    when = f" on {esc(date)}" if date else ""
    body = f"""
  <section class="tombstone">
    <a class="back" href="/app/">← the record</a>
    <h1>{esc(name) or "This issue"}</h1>
    <p class="presslede">This issue was <b>removed from the record by a
      steward{when}</b>. The record is curated in public: a steward may fold one
      issue into another or, rarely, forget one entirely. The meetings it
      gathered are all still on the record — only this grouping of them was
      withdrawn.</p>
    <p class="hint"><a href="/app/">Browse the record</a> ·
      <a href="/app/s">search it</a> · <a href="/app/covenant">the covenant</a>.</p>
  </section>
"""
    return shell(f"{name or 'Removed'} — removed from the record",
                 f"This issue was removed from the record by a steward{when}.",
                 f"{base}/app/i/{slug}", body, "", manifest,
                 version=manifest["version"])


def page_reel(manifest, base):
    """The reel viewer — /app/r (specs/20 §6/§7, P1). A shared reel lives
    entirely in its link (?v=1&m=<pid>&c=<start>-<end>,…); this page is the
    same static stub for every reel, and app.js decodes the link, fetches the
    meeting's own plane, and plays the sequence through the youtube-nocookie
    facade, clip to clip. No server, no reader state — the reel is in the URL
    and nowhere else.

    JS-off, a reel is just its citations, and a static page cannot read the
    query string to list them — so the honest fallback says exactly that, and
    sends the reader to the record where every moment reads in place. app.js
    replaces this with the decoded cite list (and the player) when it runs."""
    body = f"""
  <section class="reel" id="reel">
    <a class="back" href="/app/">← the record</a>
    <h1>A reel from the record</h1>
    <div class="reelstage" id="reelstage"></div>
    <div class="reelcites" id="reelcites">
      <p class="hint">Playing the reel — seeking the tape from clip to clip —
        needs JavaScript, and so does listing its clips (they live in the link,
        not on any page). With JavaScript off, open <a href="/app/">the
        record</a> or <a href="/app/s">search it</a> to read the moments in
        place.</p>
    </div>
    <p class="presslede">A <b>reel</b> is a short sequence of moments — roll
      calls, decisions, questions, the turns of an argument — pulled from the
      record, from one meeting or several, and strung together in order. The
      whole reel rides in the link that brought you here: which meetings, which
      moments, in what order. Nothing was uploaded, and nothing about you was
      kept.</p>
    <p class="disclose">The tape is embedded from YouTube, never rehosted.
      A reel of one meeting renders as a video at the desk — its reel.json
      opens in Highlighter, in <a href="{DESK_DMG}" rel="noopener">the desktop
      app</a>.</p>
  </section>
"""
    return shell("A reel — publicrecord.studio",
                 "A sequence of moments from one meeting on the record, played "
                 "clip to clip — the reel lives entirely in its link.",
                 f"{base}/app/r", body, "", manifest,
                 version=manifest["version"])


def _js_euc(s) -> str:
    """encodeURIComponent, byte for byte — one copy, in web/charts.py."""
    from .charts import js_euc
    return js_euc(s)


_BS_PART = {"week": "w", "threads": "k", "strip": "h", "names": "p"}   # app.js BS_PART, held equal by the codec twin


def _paper_qs(title, blocks) -> str:
    """The Python twin of app.js encodePaperQS, for the block kinds the press
    itself mints — stories and charts. (No reels: reel-shaped things demand
    play-testing against a real tape. No notes: a note is the editor's own
    words, and they are nobody's to pre-write.) v matches paperV exactly —
    v=2 the moment a chart or note rides along, v=1 only for stories+reels —
    so the shipped v1 reader degrades honestly on these links too."""
    parts = []
    for b in blocks:
        if b["kind"] == "story" and b["story"] == "meeting":
            parts.append("m." + _js_euc(b["pid"]))
        elif b["kind"] == "story" and b["story"] == "issue":
            parts.append("i." + _js_euc(b["slug"]))
        elif b["kind"] == "chart" and b["chart"] == "numbers":
            # a numbers chart names a meeting OR an issue — the ref says which
            parts.append("c.numbers." + _js_euc(
                ("m:" + b["pid"]) if b.get("pid") else ("i:" + b["slug"])))
        elif b["kind"] == "chart":
            ref = b.get("slug") or b.get("pid") or ""
            parts.append("c." + b["chart"] + (("." + _js_euc(ref)) if ref else ""))
        elif b["kind"] == "reading":
            parts.append("a." + _js_euc(
                ("m:" + b["pid"]) if b.get("pid") else ("i:" + b["slug"])))
        # specs/29 P1: the broadsheet's blocks — l.<pid>; w k h p bare, or
        # with t:<town> / (names) w:<who>; s — the reader's own grammar
        elif b["kind"] == "lead":
            parts.append("l." + _js_euc(b["pid"]))
        elif b["kind"] == "beside":
            parts.append("e." + _js_euc(b["slug"]))    # said alongside an issue (v=6)
        elif b["kind"] == "search":
            parts.append("s")
        elif b["kind"] in _BS_PART:
            scope = (("w:" + b["who"]) if b.get("who") else ("t:" + b["town"]) if b.get("town") else "")
            parts.append(_BS_PART[b["kind"]] + (("." + _js_euc(scope)) if scope else ""))
        else:
            # strict, like the store: a kind this builder does not know is a
            # link it would mint wrong, never a block silently dropped
            raise ValueError(f"_paper_qs: unknown block {b!r}")
    v4 = any(b["kind"] == "reading"
             or (b["kind"] == "chart" and (b["chart"] in ("numbers", "shape", "ledger")
                                           or (b["chart"] == "votes" and b.get("pid"))))
             for b in blocks)
    v = ("6" if any(b["kind"] == "beside" for b in blocks)
         else "5" if any(b["kind"] in ("lead", "search") or b["kind"] in _BS_PART for b in blocks)
         else "4" if v4 else "2" if any(b["kind"] in ("chart", "note") for b in blocks) else "1")
    qs = "v=" + v
    if title:
        qs += "&t=" + _js_euc(title)
    if parts:
        qs += "&b=" + ",".join(parts)
    return qs


# the press's own front pages carry this on their links (specs/29, decided
# 2026-09-24): the reader's decodePaper reads it as `by`, and the page says
# "the record's own, pressed nightly" instead of "shared as a link · the
# writer is not named". Never a block, never stored — a link's marker only.
PRESS_BY = "&by=press"


def featured_papers(meetings, issues, stats):
    """The front door's examples (specs/21 P3, settled with Stephen
    2026-07-22): two or three papers built at press time from the record's
    own top issues and votes, each an ordinary /app/p link — the same link
    form every paper travels as, no store, no state, nothing new to serve.
    Deterministic by construction (the pressed inputs only), so
    byte-idempotent presses hold. Every block is a ref into the record;
    the one free text is each paper's title, and it names only what the
    record itself holds."""
    out = []
    if any(m.get("votes") for m in meetings):
        blocks = [{"kind": "chart", "chart": "votes"},
                  {"kind": "chart", "chart": "framing"}]
        out.append({
            "title": "the roll calls, watched",
            "sub": "every roll call on the record, dot by dot — and how the "
                   "talk around them was framed",
            "qs": _paper_qs("the roll calls, watched", blocks) + PRESS_BY, "blocks": blocks,
        })
    loud = (stats or {}).get("loud") or []
    if loud:
        i = loud[0]
        # the JS title cap is 200 UTF-16 units; 95 code points + ", watched"
        # stays under it even if every code point were astral
        title = f'{i["name"][:95]}, watched'
        n = i.get("n_meetings") or 0
        # a young record's loudest issue may hold one meeting — "longest
        # thread across 1 meetings" would be both broken English and a boast
        sub = (f"the record's longest thread — one issue across {n} "
               "meetings: its numbers, its reach, every roll call along the "
               "way, and the record's reading") if n > 1 else \
              "one issue, tracked from its first appearance — its reach, its ledger, its reading"
        blocks = [{"kind": "story", "story": "issue", "slug": i["slug"]},
                  {"kind": "chart", "chart": "numbers", "slug": i["slug"]},
                  {"kind": "chart", "chart": "reach", "slug": i["slug"]},
                  {"kind": "chart", "chart": "ledger", "slug": i["slug"]},
                  {"kind": "reading", "slug": i["slug"]}]
        out.append({
            "title": title,
            "sub": sub,
            "qs": _paper_qs(title, blocks) + PRESS_BY, "blocks": blocks,
        })
    ms = sorted(meetings, key=lambda m: (m.get("date") or ""), reverse=True)
    if ms:
        m = ms[0]
        blocks = [{"kind": "story", "story": "meeting", "pid": m["pid"]},
                  {"kind": "chart", "chart": "numbers", "pid": m["pid"]},
                  {"kind": "chart", "chart": "shape", "pid": m["pid"]},
                  {"kind": "chart", "chart": "framing", "pid": m["pid"]},
                  {"kind": "reading", "pid": m["pid"]},
                  {"kind": "chart", "chart": "topics"}]
        out.append({
            "title": "the latest meeting, covered",
            "pid": m["pid"], "town": m.get("town") or "",
            "sub": f'{m.get("title") or m["pid"]} — as a story: its numbers, '
                   "its shape, its framing, the record's reading, and what "
                   "keeps coming back record-wide",
            "qs": _paper_qs("the latest meeting, covered", blocks) + PRESS_BY, "blocks": blocks,
        })
    return out


def page_frontpages(featured, frontpages, meetings, manifest, base, stills=None, towns=None):
    """The front pages (specs/29 P2, board 9): the record's own, pressed
    nightly, and readers' shared pages beside them — one card design for
    both, unsigned by design, judged by receipts; the filters are anchors
    the reader's script narrows the grid by, and the pressed page shows
    every card. web/gallery.py makes the cards and lays the page out."""
    from . import gallery as _g
    own = _g.own_cards(featured or [], meetings, stills or {}, "/app")
    body = _g.page_body(own, frontpages or [], (towns or {}).get("towns") or [], "/app")
    n = len(own) + len(frontpages or [])
    return shell("Front pages — publicrecord.studio",
                 f"{n} front pages of the public record — the record's own, pressed nightly, "
                 "and readers' shared pages beside them, each judged by its receipts.",
                 f"{base}/app/front-pages/", body, "paper", manifest, version=manifest["version"])


def page_paper(manifest, base, featured=None):
    """Your paper — /app/p (specs/21 §7, P1). A curated paper lives entirely
    outside the server: in its link (?v=1&t=<title>&b=<blocks>), in the
    browser's own draft, or — when the editor asked for a short link — at a
    content-addressed id (?p=<id>) the store serves back read-only. This page
    is the same static stub for every paper; app.js decodes whichever of those
    arrived, fetches the record's own planes for the stories and clips it
    references, and renders the paper in the quiet reading palette. The studio
    hue never reaches a rendered paper — the volume was the editor's, in their
    studio, and it stays there.

    P3 adds the featured papers: example links the press built from the
    record itself, server-rendered OUTSIDE #paperbody (the renderer owns that
    node's innerHTML and must never fight the stub for it). They belong to
    the empty state; app.js hides them the moment any paper renders. With
    JavaScript off they stand as plain pressed links — but rendering the
    paper a link carries still needs the reader's script, so a JS-off click
    lands back on this same stub, whose hint above the cards says exactly
    what is missing.

    JS-off, a paper cannot decode (it lives in the query string or the
    browser, which a static page cannot read) — so the honest fallback says
    exactly that and sends the reader to the record itself, where every story
    and moment reads in place."""
    feats = "".join(
        f'<a class="pf-card" href="/app/p?{esc(f["qs"])}">'
        f'<b>{esc(f["title"])}</b>'
        f'<span class="pf-sub">{esc(f["sub"])}</span></a>'
        for f in (featured or []))
    feat_html = f"""
    <div class="pfeat" id="pfeat">
      <div class="sectionhead"><span class="kicker">no paper in hand? three the press built</span></div>
      <p class="pf-lede">Examples pressed from the record itself — each an
        ordinary paper link, built the way any editor's is. Open one to read
        it; <a href="/app/p#edit">edit your own</a> to make one.</p>
      <div class="pf-cards">{feats}</div>
    </div>""" if feats else ""
    body = f"""
  <section class="paper-page" id="paperpage">
    <a class="back" href="/app/">← the record</a>
    <h1>A paper, edited from the record</h1>
    <p class="presslede">Everyone gets the record; a writer makes a front
      page of it. A <b>front page</b> is what somebody curated — a lead
      story, the week, the threads, how they talked, who and where, stories,
      reels, charts, pull-quotes, filings and what-changed digests of the
      public record they judged worth your attention, arranged, titled, and
      written under. Every block but the writer's paragraphs points back into
      the record itself: a pull-quote's words are read off the meeting's own
      transcript, a filing is the meeting's own document, and every picture
      is computed in your browser from the record's own planes. The
      paragraphs are the writer's own words, labeled as exactly that. Eight
      templates start one — a meeting, an issue over time, a vote and its
      history, a person, a place, two towns side by side, the year so far,
      or a blank broadsheet — each but the blank asking three questions the
      writer answers.</p>
    <div class="paperbody" id="paperbody">
      <p class="hint">Reading a paper, or editing your own, needs JavaScript:
        a paper lives in the link that brought you here, or in your own
        browser, not on any page a server could print, and the editor runs
        there too. With JavaScript off, open <a
        href="/app/">the record</a> or <a href="/app/s">search it</a> — every
        story a paper could cite reads there in full.</p>
    </div>{feat_html}
    <p class="disclose">A paper is its editor's selection, not the record's
      judgement — the full record is one link up. Papers travel as links and
      files; a short link is served from a content-addressed store that knows
      nothing about who reads it.</p>
  </section>
"""
    return shell("Your paper — publicrecord.studio",
                 "A curated front page of the public record — stories, reels, "
                 "charts, pull-quotes, filings and digests an editor arranged; "
                 "the record's blocks point back into the record, and a note "
                 "says whose words it is.",
                 f"{base}/app/p", body, "", manifest,
                 version=manifest["version"])


def _kit_card(k):
    """A kit in the index — a meeting's still + deck, linking to its kit."""
    meta = k.get("meta") or {}
    # the edition's own still, or the town's colour — never YouTube's poster
    # on a reader page (specs/29 §P0.2)
    thumb = meta.get("still") or ""
    n = len(k.get("clips") or [])
    return (f'<a class="mcard" href="/app/k/{esc(k.get("slug", ""))}" '
            f'data-town="{esc(meta.get("town", ""))}" '
            f'data-body="{esc(meta.get("body", ""))}">'
            + (f'<img loading="lazy" src="{esc(thumb)}" alt="" width="96" height="54">'
               if thumb else f'<span class="bs-nostill mc-nostill" style="background:{_charts_town_light(meta.get("town"))}"></span>')
            + f'<div class="mc-body"><span class="chip">{esc(meta.get("body") or "meeting")}</span>'
              f'<b>{esc(meta.get("title") or "Community program")}</b>'
              f'<span class="mc-meta">{esc(meta.get("date") or "undated")} · '
              f'{n} clip{"" if n == 1 else "s"}</span></div></a>')


def page_kits_index(kits, manifest, base):
    """The kits index — /app/k (specs/20 §6, §7.9 P2). Publisher's reading half:
    one entry per meeting that has a video and moments to publish. When an
    edition has none (nothing with a tape to cut), the page says so plainly
    rather than standing empty — the same honesty the /app/press door keeps."""
    if kits:
        cards = "".join(_kit_card(k) for k in kits)
        listing = f'<div class="kitgrid">{cards}</div>'
    else:
        listing = ('<p class="hint">No publish kits in this edition yet — a kit '
                   'is pressed for each meeting that has a tape to cut from. '
                   '<a href="/app/">Browse the record</a> in the meantime.</p>')
    body = f"""
  <section class="press">
    <a class="back" href="/app/">← the record</a>
    <div class="eyebrow"><span class="kicker">from Community Publisher</span></div>
    <h1>Publish kits</h1>
    <p class="presslede">A <b>publish kit</b> is what a producer needs to take a
      meeting out to the world: the clips worth cutting, and draft copy to ship
      them with — titles, a description, chapters — all assembled from the
      transcript, no model. Every kit here reads in the browser; <b>cutting the
      video and burning captions happen in Publisher at the desk</b>, and each
      kit downloads as a file that opens there.</p>
    <div class="presscta">{desk_button()}<span class="hint">Civic Media Studio {DESK_VERSION} — Publisher is in it</span></div>
    {listing}
    <p class="hint">Kits are drafts, not decisions — the analyzer scored the
      moments and the copy is lifted from the record itself. A producer edits
      the kit in <a href="/app/press#publisher">Community Publisher</a> before
      anything is published.</p>
  </section>
"""
    return shell("Publish kits — publicrecord.studio",
                 "A publish kit for every meeting: the clips worth cutting and "
                 "draft copy, assembled from the transcript.",
                 f"{base}/app/k", body, "", manifest,
                 version=manifest["version"])


def page_kit(kit, manifest, base):
    """One meeting's publish kit, read-only (specs/20 §6, §7.9 P2).

    Publisher's reading half: the clips (the moments plane, as cut candidates)
    and the draft copy, assembled from the transcript and labeled so. Rendering
    the clips — the one step that touches local media — stays at the desk, and
    the page says so. JS-off everything reads: the clips are server-rendered
    cards deep-linking the tape, the copy is real text, kit.json is a plain
    download, and 'play as a reel' is a link into the /app/r viewer (P1)."""
    meta = kit.get("meta") or {}
    slug = kit.get("slug") or ""
    pid = esc(meta.get("pid") or "")
    title = esc(meta.get("title") or "Community program")
    where = " · ".join(x for x in [meta.get("body"), meta.get("town"),
                                   meta.get("date")] if x)
    clips = kit.get("clips") or []
    copy = kit.get("copy") or {}

    cards = ""
    for c in clips:
        t = float(c.get("t", c.get("start", 0)) or 0)
        quote = esc(c.get("text") or c.get("label") or "")
        span = f'{hms(c.get("start", 0))}–{hms(c.get("end", 0))}'
        cards += (
            '<div class="mo-card">'
            f'<a class="moment" href="/app/m/{pid}#t{int(t)}" '
            f'data-t="{c.get("t", c.get("start", 0))}">'
            f'<div class="mo-head"><span class="ts">{hms(t)}</span>'
            f'<span class="mo-kind">{esc(c.get("kind") or "moment")}</span></div>'
            f'<p class="mo-quote">{quote}</p>'
            f'<div class="mo-foot"><span class="mo-reason">clip {esc(span)}</span></div>'
            '</a></div>')

    # 'play as a reel' hands the whole kit to /app/r (P1), which plays clip to
    # clip through the facade — the same clip encoding the composer writes.
    # `%g` matches app.js's r1() stringification (0.1-quantized, no trailing
    # ".0"), so a kit-page reel link is byte-identical to a composer share link.
    def _b(v):
        return "%g" % round(float(v or 0), 1)
    reel_clips = ",".join(f"{_b(c.get('start'))}-{_b(c.get('end'))}" for c in clips)
    reel_href = esc(f"/app/r?v=1&m={meta.get('pid', '')}&c={reel_clips}")
    kit_href = esc(f"/app/kits/{slug}.json")

    titles = copy.get("titles") or []
    title_opts = "".join(f'<li>{esc(t)}</li>' for t in titles)
    desc = esc(copy.get("description") or "").replace("\n", "<br>")
    origin = esc(copy.get("origin") or "")

    body = f"""
  <section class="press kit">
    <a class="back" href="/app/k">← all the kits</a>
    <div class="eyebrow"><span class="kicker">a publish kit — Community Publisher</span></div>
    <h1>{title}</h1>
    <p class="hint">{esc(where)}</p>
    <p class="presslede">The <b>publish kit</b> for this meeting: the clips worth
      cutting and draft copy to ship them with, assembled from the transcript.
      It reads here; <b>cutting the video, burning captions and choosing aspect
      ratios happen in Publisher at the desk</b>, against the program file on
      your own machine. Download the kit and open it there to carry on from this
      draft.</p>

    <div class="sectionhead"><span class="kicker">the clips — {len(clips)}</span></div>
    <div class="mo-grid">{cards}</div>
    <div class="presscta">
      <a class="btn primary" href="{reel_href}">▶ Play these clips as a reel</a>
      <a class="btn" href="{kit_href}" download>⬇ kit.json — open at the desk</a>
      {desk_button()}
      <a class="btn" href="/app/m/{pid}">Read the whole meeting →</a>
    </div>

    <div class="sectionhead"><span class="kicker">draft headlines</span></div>
    <ul class="kittitles">{title_opts}</ul>
    <div class="sectionhead"><span class="kicker">draft description</span></div>
    <p class="kitdesc">{desc}</p>
    <p class="hint">{origin}. Every line is a working draft — a producer edits it
      in Publisher before anything goes out.</p>

    <p class="disclose">The tape is embedded from YouTube, never rehosted.
      Rendering the clips as video needs the desk — this page composes, it does
      not cut. Community Publisher is
      <a href="{COMMUNITYAI}">a Community AI Project</a> tool.</p>
  </section>
"""
    return shell(f"{meta.get('title') or 'Publish kit'} — the kits · publicrecord.studio",
                 f"The publish kit for {meta.get('title') or 'this meeting'}: "
                 "clips and draft copy, assembled from the transcript.",
                 f"{base}/app/k/{slug}", body, "", manifest,
                 version=manifest["version"])


def _search_note() -> str:
    """What the search field promises, which differs by pressing.

    A desk edition genuinely has no server, and saying "vector search stays at
    the desk" is true there. On a Studio pressing it was a lie the page told
    for a month, so the sentence is now derived from the same fact the CSP is:
    whether this edition was pressed with an API behind it. app.js replaces it
    again at runtime if the API turns out to be unreachable — a promise made at
    press time cannot know that, and the reader deserves the live answer."""
    if _API["base"]:
        return ("Search reads the record two ways at once — the words you typed, "
                "and what they mean. Nothing about you is sent with the query.")
    return ("Search runs in your browser over a prebuilt lexical index — no "
            "query leaves this page. (Meaning-search needs the Studio.)")


def page_search(manifest, base, examples=None, topics=None):
    # The two filters are baked as real <select name=…> inside the form, so a
    # scoped search is a URL: /app/s?q=override&town=Brookline&body=Select+Board.
    # That is what makes a filtered result shareable, and it is why they are
    # form controls rather than script-minted chips — the search page is the
    # one surface where JavaScript is already load-bearing (the index is read
    # in the browser), so a control that submits a query string is honest here
    # in a way it would not be on the home page.
    towns = _EDITION.get("towns") or []
    bodies = _EDITION.get("bodies") or []
    tsel = ""
    if len(towns) > 1:
        opts = "".join(f'<option value="{esc(t["town"])}">{esc(t["town"])}</option>'
                       for t in towns)
        tsel = ('<label class="filt">town <select name="town" id="townsel">'
                f'<option value="">every town</option>{opts}</select></label>')
    bsel = ""
    if len(bodies) > 1:
        opts = "".join(
            f'<option value="{esc(b["body"])}">'
            f'{esc(b["body"] or "no body recorded")} ({b["meetings"]})</option>'
            for b in bodies)
        bsel = ('<label class="filt">body <select name="body" id="bodysel">'
                f'<option value="">every body</option>{opts}</select></label>')
    filters = (f'<div class="searchfilters">{tsel}{bsel}</div>'
               if (tsel or bsel) else "")
    # the empty state says what a search can do here (specs/25 §2.4): the
    # three steps, a few of the record's own words to try, the featured
    # story as the worked example — pressed prose, no script, no button
    from .charts import search_url as _surl
    tries = "".join(f'<a class="btn tp-try" href="{esc(_surl(str(x)))}">{esc(x)}</a>'
                    for x in (examples or [])[:6])
    worked = "".join(
        f'<a class="pf-card" href="/app/topic/{esc(t["slug"])}/"><b>How {esc(t["town"])} talks about {esc(t["name"])}</b>'
        f'<span class="pf-sub">the search for “{esc(t["q"])}”, told as a story — {t["mentions"]} mentions across '
        f'{t["n_meetings"]} meetings, month by month, with a supercut</span></a>' for t in (topics or []))
    guide = f'''
    <div class="sq-guide" id="sq-guide">
      <ol class="tp-steps">
        <li><b>Search a word.</b> A program, a street, a worry. Three letters is enough — the record searches as you type. Every hit is one line of one transcript, with its time.</li>
        <li><b>See how it was said.</b> The record counts every line that says it and draws the count: month by month, night by night, the words beside it. Nothing modeled; every number opens the tape.</li>
        <li><b>Cut it, share it.</b> Press <b>▶ play all</b> and the hits play as a reel. Press <b>＋ reel</b> on any hit to cut your own. The link is the share — no account, nothing uploaded.</li>
      </ol>
      {f'<p class="tp-tries"><span class="kicker">try one</span>{tries}</p>' if tries else ""}
      {f'<div class="sq-worked"><span class="kicker">a search, told as a story</span><div class="pf-cards">{worked}</div></div>' if worked else ""}
      <p class="sq-keys"><span class="kicker">keys</span> <kbd>/</kbd> search from any page · <kbd>j</kbd> <kbd>k</kbd> walk the hits · <kbd>enter</kbd> opens the tape · <kbd>c</kbd> cuts the hit under the cursor</p>
    </div>'''
    body = f"""
  <section class="searchpage bs-searchpage">
    <span class="kicker">Search a word over time</span>
    <h1>Search the record</h1>
    <form class="askform bs-searchform" id="searchform" action="/app/s" method="get">
      <input name="q" id="q" placeholder="a word, a name, a street, a vote…" aria-label="Search">
      <button class="btn primary" type="submit">Search</button>
    </form>
    {filters}
    <p class="hint" id="search-note">{_search_note()}</p>
    <div class="sq-prog" id="sq-prog" hidden aria-live="polite"><span class="sq-progbar"><i></i></span><span class="sq-progtext"></span></div>
    <div id="sq-story"></div>
    <div id="results"><noscript><p class="hint">Search needs JavaScript.
      <a href="/app/">Browse the record</a> instead — every meeting is a readable
      document with JavaScript off.</p></noscript></div>
    {guide}
  </section>
"""
    return shell("Search — the record", "Search everything the town has said.",
                 f"{base}/app/s", body, "search", manifest,
                 version=manifest["version"])


def page_add(manifest, base):
    body = """
  <section class="addpage">
    <a class="back" href="/app/">← the record</a>
    <h1>Add a meeting</h1>
    <p class="why">Paste a meeting's link. If it's already on the record, this
      walks you to it. If not, it composes a submission for the steward — a
      steward reviews; the record updates on the next pressing.</p>
    <form class="askform" id="addform">
      <input id="addurl" placeholder="https://youtube.com/watch?v=…  —or—  a meeting URL" aria-label="Meeting URL">
      <button class="btn primary" type="submit">Check the record</button>
    </form>
    <div id="addresult"></div>
    <details class="addcompose" id="addcompose" hidden>
      <summary>Compose a submission</summary>
      <div class="composebody">
        <label>Town <input id="ctown" placeholder="Brookline"></label>
        <label>Body <input id="cbody" placeholder="Select Board"></label>
        <label>Date <input id="cdate" placeholder="2026-06-18"></label>
        <label>Note <textarea id="cnote" placeholder="anything the steward should know"></textarea></label>
        <div class="composeacts">
          <a class="btn primary" id="c-github" target="_blank" rel="noopener">Open a GitHub submission</a>
          <button class="btn" id="c-copy" type="button">Copy submission JSON</button>
          <a class="btn" id="c-mail">Email the steward</a>
        </div>
      </div>
    </details>
  </section>
"""
    return shell("Add a meeting — the record",
                 "Paste a link; add a meeting to the town's record.",
                 f"{base}/app/add", body, "home", manifest,
                 version=manifest["version"])


def page_covenant(manifest, base):
    body = f"""
  <section class="covpage">
    <a class="back" href="/app/">← the record</a>
    <h1>The covenant, in public</h1>
    <p class="covai"><a class="btn" href="/app/ai">How this site uses AI — Our
      AI Constitution →</a></p>
    <ul class="covlist">
      <li><b>Static files only.</b> No backend, no compute, no accounts.</li>
      <li><b>No cookies, no analytics, no telemetry.</b> We will not know our
        reader count, and we ship anyway.</li>
      <li><b>Follows and your chosen town live in your browser</b>
        (localStorage, never a cookie — a cookie would ride every request and
        become the server's business); notifications are RSS.</li>
      <li><b>Embeds are click-to-load</b> (youtube-nocookie) — nothing plays,
        and no third party sees you, until you tap.</li>
      <li><b>No video rehosting.</b> Tapes are embedded or transcript-first; a
        meeting whose tape is a local file ships as a document.</li>
      <li><b>No person pages.</b> Officials-only aggregation is applied at press
        time; nothing about a private citizen is aggregated into an edition.</li>
      <li><b>Corrections annotate, never rewrite.</b> A takedown path reaches the steward.</li>
      <li><b>Anti-lock-in.</b> Every meeting downloads as transcript and every
        timeline as data — the record is yours to keep.</li>
      <li><b>Licensed to stay free.</b> AGPL-3.0 for the code, CC BY-SA 4.0 for
        the record — and below, in plain words, what that buys you.</li>
    </ul>
    <h2>What the licence means for you</h2>
    <p class="covwhy">Three different things are licensed here, and the
      difference matters more than the names do.</p>
    <ul class="covlist">
      <li><b>The meetings belong to the town.</b> They were public when they
        happened and they are public now. This site supplements the official
        record; it does not replace it, and it cannot become the only place the
        town's business can be found.</li>
      <li><b>The record on this site is CC BY-SA 4.0.</b> Anyone may copy it,
        quote it, republish it, or build something else on top of it — so long
        as they credit it and pass the same freedom on to whoever comes next.</li>
      <li><b>The software is AGPL-3.0</b> — a licence whose whole purpose is
        that a public thing stays public. The program that pressed this edition
        is published in full. Anyone can run their own copy: the town, the
        library, a neighbor with a laptop. And anyone who changes it and runs it
        as a service for other people owes those people the changed program too.
        So this record cannot be taken away, fenced off, or sold back to the
        town, and there is no version of it that quietly becomes somebody's
        product.</li>
    </ul>
    <p class="hint">The source is at
      <a href="{SOURCE_REPO}">github.com/amateurmenace/publicrecord-studio</a>; which
      licence covers which part, in full, is in
      <a href="{LICENSING_DOC}">LICENSING.md</a>.</p>
    <p class="hint">A strict Content-Security-Policy on every page enforces all
      of this in the browser: no third-party script, font, or beacon can load.</p>
    <p class="hint">This edition was pressed {esc(manifest.get('edition_date',''))}
      from a corpus fingerprinted {esc(manifest.get('corpus_hash',''))}.</p>
  </section>
"""
    return shell("The covenant — publicrecord.studio",
                 "Static files, no accounts, no tracking. The covenant in one screen.",
                 f"{base}/app/covenant", body, "", manifest,
                 version=manifest["version"])


def page_officials(officials, manifest, base):
    """The accountability page — every official's roll-call record, each cell a
    receipt into the tape. Officials only, by construction (specs/14 §8)."""
    cards = []
    for o in officials:
        # the 24 MOST-RECENT roll calls, newest first (member_records appends
        # oldest-first, so slice the tail and reverse — not the head)
        recent = "".join(
            f'<a class="vcell" href="/app/m/{v["pid"]}#t{int(v.get("t") or 0)}" '
            f'title="{esc((v.get("motion") or "")[:80])}">'
            f'{_rollcell(v.get("vote",""))}<span class="vc-date">{esc((v.get("date") or "")[5:])}</span></a>'
            for v in reversed(o.get("votes", [])[-24:]))
        cards.append(
            f'<div class="offcard" data-town="{esc(o.get("town", ""))}">'
            f'<div class="offhead"><b>{esc(o["name"])}</b>'
            f'<span class="lmeta">{esc(o.get("town",""))}</span></div>'
            f'<div class="offtally"><span class="rc y">{o["yes"]} aye</span>'
            f'<span class="rc n">{o["no"]} no</span>'
            f'<span class="rc a">{o["abstain"]} abs</span>'
            f'<span class="offtot">{o["total"]} recorded votes</span></div>'
            f'<div class="vcells">{recent}</div></div>')
    body = f"""
  <section class="officials">
    <a class="back" href="/app/">← the record</a>
    <h1>The people's votes</h1>
    <p class="why">Every roll call the record has read, by member. These are the
      votes officials cast in public session — officials only, by construction:
      a roll call is the board voting. Each cell links to the moment on the tape.
      Read from the transcript; verify against the official minutes.</p>
    <div class="offgrid">{"".join(cards) or '<p class="hint">no roll calls on the record yet</p>'}</div>
  </section>
"""
    return shell("The people's votes — the record",
                 "Every official's roll-call record, each cell a receipt into the tape.",
                 f"{base}/app/officials", body, "officials", manifest,
                 version=manifest["version"])


def page_analytics(analytics, manifest, base):
    """The record, drawn — the desk's Library made static: the eight civic
    framing lenses per meeting, the topics that recur, the names that keep
    appearing. Every mark links to its meeting. JS-off complete."""
    order = analytics.get("lens_order", [])
    color = analytics.get("lens_color", {})
    fm = analytics.get("framing", [])
    # framing heatmap: meetings × lenses, cell shade = share of that meeting
    head = "".join(f'<th>{esc(n)}</th>' for n in order)
    body_rows = []
    for r in fm:
        tot = r.get("total", 0) or 1
        # the green tint scale (specs/20 §5): a darker deep-green is a bigger
        # share; the lens hues never come near this domain. The count reads at
        # AA (4.5:1 at this size) on every cell: dark ink to 0.56, white from
        # 0.62, and a cell between — where neither ink reads — takes the
        # darker 0.62 (a sweep's catch: white flipped in at 0.46 and read 2.9:1)
        cells = ""
        for n in order:
            cnt = r["lenses"].get(n, 0)
            a = round(0.05 + 0.9 * min(1, cnt / tot * 4), 2)
            if 0.56 < a < 0.62:
                a = 0.62
            ink = "#ffffff" if a >= 0.62 else "#0f172a"
            cells += (f'<td style="background:rgba(5,46,22,{a});color:{ink}" '
                      f'title="{esc(n)}: {cnt}">{cnt or ""}</td>')
        body_rows.append(
            f'<tr><th class="fmlbl"><a href="/app/m/{r["pid"]}">'
            f'{esc((r["date"] or "?")[:10])} · {esc((r["body"] or r["title"])[:26])}</a></th>{cells}</tr>')
    heat = (f'<table class="heat"><thead><tr><th></th>{head}</tr></thead>'
            f'<tbody>{"".join(body_rows)}</tbody></table>') if fm else \
        '<p class="hint">the framing map needs a read meeting</p>'
    # topics that recur across meetings
    topics = "".join(
        f'<a class="trow" href="/app/m/{t["meetings"][0]["pid"]}#t{int(t["meetings"][0].get("t") or 0)}">'
        f'<b>{esc(t["topic"])}</b>'
        f'<span class="lmeta">{len(t["meetings"])} meetings · {t["count"]} mentions</span></a>'
        for t in analytics.get("topics", [])[:24])
    # recurring names
    names = "".join(
        f'<a class="nrow" href="/app/m/{n["meetings"][0]["pid"]}#t{int(n["meetings"][0].get("t") or 0)}">'
        f'<span class="nkind nk-{esc(n["kind"][:3])}"></span><b>{esc(n["name"])}</b>'
        f'<span class="lmeta">{len(n["meetings"])} meetings · {n["count"]}×</span></a>'
        for n in analytics.get("names", [])[:30])
    body = f"""
  <section class="analytics">
    <a class="back" href="/app/">← the record</a>
    <h1>The record, drawn</h1>
    <p class="why">Every read meeting as one picture — how the town framed what
      it discussed, the topics that keep returning, and the names that recur.
      Counted from the record's own words; every mark opens its meeting.</p>
    <section class="card"><span class="tag">civic framing — meetings down, lenses across</span>
      <div class="heatwrap">{heat}</div>
      <p class="hint">A darker cell is a bigger share of that meeting's framing —
        the green scale is measurement, and these are measurements.</p></section>
    <div class="grid2">
      <section class="card"><span class="tag">topics that recur across the record</span>
        <div class="trows">{topics or '<p class="hint">nothing recurs yet</p>'}</div></section>
      <section class="card"><span class="tag">names across two or more meetings</span>
        <div class="nrows">{names or '<p class="hint">no name recurs yet</p>'}</div></section>
    </div>
  </section>
"""
    return shell("The record, drawn — publicrecord.studio",
                 "The town's meetings as one picture — framing, topics, and names "
                 "counted across the record.",
                 f"{base}/app/analytics", body, "analytics", manifest,
                 version=manifest["version"])


def page_graph(graph, manifest, base):
    """The issue graph — issues that share meetings, drawn as the network they
    are. A hand-laid ring of nodes with weighted chords; SVG, no libraries, so
    the strict CSP holds. JS-off it's a readable ring; app.js adds hover."""
    import math
    nodes = graph.get("nodes", [])
    edges = graph.get("edges", [])
    W = 760
    R = 300
    cx = cy = W / 2
    n = len(nodes)
    pos = []
    for i in range(n):
        a = -math.pi / 2 + 2 * math.pi * i / max(1, n)
        pos.append((round(cx + R * math.cos(a), 1), round(cy + R * math.sin(a), 1)))
    idx = {node["slug"]: i for i, node in enumerate(nodes)}
    mxw = max((e["weight"] for e in edges), default=1) or 1
    lines = "".join(
        f'<line x1="{pos[idx[e["a"]]][0]}" y1="{pos[idx[e["a"]]][1]}" '
        f'x2="{pos[idx[e["b"]]][0]}" y2="{pos[idx[e["b"]]][1]}" '
        f'stroke="#052e16" stroke-opacity="{0.12 + 0.5*e["weight"]/mxw:.2f}" '
        f'stroke-width="{0.5 + 2.5*e["weight"]/mxw:.1f}"/>'
        for e in edges if e["a"] in idx and e["b"] in idx)
    mxm = max((node["n_meetings"] for node in nodes), default=1) or 1
    dots = ""
    labels = ""
    for i, node in enumerate(nodes):
        x, y = pos[i]
        r = 3 + 7 * node["n_meetings"] / mxm
        dots += (f'<a href="/app/i/{esc(node["slug"])}">'
                 f'<circle cx="{x}" cy="{y}" r="{r:.1f}" fill="#052e16" '
                 f'fill-opacity=".82"><title>{esc(node["name"])} · '
                 f'{n_of(node["n_meetings"], "meeting")}</title></circle></a>')
        # label just outside the ring, anchored by side
        lx = round(cx + (R + 14) * math.cos(-math.pi/2 + 2*math.pi*i/max(1, n)), 1)
        ly = round(cy + (R + 14) * math.sin(-math.pi/2 + 2*math.pi*i/max(1, n)), 1)
        anchor = "start" if lx >= cx else "end"
        labels += (f'<text x="{lx}" y="{ly}" text-anchor="{anchor}" '
                   f'font-size="10" fill="#475569" dominant-baseline="middle">'
                   f'{esc(node["name"][:22])}</text>')
    # the picture is widened by the longest name's overhang, so a name at the
    # ring's side is read whole (a sweep of the live graph: up to 35 px cut)
    # (each side by its own overhang — both by the larger shrank every name, a review catch)
    from . import charts as _charts
    left = right = 0.0
    for i, node in enumerate(nodes):
        lx = round(cx + (R + 14) * math.cos(-math.pi/2 + 2*math.pi*i/max(1, n)), 1)
        w = _charts.sans_w(node["name"][:22], 10)
        if lx >= cx:
            right = max(right, lx + w - W)
        else:
            left = max(left, w - lx)
    lpad, rpad = (math.ceil(v + 4) if v > 0 else 0 for v in (left, right))
    svg = (f'<svg viewBox="{-lpad} 0 {W + lpad + rpad} {W}" class="graphsvg" '
           f'xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="issue co-occurrence network">{lines}{dots}{labels}</svg>'
           if nodes else '<p class="hint">the graph needs issues that share meetings</p>')
    # a JS-off table twin (WCAG: every chart has a table twin)
    twin = "".join(
        f'<tr><td><a href="/app/i/{esc(e["a"])}">{esc(_gname(nodes, e["a"]))}</a></td>'
        f'<td><a href="/app/i/{esc(e["b"])}">{esc(_gname(nodes, e["b"]))}</a></td>'
        f'<td>{e["weight"]} shared</td></tr>' for e in edges[:60])
    body = f"""
  <section class="graphpage">
    <a class="back" href="/app/">← the record</a>
    <h1>The issue graph</h1>
    <p class="why">The town's concerns as the network they are: two issues are
      tied when they share meetings, and the tie thickens with every meeting
      they share. A bigger dot appears on more of the record. Tap a node to walk
      its long view.</p>
    <section class="card graphcard">{svg}</section>
    <details class="graphtwin"><summary>the same, as a table</summary>
      <table class="twin"><thead><tr><th>issue</th><th>issue</th><th>tie</th></tr></thead>
      <tbody>{twin or '<tr><td colspan="3">no ties yet</td></tr>'}</tbody></table>
    </details>
  </section>
"""
    return shell("The issue graph — publicrecord.studio",
                 "The town's issues drawn as the network they are — tied when "
                 "they share meetings.",
                 f"{base}/app/graph", body, "graph", manifest,
                 version=manifest["version"])


def _gname(nodes, slug):
    for n in nodes:
        if n["slug"] == slug:
            return n["name"]
    return slug


def page_still(manifest, base):
    """Still watching — the follows view. Follows live only in localStorage, so
    the body is a JS-rendered list with an honest noscript story."""
    body = """
  <section class="stillpage">
    <a class="back" href="/app/">← the record</a>
    <h1>Still watching</h1>
    <p class="why">The issues you follow, and what has changed on each since you
      last looked. Follows live in your browser — no account, nothing uploaded.</p>
    <div class="stilltools">
      <button class="btn" id="follow-export" type="button">Export follows (JSON)</button>
      <label class="btn" for="follow-import">Import follows<input id="follow-import" type="file" accept="application/json" hidden></label>
    </div>
    <div id="stilllist"><noscript><p class="hint">The still-watching view needs
      JavaScript to read your follows. <a href="/app/">Browse the record</a> —
      every issue timeline is a readable document, and each offers RSS.</p></noscript></div>
  </section>
"""
    return shell("Still watching — the record",
                 "The issues you follow, and what changed since you last looked.",
                 f"{base}/app/watching", body, "watching", manifest,
                 version=manifest["version"])


CREDIT = ("designed + developed by Stephen Walter with Brookline Interactive "
          "Group &amp; Neighborhood AI · CC BY-SA 4.0")


def _tool_row(t, lives_here=None):
    """A tool's one-line entry. `lives_here` defaults to the registry's static
    link, but a caller can pass one the registry can't know at import time — the
    Publisher row's cross-link into /app/k, say, which is honest only in an
    edition that actually pressed kits (specs/20 §7.9: the door stays honest
    until then)."""
    lh = lives_here if lives_here is not None else t.get("lives_here")
    lives = ""
    if lh:
        lives = (f' <a class="liveshere" href="{esc(lh["href"])}">'
                 f'its work already lives here → {esc(lh["label"])}</a>')
    return (f'<div class="toolrow" id="{esc(t["id"])}">'
            f'<div class="toolname">{esc(t.get("long", t["name"]))}'
            f'<span class="tverb">{esc(t["verb"])}</span></div>'
            f'<div class="toolwhy">{esc(t["why_desk"] or t["one"])}{lives}</div>'
            f'</div>')


def page_ai(manifest, base):
    """The AI constitution — /app/ai. The one page that says, in full, when a
    model touches this record, whose model it is, where it runs, and what
    stands when it is gone. It exists because the program's argument
    (communityai.studio names AI; the products do not) owes the reader a
    disclosure surface at the product — total transparency at the point of
    use, in the record's own quiet register.

    Every claim on this page is checkable — the origin labels in the data,
    the fallbacks in the open source, the covenant beside it — because a
    constitution nobody can audit is a press release. Interactivity is
    native (details/summary receipts, anchors), so the page is complete with
    JavaScript off, like everything else in the paper."""
    from . import glossary as _glossary     # the glossary row names the glossary's own model
    diagram = """
    <svg class="aidiagram" viewBox="0 0 720 240" role="img"
         aria-label="Where models sit in the record's pipeline: the tape becomes
         a transcript (speech-to-text on our hardware only when official
         captions are missing); the transcript becomes the record (summaries
         drafted by a labeled model, everything else by open rules); the record
         reaches your reading (meaning search embeds your query; the keyword
         index answers without it). The ledger below carries the same facts as
         a table.">
      <g fill="none" stroke="#052e16" stroke-width="2">
        <rect x="8"   y="92" width="150" height="52" rx="4"/>
        <rect x="214" y="92" width="150" height="52" rx="4"/>
        <rect x="420" y="92" width="150" height="52" rx="4"/>
        <path d="M158 118 h48 m-10 -6 10 6 -10 6"/>
        <path d="M364 118 h48 m-10 -6 10 6 -10 6"/>
        <path d="M570 118 h48 m-10 -6 10 6 -10 6"/>
      </g>
      <g font-family="'IBM Plex Mono',monospace" font-size="14" fill="#191712"
         text-anchor="middle">
        <text x="83"  y="123">the tape</text>
        <text x="289" y="123">the transcript</text>
        <text x="495" y="123">the record</text>
        <text x="668" y="123" fill="#052e16" font-weight="700">you</text>
      </g>
      <g font-family="'IBM Plex Mono',monospace" font-size="11" fill="#4B473E">
        <g stroke="#059669" stroke-dasharray="4 3" fill="none">
          <path d="M186 60 v26"/><path d="M392 60 v26"/><path d="M598 60 v26"/>
        </g>
        <text x="186" y="40" text-anchor="middle">no captions? speech-to-text,</text>
        <text x="186" y="54" text-anchor="middle">our hardware</text>
        <text x="392" y="40" text-anchor="middle">summary drafted by a model —</text>
        <text x="392" y="54" text-anchor="middle">labeled, fallback stands alone</text>
        <text x="598" y="40" text-anchor="middle">meaning search embeds</text>
        <text x="598" y="54" text-anchor="middle">your query, nothing about you</text>
        <text x="360" y="200" text-anchor="middle">moments · reels · kits · papers · the front page — open rules, no model</text>
        <text x="360" y="222" text-anchor="middle" fill="#052e16">every dashed line is optional; the record reads with all of them gone</text>
      </g>
    </svg>"""
    body = f"""
  <section class="aipage">
    <a class="back" href="/app/">← the record</a>
    <h1>Our AI Constitution</h1>
    <p class="presslede">Making a tool once required permission — a degree, a
      department, a budget line. AI collapses the distance between wishing a
      tool existed and building it: anyone who understands a problem can now
      build the thing that meets it. Toolmaking, the oldest civic craft,
      becomes available to everyone. But that potential won't bend toward the
      public good on its own — not while the companies building AI are the only
      ones deciding what it's for. This page is what deciding for ourselves
      looks like: every place a model touches this record, named; every promise,
      checkable.</p>

    <a class="aiband" href="{COMMUNITYAI}">
      <span class="aiband-kicker">part of the Community AI Project</span>
      <span class="aiband-line">A live experiment in taking hold of AI and
        pointing it at civic life — open-source, locally-owned tools, deployed
        in real neighborhoods, so communities shape their own future rather
        than rent it. Read the whole argument at communityai.studio →</span>
    </a>

    <div class="sectionhead"><span class="kicker">the articles — what we
      promise, and how to check us</span></div>
    <ol class="ailist">
      <li><b>The record is the source.</b> Models summarize, find, and label;
        they never replace the transcript. Every AI-made line sits beside the
        record it came from, and points back to it.
        <details><summary>check it yourself</summary><p>Open any meeting: the
          summary is one labeled paragraph above the complete transcript, and
          every moment deep-links a timestamp on the tape.</p></details></li>
      <li><b>Disclosure at the point of use.</b> Anything a model wrote is
        labeled where you read it — “AI summary” on the page,
        <code>ai:&lt;model&gt;</code> in the data. Nothing AI-made is passed
        off as the record.
        <details><summary>check it yourself</summary><p>Every meeting's own
          plane (<code>meetings/&lt;id&gt;.json</code>) carries a
          <code>summary_origin</code> field: <code>ai:&lt;model&gt;</code>
          when a model drafted it, <code>extractive</code> when the sentences
          came from the transcript itself.</p></details></li>
      <li><b>Reading never requires AI.</b> Meaning search is an upgrade, not
        a dependency: when the model is off, the static keyword index answers
        and the page says so. Every page reads with every server gone.
        <details><summary>check it yourself</summary><p>Search the record,
          then search it again offline — the results say which index answered.
          The <a href="/app/covenant">covenant</a> holds the larger promise:
          static files only.</p></details></li>
      <li><b>Readers are never fed to models.</b> The models see public record
        text — transcripts, agendas, minutes — and, for search, the words of
        your query alone. Never anything about you: no account, cookie, or
        analytics exists here to share.
        <details><summary>check it yourself</summary><p>The
          <a href="/app/covenant">covenant</a> is enforced by a strict
          Content-Security-Policy on every page — no third-party script or
          beacon can load, and the search call carries no identity.</p></details></li>
      <li><b>People gate the record.</b> Nothing enters on a model's say-so: a
        steward approves every submitted meeting — in person, or by a standing
        rule the steward wrote for a channel they trust, which approves only a
        meeting YouTube's own list carries captions for; the record's audit
        names the rule the way it names a person. Corrections annotate, never
        rewrite. AI drafts; people decide.
        <details><summary>check it yourself</summary><p>Submit a meeting from
          <a href="/app/add">the add page</a> — the reply says a steward
          reviews it before the record updates. A standing rule reaches only
          the nightly poll of a channel a steward configured; it never touches
          what a person submits.</p></details></li>
      <li><b>Local first where it counts.</b> The desk tools run their models
        on your machine — noise reduction, voice isolation, rotoscoping — and
        nothing leaves the room. The hosted record uses a cloud model only
        where static files structurally cannot (embedding a search query at
        the moment you ask it), and names the model it uses.
        <details><summary>check it yourself</summary><p>Install the desk from
          <a href="/app/press">the press</a> — then unplug the network and cut
          a film. It all still works.</p></details></li>
      <li><b>Open to audit.</b> The code that pressed this page — prompts,
        gates, fallbacks — is public under AGPL-3.0, a license whose purpose
        is that a public thing stays public. A constitution nobody can audit
        is a press release.
        <details><summary>check it yourself</summary><p>The source is at
          <a href="{SOURCE_REPO}">github.com/amateurmenace/publicrecord-studio</a>;
          which license covers which part is in
          <a href="{LICENSING_DOC}">LICENSING.md</a>.</p></details></li>
      <li><b>Built with AI, signed by people.</b> This software is itself
        developed with AI assistance — the same collapse of distance we argue
        for is how a tiny shop built a record this size. Every change lands in
        a public commit a person reviewed and signed.
        <details><summary>check it yourself</summary><p>The commit history is
          public — the AI-assisted work is co-authored in the open, not
          laundered.</p></details></li>
    </ol>

    <div class="sectionhead"><span class="kicker">where the models sit</span></div>
    {diagram}

    <div class="sectionhead"><span class="kicker">the ledger — when, whose,
      where, and what stands without it</span></div>
    <div class="aitable-wrap"><table class="aitable">
      <thead><tr><th>where you meet it</th><th>what the model does</th>
        <th>whose model</th><th>where it runs</th><th>without it</th></tr></thead>
      <tbody>
        <tr><td>meaning search</td>
          <td>turns your query and the record's segments into vectors so
            related passages match</td>
          <td>Google <code>gemini-embedding-001</code></td>
          <td>our server, at the moment you search; it sees the query text
            and nothing about you</td>
          <td>the static keyword index answers, labeled “lexical”</td></tr>
        <tr><td>meeting summaries</td>
          <td>drafts one paragraph from the transcript</td>
          <td>Google Gemini (Flash) on the hosted lane — labeled
            <code>ai:&lt;model&gt;</code> in the data. A summary pressed
            before that lane existed names the desk model that drafted it
            (<code>ai:gpt-4o-mini</code>); the label is always the model
            that wrote the words</td>
          <td>our pipeline, at ingest, over public transcript text</td>
          <td>an extractive summary — sentences drawn from the transcript
            itself, labeled <code>extractive</code>. The same stands when a
            model's answer comes back cut off at its length limit: a fragment
            is refused, never pressed</td></tr>
        <tr><td>the reading, drafted</td>
          <td>drafts three short paragraphs — what the meeting meant, who
            moved it, what to watch — with a timestamp beside every claim</td>
          <td>Google Gemini (Flash) — labeled <code>ai:&lt;model&gt;</code>
            beside the text on the meeting page, the front page and in a
            paper’s reading block — and, since v2.2.1, the writing desk’s
            <em>a draft, if you want one</em> card, where the same pressed
            paragraphs are offered under the model’s name and join a page
            only when the writer adds them</td>
          <td>our pipeline, at ingest, over public transcript text</td>
          <td>the counted reading stands alone — decisions, questions, names
            and pushback drawn from the transcript by open rules; a draft cut
            off at its length limit is refused the same way</td></tr>
        <tr><td>the glossary</td>
          <td>wrote the plain definitions of the civic words the record uses —
            warrant article, free cash, override, docket — drawing on the
            public source each entry names</td>
          <td>Anthropic <code>Claude</code> (<code>{_glossary.MODEL}</code>) —
            labeled on the glossary’s own page, which says whether a person
            has read them yet</td>
          <td>Anthropic’s servers, through the coding assistant the developers
            used while writing this code — the text is in the open
            repository; never at press time, never in your browser. The counts
            beside each word are the press’s, and no model counts them</td>
          <td>the words, their counts and their sources stand; where an entry
            and its source differ the source is the authority, and a
            correction is dated beside the entry</td></tr>
        <tr><td>issue names &amp; labels</td>
          <td>suggests a plain name for a thread that spans meetings</td>
          <td>the model named in the issue’s own plane —
            <code>name_origin</code> says <code>ai:&lt;model&gt;</code>, or
            that the keywords named it. The names on the record today were
            drafted by OpenAI <code>gpt-4o-mini</code>
            (<code>ai:gpt-4o-mini</code>), and each issue page says “Named by
            a model”</td>
          <td>the desk, when a steward built the threads on their own key, and
            carried here by the import — never at press time, never in your
            browser. A rebuild on the hosted service carries no model key and
            names by keywords</td>
          <td>a keyword-derived name</td></tr>
        <tr><td>transcripts</td>
          <td>speech-to-text, only when a tape arrives with no official
            captions</td>
          <td>an open Whisper-family model</td>
          <td>our own hardware — the audio is never sent to a third party</td>
          <td>official captions are always preferred; a tape with neither
            ships as a document, not a guess</td></tr>
        <tr><td>moments · reels · kits · your paper · the front page</td>
          <td colspan="2"><b>no model at all</b> — open keyword rules and
            extraction, readable in the source</td>
          <td>your browser, or press time</td>
          <td>they are the fallback</td></tr>
        <tr><td>the desk — <a href="https://civicmedia.studio">civicmedia.studio</a>
            / <a href="https://control-z.org">Control-Z</a></td>
          <td>noise reduction, voice isolation, rotoscoping, film emulation</td>
          <td>open models, bundled with the app</td>
          <td><b>your machine only</b> — offline works; no account, no cloud,
            nothing leaves the room</td>
          <td>they are the tool</td></tr>
      </tbody>
    </table></div>

    <div class="sectionhead"><span class="kicker">use AI that stays local</span></div>
    <p class="aip">The record is the reading half; the making half is a desk of
      free, open-source tools whose models run entirely on your computer.
      Community media stations, filmmakers, and neighbors finish real work with
      them — denoise a meeting tape, isolate a voice, cut a reel into a film —
      with the network cable out of the wall. That is what “locally-owned AI”
      means here: not a slogan, a download.
      <a href="/app/press">Get the desk from the press →</a></p>
    <div class="presscta">{desk_button()}<span class="hint">Civic Media Studio {DESK_VERSION} · macOS · Apple silicon</span></div>

    <div class="sectionhead"><span class="kicker">understand it deeper</span></div>
    <ul class="ailinks">
      <li><a href="{COMMUNITYAI}">communityai.studio</a> — the program's whole
        argument: why civic AI, why open source, why locally owned.</li>
      <li><a href="/app/covenant">the covenant</a> — the promises this site
        keeps about you, enforced in the browser.</li>
      <li><a href="{SOURCE_REPO}">the source</a> — every prompt, gate, and
        fallback named on this page, in the open.</li>
      <li><a href="https://www.elementsofai.com/">Elements of AI</a> — a free,
        plain-language university course; the best first step we know.</li>
      <li><a href="https://www.youtube.com/watch?v=wjZofJX0v4M">But what is a
        GPT?</a> — 3Blue1Brown's visual walk through how language models
        actually work.</li>
      <li><a href="https://www.eff.org/issues/artificial-intelligence">EFF on
        AI</a> — the civil-liberties view: rights, risks, and policy.</li>
    </ul>

    <p class="hint">This page is made to be shared — the direct link is
      <a href="{esc(base)}/constitution"><b>{esc(base.replace('https://', '').replace('http://', ''))}/constitution</b></a>.
      This edition was pressed {esc(manifest.get('edition_date',''))}
      from a corpus fingerprinted {esc(manifest.get('corpus_hash',''))}. When our
      use of AI changes, this page changes in the same commit.</p>
  </section>
"""
    return shell("Our AI Constitution — publicrecord.studio",
                 "When a model touches this record, whose model it is, where "
                 "it runs, and what stands when it is gone — every promise "
                 "checkable, part of the Community AI Project.",
                 f"{base}/app/ai", body, "", manifest,
                 version=manifest["version"])


def page_constitution_alias(manifest, base):
    """The shareable spelling — /app/constitution redirects to /app/ai (the
    page_door_stub pattern: meta-refresh, CSP-safe, a real link beneath).
    Its root-level twin (publicrecord.studio/constitution) is a hand-file in
    the Pages repo, outside the pressed app/ — OPERATING §5 lists it."""
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{csp()}">
<meta http-equiv="refresh" content="0; url=/app/ai/">
<title>Our AI Constitution — publicrecord.studio</title>
<meta name="description" content="When a model touches this record, whose it
  is, where it runs, and what stands without it — every promise checkable.">
<link rel="canonical" href="{esc(base)}/app/ai">
<link rel="stylesheet" href="/app/app.css?v={esc(manifest['version'])}">
</head><body>
<main class="main paper"><section class="aipage">
  <h1>Our AI Constitution</h1>
  <p class="presslede">It lives at <a href="/app/ai/">publicrecord.studio/app/ai</a>
    — you are being redirected there.</p>
</section></main>
</body></html>"""


def page_press(manifest, base, has_kits=False):
    """The press behind the paper — one quiet page where the thirteen doors
    used to shout (specs/20 §5). The civicmedia story in three sentences, the
    tool list as one-line entries (name, verb, the true reason each needs the
    desk), the DMG, and the cross-link to communityai.studio done once.

    `has_kits` flips Publisher's line from "nothing yet" to a cross-link into
    /app/k, but only when this edition actually pressed kits — the door stays
    honest until then (specs/20 §6, §7.9)."""
    def row(t):
        if t["id"] == "publisher" and has_kits:
            return _tool_row(t, {"label": "a publish kit for every meeting",
                                 "href": "/app/k"})
        return _tool_row(t)
    suite = "".join(row(t) for t in tools.community()
                    if t["surface"] != "web")
    bench = "".join(_tool_row(t) for t in tools.workbench())
    body = f"""
  <section class="press">
    <a class="back" href="/app/">← the record</a>
    <h1>The press behind the paper</h1>
    <p class="presslede">The Public Record is the newspaper; <b>Civic Media
      Studio</b> is the press that makes it. The Studio is a desktop suite that
      fetches, transcribes, translates, describes and cuts civic video on your
      own machine — your files, your GPU, nothing uploaded. Everything those
      tools produce that can be <em>read</em> already lives here on the record;
      the tools themselves stay at the desk, because they touch local media and
      local compute — and below, for each one, is why.</p>
    <div class="sectionhead"><span class="kicker">the civic media suite</span></div>
    <div class="toollist">{suite}</div>
    <div class="sectionhead"><span class="kicker">control-z — the finishing tools</span></div>
    <div class="toollist">{bench}</div>
    <div class="presscta">
      {desk_button("↓ Get the desktop app — macOS", primary=True)}
      <span class="hint">Civic Media Studio {DESK_VERSION} · macOS 12+ · Apple silicon · signed &amp; notarized ·
        <a href="{DMG_LATEST}">every release →</a></span>
    </div>
    <p class="hint">Civic Media Studio and The Public Record are
      <a href="{COMMUNITYAI}">a Community AI Project</a> — {CREDIT}.</p>
  </section>
"""
    return shell("The press — publicrecord.studio",
                 "Civic Media Studio, the desktop press that makes the record: "
                 "what each tool does, and why it lives at the desk.",
                 f"{base}/app/press", body, "press", manifest,
                 version=manifest["version"])


def page_door_stub(t, manifest, base):
    """A citation must never die (specs/20 §5). Every /app/t/<tool>/ URL the
    old doors answered survives as a slim redirect into /app/press#<tool> — a
    meta-refresh (CSP-safe, no inline script) with a real link underneath for
    the reader whose browser honours neither. No slide, no site/ asset, nothing
    to break."""
    dest = f"/app/press#{esc(t['id'])}"
    name = esc(t.get("long", t["name"]))
    return f"""<!doctype html>
<html lang="en"><head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="{csp()}">
<meta http-equiv="refresh" content="0; url={dest}">
<title>{name} — the press · publicrecord.studio</title>
<meta name="description" content="{name} is a desk tool; its page is on the press.">
<link rel="canonical" href="{esc(base)}/app/press#{esc(t['id'])}">
<link rel="stylesheet" href="/app/app.css?v={esc(manifest['version'])}">
</head><body>
<main class="main paper"><section class="press">
  <h1>{name}</h1>
  <p class="presslede">{name} is a desk tool. Its page is now part of
    <a href="{dest}">the press</a> — you are being redirected there.</p>
</section></main>
</body></html>"""


# --------------------------------------------------------------------------
# assets + orchestration
# --------------------------------------------------------------------------

_VAR_RE = re.compile(r"--([a-z0-9-]+)\s*:\s*([^;]+);")
_COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)

# The two critical first-paint faces (body + headline) preloaded in <head>; the
# rest swap in. font-display:swap means the system stack is the visible
# fallback, never a blank. CSP stays font-src 'self' — every byte is ours.
_FONTS = [
    # (family, weight or range, style, file) — the broadsheet's three faces
    ("Fraunces", "300 700", "normal", "fraunces-300-700"),
    ("Fraunces", "300 700", "italic", "fraunces-italic-300-700"),
    ("IBM Plex Sans", "400 600", "normal", "plex-sans-400-600"),
    ("IBM Plex Mono", "400", "normal", "plex-mono-400"),
    ("IBM Plex Mono", "500", "normal", "plex-mono-500"),
]
_PRELOAD_FONTS = ["plex-sans-400-600", "fraunces-300-700"]
_FONT_FACES = "".join(
    f"@font-face{{font-family:'{fam}';font-style:{style};font-weight:{w};"
    f"font-display:swap;src:url('/app/fonts/{file}.woff2') format('woff2');}}"
    for fam, w, style, file in _FONTS)


def _brand_vars(name) -> dict:
    """Parse a brand token file into {var: value}, resolving one level of
    var() references within the same file. brand/ is the single source for the
    record's face (specs/20 §8) — values are read, never re-typed."""
    text = _COMMENT_RE.sub("", (BRAND / "tokens" / name).read_text(encoding="utf-8"))
    raw = {m.group(1): m.group(2).strip() for m in _VAR_RE.finditer(text)}
    def deref(v):
        m = re.fullmatch(r"var\(--([a-z0-9-]+)\)", v)
        return raw.get(m.group(1), v) if m else v
    return {k: deref(v) for k, v in raw.items()}


def _brand_inner(name) -> str:
    """The declarations inside a brand :root block, comments stripped — used
    verbatim for the type and spacing scales (no colour lives there)."""
    text = _COMMENT_RE.sub("", (BRAND / "tokens" / name).read_text(encoding="utf-8"))
    return " ".join(f"--{m.group(1)}:{m.group(2).strip()};"
                    for m in _VAR_RE.finditer(text))


def _brand_tokens() -> str:
    """The publicrecord :root — the civic broadsheet's set (specs/29), drawn
    byte-faithfully from brand/tokens/broadsheet.css: paper and ink, rust for
    writing, a municipality's colour for what belongs to it, and the three
    faces. The semantic names the stylesheet has always used (--surface-page,
    --text-primary, --accent, --state…) are kept and re-pointed, so every
    older rule reads on paper without being re-typed. The pop accents
    (fuchsia, purple) and the desk palette never enter this file — the
    stylesheet has to prove it: no forbidden hex ever appears."""
    b = _brand_vars("broadsheet.css")
    colours = (
        f"--surface-page:{b['paper']};--surface-card:{b['paper-card']};"
        f"--surface-inverse:{b['ink-record']};"
        f"--text-primary:{b['ink-record']};--text-secondary:{b['ink-2']};"
        f"--text-muted:{b['ink-muted']};--text-inverse:{b['paper']};"
        f"--border-hairline:{b['rule']};--border-strong:{b['ink-muted']};"
        # measurement and controls are ink; rust is the one action colour and
        # the state light (the focus ring keeps its --state fallback)
        f"--accent:{b['ink-record']};--state:{b['rust']};--write:{b['rust']};--write-light:{b['rust-light']};--live:{b['ink-2']};"
        f"--paper:{b['paper']};--card:{b['paper-card']};--rule:{b['rule']};--rust:{b['rust']};"
        f"--ink:{b['ink-record']};--ink-2:{b['ink-2']};--muted:{b['ink-muted']};"
        f"--boston:{b['boston']};--boston-light:{b['boston-light']};"
        f"--brookline:{b['brookline']};--brookline-light:{b['brookline-light']};"
        # paper tints — the marks a reader leaves in a transcript
        f"--tint-1:{b['paper-tint-1']};--tint-2:{b['paper-tint-2']};"
        f"--tint-3:{b['rule']};--tint-4:{b['ink-muted']};"
        f"--font-display:{b['font-display']};--font-sans:{b['font-sans']};--font-mono:{b['font-mono']};")
    return (":root{" + _brand_inner("typography.css") + " " + _brand_inner("spacing.css") + " "
            + colours + "}")


def emit_assets(out: Path, version, manifest):
    (out / "assets").mkdir(parents=True, exist_ok=True)
    # app.css = publicrecord's own tokens (from brand/) + the self-hosted
    # @font-face block + the web rules. No desk tokens, no third-party fonts.
    web_css = (Path(__file__).resolve().parent / "static" / "app.web.css").read_text(encoding="utf-8")
    (out / "app.css").write_text(
        _brand_tokens() + "\n" + _FONT_FACES + "\n\n" + web_css, encoding="utf-8")
    # app.js (the reader)
    shutil.copyfile(Path(__file__).resolve().parent / "static" / "app.js",
                    out / "app.js")
    # the self-hosted faces (subset latin woff2, vendored with their OFL texts)
    fonts_src = Path(__file__).resolve().parent / "static" / "fonts"
    if fonts_src.is_dir():
        shutil.copytree(fonts_src, out / "fonts", dirs_exist_ok=True)
    # favicon — the publicrecord keycap, byte-equal from brand/logos (never
    # redrawn); the mark must survive as a favicon and this is where it does.
    (out / "favicon.svg").write_text(_brand_mark(), encoding="utf-8")
    # PWA: the web-app manifest (a DIFFERENT file from the edition manifest.json)
    # + a service worker. Both deterministic — the SW's cache name rides the
    # corpus fingerprint so a new pressing supersedes the old cache cleanly.
    _write_pwa(out, manifest)


def _write_pwa(out: Path, manifest):
    import json as _json
    webmanifest = {
        "name": "The Public Record — publicrecord.studio",
        "short_name": "the record",
        "description": "A town's whole spoken life, cross-linked and searchable "
                       "— open in any browser.",
        "start_url": "/app/", "scope": "/app/", "display": "standalone",
        "background_color": "#F3EEE3", "theme_color": "#F3EEE3",
        "icons": [{"src": "/app/favicon.svg", "sizes": "any",
                   "type": "image/svg+xml"}],
    }
    (out / "manifest.webmanifest").write_text(
        _json.dumps(webmanifest, ensure_ascii=False, sort_keys=True,
                    separators=(",", ":")), encoding="utf-8")
    # the service worker: precache the shell, cache-first for the edition, and
    # tell the page when a fresher pressing has been fetched. Cache name = the
    # corpus fingerprint, so a new edition's SW owns a new cache and sweeps the
    # old one on activate. No wall-clock anywhere (idempotence).
    # cache name keys on BOTH the version and the corpus fingerprint: a new
    # pressing (corpus change) OR a new release (statics/pages change, which
    # always bumps the version) supersedes the old cache, so a returning reader
    # never sees a stale shell after an edition ships.
    # the key names the corpus AND the listed front pages (specs/29 P2): a
    # page taken down or newly listed on a quiet week must reach returning
    # readers, and a cache-first shell changes only when its key does
    cache = f"cz-record-{manifest.get('version','0')}-{manifest.get('corpus_hash','0')}" + (
        f"-{manifest['shared_hash']}" if manifest.get("shared_hash") else "")
    v = esc(manifest.get("version", "0"))
    # Stub URLs precache in their TRAILING-SLASH canonical form: the host
    # serves the bare form as a 301, addAll would store the redirected
    # response, and a navigation served a redirected response is a browser
    # error — the review that added /app/p caught this had silently broken
    # the sibling stubs offline all along. The make surfaces (/app/p, /app/r)
    # and the constitution join the shell: the covenant's own case is
    # composing with the servers gone.
    shell_urls = _json.dumps([
        "/app/", f"/app/app.css?v={manifest.get('version','0')}",
        f"/app/app.js?v={manifest.get('version','0')}", "/app/favicon.svg",
        "/app/manifest.json", "/app/stats.json", "/app/s/", "/app/watching/",
        "/app/officials/", "/app/p/", "/app/front-pages/", "/app/r/", "/app/ai/",
        # the editor's add-search reads these two (specs/23 A3) — small, and
        # with them in the shell a paper can be assembled with the host gone
        "/app/search/meta.json", "/app/issues/index.json",
        # the municipality switch reads the edition's towns on every page
        "/app/towns.json"],
        separators=(",", ":"))
    sw = f"""'use strict';
// the record's service worker — precache the shell, keep last-read meetings,
// and let the page announce a fresher pressing. Cache name is the corpus
// fingerprint (deterministic; a new edition = a new cache).
const CACHE = {cache!r};
const SHELL = {shell_urls};
self.addEventListener('install', e => {{
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
}});
self.addEventListener('activate', e => {{
  e.waitUntil(caches.keys().then(ks => Promise.all(
    ks.filter(k => k !== CACHE && k.indexOf('cz-record-') === 0).map(k => caches.delete(k))
  )).then(() => self.clients.claim()));
}});
self.addEventListener('fetch', e => {{
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== location.origin || url.pathname.indexOf('/app/') !== 0) return;
  // cache-first: the edition is immutable within a pressing; the shell and any
  // meeting you've read stay available offline. A bare-path navigation
  // (/app/s) falls to its canonical slash form before the network — the host
  // would have 301'd it there anyway, and offline has no host. Redirected
  // responses are never cached: serving one to a navigation is a browser
  // error, not a page.
  e.respondWith(caches.match(req)
    .then(hit => hit || (req.mode === 'navigate' && url.pathname.slice(-1) !== '/'
        ? caches.match(url.pathname + '/') : undefined))
    .then(hit => hit || fetch(req).then(res => {{
      if (res && res.ok && res.type === 'basic' && !res.redirected) {{
        const copy = res.clone();
        caches.open(CACHE).then(c => c.put(req, copy));
      }}
      return res;
    }}).catch(() => hit)));
}});
"""
    (out / "sw.js").write_text(sw, encoding="utf-8")


def emit_stubs(out, meetings, issues, stats, manifest, base, officials=None,
               analytics=None, graph=None, towns=None, tombstones=None,
               kits=None, topics=None, stills=None, frontpages=None):
    v = manifest["version"]
    # before a single stub renders: the chrome needs to know what it may offer
    set_edition(towns)
    # the pictures as files (specs/27 §3.3): collected as the pages render,
    # written once at the end — the desk bake and the hosted press share this
    from . import pictures as _pictures
    _pictures.reset(base, manifest.get("edition_date") or "")
    # …and what the search spine should suggest (specs/29): the record's own words
    set_spine(_examples(analytics, issues))
    # the featured papers are computed HERE, from arguments bake and press
    # already pass identically — so the two pressings cannot drift apart
    featured = featured_papers(meetings, issues, stats)
    (out / "index.html").write_text(
        page_home(meetings, issues, stats, manifest, base, featured=featured,
                  analytics=analytics, topics=topics, stills=stills or {},
                  frontpages=frontpages),
        encoding="utf-8")
    # a word, over time — each featured topic story at an address of its own
    for t in (topics or []):
        d = out / "topic" / t["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(
            page_topic(t, issues, manifest, base, analytics=analytics), encoding="utf-8")
    (out / "s" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "s" / "index.html").write_text(
        page_search(manifest, base, examples=_examples(analytics, issues), topics=topics), encoding="utf-8")
    (out / "add" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "add" / "index.html").write_text(page_add(manifest, base), encoding="utf-8")
    (out / "covenant" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "covenant" / "index.html").write_text(page_covenant(manifest, base), encoding="utf-8")
    (out / "watching" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "watching" / "index.html").write_text(page_still(manifest, base), encoding="utf-8")
    (out / "officials" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "officials" / "index.html").write_text(
        page_officials(officials or [], manifest, base), encoding="utf-8")
    (out / "analytics" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "analytics" / "index.html").write_text(
        page_analytics(analytics or {}, manifest, base), encoding="utf-8")
    (out / "graph" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "graph" / "index.html").write_text(
        page_graph(graph or {}, manifest, base), encoding="utf-8")
    # the press page — the one place the thirteen doors now lead. Publisher's
    # line points at the kits only when this edition pressed some.
    kits = kits or []
    (out / "press" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "press" / "index.html").write_text(
        page_press(manifest, base, has_kits=bool(kits)), encoding="utf-8")
    # the reel viewer — one static stub; the reel itself lives in the link
    (out / "r" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "r" / "index.html").write_text(
        page_reel(manifest, base), encoding="utf-8")
    # your paper — one static stub; a curated paper lives in its link, the
    # browser's draft, or a content-addressed id (specs/21 P1). P3: the
    # empty state offers the featured papers the press built above.
    (out / "p" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "p" / "index.html").write_text(
        page_paper(manifest, base, featured=featured), encoding="utf-8")
    # the front pages (specs/29 P2, board 9): the record's own and readers'
    # shared pages, listed — the same featured list, and the store's rows
    (out / "front-pages" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "front-pages" / "index.html").write_text(
        page_frontpages(featured, frontpages or [], meetings, manifest, base,
                        stills=stills or {}, towns=towns), encoding="utf-8")
    # Our AI Constitution — when a model touches the record, whose it is,
    # where it runs, and what stands without it; linked from every footer.
    # /app/constitution is its shareable spelling (a slim redirect); the
    # root-level /constitution twin is a hand-file in the Pages repo.
    (out / "ai" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "ai" / "index.html").write_text(
        page_ai(manifest, base), encoding="utf-8")
    (out / "constitution" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "constitution" / "index.html").write_text(
        page_constitution_alias(manifest, base), encoding="utf-8")
    # the kits — Publisher's reading half (specs/20 §6, §7.9 P2). An index, and
    # a read-only page per meeting whose kit the bake pressed. The downloadable
    # kit.json is the plane the bake already wrote at /app/kits/<slug>.json.
    (out / "k" / "index.html").parent.mkdir(parents=True, exist_ok=True)
    (out / "k" / "index.html").write_text(
        page_kits_index(kits, manifest, base), encoding="utf-8")
    for kit in kits:
        d = out / "k" / kit["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page_kit(kit, manifest, base), encoding="utf-8")
    # the glossary (specs/27 §3.4): counted once, over every transcript, for
    # its own page and for each meeting page's line of words it explains
    from . import glossary as _glossary
    gcounts = _glossary.count(meetings)
    (out / "glossary").mkdir(parents=True, exist_ok=True)
    (out / "glossary" / "index.html").write_text(
        page_glossary(meetings, manifest, base, counts=gcounts), encoding="utf-8")
    # what the search page needs to count an entry's words the glossary's way,
    # so each count's link lands on its own number (the featured words' rule)
    import json as _json_mod
    (out / "glossary" / "index.json").write_text(
        _json_mod.dumps(_glossary.index(gcounts), ensure_ascii=False, sort_keys=True, separators=(",", ":")),
        encoding="utf-8")
    for m in meetings:
        d = out / "m" / m["pid"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(
            page_meeting(m, manifest, base, terms=_glossary.terms_on(m, gcounts)), encoding="utf-8")
        (d / "transcript.txt").write_text(page_meeting_txt(m), encoding="utf-8")
    for i in issues:
        d = out / "i" / i["slug"]
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(page_issue(i, manifest, base), encoding="utf-8")
    # tombstones — a forgotten issue's URL explains itself, never 404s. Written
    # after the live issues so a live issue always wins a shared slug.
    for t in (tombstones or []):
        d = out / "i" / t["slug"]
        if (d / "index.html").exists():
            continue
        d.mkdir(parents=True, exist_ok=True)
        (d / "index.html").write_text(
            page_tombstone(t["slug"], t["name"], t["date"], manifest, base),
            encoding="utf-8")
    # the thirteen door URLs survive as slim redirect stubs into /app/press
    for t in tools.TOOLS:
        if t["surface"] != "web":
            d = out / "t" / t["id"]
            d.mkdir(parents=True, exist_ok=True)
            (d / "index.html").write_text(
                page_door_stub(t, manifest, base), encoding="utf-8")
    # the pictures the pages above collected, written once (specs/27 §3.3)
    _pictures.flush(out)
