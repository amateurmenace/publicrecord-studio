"""The front pages, listed (specs/29 P2, board 9).

The record presses its own front pages every night; readers press theirs
whenever they like and share them as links. A short link is a share: the
API stores the page's canonical bytes under a content address
(record/papers.py), and the press lists what the store holds — the title,
what the page is made of, its first still — beside the record's own. Nobody
signs, because the record keeps no reader identity, so a front page is
judged by its receipts. A steward takes a page down by moving its object out
of the listed prefix (record/OPERATING.md §5, "the front pages"): the next
press stops listing it, the store refuses the same bytes again, and its
short link says the store holds nothing at that address — the reader's
existing words, none new.

Everything here is pure over the pressed planes, the stored bytes and one
reference day (the pressing's, handed in — never the wall clock at render,
so two presses of one store on one day are byte-identical and the words on
a static page do not go stale). A stored blob that is not a page, whatever
shape it has, makes no card, never a failed press (decodeReel's law,
press-side). The words that say what kind of page it is follow the reader's
own `bsMadeFrom` (web/static/app.js); a node twin holds the kinds and the
counts equal.

Three brakes, all derived from the store's own timestamps and no new field
(a review's catch: the newest title on the record's masthead within one
press, and nothing metering the store): pages minted before LISTED_SINCE —
the day the short-link button began to say it lists the page — are not
listed; at most PER_DAY pages from any one day are (a flood buries a day,
not the store); and the front page's strip seats only a page a day old,
so a steward's morning glance at the gallery comes first.
"""

from __future__ import annotations

import datetime as _dt
import json
import re
from typing import Dict, List, Optional, Sequence

from . import charts
from .charts import esc, n_of, still_src

MAX_LISTED = 400          # a press lists this many of the newest shared pages (record/papers.py LIST_MAX)
PER_DAY = 12              # …and this many from any one day
STRIP_READERS = 1         # readers' pages on the front page's strip (board 1)
WEEK_DAYS = 7
LISTED_SINCE = _dt.date(2026, 9, 24)   # the day "⚡ short link" began to say "lists it on the front pages"
SCHEMA = "publicrecord.paper/1"

# what each block kind reads as, in a card's "made from" line — the reader's
# own labels (pillLabel), said plainly
_WHAT = {"lead": "a lead story", "week": "the week", "threads": "threads", "strip": "how they talked",
         "search": "a search box", "reading": "the record’s reading", "digest": "what changed"}
_CHART = {"reach": "a timeline", "votes": "the roll calls", "numbers": "the numbers", "shape": "the shape of the tape",
          "framing": "the framing", "ledger": "every roll call", "topics": "recurring topics"}
_ID = re.compile(r"[0-9a-f]{16}")


def _blocks(paper) -> List[dict]:
    bl = paper.get("blocks") if isinstance(paper, dict) else None
    return [b for b in bl if isinstance(b, dict)] if isinstance(bl, list) else []


def _clips(b: dict) -> List[dict]:
    cl = b.get("clips")
    return [c for c in cl if isinstance(c, dict)] if isinstance(cl, list) else []


def pids_of(blocks: Sequence[dict]) -> List[str]:
    """Every meeting a page cites, in the order it cites them (a reel's clips included)."""
    out: List[str] = []
    for b in blocks:
        if not isinstance(b, dict):
            continue
        ps = [c.get("pid") for c in _clips(b)] if b.get("kind") == "reel" else [b.get("pid")]
        for p in ps:
            if isinstance(p, str) and p and p not in out:
                out.append(p)
    return out


def slugs_of(blocks: Sequence[dict]) -> List[str]:
    out: List[str] = []
    for b in blocks:
        s = b.get("slug") if isinstance(b, dict) else None
        if isinstance(s, str) and s and s not in out:
            out.append(s)
    return out


def paragraphs_of(blocks: Sequence[dict]) -> int:
    """The writer's paragraphs, counted as the reader counts them (bsMadeFrom)."""
    n = 0
    for b in blocks:
        if isinstance(b, dict) and b.get("kind") == "note" and isinstance(b.get("text"), str):
            n += len([p for p in re.split(r"\n+", b["text"].strip()) if p.strip()])
    return n


