"""The week in the record: a calendar week of the record's meetings — Monday
to Sunday, by the meetings' own dates — counted into one page, as a weekly
edition is: the meetings, what was decided, the sums named, the threads
that moved, and how the week talked against the whole record.

Every number here is counted from what the press already builds (the
meetings' own votes, moments, money and framing; the issues' timelines) —
no model writes a word of it, and nothing new is stored. A week keeps its
address (`/app/week/<its Monday>/`), so a past week's page is a permanent
page and the week feed has one item per week; `/app/week/` is the latest.
Pure over the press's meetings and issues, so the desk bake and the hosted
press count a week alike.
"""

from __future__ import annotations

import datetime as _dt
import re
from typing import Dict, List, Optional, Sequence

from . import charts

SHOWN = 12            # the most rows a list on the page shows; the rest are said, and live on the meetings' pages
DECIDED = 6           # the loudest decisions and pushback shown beside the roll calls


_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}")     # the reader's own TP_DAY: a day is written whole


def _day(d) -> Optional[_dt.date]:
    """A real calendar day, or None — a stored '2026-02-30' is undated, and
    so is a day written loosely ('2026-9-1'), as the reader reads it; never a crash."""
    s = str(d or "")
    if not _DAY.match(s):
        return None
    try:
        return _dt.datetime.strptime(s[:10], "%Y-%m-%d").date()
    except ValueError:
        return None


def monday_of(d) -> Optional[str]:
    """The Monday that begins a meeting's week, as 'YYYY-MM-DD' — or None undated."""
    day = _day(d)
    if day is None:
        return None
    return (day - _dt.timedelta(days=day.weekday())).isoformat()


def weeks(meetings: Sequence[dict]) -> List[str]:
    """Every week that holds a dated meeting, newest first."""
    return sorted({k for k in (monday_of(m.get("date")) for m in meetings) if k}, reverse=True)


def week_data(key: str, meetings: Sequence[dict], issues: Sequence[dict], all_weeks: Sequence[str] = ()) -> dict:
    """One week, counted: its meetings (in date order), its tape, its roll
    calls and decisions, its sums, the threads that moved and its lenses."""
    ms = sorted((m for m in meetings if monday_of(m.get("date")) == key),
                key=lambda m: (str(m.get("date")), str(m.get("pid"))))
    pids = {str(m.get("pid")) for m in ms}
    where = lambda m: {"pid": str(m.get("pid")), "date": str(m.get("date") or ""),
                       "body": str(m.get("body") or ""), "town": str(m.get("town") or ""),
                       "title": str(m.get("title") or m.get("pid"))}
    rolls, decisions, sums = [], [], []
    for m in ms:
        for v in (m.get("votes") or []):
            if v.get("t") is None:
                continue
            rolls.append({**where(m), "t": float(v["t"]), "motion": str(v.get("motion") or ""),
                          "outcome": str(v.get("outcome") or ""), "tally": str(v.get("tally") or "")})
        for mo in charts.score_moments(m):
            if mo["kind"] in ("decision", "tension"):
                decisions.append({**where(m), **mo})
        for e in (((m.get("analysis") or {}).get("entities") or {}).get("money") or []):
            if e.get("t") is None or not e.get("name"):
                continue
            sums.append({**where(m), "t": float(e["t"]), "label": charts.money_label(e["name"]),
                         "count": int(e.get("count") or 0)})
    rolls.sort(key=lambda r: (r["date"], r["pid"], r["t"]))
    # the loudest decisions first — the score the moments plane gave them
    decisions.sort(key=lambda d: (-d["score"], d["date"], d["pid"], d["t"]))
    sums.sort(key=lambda s: (-s["count"], s["date"], s["pid"], s["t"]))
    threads = []
    for i in (issues or []):
        if not isinstance(i, dict):
            continue
        tl = [n for n in (i.get("timeline") or []) if isinstance(n, dict)]
        here = [n for n in tl if str(n.get("pid")) in pids]
        if here:
            # how often the week said it — the timeline's own moments in the week's meetings
            said = sum(len(n.get("beads") or []) for n in here)
            threads.append({"slug": str(i.get("slug") or ""), "name": str(i.get("name") or i.get("slug") or ""),
                            "said": said, "week": len({str(n.get("pid")) for n in here}),
                            "all": len({str(n.get("pid")) for n in tl})})
    threads.sort(key=lambda t: (-t["said"], -t["week"], -t["all"], t["name"]))
    ks = list(all_weeks) or weeks(meetings)
    at = ks.index(key) if key in ks else -1
    return {"key": key, "meetings": ms, "seconds": sum(float(m.get("duration") or 0) for m in ms),
            "towns": sorted({str(m.get("town")) for m in ms if m.get("town")}),
            "rolls": rolls, "decisions": decisions, "sums": sums, "threads": threads,
            "lens": lens_shares(ms, meetings),
            "newer": ks[at - 1] if at > 0 else None,
            "older": ks[at + 1] if 0 <= at < len(ks) - 1 else None}


