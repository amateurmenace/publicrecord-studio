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
words, each in either number: a thing is not said beside itself, while a phrase that merely
shares a word with it, said elsewhere, stays; the record's tokeniser reads
a hyphenated word as two, as the search index does), civic stopwords out,
and transcript artifacts out (an issue was
never said alongside a cough). Ranked by count, then alphabet; only what
came up more than once; a phrase said in both numbers ("complete street",
"complete streets", "lane plan", "lanes plan") shows once, the way it was said most, with that form's
own count — the chip opens the record's search, which reads words exactly,
so a count summed over both would promise lines its search cannot open.
Pure over the corpus's meetings as the press reads
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
_TOKEN = re.compile(r"[A-Za-z0-9']+")   # the same boundaries, with the caption's own casing kept
# a caption line read for its casing: words, the marks that end a sentence,
# and the marks that end a clause (so a pair never spans one — _CLAUSE's set)
_SCAN = re.compile(r"[A-Za-z0-9']+|[.?!…]+|[,;:—–()\[\]\"]+|\s-+\s|-{2,}")
# a full stop after one of these ends no sentence ("Mr. Quillon" — the name
# after it is written with a capital mid-sentence, which is the evidence)
HONORIFIC = frozenset("mr mrs ms mx dr st jr sr prof rev hon gov sen rep lt sgt capt col gen mt ft ave vs no".split())
# capitalised by the calendar's rule, never a name: a deadline ("July 4th")
# is one of the most useful things said beside an issue
CALENDAR = frozenset("""january february march april may june july august september october november
    december jan feb mar apr jun jul aug sep sept oct nov dec monday tuesday wednesday thursday friday
    saturday sunday""".split())
# a pair that ends in one of these names a day on the calendar, never a person
# ("Memorial Day", "Heritage Month") — the named-pair rule lets it pass
CALENDAR_HEADS = frozenset("day days week month eve".split())


def _bigrams(seqs: Iterable[Sequence[str]]) -> set:
    """Every contiguous pair inside a set of token sequences."""
    return {f"{s[i]} {s[i + 1]}" for s in seqs for i in range(len(s) - 1)}


