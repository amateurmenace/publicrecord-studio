"""The front page's two stories, written by the press (specs/24 §2.4).

The record's front page is a story, not a dashboard and not a door: the
record over time, and the latest meeting — each told whole, with its pictures
(web/charts.py) and a commentary that is COUNTED, never modeled. Every
sentence here is a rule over the pressed planes, and every number in it is a
receipt into the page that holds it. The one paragraph a model may have
drafted — a meeting's summary — arrives labeled, as it does everywhere else
on the record (`summary_origin`), and stands beside the counted commentary,
never instead of it.

Two stories, one toggle: the page presses both; the reader's script shows one
at a time (the choice is remembered in this browser and nowhere else); with
JavaScript off both stand, in order, under their own headings. Each story
ends where the making half begins — "make this story yours" opens the same
story as a draft in the studio, block for block.
"""

from __future__ import annotations

import datetime as _dt
import html as _html
import re
from typing import Dict, List, Optional, Sequence

from . import charts, pictures
from .charts import esc, hms, n_of, ARTIFACTS, cut_words


# --------------------------------------------------------------------------
# small helpers
# --------------------------------------------------------------------------

def month_name(d: str) -> str:
    """'2026-06-18' → 'June 2026'; anything else → '' (never a guess)."""
    try:
        return _dt.datetime.strptime(str(d)[:7], "%Y-%m").strftime("%B %Y")
    except ValueError:
        return ""


def day_name(d: str) -> str:
    """'2026-06-18' → 'June 18, 2026'."""
    try:
        t = _dt.datetime.strptime(str(d)[:10], "%Y-%m-%d")
        return f'{t.strftime("%B")} {t.day}, {t.year}'
    except ValueError:
        return str(d or "undated")


def the_list(items: Sequence[str]) -> str:
    """'a', 'a and b', 'a, b and c' — prose, not a dump."""
    xs = [x for x in items if x]
    if not xs:
        return ""
    if len(xs) == 1:
        return xs[0]
    return ", ".join(xs[:-1]) + " and " + xs[-1]


def hours_words(seconds: float) -> str:
    s = int(seconds or 0)
    h, m = s // 3600, (s % 3600) // 60
    if h and m:
        return f"{h} h {m} min"
    if h:
        return f"{h} h"
    return f"{m} min"


def _name(e) -> str:
    """A named thing, without the punctuation the analyzer's cut left on it."""
    v = str(e.get("name") or e.get("text") or "") if isinstance(e, dict) else str(e or "")
    return v.strip().rstrip(".,;:")


def _topic_name(t) -> str:
    if isinstance(t, dict):
        return str(t.get("topic") or t.get("name") or t.get("word") or "").strip()
    return str(t or "").strip()


def _real_topics(topics) -> List[dict]:
    out = []
    for t in topics or []:
        name = _topic_name(t)
        if name and name.lower() not in ARTIFACTS:
            out.append({"name": name, "count": int((t.get("count") if isinstance(t, dict) else 0) or 0),
                        "meetings": (t.get("meetings") if isinstance(t, dict) else None) or [],
                        "t": (t.get("t") if isinstance(t, dict) else None)})
    return out


def kicker(text: str, right: str = "") -> str:
    return (f'<div class="sectionhead"><span class="kicker">{text}</span>'
            + (f'<span class="fp-right">{right}</span>' if right else "") + "</div>")


def say(html_: str) -> str:
    """A commentary line under a picture — what the picture says, counted."""
    return f'<p class="fp-say">{html_}</p>'


# --------------------------------------------------------------------------
# the toggle
# --------------------------------------------------------------------------

def tabs(latest_title: str = "", topics: Sequence[dict] = ()) -> str:
    """The front page's stories as tabs, as links: with JavaScript off they
    are in-page anchors and every story stands; the reader's script turns
    them into a toggle that shows one story at a time and says which is
    showing. A featured topic story (specs/25) leads when the record holds
    one — the front page opens on how the town talks about a word."""
    items = []
    # each tab names its own story — with two words on the strip, "A word,
    # over time" twice told a reader nothing (specs/27 §3.1)
    for t in topics:
        items.append(f'<a class="stab-a" href="#topic-{esc(t["slug"])}" data-story="topic-{esc(t["slug"])}">'
                     f'<b>“{esc(t["name"])}”, over time</b><span>how {esc(t["town"])} talks about it</span></a>')
    items.append('<a class="stab-a" href="#over-time" data-story="over-time"><b>The record, over time</b><span>how it moved</span></a>')
    items.append(f'<a class="stab-a" href="#latest" data-story="latest"><b>The latest meeting</b><span>{esc(latest_title or "what happened")}</span></a>')
    items[0] = items[0].replace('<a class="stab-a" ', '<a class="stab-a" aria-current="true" ', 1) \
        if items[0].startswith('<a class="stab-a" href="#topic') else \
        items[0].replace('data-story="over-time"', 'data-story="over-time" aria-current="true"', 1)
    n = len(items)
    label = "the front page’s two stories" if n == 2 else f"the front page’s {n} stories"
    return f'''  <nav class="stab" aria-label="{label}">
    {chr(10).join("    " + i for i in items).strip()}
  </nav>
'''


# --------------------------------------------------------------------------
# story one — the record, over time
# --------------------------------------------------------------------------

