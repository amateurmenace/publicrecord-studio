"""The civic broadsheet — the record as a front page (specs/29, P0).

Stephen's verdict on the site was "too lifeless, too much text down a single
column". The answer is a front page laid out like a paper: a masthead with
the municipality switch and the READ stamp; the search spine (a real form,
six words to try, and the sentence *everything you see is a search*); then,
on a twelve-column grid, tonight's tape — the frame large, the score of the
night beneath it, the headline and the counted lede beside it, money named
on the tape, a filmstrip of three real frames across; the year in tapes with
its four chapters; four columns to delve into; how the talk flowed; the front
pages the press built; this week; the threads; and the three doors into
writing. Every name, place, topic and chart element is a link into the
search page or the meeting.

The laws it keeps. The reader is static files: every picture here is pressed
SVG (web/charts.py) with its numbers beside it as data-bs-* JSON, and app.js
re-lights it — a click moves the playhead, a chapter re-lights the year;
with scripts off every chart is a still and every control an anchor. The
words are counted (web/story.py), never modeled; a model's one paragraph —
the summary — arrives labeled. The pressed bytes carry no studio class, no
studio hue, no button and no script: the byte-clean guard sweeps this page.
Nothing loads from a third party — the stills are the edition's own
(record/stills.py). Two presses of one corpus agree byte for byte.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from . import charts, story
from . import pictures
from .charts import esc, hms, n_of, cut_words, town_color, still_src, data_attr

WEEK_DAYS = 7
THREADS = 6
TRIES = 6


# --------------------------------------------------------------------------
# the masthead's pieces (shared chrome — emit.masthead calls these)
# --------------------------------------------------------------------------

def stamp() -> str:
    """The mode stamp: READ in ink. app.js paints EDIT in rust over it when
    the reader enters the studio (paintModeBar), and says what that means."""
    return ('<span class="bs-stamp" id="bs-stamp" data-mode="read">'
            '<span class="bs-stamp-word">READ</span> · the record</span>')


def edition_line(manifest: dict) -> str:
    c = manifest.get("counts") or {}
    ed = manifest.get("edition_date") or ""
    bits = []
    if ed:
        bits.append(f'Record of {esc(story.day_name(ed))}')
    bits.append("pressed nightly")
    if c.get("meetings") is not None:
        bits.append(n_of(c.get("meetings"), "meeting"))
    if c.get("hours") is not None:
        bits.append(f'{c.get("hours")} hours')
    bits += ["no accounts", "no tracking"]
    return " · ".join(bits)


def topbar(manifest: dict, current: str, mark: str) -> str:
    """The thin bar over every page: the site's name (the keycap beside it,
    byte-equal from brand/ — the brand law), the edition line, the stamp.
    Off the front page the name is the way back."""
    if current == "home":
        who = f'<span class="bs-site"><span class="brandmark">{mark}</span>publicrecord.studio</span>'
    else:
        who = f'<a class="bs-site bs-back" href="/app/"><span class="brandmark">{mark}</span>← The Public Record</a>'
    return (f'<div class="bs-topbar">{who}<span class="bs-edline">{edition_line(manifest)}</span>{stamp()}</div>')


def municipality(towns: Sequence[dict]) -> str:
    """The municipality switch: each town with its count, and the whole
    record. Real links (a scoped page is a URL); app.js takes the click over
    so the choice persists in this browser and the page re-scopes in place.
    The hooks are the scope's own (scopetown / data-town / #scopenow), so
    every page obeys the switch the way it obeyed the old picker."""
    ts = list(towns or [])
    if not ts:
        return ""
    if len(ts) == 1:
        t = ts[0]
        return (f'<div class="scope one bs-muni" id="scope"><span class="kicker">Municipality</span>'
                f'<span class="bs-muni-row"><span class="bs-town scopenow" id="scopenow" data-town="{esc(t["town"])}">{esc(t["town"])}'
                f' <span class="bs-n">{t["meetings"]}</span></span>'
                f'<span class="hint">the only town on this edition</span></span></div>')
    links = "".join(
        f'<a class="bs-town scopetown" href="/app/?town={esc(t["town"])}" data-town="{esc(t["town"])}" '
        f'style="--town:{town_color(t["town"])}">{esc(t["town"])} <span class="bs-n">{t["meetings"]}</span></a>' for t in ts)
    return (f'<div class="scope bs-muni" id="scope"><span class="kicker">Municipality</span>'
            f'<span class="bs-muni-row">{links}'
            f'<a class="bs-town bs-town-all scopetown" href="/app/" data-town="">The whole record</a></span>'
            f'<span class="bs-scopenow" id="scopenow">the whole record</span></div>')


def nameplate(manifest: dict, towns: Sequence[dict], spine_html: str = "") -> str:
    """The wordmark, then the search spine, then the municipality switch —
    in that order in the page, so a phone (board 3: "the spine second") and
    a screen reader meet them as the spec orders them; the desktop grid
    still sets the switch at the wordmark's right (app.web.css)."""
    return (f'<div class="bs-nameplate"><div class="bs-wordmark-box">'
            f'<a class="bs-wordmark" href="/app/">The Public Record</a>'
            f'<p class="bs-promise">What {esc(story.the_list([t["town"] for t in (towns or [])]) or "the town")} said in their own public meetings — searchable, quotable, and yours to retell.</p>'
            f'</div>{spine_html}{municipality(towns)}</div>')


