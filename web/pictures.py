"""Every picture the press draws, as a file a reader can take (specs/28 §3.3).

The front page's pictures were the record's most shareable thing and the one
thing on it that did not download: a reporter who wanted "mentions of AI,
month by month" for a slide had a screenshot. Now each picture carries a
link to the same picture as a standalone .svg — a white page, the story's
own title above it, a line that says how to read its marks, and the source
and the licence beneath. Pure functions of the planes, like every other
picture: two presses agree byte for byte.

Two kinds. The pictures the press already draws as SVG (the votes as dots,
the word clouds, the shape of a meeting) are wrapped (`standalone`), and
every mark that was a link stays a link, made absolute so it works from a
slide deck. The topic story's three HTML pictures — the months, the tapes,
the words beside it — are drawn again here as SVG (`months_svg`,
`tapes_svg`, `words_svg`); they are pictures only, and the address on
their source line is the way back. Their JS twins (app.js tpMonthsSvg,
tpTapesSvg, tpWordsSvg) draw the same bytes for the search page's live
story, so a reader's own word downloads too, and a node twin holds the two
equal.

A file is strict XML where a page is forgiving: a control character in a
caption or a title would leave a file nothing can open, so every text in
it is stripped of the characters XML forbids before it is escaped.

The press collects the files as it renders (`put`) and writes them once
(`flush`), from emit_stubs — the one place the desk bake and the hosted
press share, so the two editions carry the same pictures.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Dict, List, Sequence

GREEN = "#052e16"     # measurement — the charts' own palette (web/charts.py)
INK = "#0f172a"
SLATE = "#475569"
HAIR = "#e2e8f0"
FONT = "JetBrains Mono, ui-monospace, Menlo, Consolas, monospace"
MONTH_ABBR = ("", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")
_MONTH = re.compile(r"^[0-9]{4}-(0[1-9]|1[0-2])")
_DAY = re.compile(r"^[0-9]{4}-[0-9]{2}-[0-9]{2}")

# what XML 1.0 forbids in text: C0 controls but tab, newline and return; the
# two noncharacters; a lone surrogate (in a Python str a real astral
# character is one code point, never in the surrogate range)
_XML_BAD = re.compile("[\x00-\x08\x0b\x0c\x0e-\x1f\ufffe\uffff\ud800-\udfff]")

_PENDING: Dict[str, str] = {}
_SITE = {"base": "https://publicrecord.studio", "edition": ""}

# how to read each picture's marks, on the file itself — on a slide, the
# page's commentary is not there to say it
LEGEND = {
    "months": "a bar is the month's mentions · a filled dot, a meeting that said it; a hollow one, a meeting that did not",
    "tapes": "a row is one night's tape, start to end · a taller bar, more lines said it there",
    "words": "counted in each line that says it and the lines either side, civic stopwords out",
    "votes": "a filled dot passes · a hollow dot fails · a square, any other outcome",
    "cloud": "sized by how often each word was said, civic stopwords out",
    "shape": "a bar is a roll call · a triangle a decision · a diamond pushback · a dot a question",
}


def x(s) -> str:
    """The reader's own escape (& < > "), after the characters XML forbids
    are gone — the JS twin (tpPicX) does the same, byte for byte. Text
    content and double-quoted attributes only, where ' is inert."""
    t = _XML_BAD.sub("", str("" if s is None else s))
    return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")


def reset(site_base: str, edition: str = "") -> None:
    """A fresh press: nothing pending, links made absolute against this site,
    the source line dated by the record it was pressed from."""
    _PENDING.clear()
    _SITE["base"] = str(site_base or "").rstrip("/") or "https://publicrecord.studio"
    _SITE["edition"] = str(edition or "")


def source(page: str, how: str = "counted from the record’s transcripts, no model") -> str:
    """The line under every picture file: where it lives, how it was made,
    the record it was pressed from, the licence the record's content carries."""
    ed = f" · the record of {_SITE['edition']}" if _SITE["edition"] else ""
    return f"{_SITE['base']}{page} · {how}{ed} · CC BY-SA 4.0"


_ONE_SVG = re.compile(r"<svg\b.*?</svg>", re.S)


