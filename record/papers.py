"""The shared-paper store — content-addressed, write-once, read-only.

specs/21 §6.2, the one server touch a curated paper can have. A paper is PUT
by the hash of its own canonical bytes, so the URL *is* the content: the same
paper always lands at the same address, a re-share is a no-op, and nothing at
this layer knows or asks who wrote or reads one. The store is **additive,
never load-bearing** — every paper also travels as a URL-encoded link and an
exportable ``paper.json``, so losing this bucket loses the shortness of the
short links and nothing else (specs/17 §6.2 holds whole).

The abuse posture, P1 (settled with Stephen 2026-07-21) and extended for P2
(notes, settled 2026-07-22): the free text a stored paper may carry is its
**title** and its **notes** — each length-capped, plain text, control-char
policed (a note may hold newlines; a title may not); every other field is an
exact-shaped reference into the record (a pid, a slug, a clip's two
timestamps, a chart kind from a closed list). Validation is **strict, not
corrective** — an
unknown key or a malformed block is a 422, never silently rewritten, because
a store that "helpfully" edits documents stores things nobody ever saw. (The
reader's own decoder is the opposite — total, malformed-degrades — and that
is the right split: a *link* must survive a mangling email client; a *store*
must refuse to hold what the client never meant.)

Canonical form is decided HERE and only here: keys sorted, separators tight,
ASCII-escaped, clip times snapped to the tenth-second grid with whole seconds
collapsed to ints (``12``, ``12.0`` and ``12.00`` are one clip, one hash).
The client never computes the hash — it POSTs the portable form and receives
the address back — so there is no cross-language byte contract to drift.

Takedown: there is no delete API on purpose. A steward removes the object
``p/<id>.json`` from the bucket by hand (``record/OPERATING.md`` §papers),
and the address goes honestly 404.
"""

from __future__ import annotations

import hashlib
import datetime as _dt
import json
import math
import re

SCHEMA = "publicrecord.paper/1"
MAX_BYTES = 64 * 1024        # the raw POST and the canonical form both
MAX_BLOCKS = 64
MAX_CLIPS = 100              # per reel block — matches the reader's cap
TITLE_MAX = 200
# The P2 posture, settled with Stephen 2026-07-22: a note is the second and
# last free text a stored paper may carry — plain text, capped, newlines
# allowed (a note has paragraphs; a title does not), every other control
# character refused. No markdown, no HTML: the reader esc()s it at render,
# so what is stored is what is shown, verbatim and inert.
NOTE_MAX = 2000
# The chart kinds a paper may carry (specs/21 P2). A chart block is refs and
# an enum, never data or free text — the reader computes the picture from the
# record's own pressed planes, so a stored paper cannot assert a number the
# record would not draw.
CHARTS = ("votes", "reach", "framing", "topics",
          # specs/24 — the two paths' pictures, refs and enums like the rest:
          # the numbers (a meeting's or an issue's), the shape of a meeting
          # (its moments on its own time axis), an issue's ledger (every roll
          # call along its way)
          "numbers", "shape", "ledger")
# The layouts a block may ask for (specs/23 C1): an enum, never data. A
# block with no layout reads as it always did; any other value is refused —
# the store holds no layout the reader would have to guess at.
LAYOUTS = ("lead", "head", "half")
# The broadsheet's blocks (specs/29 P1) — every one an enum or a ref, like
# the kinds before them; the reader computes each from the record's own
# planes at render and stores nothing it could not redraw:
#   lead    — one meeting told large (its still, its counted lede, the
#             moments that decided it): {"kind": "lead", "pid": …}
#   week    — the record's latest week of meetings as cards
#   threads — the widest threads as small multiples
#   strip   — how they talked: one lens bar per meeting, in date order
#   names   — who and where: the names and places the record keeps hearing,
#             or ONE of them ("who": a name's slug from analytics.json)
#   search  — a search box readers use over the page's own meetings
# week, threads, strip and names may name a municipality ("town": the slug
# the press mints from towns.json — boston, brookline); names may name a
# town OR a who, never both. A town or a who the pressing does not hold is
# said so by the reader ("not in this pressing"), never stored as a word
# the record would not draw — the refs are exact-shaped (_REF) and opaque
# here, as a pid or an issue slug is.
BS_KINDS = ("lead", "week", "threads", "strip", "names", "search")
BS_SCOPED = ("week", "threads", "strip", "names")
# The C2 kinds (specs/23 C2) — refs only, every one. A pull-quote is a
# transcript line named by (pid, t): the words are fetched from the pressed
# tape at render, never stored. A document is a meeting's own filing named
# by its id. A digest is an issue and a window (how many of its latest
# appearances to show), computed at render from the issue's own timeline.
DIGEST_MAX = 12
_DOC_REF = re.compile(r"[A-Za-z0-9_:.-]{1,160}")   # a document id ("doc:budget")

