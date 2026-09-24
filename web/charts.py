"""The front page's pictures, pressed (specs/24 §2.4).

Every picture here is computed at press time from the record's own planes and
written as plain SVG or HTML into the page — so the front page's two stories
read complete with JavaScript off, and the pressed bytes are the same on every
press (no randomness anywhere: the word cloud walks a fixed spiral, every list
is sorted). The paper palette only: deep green is measurement, slate is label,
ink is text; a receipt under every mark; a table twin where the picture is
positional (the chart blocks' own house rules, app.js chartShell).

These are the press-time twins of the paper's chart blocks (app.js chartVotes,
chartShape) and of the highlighter's signature views — the word cloud, the
sparkline search — brought to the record's front page as content.
"""

from __future__ import annotations

import html
import math
import re
from typing import Callable, Dict, List, Optional, Sequence, Tuple

# The broadsheet's palette (specs/29): paper and ink, a municipality's
# colour on what belongs to it, rust for the one action — writing — and for
# the failed vote, the pushback, the playhead. The lens hues stay the
# analyzer's own (highlighter.insight.FRAMING_LENSES). Measurement is ink.
PAPER = "#F3EEE3"     # the page
CARD = "#FBF9F4"      # a card, a chart's ground
INK = "#191712"       # text, measurement
INK2 = "#4B473E"      # second ink — labels, ledes
MUTED = "#6F6A5B"     # muted — axes, receipts
RULE = "#D9D1BF"      # rules, hairlines
RUST = "#B23A1D"      # writing; the failed vote; tension; the playhead
MONEY = "#7A5A10"     # a dollar figure's label (the financial lens, darkened to AA)
GREEN = INK           # the old name for measurement — ink now; callers keep the name
SLATE = INK2
HAIR = RULE
# a municipality's colour, on every card top, kicker and dot that belongs to
# it — (the colour, its light) by town name, case-blind; an unknown town is ink
TOWNS = {"boston": ("#1F4E79", "#DEE8F3"), "brookline": ("#1E5E3F", "#DDEBE1")}


def town_color(town) -> str:
    return TOWNS.get(str(town or "").strip().lower(), (INK, RULE))[0]


def town_light(town) -> str:
    return TOWNS.get(str(town or "").strip().lower(), (INK, RULE))[1]

# transcript artifacts a story must not mistake for a topic
ARTIFACTS = {"clears throat", "music", "applause", "laughter", "mhm", "um", "uh",
             "inaudible", "crosstalk", "foreign", "silence",
             # pleasantries a counter mistakes for topics
             "good evening", "good morning", "good afternoon", "good night", "thank you",
             "thanks", "hello", "welcome", "okay", "yeah", "everybody", "everyone",
             "next slide", "point of order", "roll call",
             # forms of address — procedure, not a topic
             "madam president", "mr president", "mister president", "madam chair", "mr chair",
             "madam clerk", "mr clerk", "madam mayor", "mr mayor", "councilor", "council president"}


def cut_words(s, n: int) -> str:
    """Cut at a cap, at a word boundary, with an ellipsis — never mid-word."""
    s = " ".join(str(s or "").split())
    if len(s) <= n:
        return s
    head = s[:n]
    if " " in head:
        head = head[:head.rfind(" ")]
    return head.rstrip(",;:—-") + "…"


def esc(s) -> str:
    return html.escape("" if s is None else str(s), quote=True)


def _r(x) -> str:
    return f"{round(float(x), 1):g}"


def hms(t) -> str:
    t = max(0, int(float(t or 0)))
    h, m, s = t // 3600, (t % 3600) // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def n_of(n, noun, plural=None) -> str:
    n = int(n or 0)
    return f"{n} {noun if n == 1 else (plural or noun + 's')}"


def twin(rows_html: str, head: str) -> str:
    """The table twin every positional picture carries."""
    return (f'<details class="graphtwin"><summary>the same, as a table</summary>'
            f'<div class="fp-twinwrap"><table class="twin"><thead><tr>{head}</tr></thead>'
            f'<tbody>{rows_html}</tbody></table></div></details>')


# --------------------------------------------------------------------------
# votes over time — the record's roll calls, one dot each, stacked by meeting
# --------------------------------------------------------------------------

def votes_over_time(votes: Sequence[dict], base: str = "/app") -> str:
    """One column per meeting in date order, a dot per roll call: a filled dot
    passes, a hollow one fails, a half-tone square is any other outcome (the
    word rides the tooltip and the twin). Each dot opens the tape where the
    vote was taken. Empty → an honest line, no picture."""
    vs = sorted((v for v in votes if v.get("pid")),
                key=lambda v: (str(v.get("date") or ""), float(v.get("t") or 0)))
    if not vs:
        return '<p class="hint">No roll call has been read from a tape yet.</p>'
    cols: List[dict] = []
    for v in vs:
        if cols and cols[-1]["pid"] == v["pid"]:
            cols[-1]["votes"].append(v)
        else:
            cols.append({"pid": v["pid"], "date": str(v.get("date") or ""),
                         "body": str(v.get("body") or ""), "votes": [v]})
    colw, pad, dotr, pitch = 56, 10, 7, 19
    maxn = max(len(c["votes"]) for c in cols)
    ploth = maxn * pitch + 12
    W, H = pad * 2 + len(cols) * colw, ploth + 36
    marks, labels, prev_year = [], [], None
    for i, c in enumerate(cols):
        cx = pad + i * colw + colw / 2
        for j, v in enumerate(c["votes"]):
            cy = ploth - dotr - 2 - j * pitch
            out = str(v.get("outcome") or "")
            mark = "pass" if out == "passes" else "fail" if out == "fails" else "other"
            tip = (f'{c["date"] or "undated"} · {out}'
                   + (f' {v["tally"]}' if v.get("tally") else "")
                   + f' — {str(v.get("motion") or "(motion)")[:120]}')
            href = f'{base}/m/{esc(c["pid"])}#t{int(float(v.get("t") or 0))}'
            if mark == "other":
                glyph = (f'<rect x="{_r(cx - dotr + 1)}" y="{_r(cy - dotr + 1)}" '
                         f'width="{(dotr - 1) * 2}" height="{(dotr - 1) * 2}" rx="2" '
                         f'fill="{GREEN}" fill-opacity=".5"><title>{esc(tip)}</title></rect>')
            elif mark == "pass":
                glyph = (f'<circle cx="{_r(cx)}" cy="{_r(cy)}" r="{dotr}" fill="{GREEN}" '
                         f'fill-opacity=".82"><title>{esc(tip)}</title></circle>')
            else:
                glyph = (f'<circle cx="{_r(cx)}" cy="{_r(cy)}" r="{dotr}" fill="#ffffff" '
                         f'stroke="{GREEN}" stroke-width="2"><title>{esc(tip)}</title></circle>')
            marks.append(f'<a href="{href}" aria-label="{esc(tip[:140])}">{glyph}</a>')
        day = c["date"][5:] if c["date"] else "—"
        labels.append(f'<text x="{_r(cx)}" y="{ploth + 14}" text-anchor="middle" '
                      f'font-size="10" fill="{SLATE}">{esc(day)}</text>')
        yr = c["date"][:4]
        if yr and yr != prev_year:
            labels.append(f'<text x="{_r(cx)}" y="{ploth + 28}" text-anchor="middle" '
                          f'font-size="10" fill="{SLATE}">{esc(yr)}</text>')
            prev_year = yr
    n_meet = len({c["pid"] for c in cols})
    svg = (f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" '
           f'role="group" aria-label="the record’s roll calls, meeting by meeting — {len(vs)} votes across '
           f'{n_meet} meetings; the table below carries every motion and outcome">'
           f'<line x1="0" y1="{ploth + 0.5}" x2="{W}" y2="{ploth + 0.5}" stroke="{HAIR}"/>'
           + "".join(marks) + "".join(labels) + "</svg>")
    rows = "".join(
        f'<tr><td><a href="{base}/m/{esc(v["pid"])}#t{int(float(v.get("t") or 0))}">{esc(v.get("date") or "undated")}</a></td>'
        f'<td>{esc(v.get("body") or "")}</td><td>{esc(str(v.get("motion") or "")[:110])}</td>'
        f'<td>{esc(v.get("outcome") or "")}</td><td>{esc(v.get("tally") or "")}</td></tr>' for v in vs)
    return (f'<div class="fp-chartwrap">{svg}</div>'
            + twin(rows, "<th>date</th><th>body</th><th>motion</th><th>outcome</th><th>tally</th>"))


# --------------------------------------------------------------------------
# the threads, over time — the loudest issues, appearances per month
# --------------------------------------------------------------------------

def issues_over_time(issues: Sequence[dict], months: Sequence[str], top: int = 6,
                     base: str = "/app") -> str:
    """Small multiples, one row per issue: its name, a run of month cells whose
    bar is the number of meetings it surfaced in that month, and the total.
    Magnitude bars in HTML (the heatmap's precedent) — real labels, deep green
    the only hue; each cell a receipt into the first meeting of that month."""
    ms = [m for m in months if m and m != "undated"]
    picked = sorted(issues, key=lambda i: (-int(i.get("n_meetings") or 0),
                                           -int(i.get("n_segments") or 0), str(i.get("name") or "")))[:top]
    if not picked or not ms:
        return '<p class="hint">the long view needs two read meetings</p>'
    rows = []
    allmax = 1
    table: List[Tuple[dict, Dict[str, List[dict]]]] = []
    for it in picked:
        by: Dict[str, List[dict]] = {}
        for n in (it.get("timeline") or []):
            d = str(n.get("date") or "")
            if len(d) >= 7:
                by.setdefault(d[:7], []).append(n)
        table.append((it, by))
        allmax = max(allmax, *(len(v) for v in by.values()), 1)
    for it, by in table:
        cells = []
        for mo in ms:
            nodes = by.get(mo, [])
            n = len(nodes)
            h = 4 + round(24 * n / allmax) if n else 2
            if n:
                first = nodes[0]
                bead = (first.get("beads") or [{}])[0]
                href = f'{base}/m/{esc(first["pid"])}' + (f'#t{int(float(bead["t"]))}' if bead.get("t") is not None else "")
                cells.append(f'<a class="fp-mcell" href="{href}" title="{esc(mo)}: {n_of(n, "meeting")}">'
                             f'<i style="height:{h}px"></i></a>')
            else:
                cells.append(f'<span class="fp-mcell" title="{esc(mo)}: none"><i style="height:{h}px"></i></span>')
        span = f'{str(it.get("first_seen") or "")[:7]} → {str(it.get("last_seen") or "")[:7]}'
        rows.append(f'<div class="fp-mrow"><a class="fp-mname" href="{base}/i/{esc(it["slug"])}">{esc(it["name"])}</a>'
                    f'<span class="fp-mcells">{"".join(cells)}</span>'
                    f'<span class="fp-mn">{n_of(int(it.get("n_meetings") or 0), "meeting")} · {esc(span)}</span></div>')
    labels = "".join(f'<span class="fp-mlabel">{esc(mo[5:] if len(mo) >= 7 else mo)}</span>' for mo in ms)
    yrs = sorted({mo[:4] for mo in ms})
    return (f'<div class="fp-multiples">{"".join(rows)}'
            f'<div class="fp-mrow fp-mrow-labels"><span class="fp-mname"></span>'
            f'<span class="fp-mcells">{labels}</span><span class="fp-mn">{esc(" · ".join(yrs))}</span></div></div>')