def take(name: str, pressed_html: str, title: str, page: str, hash_page: str = "", legend: str = "") -> str:
    """A pressed picture's one <svg>, kept as a file; the link to it, or
    nothing when the picture drew no SVG (an empty record's honest line)."""
    m = _ONE_SVG.search(str(pressed_html or ""))
    if not m:
        return ""
    svg = standalone(m.group(0), title, source(page), page=hash_page, legend=legend)
    if not svg:
        return ""
    return link(put(name, svg), slug(title) + ".svg", title)


def put(name: str, svg: str) -> str:
    """Keep a picture for the press to write; its address on the edition."""
    _PENDING[name] = svg
    return f"/app/pictures/{name}.svg"


def flush(out: Path) -> int:
    d = Path(out) / "pictures"
    d.mkdir(parents=True, exist_ok=True)
    for name in sorted(_PENDING):
        (d / f"{name}.svg").write_text(_PENDING[name], encoding="utf-8")
    n = len(_PENDING)
    _PENDING.clear()
    return n


def link(href: str, filename: str, title: str = "") -> str:
    """The pressed way to the file — an anchor with a download name, content
    in the paper (no button, no script: it works with JavaScript off); its
    name says which picture, where ten on a page read the same."""
    named = f' aria-label="download “{x(title)}” as .svg"' if title else ""
    return (f'<p class="pic-dl"><a href="{x(href)}" download="{x(filename)}"{named}>'
            '↓ this picture, as .svg</a></p>')


def slug(s: str) -> str:
    """A download's name, readable: lowercase words and hyphens."""
    s = re.sub(r"[’']", "", str(s or "").lower())      # "the record’s" names "the-records", not "the-record-s"
    return re.sub(r"[^a-z0-9]+", "-", s).strip("-") or "picture"


def key(pid: str) -> str:
    """A meeting's part of a file name — its id as the record writes it
    (/app/m/<pid>/): case kept, so two tapes whose ids differ only in case
    never share a file; anything outside the id alphabet made safe."""
    return re.sub(r"[^A-Za-z0-9_-]", "_", str(pid or "")) or "_"