# A pid or an issue slug. The bake mints pids to 80 chars and issue slugs to
# 96 (web/bake.py pid()/islug()); 128 leaves headroom and matches the reader's
# PAPER_REF exactly. fullmatch, not match-with-$: "$" would admit a trailing
# newline, and a strict store must not hold refs the renderer then drops.
_REF = re.compile(r"[A-Za-z0-9_-]{1,128}")
# a municipality's slug and a name's (specs/29 P1): exactly what the press
# mints (web/bake.py nslug — lower-case ascii runs joined by "-", capped at
# 96; who_slug — the kind's letter, a dash, the same), so the store never
# holds a scope the reader could not have minted
_TOWN_REF = re.compile(r"[a-z0-9-]{1,96}")
_WHO_REF = re.compile(r"[plo]-[a-z0-9-]{1,96}")
ID_RX = re.compile(r"[0-9a-f]{16}")             # a paper's content address
LIST_MAX = 400                                  # the newest pages a press lists (web/gallery.py MAX_LISTED)


class PaperError(ValueError):
    """A document the store refuses — the message is the 422 body."""


class PaperTaken(PaperError):
    """A page a steward took down (record/OPERATING.md §5, `taken/`): the
    store will not hold the same bytes again, and says so instead of
    answering a link that only says so when followed."""


def _t(x, what):
    """A clip time: a real JSON number, finite, >= 0, snapped to the
    tenth-second grid, whole seconds collapsed to int so 12 and 12.0 hash
    identically whichever a client sent."""
    if isinstance(x, bool) or not isinstance(x, (int, float)):
        raise PaperError(f"{what} must be a number")
    try:
        v = round(float(x), 1)
    except OverflowError:   # an int too large for a float is not a clip time
        raise PaperError(f"{what} must be a finite time from the tape's start")
    if not math.isfinite(v) or v < 0:
        raise PaperError(f"{what} must be a finite time from the tape's start")
    return int(v) if float(v).is_integer() else v


def _exact_keys(obj, want, what):
    # `layout` is the one optional key any block may add (C1) — checked by
    # _layout; every other key is exact
    got = set(obj) - {"layout"}
    if got != want:
        raise PaperError(
            f"{what} must carry exactly {sorted(want)} (got {sorted(got)})")


def _layout(b, what):
    """The block's layout, when it asks for one — strictly one of LAYOUTS."""
    if "layout" not in b:
        return None
    lay = b.get("layout")
    if lay not in LAYOUTS:
        raise PaperError(
            f"{what}: unknown layout {lay!r} — a block may be "
            f"{', '.join(LAYOUTS)}, or carry no layout at all")
    return lay


def _pid(b, what):
    pid = b.get("pid")
    if not isinstance(pid, str) or not _REF.fullmatch(pid):
        raise PaperError(f"{what}: not a meeting id")
    return pid


def _slug(b, what):
    slug = b.get("slug")
    if not isinstance(slug, str) or not _REF.fullmatch(slug):
        raise PaperError(f"{what}: not an issue slug")
    return slug


def _one_ref(b, what, fixed):
    """Exactly one of `pid` / `slug`, beside the fixed keys — a block that
    names both, or neither, is refused rather than guessed at."""
    has_pid, has_slug = "pid" in b, "slug" in b
    if has_pid == has_slug:
        raise PaperError(f"{what}: name a meeting (pid) or an issue (slug), "
                         "exactly one")
    if has_pid:
        _exact_keys(b, fixed | {"pid"}, what)
        return {"pid": _pid(b, what)}
    _exact_keys(b, fixed | {"slug"}, what)
    return {"slug": _slug(b, what)}


def _block(b, i):
    out = _block_kind(b, i)
    lay = _layout(b, f"block {i + 1}")
    if lay:
        out["layout"] = lay
    return out