# --------------------------------------------------------------------------
# how the talk was framed, meeting by meeting — a heat strip
# --------------------------------------------------------------------------

def framing_strip(framing_rows: Sequence[dict], lens_order: Sequence[str], base: str = "/app") -> str:
    """Rows are the eight civic lenses, columns the meetings in date order; a
    cell's depth is that lens's share of the meeting's framed lines. The
    number rides the tooltip and the twin; the column head opens the meeting."""
    cols = sorted((r for r in framing_rows if r.get("pid")),
                  key=lambda r: (str(r.get("date") or "9999"), str(r.get("pid"))))
    lenses = [l for l in lens_order if any((c.get("lenses") or {}).get(l) for c in cols)]
    if not cols or not lenses:
        return '<p class="hint">the framing strip needs a read meeting</p>'
    head = "".join(
        f'<a class="fp-hcol" href="{base}/m/{esc(c["pid"])}" title="{esc(c.get("title") or c["pid"])}">'
        f'{esc((c.get("date") or "")[5:] or "—")}</a>' for c in cols)
    rows, trows = [], []
    for l in lenses:
        cells = []
        for c in cols:
            tot = float(c.get("total") or 0) or 1.0
            n = float((c.get("lenses") or {}).get(l) or 0)
            share = n / tot
            op = 0.08 + 0.85 * min(1.0, share * 2.5)   # a third of the talk reads full-depth
            tip = f'{c.get("date") or "undated"} · {l}: {int(n)} of {int(tot)} framed lines ({round(100 * share)}%)'
            cells.append(f'<a class="fp-hcell" href="{base}/m/{esc(c["pid"])}" style="--o:{op:.2f}" '
                         f'title="{esc(tip)}" aria-label="{esc(tip)}"></a>')
            trows.append(f'<tr><td>{esc(c.get("date") or "undated")}</td><td>{esc(l)}</td>'
                         f'<td>{int(n)}</td><td>{round(100 * share)}%</td></tr>')
        rows.append(f'<div class="fp-hrow"><span class="fp-hlens">{esc(l)}</span><span class="fp-hcells">{"".join(cells)}</span></div>')
    return (f'<div class="fp-heat"><div class="fp-hrow fp-hrow-head"><span class="fp-hlens"></span>'
            f'<span class="fp-hcells">{head}</span></div>{"".join(rows)}</div>'
            + twin("".join(trows), "<th>meeting</th><th>lens</th><th>lines</th><th>share</th>"))


# --------------------------------------------------------------------------
# what keeps coming back — the record's recurring topics
# --------------------------------------------------------------------------

def topic_bars(topics: Sequence[dict], base: str = "/app", top: int = 10) -> str:
    """Magnitude bars: the topic, a bar for its count, the count and how many
    meetings it reached; the name searches the record for it."""
    ts = [t for t in topics if str(t.get("topic") or "").strip()
          and str(t.get("topic")).strip().lower() not in ARTIFACTS][:top]
    if not ts:
        return '<p class="hint">no recurring topic yet — the long view needs two read meetings</p>'
    mx = max(int(t.get("count") or 0) for t in ts) or 1
    rows = []
    for t in ts:
        name = str(t.get("topic")).strip()
        n = int(t.get("count") or 0)
        nm = len(t.get("meetings") or [])
        q = html.escape(name).replace(" ", "+")
        rows.append(f'<div class="lensrow"><a class="lenslabel fp-topic" href="{base}/s?q={q}">{esc(name)}</a>'
                    f'<span class="lensbar"><i style="width:{round(100 * n / mx)}%"></i></span>'
                    f'<span class="lensn">{n}</span><span class="lensdrift">{n_of(nm, "meeting")}</span></div>')
    return f'<div class="lenses fp-topics">{"".join(rows)}</div>'


# --------------------------------------------------------------------------
# the word cloud — the highlighter's signature, deterministic
# --------------------------------------------------------------------------

def word_cloud(words: Sequence[dict], base: str = "/app", width: int = 720, height: int = 300,
               limit: int = 60, href: Optional[Callable[[dict], str]] = None,
               each: str = "each opens the record’s search for it") -> str:
    """Words sized by count (square-root scale, 11–46 px), placed on a fixed
    Archimedean spiral from the centre, never overlapping — the layout is a
    pure function of the words, so two presses agree byte for byte. Every
    word is a link: by default into the record's search for it. Monospace
    metrics (the record's headings are JetBrains Mono), so the boxes are
    honest. Opacity follows rank: the loudest words are the darkest."""
    ws = [w for w in words if str(w.get("word") or "").strip()
          and str(w.get("word")).strip().lower() not in ARTIFACTS][:limit]
    if not ws:
        return '<p class="hint">no words counted yet</p>'
    counts = [max(1, int(w.get("count") or 1)) for w in ws]
    lo, hi = math.sqrt(min(counts)), math.sqrt(max(counts))
    def size(c):
        if hi == lo:
            return 28
        return 11 + (46 - 11) * (math.sqrt(c) - lo) / (hi - lo)
    cx, cy = width / 2, height / 2
    placed: List[Tuple[float, float, float, float]] = []
    out = []
    for rank, (w, c) in enumerate(zip(ws, counts)):
        word = str(w["word"]).strip()
        fs = size(c)
        bw, bh = 0.62 * fs * len(word) + 4, fs * 1.05
        pos = None
        t = 0.0
        for _ in range(900):
            x = cx + 2.6 * t * math.cos(t)
            y = cy + 1.9 * t * math.sin(t)
            x0, y0, x1, y1 = x - bw / 2, y - bh / 2, x + bw / 2, y + bh / 2
            if x0 >= 2 and y0 >= 2 and x1 <= width - 2 and y1 <= height - 2 and \
               not any(x0 < px1 and x1 > px0 and y0 < py1 and y1 > py0 for px0, py0, px1, py1 in placed):
                pos = (x, y, x0, y0, x1, y1)
                break
            t += 0.31
        if not pos:
            continue
        x, y, x0, y0, x1, y1 = pos
        placed.append((x0, y0, x1, y1))
        op = 0.95 - 0.55 * (rank / max(1, len(ws) - 1))
        link = href(w) if href else f'{base}/s?q={html.escape(word).replace(" ", "+")}'
        tip = f'{word} — {n_of(c, "mention")}'
        out.append(f'<a href="{link}" aria-label="{esc(tip)}"><text x="{_r(x)}" y="{_r(y + fs * 0.35)}" '
                   f'text-anchor="middle" font-size="{_r(fs)}" fill="{GREEN}" fill-opacity="{op:.2f}">'
                   f'{esc(word)}<title>{esc(tip)}</title></text></a>')
    svg = (f'<svg class="fp-cloud" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
           f'xmlns="http://www.w3.org/2000/svg" role="group" aria-label="the words that came up most, '
           f'sized by how often — {len(out)} words; {esc(each)}">'
           + "".join(out) + "</svg>")
    rows = "".join(f'<tr><td>{esc(w["word"])}</td><td>{c}</td></tr>' for w, c in zip(ws, counts))
    return f'<div class="fp-chartwrap fp-cloudwrap">{svg}</div>' + twin(rows, "<th>word</th><th>mentions</th>")


# --------------------------------------------------------------------------
# the shape of a meeting — its moments on its own time axis
# --------------------------------------------------------------------------

SHAPE_KINDS = {"vote": "roll call", "decision": "decision", "tension": "pushback", "question": "question"}


def meeting_shape(moments: Sequence[dict], duration: float, pid: str, base: str = "/app") -> str:
    """The tape as one strip, the analyzer's moments marked where they fell:
    a bar for a roll call, a triangle for a decision, a diamond for pushback,
    a dot for a question — each a deep link into the tape; a table twin in
    order. The press-time twin of app.js chartShape (same geometry)."""
    mos = sorted((mo for mo in moments if mo.get("t") is not None), key=lambda mo: float(mo["t"]))
    if not mos:
        return '<p class="hint">The analyzer scored no moments on this tape — the meeting reads whole on its page.</p>'
    dur = max(float(duration or 0), *(float(mo.get("end") or mo["t"]) for mo in mos), 1.0)
    W, H, padl, padr, axisy = 720, 92, 8, 8, 60
    plotw = W - padl - padr
    x = lambda t: padl + plotw * max(0.0, min(1.0, float(t) / dur))
    marks, counts = [], {}
    for mo in mos:
        kind = mo.get("kind") if mo.get("kind") in SHAPE_KINDS else "question"
        counts[kind] = counts.get(kind, 0) + 1
        cx = x(mo["t"])
        tip = f'{hms(mo["t"])} · {SHAPE_KINDS[kind]} — {str(mo.get("quote") or "")[:120]}'
        if kind == "vote":
            g = f'<rect x="{_r(cx - 4)}" y="18" width="8" height="{axisy - 18}" rx="1" fill="{GREEN}" fill-opacity=".85"/>'
        elif kind == "decision":
            g = f'<path d="M{_r(cx)} 26 l7 14 h-14 z" fill="{GREEN}" fill-opacity=".85"/>'
        elif kind == "tension":
            g = f'<path d="M{_r(cx)} 30 l6 8 -6 8 -6 -8 z" fill="#ffffff" stroke="{GREEN}" stroke-width="2"/>'
        else:
            g = f'<circle cx="{_r(cx)}" cy="{axisy - 10}" r="3.5" fill="{GREEN}" fill-opacity=".55"/>'
        marks.append(f'<a href="{base}/m/{esc(pid)}#t{int(float(mo["t"]))}" aria-label="{esc(tip[:140])}">'
                     f'{g}<title>{esc(tip)}</title></a>')
    ticks = []
    h = 0
    while h * 3600 <= dur:
        cx = x(h * 3600)
        ticks.append(f'<line x1="{_r(cx)}" y1="{axisy}" x2="{_r(cx)}" y2="{axisy + 6}" stroke="{SLATE}"/>'
                     f'<text x="{_r(cx)}" y="{axisy + 20}" text-anchor="{"start" if h == 0 else "middle"}" '
                     f'font-size="10" fill="{SLATE}">{h}h</text>')
        h += 1
    legend = " · ".join(n_of(counts[k], SHAPE_KINDS[k]) for k in SHAPE_KINDS if counts.get(k))
    svg = (f'<svg width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="group" '
           f'aria-label="the shape of the meeting — {len(mos)} moments on a {hms(dur)} tape; the table below reads them in order">'
           f'<line x1="{padl}" y1="{axisy + 0.5}" x2="{W - padr}" y2="{axisy + 0.5}" stroke="{INK}" stroke-width="1"/>'
           + "".join(ticks) + "".join(marks) + "</svg>")
    rows = "".join(
        f'<tr><td><a href="{base}/m/{esc(pid)}#t{int(float(mo["t"]))}">{hms(mo["t"])}</a></td>'
        f'<td>{esc(SHAPE_KINDS.get(mo.get("kind"), "question"))}</td><td>{esc(str(mo.get("quote") or "")[:160])}</td></tr>'
        for mo in mos)
    return (f'<p class="fp-legend">{hms(dur)} of tape · {esc(legend)} — a bar is a roll call, a triangle a decision, '
            f'a diamond pushback, a dot a question</p><div class="fp-chartwrap">{svg}</div>'
            + twin(rows, "<th>time</th><th>kind</th><th>the moment</th>"))