def spine(tries: Sequence[str], base: str = "/app") -> str:
    """The search spine: a real form that submits to the search page without
    scripts; six words to try; the sentence. app.js adds the type-ahead panel
    over the shipped index (bsSpine) — grouped as moments · meetings ·
    threads · over time, keyboard-first, nothing leaves the browser."""
    chips = "".join(f'<a class="bs-try" href="{esc(charts.search_url(str(x), "", base))}">{esc(x)}</a>' for x in list(tries or [])[:TRIES])
    return f'''<div class="bs-spine" id="bs-spine">
  <form class="bs-spineform" action="{base}/s" method="get" role="search">
    <label for="spine" class="bs-vh">Search the record</label>
    <svg class="bs-spine-glass" width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
    <input id="spine" name="q" type="search" autocomplete="off" placeholder="Search the record — a word, a name, a street, a vote. Every hit is a moment you can play." aria-label="Search the record">
    <button class="bs-spinego" type="submit">Search</button>
  </form>
  <div class="bs-tries"><span>try</span>{chips}<span class="bs-spine-say">everything you see is a search — click a name, a place, a thread</span></div>
  <div class="bs-ta" id="bs-ta" hidden></div>
</div>'''


NAV = [("home", "Read the record", "/app/"),
       ("search", "A word over time", "/app/s"),
       ("officials", "The votes", "/app/officials"),
       ("graph", "Threads", "/app/graph"),
       ("paper", "Front pages", "/app/front-pages/"),
       ("glossary", "The glossary", "/app/glossary/")]
WRITE = ("write", "Write your own", "/app/p#edit")


def primary_nav(current: str, towns: Sequence[dict] = ()) -> str:
    """Five words on the reading side and one rust word on the writing side,
    a mono hint between them (specs/29 — the stamps). Off the front page the
    municipality switch rides the line's right slot, compact — the switch is
    on every page (specs/17 §8), the nameplate only on the front page."""
    items = "".join(f'<a class="navlink{" active" if k == current else ""}" href="{href}">{esc(label)}</a>'
                    for k, label, href in NAV)
    pen = ('<svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" aria-hidden="true">'
           '<path d="M12 20h9"/><path d="M16.5 3.5a2.1 2.1 0 0 1 3 3L7 19l-4 1 1-4Z"/></svg>')
    right = (f'<span class="bs-navhint">↑ reading · writing ↑</span>' if current == "home"
             else f'<div class="bs-navmuni">{municipality(towns)}</div>')
    return (f'<div class="bs-navrow"><nav class="sectionnav" aria-label="Sections">{items}'
            f'<a class="navlink bs-write" href="{WRITE[2]}">{pen}{WRITE[1]}</a></nav>{right}</div>')


# --------------------------------------------------------------------------
# the page's sections
# --------------------------------------------------------------------------

