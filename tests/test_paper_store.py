"""The shared-paper store (specs/21 §6.2) — canonical bytes, strict refusal,
idempotent addresses, honest failure.

The store's whole contract lives in `record/papers.py`: one canonical
serialization decided server-side (so there is no cross-language byte contract
for the reader to drift against), a hash that IS the address, and validation
that refuses rather than rewrites — the only free text a stored paper may
carry is its title. The endpoints are thin; these tests hold the contract.

None of this needs a database (`create_app(corpus=object())` proves the
routes never touch the corpus) or a bucket (`MemPapers` is the same two
methods the GCS backend keeps).
"""

import json
import unittest
from pathlib import Path

from record import papers
from record.papers import (NOTE_MAX, SCHEMA, TITLE_MAX, MemPapers, PaperError,
                           canonical, paper_id)

REPO = Path(__file__).resolve().parents[1]


def portable(title="Overrides, watched", blocks=None):
    """A well-formed portable paper — the exact shape the reader POSTs."""
    return {"schema": SCHEMA, "title": title,
            "blocks": blocks if blocks is not None else [
                {"kind": "story", "story": "meeting", "pid": "2YhgO14jXys"},
                {"kind": "story", "story": "issue", "slug": "the-override"},
                {"kind": "reel", "clips": [
                    {"pid": "2YhgO14jXys", "start": 900.2, "end": 907.3},
                    {"pid": "abc_def-123", "start": 12, "end": 24.0},
                ]},
            ]}




class TestC2Kinds(unittest.TestCase):
    """specs/23 C2: three more kinds, refs only — a pull-quote is (pid, t)
    and never its words; a document is (pid, doc id); a digest is an issue
    and a window. Exact keys, strict values, no free text anywhere."""

    def _doc(self, block):
        return {"schema": papers.SCHEMA, "title": "", "blocks": [block]}

    def test_the_three_kinds_are_accepted_as_refs(self):
        for block, want in (
            ({"kind": "quote", "pid": "vid1", "t": 12.04}, '"kind":"quote","pid":"vid1","t":12'),
            ({"kind": "doc", "pid": "vid1", "doc": "doc:budget"}, '"doc":"doc:budget","kind":"doc","pid":"vid1"'),
            ({"kind": "digest", "slug": "s", "n": 3}, '"kind":"digest","n":3,"slug":"s"')):
            self.assertIn(want, papers.canonical(self._doc(block)))

    def test_a_quote_never_carries_its_words(self):
        with self.assertRaises(papers.PaperError):
            papers.canonical(self._doc({"kind": "quote", "pid": "v", "t": 1, "text": "words"}))
        with self.assertRaises(papers.PaperError):
            papers.canonical(self._doc({"kind": "quote", "pid": "v", "t": -1}))
        with self.assertRaises(papers.PaperError):
            papers.canonical(self._doc({"kind": "quote", "pid": "v"}))

    def test_a_document_and_a_digest_are_strict(self):
        for bad in ({"kind": "doc", "pid": "v", "doc": ""},
                    {"kind": "doc", "pid": "v", "doc": "a b"},
                    {"kind": "doc", "pid": "v", "doc": "x", "title": "t"},
                    {"kind": "digest", "slug": "s", "n": 0},
                    {"kind": "digest", "slug": "s", "n": 13},
                    {"kind": "digest", "slug": "s", "n": "3"},
                    {"kind": "digest", "slug": "s", "n": True},
                    {"kind": "digest", "slug": "s"}):
            with self.assertRaises(papers.PaperError, msg=repr(bad)):
                papers.canonical(self._doc(bad))