def over_time(meetings: Sequence[dict], issues: Sequence[dict], stats: dict,
              analytics: Optional[dict], base: str = "/app") -> str:
    c = stats.get("counts") or {}
    ms = sorted(meetings, key=lambda m: (str(m.get("date") or "")))
    dated = [m for m in ms if m.get("date")]
    first, last = (dated[0], dated[-1]) if dated else (None, None)
    bodies = sorted({str(m.get("body") or "") for m in ms if m.get("body")})
    towns = sorted({str(m.get("town") or "") for m in ms if m.get("town")})
    votes = [{**v, "pid": m["pid"], "date": m.get("date", ""), "body": m.get("body", ""),
              "town": m.get("town", ""), "title": m.get("title", "")}
             for m in ms for v in (m.get("votes") or [])]
    passed = sum(1 for v in votes if v.get("outcome") == "passes")
    failed = sum(1 for v in votes if v.get("outcome") == "fails")
    other = len(votes) - passed - failed
    hours = c.get("hours") or round(sum(float(m.get("duration") or 0) for m in ms) / 3600, 1)
    an = analytics or {}
    loud = [i for i in (stats.get("loud") or []) if i.get("slug")]
    n_meet = len(ms)

    # -- the headline and the lede: counted, every number a receipt --------
    since = month_name(first["date"]) if first else ""
    headline = (f'{n_of(n_meet, "meeting")}, {hours} hours, {n_of(len(votes), "roll call")} — '
                + (f'the record since {esc(since)}' if since else "the record so far"))
    lede = []
    if n_meet:
        who = the_list([f"the {b}" for b in bodies]) or "its public bodies"
        where = the_list(towns)
        lede.append(
            f'Since {esc(day_name(first["date"])) if first else "its first pressing"}, the record holds '
            f'<a href="{base}/s">{n_of(n_meet, "meeting")}</a> of {esc(who)}'
            + (f' in {esc(where)}' if where else "")
            + f' — <a href="{base}/analytics">{hours} hours</a> of tape, '
            f'<a href="{base}/s">{int(c.get("segments") or 0):,} lines</a> of it, every line searchable.')
    if loud:
        top = loud[0]
        tail = the_list([f'<a href="{base}/i/{esc(i["slug"])}">{esc(i["name"])}</a>' for i in loud[1:3]])
        lede.append(
            f'The longest thread is <a href="{base}/i/{esc(top["slug"])}">{esc(top["name"])}</a>, on the table in '
            f'{n_of(int(top.get("n_meetings") or 0), "meeting")} ({n_of(int(top.get("n_segments") or 0), "moment")})'
            + (f'; {tail} follow.' if tail else "."))
    if votes:
        latest_v = max(votes, key=lambda v: (str(v.get("date") or ""), float(v.get("t") or 0)))
        lede.append(
            f'<a href="{base}/officials">{n_of(len(votes), "roll call")}</a> were read from the tapes: '
            f'{passed} passed, {failed} failed' + (f', {other} landed otherwise' if other else "")
            + f'. The latest was <a href="{base}/m/{esc(latest_v["pid"])}#t{int(float(latest_v.get("t") or 0))}">'
            f'“{esc(cut_words(latest_v.get("motion"), 90))}”</a> — {esc(latest_v.get("outcome") or "")}'
            + (f' {esc(latest_v["tally"])}' if latest_v.get("tally") else "")
            + f', {esc(day_name(latest_v.get("date") or ""))}.')
    else:
        lede.append("No roll call has been read from a tape yet — the bodies' votes so far were by voice, or unrecorded.")
    cov = [x for x in (stats.get("coverage") or []) if x.get("month") and x["month"] != "undated"]
    if cov:
        busiest = max(cov, key=lambda x: (int(x.get("total") or 0), x["month"]))
        lede.append(f'The busiest month was {esc(month_name(busiest["month"]))} ({n_of(int(busiest["total"]), "meeting")}).')
    frows = [r for r in (an.get("framing") or []) if isinstance(r, dict)]
    lens_tot: Dict[str, float] = {}
    for r in frows:
        for l, n in (r.get("lenses") or {}).items():
            lens_tot[l] = lens_tot.get(l, 0.0) + float(n or 0)
    tot = sum(lens_tot.values())
    top_lenses = sorted(lens_tot.items(), key=lambda kv: -kv[1])[:2]
    if tot and top_lenses:
        lede.append(
            f'Across the record the talk leaned <a href="{base}/analytics">{esc(top_lenses[0][0])}</a> '
            f'({round(100 * top_lenses[0][1] / tot)}% of framed lines)'
            + (f' and {esc(top_lenses[1][0])} ({round(100 * top_lenses[1][1] / tot)}%)' if len(top_lenses) > 1 else "")
            + ' — counted by open word lists, not modeled.')
    topics = _real_topics(an.get("topics"))
    if topics:
        t0 = topics[0]
        # a phrase the glossary explains says where (specs/27 §3.4)
        from . import glossary as _glossary
        g0 = _glossary.entry_for(t0["name"])
        meaning = f' (<a href="{base}/glossary/#{esc(g0["slug"])}">what it means</a>)' if g0 else ""
        lede.append(
            f'“{esc(t0["name"])}”{meaning} came up {n_of(t0["count"], "time")} across {n_of(len(t0["meetings"]), "meeting")}'
            + (f'; “{esc(topics[1]["name"])}” and “{esc(topics[2]["name"])}” keep coming back too' if len(topics) > 2 else "")
            + '.')

    # -- the pictures, each with what it says ------------------------------
    parts: List[str] = []
    # by the numbers + meetings by month
    cells = [(c.get("meetings", n_meet), "meetings", f"{base}/s"),
             (hours, "hours", f"{base}/analytics"),
             (c.get("bodies", len(bodies)), "bodies", f"{base}/analytics"),
             (c.get("issues", len(issues)), "issues", f"{base}/graph"),
             (c.get("votes", len(votes)), "roll calls", f"{base}/officials"),
             (f'{int(c.get("segments") or 0):,}', "lines", f"{base}/s")]
    mx = max([int(x.get("total") or 0) for x in cov] or [1])
    bars = "".join(
        f'<div class="covbar" data-month="{esc(x["month"])}" title="{esc(x["month"])}: {x["total"]} meeting(s)">'
        f'<span style="height:{max(6, round(56 * int(x["total"]) / mx))}px"></span>'
        f'<label>{esc(x["month"][5:] or "?")}</label></div>' for x in cov)
    parts.append(f'<section class="fp-part">{kicker("the record, by the numbers")}'
                 + charts.numbers_strip(cells)
                 + (f'<div class="covwrap"><span class="kicker">meetings by month</span><div class="covstrip">{bars}</div></div>' if cov else "")
                 + "</section>")
    # votes over time
    vsay = ""
    if votes:
        by_body: Dict[str, int] = {}
        for v in votes:
            by_body[v.get("body") or "—"] = by_body.get(v.get("body") or "—", 0) + 1
        bb = max(by_body.items(), key=lambda kv: (kv[1], kv[0]))
        vsay = say(f'{n_of(len(votes), "roll call")} across {n_of(len({v["pid"] for v in votes}), "meeting")}: '
                   f'{passed} passed, {failed} failed' + (f', {other} otherwise' if other else "")
                   + f'. The {esc(bb[0])} took the most ({bb[1]}). A filled dot passes, a hollow one fails; '
                   f'every dot opens the tape where the vote was taken — '
                   f'<a href="{base}/officials">who voted how</a> reads in place.')
    teaser = "".join(
        f'<a class="vteaser" href="{base}/m/{esc(v["pid"])}#t{int(float(v.get("t") or 0))}">'
        f'<span class="vt-motion">{esc(str(v.get("motion") or "")[:90])}</span>'
        f'<span class="vt-meta"><span class="outcome">{esc(v.get("outcome") or "")}</span> '
        f'<span class="tally">{esc(v.get("tally") or "")}</span> · {esc(v.get("date") or "")}</span></a>'
        for v in sorted(votes, key=lambda v: (str(v.get("date") or ""), float(v.get("t") or 0)), reverse=True)[:4])
    see_all = f'<a class="seeall" href="{base}/officials">the votes →</a>'
    teaser_block = (f'<div class="fp-sub">{kicker("the latest roll calls", see_all)}'
                    f'<div class="vteasers">{teaser}</div></div>' if teaser else "")
    vpic = charts.votes_over_time(votes, base)
    parts.append(f'<section class="fp-part">{kicker("votes over time — every roll call, meeting by meeting")}'
                 + vpic + pictures.take("record-votes", vpic, "The record’s roll calls, meeting by meeting", f"{base}/",
                                legend=pictures.LEGEND["votes"])
                 + vsay + teaser_block + "</section>")
    # the long view
    months = [x["month"] for x in cov]
    isay = ""
    if loud:
        top = loud[0]
        isay = say(f'<a href="{base}/i/{esc(top["slug"])}">{esc(top["name"])}</a> surfaced in '
                   f'{n_of(int(top.get("n_meetings") or 0), "meeting")}'
                   + (f', from {esc(month_name(top.get("first_seen") or ""))} to {esc(month_name(top.get("last_seen") or ""))}'
                      if top.get("first_seen") and top.get("last_seen") else "")
                   + '. A taller bar is a month it came up more; every bar opens the meeting it came up in. '
                   f'The whole long view — {n_of(len(issues), "issue")} — reads on <a href="{base}/graph">the issue graph</a>.')
    parts.append(f'<section class="fp-part">{kicker("the long view — issues by reach, month by month")}'
                 + charts.issues_over_time(issues, months, base=base) + isay + "</section>")
    # how the talk was framed
    fsay = ""
    if frows and last:
        lastrow = next((r for r in frows if r.get("pid") == last.get("pid")), None)
        if lastrow and lastrow.get("total"):
            ll = max((lastrow.get("lenses") or {}).items(), key=lambda kv: kv[1], default=None)
            if ll:
                fsay = say(f'Deeper is more of the meeting’s talk through that lens. In the latest meeting, '
                           f'<a href="{base}/m/{esc(last["pid"])}">{esc(last.get("title") or last["pid"])}</a>, '
                           f'the talk leaned {esc(ll[0])} ({round(100 * float(ll[1]) / float(lastrow["total"]))}%). '
                           'Eight civic lenses, counted from the words themselves — a lens is a word list, readable in the source.')
    parts.append(f'<section class="fp-part">{kicker("how the talk was framed — eight civic lenses, meeting by meeting")}'
                 + charts.framing_strip(frows, an.get("lens_order") or [], base=base) + fsay + "</section>")
    # what keeps coming back
    tsay = ""
    if topics:
        t0 = topics[0]
        tsay = say(f'“{esc(t0["name"])}” led with {n_of(t0["count"], "mention")} across {n_of(len(t0["meetings"]), "meeting")}. '
                   'Each name is the record’s own search for it — the same search that found these.')
    parts.append(f'<section class="fp-part">{kicker("what keeps coming back — recurring topics, record-wide")}'
                 + charts.topic_bars(an.get("topics") or [], base=base) + tsay + "</section>")
    # the record in words
    words = record_words(ms)
    wsay = ""
    if words:
        w0 = words[0]
        wsay = say(f'“{esc(w0["word"])}” came up most — {n_of(int(w0["count"]), "mention")} across the record'
                   + (f'; “{esc(words[1]["word"])}” and “{esc(words[2]["word"])}” next' if len(words) > 2 else "")
                   + '. Sized by how often, placed by rank; every word opens the search for it.')
    wpic = charts.word_cloud(words, base=base)
    parts.append(f'<section class="fp-part">{kicker("the record in words — what was said most")}'
                 + wpic + pictures.take("record-words", wpic, "The record in words — what was said most", f"{base}/",
                                legend=pictures.LEGEND["cloud"])
                 + wsay + "</section>")
    # what changed
    resurf = stats.get("resurfacings") or []
    rrows = "".join(
        f'<a class="rsrow" href="{base}/i/{esc(r["slug"])}"><b>{esc(r["name"])}</b>'
        f'<span class="rsdelta">{esc(cut_words(str(r.get("delta") or ""), 220))}</span></a>' for r in resurf[:6]) \
        or '<p class="hint">No thread has resurfaced yet — follow an issue and the record will keep watch.</p>'
    parts.append(f'<section class="fp-part">{kicker("what changed, last time — threads that resurfaced")}'
                 f'<div class="rsrows">{rrows}</div></section>')
    # the close: make this story yours
    starts = "".join(
        f'<a class="btn" href="{base}/p#edit&amp;tpl=issue&amp;ref={esc(i["slug"])}">{esc(i["name"][:44])}</a>'
        for i in loud[:4])
    close = (f'<div class="fp-close"><a class="btn primary" href="{base}/p#edit&amp;tpl=rolls">make this story yours →</a>'
             f'<span class="fp-or">or follow one thread over time:</span>{starts}</div>')
    return f'''  <article class="fp-story fp-over" id="over-time" aria-labelledby="fp-over-hl">
    <span class="kicker">the record, over time — how it moved</span>
    <h2 class="fp-hl" id="fp-over-hl">{headline}</h2>
    <p class="fp-lede">{" ".join(lede)}</p>
    <p class="decksrc">counted from the record’s own planes when this edition was pressed — no model wrote a line of it; every number opens the page that holds it</p>
    {"".join(parts)}
    {close}
  </article>
'''