def section_head(title: str, sub: str = "", right: str = "", right_href: str = "", hid: str = "") -> str:
    r = f'<a class="bs-right" href="{esc(right_href)}">{right}</a>' if right and right_href else (f'<span class="bs-right">{right}</span>' if right else "")
    idattr = f' id="{esc(hid)}"' if hid else ""      # the section's aria-labelledby names it (a review catch: the year's named no element)
    return (f'<div class="bs-sechead"><div class="bs-sechead-l"><h2{idattr}>{title}</h2>'
            + (f'<span class="bs-sub">{sub}</span>' if sub else "") + f'</div>{r}</div>')


def _summary_label(m: dict) -> str:
    origin = str(m.get("summary_origin") or "")
    if origin.startswith("ai:"):
        return f"summary · {esc(origin[3:])}"
    return "summary drawn from the tape" if m.get("summary") else "no summary yet"


def tonight_section(m: dict, stills: Optional[dict], base: str = "/app") -> str:
    """Tonight's tape: the frame large with the Play-from chip and the
    caption under the playhead; the score beneath; the headline, the counted
    lede, the now-at card and money named on the tape at the right; the
    filmstrip across. The state is `t` — the loudest moment at press time."""
    w = story.tonight(m, base)
    d = charts.score_data(m)
    st = charts.score_state(d, d["t"])
    pid = w["pid"]
    href = f"{base}/m/{esc(pid)}"
    near = d["decisions"][st["near"]] if st["near"] is not None else None
    frame = still_src(stills, pid, st["third"] + 1, base) or still_src(stills, pid, 0, base)
    hero = (f'<img id="bs-hero-img" src="{esc(frame)}" alt="A frame from {esc(w["title"])}" width="880" height="495">' if frame
            else f'<span class="bs-nostill bs-hero-none" style="background:{charts.town_light(w["town"])}"><span>the tape · {hms(m.get("duration") or 0)}</span></span>')
    quote = f'“{esc(near["quote"])}”' if near else ""
    now_card = ""
    if near:
        now_card = (f'<div class="bs-now" id="bs-now" aria-live="polite"><span class="bs-now-k">now at <span class="bs-now-t">{st["mmss"]}</span> · <span class="bs-now-kind">'
                    f'{"a decision" if near["kind"] != "tension" else "tension"}</span></span>'
                    f'<span class="bs-now-q">“{esc(near["quote"])}”</span><span class="bs-now-why">{esc(story.now_words(near))}</span></div>')
    cur = ' class="bs-moneyrow on" aria-current="true"'   # the row under the playhead, at press time
    plain = ' class="bs-moneyrow"'                          # built first: no backslash in an f-string (3.11)
    money = "".join(
        f'<a{cur if abs(x["t"] - d["t"]) < 1 else plain} href="{href}#t{int(x["t"])}" data-t="{charts._r(x["t"])}">'
        f'<span class="bs-money-l">{esc(x["label"])}</span><span class="bs-money-m">said {n_of(x["count"], "time")} · at {hms(x["t"])}</span></a>'
        for x in w["money"])
    money_box = (f'<div class="bs-moneybox"><span class="kicker bs-money-k">money named on the tape · click to go there</span>{money}</div>'
                 if money else "")
    labels = "".join(f'<span class="bs-label">{esc(x)}</span>' for x in w["labels"])
    score_pic = charts.score(m, base=base, data=d)
    score_pic += pictures.take("tonight-score", score_pic, f"The score of the night — {w['title']}", href,
                               legend="a dot is a decision, sized by its weight; rust, pushback · $ a dollar figure the room named · the eight lanes: where each lens’s words fell")
    return f'''<section class="bs-tonight" id="tonight" aria-labelledby="bs-tonight-hl" data-town="{esc(w["town"])}" data-body="{esc(w["body"])}">
  <div class="bs-tonight-l">
    <div class="bs-kickrow"><span class="kicker bs-kick" style="color:{town_color(w["town"])}">{esc(w["kicker"])}</span><span class="bs-meta">{esc(w["meta"])}</span></div>
    <div class="bs-hero" id="bs-hero">{hero}
      <div class="bs-hero-foot"><a class="bs-playfrom" id="bs-playfrom" href="{href}#t{int(d["t"])}">▶ Play from <span class="bs-play-t">{st["mmss"]}</span></a>
        <span class="bs-hero-q" id="bs-hero-q">{quote}</span></div>
    </div>
    <div class="bs-scorecard">
      <div class="bs-scorehead"><span class="kicker">the score of the night — click anything to go there</span>
        <span class="bs-legend">● a decision, sized by weight · ▮ tension · $ money named · the eight lanes: where each lens’s words fell</span></div>
      {score_pic}
    </div>
  </div>
  <div class="bs-tonight-r">
    <h1 class="bs-hl" id="bs-tonight-hl"><a href="{href}">{w["headline"]}</a></h1>
    <p class="bs-lede">{w["lede"]}</p>
    {now_card}
    {money_box}
    <div class="bs-labels">{labels}<a class="bs-makeit" href="{base}/p#edit&amp;tpl=meeting&amp;ref={esc(pid)}">make this your front page →</a></div>
  </div>
  <div class="bs-tonight-strip">{charts.filmstrip(m, stills, base=base, data=d)}</div>
</section>'''