def _block_kind(b, i):
    what = f"block {i + 1}"
    if not isinstance(b, dict):
        raise PaperError(f"{what} is not an object")
    kind = b.get("kind")
    if kind == "story":
        story = b.get("story")
        if story == "meeting":
            _exact_keys(b, {"kind", "story", "pid"}, what)
            pid = b.get("pid")
            if not isinstance(pid, str) or not _REF.fullmatch(pid):
                raise PaperError(f"{what}: not a meeting id")
            return {"kind": "story", "story": "meeting", "pid": pid}
        if story == "issue":
            _exact_keys(b, {"kind", "story", "slug"}, what)
            slug = b.get("slug")
            if not isinstance(slug, str) or not _REF.fullmatch(slug):
                raise PaperError(f"{what}: not an issue slug")
            return {"kind": "story", "story": "issue", "slug": slug}
        raise PaperError(f"{what}: a story is a meeting or an issue")
    if kind == "reel":
        _exact_keys(b, {"kind", "clips"}, what)
        clips = b.get("clips")
        if not isinstance(clips, list) or not clips:
            raise PaperError(f"{what}: a reel carries a list of clips")
        if len(clips) > MAX_CLIPS:
            raise PaperError(f"{what}: more than {MAX_CLIPS} clips")
        out = []
        for j, c in enumerate(clips):
            cw = f"{what}, clip {j + 1}"
            if not isinstance(c, dict):
                raise PaperError(f"{cw} is not an object")
            if set(c) != {"pid", "start", "end"}:
                raise PaperError(
                    f"{cw} must carry exactly ['end', 'pid', 'start'] "
                    f"(got {sorted(c)})")
            pid = c.get("pid")
            if not isinstance(pid, str) or not _REF.fullmatch(pid):
                raise PaperError(f"{cw}: not a meeting id")
            start, end = _t(c.get("start"), f"{cw} start"), _t(c.get("end"), f"{cw} end")
            if end <= start:
                raise PaperError(f"{cw}: ends before it starts")
            out.append({"pid": pid, "start": start, "end": end})
        return {"kind": "reel", "clips": out}
    if kind == "note":
        _exact_keys(b, {"kind", "text"}, what)
        text = b.get("text")
        if not isinstance(text, str):
            raise PaperError(f"{what}: a note's text must be a string")
        # the cap counts UTF-16 units — the READER's unit — or a stored
        # astral-heavy note would be legal here and silently truncated at
        # every render (the client caps at 2,000 units; a review catch)
        units = sum(2 if ord(ch) > 0xFFFF else 1 for ch in text)
        if units > NOTE_MAX:
            raise PaperError(
                f"{what}: the note is longer than {NOTE_MAX} characters — "
                "share the fuller version as a paper.json file")
        if any((ord(ch) < 0x20 and ch != "\n") or ord(ch) == 0x7F
               for ch in text):
            raise PaperError(f"{what}: the note carries control characters "
                             "(only newlines may break it)")
        if not text.strip():
            raise PaperError(f"{what}: an empty note has nothing to store")
        return {"kind": "note", "text": text}
    if kind == "chart":
        chart = b.get("chart")
        if chart not in CHARTS:
            raise PaperError(
                f"{what}: unknown chart {chart!r} — this record draws "
                f"{', '.join(CHARTS)}")
        if chart == "reach":
            _exact_keys(b, {"kind", "chart", "slug"}, what)
            slug = b.get("slug")
            if not isinstance(slug, str) or not _REF.fullmatch(slug):
                raise PaperError(f"{what}: not an issue slug")
            return {"kind": "chart", "chart": "reach", "slug": slug}
        if chart == "framing" and "pid" in b:
            _exact_keys(b, {"kind", "chart", "pid"}, what)
            pid = b.get("pid")
            if not isinstance(pid, str) or not _REF.fullmatch(pid):
                raise PaperError(f"{what}: not a meeting id")
            return {"kind": "chart", "chart": "framing", "pid": pid}
        # specs/24: a meeting's own roll calls (votes with a pid), the shape
        # of a meeting (pid only), an issue's ledger (slug only), and the
        # numbers of exactly one of the two
        if chart == "votes" and "pid" in b:
            _exact_keys(b, {"kind", "chart", "pid"}, what)
            return {"kind": "chart", "chart": "votes", "pid": _pid(b, what)}
        if chart == "shape":
            _exact_keys(b, {"kind", "chart", "pid"}, what)
            return {"kind": "chart", "chart": "shape", "pid": _pid(b, what)}
        if chart == "ledger":
            _exact_keys(b, {"kind", "chart", "slug"}, what)
            return {"kind": "chart", "chart": "ledger", "slug": _slug(b, what)}
        if chart == "numbers":
            return {"kind": "chart", "chart": "numbers", **_one_ref(b, what, {"kind", "chart"})}
        _exact_keys(b, {"kind", "chart"}, what)
        return {"kind": "chart", "chart": chart}
    if kind == "reading":
        # specs/24: the record's reading of a meeting or an issue — decisions,
        # questions, names, milestones — computed at render from the pressed
        # plane; a ref and nothing else
        return {"kind": "reading", **_one_ref(b, what, {"kind"})}
    if kind == "quote":
        _exact_keys(b, {"kind", "pid", "t"}, what)
        pid = b.get("pid")
        if not isinstance(pid, str) or not _REF.fullmatch(pid):
            raise PaperError(f"{what}: not a meeting id")
        return {"kind": "quote", "pid": pid, "t": _t(b.get("t"), f"{what} t")}
    if kind == "doc":
        _exact_keys(b, {"kind", "pid", "doc"}, what)
        pid, doc = b.get("pid"), b.get("doc")
        if not isinstance(pid, str) or not _REF.fullmatch(pid):
            raise PaperError(f"{what}: not a meeting id")
        if not isinstance(doc, str) or not _DOC_REF.fullmatch(doc):
            raise PaperError(f"{what}: not a document id")
        return {"kind": "doc", "pid": pid, "doc": doc}
    if kind == "digest":
        _exact_keys(b, {"kind", "slug", "n"}, what)
        slug, n = b.get("slug"), b.get("n")
        if not isinstance(slug, str) or not _REF.fullmatch(slug):
            raise PaperError(f"{what}: not an issue slug")
        if isinstance(n, bool) or not isinstance(n, int) or not 1 <= n <= DIGEST_MAX:
            raise PaperError(f"{what}: a digest's window is 1 to {DIGEST_MAX} appearances")
        return {"kind": "digest", "slug": slug, "n": n}
    if kind == "lead":
        _exact_keys(b, {"kind", "pid"}, what)
        return {"kind": "lead", "pid": _pid(b, what)}
    if kind == "search":
        _exact_keys(b, {"kind"}, what)
        return {"kind": "search"}
    if kind in BS_SCOPED:
        # a municipality, when the block names one — and for names, a who;
        # a block that names both is refused rather than guessed at
        extra = set(b) - {"layout", "kind"}
        allowed = {"town", "who"} if kind == "names" else {"town"}
        if not extra <= allowed:
            raise PaperError(f"{what}: a {kind} block may carry only "
                             f"{', '.join(sorted(allowed))} beside its kind "
                             f"(got {sorted(extra)})")
        if len(extra) > 1:
            raise PaperError(f"{what}: a names block names a town or a who, not both")
        out = {"kind": kind}
        for key in extra:
            ref = b.get(key)
            rx = _TOWN_REF if key == "town" else _WHO_REF
            if not isinstance(ref, str) or not rx.fullmatch(ref):
                raise PaperError(f"{what}: not a {'municipality' if key == 'town' else 'name'} slug")
            out[key] = ref
        return out
    raise PaperError(f"{what}: unknown kind {kind!r} — this store holds "
                     "stories, reels, charts, notes, quotes, documents, digests, "
                     "the record's reading, and the broadsheet's blocks "
                     f"({', '.join(BS_KINDS)})")