def _framed(ms: Sequence[dict]) -> Dict[str, int]:
    tot: Dict[str, int] = {}
    for m in ms:
        for l in ((((m.get("analysis") or {}).get("framing") or {}).get("lenses")) or []):
            if l.get("lens") in charts.LENS_ORDER:
                tot[l["lens"]] = tot.get(l["lens"], 0) + int(l.get("count") or 0)
    return tot


def lens_shares(week_ms: Sequence[dict], all_ms: Sequence[dict]) -> Optional[dict]:
    """The week's share of framed words by lens beside the whole record's —
    the lens the week leaned to most against its share of the record; None
    when the week framed no words."""
    wk, rec = _framed(week_ms), _framed(all_ms)
    wt, rt = sum(wk.values()), sum(rec.values())
    if not wt or not rt:
        return None
    share = lambda d, t, l: d.get(l, 0) / t
    # the week's own loudest lens, and the one it leaned to most beyond the record's habit
    loudest = max(charts.LENS_ORDER, key=lambda l: (share(wk, wt, l), -charts.LENS_ORDER.index(l)))
    leaned = max(charts.LENS_ORDER, key=lambda l: (share(wk, wt, l) - share(rec, rt, l), -charts.LENS_ORDER.index(l)))
    return {"loudest": loudest, "loudest_week": share(wk, wt, loudest), "loudest_record": share(rec, rt, loudest),
            "leaned": leaned, "leaned_week": share(wk, wt, leaned), "leaned_record": share(rec, rt, leaned),
            "words": wt}


# --------------------------------------------------------------------------
# the page — the broadsheet's own parts (its cards, its section heads, its
# counted headlines), and the week's words, every number a receipt
# --------------------------------------------------------------------------

_OUT = {"passes": "passed", "fails": "failed"}
_KIND = {"decision": "a decision", "tension": "the room pushed back"}


def _when(r: dict, t: Optional[float] = None) -> str:
    from . import story
    bits = [r["body"], story.day_name(r["date"]) if _day(r["date"]) else "undated"]
    if t is not None:
        bits.append(charts.hms(t))
    return " · ".join(charts.esc(b) for b in bits if b)


def _at(r: dict, t: float, base: str) -> str:
    return f'{base}/m/{charts.esc(r["pid"])}#t{int(t)}'


def _more(n: int, what: str) -> str:
    return f'<p class="hint wk-more">and {charts.n_of(n, what)} more, on the meetings’ own pages</p>' if n > 0 else ""


def week_label(key: str) -> str:
    """'The week of September 21, 2026' — a week, by its Monday."""
    from . import story
    return f"The week of {story.day_name(key)}"