def names_of(meetings: Iterable[dict], roster: Iterable[str] = (), plane: Iterable[dict] = ()) -> dict:
    """What the phrases beside an issue may name (specs/17: officials-only
    aggregation — the record never counts a private citizen's name across
    its meetings).

    `common` — the record's ordinary words, learned from its own captions:
    a word written in lower case (or as an acronym — "CPA", "DPW" name
    bodies and programs, never a person) at least twice, anywhere in a
    line, and at least a quarter as often as it is capitalised mid-sentence
    (a capital that opens a sentence is the sentence's, not the word's; a
    full stop after "Mr." or "Dr." opens none), in the transcripts whose
    casing carries meaning (Boston's council captions are ALL CAPS and an
    unpunctuated auto-caption may be all lower case; neither says anything
    about names, so neither votes); plus every town the record holds and
    the calendar's words. A word that is not ordinary is part of a proper
    name — a person, a place, a body.
    `named` — the pairs the captions write Capital Capital mid-sentence at
    least twice and four times as often as in lower case: a name even when
    both of its words are everyday words.
    `carried` — the pairs inside a name the record already shows: the names
    plane (`plane`, web/bake.py names_plane — the same forty rows the "Who
    and where" block reads) and every name the roll calls read (officials,
    by construction).
    `unshown` — the pairs inside any person's name the analyzer found that
    the names plane does not show: a name made of ordinary words ("Bill
    Green") is still a person's name when the analyzer says so."""
    lower: Dict[str, int] = {}
    title: Dict[str, int] = {}
    tt: Dict[str, int] = {}      # a pair written Capital Capital mid-sentence
    ll: Dict[str, int] = {}      # …and in lower case
    towns: set = set()
    people: set = set()
    for m in meetings:
        if not isinstance(m, dict):
            continue
        towns.update(_WORD.findall(str(m.get("town") or "").lower()))
        an = m.get("analysis") if isinstance(m.get("analysis"), dict) else {}
        ents = an.get("entities") if isinstance(an.get("entities"), dict) else {}
        for e in (ents.get("people") or []):
            toks = tuple(_WORD.findall(str(e.get("name") or "").lower())) if isinstance(e, dict) else ()
            if toks:
                people.add(toks)
        # one meeting's casing, counted apart, and kept only if it carries meaning
        lo: Dict[str, int] = {}
        ti: Dict[str, int] = {}
        mtt: Dict[str, int] = {}
        mll: Dict[str, int] = {}
        n = n_lower = n_mid_title = 0
        towns_m = set(_WORD.findall(str(m.get("town") or "").lower())) | towns
        start = True                 # the meeting opens a sentence; a caption line may continue one
        for s in (m.get("segments") or []):
            text = str(s.get("text") or "") if isinstance(s, dict) else ""
            prev = None              # (word, lower-case?, title-case?, opened a sentence or a line?) — the pair's first half
            line_first = True        # a caption line's first word may be capitalised by the captioner, not by a name
            for mt in _SCAN.finditer(text):
                w = mt.group(0)
                if not (w[0].isalnum() or w[0] == "'"):
                    if w[0] in ".?!…" and not (w == "." and prev and prev[0].lower() in HONORIFIC):
                        start = True
                    prev = None      # a pair never spans a mark
                    continue
                n += 1
                is_lower = w.islower()
                is_lo = is_lower or (len(w) >= 2 and w.isupper())     # an acronym is ordinary evidence too
                is_ti = not is_lo and w[:1].isupper() and any(c.islower() for c in w[1:])
                lw = w.lower()
                initial = start or line_first
                n_lower += is_lower
                if is_lo:
                    lo[lw] = lo.get(lw, 0) + 1                        # lower case is evidence wherever it stands
                elif is_ti and not initial:
                    ti[lw] = ti.get(lw, 0) + 1                        # a capital counts only mid-sentence, mid-line
                    # …and says the casing means something only if no rule put it
                    # there: "I'm", a month, a town are capitalised by every
                    # captioner, even one who writes names in lower case (a skeptic's catch)
                    if not (lw.startswith("i'") or lw in CALENDAR or lw in towns_m):
                        n_mid_title += 1
                if prev is not None:
                    pair = f"{prev[0].lower()} {lw}"
                    if prev[1] and is_lower:
                        mll[pair] = mll.get(pair, 0) + 1
                    elif prev[2] and is_ti and not prev[3]:
                        mtt[pair] = mtt.get(pair, 0) + 1
                prev = (w, is_lower, is_ti, initial)
                start = line_first = False
        if n and n_lower >= 0.5 * n and n_mid_title >= 0.005 * n:
            for src, dst in ((lo, lower), (ti, title), (mtt, tt), (mll, ll)):
                for k, v in src.items():
                    dst[k] = dst.get(k, 0) + v
    common = {w for w, k in lower.items() if k >= 2 and 4 * k >= title.get(w, 0)} | towns | CALENDAR
    shown = [tuple(_WORD.findall(str(r.get("name") or "").lower())) for r in (plane or []) if isinstance(r, dict)]
    shown += [tuple(_WORD.findall(str(nm or "").lower())) for nm in (roster or [])]
    carried = _bigrams(shown)
    # a pair the captions write Capital Capital mid-sentence, twice at least
    # and four times as often as in lower case, is a name even when both its
    # words are everyday words ("Grace Park", "Mark Hall" — a reviewer's
    # catch); a pair they write in lower case twice is no one's name, whatever
    # the analyzer filed it under ("vision zero" as a person)
    named = {p for p, k in tt.items() if k >= 2 and k >= 4 * ll.get(p, 0) and p.split()[-1] not in CALENDAR_HEADS}
    # …written in lower case at least as often as in capitals, and twice: the
    # captions' own verdict outweighs the analyzer's filing (a skeptic's catch —
    # without the weighing, a person captioned three times as a name and twice
    # in lower case walked out of the backstop)
    vouched = {p for p, k in ll.items() if k >= 2 and k >= tt.get(p, 0)}
    return {"common": common, "carried": carried, "named": named - carried,
            "unshown": _bigrams(people) - carried - vouched}


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


