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

GREEN = "#052e16"     # measurement (the record's deep green)
INK = "#0f172a"       # text
SLATE = "#475569"     # labels
HAIR = "#e2e8f0"      # rules

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


def _rd_cut(ln: str, n: int) -> str:
    """A line cut at a word — and never inside a receipt group: an unclosed
    "[12:12, 17…" at the cut is dropped whole, not left half-linked."""
    c = cut_words(ln, n)
    if c.endswith("…") and c != ln:
        body = re.sub(r"\s*\[[^\]]*$", "", c[:-1])
        c = body.rstrip(",;:—- ") + "…"
    return c


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
        # stands (cut to the room left) — a heading or a line of bare syntax
        # never spends the cut, and the lede never ends on a heading
        def head_or_bare(ln: str) -> bool:
            return (not plain and bool(_RD_HASH.match(ln) or _RD_BOLDLINE.match(ln))) \
                or not _rd_inline(ln, "", plain).strip(_RD_WS)
        kept, used, words = [], 0, False
        for ln in lines:
            room = limit - used
            if len(ln) <= room:
                kept.append(ln)
                used += len(ln)
                words = words or not head_or_bare(ln)
                continue
            if not words and not head_or_bare(ln):
                kept.append(_rd_cut(ln, max(room, 200)))
                words = True
            break
        while kept and head_or_bare(kept[-1]):
            kept.pop()
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
