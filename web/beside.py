"""Said alongside it (specs/29 board 6): the phrases said in the same breath
as an issue, counted at press time.

The record files transcript lines under an issue (memory/issues.py assigns
them; the issue plane carries them as beads). Every such line and the line
either side of it is the issue's breath; the two-word phrases in those lines
whose every token carries signal (memory.issues.phrases: no filler, no
procedural grams) are counted — each line once, however many beads touch
it, and a line cut at its punctuation first, so a pair no one said across
a full stop is not a phrase — with the issue's own names kept out (any
pair that overlaps its name, its other names or its keywords where they
are said, and any pair that is one of them or is made only of the name's
words: a thing is not said beside itself, while a phrase that merely
shares a word with it, said elsewhere, stays; the record's tokeniser reads
a hyphenated word as two, as the search index does), civic stopwords out,
and transcript artifacts out (an issue was
never said alongside a cough). Ranked by count, then alphabet; only what
came up more than once. Pure over the corpus's meetings as the press reads
them, so two presses of one corpus say the same; nothing here calls a
model, and nothing here is stored — the press writes it onto the issue's
plane and the reader renders it (app.js bsBesideBlock).
"""

from __future__ import annotations

import bisect
import re
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

from highlighter.insight import _stopish
from memory.issues import FILLER, PROCEDURAL

from .charts import ARTIFACTS

TOP = 8                                 # the plane carries this many (board 6 shows seven)
_WORD = re.compile(r"[a-z0-9']+")       # memory.issues' own token rule
_CLAUSE = re.compile(r"[.,;:!?…—–()\[\]\"]+|\s-+\s|-{2,}")   # a phrase never crosses one of these (a hyphen inside a word is not one)


def own_words(issue: dict) -> dict:
    """What an issue calls itself: `phrases` — its name, its other names
    (aliases) and its keywords, each whole and lowercased — and `tokens`,
    the words of the name alone. A phrase beside the issue is left out when
    it IS one of those names, or is made only of the name's own words; a
    phrase that merely shares a word with the name stays (a review catch:
    a bag of every alias's tokens cut the strongest collocations, which are
    what the aliases are made of)."""
    norm = lambda s: " ".join(_WORD.findall(str(s or "").lower()))
    phrases = {norm(s) for s in [issue.get("name") or ""] + list(issue.get("aliases") or []) + list(issue.get("keywords") or [])}
    phrases.discard("")
    return {"phrases": phrases, "tokens": set(_WORD.findall(str(issue.get("name") or "").lower()))}


def _lines(m: dict) -> Tuple[List[str], List[float]]:
    """A meeting's spoken lines in tape order, and their starts — blank
    caption lines are no lines (the search index reads it the same way)."""
    segs = [s for s in (m.get("segments") or []) if isinstance(s, dict) and str(s.get("text") or "").strip()]
    segs.sort(key=lambda s: float(s.get("start") or 0))
    return [str(s.get("text") or "") for s in segs], [float(s.get("start") or 0) for s in segs]


def _at(starts: Sequence[float], t) -> Optional[int]:
    """The line that begins at t (a bead's own start), else the last line
    before it — the first line when t precedes them all; None for a t that
    is not a number (a bead without a time counts nothing, never the tape's
    opening lines — a review catch)."""
    if not starts or isinstance(t, bool) or not isinstance(t, (int, float)):
        return None
    i = bisect.bisect_right(starts, float(t)) - 1
    return max(0, i)


def _pairs(clause: str, own_phrases: set) -> List[str]:
    """The two-word phrases of one clause, memory.issues.phrases' own rules
    (no filler token, no token under three letters or all digits, no
    procedural gram) — minus every pair that overlaps an occurrence of one
    of the issue's own names where it is said ("fund voted" at the edge of
    "housing trust fund", "affordable housing" inside "affordable housing
    trust fund"): the issue is not said beside itself, and a pair that
    merely shares a word with the name, said elsewhere, stays."""
    ws = _WORD.findall(clause.lower())
    masked = set()
    for q in own_phrases:
        qs = q.split()
        k = len(qs)
        if not k:
            continue
        for i in range(len(ws) - k + 1):
            if ws[i:i + k] == qs:
                masked.update(range(i, i + k))
    out = []
    for i in range(len(ws) - 1):
        g = ws[i:i + 2]
        if i in masked or i + 1 in masked:
            continue
        if any(w in FILLER or len(w) < 3 or w.isdigit() for w in g):
            continue
        p = " ".join(g)
        if p not in PROCEDURAL:
            out.append(p)
    return out


def beside(timeline: Sequence[dict], meetings_by_id: Dict[str, dict], own,
           top: int = TOP, prepared: Optional[dict] = None) -> List[dict]:
    """[{phrase, n, meetings}] — the phrases said beside the issue, over every
    bead's line and its neighbours, each line counted once; `own` is
    own_words(issue) (a bare set of tokens is read as the name's tokens).
    `prepared`, when handed in, caches a meeting's sorted lines across the
    issues of one press."""
    if not isinstance(own, dict):
        own = {"phrases": set(), "tokens": set(own or ())}
    own_phrases, own_tokens = set(own.get("phrases") or ()), set(own.get("tokens") or ())
    cache = prepared if prepared is not None else {}
    counts: Dict[str, int] = {}
    where: Dict[str, set] = {}
    for node in timeline:
        if not isinstance(node, dict):
            continue
        mid = node.get("meeting_id")
        if mid not in cache:
            cache[mid] = _lines(meetings_by_id.get(mid) or {})
        lines, starts = cache[mid]
        if not lines:
            continue
        pid = str(node.get("pid") or mid or "")
        covered = set()
        for b in (node.get("beads") or []):
            i = _at(starts, b.get("t")) if isinstance(b, dict) else None
            if i is None:
                continue
            covered.update(j for j in (i - 1, i, i + 1) if 0 <= j < len(lines))
        for j in sorted(covered):
            for clause in _CLAUSE.split(lines[j]):            # a phrase never crosses a full stop
                for p in _pairs(clause, own_phrases):           # …nor overlaps the issue's own name where it is said
                    ws = p.split()
                    # the issue's own name said apart from itself: a pair that is one of
                    # its names, or made only of the name's words ("trust fund" alone)
                    if p in own_phrases or all(w in own_tokens for w in ws):
                        continue
                    if any(_stopish(w) or w in ARTIFACTS for w in ws) or p in ARTIFACTS:
                        continue
                    counts[p] = counts.get(p, 0) + 1
                    where.setdefault(p, set()).add(pid)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    return [{"phrase": p, "n": n, "meetings": len(where[p])} for p, n in ranked[:top] if n > 1]