# --------------------------------------------------------------------------
# sparklines — the highlighter's sparkline search: where a word fell on the tape
# --------------------------------------------------------------------------

_WORD = re.compile(r"[A-Za-z][A-Za-z'’-]+")


def sparklines(segments: Sequence[dict], terms: Sequence[str], duration: float, pid: str,
               base: str = "/app", bins: int = 24) -> str:
    """For each term, mentions per slice of the tape as a tiny bar run — where
    on the night the word came up. Each bar opens the tape at its slice; the
    term opens the record's search. Pure over the transcript."""
    dur = max(float(duration or 0), 1.0)
    if segments:
        dur = max(dur, max(float(s.get("start") or 0) for s in segments) + 1)
    rows = []
    for term in terms:
        t = str(term or "").strip().lower()
        if not t or t in ARTIFACTS:
            continue
        counts = [0] * bins
        total = 0
        for s in segments:
            text = str(s.get("text") or "").lower()
            if t in text:
                b = min(bins - 1, int(bins * float(s.get("start") or 0) / dur))
                counts[b] += 1
                total += 1
        if not total:
            continue
        mx = max(counts)
        bars = "".join(
            f'<a class="fp-sbar" href="{base}/m/{esc(pid)}#t{int(dur * i / bins)}" '
            f'title="{hms(dur * i / bins)}–{hms(dur * (i + 1) / bins)}: {n_of(c, "mention")}">'
            f'<i style="height:{2 + round(20 * c / mx) if c else 1}px"></i></a>' for i, c in enumerate(counts))
        rows.append(f'<div class="fp-spark"><a class="fp-sterm" href="{base}/s?q={html.escape(t).replace(" ", "+")}">{esc(term)}</a>'
                    f'<span class="fp-sbars">{bars}</span><span class="fp-sn">{n_of(total, "mention")}</span></div>')
    if not rows:
        return ""
    return f'<div class="fp-sparks">{"".join(rows)}</div>'


# --------------------------------------------------------------------------
# small pieces — a numbers strip, question bars, lens bars with drift
# --------------------------------------------------------------------------

# A model's prose, pressed (specs/27 §2.2). The models write Markdown whether
# asked to or not — v2.1.21 pressed "**What it means**" and "*   Motion/Vote:"
# raw onto every meeting page — so the reader renders the small subset they
# actually use, and nothing else: a heading line, a bullet, **bold**, *italic*;
# every other asterisk and backtick is dropped as the syntax it is. Escaped
# FIRST, marked up after: a draft is untrusted text, and no tag it holds
# survives. The JS twin is app.js receiptParas; a node twin holds them equal.
_RD_BULLET = re.compile(r"^[*•-][ \t]+(.+)$")
_RD_HASH = re.compile(r"^#{1,6}[ \t]+(.+)$")
_RD_BOLDLINE = re.compile(r"^\*\*([^*]{1,80}?):?\*\*:?$")
_RD_RULE = re.compile(r"^(?:[-*_•#][ \t]*)+$")  # a rule, spaced or not, or a bare marker ("##"): no content
_RD_WS = " \t\u00a0\ufeff"   # what a line is trimmed of, in both twins — named, so they agree
_RD_BOLD = re.compile(r"\*\*([^*]{1,200}?)\*\*")
_RD_ITAL = re.compile(r"\*([^* \t\u00a0](?:[^*]{0,200}?[^* \t\u00a0])?)\*")
_RD_STAR = re.compile(r"( ?)\*+( ?)")
_RD_LABEL = re.compile(r"^(what it means|who moved it|what to watch):", re.I | re.A)
# a receipt group: brackets holding only times and their separators —
# [1:52:55], [13:15-13:44], [12:12, 17:13]
_RD_GROUP = re.compile(r"\[([0-9:,; \t–—-]{3,60})\]")
_RD_TIME = re.compile(r"([0-9]{1,3}):([0-9]{2})(?::([0-9]{2}))?")


def _rd_esc(s: str) -> str:
    """The reader's own esc (app.js): & < > " — so the twins agree byte for
    byte. Text content and double-quoted attributes only, where ' is inert."""
    return (str(s).replace("&", "&amp;").replace("<", "&lt;")
            .replace(">", "&gt;").replace('"', "&quot;"))


def _rd_group(m, href_base: str) -> str:
    """Every time in a receipt group becomes its own bracketed link, said the
    way the rest of the record says a time (hms: [264:28] reads [4:24:28]).
    A group holding anything that is not a real time stays as the model
    wrote it — half-linked is worse than plain."""
    inner = m.group(1)
    parts, prev, times = [], 0, 0
    for t in _RD_TIME.finditer(inner):
        a, b, c = t.group(1), t.group(2), t.group(3)
        if c is not None:
            if int(b) > 59 or int(c) > 59:
                return m.group(0)
            sec = int(a) * 3600 + int(b) * 60 + int(c)
        else:
            if int(b) > 59:
                return m.group(0)
            sec = int(a) * 60 + int(b)
        sep = inner[prev:t.start()].strip()
        if times:
            if "," in sep or ";" in sep:
                parts.append(", ")
            elif sep in ("-", "–", "—"):
                parts.append("–")
            elif sep == "":
                parts.append(" ")
            else:
                return m.group(0)
        elif sep:
            return m.group(0)
        parts.append(f'<a class="ts" href="{href_base}#t{sec}">[{hms(sec)}]</a>')
        prev, times = t.end(), times + 1
    if not times or inner[prev:].strip():
        return m.group(0)
    return "".join(parts)


def _rd_inline(s: str, href_base: str, plain: bool = False) -> str:
    t = _rd_esc(s)
    if plain:
        # the tape's own sentences (an extractive summary): escaped and their
        # receipts linked — never read as Markdown ("- " is a dash, "*" a star)
        return _RD_GROUP.sub(lambda m: _rd_group(m, href_base), t)
    t = _RD_BOLD.sub(r"<b>\1</b>", t)
    t = _RD_ITAL.sub(r"<i>\1</i>", t)
    # what is left of the syntax goes; an asterisk with a space either side
    # is not syntax ("3 * 4") and stays
    t = _RD_STAR.sub(lambda m: m.group(0) if m.group(1) and m.group(2) else m.group(1) + m.group(2), t)
    t = t.replace("`", "")
    t = _RD_GROUP.sub(lambda m: _rd_group(m, href_base), t)
    lab = _RD_LABEL.match(t)
    if lab:
        t = f"<b>{lab.group(0)}</b>" + t[lab.end():]
    return t


# a receipt group left open at the cut ("[12:12, 17") — only times and their
# separators after the bracket: a bracket of words ("[inaudible") is prose
_RD_OPEN_GROUP = re.compile(r"\s*\[[0-9:,; \t–—-]*$")
# a label standing alone once read ("What to watch:" with nothing after it;
# bold or italic, the colon inside the mark or after it)
_RD_LONE_LABEL = re.compile(r"<(b|i)>(?:<b>)?(?:what it means|who moved it|what to watch):?(?:</b>)?</\1>:?",
                            re.I | re.A)
_RD_LABEL_WORDS = re.compile(r"(?:what it means|who moved it|what to watch)", re.I | re.A)


def _rd_cut(ln: str, n: int) -> str:
    """A line cut at a word — and never inside a receipt group: an unclosed
    "[12:12, 17…" at the cut is dropped whole, not left half-linked."""
    c = cut_words(ln, n)
    if c.endswith("…") and c != ln:
        body = _RD_OPEN_GROUP.sub("", c[:-1])
        c = body.rstrip(",;:—- ") + "…"
    return c


def _rd_says(ln: str, plain: bool = False) -> str:
    """What a line says once read, for the lede's cut: "" (nothing — bare
    syntax), "head" (a heading, or a label standing alone: "**Who moved
    it:**", "What to watch:"), or "words". A bullet is judged by its own
    text, the way the renderer reads it: an item is words however bold it
    is ("* **Approved the override [1:12:24]**" is a decision, not a head),
    unless all it says is a label."""
    if plain:
        return "words" if _rd_inline(ln, "", True).strip(_RD_WS) else ""
    b = _RD_BULLET.match(ln)
    t = b.group(1) if b else ln
    if not b and (_RD_HASH.match(t) or _RD_BOLDLINE.match(t)):
        return "head"
    x = _rd_inline(t, "").strip(_RD_WS)
    if not x:
        return ""
    return "head" if _RD_LONE_LABEL.fullmatch(x) else "words"


def _rd_unhead(ln: str) -> str:
    """A heading-shaped line as plain words — a summary that is one bold
    headline is still what the summary said ("## **…**" unwrapped all the
    way). A lone label says nothing; a headline that starts with one
    ("What it means: the town will borrow…") is words."""
    b = _RD_BULLET.match(ln)
    t = b.group(1) if b else ln
    while True:
        h = _RD_HASH.match(t) or _RD_BOLDLINE.match(t)
        if not h or h.group(1) == t:
            break
        t = h.group(1)
    return "" if _RD_LABEL_WORDS.fullmatch(t.strip(" *`:\t")) else t


def receipt_paras(text: str, href_base: str, limit: int = 0, plain: bool = False) -> str:
    """A model's paragraphs with their receipts turned into links: every
    [MM:SS] or [H:MM:SS] the draft carries opens the tape there
    (`href_base` is the meeting page, or "" for the page itself). A heading
    line is a small head, bullets are a list, **bold** is bold — the rest of
    Markdown's syntax is dropped, never shown. `limit` keeps whole lines up
    to that many characters of source (the first line cut at a word), so a
    front page never ends a draft mid-receipt."""
    src = re.sub(r"\r\n|[\r\u2028\u2029]", "\n", str(text or ""))
    lines = [ln.strip(_RD_WS) for ln in src.split("\n")]
    lines = [ln for ln in lines if ln and (plain or not _RD_RULE.match(ln))]
    if limit:
        # whole lines up to the limit; the first line with words in it always
        # stands (cut to the room left) — a heading, a label alone or a line
        # of bare syntax never spends the cut, and the lede never ends on one
        kept, used, words = [], 0, False
        for ln in lines:
            room = limit - used
            says = _rd_says(ln, plain)
            if len(ln) <= room:
                kept.append(ln)
                used += len(ln)
                words = words or says == "words"
                continue
            if not words:
                if says == "words":
                    kept.append(_rd_cut(ln, max(room, 200)))
                    words = True
                    break
                continue       # a head or bare syntax too long for the room says nothing: pass it
            break
        while kept and _rd_says(kept[-1], plain) != "words":
            kept.pop()
        if not kept:
            # nothing but headings: a one-line bold headline is the summary,
            # pressed as its words — a paragraph, never a head
            heads = [u for u in (_rd_unhead(ln) for ln in lines if _rd_says(ln, plain) == "head")
                     if _rd_inline(u, "").strip(_RD_WS)]
            return f"<p>{_rd_inline(_rd_cut(heads[0], limit), href_base, plain)}</p>" if heads else ""
        lines = kept
    out: List[str] = []
    items: List[str] = []

    def flush() -> None:
        if items:
            out.append('<ul class="rd-list">' + "".join(f"<li>{x}</li>" for x in items) + "</ul>")
            items.clear()
    for ln in lines:
        b = None if plain else _RD_BULLET.match(ln)
        if b:
            x = _rd_inline(b.group(1), href_base)
            if x.strip(_RD_WS):
                items.append(x)
            continue
        h = None if plain else (_RD_HASH.match(ln) or _RD_BOLDLINE.match(ln))
        x = _rd_inline(h.group(1) if h else ln, href_base, plain)
        if not x.strip(_RD_WS):
            continue       # a line that was only syntax (a fence, a bare **) says nothing
        flush()
        out.append(f'<p class="rd-h">{x}</p>' if h else f"<p>{x}</p>")
    flush()
    return "".join(out)