def year_section(meetings: Sequence[dict], votes: Sequence[dict], analytics: dict, stills: Optional[dict],
                 base: str = "/app") -> str:
    # one window for the strip, its chapters and its words (a skeptic's catch)
    months, dated, windowed = charts.year_window(meetings)
    chs = story.chapters(dated, votes, (analytics or {}).get("framing") or [], base=base)
    if not chs:
        return ""
    last = chs[-1]
    current = ' aria-current="true"'     # built first: an f-string expression holds no backslash (3.11)
    pills = "".join(f'<a class="bs-chap{" on" if c["i"] == last["i"] else ""}" href="#year" data-chapter="{c["i"]}"'
                    f'{current if c["i"] == last["i"] else ""}>{esc(c["title"])}</a>' for c in chs)
    n = len(dated)
    span = story.month_span_words([months[0], months[-1]]).replace(" and ", " to ") if len(months) > 1 else story.month_span_words(months)
    # the words and the download describe the picture on screen: the tapes
    # wide, board 3's dots on a phone (a review catch — the phone read "click
    # one" beneath dots that do nothing, and saved a picture it never showed)
    sub = (f'{story.number_words(n)} meeting{"" if n == 1 else "s"}, {esc(span)}'
           + (" — the last twelve months" if windowed else "")
           + '<span class="bs-onwide"> — each tape sized by its length; click one, or a chapter</span>'
           + '<span class="bs-onphone"> — a dot per meeting, its month’s count above; press a chapter</span>')
    year_pic = charts.year_tapes(dated, chs, stills, base=base, windowed=windowed)
    wide_take = pictures.take("year-in-tapes", year_pic, "The year in tapes", f"{base}/",
                              legend="every meeting as its own still on the year, sized by its length; the top edge is the town’s colour")
    at = year_pic.find('<div class="bs-yearphone">')
    phone_take = pictures.take("year-by-month", year_pic[at:] if at >= 0 else "", "The year, month by month", f"{base}/",
                               legend="a dot per meeting in its town’s colour, month by month; the count above each month")
    # a phone shows board 3's dots and never the tapes, so it never fetches
    # their stills: the page's <image>s wait (data-href) until the strip has
    # a box — app.js bsYearStills — while the picture file keeps them whole
    year_pic = year_pic.replace('<image href="', '<image data-href="')
    year_pic += ((f'<div class="bs-onwide">{wide_take}</div>' if wide_take else "")
                 + (f'<div class="bs-onphone">{phone_take}</div>' if phone_take else ""))
    return f'''<section class="bs-year-sec" id="year" aria-labelledby="bs-year-hl">
  {section_head("The year in tapes", sub, "every meeting →", f"{base}/s", hid="bs-year-hl")}
  {year_pic}
  <div class="bs-yearwords">
    <div class="bs-yearline" aria-live="polite"><p class="bs-tapeline" id="bs-tapeline">{last["html"]}</p>
      <span class="bs-tapemeta" id="bs-tapemeta">chapter {last["i"] + 1} of {len(chs)} · {n_of(len(last["months"]), "month")}</span></div>
    <div class="bs-chapters" role="group" aria-label="the year’s chapters">{pills}</div>
  </div>
</section>'''