def _fit(w: int, title: str, source: str, legend: str) -> int:
    """A page wide enough for its own words: the title at 8 px a character,
    the small lines at 6.1 — counted in characters (code points), as the JS
    twin counts them — so nothing runs off the page's right edge."""
    where, _, how = str(source).partition(" · ")
    need = [32 + len(_XML_BAD.sub("", str(title))) * 8] + \
           [32 + len(_XML_BAD.sub("", str(t))) * 61 // 10 for t in (where, how, legend)]
    return max([w] + need)


def _page(w: int, h: int, title: str, source: str, inner: str, legend: str = "") -> str:
    """The file around a picture: a white page, its title (and a <title>, so
    a slide or a document can name it), the picture, the line that says how
    to read it, and the source beneath in two lines — where it lives, then
    how it was made. `h` is the picture's own height; the lines add theirs."""
    where, _, how = str(source).partition(" · ")
    h += 14 + (14 if legend else 0)
    key_line = f'<text x="16" y="{h - 40}" font-size="10" fill="{SLATE}">{x(legend)}</text>' if legend else ""
    return ('<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" '
            f'font-family="{FONT}"><title>{x(title)}</title>'
            f'<rect width="{w}" height="{h}" fill="#ffffff"/>'
            f'<text x="16" y="26" font-size="13" font-weight="700" fill="{INK}">{x(title)}</text>'
            + inner + key_line
            + f'<text x="16" y="{h - 26}" font-size="10" fill="{SLATE}">{x(where)}</text>'
            + f'<text x="16" y="{h - 12}" font-size="10" fill="{SLATE}">{x(how)}</text></svg>\n')


# --------------------------------------------------------------------------
# a pressed SVG, wrapped
# --------------------------------------------------------------------------

_SVG_OPEN = re.compile(r'^<svg\b[^>]*\bwidth="([0-9]+)"[^>]*\bheight="([0-9]+)"[^>]*>')


def standalone(svg: str, title: str, source: str, page: str = "", legend: str = "") -> str:
    """A pressed inline <svg> as a file: nested under a title, over a source
    line, its /app/ links made absolute — and its "#t…" links, which point
    into the page they were pressed on, pointed at that page (`page`)."""
    m = _SVG_OPEN.match(str(svg or "").strip())
    if not m:
        return ""
    w, h = int(m.group(1)), int(m.group(2))
    inner = str(svg).strip()[m.end():]
    if inner.endswith("</svg>"):
        inner = inner[:-len("</svg>")]
    inner = _XML_BAD.sub("", inner)
    base = _SITE["base"]
    inner = inner.replace('href="/app/', f'href="{base}/app/')
    if page:
        inner = inner.replace('href="#', f'href="{base}{page}#')
    W = _fit(max(w + 32, 600), title, source, legend)
    H = 44 + h + 36
    return _page(W, H, title, source,
                 f'<svg x="{(W - w) // 2}" y="44" width="{w}" height="{h}" viewBox="0 0 {w} {h}">{inner}</svg>',
                 legend)


# --------------------------------------------------------------------------
# the topic story's three pictures, drawn as SVG (twins: app.js tp*Svg)
# --------------------------------------------------------------------------

_NUM = re.compile(r"^[ \t\n\r]*[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)([eE][+-]?[0-9]+)?[ \t\n\r]*$")


def _n(v) -> int:
    """A count, whatever arrived: a number or a plain numeric string, clamped
    to [0, 1e9] and truncated; anything else is 0 — never a throw (the
    decoders' law). Spelled so the JS twin (tpPicN) reads every input the
    same way: no bools, no hex, no underscores, ASCII digits only."""
    if isinstance(v, bool) or not isinstance(v, (int, float, str)):
        return 0
    if isinstance(v, str) and not _NUM.match(v):
        return 0
    try:
        f = float(v)
    except (ValueError, OverflowError):
        return 0
    if f != f or f in (float("inf"), float("-inf")):
        return 0
    return int(min(max(f, 0.0), 1e9))


def _s(v) -> str:
    """A label, when it is one: a string, else nothing."""
    return v if isinstance(v, str) else ""


_WS = " \t\n\r"      # the whitespace both twins trim a word by — named, so they agree


def _cut(s: str, n: int) -> str:
    """At most n characters (code points — the JS twin counts the same way)."""
    return s if len(s) <= n else s[:n - 1] + "…"


def months_svg(months: Sequence[dict], title: str, source: str, legend: str = LEGEND["months"]) -> str:
    """Mentions, month by month — a column per month, contiguous; the count
    over its bar; under it a dot per meeting (filled where the word came up,
    hollow where it did not) — or, past twenty meetings, the count of them
    ("25/30"), never a silent twenty; the month, and the year where it turns."""
    ms = [m for m in months if isinstance(m, dict) and _MONTH.match(_s(m.get("month")))]
    colw, bar_max = 40, 72
    n = len(ms)
    mx = max([_n(m.get("mentions")) for m in ms] + [1])
    most = min(20, max([_n(m.get("meetings")) for m in ms] + [0]))
    dot_rows = max(1, (most + 4) // 5)
    base_y = 58 + bar_max
    label_y = base_y + 10 + dot_rows * 7 + 10
    W = _fit(max(32 + n * colw, 600), title, source, legend)
    H = label_y + 14 + 12 + 36
    x0 = (W - n * colw) // 2
    parts: List[str] = [f'<line x1="{x0}" y1="{base_y}" x2="{x0 + n * colw}" y2="{base_y}" stroke="{HAIR}"/>']
    prev_year = ""
    for i, m in enumerate(ms):
        mo = str(m["month"])
        c = _n(m.get("mentions"))
        meets = _n(m.get("meetings"))
        said = min(meets, _n(m.get("said")))
        cx = x0 + i * colw + colw // 2
        if c:
            h = 4 + (bar_max - 4) * c // mx
            parts.append(f'<rect x="{cx - 12}" y="{base_y - h}" width="24" height="{h}" fill="{GREEN}"/>')
            parts.append(f'<text x="{cx}" y="{base_y - h - 5}" text-anchor="middle" font-size="11" '
                         f'font-weight="700" fill="{INK}">{c}</text>')
        else:
            parts.append(f'<rect x="{cx - 12}" y="{base_y - 2}" width="24" height="2" fill="{HAIR}"/>')
        if meets > 20:
            parts.append(f'<text x="{cx}" y="{base_y + 13}" text-anchor="middle" font-size="9" '
                         f'fill="{GREEN}">{said}/{meets}</text>')
        else:
            for k in range(meets):
                row, col = k // 5, k % 5
                in_row = min(5, meets - row * 5)
                dx = cx + col * 7 - ((in_row - 1) * 7) // 2
                dy = base_y + 10 + row * 7
                if k < said:
                    parts.append(f'<circle cx="{dx}" cy="{dy}" r="2.5" fill="{GREEN}"/>')
                else:
                    parts.append(f'<circle cx="{dx}" cy="{dy}" r="2.5" fill="#ffffff" stroke="{GREEN}"/>')
        parts.append(f'<text x="{cx}" y="{label_y}" text-anchor="middle" font-size="10" '
                     f'fill="{SLATE if meets else HAIR}">{MONTH_ABBR[int(mo[5:7])]}</text>')
        if mo[:4] != prev_year:
            parts.append(f'<text x="{cx}" y="{label_y + 12}" text-anchor="middle" font-size="9" '
                         f'fill="{SLATE}">{mo[:4]}</text>')
            prev_year = mo[:4]
    return _page(W, H, title, source, "".join(parts), legend)


def tapes_svg(rows: Sequence[dict], title: str, source: str, legend: str = LEGEND["tapes"]) -> str:
    """Where it fell — a row per night that said it, the tape in its slices,
    a taller bar where it came up more (each row on its own scale, as on
    the page); the night on the left, its lines on the right."""
    said = [r for r in rows if isinstance(r, dict) and _n(r.get("n"))]
    row_h, bw = 24, 6
    W = _fit(640, title, source, legend)
    H = 52 + len(said) * row_h + 36
    parts: List[str] = []
    for i, r in enumerate(said):
        y = 52 + i * row_h
        bins = r.get("bins")
        counts = [_n(c) for c in bins][:64] if isinstance(bins, list) else []
        mx = max(counts + [1])
        date = _s(r.get("date"))
        when = date[5:10] if _DAY.match(date) else "undated"
        label = _cut(f'{when} · {_s(r.get("body"))}', 26)
        parts.append(f'<text x="16" y="{y + 16}" font-size="11" fill="{INK}">{x(label)}</text>')
        parts.append(f'<line x1="200" y1="{y + 18}" x2="{200 + len(counts) * bw}" y2="{y + 18}" stroke="{HAIR}"/>')
        for j, c in enumerate(counts):
            if c:
                h = 2 + 14 * c // mx
                parts.append(f'<rect x="{200 + j * bw}" y="{y + 18 - h}" width="{bw - 1}" height="{h}" fill="{GREEN}"/>')
        from .charts import n_of          # counted nouns go through n_of (CLAUDE.md)
        lines_said = n_of(_n(r.get("n")), "line")
        parts.append(f'<text x="{210 + len(counts) * bw}" y="{y + 16}" font-size="11" fill="{SLATE}">'
                     f'{lines_said}</text>')
    return _page(W, H, title, source, "".join(parts), legend)


def words_svg(words: Sequence[dict], title: str, source: str, legend: str = LEGEND["words"]) -> str:
    """The words beside it — magnitude bars, the word and its count."""
    ws = [w for w in words if isinstance(w, dict) and _s(w.get("word")).strip(_WS)]
    row_h = 20
    W = _fit(600, title, source, legend)
    H = 52 + len(ws) * row_h + 36
    mx = max([_n(w.get("count")) for w in ws] + [1])
    parts: List[str] = []
    for i, w in enumerate(ws):
        y = 52 + i * row_h
        c = _n(w.get("count"))
        bar = 2 + 298 * c // mx
        word = x(_cut(_s(w.get("word")).strip(_WS), 18))    # built first: an f-string holds no backslash
        parts.append(f'<text x="16" y="{y + 13}" font-size="11" fill="{INK}">{word}</text>')
        parts.append(f'<rect x="150" y="{y + 4}" width="{bar}" height="11" fill="{GREEN}"/>')
        parts.append(f'<text x="{150 + bar + 8}" y="{y + 13}" font-size="11" font-weight="700" fill="{INK}">{c}</text>')
    return _page(W, H, title, source, "".join(parts), legend)