def numbers_strip(cells: Sequence[Tuple[object, str, str]]) -> str:
    return '<div class="lead-nums">' + "".join(
        f'<a class="ln" href="{esc(href)}"><b>{esc(n)}</b><span>{esc(label)}</span></a>'
        for n, label, href in cells) + "</div>"


def question_bars(questions: Sequence[dict], pid: str, base: str = "/app") -> str:
    by: Dict[str, List[dict]] = {}
    for q in questions:
        by.setdefault(str(q.get("type") or "information"), []).append(q)
    if not by:
        return ""
    mx = max(len(v) for v in by.values()) or 1
    rows = []
    for t, qs in sorted(by.items(), key=lambda kv: (-len(kv[1]), kv[0])):
        first = qs[0]
        rows.append(f'<div class="lensrow"><a class="lenslabel" href="{base}/m/{esc(pid)}#t{int(float(first.get("t") or 0))}">{esc(t)}</a>'
                    f'<span class="lensbar"><i style="width:{round(100 * len(qs) / mx)}%"></i></span>'
                    f'<span class="lensn">{len(qs)}</span><span class="lensdrift"></span></div>')
    return f'<div class="lenses">{"".join(rows)}</div>'


DRIFT = {"rising": "↑ rising", "fading": "↓ fading", "steady": "· steady"}


def lens_bars(lenses: Sequence[dict]) -> str:
    ls = [l for l in lenses if int(l.get("count") or 0) > 0]
    if not ls:
        return ""
    mx = max(int(l["count"]) for l in ls) or 1
    return '<div class="lenses">' + "".join(
        f'<div class="lensrow"><span class="lenslabel">{esc(l["lens"])}</span>'
        f'<span class="lensbar"><i style="width:{round(100 * int(l["count"]) / mx)}%"></i></span>'
        f'<span class="lensn">{int(l["count"])}</span>'
        f'<span class="lensdrift">{DRIFT.get(l.get("drift"), "")}</span></div>' for l in ls) + "</div>"


# --------------------------------------------------------------------------
# a word, over time (specs/25) — the topic story's three pictures
# --------------------------------------------------------------------------

MONTH_ABBR = ("", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
MONTH_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])")     # a month the story can place; anything else is undated
DAY_RE = re.compile(r"^\d{4}-\d{2}-\d{2}")


def is_month(d) -> bool:
    return bool(MONTH_RE.match(str(d or "")))


def _mname(mo: str) -> str:
    if not is_month(mo):
        return "undated"
    return f"{MONTH_ABBR[int(mo[5:7])]} {mo[:4]}"


def search_url(q: str, town: str = "", base: str = "/app") -> str:
    """The record's search for a word, as a URL: the query percent-encoded
    whole (a '#', an '&', a '+' in a topic stay inside the query), the town
    likewise. Raw — escape '&' to '&amp;' when writing it into an attribute."""
    from urllib.parse import quote
    u = f"{base}/s?q={quote(str(q), safe='')}"
    if town:
        u += f"&town={quote(str(town), safe='')}"
    return u


def month_bars(months: Sequence[dict], rows: Sequence[dict], base: str = "/app") -> str:
    """Mentions month by month — one column per month from the first to the
    last month the town met, contiguous, so a silent month is a visible gap:
    a bar for the mentions (its count above it), under it one dot per meeting
    that month (filled where the word came up, hollow where it did not, none
    where the town did not meet). A bar with mentions opens the tape at the
    month's first mention. The JS twin is app.js tpMonthBars."""
    ms = [x for x in months if x.get("month")]
    if not ms:
        return '<p class="hint">no dated meeting says it yet</p>'
    mx = max(int(x.get("mentions") or 0) for x in ms) or 1
    first_of: Dict[str, dict] = {}
    for r in rows:
        if r.get("n") and is_month(r.get("date")):
            first_of.setdefault(str(r["date"])[:7], r)
    cols, trows, prev_year = [], [], None
    for x in ms:
        mo, n = x["month"], int(x.get("mentions") or 0)
        meets, said = int(x.get("meetings") or 0), int(x.get("said") or 0)
        h = 6 + round(58 * n / mx) if n else 2
        tip = (f'{_mname(mo)}: {n_of(n, "mention")} in {said} of {n_of(meets, "meeting")}' if meets
               else f'{_mname(mo)}: no meeting on the record')
        dots = "".join('<i class="tp-dot on"></i>' for _ in range(said)) + \
               "".join('<i class="tp-dot"></i>' for _ in range(meets - said))
        yr = mo[:4]
        label = f'<label>{esc(MONTH_ABBR[int(mo[5:7])] if is_month(mo) else "?")}' + (f'<small>{esc(yr)}</small>' if yr != prev_year else "") + '</label>'
        prev_year = yr
        inner = (f'<b>{n if n else ""}</b><span class="tp-bar" style="height:{h}px"></span>'
                 f'<span class="tp-dots">{dots}</span>{label}')
        r0 = first_of.get(mo)
        if n and r0:
            cols.append(f'<a class="tp-mcol" href="{base}/m/{esc(r0["pid"])}#t{int(float(r0.get("first_t") or 0))}" '
                        f'title="{esc(tip)}" aria-label="{esc(tip)}">{inner}</a>')
        else:
            cols.append(f'<span class="tp-mcol{"" if meets else " tp-nomeet"}" title="{esc(tip)}" aria-label="{esc(tip)}">{inner}</span>')
        trows.append(f'<tr><td>{esc(_mname(mo))}</td><td>{meets}</td><td>{said}</td><td>{n}</td></tr>')
    return (f'<div class="tp-months" role="group" aria-label="mentions month by month">{"".join(cols)}</div>'
            + twin("".join(trows), "<th>month</th><th>meetings</th><th>said it</th><th>mentions</th>"))


def term_tapes(rows: Sequence[dict], base: str = "/app", bins: int = 48) -> str:
    """Where on each night the word fell: one row per meeting that said it,
    the tape as a run of slices, a taller bar where it came up more; every bar
    opens the tape at that slice. The highlighter's sparkline search, one term
    across every tape. The JS twin is app.js tpTapes."""
    said = [r for r in rows if r.get("n")]
    if not said:
        return ""
    out, trows = [], []
    for r in said:
        dur = max(float(r.get("duration") or 0), 1.0)
        counts = list(r.get("bins") or [0] * bins)
        mx = max(counts) or 1
        bars = "".join(
            f'<a class="fp-sbar" href="{base}/m/{esc(r["pid"])}#t{int(dur * i / len(counts))}" '
            f'title="{hms(dur * i / len(counts))}–{hms(dur * (i + 1) / len(counts))}: {n_of(c, "line")}">'
            f'<i style="height:{2 + round(20 * c / mx) if c else 1}px"></i></a>'
            for i, c in enumerate(counts))
        date = str(r.get("date") or "")
        when = esc(date[5:10]) if DAY_RE.match(date) else "undated"
        label = f'{when} · {esc(r.get("body") or "")}'
        out.append(f'<div class="fp-spark"><a class="fp-sterm" href="{base}/m/{esc(r["pid"])}" '
                   f'title="{esc(r.get("title") or r["pid"])}">{label}</a>'
                   f'<span class="fp-sbars">{bars}</span>'
                   f'<span class="fp-sn">{n_of(int(r["n"]), "line")}</span></div>')
        trows.append(f'<tr><td><a href="{base}/m/{esc(r["pid"])}#t{int(float(r.get("first_t") or 0))}">'
                     f'{esc(r.get("date") or "undated")}</a></td><td>{esc(r.get("body") or "")}</td>'
                     f'<td>{int(r["n"])}</td><td>{hms(r.get("first_t") or 0)}</td><td>{hms(r.get("last_t") or 0)}</td></tr>')
    return (f'<div class="fp-sparks tp-tapes">{"".join(out)}</div>'
            + twin("".join(trows), "<th>meeting</th><th>body</th><th>lines</th><th>first at</th><th>last at</th>"))


def coword_bars(words: Sequence[dict], q: str, base: str = "/app", town: str = "") -> str:
    """The words said beside the word — magnitude bars; each opens the
    record's search for the two together."""
    ws = [w for w in words if str(w.get("word") or "").strip()]
    if not ws:
        return ""
    mx = max(int(w.get("count") or 0) for w in ws) or 1
    rows = []
    for w in ws:
        both = f'{q} {w["word"]}'
        href = search_url(both, town, base).replace("&", "&amp;")
        rows.append(f'<div class="lensrow"><a class="lenslabel fp-topic" href="{href}" '
                    f'title="search the record for “{esc(both)}”">{esc(w["word"])}</a>'
                    f'<span class="lensbar"><i style="width:{round(100 * int(w["count"]) / mx)}%"></i></span>'
                    f'<span class="lensn">{int(w["count"])}</span><span class="lensdrift"></span></div>')
    return f'<div class="lenses fp-topics tp-cowords">{"".join(rows)}</div>'


# ==========================================================================
# the broadsheet (specs/29) — the pictures of the front page, the meeting
# page's score and the search page's timeline. Pure and deterministic:
# every function is a rule over the pressed planes, writes plain SVG, and
# carries its numbers beside it as data-bs-* JSON so app.js can re-light
# the picture (a click moves the playhead; a chapter re-lights the year)
# without a second fetch. With scripts off every picture is a still and
# every control an anchor into the meeting or the search.
# ==========================================================================

import json as _json

LENS_ORDER = ("financial", "safety", "community", "environmental",
              "legal", "equity", "infrastructure", "process")
LENS_COLOR = {"financial": "#A97A16", "safety": "#B0542D", "community": "#3FA9D0",
              "environmental": "#1E7F63", "legal": "#7E5B8E", "equity": "#C77BA6",
              "infrastructure": "#B08968", "process": "#7E7D75"}