def record_words(meetings: Sequence[dict], top: int = 60) -> List[dict]:
    """Word frequencies across every meeting's transcript — the record-wide
    cloud. The analyzer's own counter (civic stopwords out), summed."""
    from highlighter import insight
    counts: Dict[str, int] = {}
    for m in meetings:
        for w in insight.word_freq(m.get("segments") or [], top=200):
            counts[w["word"]] = counts.get(w["word"], 0) + int(w["count"])
    return [{"word": w, "count": n} for w, n in sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top]]


# --------------------------------------------------------------------------
# story two — the latest meeting, what happened
# --------------------------------------------------------------------------

def latest(m: dict, base: str = "/app") -> str:
    from highlighter import insight
    pid = m["pid"]
    an = m.get("analysis") or {}
    mos = sorted((mo for mo in (m.get("moments") or []) if mo.get("t") is not None), key=lambda mo: -float(mo.get("score") or 0))
    dec, qs, ten = an.get("decisions") or [], an.get("questions") or [], an.get("tension") or []
    votes = m.get("votes") or []
    docs = m.get("documents") or []
    segs = m.get("segments") or []
    dur = float(m.get("duration") or 0)
    href = f"{base}/m/{esc(pid)}"
    at = lambda t: f"{href}#t{int(float(t or 0))}"

    # -- the lede: the labeled summary, then the counted commentary ---------
    origin = ("an AI summary, labeled" if str(m.get("summary_origin") or "").startswith("ai:")
              else "a summary drawn from the tape")
    # whole lines up to 900 characters, receipts linked: a cut at a fixed
    # character count ended the lede mid-receipt and mid-word
    said = charts.receipt_paras(str(m.get("summary") or ""), href, limit=900,
                                plain=not str(m.get("summary_origin") or "").startswith("ai:"))
    summary = (f'<div class="fp-lede fp-summ">{said}</div>'
               f'<p class="decksrc">{origin} — supplements the official record</p>' if said else "")
    # the reading, drafted (specs/24 §4) — a model's paragraphs under the
    # model's own name, receipts linked, beside the counted commentary
    d = an.get("draft") or {}
    drafted = (charts.receipt_paras(d["text"], href) if isinstance(d, dict) and str(d.get("text") or "").strip()
               and str(d.get("origin") or "").startswith("ai:") else "")
    if drafted:        # a draft that renders to nothing presses no labeled box
        summary += (f'<div class="fp-draft">{drafted}</div>'
                    f'<p class="decksrc">the reading, drafted by a model — {esc(d["origin"])}, labeled — '
                    'check it against the tape; the counted lines below stand on their own</p>')
    told = []
    told.append(f'The night ran <a href="{href}">{hours_words(dur)}</a>. The analyzer found '
                f'<a href="{href}">{n_of(len(dec), "decision")}</a>, {n_of(len(qs), "question")} and '
                f'{n_of(len(ten), "moment")} of pushback' + (f', and read {n_of(len(votes), "roll call")}' if votes else ", and read no roll call") + '.')
    top, secs = [], set()
    for mo in mos:
        if int(float(mo["t"])) in secs:
            continue
        secs.add(int(float(mo["t"]))); top.append(mo)
        if len(top) == 3:
            break
    if top:
        mo = top[0]
        told.append(f'Its loudest moment came at <a href="{at(mo["t"])}">{hms(mo["t"])}</a>, '
                    f'a {esc(charts.SHAPE_KINDS.get(mo.get("kind"), mo.get("kind") or "moment"))}: '
                    f'“{esc(cut_words(mo.get("quote"), 160))}”.')
    lenses = [l for l in ((an.get("framing") or {}).get("lenses") or []) if int(l.get("count") or 0) > 0]
    ftot = float((an.get("framing") or {}).get("total") or 0)
    if lenses and ftot:
        l0 = max(lenses, key=lambda l: int(l["count"]))
        drift = {"rising": "rising as the night went on", "fading": "fading as the night went on"}.get(l0.get("drift"), "steady through the night")
        told.append(f'The talk leaned <a href="{href}">{esc(l0["lens"])}</a> ({round(100 * int(l0["count"]) / ftot)}% of framed lines), {drift}.')
    ents = an.get("entities") or {}
    money = [_name(e) for e in (ents.get("money") or [])][:5]
    people = [_name(e) for e in (ents.get("people") or [])][:5]
    if money:
        told.append(f'Money on the table: {esc(the_list(money))}.')
    if people:
        told.append(f'Named, more than once: {esc(the_list(people))}.')
    if docs:
        told.append(f'The town filed {n_of(len(docs), "paper")} for it — {esc(the_list([str(d.get("kind") or "document") for d in docs[:3]]))}.')

    # -- the pictures ---------------------------------------------------------
    parts: List[str] = []
    cells = [(int(round(dur / 60)), "minutes", href), (len(votes), "roll calls", href),
             (len(dec), "decisions", href), (len(qs), "questions asked", href),
             (len(ten), "moments of pushback", href), (len(docs), "filings", href)]
    parts.append(f'<section class="fp-part">{kicker("the meeting in numbers")}{charts.numbers_strip(cells)}</section>')
    shape_say = say('Where the night’s moments fell on the tape, scored by the analyzer — not chosen for you. '
                    'Every mark opens the tape where it fell; the table under it reads them in order.') if mos else ""
    spic = charts.meeting_shape(m.get("moments") or [], dur, pid, base=base)
    parts.append(f'<section class="fp-part">{kicker("the shape of the meeting")}'
                 + spic + pictures.take(f"m-{pictures.key(pid)}-shape", spic,
                                        f"The shape of the meeting — {m.get('title') or pid}", f"{base}/m/{pid}",
                                        legend=pictures.LEGEND["shape"])
                 + shape_say + "</section>")
    if top:
        pulls = "".join(
            f'<a class="pull" href="{at(mo["t"])}"><span class="ts">{hms(mo["t"])}</span>'
            f'<span class="mk">{esc(mo.get("kind") or "")}</span> {esc(cut_words(mo.get("quote"), 160))}</a>' for mo in top)
        parts.append(f'<section class="fp-part"><div class="pulls">{kicker("the moments that decided it — from the tape")}{pulls}</div></section>')
    if votes:
        vrows = "".join(
            f'<a class="vteaser" href="{at(v.get("t"))}"><span class="vt-motion">{esc(str(v.get("motion") or "")[:110])}</span>'
            f'<span class="vt-meta"><span class="outcome">{esc(v.get("outcome") or "")}</span> '
            f'<span class="tally">{esc(v.get("tally") or "")}</span> · {hms(v.get("t"))}</span></a>' for v in votes[:8])
        parts.append(f'<section class="fp-part">{kicker("the roll calls — read from this tape")}<div class="vteasers">{vrows}</div>'
                     + say('Read from the transcript; a name may be misheard — verify against the official minutes.') + "</section>")
    else:
        parts.append(f'<section class="fp-part">{kicker("the roll calls")}<p class="hint">No roll call was read from this tape — the body may have voted by voice, or not at all.</p></section>')
    if lenses:
        parts.append(f'<section class="fp-part">{kicker("how the meeting framed it — eight civic lenses, counted from its own words")}'
                     + charts.lens_bars(lenses)
                     + say('Counted, not modeled — each lens is a word list; drift compares the first half of the night to the second.') + "</section>")
    if qs:
        parts.append(f'<section class="fp-part">{kicker("the questions asked — by what they ask about")}'
                     + charts.question_bars(qs, pid, base=base)
                     + say(f'{n_of(len(qs), "question")} the analyzer typed by what they ask about; each type opens the tape at the first one.') + "</section>")
    words = [w for w in insight.word_freq(segs, top=80)] if segs else []
    if words:
        w0 = words[0]
        mpic = charts.word_cloud(words, base=base, href=lambda w: at(w.get("t") or 0),
                                 each="each opens the tape at its first mention")
        parts.append(f'<section class="fp-part">{kicker("the meeting in words — what was said most")}'
                     + mpic + pictures.take(f"m-{pictures.key(pid)}-words", mpic,
                                            f"The meeting in words — {m.get('title') or pid}", f"{base}/m/{pid}",
                                            legend=pictures.LEGEND["cloud"])
                     + say(f'“{esc(w0["word"])}” came up {n_of(int(w0["count"]), "time")}. Every word opens the tape at its first mention.') + "</section>")
    topics = _real_topics(an.get("topics"))
    sparks = charts.sparklines(segs, [t["name"] for t in topics[:6]], dur, pid, base=base) if segs and topics else ""
    if sparks:
        parts.append(f'<section class="fp-part">{kicker("where the words fell — the night’s topics, slice by slice")}'
                     + sparks + say('The highlighter’s sparkline search, pressed: a taller bar is a slice of the tape where the topic came up more; each bar opens the tape there.') + "</section>")
    named = []
    for k, label in (("people", "people"), ("organizations", "organizations"), ("places", "places"), ("money", "money")):
        vals = [_name(e) for e in (ents.get(k) or [])][:8]
        vals = [v for v in vals if v]
        if vals:
            named.append(f'<p class="fp-named"><span class="pb-rdtag">{esc(label)}</span> {esc(" · ".join(vals))}</p>')
    if named:
        parts.append(f'<section class="fp-part">{kicker("who and what was named")}{"".join(named)}'
                     + say('Names the analyzer lifted from the transcript — a name may be misheard.') + "</section>")
    if docs:
        drows = "".join(
            (f'<a class="docrow" href="{esc(d["url"])}" target="_blank" rel="noopener">' if d.get("url") else '<div class="docrow">')
            + f'📄 <b>{esc(d.get("kind") or "document")}</b> {esc(str(d.get("title") or "")[:70])}'
            + (f' <span class="lmeta">{d.get("pages", 0)} pp</span>' if d.get("pages") else "")
            + ("</a>" if d.get("url") else "</div>") for d in docs[:6])
        parts.append(f'<section class="fp-part">{kicker("the town’s paper — filings for this meeting")}<div class="docrows">{drows}</div></section>')

    thumb = m.get("thumb") or ""
    still = (f'<a class="lead-still" href="{href}"><img src="{esc(thumb)}" alt="" width="320" height="180" loading="lazy">'
             f'<span class="lead-tape">▶ the tape · {hms(dur)} · loads only when you press it</span></a>' if thumb else "")
    meta = " · ".join(x for x in (m.get("town") or "", m.get("date") or "undated",
                                  f'{int(round(dur / 60))} min') if x)
    from . import cuts as _cuts
    cut = _cuts.meeting_cuts(m, base=base)
    night = (f'<a class="btn tp-play" href="{esc(cut["loudest"]["url"])}">▶ the night in {hms(cut["loudest"]["runtime"])}</a>'
             if cut else "")
    close = (f'<div class="fp-close">{night}<a class="btn primary" href="{base}/p#edit&amp;tpl=meeting&amp;ref={esc(pid)}">make this story yours →</a>'
             f'<a class="btn" href="{href}">read the meeting →</a></div>')
    return f'''  <article class="lead fp-story fp-latest" id="latest" data-town="{esc(m.get("town") or "")}" data-body="{esc(m.get("body") or "")}" aria-labelledby="fp-latest-hl">
    <span class="kicker">the latest meeting on the record — what happened</span>
    <div class="lead-grid"><div class="lead-words">
    <a class="lead-hl" href="{href}"><h2 id="fp-latest-hl">{esc(m.get("title") or pid)}</h2></a>
    <p class="lead-meta"><span class="chip">{esc(m.get("body") or "meeting")}</span> {esc(meta)}</p>
    {summary}
    <p class="fp-told">{" ".join(told)}</p>
    <p class="decksrc">counted from the meeting’s own pressed plane — no model wrote a line of it; every number opens the tape</p>
    </div>{still}</div>
    {"".join(parts)}
    {close}
  </article>
'''