def _votes_of(meetings: Sequence[dict]) -> List[dict]:
    out = []
    for m in meetings:
        for v in (m.get("votes") or []):
            out.append({**v, "pid": m["pid"], "date": m.get("date") or "", "town": m.get("town") or "",
                        "body": m.get("body") or ""})
    return out


def _real_topics(analytics: dict) -> List[dict]:
    return [t for t in ((analytics or {}).get("topics") or [])
            if str(t.get("topic") or "").strip() and str(t.get("topic")).strip().lower() not in charts.ARTIFACTS]


def columns_section(meetings: Sequence[dict], analytics: dict, issues: Sequence[dict], stills: Optional[dict],
                    base: str = "/app") -> str:
    """Four columns, each a story you can delve into: two towns' vocabularies,
    who and when, the roll calls, the widest thread's season — each ending
    in a rust delve."""
    an = analytics or {}
    tb = {str(m.get("pid")): str(m.get("town") or "") for m in meetings}
    by_pid = {str(m.get("pid")): m for m in meetings}
    months = charts.month_range([str(m.get("date"))[:7] for m in meetings if charts.is_month(m.get("date"))])
    cols = []
    # 1 — two towns, two vocabularies
    shares = charts.town_shares(an.get("framing") or [], tb)
    head, say, count = story.vocab_words(shares)
    bpic = charts.butterfly(shares)
    bpic += pictures.take("two-towns-two-vocabularies", bpic, "Two towns, two vocabularies", f"{base}/",
                          legend="each bar is a lens’s share of everything a town’s meetings say under a lens")
    cols.append(_column("Two towns, two vocabularies" if len(shares) > 1 else "One town’s vocabulary", head or "The lenses",
                        bpic, [say, count], "delve: the lenses, meeting by meeting →", f"{base}/analytics", charts.INK))
    # 2 — who, and when
    nh, ns = story.names_words(an.get("names") or [], months)
    first_town = next((t for t in tb.values() if t), "")
    wpic = charts.who_when(an.get("names") or [], months, tb, base=base)
    wpic += pictures.take("who-and-when", wpic, "Who, and when", f"{base}/",
                          legend="a dot is a month the name was said; bigger, said in more meetings; the colour is the town that says it most")
    cols.append(_column("Who, and when", nh, wpic,
                        [ns, "Every name and every street is a search — click one and the record cuts a reel."],
                        "delve: names and places, as a reel →", f"{base}/s", town_color(first_town) if first_town else charts.INK))
    # 3 — the roll calls
    votes = _votes_of(meetings)
    rh, rs, rl = story.rolls_words(votes, by_pid)
    vpic = charts.vote_grid(votes, base=base)
    vpic += pictures.take("the-roll-calls", vpic, "The roll calls", f"{base}/",
                          legend="a square is a roll call, by month; the number is the ayes; rust, the one that failed")
    cols.append(_column("The roll calls", rh, vpic, [rs, rl],
                        "delve: every roll call, dot by dot →", f"{base}/officials", charts.RUST))
    # 4 — the widest thread's season
    topics = _real_topics(an)
    if topics:
        t = topics[0]
        th, ts = story.thread_words(t)
        ms = sorted((x for x in (t.get("meetings") or []) if x.get("pid") in by_pid), key=lambda x: str(x.get("date") or ""))
        minis = "".join(
            f'<a class="bs-mini" href="{base}/m/{esc(x["pid"])}#t{int(float(x.get("t") or 0))}">'
            + (f'<img src="{esc(still_src(stills, x["pid"], 0, base))}" alt="" loading="lazy" width="52" height="30">' if still_src(stills, x["pid"], 0, base)
               else f'<span class="bs-nostill" style="background:{charts.town_light(tb.get(x["pid"]))}"></span>')
            + f'<span>{esc(charts.day_short(x.get("date")))}</span></a>' for x in ms[:5])
        iss = story.topic_issue({"phrases": [t["topic"]], "long": t["topic"]}, issues)
        delve = (f"{base}/i/{esc(iss['slug'])}" if iss else charts.search_url(str(t["topic"]), "", base).replace("&", "&amp;"))
        pic = (f'<div class="bs-minis">{minis}</div>' if minis else "") + charts.thread_spark([x.get("date") for x in ms], months, label=f'meetings that took up {t["topic"]}, month by month')
        second = ("The thread’s page lays those tapes on one line, with the moments the words were said." if iss
                  else "The search lays those tapes on one line, with every moment the words were said.")
        cols.append(_column("What keeps coming back", th, pic, [ts, second], "delve: the thread, over time →", delve, charts.INK))
    return f'''<section class="bs-columns" id="columns">
  {section_head("Four columns", "each a story you can delve into", "all the record’s stories →", f"{base}/p")}
  <div class="bs-colgrid">{"".join(cols)}</div>
</section>'''