def canonical(doc) -> str:
    """Validate a portable paper strictly and return its one canonical
    serialization — the bytes that get hashed and stored. Raises PaperError
    with a sayable message on anything malformed."""
    if not isinstance(doc, dict):
        raise PaperError("a paper is a JSON object")
    extra = set(doc) - {"schema", "title", "blocks"}
    if extra:
        raise PaperError(
            f"unknown keys {sorted(extra)} — send the portable form "
            "(schema, title, blocks of refs); the enriched paper.json is "
            "a receipt, not an upload")
    if doc.get("schema") != SCHEMA:
        raise PaperError(f"schema must be {SCHEMA!r}")
    title = doc.get("title", "")
    if not isinstance(title, str):
        raise PaperError("the title must be a string")
    if len(title) > TITLE_MAX:
        raise PaperError(f"the title is longer than {TITLE_MAX} characters")
    if any(ord(ch) < 0x20 for ch in title):
        raise PaperError("the title carries control characters")
    blocks = doc.get("blocks", [])
    if not isinstance(blocks, list):
        raise PaperError("blocks must be a list")
    if len(blocks) > MAX_BLOCKS:
        raise PaperError(f"more than {MAX_BLOCKS} blocks")
    if not blocks and not title:
        raise PaperError("an empty paper has nothing to store — the link "
                         "already carries it")
    clean = {"schema": SCHEMA, "title": title,
             "blocks": [_block(b, i) for i, b in enumerate(blocks)]}
    out = json.dumps(clean, sort_keys=True, separators=(",", ":"))
    if len(out) > MAX_BYTES:
        raise PaperError("this paper is too large to store — share it as a "
                         "paper.json file instead")
    return out