# --------------------------------------------------------------------------
# story three — a word, over time (specs/25): the search, told as a story
# --------------------------------------------------------------------------

def _span_words(sec: float) -> str:
    sec = float(sec or 0)
    if sec < 90:
        return "in under two minutes"
    if sec < 3600:
        return f"in {max(2, int(round(sec / 60)))} minutes"
    h, m = int(sec // 3600), int((sec % 3600) // 60)
    return f"over {h} h {m} min" if m else f"over {h} h"


def _month_words(d: str) -> str:
    return month_name(d) or "an undated meeting"


def _day_words(d: str) -> str:
    """'June 18, 2026', or 'an undated meeting' — never the bare word, and
    never a garbage date printed as one (February 30 is undated)."""
    try:
        _dt.datetime.strptime(str(d or "")[:10], "%Y-%m-%d")
    except ValueError:
        return "an undated meeting"
    return day_name(d)


def _town_words(t: str) -> str:
    return f"{t}’s bodies" if t else "meetings with no town recorded"


def topic_issue(d: dict, issues: Sequence[dict]) -> Optional[dict]:
    """The issue the record already tracks under this word, if any: an issue
    whose name or an alias IS one of the topic's phrases (case-blind)."""
    want = {str(p).lower() for p in d.get("phrases") or []}
    want.add(str(d.get("long") or "").lower())
    for i in sorted(issues, key=lambda i: (-int(i.get("n_meetings") or 0), str(i.get("slug") or ""))):
        names = {str(i.get("name") or "").lower()} | {str(a).lower() for a in (i.get("aliases") or [])}
        if names & want:
            return i
    return None


def topic(d: dict, base: str = "/app", issues: Sequence[dict] = (), examples: Sequence[str] = (),
          own_page: bool = True) -> str:
    """The topic story, pressed whole (specs/25 §2): a counted headline and
    lede, the numbers, mentions month by month, where on each night the word
    fell, the words said beside it, the first time it came up each night (each
    a cuttable moment), the supercut, and how to make one of these. Every
    number a receipt; no model wrote a line of it."""
    from . import topic as _topic
    q, town, name = d["q"], d["town"], d["name"]
    key = f'topic-{d["slug"]}'
    at = lambda pid, t: f'{base}/m/{esc(pid)}#t{int(float(t or 0))}'
    search_raw = _topic.search_url(q, town, base)          # for cells that escape their own href
    search = search_raw.replace("&", "&amp;")               # for hrefs written inline
    search_all = _topic.search_url(q, "", base)
    first, latest, peak = d["first"], d["latest"], d["peak"]
    # -- the lede, counted -------------------------------------------------
    lede = []
    lede.append(f'The first time anyone said “{esc(q)}” on {esc(town)}’s record was '
                f'<a href="{at(first["pid"], first["t"])}">{esc(_day_words(first["date"]))}</a>, '
                f'{hms(first["t"])} into a {esc(first["body"] or "meeting")} meeting: '
                f'“{esc(first["quote"])}”.')
    gap = int(d.get("gap") or 0)
    if gap == 1:
        lede.append("The next meeting passed without it.")
    elif gap > 1:
        lede.append(f"{gap} meetings then passed without it.")
    share = round(100 * peak["mentions"] / max(1, d["mentions"]))
    if peak["pid"] != first["pid"]:
        lede.append(f'It peaked on <a href="{at(peak["pid"], peak["t"])}">{esc(_day_words(peak["date"]))}</a>, '
                    f'when the {esc(peak["body"] or "board")} said it {n_of(peak["mentions"], "time")} '
                    f'{_span_words(peak["span"])} — {share}% of every mention on the record.')
    else:
        lede.append(f'That night is still the peak: {n_of(peak["mentions"], "mention")} '
                    f'{_span_words(peak["span"])}, {share}% of every one on the record.')
    bodies = the_list([f'the {b["body"]}' for b in d["bodies"] if b["body"] and b["body"] != "—"])
    cw = [w["word"] for w in d.get("cowords") or []][:4]
    lede.append(f'In all, <a href="{search}">{n_of(d["mentions"], "mention")}</a> across '
                f'{d["n_meetings"]} of {esc(town)}’s <a href="{base}/s">{n_of(d["n_town_meetings"], "meeting")}</a>'
                + (f', by {esc(bodies)}' if bodies else "")
                + (f'; the words said beside it most: {esc(", ".join(cw))}' if cw else "") + '.')
    if latest["pid"] != first["pid"] or latest["t"] != first["t"]:
        lede.append(f'The latest was <a href="{at(latest["pid"], latest["t"])}">{esc(_day_words(latest["date"]))}</a>: '
                    f'“{esc(latest["quote"])}”.')
    for e in (d.get("elsewhere") or [])[:2]:
        lede.append(f'{esc(_town_words(e["town"]))} said it in {n_of(e["moments"], "line")} across '
                    f'{n_of(e["meetings"], "meeting")} — <a href="{esc(search_all)}">the whole record’s search</a> reads them together.')
    # -- the pictures -------------------------------------------------------
    reel = d["reel"]
    cells = [(d["mentions"], "mentions", search_raw),
             (f'{d["n_meetings"]} of {d["n_town_meetings"]}', "meetings", f"{base}/s"),
             (len(d["bodies"]), "bodies", f"{base}/analytics"),
             (_month_words(first["date"]).replace(" ", "\u00a0"), "first said", at(first["pid"], first["t"])),
             (_month_words(latest["date"]).replace(" ", "\u00a0"), "latest", at(latest["pid"], latest["t"])),
             (hms(reel["short_runtime"]), "the supercut", reel["short"])]
    parts: List[str] = []
    parts.append(f'<section class="fp-part">{kicker(f"“{esc(q)}”, by the numbers")}{charts.numbers_strip(cells)}</section>')
    # when it came up (specs/29 board 5): each meeting a town-coloured dot on the year
    tl = charts.timeline_dots([{**r, "town": r.get("town") or town} for r in d["meetings"]], base=base, q=q)
    if tl:
        parts.append(f'<section class="fp-part">{tl}</section>')
    busiest = max(d["months"], key=lambda x: (int(x.get("mentions") or 0), x["month"])) if d["months"] else None
    silent = [x for x in d["months"] if x.get("meetings") and not x.get("said")]
    msay = ""
    if busiest and busiest.get("mentions"):
        msay = say(f'{esc(month_name(busiest["month"] + "-01"))} was the loudest month — '
                   f'{n_of(int(busiest["mentions"]), "mention")} in {busiest["said"]} of {n_of(int(busiest["meetings"]), "meeting")}'
                   + (f'; in {n_of(len(silent), "month")} the town met and never said it' if silent else "")
                   + '. A dot is a meeting: filled where the word came up, hollow where it did not. Every bar opens the tape at the month’s first mention.')
    # the three pictures as files (specs/27 §3.3) — the lead story's are the
    # record's most shareable, and a slide deck wants the picture, not a screenshot
    story_page = f"{base}/topic/{d['slug']}/"
    how_it_talks = f"How {town} talks about {name}"
    def pic(kind: str, draw, title: str, what: str) -> str:
        # the link names its picture — ten on a page must not read alike
        return pictures.link(pictures.put(f"topic-{pictures.slug(d['slug'])}-{kind}", draw(title)),
                             pictures.slug(f"{how_it_talks} {what}") + ".svg", title)
    src = pictures.source(story_page)
    mpic = pic("months", lambda t: pictures.months_svg(d["months"], t, src),
               f"{how_it_talks} — mentions, month by month", "mentions month by month") if d["months"] else ""
    parts.append(f'<section class="fp-part">{kicker("mentions, month by month")}'
                 + charts.month_bars(d["months"], d["meetings"], base=base) + mpic + msay + "</section>")
    tapes = charts.term_tapes(d["meetings"], base=base)
    if tapes:
        tapes += pic("tapes", lambda t: pictures.tapes_svg(d["meetings"], t, src),
                     f"{how_it_talks} — where it fell, night by night", "where it fell")
        parts.append(f'<section class="fp-part">{kicker("where it fell — every night that said it, slice by slice")}' + tapes
                     + say(f'Each row is a tape, start to end; a taller bar is a slice where “{esc(q)}” came up more. '
                           f'On {esc(_day_words(peak["date"]))} the {esc(peak["body"] or "board")} said it '
                           f'{n_of(peak["mentions"], "time")} {_span_words(peak["span"])} — one stretch of the night. Every bar opens the tape there.') + "</section>")
    if d.get("cowords"):
        w0 = d["cowords"][0]
        parts.append(f'<section class="fp-part">{kicker("the words beside it — what was said in the same breath")}'
                     + charts.coword_bars(d["cowords"], q, base=base, town=town)
                     + pic("words", lambda t: pictures.words_svg(d["cowords"], t, src),
                           f"{how_it_talks} — the words beside it", "the words beside it")
                     + say(f'Counted in each line that says “{esc(q)}” and the lines either side of it, civic stopwords out: '
                           f'“{esc(w0["word"])}” led with {n_of(int(w0["count"]), "mention")}. Each word opens the record’s search for the two together.') + "</section>")
    # the chapters — the first time it came up, each night; cuttable
    chs = []
    for ch in d["chapters"]:
        chs.append(
            f'<div class="tq-wrap"><a class="tq" href="{at(ch["pid"], ch["t"])}" data-pid="{esc(ch["pid"])}" '
            f'data-t="{_topic._r1(ch["t"])}" data-quote="{esc(cut_words(ch["quote"], 120))}" '
            f'data-mtitle="{esc(ch["title"])}" data-body="{esc(ch["body"])}" data-town="{esc(town)}" data-date="{esc(ch["date"])}">'
            f'<span class="tq-when">{esc(_day_words(ch["date"]))} · {esc(ch["body"] or "meeting")}</span>'
            f'<span class="tq-n">{n_of(ch["n"], "line")} that night</span>'
            f'<span class="tq-q">“{esc(ch["quote"])}”</span>'
            f'<span class="tq-ts"><span class="ts">{hms(ch["t"])}</span> on the tape</span></a></div>')
    parts.append(f'<section class="fp-part">{kicker("the first time it came up, each night")}'
                 f'<div class="tq-list">{"".join(chs)}</div>'
                 + say(f'One line per meeting, in order — the moment the word first entered the room, with the line before and after it. '
                       f'Every line opens the tape; the tick beside it cuts the line into your reel. '
                       f'<a href="{search}">All {n_of(d["moments"], "line")} →</a>') + "</section>")
    # the supercut — and the full cut, capped so its link stays under a host's
    # URL limit, its clips spread from the first night to the latest
    full_said = (f'{reel["full_n"]} of {n_of(reel.get("full_all", reel["full_n"]), "clip")}, first to latest'
                 if reel.get("full_all", reel["full_n"]) > reel["full_n"] else n_of(reel["full_n"], "clip"))
    # past the link's cap the supercut is not every night: it says so
    nights = len(d.get("chapters") or [])
    short_said = (f'{reel["short_n"]} of {nights} nights, one clip each, first to latest' if nights > reel["short_n"]
                  else f'{n_of(reel["short_n"], "clip")}, one per night')
    parts.append(
        f'<section class="fp-part">{kicker("the supercut — every one of those moments, played in order")}'
        f'<div class="tp-cut">'
        f'<a class="btn primary tp-play" href="{esc(reel["short"])}">▶ play the supercut</a>'
        f'<span class="tp-cutmeta">{short_said} · {hms(reel["short_runtime"])}</span>'
        f'<a class="btn tp-full" href="{esc(reel["full"])}">the full cut — {full_said} · {hms(reel["full_runtime"])}</a>'
        f'</div>'
        + say('A reel plays the tape clip to clip, in this browser, and the whole reel lives in its link — copy the address and it is shared; '
              'open it and press <b>make this reel yours</b> to re-cut it. Nothing is uploaded, nothing about you is kept.')
        + "</section>")
    # how to make one of these
    tries = "".join(f'<a class="btn tp-try" href="{esc(charts.search_url(str(x), "", base))}">{esc(x)}</a>' for x in examples[:6])
    parts.append(
        f'<section class="fp-part tp-howto">{kicker("make one of these — this story came from one search")}'
        f'<ol class="tp-steps">'
        f'<li><b>Search a word.</b> A program, a street, a worry — “{esc(q)}” was this one. Three letters is enough; the record searches as you type.</li>'
        f'<li><b>See how it was said.</b> The record counts every line of every transcript that says it and draws the count — month by month, night by night, the words beside it. Nothing modeled; every number opens the tape.</li>'
        f'<li><b>Cut it, share it.</b> Press ▶ and the moments play as a reel. Press ✂ on any line to cut your own — from a search, a transcript, an issue. The link is the share: no account, nothing uploaded.</li>'
        f'</ol>'
        + (f'<p class="tp-tries"><span class="kicker">try one</span>{tries}</p>' if tries else "")
        + "</section>")
    # the close
    iss = topic_issue(d, issues)
    close = (f'<div class="fp-close"><a class="btn primary" href="{search}">search “{esc(q)}” yourself →</a>'
             + (f'<a class="btn" href="{base}/topic/{esc(d["slug"])}/">this story’s own page →</a>' if own_page
                else f'<a class="btn" href="{base}/">← the record’s front page</a>')
             + (f'<a class="btn" href="{base}/i/{esc(iss["slug"])}">the thread the record tracks: {esc(iss["name"])} →</a>' if iss else "")
             + '</div>')
    headline = f'How {esc(town)} talks about {esc(name)}'
    said = " or ".join(f"“{esc(p)}”" for p in d["phrases"])
    return f'''  <article class="fp-story tp-story" id="{key}" aria-labelledby="fp-{key}-hl">
    <span class="kicker">a word, over time — the record’s search for “{esc(q)}”, told as a story</span>
    <h2 class="fp-hl" id="fp-{key}-hl">{headline}</h2>
    <p class="fp-lede">{" ".join(lede)}</p>
    <p class="decksrc">counted from the transcripts themselves when this edition was pressed — every line that says {said}, whole-word; no model wrote a line of it; every number opens the tape</p>
    {"".join(parts)}
    {close}
  </article>
'''


# ==========================================================================
# the broadsheet (specs/29) — the words beside the front page's pictures.
# Every sentence is a rule over the pressed planes; every number a receipt.
# ==========================================================================

_ONES = ("zero one two three four five six seven eight nine ten eleven twelve thirteen "
         "fourteen fifteen sixteen seventeen eighteen nineteen").split()
_TENS = ("", "", "twenty", "thirty", "forty", "fifty")


def number_words(n: int) -> str:
    """0–59 in words — the broadsheet counts hours and minutes in prose."""
    n = int(n)
    if n < 20:
        return _ONES[n]
    if n < 60:
        t, o = divmod(n, 10)
        return _TENS[t] + (f"-{_ONES[o]}" if o else "")
    return str(n)


def hours_prose_short(hours: float) -> str:
    """'16.8 hours', '1 hour', '0.6 hours' — a chapter's tape, counted."""
    h = float(hours or 0)
    return "1 hour" if h == 1 else f"{h:g} hours"


def hours_prose(seconds: float) -> str:
    """'two hours and forty-six minutes' — the tape's length, said."""
    s = int(seconds or 0)
    h, m = s // 3600, (s % 3600) // 60
    hw = f'{number_words(h)} hour{"" if h == 1 else "s"}' if h else ""
    mw = f'{number_words(m)} minute{"" if m == 1 else "s"}' if m else ""
    if hw and mw:
        return f"{hw} and {mw}"
    return hw or mw or "under a minute"


# a lens, as the thing the room was talking about
LENS_NOUN = {"financial": "money", "safety": "safety", "community": "community",
             "environmental": "the environment", "legal": "the law", "equity": "equity",
             "infrastructure": "infrastructure", "process": "procedure"}
DRIFT_WORD = {"rising": "rising", "fading": "fading", "steady": "steady through the night"}


def month_span_words(months: Sequence[str]) -> str:
    """'December', 'June and July', 'March to May' — a chapter's span."""
    ms = [m for m in months if charts.is_month(m)]
    if not ms:
        return "undated"
    names = [_dt.datetime.strptime(m, "%Y-%m").strftime("%B") for m in ms]
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return f"{names[0]} to {names[-1]}"


def tonight(m: dict, base: str = "/app") -> dict:
    """Tonight's tape, told: a counted headline, the counted lede (with its
    topics as searches), the kicker and meta line, the money named on the
    tape, the labels — the words around the frame and the score."""
    pid = str(m.get("pid") or "")
    an = m.get("analysis") or {}
    fr = an.get("framing") or {}
    lenses = sorted((l for l in (fr.get("lenses") or []) if int(l.get("count") or 0) > 0),
                    key=lambda l: (-int(l["count"]), str(l.get("lens"))))
    ftot = int(float(fr.get("total") or 0))
    dur = float(m.get("duration") or 0)
    body = str(m.get("body") or "meeting")
    town = str(m.get("town") or "")
    day = day_name(m.get("date") or "")
    topics = _real_topics(an.get("topics"))
    href = f"{base}/m/{esc(pid)}"
    # the headline: the tape's length and the lens that framed it
    if lenses:
        headline = f'{hours_prose(dur).capitalize()} of the {esc(body)}, and {esc(LENS_NOUN.get(lenses[0]["lens"], lenses[0]["lens"]))} was the frame'
    else:
        headline = f'{hours_prose(dur).capitalize()} of the {esc(body)}, {esc(day)}'
    # the lede: counted from the plane, every number a receipt
    lede = [f'<a href="{href}">{hours_prose(dur).capitalize()}</a> on {esc(day)}.']
    if lenses and ftot:
        l0 = lenses[0]
        part = (f'Of {ftot} words the record files under a lens, <a href="{href}#framing">{int(l0["count"])}</a> were '
                f'{esc(l0["lens"])} and {DRIFT_WORD.get(l0.get("drift"), "steady")}')
        if len(lenses) > 1:
            l1 = lenses[1]
            part += f'; {int(l1["count"])} were about {esc(l1["lens"])} and {DRIFT_WORD.get(l1.get("drift"), "steady")}'
        lede.append(part + ".")
    if topics:
        links = [f'<a href="{charts.search_url(t["name"], "", base).replace("&", "&amp;")}">{esc(t["name"])}</a>' for t in topics[:4]]
        lede.append(f'The room kept returning to {the_list(links)}.')
    money = []
    for e in ((an.get("entities") or {}).get("money") or [])[:6]:
        if e.get("t") is None or not e.get("name"):
            continue
        money.append({"t": float(e["t"]), "label": charts.money_label(e["name"]),
                      "count": int(e.get("count") or 0)})
    money.sort(key=lambda x: (x["t"], x["label"]))
    origin = str(m.get("summary_origin") or "")
    labels = ["summary · " + origin[3:] if origin.startswith("ai:") else "summary drawn from the tape" if m.get("summary") else "no summary yet",
              "counted by the record"]
    kicker = " · ".join(x for x in ("Tonight’s tape", town, body, day) if x)
    n_caps = int(m.get("n_segments") or 0)
    meta = f'{hms(dur)} · {n_caps:,} caption{"" if n_caps == 1 else "s"}' if n_caps else hms(dur)
    return {"pid": pid, "headline": headline, "lede": " ".join(lede), "kicker": kicker,
            "meta": meta, "money": money, "labels": labels, "town": town, "body": body,
            "title": str(m.get("title") or pid), "date": str(m.get("date") or "")}


def now_words(d: dict) -> str:
    """Why the record marked the moment under the playhead."""
    kind = str(d.get("kind") or "")
    if kind == "vote":
        return "the record read a roll call here"
    if kind == "tension":
        return "the record heard the room push back here"
    return "the record heard a motion carry here" if str(d.get("reason") or "") == "passes" else "the record heard a decision here"


# --------------------------------------------------------------------------
# the year in tapes — four chapters, written from the counts
# --------------------------------------------------------------------------

def _split_months(months: Sequence[str], k: int = 4) -> List[List[str]]:
    """The run of months in k near-equal contiguous spans (the longer spans
    first), never more spans than months."""
    ms = list(months)
    k = max(1, min(k, len(ms)))
    base_, extra = divmod(len(ms), k)
    out, i = [], 0
    for j in range(k):
        n = base_ + (1 if j < extra else 0)
        out.append(ms[i:i + n])
        i += n
    return out


def chapters(meetings: Sequence[dict], votes: Sequence[dict], framing_rows: Sequence[dict],
             base: str = "/app", k: int = 4) -> List[dict]:
    """The year in four chapters, each titled by its span and the fact that
    marks it — the roll calls, a town arriving, the budget night, the
    marathons, the busiest month — and told in a counted paragraph. Pure
    over the planes; every number a receipt."""
    dated = sorted((m for m in meetings if charts.is_month(m.get("date"))),
                   key=lambda m: (str(m["date"]), str(m.get("pid"))))
    months = charts.month_range([str(m["date"])[:7] for m in dated])
    if not months:
        return []
    spans = _split_months(months, k)
    by_pid = {str(m.get("pid")): m for m in dated}
    fshare = {}
    for r in framing_rows:
        tot = float(r.get("total") or 0)
        if tot:
            fshare[str(r.get("pid"))] = float((r.get("lenses") or {}).get("financial") or 0) / tot
    towns_first: Dict[str, dict] = {}
    for m in dated:
        t = str(m.get("town") or "")
        if t and t not in towns_first:
            towns_first[t] = m
    first_town = str(dated[0].get("town") or "")
    cov: Dict[str, int] = {}
    for m in dated:
        cov[str(m["date"])[:7]] = cov.get(str(m["date"])[:7], 0) + 1
    busiest = max(cov, key=lambda mo: (cov[mo], mo)) if cov else ""
    if busiest and sum(1 for v in cov.values() if v == cov[busiest]) > 1:
        busiest = ""          # a tie is not a busiest month
    longest = max(dated, key=lambda m: (float(m.get("duration") or 0), str(m["date"]))) if dated else None
    budget = max((m for m in dated if fshare.get(str(m.get("pid")))), key=lambda m: (fshare[str(m.get("pid"))], str(m["date"])), default=None)
    vs = [v for v in votes if v.get("pid") in by_pid]
    votes_by_span = []
    used = set()
    out = []
    for i, span in enumerate(spans):
        ms = [m for m in dated if str(m["date"])[:7] in span]
        hours = round(sum(float(m.get("duration") or 0) for m in ms) / 3600, 1)
        sv = [v for v in vs if str(by_pid[v["pid"]]["date"])[:7] in span]
        votes_by_span.append(len(sv))
        out.append({"i": i, "months": list(span), "meetings": ms, "hours": hours, "votes": sv})
    most_votes = max(votes_by_span) if votes_by_span else 0
    result = []
    for ch in out:
        ms, span, sv = ch["meetings"], ch["months"], ch["votes"]
        facts: List[Tuple[str, str]] = []   # (title fact, sentence)
        at = lambda m: f'{base}/m/{esc(m["pid"])}'
        if sv and len(sv) == most_votes and "rolls" not in used:
            passed = sum(1 for v in sv if v.get("outcome") == "passes")
            failed = [v for v in sv if v.get("outcome") == "fails"]
            sent = (f'{n_of(len(sv), "roll call")} of the record’s {len(vs)} were taken here: {passed} passed'
                    + (f', {len(failed)} failed' if failed else "")
                    + (f' — the one that failed, {esc(failed[0].get("tally") or "")}, on <a href="{at(by_pid[failed[0]["pid"]])}#t{int(float(failed[0].get("t") or 0))}">{esc(day_name(by_pid[failed[0]["pid"]]["date"]))}</a>' if len(failed) == 1 else "")
                    + ".")
            facts.append(("rolls", "the roll calls", sent))
        for town, fm in towns_first.items():
            if town != first_town and str(fm["date"])[:7] in span and f"arrives:{town}" not in used:
                facts.append((f"arrives:{town}", f"{town} arrives",
                              f'{esc(town)}’s first tape on the record is <a href="{at(fm)}">{esc(fm.get("body") or "a meeting")}, {esc(day_name(fm["date"]))}</a>.'))
        if budget is not None and str(budget["date"])[:7] in span and "budget" not in used:
            facts.append(("budget", "the budget night",
                          f'The loudest money night of the year is <a href="{at(budget)}">{esc(day_name(budget["date"]))}</a>: '
                          f'{round(100 * fshare[str(budget.get("pid"))])}% of the words the record files under a lens were financial.'))
        if longest is not None and str(longest["date"])[:7] in span and "longest" not in used:
            facts.append(("longest", "the marathons" if len(ms) > 1 else "the longest night",
                          f'The year’s longest tape is here: <a href="{at(longest)}">{esc(longest.get("body") or "a meeting")}, {esc(day_name(longest["date"]))}</a>, {hms(longest.get("duration") or 0)}.'))
        if busiest and busiest in span and "busiest" not in used:
            facts.append(("busiest", "the busiest month",
                          f'{esc(month_name(busiest + "-01"))} is the busiest month on the record: {n_of(cov[busiest], "tape")}.'))
        towns = sorted({str(m.get("town") or "") for m in ms if m.get("town")})
        bodies = sorted({str(m.get("body") or "") for m in ms if m.get("body")})
        opener = ("No tape on the record for these months." if not ms else
                  f'{n_of(len(ms), "tape")}, {hours_prose_short(ch["hours"])}'
                  + (f' — {esc(the_list(towns))}' if len(towns) > 1 else "")
                  + (f': {esc(the_list(["the " + b for b in bodies[:4]]))}' if bodies else "") + ".")
        chosen = facts[0] if facts else ("tapes", n_of(len(ms), "tape") if ms else "a quiet spell", "")
        used.add(chosen[0])
        title = f'{month_span_words(span)} — {chosen[1]}'
        sentences = [opener] + [f[2] for f in facts[:2] if f[2]]
        html = " ".join(sentences)
        plain = _html.unescape(re.sub(r"<[^>]+>", "", html))
        result.append({"i": ch["i"], "months": span, "title": title, "blurb": plain, "html": html,
                       "n": len(ms), "hours": ch["hours"]})
    return result


# --------------------------------------------------------------------------
# the four columns and the river — the readings under the pictures
# --------------------------------------------------------------------------

def _ratio_words(a: float, b: float) -> str:
    if b <= 0:
        return ""
    r = a / b
    if r >= 2.75:
        return "three times"
    if r >= 1.75:
        return "twice"
    if r >= 1.4:
        return "half again"
    return ""


def vocab_words(shares: Sequence[dict]) -> Tuple[str, str, str]:
    """(headline, the reading, the count line) for two towns' vocabularies."""
    ts = list(shares)[:2]
    if not ts:
        return "", "", ""
    noun = lambda l: LENS_NOUN.get(l, l)
    top = lambda t: max(charts.LENS_ORDER, key=lambda l: (t["shares"].get(l, 0), -charts.LENS_ORDER.index(l)))
    if len(ts) == 1:
        a = ts[0]
        la = top(a)
        la2 = sorted(charts.LENS_ORDER, key=lambda l: -a["shares"].get(l, 0))[1]
        head = f'{esc(a["town"])} talks {esc(noun(la))}, then {esc(noun(la2))}'
        say = (f'Each bar is a lens’s share of everything the town’s meetings say under a lens. {esc(a["town"])} gives '
               f'{esc(noun(la))} {round(100 * a["shares"][la])}% of its words and {esc(noun(la2))} {round(100 * a["shares"][la2])}%.')
        return head, say, f'{n_of(a["n"], "tape")} so far — one town, one accent.'
    a, b = ts[0], ts[1]
    # the lens each town leans on more than the other, relatively
    lean = lambda x, y: max(charts.LENS_ORDER, key=lambda l: ((x["shares"].get(l, 0) + 0.005) / (y["shares"].get(l, 0) + 0.005), x["shares"].get(l, 0)))
    la, lb = lean(a, b), lean(b, a)
    la2 = sorted((l for l in charts.LENS_ORDER if l != la), key=lambda l: -a["shares"].get(l, 0))[0]
    head = f'{esc(b["town"])} talks {esc(noun(lb))}; {esc(a["town"])} talks {esc(noun(la))} and {esc(noun(la2))}'
    ratio = _ratio_words(b["shares"].get(lb, 0), a["shares"].get(lb, 0))
    tb = top(b)
    say = (f'Each bar is a lens’s share of everything a town’s meetings say under a lens. {esc(a["town"])} gives '
           f'{esc(noun(la))} {round(100 * a["shares"][la])}% of its words and {esc(noun(la2))} {round(100 * a["shares"][la2])}%; '
           f'{esc(b["town"])} gives {esc(noun(lb))} {round(100 * b["shares"][lb])}%'
           + (f', {ratio} {esc(a["town"])}’s share' if ratio else "")
           + (f', and {esc(noun(tb))} {round(100 * b["shares"][tb])}%.' if tb != lb else "."))
    # the number word alone is capitalised — .capitalize() on the whole line
    # would lowercase the town (a skeptic's catch on the first fold)
    count = (f'{number_words(b["n"]).capitalize()} {esc(b["town"])} tape{"" if b["n"] == 1 else "s"} against '
             f'{number_words(a["n"])} from {esc(a["town"])}'
             + (" — early, and already a different accent." if a["n"] + b["n"] < 60 else "."))
    return head, say, count


def names_words(names: Sequence[dict], months: Sequence[str]) -> Tuple[str, str]:
    """(headline, reading) for who, and when."""
    ms = [m for m in months if charts.is_month(m)]
    people = [n for n in names if n.get("kind") == "people"]
    places = [n for n in names if n.get("kind") == "places"]
    if not (people or places) or not ms:
        return "The names the record hears", "The record needs two read meetings before a name keeps coming up."
    head = "The names the record hears, month by month"
    bits = []
    if people:
        p = people[0]
        pm = {str(x.get("date") or "")[:7] for x in (p.get("meetings") or []) if charts.is_month(x.get("date"))}
        bits.append(f'{esc(p["name"])} is named in {number_words(len(pm))} of the {number_words(len(ms))} months')
    if places:
        pl = places[0]
        ds = sorted(str(x.get("date") or "")[:7] for x in (pl.get("meetings") or []) if charts.is_month(x.get("date")))
        if ds:
            bits.append(f'{esc(pl["name"])} runs from {esc(month_name(ds[0] + "-01").split()[0])} to {esc(month_name(ds[-1] + "-01").split()[0])}')
    say = "; ".join(bits) + ". A dot is a month the name was said; bigger, said in more meetings."
    return head, say


def rolls_words(votes: Sequence[dict], meetings_by_pid: Dict[str, dict]) -> Tuple[str, str, str]:
    """(headline, reading, the officials line) for the roll calls."""
    vs = [v for v in votes if v.get("pid") in meetings_by_pid]
    if not vs:
        return "No roll call read yet", "No roll call has been read from a tape yet — the bodies’ votes so far were by voice, or unrecorded.", ""
    passed = sum(1 for v in vs if v.get("outcome") == "passes")
    failed = [v for v in vs if v.get("outcome") == "fails"]
    head = f'{n_of(len(vs), "vote")}, {passed} passed' + (f', {"one" if len(failed) == 1 else len(failed)} that failed' if failed else ", none failed")
    who = sorted({f'{meetings_by_pid[v["pid"]].get("town") or ""} {meetings_by_pid[v["pid"]].get("body") or ""}'.strip() for v in vs})
    dated = sorted(str(meetings_by_pid[v["pid"]].get("date") or "") for v in vs if charts.is_month(meetings_by_pid[v["pid"]].get("date")))
    span = (f', {esc(month_name(dated[0]).split()[0])} to {esc(month_name(dated[-1]).split()[0])}' if dated and month_name(dated[0]) != month_name(dated[-1])
            else f', in {esc(month_name(dated[0]))}' if dated else "")
    # "unanimous among those voting" is read from the rolls — every passed
    # vote must carry one, and none may hold a no
    rolled = [v for v in vs if v.get("outcome") == "passes" and v.get("roll")]
    unanimous = bool(rolled) and len(rolled) == passed and \
        all(not any(str(r.get("vote") or "").lower() in ("no", "nay", "n") for r in v["roll"]) for v in rolled)
    say = (f'Every roll call on the record so far is {esc(the_list([w + "’s" for w in who]))}{span}'
           + ("; each unanimous among those voting" if unanimous and passed else "")
           + "; the number in each square is the ayes.")
    if len(failed) == 1:
        f = failed[0]
        say += f' The rust square is the one that failed, {esc(f.get("tally") or "")}, on {esc(day_name(meetings_by_pid[f["pid"]].get("date") or ""))}.'
    elif failed:
        say += f' The rust squares are the {len(failed)} that failed.'
    counts: Dict[str, int] = {}
    for v in vs:
        for r in (v.get("roll") or []):
            nm = str(r.get("name") or "").strip()
            if nm:
                counts[nm] = counts.get(nm, 0) + 1
    top = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:2]
    line = ""
    if top:
        line = f'{esc(top[0][0])} appears in {top[0][1]} of the {len(vs)} rolls' + (f', {esc(top[1][0])} in {top[1][1]}' if len(top) > 1 else "") + "."
    return head, say, line


