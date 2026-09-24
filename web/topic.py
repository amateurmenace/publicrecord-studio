"""A word, over time — the record's search, told as a story (specs/25).

A citizen's question of the record is usually one word: *AI*, *housing*,
*parking*. The search page answers with lines. This module answers with a
story: how often the word was said, when it started, the night it peaked,
which bodies said it, what was said beside it, the first time it came up on
each night, and a supercut of every one of those moments — all COUNTED from
the transcripts at press time, never modeled, every number a receipt into
the tape. The front page leads with one such story (the featured topic), and
the search page tells the same story live for any word a reader types (the
JS twin in app.js, `topicStory`; the node twin test holds the two counts
equal).

Pure over the pressed meetings: sorted everywhere, no wall-clock, no
randomness — two presses of one corpus agree byte for byte.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import quote

from .charts import ARTIFACTS, esc, is_month, search_url  # noqa: F401 — search_url re-exported

# The record's featured case studies — the story the front page leads with.
# `phrases` are matched whole-word, case-insensitively, in every transcript
# line; `q` is the search a reader would type to make the same story. The
# story presses only where the town with the most mentions clears the floor
# (a word said twice is not a story yet).
FEATURED: List[dict] = [
    {"slug": "ai", "name": "AI", "long": "artificial intelligence", "q": "AI",
     "phrases": ["AI", "artificial intelligence"]},
]
FLOOR_MOMENTS = 3        # lines of transcript, in the leading town
FLOOR_MEETINGS = 2       # meetings those lines span
WINDOW = 12.0            # a hit's clip: its line, twelve seconds on (the tray's own rule)
MERGE_CAP = 90.0         # a run of hits merges into one clip, up to this long
BINS = 48                # where-on-the-tape slices per meeting


# --------------------------------------------------------------------------
# matching — whole words, the way the search's index tokenizes
# --------------------------------------------------------------------------

def phrase_re(phrase: str) -> "re.Pattern":
    """Whole-word, case-blind: `ai` matches "AI." and "ai," but never "said"
    or "aim". The JS twin (app.js phraseRe) is the same expression."""
    return re.compile(r"(?<![a-z0-9])" + re.escape(str(phrase).lower()) + r"(?![a-z0-9])")


def mentions_in(text: str, after: str, pats: Sequence["re.Pattern"]) -> int:
    """How many times the word is said in a line. A caption line is short and
    a phrase can break across two ("…it uses artificial" / "intelligence
    cameras"), so the line is read with the next one joined on — and only a
    match that STARTS inside the line counts for it, so no line is counted
    twice. The JS twin (app.js mentionsIn) is the same rule."""
    t = str(text or "").lower()
    joined = t + " " + str(after or "").lower()
    n = 0
    for p in pats:
        for mt in p.finditer(joined):
            if mt.start() <= len(t):
                n += 1
    return n


def find_hits(m: dict, phrases: Sequence[str]) -> List[dict]:
    """Every transcript line of a meeting that says the word: its time, the
    line, one line of context either side, and how many times it was said in
    that line. Lines in tape order."""
    pats = [phrase_re(p) for p in phrases if str(p or "").strip()]
    segs = m.get("segments") or []
    out = []
    for i, s in enumerate(segs):
        after = str(segs[i + 1].get("text") or "") if i + 1 < len(segs) else ""
        n = mentions_in(s.get("text"), after, pats)
        if not n:
            continue
        before = str(segs[i - 1].get("text") or "") if i > 0 else ""
        out.append({"pid": m["pid"], "t": float(s.get("start") or 0),
                    "text": str(s.get("text") or ""), "before": before, "after": after,
                    "mentions": n})
    return out


def context(h: dict, n: int = 220) -> str:
    """The line with its neighbours, as one quotable sentence, cut at a word."""
    from .charts import cut_words
    parts = [h.get("before") or "", h.get("text") or "", h.get("after") or ""]
    return cut_words(" ".join(" ".join(p.split()) for p in parts if p), n)


# --------------------------------------------------------------------------
# the supercut — merged windows, in the viewer's own link grammar
# --------------------------------------------------------------------------

def _euc(s) -> str:
    """encodeURIComponent's charset, byte for byte (web/emit.py _js_euc)."""
    return quote(str(s), safe="-_.!~*'()")


def _r1(x) -> str:
    """JS r1's formatting twin: one decimal, no trailing zero (1108.2, 1108)."""
    s = f"{round(float(x) + 1e-9, 1):.1f}"
    return s[:-2] if s.endswith(".0") else s


def merge_windows(hits: Sequence[dict], duration: float, window: float = WINDOW,
                  cap: float = MERGE_CAP) -> List[dict]:
    """Each hit is a clip of its line and the twelve seconds after it (the tray's
    rule for a search hit); hits that fall inside the clip before them extend
    it rather than replaying the same footage, up to `cap` seconds. Never past
    the tape's end; a clip that would be empty is not a clip."""
    dur = float(duration or 0)
    out: List[dict] = []
    for h in sorted(hits, key=lambda h: float(h["t"])):
        t = float(h["t"])
        end = t + window
        if dur:
            end = min(end, dur)
        if out and t <= out[-1]["end"] and (end - out[-1]["start"]) <= cap:
            out[-1]["end"] = max(out[-1]["end"], end)
            out[-1]["n"] += 1
            continue
        if end <= t:
            continue
        out.append({"pid": h["pid"], "start": t, "end": end, "n": 1})
    return out


def reel_url(clips: Sequence[dict], base: str = "/app") -> str:
    """The viewer's link, exactly as app.js reelShareURL writes it: v1 while
    the clips are one meeting's (`m=<pid>&c=<start>-<end>,…`), v2 the moment
    they span two (`c=<pid>:<start>-<end>,…`). The node twin test decodes
    these with the reader's own decodeReel."""
    pids = []
    for c in clips:
        if c["pid"] not in pids:
            pids.append(c["pid"])
    if not clips:
        return ""
    if len(pids) == 1:
        one = ",".join(_r1(c["start"]) + "-" + _r1(c["end"]) for c in clips)
        return f"{base}/r?v=1&m={_euc(pids[0])}&c={one}"
    many = ",".join(_euc(c["pid"]) + ":" + _r1(c["start"]) + "-" + _r1(c["end"]) for c in clips)
    return f"{base}/r?v=2&c={many}"


def runtime(clips: Sequence[dict]) -> float:
    return sum(max(0.0, float(c["end"]) - float(c["start"])) for c in clips)


# --------------------------------------------------------------------------
# the count — one story's data, pure over (meetings, hits)
# --------------------------------------------------------------------------

def month_range(months: Sequence[str]) -> List[str]:
    """Every month from the earliest to the latest, contiguous, so a silent
    month is a visible gap and not a missing bar. Only a real YYYY-MM counts
    — a malformed date is undated, never a crash (dates enter the store as
    the submitter typed them)."""
    ms = sorted(str(m)[:7] for m in months if is_month(m))
    if not ms:
        return []
    y, mo = int(ms[0][:4]), int(ms[0][5:7])
    y1, mo1 = int(ms[-1][:4]), int(ms[-1][5:7])
    out = []
    while (y, mo) <= (y1, mo1):
        out.append(f"{y:04d}-{mo:02d}")
        mo += 1
        if mo > 12:
            y, mo = y + 1, 1
    return out


_WORD = re.compile(r"[a-z][a-z'’-]+")


def cowords(hits: Sequence[dict], phrases: Sequence[str], top: int = 12) -> List[dict]:
    """The words said beside the word: counted in each hit's line and its two
    neighbours, civic stopwords out, the topic's own words out."""
    from highlighter.insight import _stopish
    skip = set()
    for p in phrases:
        for w in _WORD.findall(str(p).lower()):
            skip.add(w)
    counts: Dict[str, int] = {}
    for h in hits:
        text = " ".join([h.get("before") or "", h.get("text") or "", h.get("after") or ""]).lower()
        for w in _WORD.findall(text):
            w = w.strip("'’-")
            if not w or w in skip or _stopish(w) or w in ARTIFACTS:
                continue
            counts[w] = counts.get(w, 0) + 1
    return [{"word": w, "count": n} for w, n in
            sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))[:top] if n > 1]