_ES = ("s", "x", "z", "ch", "sh", "o")  # the endings English adds -es after (taxes, buses, heroes)


def _other(w: str) -> set:
    """A word's other forms, by the commonest English endings — street and
    streets, tax and taxes, sky and skies, policies and policy — and its
    possessive (society and society's, residents and residents'); -es only
    after a hiss or an o (taxes, heroes), so "rates" is never taken for
    "rat"'s plural, nor "cares" for "car"'s (re-review catches). Never an
    empty form: a stray "'s" is no word."""
    if w.endswith("'s") or w.endswith("s'"):
        base = w[:-2] if w.endswith("'s") else w[:-1]
        return {base} if len(base) > 1 else set()
    alt = {w + "s", w + "'s"}
    if w.endswith(_ES):
        alt.add(w + "es")
    if w.endswith("s"):
        alt.add(w + "'")
    if len(w) >= 3 and w.endswith("y") and w[-2] not in "aeiou":
        alt.add(w[:-1] + "ies")
    if len(w) > 4 and w.endswith("ies"):
        alt.add(w[:-3] + "y")
    if len(w) > 4 and w.endswith("es") and w[:-2].endswith(_ES):
        alt.add(w[:-2])
    if len(w) > 3 and w.endswith("s") and not w.endswith("ss"):
        alt.add(w[:-1])
    alt.discard(w)
    return alt


def _numbers(p: str) -> set:
    """A phrase's other numbers, one word changed at a time — "complete
    streets" for "complete street", "lanes plan" for "lane plan", and back —
    as candidates only: they are matched against the phrases actually
    counted (or the issue's own names), so no form is guessed onto a page."""
    ws = p.split()
    return {" ".join(ws[:i] + [a] + ws[i + 1:]) for i, w in enumerate(ws) for a in _other(w)}


def beside(timeline: Sequence[dict], meetings_by_id: Dict[str, dict], own,
           top: int = TOP, prepared: Optional[dict] = None, names: Optional[dict] = None) -> List[dict]:
    """[{phrase, n, meetings}] — the phrases said beside the issue, over every
    bead's line and its neighbours, each line counted once; `own` is
    own_words(issue) (a bare set of tokens is read as the name's tokens).
    `names` is names_of(the press's meetings, the roll calls' names, the
    names plane): with it, a pair holding a proper name counts only if the
    record already shows that name, and a person the names plane does not
    show never counts.
    `prepared`, when handed in, caches a meeting's sorted lines across the
    issues of one press."""
    if not isinstance(own, dict):
        own = {"phrases": set(), "tokens": set(own or ())}
    own_phrases, own_tokens = set(own.get("phrases") or ()), set(own.get("tokens") or ())
    # the issue's names in either number, or possessive: "Complete Streets"
    # is not said beside itself as "complete street", nor a society as the
    # "historical society's" (review catches — the page says its own names
    # are left out)
    own_phrases |= {v for q in own_phrases for v in _numbers(q)}
    own_tokens |= {v for w in own_tokens for v in _other(w)}
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
                    # officials-only aggregation (specs/17): a proper name the
                    # record does not already show is never counted beside an
                    # issue — nor is any person the names plane does not show
                    if names is not None and (p in names["unshown"] or p in names.get("named", ()) or (
                            any(w not in names["common"] for w in ws) and p not in names["carried"])):
                        continue
                    if any(_stopish(w) or w in ARTIFACTS for w in ws) or p in ARTIFACTS:
                        continue
                    counts[p] = counts.get(p, 0) + 1
                    where.setdefault(p, set()).add(pid)
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], kv[0]))
    out, kept = [], set()
    for p, n in ranked:
        if n < 2 or len(out) >= top:
            break
        if _numbers(p) & kept:          # its other number, said more (or first in the alphabet), stands for it
            continue
        kept.add(p)
        out.append({"phrase": p, "n": n, "meetings": len(where[p])})
    return out