def thread_words(t: dict) -> Tuple[str, str]:
    """(headline, reading) for the thread column — a recurring topic."""
    name = _topic_name(t)
    ms = sorted((x for x in (t.get("meetings") or []) if charts.is_month(x.get("date"))), key=lambda x: str(x["date"]))
    if not ms:
        return f'“{esc(name)}”', "The record needs two read meetings before a thread has a season."
    first, last = ms[0], ms[-1]
    n = len(t.get("meetings") or [])
    mf, ml = month_name(first["date"]).split()[0], month_name(last["date"]).split()[0]
    head = f'“{esc(name)}” — {n_of(int(t.get("count") or 0), "time")}, {number_words(n)} night{"" if n == 1 else "s"}, {esc(mf)} to {esc(ml)}' \
        if mf != ml else f'“{esc(name)}” — {n_of(int(t.get("count") or 0), "time")}, {number_words(n)} night{"" if n == 1 else "s"} in {esc(mf)}'
    say = (f'The phrase first lands on {esc(day_name(first["date"]))}'
           + (f' and returns {number_words(n - 1)} time{"" if n - 1 == 1 else "s"}, last on {esc(day_name(last["date"]))}.' if n > 1 else "."))
    return head, say


def river_words(d: dict) -> str:
    """The italic reading under the river: the widest band, the lens that
    widens when the second town joins, the night one lens peaks."""
    ms = d.get("meetings") or []
    if len(ms) < 2:
        return ""
    order = d.get("order") or list(charts.LENS_ORDER)
    widest = {}
    for m in ms:
        l = max(order, key=lambda l: (m["shares"].get(l, 0), -order.index(l)))
        widest[l] = widest.get(l, 0) + 1
    la = max(widest, key=lambda l: (widest[l], -order.index(l)))
    noun = lambda l: LENS_NOUN.get(l, l)
    bits = [f'{esc(noun(la)).capitalize()} is the widest band on {number_words(widest[la])} of the {number_words(len(ms))} nights']
    j = d.get("joins")
    if j is not None and 0 < j < len(ms):
        before, after = ms[:j], ms[j:]
        mean = lambda xs, l: sum(x["shares"].get(l, 0) for x in xs) / max(1, len(xs))
        lb = max(order, key=lambda l: (mean(after, l) - mean(before, l), -order.index(l)))
        if mean(after, lb) - mean(before, lb) >= 0.03:
            bits.append(f'{esc(noun(lb))} widens when {esc(ms[j]["town"])} joins in {esc(month_name(ms[j]["date"]).split()[0] if charts.is_month(ms[j]["date"]) else "an undated month")}')
    peak_l, peak_m, peak_v = None, None, 0.0
    for m in ms:
        for l in order:
            if l == la:
                continue
            if m["shares"].get(l, 0) > peak_v:
                peak_l, peak_m, peak_v = l, m, m["shares"][l]
    if peak_l and peak_v >= 0.2:
        bits.append(f'{esc(noun(peak_l))} flares on {esc(day_name(peak_m["date"]))}, {round(100 * peak_v)}% of that night’s framed words')
    return "; ".join(bits) + "."