MONTH_DAYS = (0, 31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
MONO = "font-family:var(--font-mono)"


def data_attr(name: str, obj) -> str:
    """A picture's numbers, beside it: data-bs-<name>='<json>' — sorted keys,
    no spaces, HTML-escaped once, so two presses agree byte for byte and the
    attribute cannot break out of its quotes."""
    return f'data-bs-{name}="{esc(_json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False))}"'


def still_src(stills: Optional[dict], pid: str, frame: int = 0, base: str = "/app") -> str:
    """The edition path of a pressed still, or "" — never a third party."""
    rec = (stills or {}).get(pid)
    if not rec:
        return ""
    if frame:
        return f"{base}/stills/{pid}-{frame}.jpg" if frame in (rec.get("frames") or []) else ""
    return f"{base}/stills/{pid}.jpg" if rec.get("poster") else ""


def month_axis(months: Sequence[str], width: float) -> Callable[[str], float]:
    """x along a run of months: a date lands at its month's column plus its
    day's share of it; an undated or out-of-range day lands at the edge."""
    ms = list(months)
    colw = width / max(1, len(ms))
    idx = {m: i for i, m in enumerate(ms)}
    def x(date: str) -> float:
        d = str(date or "")
        mo = d[:7]
        if mo not in idx:
            return 0.0 if (not ms or d < ms[0]) else width
        day = 1
        if DAY_RE.match(d):
            day = max(1, min(31, int(d[8:10])))
        days = MONTH_DAYS[int(mo[5:7])] or 30
        return (idx[mo] + (day - 1) / days) * colw
    return x


def month_range(months: Sequence[str]) -> List[str]:
    """Every month from the first to the last, contiguous — a silent month is
    a visible gap on an axis, never a missing column."""
    ms = sorted({str(m)[:7] for m in months if is_month(m)})
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


def month_short(mo: str) -> str:
    return MONTH_ABBR[int(mo[5:7])] if is_month(mo) else "?"


def day_short(d: str) -> str:
    """'2026-06-18' → 'Jun 18'."""
    d = str(d or "")
    return f"{MONTH_ABBR[int(d[5:7])]} {int(d[8:10])}" if DAY_RE.match(d) else "undated"


def money_label(name: str) -> str:
    """'$97 MILLION' → '$97 million' — the room's figure, in the paper's case."""
    s = " ".join(str(name or "").split()).rstrip(".,;: ")
    if not s:
        return ""
    head, _, tail = s.partition(" ")
    return head + (" " + tail.lower() if tail else "")


def _lens_rows(lenses: Sequence[dict]) -> Dict[str, dict]:
    return {str(l.get("lens") or ""): l for l in (lenses or []) if isinstance(l, dict)}


def score_moments(m: dict) -> List[dict]:
    """The dots of the score: the meeting's scored decisions, roll calls and
    pushback (the moments plane), in tape order — never the questions."""
    out = []
    for mo in (m.get("moments") or []):
        if mo.get("t") is None or mo.get("kind") not in ("vote", "decision", "tension"):
            continue
        out.append({"t": round(float(mo["t"]), 1), "kind": str(mo["kind"]),
                    "quote": cut_words(mo.get("quote"), 120), "reason": str(mo.get("reason") or ""),
                    "score": round(max(0.0, min(1.0, float(mo.get("score") or 0))), 3)})
    out.sort(key=lambda d: (d["t"], d["kind"]))
    return out


def loudest_t(m: dict) -> float:
    """Where the score opens: the loudest scored moment, else the tape's start."""
    mos = score_moments(m)
    if not mos:
        return 0.0
    return max(mos, key=lambda d: (d["score"], -d["t"]))["t"]


_SMALL = ("zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve")


def _third_label(i: int, span: float) -> str:
    mins = int(round(span / 60))
    if 50 <= mins <= 70:
        what = "hour"
    elif mins >= 90:
        h, m = divmod(mins, 60)
        hw = _SMALL[h] if h < len(_SMALL) else str(h)
        what = f"{h} h {m} min" if m else f"{hw} hours"
    else:
        what = n_of(mins, "minute")
    return ("The first", "The second", "The last")[i] + " " + what


def thirds_of(m: dict) -> List[dict]:
    """The tape in three, with the decisions that fall in each — the
    filmstrip's three frames (YouTube's own hq1–3 sit near each third's middle)."""
    dur = max(1.0, float(m.get("duration") or 0))
    mos = score_moments(m)
    out = []
    for i in range(3):
        t0, t1 = dur * i / 3, dur * (i + 1) / 3
        inside = [d for d in mos if t0 <= d["t"] < t1 or (i == 2 and d["t"] >= t1)]
        out.append({"i": i, "t0": round(t0, 1), "t1": round(t1, 1), "mid": round((t0 + t1) / 2, 1),
                    "label": _third_label(i, dur / 3), "span": f"{hms(t0)} – {hms(t1)}",
                    "decisions": [{"t": d["t"], "kind": d["kind"], "quote": cut_words(d["quote"], 70)}
                                  for d in inside[:3]]})
    return out


def score_data(m: dict, width: int = 880) -> dict:
    """The score's numbers — what app.js re-lights from (the JS twin of
    score_state reads exactly this)."""
    an = m.get("analysis") or {}
    dur = max(1.0, float(m.get("duration") or 0))
    ticks = []
    for l in ((an.get("framing") or {}).get("lenses") or []):
        for mo in (l.get("moments") or []):
            if mo.get("t") is None:
                continue
            ticks.append({"t": round(float(mo["t"]), 1), "lens": str(l.get("lens") or ""),
                          "text": cut_words(mo.get("text"), 90)})
    ticks.sort(key=lambda k: (k["t"], k["lens"]))
    money = []
    for e in ((an.get("entities") or {}).get("money") or []):
        if e.get("t") is None or not e.get("name"):
            continue
        money.append({"t": round(float(e["t"]), 1), "label": money_label(e["name"]),
                      "count": int(e.get("count") or 0)})
    money.sort(key=lambda x: (x["t"], x["label"]))
    return {"pid": str(m.get("pid") or ""), "dur": round(dur, 1), "w": int(width),
            "t": loudest_t(m), "ticks": ticks, "money": money,
            "decisions": score_moments(m), "thirds": thirds_of(m)}


def score_state(data: dict, t: float) -> dict:
    """What the score shows at a time t — the playhead's x, the nearest
    decision (ties to the earlier), the third the frame shows. The JS twin
    is app.js bsScoreState; the node twin test holds them equal."""
    dur = max(1.0, float(data.get("dur") or 1))
    w = int(data.get("w") or 880)
    t = max(0.0, min(dur, float(t or 0)))
    near = None
    for i, d in enumerate(data.get("decisions") or []):
        if near is None or abs(float(d["t"]) - t) < abs(float((data["decisions"][near])["t"]) - t):
            near = i
    return {"x": int(round(t / dur * w)), "near": near, "third": min(2, int(t / dur * 3)),
            "mmss": hms(t)}


def score(m: dict, base: str = "/app", width: int = 880, questions: bool = False,
          data: Optional[dict] = None) -> str:
    """The score of the night: the tape as a timeline — decisions as dots
    sized by their score (tension in rust), every dollar figure the room
    named as a labelled tick, eight lanes (one per lens) showing where that
    lens's words fell (the sixty-bin track), the sample moments as clickable
    ticks, and a rust playhead. Click anything and the playhead, the caption
    card and the frame move together (app.js bsScore); with scripts off
    every mark is an anchor into the tape. `questions` adds the questions
    as ticks (the meeting page's shape of the tape)."""
    d = data or score_data(m, width)
    pid, dur, W = d["pid"], float(d["dur"]), int(d["w"])
    an = m.get("analysis") or {}
    x = lambda t: W * max(0.0, min(1.0, float(t) / dur))
    at = lambda t: f'{base}/m/{esc(pid)}#t{int(float(t))}'
    lanes_y0, lane_h, lane_gap = 56, 9, 11
    out = [f'<rect x="0" y="{lanes_y0}" width="{W}" height="{8 * lane_gap + 2}" fill="{PAPER}" rx="4"/>']
    rows = _lens_rows((an.get("framing") or {}).get("lenses") or [])
    bins_n = 0
    for i, lens in enumerate(LENS_ORDER):
        y = lanes_y0 + i * lane_gap
        color = LENS_COLOR[lens]
        out.append(f'<rect x="-6" y="{y + 1}" width="4" height="{lane_h - 2}" fill="{color}"/>'
                   f'<text x="-12" y="{y + 8}" font-size="9" fill="{INK2}" text-anchor="end" style="{MONO}">{lens}</text>')
        track = list((rows.get(lens) or {}).get("track") or [])
        bins_n = max(bins_n, len(track))
        mx = max(track) if track else 0
        if mx:
            # one path per lane — a bar per slice that has words, its height
            # the slice's share of the lane's loudest slice
            bw = W / len(track)
            bar_w = max(1.0, bw - 0.6)
            dpath = "".join(f"M{_r(b * bw)},{_r(y + lane_h - max(2.0, lane_h * c / mx))}h{_r(bar_w)}v{_r(max(2.0, lane_h * c / mx))}h-{_r(bar_w)}z"
                            for b, c in enumerate(track) if c)
            out.append(f'<path class="bs-lane" data-lens="{lens}" d="{dpath}" fill="{color}" opacity=".55">'
                       f'<title>{esc(lens)} — {n_of(sum(track), "word")}, where they fell along the tape</title></path>')
    for k in d["ticks"]:
        y = lanes_y0 + LENS_ORDER.index(k["lens"]) * lane_gap if k["lens"] in LENS_ORDER else lanes_y0
        out.append(f'<a href="{at(k["t"])}" class="bs-tick" data-t="{_r(k["t"])}" data-lens="{esc(k["lens"])}" data-text="{esc(k["text"])}">'
                   f'<rect x="{_r(x(k["t"]) - 1.5)}" y="{y}" width="3" height="{lane_h}" fill="{LENS_COLOR.get(k["lens"], INK)}">'
                   f'<title>{hms(k["t"])} · {esc(k["lens"])}: “{esc(k["text"])}”</title></rect></a>')
    for i, mo in enumerate(d["money"]):
        ly = 34 + (i % 2) * 11
        anchor = "end" if x(mo["t"]) > W - 60 else "start"
        out.append(f'<a href="{at(mo["t"])}" class="bs-money" data-t="{_r(mo["t"])}" data-label="{esc(mo["label"])}">'
                   f'<line x1="{_r(x(mo["t"]))}" y1="54" x2="{_r(x(mo["t"]))}" y2="{ly}" stroke="{LENS_COLOR["financial"]}" stroke-width="1"/>'
                   f'<text x="{_r(x(mo["t"]))}" y="{ly}" font-size="10" fill="{MONEY}" text-anchor="{anchor}" style="{MONO}">{esc(mo["label"])}'
                   f'<title>{esc(mo["label"])} — said {n_of(mo["count"], "time")}, first at {hms(mo["t"])}</title></text></a>')
    if questions:
        for q in (an.get("questions") or []):
            if q.get("t") is None:
                continue
            out.append(f'<a href="{at(q["t"])}" class="bs-q" data-t="{_r(q["t"])}">'
                       f'<line x1="{_r(x(q["t"]))}" y1="24" x2="{_r(x(q["t"]))}" y2="31" stroke="{MUTED}" stroke-width="1"/>'
                       f'<title>{hms(q["t"])} · a question: “{esc(cut_words(q.get("text"), 100))}”</title></a>')
    for i, dc in enumerate(d["decisions"]):
        r = 5.0 + 3.0 * dc["score"]
        fill = RUST if dc["kind"] == "tension" else INK
        out.append(f'<a href="{at(dc["t"])}" class="bs-dec" data-i="{i}" data-t="{_r(dc["t"])}" data-kind="{esc(dc["kind"])}">'
                   f'<circle cx="{_r(x(dc["t"]))}" cy="44" r="{_r(r)}" fill="{fill}" opacity=".9">'
                   f'<title>{hms(dc["t"])} · {esc(SHAPE_KINDS.get(dc["kind"], dc["kind"]))}: “{esc(dc["quote"])}”</title></circle></a>')
    st = score_state(d, d["t"])
    out.append(f'<g class="bs-playhead"><line x1="{st["x"]}" y1="32" x2="{st["x"]}" y2="150" stroke="{RUST}" stroke-width="2"/>'
               f'<text x="{st["x"]}" y="164" font-size="11" fill="{RUST}" text-anchor="middle" style="{MONO}">{st["mmss"]}</text></g>')
    step = 1800.0
    t = 0.0
    while t < dur - 60:
        out.append(f'<text x="{_r(x(t))}" y="166" font-size="10" fill="{MUTED}" text-anchor="{"start" if t == 0 else "middle"}" style="{MONO}">{hms(t)}</text>')
        t += step
    svg = (f'<svg class="bs-score-svg" width="{W}" height="168" viewBox="-100 0 {W + 110} 168" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="the shape of the meeting along the tape: its loudest moments as dots, '
           f'the dollar figures the room named, eight lanes of lens words">' + "".join(out) + "</svg>")
    trows = "".join(f'<tr><td><a href="{at(dc["t"])}">{hms(dc["t"])}</a></td><td>{esc(SHAPE_KINDS.get(dc["kind"], dc["kind"]))}</td>'
                    f'<td>{esc(dc["quote"])}</td></tr>' for dc in d["decisions"])
    trows += "".join(f'<tr><td><a href="{at(mo["t"])}">{hms(mo["t"])}</a></td><td>money</td>'
                     f'<td>{esc(mo["label"])} — said {n_of(mo["count"], "time")}</td></tr>' for mo in d["money"])
    return (f'<div class="bs-score" {data_attr("score", d)}><div class="fp-chartwrap">{svg}</div>'
            + twin(trows, "<th>time</th><th>kind</th><th>the moment</th>") + "</div>")


def filmstrip(m: dict, stills: Optional[dict] = None, base: str = "/app",
              data: Optional[dict] = None) -> str:
    """Three real frames from inside the tape (YouTube's hq1–3, pressed into
    the edition), each with the decisions that fall in its third. Each frame
    is an anchor into the tape at its third's middle; app.js turns a click
    into the playhead's move. A frame the edition lacks is the town's colour."""
    d = data or score_data(m)
    pid = d["pid"]
    st = score_state(d, d["t"])
    out = []
    for th in d["thirds"]:
        src = still_src(stills, pid, th["i"] + 1, base)
        pic = (f'<img src="{esc(src)}" alt="" loading="lazy" width="480" height="270">' if src
               else f'<span class="bs-nostill" style="background:{town_light(m.get("town"))}"></span>')
        decs = "".join(f'<span class="bs-fdec"><span class="ts">{hms(x["t"])}</span><span>“{esc(x["quote"])}…”</span></span>'
                       for x in th["decisions"])
        on = " on" if th["i"] == st["third"] else ""
        none = '<span class="bs-fdec bs-fnone">no scored decision in this third</span>'
        out.append(f'<a class="bs-frame{on}" href="{base}/m/{esc(pid)}#t{int(th["mid"])}" data-i="{th["i"]}" data-t="{_r(th["mid"])}">'
                   f'{pic}<span class="bs-fhead"><b>{esc(th["label"])}</b><span class="bs-fspan">{esc(th["span"])}</span></span>'
                   f'{decs or none}</a>')
    return f'<div class="bs-filmstrip">{"".join(out)}</div>'


# --------------------------------------------------------------------------
# the year in tapes
# --------------------------------------------------------------------------

def tape_width(hours: float) -> int:
    return int(max(56, min(140, round(60 + 10.3 * float(hours or 0)))))


YEAR_MONTHS = 12      # the year in tapes is the last twelve months the record holds
YEAR_STILLS = 60      # the most recent tapes carry their still; older ones are the town's colour


def year_window(meetings: Sequence[dict]) -> Tuple[List[str], List[dict], bool]:
    """The year in tapes: the dated meetings of the last twelve months the
    record holds, in date order, with their run of months — ONE window the
    strip, its chapters and its words all read from (a skeptic's catch: the
    strip was windowed and the chapters were not). The flag says whether
    anything older was left off."""
    dated = sorted((m for m in meetings if is_month(m.get("date"))),
                   key=lambda m: (str(m.get("date")), str(m.get("pid"))))
    months = month_range([str(m["date"])[:7] for m in dated]) if dated else []
    windowed = len(months) > YEAR_MONTHS
    if windowed:
        months = months[-YEAR_MONTHS:]
        keep = set(months)
        dated = [m for m in dated if str(m["date"])[:7] in keep]
    return months, dated, windowed


def year_layout(meetings: Sequence[dict], width: int = 1328, height: int = 300) -> Tuple[List[str], List[dict]]:
    """Every dated meeting of the last twelve months as a still on the month
    axis, sized by its length, packed upward so no two overlap — a pure
    layout, so the JS and the press agree on where each tape sits."""
    months, dated, _windowed = year_window(meetings)
    x_of = month_axis(months, width)
    colw = width / max(1, len(months))
    floor_y, gap = height - 34, 6
    placed: List[dict] = []
    # `fan` lets a crowded month's tapes overlap like a fanned deck (each
    # still shows its top 45%) — used only when strict rows would more than
    # half again the strip's height; strict rows first, always
    fan = [0.0]
    hits = lambda x, y, w, h: any(x < p["x"] + p["w"] + gap and x + w + gap > p["x"]
                                   and y < p["y"] + p["h"] * (1 - fan[0]) + gap and y + h * (1 - fan[0]) + gap > p["y"]
                                   for p in placed)
    for m in dated:
        hours = float(m.get("duration") or 0) / 3600
        w = tape_width(hours)
        h = int(round(w * 9 / 16))
        x0 = max(0.0, min(width - w, x_of(m["date"]) - w / 2))
        # the lowest free slot: first the tape's own day, then a step to
        # either side within its month, then the row above — a crowded month
        # packs into sub-columns before it climbs
        ys = sorted({floor_y - h} | {p["y"] - h * (1 - fan[0]) - gap for p in placed}, reverse=True)
        steps = [0.0] + [s * d for s in (0.5, 1.0) for d in (colw / 2, -colw / 2)]
        x, y = x0, floor_y - h
        for cy in ys:
            found = None
            for dx in steps:
                cx = max(0.0, min(width - w, x0 + dx))
                if not hits(cx, cy, w, h):
                    found = cx
                    break
            if found is not None:
                x, y = found, cy
                break
        placed.append({"pid": str(m.get("pid") or ""), "x": round(x, 1), "y": round(y, 1), "w": w, "h": h,
                       "month": str(m["date"])[:7], "date": str(m["date"]), "town": str(m.get("town") or ""),
                       "body": str(m.get("body") or ""), "title": str(m.get("title") or m.get("pid") or ""),
                       "hours": round(hours, 1)})
    # a year too crowded for the strip's height fans its tapes (once), then
    # grows the strip rather than losing a tape
    lowest = min((p["y"] for p in placed), default=0.0)
    if lowest < -height * 0.6 and fan[0] == 0.0:
        fan[0] = 0.55
        return _refan(dated, months, width, height, fan[0])
    if lowest < 0:
        shift = -lowest + 4
        for p in placed:
            p["y"] = round(p["y"] + shift, 1)
    return months, placed


def _refan(dated, months, width, height, fanning):
    """The same layout with the deck fanned — a second pass, one rule."""
    x_of = month_axis(months, width)
    colw = width / max(1, len(months))
    floor_y, gap = height - 34, 6
    placed: List[dict] = []
    vis = 1 - fanning
    hits = lambda x, y, w, h: any(x < p["x"] + p["w"] + gap and x + w + gap > p["x"]
                                   and y < p["y"] + p["h"] * vis + gap and y + h * vis + gap > p["y"] for p in placed)
    for m in dated:
        hours = float(m.get("duration") or 0) / 3600
        w = tape_width(hours)
        h = int(round(w * 9 / 16))
        x0 = max(0.0, min(width - w, x_of(m["date"]) - w / 2))
        ys = sorted({floor_y - h} | {p["y"] - h * vis - gap for p in placed}, reverse=True)
        steps = [0.0] + [s * d for s in (0.5, 1.0) for d in (colw / 2, -colw / 2)]
        x, y = x0, floor_y - h
        for cy in ys:
            found = None
            for dx in steps:
                cx = max(0.0, min(width - w, x0 + dx))
                if not hits(cx, cy, w, h):
                    found = cx
                    break
            if found is not None:
                x, y = found, cy
                break
        placed.append({"pid": str(m.get("pid") or ""), "x": round(x, 1), "y": round(y, 1), "w": w, "h": h,
                       "month": str(m["date"])[:7], "date": str(m["date"]), "town": str(m.get("town") or ""),
                       "body": str(m.get("body") or ""), "title": str(m.get("title") or m.get("pid") or ""),
                       "hours": round(hours, 1)})
    lowest = min((p["y"] for p in placed), default=0.0)
    if lowest < 0:
        shift = -lowest + 4
        for p in placed:
            p["y"] = round(p["y"] + shift, 1)
    return months, placed


def year_tapes(meetings: Sequence[dict], chapters: Sequence[dict], stills: Optional[dict] = None,
               base: str = "/app", width: int = 1328, height: int = 300) -> str:
    """The year in tapes: every meeting as its own still on the month axis,
    sized by its hours, town-coloured on its top edge, rows to avoid overlap;
    the last chapter lit and the rest dimmed (the pressed state; the chapter
    pills re-light it with the script on, and click a still to name it).
    Every still is an anchor into its meeting."""
    months, tapes = year_layout(meetings, width, height)
    if not tapes:
        return '<p class="hint">no dated meeting on the record yet</p>'
    height = int(max(height, max(t["y"] + t["h"] for t in tapes) + 34))
    x_of = month_axis(months, width)
    lit = set()
    if chapters:
        lit = set(chapters[-1].get("months") or [])
    colw = width / len(months)
    out = []
    for i, mo in enumerate(months):
        x0 = i * colw
        out.append(f'<line x1="{_r(x0)}" y1="0" x2="{_r(x0)}" y2="{height - 24}" stroke="{RULE}" stroke-dasharray="2 4"/>'
                   f'<text x="{_r(x0 + 6)}" y="{height - 8}" font-size="12" fill="{MUTED}" style="{MONO}">{month_short(mo)}</text>')
    # the sixty most recent tapes carry their still (an SVG <image> cannot
    # load lazily); older ones are the town's colour, still the meeting's link
    with_still = {t["pid"] for t in sorted(tapes, key=lambda t: (t["date"], t["pid"]), reverse=True)[:YEAR_STILLS]}
    for t in tapes:
        dim = "" if (not lit or t["month"] in lit) else " bs-dim"
        src = still_src(stills, t["pid"], 0, base) if t["pid"] in with_still else ""
        pic = (f'<image href="{esc(src)}" x="{t["x"]}" y="{t["y"]}" width="{t["w"]}" height="{t["h"]}" preserveAspectRatio="xMidYMid slice"/>'
               if src else
               f'<rect x="{t["x"]}" y="{t["y"]}" width="{t["w"]}" height="{t["h"]}" fill="{town_light(t["town"])}" rx="2"/>'
               f'<text x="{_r(t["x"] + t["w"] / 2)}" y="{_r(t["y"] + t["h"] / 2 + 4)}" font-size="11" fill="{town_color(t["town"])}" text-anchor="middle" style="{MONO}">{esc(day_short(t["date"]))}</text>')
        tip = f'{t["title"]} — {t["date"]} · {t["town"]} · {t["body"]} · {t["hours"]} h'
        out.append(f'<a href="{base}/m/{esc(t["pid"])}" class="bs-tape{dim}" data-pid="{esc(t["pid"])}" data-month="{esc(t["month"])}">'
                   f'<title>{esc(tip)}</title>{pic}'
                   f'<rect x="{t["x"]}" y="{t["y"]}" width="{t["w"]}" height="4" fill="{town_color(t["town"])}"/>'
                   f'<rect class="bs-tape-ring" x="{t["x"]}" y="{t["y"]}" width="{t["w"]}" height="{t["h"]}" fill="none" stroke="none" stroke-width="2.5" rx="2"/></a>')
    _m, _d, windowed = year_window(meetings)
    what = "the last twelve months" if windowed else "the record"
    svg = (f'<svg class="bs-year-svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="every meeting of {what} as its own still, placed on the year — {n_of(len(tapes), "tape")}">' + "".join(out) + "</svg>")
    trows = "".join(f'<tr><td><a href="{base}/m/{esc(t["pid"])}">{esc(t["date"])}</a></td><td>{esc(t["town"])}</td>'
                    f'<td>{esc(t["body"])}</td><td>{esc(t["title"])}</td><td>{t["hours"]}</td></tr>' for t in tapes)
    # the chapters ride whole — the pressed paragraph (with its receipts) as
    # well as the plain blurb, so a re-lit chapter keeps its links
    payload = {"tapes": tapes, "chapters": list(chapters), "months": months}
    return (f'<div class="bs-year" {data_attr("year", payload)}><div class="fp-chartwrap">{svg}</div>'
            + twin(trows, "<th>date</th><th>town</th><th>body</th><th>meeting</th><th>hours</th>") + "</div>")


# --------------------------------------------------------------------------
# the four columns' pictures
# --------------------------------------------------------------------------

def town_shares(framing_rows: Sequence[dict], towns_by_pid: Dict[str, str]) -> List[dict]:
    """Each town's share of its framed words by lens, from the analytics
    framing matrix — the butterfly's numbers; towns by meetings, most first."""
    tot: Dict[str, Dict[str, float]] = {}
    n: Dict[str, int] = {}
    for r in framing_rows:
        town = towns_by_pid.get(str(r.get("pid") or ""), "")
        if not town:
            continue
        n[town] = n.get(town, 0) + 1
        d = tot.setdefault(town, {})
        for l, c in (r.get("lenses") or {}).items():
            d[l] = d.get(l, 0.0) + float(c or 0)
    out = []
    for town in sorted(tot, key=lambda t: (-n[t], t)):
        s = sum(tot[town].values()) or 1.0
        out.append({"town": town, "color": town_color(town), "n": n[town],
                    "shares": {l: round(tot[town].get(l, 0.0) / s, 3) for l in LENS_ORDER}})
    return out


def butterfly(shares: Sequence[dict], width: int = 290) -> str:
    """Two towns, two vocabularies: each lens's share of everything a town's
    meetings say under a lens, one town to the left of the spine and one to
    the right (a single town reads to the right alone)."""
    ts = list(shares)[:2]
    if not ts:
        return '<p class="hint">the lenses need a read meeting</p>'
    mid = width / 2 + 5 if len(ts) == 2 else 110
    rowh, top = 24, 22
    mx = max((v for t in ts for v in t["shares"].values()), default=0.0) or 1.0
    scale = (mid - 20) / mx
    out = []
    if len(ts) == 2:
        out.append(f'<text x="{_r(mid - 4)}" y="10" font-size="10" fill="{ts[0]["color"]}" text-anchor="end" style="{MONO}">{esc(ts[0]["town"])}</text>'
                   f'<text x="{_r(mid + 4)}" y="10" font-size="10" fill="{ts[1]["color"]}" style="{MONO}">{esc(ts[1]["town"])}</text>')
    else:
        out.append(f'<text x="{_r(mid + 4)}" y="10" font-size="10" fill="{ts[0]["color"]}" style="{MONO}">{esc(ts[0]["town"])}</text>')
    trows = []
    for i, lens in enumerate(LENS_ORDER):
        y = top + i * rowh
        out.append(f'<text x="{_r(mid)}" y="{y - 3}" font-size="10" fill="{MUTED}" text-anchor="middle">{lens}</text>')
        if len(ts) == 2:
            a, b = ts[0]["shares"].get(lens, 0), ts[1]["shares"].get(lens, 0)
            wa, wb = a * scale, b * scale
            out.append(f'<rect x="{_r(mid - 4 - wa)}" y="{y}" width="{_r(wa)}" height="14" fill="{ts[0]["color"]}" opacity=".85"/>'
                       f'<rect x="{_r(mid + 4)}" y="{y}" width="{_r(wb)}" height="14" fill="{ts[1]["color"]}" opacity=".85"/>'
                       f'<text x="{_r(mid - 8 - wa)}" y="{y + 11}" font-size="10" fill="{INK2}" text-anchor="end" style="{MONO}">{round(100 * a)}%</text>'
                       f'<text x="{_r(mid + 8 + wb)}" y="{y + 11}" font-size="10" fill="{INK2}" style="{MONO}">{round(100 * b)}%</text>')
            trows.append(f'<tr><td>{lens}</td><td>{round(100 * a)}%</td><td>{round(100 * b)}%</td></tr>')
        else:
            a = ts[0]["shares"].get(lens, 0)
            wa = a * scale
            out.append(f'<rect x="{_r(mid + 4)}" y="{y}" width="{_r(wa)}" height="14" fill="{ts[0]["color"]}" opacity=".85"/>'
                       f'<text x="{_r(mid + 8 + wa)}" y="{y + 11}" font-size="10" fill="{INK2}" style="{MONO}">{round(100 * a)}%</text>')
            trows.append(f'<tr><td>{lens}</td><td>{round(100 * a)}%</td></tr>')
    H = top + rowh * len(LENS_ORDER)
    svg = (f'<svg class="bs-butterfly" width="{width}" height="{H}" viewBox="0 0 {width} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="each town’s share of words by lens">' + "".join(out) + "</svg>")
    head = "<th>lens</th>" + "".join(f'<th>{esc(t["town"])}</th>' for t in ts)
    return f'<div class="fp-chartwrap">{svg}</div>' + twin("".join(trows), head)


def who_when(names: Sequence[dict], months: Sequence[str], towns_by_pid: Dict[str, str],
             base: str = "/app", width: int = 290, people: int = 3, places: int = 3) -> str:
    """Who, and when: the names the record hears, month by month — a dot is
    a month the name was said, bigger where it was said in more meetings,
    in the colour of the town that says it most. Each name is a search."""
    ms = [m for m in months if is_month(m)]
    picked = [n for n in names if n.get("kind") == "people"][:people] + \
             [n for n in names if n.get("kind") == "places"][:places]
    if not picked or not ms:
        return '<p class="hint">the record needs two read meetings to know who keeps coming up</p>'
    left, rowh = 120.0, 22
    step = (width - left - 6) / len(ms)
    cx = lambda i: left + step * (i + 0.5)
    out, trows = [], []
    for i, mo in enumerate(ms):
        out.append(f'<text x="{_r(cx(i))}" y="{rowh * len(picked) + 10}" font-size="9" fill="{MUTED}" text-anchor="middle" style="{MONO}">{month_short(mo)[0]}</text>')
    for r, n in enumerate(picked):
        y = rowh * r + 4
        by: Dict[str, int] = {}
        towns: Dict[str, int] = {}
        for mt in (n.get("meetings") or []):
            mo = str(mt.get("date") or "")[:7]
            if is_month(mo):
                by[mo] = by.get(mo, 0) + 1
            tw = towns_by_pid.get(str(mt.get("pid") or ""), "")
            if tw:
                towns[tw] = towns.get(tw, 0) + 1
        town = max(towns, key=lambda t: (towns[t], t)) if towns else ""
        col = town_color(town) if n.get("kind") == "places" else (town_color(town) if len({towns_by_pid.get(str(mt.get("pid") or ""), "") for mt in (n.get("meetings") or [])} - {""}) == 1 else INK)
        href = search_url(str(n.get("name") or ""), "", base).replace("&", "&amp;")
        out.append(f'<a href="{href}"><text x="0" y="{y + 20}" font-size="12" fill="{INK}">{esc(cut_words(n.get("name"), 22))}</text></a>')
        for i, mo in enumerate(ms):
            k = by.get(mo, 0)
            if k:
                out.append(f'<circle cx="{_r(cx(i))}" cy="{y + 16}" r="{_r(min(7.2, 3.0 + 1.4 * k))}" fill="{col}" opacity=".85">'
                           f'<title>{esc(n.get("name"))} · {month_short(mo)}: {n_of(k, "meeting")}</title></circle>')
            else:
                out.append(f'<circle cx="{_r(cx(i))}" cy="{y + 16}" r="1.2" fill="{RULE}"/>')
        trows.append(f'<tr><td><a href="{href}">{esc(n.get("name"))}</a></td><td>{esc(n.get("kind"))}</td>'
                     f'<td>{n_of(len(n.get("meetings") or []), "meeting")}</td><td>{int(n.get("count") or 0)}</td></tr>')
    H = rowh * len(picked) + 16
    svg = (f'<svg class="bs-whowhen" width="{width}" height="{H}" viewBox="0 0 {width} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="who was named, month by month">' + "".join(out) + "</svg>")
    return f'<div class="fp-chartwrap">{svg}</div>' + twin("".join(trows), "<th>name</th><th>kind</th><th>meetings</th><th>mentions</th>")


def ayes_of(v: dict) -> Optional[int]:
    """The ayes in a roll call: the roll's yes votes, else the tally's first
    number, else None (nothing countable — the square shows a dot, not a zero)."""
    roll = v.get("roll") or []
    if roll:
        return sum(1 for r in roll if str(r.get("vote") or "").lower() in ("yes", "aye", "y"))
    m = re.match(r"\s*(\d+)", str(v.get("tally") or ""))
    return int(m.group(1)) if m else None


def vote_grid(votes: Sequence[dict], base: str = "/app") -> str:
    """The roll calls: a square per vote, month by month, the ayes in each,
    the one that failed in rust; every square opens the tape where the vote
    was taken. `votes` rows carry pid, date, t, outcome, tally, roll."""
    vs = sorted((v for v in votes if v.get("pid") and is_month(v.get("date"))),
                key=lambda v: (str(v.get("date")), str(v.get("pid")), float(v.get("t") or 0)))
    if not vs:
        return '<p class="hint">No roll call has been read from a tape yet.</p>'
    months = month_range([str(v["date"])[:7] for v in vs])
    by: Dict[str, List[dict]] = {}
    for v in vs:
        by.setdefault(str(v["date"])[:7], []).append(v)
    sq, gap, cols = 16, 3, 4
    x0 = 0.0
    out, trows = [], []
    maxrows = 1
    for mo in months:
        ms = by.get(mo, [])
        ncols = max(1, min(cols, len(ms)))
        out.append(f'<text x="{_r(x0)}" y="10" font-size="10" fill="{MUTED}" style="{MONO}">{month_short(mo)} · {len(ms)}</text>')
        for i, v in enumerate(ms):
            r, c = divmod(i, cols)
            maxrows = max(maxrows, r + 1)
            x, y = x0 + c * (sq + gap), 16 + r * (sq + gap + 1)
            out_ = str(v.get("outcome") or "")
            fill, op = (RUST, ".95") if out_ == "fails" else (INK, ".8") if out_ == "passes" else (INK, ".45")
            tip = f'{v.get("date")} · {out_}' + (f' {v["tally"]}' if v.get("tally") else "") + f' — {cut_words(v.get("motion"), 100)}'
            out.append(f'<a href="{base}/m/{esc(v["pid"])}#t{int(float(v.get("t") or 0))}"><rect x="{_r(x)}" y="{y}" width="{sq}" height="{sq}" rx="3" fill="{fill}" opacity="{op}"/>'
                       f'<text x="{_r(x + sq / 2)}" y="{y + 12}" font-size="8" fill="{PAPER}" text-anchor="middle" style="{MONO}">{"·" if ayes_of(v) is None else ayes_of(v)}</text><title>{esc(tip)}</title></a>')
            trows.append(f'<tr><td><a href="{base}/m/{esc(v["pid"])}#t{int(float(v.get("t") or 0))}">{esc(v.get("date"))}</a></td>'
                         f'<td>{esc(cut_words(v.get("motion"), 90))}</td><td>{esc(out_)}</td><td>{esc(v.get("tally") or "")}</td></tr>')
        x0 += ncols * (sq + gap) + 14
    W, H = int(x0), 16 + maxrows * (sq + gap + 1) + 4
    svg = (f'<svg class="bs-votegrid" width="{W}" height="{H}" viewBox="0 0 {W} {H}" xmlns="http://www.w3.org/2000/svg" role="img" '
           f'aria-label="{n_of(len(vs), "roll call")} by month">' + "".join(out) + "</svg>")
    return f'<div class="fp-chartwrap">{svg}</div>' + twin("".join(trows), "<th>date</th><th>motion</th><th>outcome</th><th>tally</th>")


def thread_spark(dates: Sequence[str], months: Sequence[str], color: str = INK,
                 width: int = 200, height: int = 44, label: str = "") -> str:
    """A thread's sparkline: the meetings that took it up, month by month —
    the small multiple every thread card and the type-ahead's over-time box
    carry. The JS twin is app.js bsSpark."""
    ms = [m for m in months if is_month(m)]
    if not ms:
        return ""
    counts = [0] * len(ms)
    idx = {m: i for i, m in enumerate(ms)}
    for d in dates:
        mo = str(d or "")[:7]
        if mo in idx:
            counts[idx[mo]] += 1
    step = (width - 8) / max(1, len(ms) - 1)
    pts = [(4 + i * step, height - 6 - min(2, c) * 15) for i, c in enumerate(counts)]
    line = " ".join(f"{_r(x)},{_r(y)}" for x, y in pts)
    dots = "".join(f'<circle cx="{_r(x)}" cy="{_r(y)}" r="3" fill="{color}"><title>{month_short(ms[i])}: {n_of(counts[i], "meeting")}</title></circle>'
                   for i, (x, y) in enumerate(pts) if counts[i])
    return (f'<svg class="bs-spark" width="{width}" height="{height}" viewBox="0 0 {width} {height}" xmlns="http://www.w3.org/2000/svg" role="img" '
            f'aria-label="{esc(label or "meetings that took it up, month by month")}">'
            f'<polyline points="{line}" fill="none" stroke="{color}" stroke-width="1.5" opacity=".55"/>{dots}</svg>')


# --------------------------------------------------------------------------
# how the talk flowed — the lens river
# --------------------------------------------------------------------------

def _smooth(pts: Sequence[Tuple[float, float]]) -> str:
    """A path through the points, quadratic through the midpoints — the
    band's edge; the same expression forwards and, reversed, backwards."""
    if len(pts) < 2:
        return ""
    out = [f"M{_r(pts[0][0])},{_r(pts[0][1])}"]
    for i in range(1, len(pts) - 1):
        mx, my = (pts[i][0] + pts[i + 1][0]) / 2, (pts[i][1] + pts[i + 1][1]) / 2
        out.append(f"Q{_r(pts[i][0])},{_r(pts[i][1])} {_r(mx)},{_r(my)}")
    out.append(f"L{_r(pts[-1][0])},{_r(pts[-1][1])}")
    return " ".join(out)


def river_data(framing_rows: Sequence[dict], towns_by_pid: Dict[str, str]) -> dict:
    rows = sorted((r for r in framing_rows if r.get("pid")),
                  key=lambda r: (str(r.get("date") or "9999"), str(r.get("pid"))))
    ms = []
    for r in rows:
        tot = float(r.get("total") or 0) or 1.0
        ms.append({"pid": str(r["pid"]), "date": str(r.get("date") or ""), "town": towns_by_pid.get(str(r["pid"]), ""),
                   "total": int(float(r.get("total") or 0)),
                   "shares": {l: round(float((r.get("lenses") or {}).get(l) or 0) / tot, 4) for l in LENS_ORDER}})
    joins = None
    if ms:
        first = ms[0]["town"]
        for i, m in enumerate(ms):
            if m["town"] and first and m["town"] != first:
                joins = i
                break
    return {"meetings": ms, "joins": joins, "order": list(LENS_ORDER)}


def lens_river(framing_rows: Sequence[dict], towns_by_pid: Dict[str, str], base: str = "/app",
               width: int = 1328, height: int = 260) -> str:
    """How the talk flowed, meeting by meeting: eight bands, each a lens's
    share of a night's framed words, stacked and smoothed, separated by a
    hair of paper, each lens labelled at its widest point, a dashed line
    where the second town joins the record. With the script on a label
    isolates its lens (app.js bsRiver); the bands open the record drawn."""
    d = river_data(framing_rows, towns_by_pid)
    ms = d["meetings"]
    if len(ms) < 2:
        return '<p class="hint">the river needs two read meetings</p>'
    top, bottom = 8.0, height - 22.0
    plot = bottom - top
    n = len(ms)
    xs = [i * width / (n - 1) for i in range(n)]
    # cumulative edges from the bottom up, lens by lens
    base_y = [bottom] * n
    out, labels, trows = [], [], []
    for lens in LENS_ORDER:
        tops = [base_y[i] - ms[i]["shares"][lens] * plot for i in range(n)]
        fwd = _smooth(list(zip(xs, tops)))
        back = _smooth(list(zip(xs, base_y))[::-1])
        path = f'{fwd} L{_r(xs[-1])},{_r(base_y[-1])} {back[1:]} Z'
        out.append(f'<a href="{base}/analytics"><path class="bs-band" data-lens="{lens}" d="{path}" fill="{LENS_COLOR[lens]}" '
                   f'opacity=".86" stroke="{CARD}" stroke-width="1.2"><title>{lens} — its share of each night’s framed words</title></path></a>')
        widest = max(range(n), key=lambda i: (base_y[i] - tops[i], -i))
        if base_y[widest] - tops[widest] >= 9:
            labels.append(f'<text class="bs-rlabel" data-lens="{lens}" x="{_r(xs[widest])}" y="{_r((base_y[widest] + tops[widest]) / 2 + 4)}" '
                          f'font-size="11" fill="{INK}" text-anchor="middle" style="{MONO};paint-order:stroke" stroke="{CARD}" stroke-width="3">{lens}</text>')
        base_y = tops
    if d["joins"] is not None:
        j = d["joins"]
        out.append(f'<line x1="{_r(xs[j])}" y1="4" x2="{_r(xs[j])}" y2="{_r(bottom - 4)}" stroke="{INK}" stroke-dasharray="3 4"/>'
                   f'<text x="{_r(xs[j] + 6)}" y="16" font-size="13" fill="{INK}" class="bs-rjoin">{esc(ms[j]["town"])} joins the record</text>')
    every = max(1, n // 6)
    for i, m in enumerate(ms):
        if i % every and i != n - 1:
            continue
        anchor = "start" if i == 0 else "end" if i == n - 1 else "middle"
        out.append(f'<text x="{_r(xs[i])}" y="{height - 8}" font-size="11" fill="{MUTED}" text-anchor="{anchor}" style="{MONO}">{esc(day_short(m["date"]))}</text>')
    for m in ms:
        trows.append(f'<tr><td><a href="{base}/m/{esc(m["pid"])}">{esc(m["date"] or "undated")}</a></td><td>{esc(m["town"])}</td>'
                     + "".join(f'<td>{round(100 * m["shares"][l])}%</td>' for l in LENS_ORDER) + "</tr>")
    svg = (f'<svg class="bs-river-svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" preserveAspectRatio="none" '
           f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="the share of each lens across every meeting">'
           + "".join(out) + "".join(labels) + "</svg>")
    head = "<th>meeting</th><th>town</th>" + "".join(f"<th>{l}</th>" for l in LENS_ORDER)
    return (f'<div class="bs-river" {data_attr("river", d)}><div class="bs-riverwrap">{svg}</div>'
            + twin("".join(trows), head) + "</div>")


# --------------------------------------------------------------------------
# a word over time — the timeline of meetings (the search page's, pressed)
# --------------------------------------------------------------------------

def timeline_dots(rows: Sequence[dict], base: str = "/app", width: int = 1160, height: int = 170,
                  q: str = "") -> str:
    """When it came up: each meeting that said the word as a dot on the month
    axis, in its town's colour, the body above it and the day above that;
    click one to jump to the first mention. The JS twin is app.js bsTimeline."""
    said = [r for r in rows if r.get("n") and is_month(r.get("date"))]
    months = month_range([str(r["date"])[:7] for r in rows if is_month(r.get("date"))])
    if not said or not months:
        return ""
    x_of = month_axis(months, width)
    colw = width / len(months)
    base_y = 110
    out = []
    for i, mo in enumerate(months):
        out.append(f'<text x="{_r(i * colw + 4)}" y="{height - 8}" font-size="11" fill="{MUTED}" style="{MONO}">{month_short(mo)}</text>'
                   f'<line x1="{_r(i * colw)}" y1="{base_y - 6}" x2="{_r(i * colw)}" y2="{base_y + 6}" stroke="{RULE}"/>')
    out.append(f'<line x1="0" y1="{base_y}" x2="{width}" y2="{base_y}" stroke="{RULE}" stroke-width="2"/>')
    for r in sorted(said, key=lambda r: (str(r["date"]), str(r["pid"]))):
        x = x_of(r["date"])
        col = town_color(r.get("town"))
        out.append(f'<a href="{base}/m/{esc(r["pid"])}#t{int(float(r.get("first_t") or 0))}" class="bs-tdot" data-pid="{esc(r["pid"])}">'
                   f'<circle cx="{_r(x)}" cy="{base_y}" r="9" fill="{col}"><title>{esc(r.get("title") or r["pid"])} — {n_of(int(r["n"]), "line")}</title></circle>'
                   f'<text x="{_r(x)}" y="{base_y - 22}" font-size="12" fill="{INK2}" text-anchor="middle" style="font-family:var(--font-sans)">{esc(cut_words(r.get("body"), 24))}</text>'
                   f'<text x="{_r(x)}" y="{base_y - 38}" font-size="11" fill="{MUTED}" text-anchor="middle" style="{MONO}">{esc(day_short(r["date"]))}</text></a>')
    label = f'when “{q}” came up' if q else "when it came up"
    return (f'<div class="bs-timeline"><span class="kicker">{esc(label)} — each dot is a meeting; click one to jump</span>'
            f'<div class="fp-chartwrap"><svg class="bs-timeline-svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" '
            f'xmlns="http://www.w3.org/2000/svg" role="img" aria-label="{esc(label)}">' + "".join(out) + "</svg></div></div>")