def kind_of(blocks: Sequence[dict]) -> str:
    """What kind of front page this is, read off its blocks — the reader's
    bsMadeFrom rule, claimed only where the shape bears it out."""
    bs = [b for b in blocks if isinstance(b, dict)]
    first = bs[0] if bs else {}
    second = bs[1] if len(bs) > 1 else {}
    pids = pids_of(bs)
    k = first.get("kind")
    if (k == "lead" or (k == "story" and first.get("story") == "meeting")) and len(pids) == 1:
        return "One meeting"
    if k == "story" and first.get("story") == "issue":
        return ("A vote and its history" if second.get("kind") == "chart" and second.get("chart") == "ledger"
                else "An issue over time")
    if k == "names" and first.get("who"):
        who = str(first.get("who"))
        return ("A place on the record" if who.startswith("l-") else
                "An organization on the record" if who.startswith("o-") else "A person on the record")
    if (k == "strip" and first.get("town") and second.get("kind") == "strip" and second.get("town")
            and second.get("town") != first.get("town")):
        return "Two towns, side by side"
    if k in ("strip", "threads"):
        return "The record, over time"
    if k == "chart" and first.get("chart") == "votes" and not first.get("pid"):
        return "The roll calls, watched"
    return "A front page"


def kind_slug(kind: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", kind.lower()).strip("-")


def town_slug(town: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", str(town or "").lower()).strip("-")


def what_of(blocks: Sequence[dict], cap: int = 5) -> str:
    """The blocks, said in order: 'a timeline, a reel of 3 clips, 2 paragraphs'."""
    seen: List[str] = []
    quotes = docs = 0
    for b in blocks:
        if not isinstance(b, dict):
            continue
        k = b.get("kind")
        if k == "note":
            continue
        if k == "quote":
            quotes += 1
            continue
        if k == "doc":
            docs += 1
            continue
        if k == "story":
            continue    # the meetings and issues a page is made from are counted beside it, not named twice
        elif k == "chart":
            w = _CHART.get(str(b.get("chart")), "a chart")
        elif k == "reel":
            w = f"a reel of {n_of(len(_clips(b)), 'clip')}"
        elif k == "names":
            w = "a name" if b.get("who") else "who and where"
        else:
            w = _WHAT.get(str(k), "")
        if w and w not in seen:
            seen.append(w)
    if quotes:
        seen.append(n_of(quotes, "quote"))
    if docs:
        seen.append(n_of(docs, "filing"))
    paras = paragraphs_of(blocks)
    if paras:
        seen.append(n_of(paras, "paragraph"))
    if len(seen) > cap:
        seen = seen[:cap] + ["more"]
    return ", ".join(seen)


def _day(iso) -> Optional[_dt.date]:
    try:
        return _dt.datetime.fromisoformat(str(iso).replace("Z", "+00:00")).date()
    except (TypeError, ValueError):
        return None


def when_words(created, today: _dt.date) -> str:
    """'shared September 20' — the day, said absolutely, so a static page
    never says 'today' a week later; the year only when it is not this one."""
    d = _day(created)
    if d is None:
        return ""
    return f"{d.strftime('%B')} {d.day}" + ("" if d.year == today.year else f", {d.year}")


def _town_of_slug(slug: str) -> str:
    """The town an issue id names (issue:<town>:<rest> → issue_<town>_<rest>),
    for a plane that carries none — a hyphenated town id reads as its words."""
    m = re.match(r"^issue_([a-z0-9-]+)_", str(slug or ""))
    return " ".join(w.capitalize() for w in m.group(1).split("-") if w) if m else ""


def is_page(paper) -> bool:
    """The shape the store keeps (record/papers.py canonical), loosely: a
    dict with the schema, a list of dict blocks each with a kind, a reel's
    clips a list of dicts, a note's text a string. Anything else is not a
    page — a hand-placed object, never the store's — and makes no card."""
    if not isinstance(paper, dict) or paper.get("schema") != SCHEMA:
        return False
    bl = paper.get("blocks")
    if not isinstance(bl, list) or not isinstance(paper.get("title", ""), str):
        return False
    for b in bl:
        if not isinstance(b, dict) or not isinstance(b.get("kind"), str):
            return False
        if b.get("kind") == "reel" and not (isinstance(b.get("clips"), list) and all(isinstance(c, dict) for c in b["clips"])):
            return False
        if b.get("kind") == "note" and not isinstance(b.get("text"), str):
            return False
    return True


def card_of(paper: dict, pid: str, created, meetings_by_pid: Dict[str, dict], issues_by_slug: Dict[str, dict],
            stills, base: str, today: _dt.date) -> Optional[dict]:
    """One reader's page as a card, or None when the bytes are not a page."""
    if not is_page(paper):
        return None
    blocks = _blocks(paper)
    title = paper.get("title")
    title = (title.strip() if isinstance(title, str) else "") or "Untitled front page"
    pids, slugs = pids_of(blocks), slugs_of(blocks)
    # the record speaks of what it holds: a meeting this pressing lacks is
    # not counted among a page's makings (its page says "not in this pressing")
    held = [p for p in pids if p in meetings_by_pid]
    held_slugs = [s for s in slugs if s in issues_by_slug]
    towns: List[str] = []
    for p in held:
        t = str((meetings_by_pid.get(p) or {}).get("town") or "")
        if t and t not in towns:
            towns.append(t)
    for s in slugs:
        t = str((issues_by_slug.get(s) or {}).get("town") or "") or _town_of_slug(s)
        if t and t not in towns:
            towns.append(t)
    still = ""
    for p in held:
        src = still_src(stills, p, 0, base)
        if src:
            still = src
            break
    made = [n_of(len(held), "meeting")] if held else []
    if held_slugs:
        made.append(n_of(len(held_slugs), "issue"))
    d = _day(created)
    return {"id": pid, "href": f"{base}/p?p={pid}", "title": title[:200], "kind": kind_of(blocks),
            "made": " · ".join(made), "what": what_of(blocks), "when": when_words(created, today),
            "towns": towns, "town": towns[0] if len(towns) == 1 else "", "still": still, "by": "readers",
            "day": d.isoformat() if d else "",
            "week": bool(d and 0 <= (today - d).days < WEEK_DAYS),
            # a day old at least: the strip seats a page only after a night's
            # press has already listed it in the gallery
            "seasoned": bool(d and (today - d).days >= 1)}


def readers_cards(shared: Optional[Sequence[dict]], meetings: Sequence[dict], issues: Sequence[dict], stills,
                  base: str = "/app", today: Optional[_dt.date] = None) -> List[dict]:
    """The store's pages as cards, newest first — each parsed from its own
    canonical bytes; bytes that are not a page, whatever their shape, make
    no card. Pages minted before LISTED_SINCE are not listed; at most
    PER_DAY from any one day are."""
    today = today or _dt.date.today()
    by_pid = {str(m.get("pid")): m for m in meetings if isinstance(m, dict)}
    by_slug = {str(i.get("slug")): i for i in issues if isinstance(i, dict)}
    rows = []
    for row in (shared or []):
        if not isinstance(row, dict):
            continue
        pid = str(row.get("id") or "")
        if not _ID.fullmatch(pid):
            continue
        d = _day(row.get("created"))
        if d is None or d < LISTED_SINCE:
            continue
        data = row.get("data")
        try:
            doc = json.loads(data.decode("utf-8") if isinstance(data, (bytes, bytearray)) else str(data or ""))
            card = card_of(doc, pid, row.get("created"), by_pid, by_slug, stills, base, today)
        except Exception:   # not a page, whatever its shape — no card, never a failed press
            continue
        if card:
            rows.append((str(row.get("created") or ""), card))
    rows.sort(key=lambda x: x[0], reverse=True)
    out, per_day = [], {}
    for _, c in rows:
        if per_day.get(c["day"], 0) >= PER_DAY:
            continue
        per_day[c["day"]] = per_day.get(c["day"], 0) + 1
        out.append(c)
        if len(out) >= MAX_LISTED:
            break
    return out


def strip_cards(readers: Sequence[dict]) -> List[dict]:
    """The readers' page(s) the front page's strip seats: the newest that is
    at least a day old."""
    return [c for c in (readers or []) if c.get("seasoned")][:STRIP_READERS]


def own_cards(featured: Sequence[dict], meetings: Sequence[dict], stills, base: str = "/app") -> List[dict]:
    """The record's own front pages (web/emit.py featured_papers) as cards."""
    by_pid = {str(m.get("pid")): m for m in meetings}
    out = []
    for f in (featured or []):
        pid = str(f.get("pid") or "")
        m = by_pid.get(pid)
        town = str(f.get("town") or (m.get("town") if m else "") or "")
        blocks = f.get("blocks") or []
        pids = pids_of(blocks)
        out.append({"id": "", "href": f"{base}/p?{f['qs']}", "title": str(f.get("title") or ""), "kind": kind_of(blocks),
                    "made": n_of(len(pids), "meeting") if pids else "",
                    "what": str(f.get("sub") or ""), "when": "", "towns": [town] if town else [], "town": town,
                    "still": still_src(stills, pid, 0, base) if pid else "", "by": "own", "day": "",
                    "week": True, "seasoned": True})
    return out


def card_html(c: dict) -> str:
    """One card, on the strip or the gallery: the still, who made it, the
    title, what it is made of, and when — never who."""
    own = c.get("by") == "own"
    pic = (f'<img src="{esc(c["still"])}" alt="" loading="lazy" width="480" height="270">' if c.get("still")
           else f'<span class="bs-nostill" style="background:{charts.town_light(c["town"]) if c.get("town") else charts.RULE}"></span>')
    kick = "The record’s front page" if own else "A reader’s front page"
    sub = c["what"] if own else " · ".join(x for x in (("made from " + c["made"]) if c["made"] else "", c["what"]) if x)
    foot = ("pressed nightly" if own
            else " · ".join(x for x in ("shared as a link", ("shared " + c["when"]) if c.get("when") else "", "no name, by design") if x)
            .replace("shared as a link · shared ", "shared as a link, "))
    towns = " ".join(town_slug(t) for t in (c.get("towns") or []))
    return (f'<a class="bs-fpcard" href="{esc(c["href"])}" style="--town:{charts.town_color(c["town"]) if c.get("town") else charts.INK}" '
            f'data-by="{"own" if own else "readers"}" data-kind="{esc(kind_slug(c["kind"]))}" '
            f'data-town="{esc(town_slug(c["town"])) if c.get("town") else ""}" data-towns="{esc(towns)}" '
            f'data-week="{1 if c.get("week") else 0}">{pic}'
            # the title first in the DOM (a link's name leads with it; four hundred
            # names that all begin "A reader's front page" would not) — the sheet
            # paints the kicker above it
            f'<span class="bs-fpbody"><b>{esc(c["title"])}</b><span class="bs-fpkick">{kick}</span>'
            f'<span class="bs-fpsub">{esc(sub)}</span><span class="bs-fpfoot">{esc(foot)}</span></span></a>')


def door_html(base: str = "/app") -> str:
    return (f'<a class="bs-fpdoor" href="{base}/p#edit"><span class="bs-fpkick">Yours</span><b>Write your own front page</b>'
            f'<span>Eight templates. The record draws the charts and the reel and offers its labeled reading; you write what it means. '
            f'No account — your page lives in the link.</span><span class="bs-fpgo">Start from a template →</span></a>')


def page_body(own: Sequence[dict], readers: Sequence[dict], towns: Sequence[dict], base: str = "/app") -> str:
    """Board 9: the head, the filters (anchors — the reader's script narrows
    the grid, the pressed page shows every card), the grid, the foot."""
    town_names = [str(t.get("town") or "") for t in (towns or []) if isinstance(t, dict) and t.get("town")]

    def filt(href, f, label, cur=False):
        current = ' aria-current="true"' if cur else ""   # built first: an f-string expression holds no backslash on 3.11
        return f'<a class="bs-filter" href="{href}" data-filter="{esc(f)}"{current}>{esc(label)}</a>'

    filters = [filt("#everything", "all", "Everything", True), filt("#own", "by:own", "The record’s own"),
               filt("#readers", "by:readers", "Readers’")]
    for t in town_names:
        filters.append(filt(f"#{town_slug(t)}", "town:" + town_slug(t), t))
    filters += [filt("#this-week", "week", "This week"), filt("#issues", "kind:an-issue-over-time", "Issues over time"),
                filt("#meetings", "kind:one-meeting", "One meeting")]
    # the count says what is listed — and when the list is capped, that it is
    readers_words = (f"readers’ {len(readers)}, the newest" if len(readers) >= MAX_LISTED
                     else f"readers’ {len(readers)}")
    count = f'{n_of(len(own) + len(readers), "front page")} · the record’s own {len(own)} · {readers_words}'
    cards = "".join(card_html(c) for c in own) + door_html(base) + "".join(card_html(c) for c in readers)
    return f'''<section class="bs-gallery" id="frontpages">
  <div class="bs-gallery-head">
    <h1>Front pages</h1>
    <p class="bs-gallery-lede">The record presses its own every night. Readers press theirs whenever they like and share them as links. Nobody signs — the record keeps no names — so a front page is judged by its receipts: every chart, reel and bracket points back into the tape.</p>
    <nav class="bs-filters" aria-label="which front pages" hidden>{"".join(filters)}<span class="bs-filter-note">newest first</span></nav>
  </div>
  <p class="bs-gallery-count" id="bs-gallery-count" role="status" data-all="{esc(count)}">{esc(count)}</p>
  <div class="bs-fpgrid bs-gallery-grid" id="bs-gallery-grid">{cards}</div>
  <p class="bs-gallery-foot">readers’ pages appear here when their makers press <em>short link</em> — the share · a steward can take one down · the record’s bytes are never copied, only referenced · <a href="https://creativecommons.org/licenses/by-sa/4.0/" rel="license">CC BY-SA 4.0</a></p>
</section>'''