class TestLayouts(unittest.TestCase):
    """specs/23 C1: a block may carry one layout — an enum, strictly one of
    LAYOUTS, refused otherwise; the canonical form carries it, so the same
    paper laid out two ways is two papers; a clip never carries one."""

    def _doc(self, block):
        return {"schema": papers.SCHEMA, "title": "", "blocks": [block]}

    def test_each_layout_is_accepted_and_travels_into_the_canonical_form(self):
        for lay in papers.LAYOUTS:
            out = papers.canonical(self._doc(
                {"kind": "story", "story": "meeting", "pid": "vid1", "layout": lay}))
            self.assertIn(f'"layout":"{lay}"', out)
        # the same block without a layout is a different (older) paper
        plain = papers.canonical(self._doc({"kind": "story", "story": "meeting", "pid": "vid1"}))
        self.assertNotIn("layout", plain)
        self.assertNotEqual(papers.paper_id(plain),
                            papers.paper_id(papers.canonical(self._doc(
                                {"kind": "story", "story": "meeting", "pid": "vid1", "layout": "lead"}))))

    def test_an_unknown_layout_is_refused_not_corrected(self):
        for bad in ("wide", "", None, 1, "LEAD", "lead "):
            with self.assertRaises(papers.PaperError, msg=repr(bad)):
                papers.canonical(self._doc(
                    {"kind": "chart", "chart": "votes", "layout": bad}))

    def test_every_kind_may_lay_out_and_a_clip_may_not(self):
        for block in ({"kind": "note", "text": "a word", "layout": "head"},
                      {"kind": "chart", "chart": "reach", "slug": "s", "layout": "half"},
                      {"kind": "reel", "clips": [{"pid": "v", "start": 1, "end": 2}], "layout": "lead"}):
            self.assertIn('"layout"', papers.canonical(self._doc(block)))
        with self.assertRaises(papers.PaperError):
            papers.canonical(self._doc({"kind": "reel", "layout": "lead",
                "clips": [{"pid": "v", "start": 1, "end": 2, "layout": "lead"}]}))