def paper_id(canonical_form: str) -> str:
    """The content address: sixteen hex characters of the canonical bytes'
    SHA-256. Idempotent by construction — the same paper cannot have two."""
    return hashlib.sha256(canonical_form.encode("utf-8")).hexdigest()[:16]


# -- backends ---------------------------------------------------------------
# One method pair, two homes. `put_new` must be create-only (an existing
# object is left byte-identical — content addressing makes overwrite and
# no-op indistinguishable anyway); `get` returns bytes or None.

class MemPapers:
    """The store in a dict — tests, and any run without a bucket."""

    def __init__(self):
        self._d = {}
        self._when = {}
        self.taken = set()   # ids a steward took down — the bucket's taken/ prefix
        # creation times the tests can reason about — newest last, a second
        # apart, on the clock's own day (the press lists nothing minted
        # before its threshold, so a store of yesteryear would list nothing)
        self._t0 = _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)

    def put_new(self, pid: str, data: bytes) -> None:
        if pid in self.taken:
            raise PaperTaken(pid)   # taken down stays down: the same bytes do not come back
        if pid not in self._d:
            self._d[pid] = data
            self._when[pid] = (self._t0 + _dt.timedelta(seconds=len(self._when))).isoformat()

    def get(self, pid: str):
        return self._d.get(pid)

    def list_all(self, limit: int = LIST_MAX):
        """The store's pages, newest first, for the press's front pages
        (specs/29 P2) — the test seam's twin of GcsPapers.list_all: id,
        bytes, created."""
        rows = [{"id": k, "data": v, "created": self._when.get(k)} for k, v in self._d.items()]
        rows.reverse()
        return rows[:limit]


class GcsPapers:
    """The store in a private GCS bucket, `p/<id>.json` per paper.
    `if_generation_match=0` makes the write create-only at the bucket, so
    even a raced double-POST stores one object once. The client library is
    imported lazily — importing this module must never need credentials."""

    def __init__(self, bucket_name: str):
        self._name = bucket_name
        self._bucket = None

    def _b(self):
        if self._bucket is None:
            from google.cloud import storage
            self._bucket = storage.Client().bucket(self._name)
        return self._bucket

    def put_new(self, pid: str, data: bytes) -> None:
        from google.api_core.exceptions import PreconditionFailed
        # a page a steward took down (moved to taken/) stays down: the same
        # bytes POSTed again write nothing, and the share is refused outright
        # rather than answered with a link that 404s (a review catch: one
        # move must be one; a skeptic's: a refusal must be said at the door)
        if self._b().blob(f"taken/{pid}.json").exists():
            raise PaperTaken(pid)
        blob = self._b().blob(f"p/{pid}.json")
        try:
            blob.upload_from_string(data, content_type="application/json",
                                    if_generation_match=0)
        except PreconditionFailed:
            pass    # the same bytes are already there — that is the point

    def get(self, pid: str):
        from google.api_core.exceptions import NotFound
        blob = self._b().blob(f"p/{pid}.json")
        try:
            return blob.download_as_bytes()
        except NotFound:
            return None

    def list_all(self, limit: int = LIST_MAX):
        """The store's pages, newest first, capped — what the press lists as
        readers' front pages (specs/29 P2). Under `p/` only: a page a
        steward moved out of that prefix (record/OPERATING.md §5, the
        takedown act) is not listed, and its short link says the store
        holds nothing there. Best effort per object — one unreadable blob is
        one missing card, never a failed press."""
        client = self._b().client
        blobs = [b for b in client.list_blobs(self._name, prefix="p/")
                 if b.name.endswith(".json") and ID_RX.fullmatch(b.name[len("p/"):-len(".json")])]
        floor = _dt.datetime.min.replace(tzinfo=_dt.timezone.utc)
        blobs.sort(key=lambda b: b.time_created or floor, reverse=True)
        out = []
        for b in blobs[:limit]:
            pid = b.name[len("p/"):-len(".json")]
            try:
                data = b.download_as_bytes()
            except Exception:
                continue
            out.append({"id": pid, "data": data,
                        "created": b.time_created.isoformat() if b.time_created else None})
        return out