def count(meetings: Sequence[dict], topic: dict) -> Optional[dict]:
    """The story's data for one topic, or None when no town clears the floor.

    `meetings` are the pressed meetings (with their segments). The town with
    the most lines leads the story; every other town's lines are counted as
    'elsewhere', with the search that reaches them."""
    phrases = [p for p in (topic.get("phrases") or []) if str(p or "").strip()]
    if not phrases:
        return None
    hits = [h for m in meetings for h in find_hits(m, phrases)]
    return aggregate(meetings, hits, topic)


def aggregate(meetings: Sequence[dict], hits: Sequence[dict], topic: dict,
              town: str = "", floor: bool = True) -> Optional[dict]:
    """The count, pure over (meetings, hits): `meetings` need only pid, title,
    date, body, town and duration; `hits` are find_hits' rows. The JS twin
    (app.js tpAggregate) takes the same two lists and answers the same — the
    node twin test holds them equal. `town` pins the story to one town (the
    search page's scope); otherwise the town with the most lines leads."""
    phrases = [p for p in (topic.get("phrases") or []) if str(p or "").strip()]
    by_pid: Dict[str, dict] = {m["pid"]: m for m in meetings}
    hits_by_pid: Dict[str, List[dict]] = {}
    for h in sorted(hits, key=lambda h: (str(h.get("pid") or ""), float(h.get("t") or 0))):
        if h.get("pid") in by_pid:
            hits_by_pid.setdefault(h["pid"], []).append(h)
    if not hits_by_pid:
        return None
    # the leading town — by lines, then by meetings, then by name
    town_lines: Dict[str, int] = {}
    town_meets: Dict[str, int] = {}
    for pid, hs in hits_by_pid.items():
        tn = str(by_pid[pid].get("town") or "")
        town_lines[tn] = town_lines.get(tn, 0) + len(hs)
        town_meets[tn] = town_meets.get(tn, 0) + 1
    # a meeting with no town recorded never leads a story — it is counted
    # as elsewhere, and named as what it is
    named = [t for t in town_lines if t]
    if not town or town not in town_lines:
        if not named:
            return None
        town = sorted(named, key=lambda t: (-town_lines[t], -town_meets[t], t))[0]
    if floor and (town_lines[town] < FLOOR_MOMENTS or town_meets[town] < FLOOR_MEETINGS):
        return None
    # undated nights sort last: the first word on the record is a dated one
    ms = sorted((m for m in meetings if str(m.get("town") or "") == town),
                key=lambda m: (str(m.get("date") or "") if is_month(m.get("date")) else "9999-99-99", m["pid"]))
    rows = []
    for m in ms:
        hs = hits_by_pid.get(m["pid"], [])
        dur = float(m.get("duration") or 0)
        if hs:
            dur = max(dur, max(h["t"] for h in hs) + 1)
        bins = [0] * BINS
        for h in hs:
            bins[min(BINS - 1, int(BINS * h["t"] / dur))] += 1 if dur else 0
        rows.append({"pid": m["pid"], "title": str(m.get("title") or m["pid"]),
                     "date": str(m.get("date") or ""), "body": str(m.get("body") or ""),
                     "duration": dur, "n": len(hs),
                     "mentions": sum(h["mentions"] for h in hs),
                     "first_t": hs[0]["t"] if hs else None,
                     "last_t": hs[-1]["t"] if hs else None,
                     "bins": bins, "hits": hs,
                     "clips": merge_windows(hs, dur)})
    said = [r for r in rows if r["n"]]
    all_hits = [h for r in said for h in r["hits"]]
    # months — contiguous over the town's dated meetings
    dated = [r for r in rows if is_month(r["date"])]
    months = []
    for mo in month_range([r["date"][:7] for r in dated]):
        rs = [r for r in dated if r["date"][:7] == mo]
        months.append({"month": mo, "meetings": len(rs),
                       "said": sum(1 for r in rs if r["n"]),
                       "moments": sum(r["n"] for r in rs),
                       "mentions": sum(r["mentions"] for r in rs)})
    undated = [r for r in said if not is_month(r["date"])]
    # bodies
    bb: Dict[str, dict] = {}
    for r in said:
        b = bb.setdefault(r["body"] or "—", {"body": r["body"] or "—", "moments": 0, "meetings": 0, "mentions": 0})
        b["moments"] += r["n"]; b["meetings"] += 1; b["mentions"] += r["mentions"]
    bodies = sorted(bb.values(), key=lambda b: (-b["moments"], b["body"]))
    # the first, the latest, the peak
    first = said[0]
    # "the latest" is a chronological claim: the last dated night that said
    # it, when any night is dated (undated nights sort last, and cannot be it)
    dated_said = [r for r in said if is_month(r["date"])]
    latest = dated_said[-1] if dated_said else said[-1]
    peak = max(said, key=lambda r: (r["n"], r["date"]))
    # meetings that passed in silence after the first word
    i_first = rows.index(first)
    gap = 0
    for r in rows[i_first + 1:]:
        if r["n"]:
            break
        gap += 1
    # elsewhere — the other towns, counted
    elsewhere = sorted(({"town": t, "moments": town_lines[t], "meetings": town_meets[t]}
                        for t in town_lines if t != town),
                       key=lambda e: (-e["moments"], e["town"]))
    # the chapters: the first time it came up, each night
    chapters = [{"pid": r["pid"], "date": r["date"], "body": r["body"], "title": r["title"],
                 "n": r["n"], "t": r["hits"][0]["t"], "quote": context(r["hits"][0]),
                 "clip": {"pid": r["pid"], "start": r["hits"][0]["t"],
                          "end": r["clips"][0]["end"] if r["clips"] else r["hits"][0]["t"] + WINDOW}}
                for r in said]
    short = [c["clip"] for c in chapters]
    full = [c for r in said for c in r["clips"]]
    return {
        "slug": topic["slug"], "name": topic.get("name") or topic["slug"],
        "long": topic.get("long") or topic.get("name") or topic["slug"],
        "q": topic.get("q") or topic.get("name") or topic["slug"],
        "phrases": phrases, "town": town,
        "moments": len(all_hits), "mentions": sum(h["mentions"] for h in all_hits),
        "n_meetings": len(said), "n_town_meetings": len(rows),
        "meetings": rows, "months": months, "undated": len(undated), "bodies": bodies,
        "first": {"pid": first["pid"], "date": first["date"], "body": first["body"],
                  "t": first["hits"][0]["t"], "quote": context(first["hits"][0])},
        "latest": {"pid": latest["pid"], "date": latest["date"], "body": latest["body"],
                   "t": latest["hits"][-1]["t"], "quote": context(latest["hits"][-1])},
        "peak": {"pid": peak["pid"], "date": peak["date"], "body": peak["body"], "n": peak["n"],
                 "mentions": peak["mentions"], "t": peak["first_t"],
                 "span": max(0.0, float(peak["last_t"]) - float(peak["first_t"]))},
        "gap": gap, "elsewhere": elsewhere,
        "cowords": cowords(all_hits, phrases),
        "chapters": chapters,
        "reel": {"short": reel_url(short), "short_n": len(short), "short_runtime": runtime(short),
                 "full": reel_url(full), "full_n": len(full), "full_runtime": runtime(full)},
    }


def featured(meetings: Sequence[dict], topics: Optional[Sequence[dict]] = None) -> List[dict]:
    """Every featured topic that clears the floor on this corpus, in the
    order FEATURED lists them."""
    out = []
    for t in (FEATURED if topics is None else topics):
        d = count(meetings, t)
        if d:
            out.append(d)
    return out