class TestCanonicalForm(unittest.TestCase):
    def test_canonical_is_deterministic_and_key_order_blind(self):
        a = canonical(portable())
        scrambled = json.loads(json.dumps(portable()))
        scrambled = {k: scrambled[k] for k in ("blocks", "schema", "title")}
        self.assertEqual(a, canonical(scrambled))

    def test_whole_second_times_collapse_to_one_address(self):
        """12, 12.0 and 12.00 are the same clip; a client's int and another's
        float must not mint two addresses for one paper."""
        ints = portable(blocks=[{"kind": "reel", "clips": [
            {"pid": "abc", "start": 12, "end": 24}]}])
        floats = portable(blocks=[{"kind": "reel", "clips": [
            {"pid": "abc", "start": 12.0, "end": 24.00}]}])
        self.assertEqual(paper_id(canonical(ints)), paper_id(canonical(floats)))
        self.assertIn('"start":12}', canonical(ints))

    def test_times_snap_to_the_tenth_second_grid(self):
        a = portable(blocks=[{"kind": "reel", "clips": [
            {"pid": "abc", "start": 1.23, "end": 4.56}]}])
        b = portable(blocks=[{"kind": "reel", "clips": [
            {"pid": "abc", "start": 1.2, "end": 4.6}]}])
        self.assertEqual(canonical(a), canonical(b))

    def test_canonical_round_trips_through_itself(self):
        """canonical(parse(canonical(x))) == canonical(x) — the stored bytes
        are a fixed point, so a re-share of a fetched paper re-mints its own
        address."""
        c = canonical(portable())
        self.assertEqual(c, canonical(json.loads(c)))

    def test_the_id_is_sixteen_hex_characters(self):
        pid = paper_id(canonical(portable()))
        self.assertRegex(pid, r"^[0-9a-f]{16}$")

    def test_real_length_refs_are_accepted(self):
        """The bake mints pids to 80 chars and issue slugs to 96
        (web/bake.py) — the store must hold what the record actually names.
        A review lens caught the original 64-char cap silently refusing
        real refs."""
        canonical(portable(blocks=[
            {"kind": "story", "story": "meeting", "pid": "p" * 80},
            {"kind": "story", "story": "issue", "slug": "s" * 96},
            {"kind": "reel", "clips": [
                {"pid": "p" * 80, "start": 1, "end": 2}]}]))

    def test_a_trailing_newline_is_not_a_ref(self):
        """fullmatch, not $ — "$" admits a trailing newline, and a strict
        store must not hold refs the renderer then drops."""
        with self.assertRaises(PaperError):
            canonical(portable(blocks=[
                {"kind": "story", "story": "meeting", "pid": "abc\n"}]))

    def test_an_astronomical_clip_time_is_refused_not_a_crash(self):
        """int(10**400) overflows float() — that must be a 422-shaped
        PaperError, never an uncaught OverflowError (a 500)."""
        with self.assertRaises(PaperError):
            canonical(portable(blocks=[{"kind": "reel", "clips": [
                {"pid": "abc", "start": 10 ** 400, "end": 10 ** 400 + 1}]}]))

    def test_a_title_only_paper_stores(self):
        canonical({"schema": SCHEMA, "title": "just a name", "blocks": []})

    def test_refusals_name_their_reason(self):
        """Strict, not corrective: every malformed document is a PaperError
        whose message a reader could act on — never a silent rewrite."""
        cases = [
            ("not even an object", [], "json object"),
            ({"schema": "publicrecord.reel/1", "title": "x", "blocks": []},
             None, "schema"),
            ({"schema": SCHEMA, "title": "x", "blocks": [], "author": "me"},
             None, "unknown keys"),
            ({"schema": SCHEMA, "title": 7, "blocks": []}, None, "string"),
            ({"schema": SCHEMA, "title": "a" * (TITLE_MAX + 1), "blocks": []},
             None, "longer"),
            ({"schema": SCHEMA, "title": "a\x00b", "blocks": []},
             None, "control"),
            ({"schema": SCHEMA, "title": "", "blocks": []}, None, "empty"),
            (portable(blocks=[{"kind": "widget", "text": "hi"}]), None,
             "unknown kind"),
            (portable(blocks=[{"kind": "story", "story": "meeting",
                               "pid": "has space"}]), None, "meeting id"),
            (portable(blocks=[{"kind": "story", "story": "meeting",
                               "pid": "ok", "title": "smuggled"}]), None,
             "exactly"),
            (portable(blocks=[{"kind": "reel", "clips": []}]), None, "clips"),
            (portable(blocks=[{"kind": "reel", "clips": [
                {"pid": "abc", "start": 9, "end": 3}]}]), None, "ends before"),
            (portable(blocks=[{"kind": "reel", "clips": [
                {"pid": "abc", "start": "9", "end": 12}]}]), None, "number"),
            (portable(blocks=[{"kind": "reel", "clips": [
                {"pid": "abc", "start": True, "end": 12}]}]), None, "number"),
            (portable(blocks=[{"kind": "reel", "clips": [
                {"pid": "abc", "start": -1, "end": 12}]}]), None, "finite"),
            (portable(blocks=[{"kind": "reel", "clips": [
                {"pid": "abc", "start": 1, "end": 2, "quote": "free text"}]}]),
             None, "exactly"),
        ]
        for doc, _, fragment in cases:
            with self.assertRaises(PaperError, msg=repr(doc)) as cm:
                canonical(doc)
            self.assertIn(fragment, str(cm.exception).lower(),
                          f"for {doc!r} got: {cm.exception}")

    def test_notes_store_on_the_settled_posture(self):
        """P2 (settled with Stephen 2026-07-22): a note is plain text, capped,
        newlines allowed, every other control character refused — the second
        and last free text a stored paper may carry."""
        c = canonical(portable(blocks=[
            {"kind": "note", "text": "Two overrides in one spring.\n\n"
                                     "Watch the tally, not the speeches."}]))
        self.assertIn("Watch the tally", c)
        # exactly at the cap is legal; one past it is refused — and the cap
        # counts UTF-16 units (the reader's unit), so an astral-heavy note
        # the reader would silently truncate is refused here instead:
        # 1,000 astral chars = 2,000 units (legal); 1,001 = 2,002 (refused)
        canonical(portable(blocks=[{"kind": "note", "text": "x" * NOTE_MAX}]))
        canonical(portable(blocks=[
            {"kind": "note", "text": "\U0001d400" * (NOTE_MAX // 2)}]))
        cases = [
            ({"kind": "note", "text": "x" * (NOTE_MAX + 1)}, "longer"),
            ({"kind": "note", "text": "\U0001d400" * (NOTE_MAX // 2 + 1)},
             "longer"),
            ({"kind": "note", "text": "a\tb"}, "control"),
            ({"kind": "note", "text": "a\rb"}, "control"),
            ({"kind": "note", "text": "a\x00b"}, "control"),
            ({"kind": "note", "text": "a\x7fb"}, "control"),
            ({"kind": "note", "text": "   \n  "}, "empty note"),
            ({"kind": "note", "text": 7}, "string"),
            ({"kind": "note"}, "exactly"),
            ({"kind": "note", "text": "ok", "author": "me"}, "exactly"),
        ]
        for block, fragment in cases:
            with self.assertRaises(PaperError, msg=repr(block)) as cm:
                canonical(portable(blocks=[block]))
            self.assertIn(fragment, str(cm.exception).lower(),
                          f"for {block!r} got: {cm.exception}")

    def test_charts_store_as_an_enum_and_refs_never_data(self):
        """A chart block is a kind from a closed list plus at most one ref —
        the reader computes the picture from the record's planes, so a stored
        paper cannot assert a number the record would not draw."""
        c = canonical(portable(blocks=[
            {"kind": "chart", "chart": "votes"},
            {"kind": "chart", "chart": "topics"},
            {"kind": "chart", "chart": "framing"},
            {"kind": "chart", "chart": "framing", "pid": "2YhgO14jXys"},
            {"kind": "chart", "chart": "reach", "slug": "the-override"},
        ]))
        self.assertEqual(canonical(json.loads(c)), c)   # a fixed point too
        cases = [
            ({"kind": "chart", "chart": "sparkline"}, "unknown chart"),
            ({"kind": "chart"}, "unknown chart"),
            ({"kind": "chart", "chart": "reach"}, "exactly"),
            ({"kind": "chart", "chart": "reach", "slug": "has space"},
             "issue slug"),
            ({"kind": "chart", "chart": "framing", "pid": "has space"},
             "meeting id"),
            # specs/24: votes may name ONE meeting (a pid); a slug is a mangle
            ({"kind": "chart", "chart": "votes", "slug": "abc"}, "exactly"),
            ({"kind": "chart", "chart": "topics", "slug": "abc"}, "exactly"),
            ({"kind": "chart", "chart": "votes", "data": [1, 2]}, "exactly"),
            ({"kind": "chart", "chart": "numbers"}, "exactly one"),
            ({"kind": "chart", "chart": "numbers", "pid": "a", "slug": "b"}, "exactly one"),
            ({"kind": "chart", "chart": "shape", "slug": "abc"}, "exactly"),
            ({"kind": "chart", "chart": "ledger", "pid": "abc"}, "exactly"),
            ({"kind": "chart", "chart": "shape", "pid": "has space"}, "meeting id"),
            ({"kind": "reading"}, "exactly one"),
            ({"kind": "reading", "pid": "a", "slug": "b"}, "exactly one"),
            ({"kind": "reading", "pid": "a", "text": "words"}, "exactly"),
        ]
        for block, fragment in cases:
            with self.assertRaises(PaperError, msg=repr(block)) as cm:
                canonical(portable(blocks=[block]))
            self.assertIn(fragment, str(cm.exception).lower(),
                          f"for {block!r} got: {cm.exception}")

    def test_a_p2_paper_round_trips_the_endpoints(self):
        """The full P2 shape — stories, a reel, charts, a note — stores and
        serves byte-canonically, one address per paper."""
        from fastapi.testclient import TestClient

        from record.app import create_app
        mem = MemPapers()
        client = TestClient(create_app(corpus=object(), papers=mem))
        doc = portable(blocks=[
            {"kind": "story", "story": "issue", "slug": "the-override"},
            {"kind": "chart", "chart": "reach", "slug": "the-override"},
            {"kind": "chart", "chart": "votes"},
            {"kind": "note", "text": "The spring the override kept\nreturning."},
        ])
        r = client.post("/api/papers", json=doc)
        self.assertEqual(r.status_code, 200, r.text)
        pid = r.json()["id"]
        g = client.get(f"/api/papers/{pid}")
        self.assertEqual(g.status_code, 200)
        kinds = [b["kind"] for b in g.json()["blocks"]]
        self.assertEqual(kinds, ["story", "chart", "chart", "note"])
        self.assertEqual(mem.get(pid).decode(), canonical(doc))

    def test_the_reader_never_computes_the_hash(self):
        """The canonical form is decided HERE — app.js must not grow its own
        (a client-side hash would be a cross-language byte contract waiting
        to drift; the client POSTs and receives the address)."""
        js = (REPO / "web" / "static" / "app.js").read_text()
        for token in ("sha256", "SHA-256", "crypto.subtle", "digest("):
            self.assertNotIn(token, js,
                             f"app.js grew {token!r} — the store's canonical "
                             "bytes are server-side only (record/papers.py)")


class TestPaperEndpoints(unittest.TestCase):
    def setUp(self):
        from fastapi.testclient import TestClient

        from record.app import create_app
        self.mem = MemPapers()
        # corpus=object(): these routes must never touch the record itself
        self.client = TestClient(create_app(corpus=object(), papers=self.mem))

    def test_post_answers_the_address_and_get_serves_the_bytes(self):
        r = self.client.post("/api/papers", json=portable())
        self.assertEqual(r.status_code, 200, r.text)
        pid = r.json()["id"]
        self.assertRegex(pid, r"^[0-9a-f]{16}$")
        self.assertEqual(r.json()["path"], f"/api/papers/{pid}")
        g = self.client.get(f"/api/papers/{pid}")
        self.assertEqual(g.status_code, 200)
        self.assertEqual(g.json()["schema"], SCHEMA)
        self.assertEqual(g.json()["title"], "Overrides, watched")
        # the address is the content, so the cache may say forever
        self.assertIn("immutable", g.headers.get("cache-control", ""))

    def test_the_same_paper_cannot_have_two_addresses(self):
        a = self.client.post("/api/papers", json=portable())
        b = self.client.post("/api/papers", json=portable())
        self.assertEqual(a.json()["id"], b.json()["id"])
        self.assertEqual(len(self.mem._d), 1)

    def test_stored_bytes_are_canonical_not_the_wire_bytes(self):
        """However the client spelled it (key order, 12.0), the store holds
        the one canonical form."""
        doc = portable(blocks=[{"kind": "reel", "clips": [
            {"end": 24.0, "start": 12, "pid": "abc"}]}])
        pid = self.client.post("/api/papers", json=doc).json()["id"]
        self.assertEqual(self.mem.get(pid).decode(), canonical(doc))

    def test_invalid_documents_are_422_with_the_reason(self):
        r = self.client.post("/api/papers",
                             json={"schema": SCHEMA, "title": "x",
                                   "blocks": [], "author": "me"})
        self.assertEqual(r.status_code, 422)
        self.assertIn("unknown keys", r.json()["error"])
        r = self.client.post("/api/papers", content=b"not json{",
                             headers={"Content-Type": "application/json"})
        self.assertEqual(r.status_code, 422)

    def test_oversize_is_413_before_parsing(self):
        blob = b"x" * (64 * 1024 + 1)
        r = self.client.post("/api/papers", content=blob,
                             headers={"Content-Type": "application/json"})
        self.assertEqual(r.status_code, 413)

    def test_absent_papers_are_honest_404s(self):
        r = self.client.get("/api/papers/0123456789abcdef")
        self.assertEqual(r.status_code, 404)
        self.assertIn("no paper at this address", r.json()["error"])
        # a malformed id is a 404 too, not a 500 and not a probe surface
        self.assertEqual(self.client.get("/api/papers/xyz").status_code, 404)
        self.assertEqual(
            self.client.get("/api/papers/AAAAAAAAAAAAAAAA").status_code, 404)
        # fullmatch: an id with a smuggled newline is not an address either
        self.assertEqual(
            self.client.get("/api/papers/0123456789abcde%0a").status_code, 404)

    def test_an_astronomical_time_is_a_422_at_the_endpoint(self):
        r = self.client.post("/api/papers", json=portable(blocks=[
            {"kind": "reel", "clips": [
                {"pid": "abc", "start": 10 ** 400, "end": 10 ** 400 + 1}]}]))
        self.assertEqual(r.status_code, 422, r.text)

    def test_without_a_bucket_the_store_says_so(self):
        """papers=None and no RECORD_PAPERS_BUCKET → 503 with the covenant
        line, not a crash and not a silent success."""
        from fastapi.testclient import TestClient

        from record.app import create_app
        from record.settings import settings
        if settings.papers_bucket:
            self.skipTest("RECORD_PAPERS_BUCKET is set in this environment")
        bare = TestClient(create_app(corpus=object()))
        r = bare.post("/api/papers", json=portable())
        self.assertEqual(r.status_code, 503)
        self.assertIn("full link", r.json()["error"])
        self.assertEqual(bare.get("/api/papers/0123456789abcdef").status_code,
                         503)

    def test_the_store_takes_no_identity(self):
        """No cookie is set and nothing about the caller is stored — the
        object is the canonical document bytes and only that."""
        r = self.client.post("/api/papers", json=portable())
        self.assertNotIn("set-cookie", {k.lower() for k in r.headers})
        pid = r.json()["id"]
        stored = json.loads(self.mem.get(pid))
        self.assertEqual(set(stored), {"schema", "title", "blocks"})

    def test_a_taken_page_offered_again_is_refused_at_the_door(self):
        """A steward's takedown (record/OPERATING.md §5) moves the object
        under taken/; the same bytes POSTed again are not stored and the
        share is told so — 410 with the read path's own sentence — never a
        200 whose link answers 404 (a skeptic's catch on the P2 folds)."""
        r = self.client.post("/api/papers", json=portable())
        self.assertEqual(r.status_code, 200)
        pid = r.json()["id"]
        self.mem.taken.add(pid); del self.mem._d[pid]
        again = self.client.post("/api/papers", json=portable())
        self.assertEqual(again.status_code, 410)
        self.assertIn("took this page down", again.json()["error"])        # the share's own sentence (decided 2026-09-24); the editor copies the full link
        gone = self.client.get(f"/api/papers/{pid}")
        self.assertEqual(gone.status_code, 404)
        self.assertIn("taken down", gone.json()["error"])                  # the read path keeps its sentence
        self.assertIsNone(self.mem.get(pid))


if __name__ == "__main__":
    unittest.main()


class TestTwoPathsKinds(unittest.TestCase):
    """specs/24: the two paths' kinds are refs and enums like every kind
    before them — a numbers chart names a meeting or an issue (one), a
    shape a meeting, a ledger an issue, votes may name one meeting, and the
    record's reading names a meeting or an issue. No new free text."""

    def test_the_new_kinds_store_as_refs(self):
        from record.papers import canonical
        blocks = [{"kind": "chart", "chart": "numbers", "pid": "2YhgO14jXys"},
                  {"kind": "chart", "chart": "numbers", "slug": "issue_x"},
                  {"kind": "chart", "chart": "shape", "pid": "2YhgO14jXys"},
                  {"kind": "chart", "chart": "ledger", "slug": "issue_x"},
                  {"kind": "chart", "chart": "votes", "pid": "2YhgO14jXys"},
                  {"kind": "chart", "chart": "votes"},
                  {"kind": "reading", "pid": "2YhgO14jXys"},
                  {"kind": "reading", "slug": "issue_x"}]
        c = canonical(portable(blocks=blocks))
        doc = json.loads(c)
        self.assertEqual(doc["blocks"], blocks)
        self.assertEqual(canonical(json.loads(c)), c)

class TestBroadsheetKinds(unittest.TestCase):
    """specs/29 P1: the broadsheet's six blocks are enums and refs like every
    kind before them — a lead names a meeting, a search box names nothing,
    and week / threads / strip / names may name a municipality (names may
    name one name instead). No new free text; a block that names both a town
    and a who, an unknown key, or a ref that is not slug-shaped is refused,
    never corrected."""

    def test_the_six_kinds_store_as_refs(self):
        from record.papers import canonical, BS_KINDS
        blocks = [{"kind": "lead", "pid": "2YhgO14jXys"},
                  {"kind": "week"}, {"kind": "week", "town": "brookline"},
                  {"kind": "threads"}, {"kind": "threads", "town": "boston"},
                  {"kind": "strip"}, {"kind": "strip", "town": "boston", "layout": "half"},
                  {"kind": "names"}, {"kind": "names", "town": "brookline"},
                  {"kind": "names", "who": "p-paul-warren"},
                  {"kind": "search"}]
        c = canonical(portable(blocks=blocks))
        doc = json.loads(c)
        self.assertEqual(doc["blocks"], blocks)
        self.assertEqual(canonical(json.loads(c)), c)
        self.assertEqual(BS_KINDS, ("lead", "week", "threads", "strip", "names", "search"))

    def test_the_six_kinds_are_strict(self):
        from record.papers import canonical, PaperError
        bad = [
            ({"kind": "lead"}, "exactly"),                             # a lead names a meeting
            ({"kind": "lead", "pid": "a b"}, "not a meeting id"),
            ({"kind": "lead", "pid": "x", "town": "boston"}, "exactly"),
            ({"kind": "search", "q": "housing"}, "exactly"),           # a search box stores no query
            ({"kind": "week", "town": "Brookline MA"}, "municipality slug"),
            ({"kind": "week", "who": "p-x"}, "may carry only town"),
            ({"kind": "strip", "town": ""}, "municipality slug"),
            ({"kind": "threads", "n": 6}, "may carry only town"),
            ({"kind": "names", "town": "boston", "who": "p-x"}, "not both"),
            ({"kind": "names", "who": "Paul Warren"}, "name slug"),
            ({"kind": "names", "who": "boston"}, "name slug"),          # a who wears its kind's letter
            ({"kind": "names", "town": "Boston"}, "municipality slug"),   # a town is the press's lower-case slug
            ({"kind": "strip", "town": "x" * 97}, "municipality slug"),
            ({"kind": "names", "name": "Paul Warren"}, "may carry only town, who"),
        ]
        for b, why in bad:
            with self.assertRaises(PaperError, msg=b) as cm:
                canonical(portable(blocks=[b]))
            self.assertIn(why, str(cm.exception), b)