def _column(kicker: str, head: str, pic: str, paras: Sequence[str], delve: str, href: str, color: str) -> str:
    ps = "".join(f"<p>{p}</p>" for p in paras if p)
    return (f'<article class="bs-col"><span class="bs-colkick" style="color:{color}">{kicker}</span><h3>{head}</h3>'
            f'<div class="bs-colpic">{pic}</div>{ps}<a class="bs-delve" href="{href}">{delve}</a></article>')


def river_section(meetings: Sequence[dict], analytics: dict, base: str = "/app") -> str:
    tb = {str(m.get("pid")): str(m.get("town") or "") for m in meetings}
    rows = (analytics or {}).get("framing") or []
    d = charts.river_data(rows, tb)
    if len(d["meetings"]) < 2:
        return ""
    river_pic = charts.lens_river(rows, tb, base=base)
    river_pic += pictures.take("how-the-talk-flowed", river_pic, "How the talk flowed, meeting by meeting", f"{base}/",
                               legend="each band is one lens’s share of a night’s framed words, meeting by meeting; the dashed line is where the second town joins")
    return f'''<section class="bs-river-sec" id="river">
  {section_head("How the talk flowed, meeting by meeting", "each band is one lens’s share of a night’s words; the record reads eight", "the lenses, explained →", f"{base}/analytics")}
  {river_pic}
  <p class="bs-reading">{story.river_words(d)}<span class="bs-onphone"> Tap a band for the full page, where each lens is named.</span></p>
</section>'''


def frontpages_section(featured: Sequence[dict], meetings: Sequence[dict], stills: Optional[dict], base: str = "/app",
                       shared: Optional[Sequence[dict]] = None) -> str:
    """The front pages the press built (specs/21 P3), as cards with a still
    where the paper is one meeting's, the newest reader's page beside them
    (specs/29 P2), and the ink door into writing — web/gallery.py makes the
    cards, the same ones the gallery page lists."""
    from . import gallery
    own = gallery.own_cards(featured or [], meetings, stills, base)
    readers = gallery.strip_cards(shared or [])   # the newest reader's page a previous press has listed, and that cites the record
    cards = "".join(gallery.card_html(c) for c in own) + "".join(gallery.card_html(c) for c in readers)
    return f'''<section class="bs-frontpages" id="frontpages">
  {section_head("Front pages", "the record’s own, and readers’", "all front pages →", f"{base}/front-pages/")}
  <div class="bs-fpgrid">{cards}{gallery.door_html(base)}</div>
</section>'''


def _day_of(d) -> Optional[story._dt.datetime]:
    """A real calendar day, or None — a stored '2026-02-30' is undated, not a crash."""
    try:
        return story._dt.datetime.strptime(str(d or "")[:10], "%Y-%m-%d")
    except ValueError:
        return None