def page_body(d: dict, counts: Dict[str, int], stills: Optional[dict], base: str = "/app") -> str:
    """One week's page. `counts` is every week's meeting count, newest first
    in its order (the weeks list at the foot)."""
    from . import broadsheet as bs, story
    esc, n_of = charts.esc, charts.n_of
    ms, key = d["meetings"], d["key"]
    n = len(ms)
    towns = d["towns"]
    nav = []
    if d["older"]:
        nav.append(f'<a class="wk-nav-a" href="{base}/week/{d["older"]}/" rel="prev">← {esc(week_label(d["older"]).replace("The week", "the week"))}</a>')
    if d["newer"]:
        nav.append(f'<a class="wk-nav-a" href="{base}/week/{d["newer"]}/" rel="next">{esc(week_label(d["newer"]).replace("The week", "the week"))} →</a>')
    nav_html = f'<nav class="wk-nav" aria-label="the weeks before and after">{"".join(nav)}</nav>' if nav else ""
    lede = (f'{story.number_words(n).capitalize()} meeting{"" if n == 1 else "s"}, {story.hours_prose(d["seconds"])} of tape'
            + (f', in {esc(story.the_list(towns))}' if towns else "") + ".")
    # the meetings, as the front page's week draws them, each with its counted headline
    cards = []
    for m in ms:
        pid = str(m.get("pid"))
        src = charts.still_src(stills, pid, 0, base)
        pic = (f'<img src="{esc(src)}" alt="" loading="lazy" width="480" height="270">' if src
               else f'<span class="bs-nostill" style="background:{charts.town_light(m.get("town"))}"></span>')
        head = story.tonight(m, base)["headline"]
        cards.append(f'<a class="mcard bs-week-card" href="{base}/m/{esc(pid)}" style="--town:{charts.town_color(m.get("town"))}">{pic}'
                     f'<span class="bs-wkbody"><span class="bs-wkkick">{esc(" · ".join(x for x in (m.get("town"), m.get("body")) if x))}</span>'
                     f'<b>{esc(m.get("title") or pid)}</b><span class="wk-head">{head}</span>'
                     f'<span class="bs-wkmeta">{esc(story.day_name(m.get("date") or ""))} · {esc(story.hours_words(m.get("duration") or 0))}</span></span></a>')
    # what was decided: the roll calls, then the loudest decisions and pushback
    rolls, decs = d["rolls"], d["decisions"]
    decided = []
    for r in rolls:
        out = _OUT.get(r["outcome"], r["outcome"] or "read")
        decided.append(f'<li><a href="{_at(r, r["t"], base)}"><span class="wk-when">{_when(r, r["t"])} · a roll call</span>'
                       f'<span class="wk-what">“{esc(charts.cut_words(r["motion"], 140))}”</span>'
                       f'<span class="wk-out">{esc(out)}{(" " + esc(r["tally"])) if r["tally"] else ""}</span></a></li>')
    for r in decs[:DECIDED]:
        decided.append(f'<li><a href="{_at(r, r["t"], base)}"><span class="wk-when">{_when(r, r["t"])} · {_KIND.get(r["kind"], r["kind"])}</span>'
                       f'<span class="wk-what">“{esc(r["quote"])}”</span></a></li>')
    decided_html = (f'<ul class="wk-list">{"".join(decided)}</ul>' + _more(len(decs) - DECIDED, "moment")) if decided else \
        '<p class="hint">No roll call or decision was read from this week’s tapes.</p>'
    # the sums the room named, the most said first
    sums = d["sums"]
    sums_html = (f'<ul class="wk-list wk-sums">' + "".join(
        f'<li><a href="{_at(s, s["t"], base)}"><b class="wk-sum">{esc(s["label"])}</b>'
        f'<span class="wk-when">said {n_of(s["count"], "time")} · {_when(s, s["t"])}</span></a></li>' for s in sums[:SHOWN])
        + "</ul>" + _more(len(sums) - SHOWN, "sum")) if sums else '<p class="hint">No sum of money was named on this week’s tapes.</p>'
    # the threads that moved: the issues the record follows, as this week took them up
    ths = d["threads"]
    threads_html = (f'<ul class="wk-list wk-threads">' + "".join(
        f'<li><a href="{base}/i/{esc(t["slug"])}"><b>{esc(t["name"])}</b>'
        f'<span class="wk-when">said {n_of(t["said"], "time")} this week, in {t["week"]} of its {n_of(n, "meeting")} · {n_of(t["all"], "meeting")} on the record</span></a></li>'
        for t in ths[:SHOWN]) + "</ul>" + _more(len(ths) - SHOWN, "thread")) if ths else \
        '<p class="hint">No thread the record follows came up this week.</p>'
    # how the week talked, against the whole record
    lz = d["lens"]
    if lz:
        noun = lambda l: esc(story.LENS_NOUN.get(l, l))
        pct = lambda v: f"{round(100 * v)}%"
        talk = (f'Of {lz["words"]:,} words this week’s tapes file under a lens, {pct(lz["loudest_week"])} were about {noun(lz["loudest"])}'
                f' — {pct(lz["loudest_record"])} across the whole record.')
        if lz["leaned"] != lz["loudest"] and lz["leaned_week"] > lz["leaned_record"]:
            talk += (f' It leaned furthest from the record’s habit toward {noun(lz["leaned"])}: '
                     f'{pct(lz["leaned_week"])} of the week’s words, against {pct(lz["leaned_record"])}.')
        talk_html = f'<p class="fp-say">{talk}</p>'
    else:
        talk_html = '<p class="hint">No word of this week’s tapes has been read under a lens yet.</p>'
    part = lambda hid, title, sub, inner, right="", href="": (
        f'<section class="wk-part" aria-labelledby="{hid}">{bs.section_head(title, sub, right, href, hid=hid)}{inner}</section>')
    here = ' aria-current="page"'
    every = "".join(
        f'<li><a href="{base}/week/{k}/"{here if k == key else ""}>{esc(week_label(k).replace("The week of ", ""))}'
        f' <span class="wk-when">{n_of(c, "meeting")}</span></a></li>' for k, c in counts.items())
    return f'''<article class="wk-page">
  <p class="kicker">the week in the record</p>
  <h1 class="wk-title">{esc(week_label(key))}</h1>
  <p class="fp-lede">{lede}</p>
  {nav_html}
  {part("wk-meetings", "The meetings", "each opens its tape and its page", f'<div class="mcards wk-cards">{"".join(cards)}</div>')}
  {part("wk-decided", "What was decided", "the roll calls read from the tapes, and the loudest decisions and pushback", decided_html)}
  {part("wk-sums", "The sums named", "every dollar figure the room said, the most said first", sums_html)}
  {part("wk-threads", "The threads that moved", "the issues the record follows, the most said this week first", threads_html, "every thread →", f"{base}/#threads")}
  {part("wk-talk", "How the week talked", "the eight lenses, this week against the whole record", talk_html, "the lenses, explained →", f"{base}/analytics")}
  <p class="decksrc">counted by the press from the record’s own planes — the meetings’ roll calls, moments, sums and lenses, and the threads’ timelines; no model wrote a word of it, and every line opens the tape</p>
  {nav_html}
  <section class="wk-part wk-every" aria-labelledby="wk-every">{bs.section_head("Every week on the record", "", "", "", hid="wk-every")}<ul class="wk-weeks">{every}</ul></section>
</article>'''