def week_section(meetings: Sequence[dict], stills: Optional[dict], bodies_html: str, base: str = "/app") -> str:
    ms = sorted((m for m in meetings if m.get("date")), key=lambda m: (str(m["date"]), str(m.get("pid"))), reverse=True)
    if not ms:
        return ""
    latest_day = _day_of(ms[0]["date"])
    since = latest_day - story._dt.timedelta(days=WEEK_DAYS) if latest_day else None
    week = [m for m in ms if since is None or ((d := _day_of(m["date"])) is not None and d > since)]
    fell_back = len(week) < 3
    if fell_back:
        week = ms[:5]
    cards = []
    for m in week[:8]:
        pid = str(m.get("pid"))
        src = still_src(stills, pid, 0, base)
        pic = (f'<img src="{esc(src)}" alt="" loading="lazy" width="480" height="270">' if src
               else f'<span class="bs-nostill" style="background:{charts.town_light(m.get("town"))}"></span>')
        cards.append(f'<a class="mcard bs-week-card" href="{base}/m/{esc(pid)}" data-town="{esc(m.get("town") or "")}" data-body="{esc(m.get("body") or "")}" '
                     f'style="--town:{town_color(m.get("town"))}">{pic}<span class="bs-wkbody">'
                     f'<span class="bs-wkkick">{esc(" · ".join(x for x in (m.get("town"), m.get("body")) if x))}</span>'
                     f'<b>{esc(m.get("title") or pid)}</b><span class="bs-wkmeta">{esc(story.day_name(m.get("date") or ""))} · {esc(story.hours_words(m.get("duration") or 0))}</span></span></a>')
    title = "The latest on the record" if (fell_back or since is None) else "This week on the record"
    return f'''<section class="bs-week" id="week">
  {section_head(title, "", "every meeting, by town and body →", f"{base}/s")}
  {bodies_html}
  <div class="mcards bs-weekrow">{"".join(cards)}</div>
  <p class="scopeline" id="scopeline" hidden></p>
</section>'''


def threads_section(analytics: dict, issues: Sequence[dict], topics: Sequence[dict], meetings: Sequence[dict],
                    base: str = "/app", stats: Optional[dict] = None) -> str:
    """Threads: six small multiples — the featured words first (each with its
    own story page), then the recurring topics — each with what it keeps
    coming back as, and *tell its story →*."""
    months = charts.month_range([str(m.get("date"))[:7] for m in meetings if charts.is_month(m.get("date"))])
    cards = []
    seen = set()
    for t in (topics or []):
        dates = [r.get("date") for r in (t.get("meetings") or []) if r.get("n")]
        seen.add(str(t.get("q") or "").lower())
        cards.append(_thread_card(str(t.get("name") or t.get("q")), int(t.get("mentions") or 0), int(t.get("n_meetings") or 0),
                                  charts.thread_spark(dates, months, color=town_color(t.get("town")), label=f'meetings that took up {t.get("q")}, month by month'),
                                  months, charts.search_url(str(t.get("q")), str(t.get("town") or ""), base).replace("&", "&amp;"),
                                  f'{base}/topic/{esc(t["slug"])}/', "its story →"))
    for t in _real_topics(analytics):
        if len(cards) >= THREADS:
            break
        name = str(t["topic"]).strip()
        if name.lower() in seen:
            continue
        seen.add(name.lower())
        ms = t.get("meetings") or []
        iss = story.topic_issue({"phrases": [name], "long": name}, issues)
        tell = f'{base}/p#edit&amp;tpl=issue&amp;ref={esc(iss["slug"])}' if iss else f'{base}/p#edit&amp;tpl=meeting&amp;ref={esc(sorted(ms, key=lambda x: str(x.get("date") or ""))[-1]["pid"])}' if ms else f"{base}/p#edit"
        cards.append(_thread_card(name, int(t.get("count") or 0), len(ms),
                                  charts.thread_spark([x.get("date") for x in ms], months, label=f"meetings that took up {name}, month by month"),
                                  months, charts.search_url(name, "", base).replace("&", "&amp;"), tell, "tell its story →"))
    resurf = (stats or {}).get("resurfacings") or []
    rrows = "".join(
        f'<a class="rsrow" href="{base}/i/{esc(r["slug"])}"><b>{esc(r["name"])}</b>'
        f'<span class="rsdelta">{esc(cut_words(str(r.get("delta") or ""), 220))}</span></a>' for r in resurf[:6])
    changed = (f'<div class="bs-changed"><span class="kicker">what changed, last time — threads that resurfaced</span>'
               f'<div class="rsrows">{rrows}</div></div>' if rrows else "")
    if not cards and not changed:
        return ""
    return f'''<section class="bs-threads" id="threads">
  {section_head("Threads", "what keeps coming back", "search any word over time →", f"{base}/s")}
  <div class="bs-threadgrid">{"".join(cards)}</div>
  {changed}
</section>'''


def _thread_card(name: str, mentions: int, n_meet: int, spark: str, months: Sequence[str], href: str, tell: str, tell_label: str) -> str:
    span = f'{charts.month_short(months[0])} → {charts.month_short(months[-1])}' if months else ""
    return (f'<article class="bs-thread"><a class="bs-thread-name" href="{href}">{esc(name)}</a>'
            f'<span class="bs-thread-n">{n_of(mentions, "mention")} · {n_of(n_meet, "meeting")}</span>{spark}'
            f'<span class="bs-thread-foot"><span>{esc(span)}</span><a class="bs-tell" href="{tell}">{tell_label}</a></span></article>')


def tell_section(lead: Optional[dict], stats: dict, base: str = "/app") -> str:
    loud = (stats or {}).get("loud") or []
    one = f'{base}/p#edit&amp;tpl=meeting&amp;ref={esc(lead["pid"])}' if lead else f"{base}/p#edit&amp;tpl=meeting"
    issue = f'{base}/p#edit&amp;tpl=issue&amp;ref={esc(loud[0]["slug"])}' if loud else f"{base}/p#edit&amp;tpl=issue"
    return f'''<section class="bs-yours" id="yourpaper" aria-labelledby="bs-tell-hl">
  <div class="bs-sechead"><div class="bs-sechead-l"><h2 id="bs-tell-hl">Now tell yours.</h2></div><span class="bs-right bs-rustline">everything past this line is writing — the record itself never changes</span></div>
  <div class="bs-doors">
    <a class="bs-door bs-door-ink" href="{one}"><span class="bs-fpkick">One meeting</span><b>What happened on the night, in your words</b><span>Start from the summary, the roll calls and the moments; add the clip, the chart and the caption you want.</span><span class="bs-fpgo">Start with tonight’s tape →</span></a>
    <a class="bs-door" href="{issue}"><span class="bs-fpkick">An issue over time</span><b>How one thread moved across a year of meetings</b><span>Pick a thread and the record draws the months, the lenses, the votes and a reel of the moments.</span><span class="bs-fpgo">Start with a thread →</span></a>
    <a class="bs-door" href="{base}/p#edit"><span class="bs-fpkick">Five more templates</span><b>A vote’s history · a person · a place · two towns · the year so far</b><span>Each draws its own charts and drafts its own labeled reading; each asks you three questions.</span><span class="bs-fpgo">See the templates →</span></a>
  </div>
</section>'''


# --------------------------------------------------------------------------
# the page
# --------------------------------------------------------------------------

def page_body(meetings: Sequence[dict], issues: Sequence[dict], stats: dict, base: str = "/app",
              featured: Optional[Sequence[dict]] = None, analytics: Optional[dict] = None,
              topics: Optional[Sequence[dict]] = None, stills: Optional[dict] = None,
              bodies_html: str = "", shared: Optional[Sequence[dict]] = None) -> str:
    """The front page's body, in the order of board 1 — the masthead and the
    spine are the shell's (emit.masthead), the footer the shell's too."""
    ms = sorted(meetings, key=lambda m: (str(m.get("date") or ""), str(m.get("pid"))), reverse=True)
    lead = ms[0] if ms else None
    parts: List[str] = []
    if lead and float(lead.get("duration") or 0) > 0:
        parts.append(tonight_section(lead, stills, base))
    elif lead:
        parts.append(f'<section class="bs-tonight" id="tonight"><p class="hint">The latest meeting on the record, '
                     f'<a href="{base}/m/{esc(lead["pid"])}">{esc(lead.get("title") or lead["pid"])}</a>, has no tape length yet — '
                     'the score needs one.</p></section>')
    else:
        parts.append('<section class="bs-tonight"><p class="hint">The record is empty — no meetings pressed yet.</p></section>')
    votes = _votes_of(meetings)
    parts.append(year_section(meetings, votes, analytics or {}, stills, base))
    parts.append(columns_section(meetings, analytics or {}, issues, stills, base))
    parts.append(river_section(meetings, analytics or {}, base))
    parts.append(frontpages_section(featured or [], meetings, stills, base, shared=shared))
    parts.append(week_section(meetings, stills, bodies_html, base))
    parts.append(threads_section(analytics or {}, issues, topics or [], meetings, base, stats=stats))
    parts.append(tell_section(lead, stats, base))
    return "\n".join(p for p in parts if p)
