"""specs/29 P2 — the front pages, listed: the press turns the share store's
pages into cards beside the record's own; the gallery page and the front
page's strip carry them; the kinds the press claims are the reader's own
(bsMadeFrom), held equal by a node twin; a stored blob that is not a page
makes no card; nothing names a writer."""

import datetime as dt
import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.test_web_bake import TestBakeEdition
from web import gallery

REPO = Path(__file__).resolve().parents[1]
JS = (REPO / "web" / "static" / "app.js").read_text()

_TMP = None
OUT = None
TODAY = dt.date(2026, 9, 30)   # the reference day every press passes in — never the wall clock


def _paper(title, blocks):
    return json.dumps({"schema": "publicrecord.paper/1", "title": title, "blocks": blocks},
                      sort_keys=True, separators=(",", ":")).encode("utf-8")


SHARED = [
    # an issue over time, shared four days before the press
    {"id": "aaaaaaaaaaaaaaaa", "created": "2026-09-26T12:00:00+00:00",
     "data": _paper("Overrides, watched", [
         {"kind": "story", "story": "issue", "slug": "issue_testville_budget-override", "layout": "lead"},
         {"kind": "chart", "chart": "reach", "slug": "issue_testville_budget-override"},
         {"kind": "note", "text": "What changed: the override carried.\n\nWatch the fall."},
         {"kind": "reel", "clips": [{"pid": "vid1", "start": 10, "end": 40}, {"pid": "vid2", "start": 5, "end": 30}], "layout": "half"},
         {"kind": "search"}])},
    # one meeting, shared today
    {"id": "bbbbbbbbbbbbbbbb", "created": "2026-09-30T09:00:00+00:00",
     "data": _paper("The board, in one night", [
         {"kind": "lead", "pid": "vid2"}, {"kind": "chart", "chart": "numbers", "pid": "vid2"},
         {"kind": "quote", "pid": "vid2", "t": 12}, {"kind": "note", "text": "one paragraph"}])},
    # not a page: bytes the store would never hold, and an id that is not one
    {"id": "cccccccccccccccc", "created": "2026-09-29T00:00:00+00:00", "data": b"{not json"},
    {"id": "dddddddddddddddd", "created": "2026-09-29T00:00:00+00:00", "data": b'{"schema": "other", "title": "x", "blocks": []}'},
    # valid JSON of the wrong shape, and a page minted before the button said it lists the page
    {"id": "eeeeeeeeeeeeeeee", "created": "2026-09-29T01:00:00+00:00", "data": b'{"schema": "publicrecord.paper/1", "title": "x", "blocks": 5}'},
    {"id": "ffffffffffffffff", "created": "2026-09-29T02:00:00+00:00", "data": _paper("x", [{"kind": "reel", "clips": 5}, {"kind": "note", "text": 7}])},
    {"id": "1111111111111111", "created": "2026-09-01T02:00:00+00:00", "data": _paper("Before the button said so", [{"kind": "search"}])},
    {"id": "not-an-id", "created": None, "data": _paper("x", [{"kind": "search"}])},
]


def setUpModule():
    global _TMP, OUT
    from web import bake
    _TMP = tempfile.TemporaryDirectory()
    root = Path(_TMP.name)
    db = root / "corpus.db"
    TestBakeEdition._seed(db)
    OUT = root / "app"
    bake.bake(str(db), str(OUT), "9.9.9", "https://example.org", shared=SHARED, today=TODAY)


def tearDownModule():
    if _TMP:
        _TMP.cleanup()


def node(body):
    exe = shutil.which("node")
    if not exe:
        raise unittest.SkipTest("node not available")
    return subprocess.run([exe, "-e", body], capture_output=True, text=True)


def lift(pattern):
    m = re.search(pattern, JS, re.S)
    assert m, f"{pattern!r} not found in the reader — did it move?"
    return m.group(0)


class TestCards(unittest.TestCase):
    def test_the_kind_is_the_readers_own(self):
        """kind_of ≡ bsMadeFrom(...).kind over every shape the templates write
        and a few they do not — the press and the reader must call a page
        the same thing."""
        shapes = [
            [{"kind": "lead", "pid": "a"}, {"kind": "note", "text": "x"}],
            [{"kind": "lead", "pid": "a"}, {"kind": "quote", "pid": "b", "t": 1}],
            [{"kind": "story", "story": "meeting", "pid": "a", "layout": "lead"}],
            [{"kind": "story", "story": "meeting", "pid": "a"}],
            [{"kind": "story", "story": "issue", "slug": "s"}, {"kind": "chart", "chart": "reach", "slug": "s"}],
            [{"kind": "story", "story": "issue", "slug": "s"}, {"kind": "chart", "chart": "ledger", "slug": "s"}],
            [{"kind": "names", "who": "p-jane"}], [{"kind": "names", "who": "l-kent-st"}], [{"kind": "names", "who": "o-bpda"}],
            [{"kind": "names"}],
            [{"kind": "strip", "town": "boston"}, {"kind": "strip", "town": "brookline"}],
            [{"kind": "strip", "town": "boston"}, {"kind": "strip", "town": "boston"}],
            [{"kind": "strip"}, {"kind": "threads"}], [{"kind": "threads"}],
            [{"kind": "chart", "chart": "votes"}], [{"kind": "chart", "chart": "votes", "pid": "a"}],
            [{"kind": "search"}], [],
        ]
        body = "\n".join([
            'const BASE = "/app"; const esc = s => String(s == null ? "" : s);',
            lift(r"  const nOf = \(n, one, many\) => .+?;"),
            lift(r"  function bsMadeFrom\(doc, mby, iby\) \{.+?\n  \}"),
            "const S = " + json.dumps(shapes) + ";",
            "console.log(JSON.stringify(S.map(blocks => bsMadeFrom({ blocks }, {}, {}).kind)));"])
        r = node(body)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertEqual(json.loads(r.stdout), [gallery.kind_of(b) for b in shapes])

    def test_what_and_when_are_said_plainly(self):
        self.assertEqual(gallery.what_of(SHARED[0] and json.loads(SHARED[0]["data"])["blocks"]),
                         "a timeline, a reel of 2 clips, a search box, 2 paragraphs")
        self.assertEqual(gallery.what_of([{"kind": "lead", "pid": "a"}, {"kind": "quote", "pid": "a", "t": 1},
                                          {"kind": "quote", "pid": "a", "t": 2}, {"kind": "doc", "pid": "a", "doc": "d"}]),
                         "a lead story, 2 quotes, 1 filing")
        self.assertEqual(gallery.what_of([{"kind": k} for k in ("week", "threads", "strip", "names", "search", "reading", "digest")]),
                         "the week, threads, how they talked, who and where, a search box, more")
        # the day, said absolutely — a static page must never say "today" a week on
        self.assertEqual(gallery.when_words("2026-09-30T09:00:00+00:00", TODAY), "September 30")
        self.assertEqual(gallery.when_words("2026-06-16T00:00:00+00:00", TODAY), "June 16")
        self.assertEqual(gallery.when_words("2025-06-16T00:00:00+00:00", TODAY), "June 16, 2025")
        self.assertEqual(gallery.when_words(None, TODAY), "")
        self.assertEqual(gallery.when_words("garbage", TODAY), "")
        self.assertEqual(gallery.paragraphs_of([{"kind": "note", "text": "a\n\nb\n c"}, {"kind": "note", "text": "  "}]), 3)

    def test_a_blob_that_is_not_a_page_makes_no_card_and_nobody_is_named(self):
        cards = gallery.readers_cards(SHARED, [{"pid": "vid1", "town": "Testville"}, {"pid": "vid2", "town": "Testville"}],
                                      [{"slug": "issue_testville_budget-override", "town": "Testville"}], {}, "/app", TODAY)
        # newest first; the malformed rows and the page minted before LISTED_SINCE make no card
        self.assertEqual([c["id"] for c in cards], ["bbbbbbbbbbbbbbbb", "aaaaaaaaaaaaaaaa"])
        one, issue = cards
        self.assertEqual(one["kind"], "One meeting")
        self.assertEqual(one["made"], "1 meeting")
        self.assertTrue(one["week"])
        self.assertFalse(one["seasoned"])          # shared today: the gallery lists it, the strip waits for a press to have listed it
        self.assertEqual(one["when"], "September 30")
        self.assertEqual(issue["kind"], "An issue over time")
        self.assertEqual(issue["made"], "2 meetings · 1 issue")
        self.assertEqual(issue["town"], "Testville")
        self.assertEqual(issue["when"], "September 26")
        self.assertTrue(issue["week"] and issue["seasoned"])
        html = gallery.card_html(issue)
        self.assertIn("A reader’s front page", html)
        self.assertIn("shared as a link, September 26 · no name, by design", html)
        self.assertIn('data-by="readers" data-kind="an-issue-over-time" data-town="testville" data-towns="testville" data-week="1"', html)
        self.assertLess(html.index("<b>Overrides"), html.index("A reader’s front page"))   # the title leads the link's name
        for bad in ("author", "writer", "@", "cz-", "2026-09-26T"):
            self.assertNotIn(bad, html)
        self.assertEqual(gallery.strip_cards(cards), [issue])   # the newest page a previous press has listed
        # a meeting the pressing lacks is not counted among a page's makings
        c = gallery.card_of(json.loads(SHARED[0]["data"]), "a" * 16, SHARED[0]["created"], {"vid1": {"town": "T"}}, {}, {}, "/app", TODAY)
        self.assertEqual(c["made"], "1 meeting")
        # the day's cap: thirteen pages from one day list twelve
        flood = [{"id": f"{i:016x}", "created": "2026-09-28T10:%02d:00+00:00" % i, "data": _paper(f"page {i}", [{"kind": "search"}])} for i in range(13)]
        self.assertEqual(len(gallery.readers_cards(flood, [], [], {}, "/app", TODAY)), gallery.PER_DAY)
        from record.papers import LIST_MAX
        self.assertEqual(gallery.MAX_LISTED, LIST_MAX)
        # a card whose maker's title is empty is still a card, untitled
        c = gallery.card_of({"schema": "publicrecord.paper/1", "title": "", "blocks": [{"kind": "search"}]}, "e" * 16, None, {}, {}, {}, "/app", TODAY)
        self.assertEqual(c["title"], "Untitled front page")
        self.assertEqual(gallery.readers_cards(None, [], [], {}, "/app", TODAY), [])
        self.assertEqual(gallery.readers_cards([{"id": "f" * 16, "created": "2026-09-29T00:00:00Z", "data": b"[]"}], [], [], {}, "/app", TODAY), [])

    def test_the_memory_store_lists_like_the_bucket(self):
        from record.papers import MemPapers
        s = MemPapers()
        s.put_new("a" * 16, b"x"); s.put_new("b" * 16, b"y")
        rows = s.list_all()
        self.assertEqual([r["id"] for r in rows], ["b" * 16, "a" * 16])     # newest first, as the bucket lists
        self.assertEqual(rows[0]["data"], b"y")
        self.assertTrue(rows[0]["created"] > rows[1]["created"])
        self.assertEqual(len(s.list_all(limit=1)), 1)
        # taken down stays down: the same bytes do not come back
        s.taken.add("a" * 16); del s._d["a" * 16]
        from record.papers import PaperTaken
        with self.assertRaises(PaperTaken):
            s.put_new("a" * 16, b"x")
        self.assertIsNone(s.get("a" * 16))
        # minted on the clock's own day, so a memory store's pages are listable
        self.assertGreaterEqual(rows[0]["created"][:10], gallery.LISTED_SINCE.isoformat())

    def test_the_bucket_store_lists_newest_first_capped_and_refuses_a_taken_page(self):
        """GcsPapers against a fake client: only p/<id>.json objects count, the
        newest LIST_MAX are downloaded (the cap comes before the downloads),
        one unreadable object is one missing row, and put_new writes nothing
        when the page sits under taken/."""
        from record.papers import GcsPapers, LIST_MAX, PaperTaken

        class Blob:
            def __init__(self, name, when, data=b"{}", fail=False):
                self.name, self.time_created, self._data, self._fail = name, when, data, fail
                self.downloads = 0
            def download_as_bytes(self):
                self.downloads += 1
                if self._fail:
                    raise RuntimeError("gone")
                return self._data
        t0 = dt.datetime(2026, 9, 20, tzinfo=dt.timezone.utc)
        blobs = [Blob(f"p/{i:016x}.json", t0 + dt.timedelta(minutes=i)) for i in range(LIST_MAX + 5)]
        blobs += [Blob("p/not-an-id.json", t0 + dt.timedelta(days=9)), Blob("p/readme.txt", t0 + dt.timedelta(days=9)),
                  Blob("taken/" + "9" * 16 + ".json", t0 + dt.timedelta(days=9)), Blob("p/" + "8" * 16 + ".json", t0 + dt.timedelta(days=10), fail=True)]   # the newest of all, and unreadable
        class Client:
            def list_blobs(self, name, prefix=""):
                return [b for b in blobs if b.name.startswith(prefix)]
        class Bucket:
            client = Client()
            def blob(self, name):
                b = type("B", (), {})()
                b.exists = lambda: name.startswith("taken/") and name.endswith("9" * 16 + ".json")
                b.upload_from_string = lambda *a, **k: writes.append(name)
                return b
        writes = []
        store = GcsPapers("fake")
        store._bucket = Bucket()
        rows = store.list_all()
        self.assertEqual(len(rows), LIST_MAX - 1)                               # the cut is LIST_MAX; the unreadable one is one missing row
        ids = [r["id"] for r in rows]
        self.assertEqual(ids[0], f"{LIST_MAX + 4:016x}")                      # newest first, the unreadable newest absent
        self.assertNotIn("not-an-id", ids); self.assertNotIn("9" * 16, ids); self.assertNotIn("8" * 16, ids)
        self.assertEqual(sum(b.downloads for b in blobs), LIST_MAX)             # downloads only inside the cut, none for the rest
        with self.assertRaises(PaperTaken):
            store.put_new("9" * 16, b"{}")
        self.assertEqual(writes, [])                                            # taken down stays down, and said so
        store.put_new("7" * 16, b"{}")
        self.assertEqual(writes, ["p/" + "7" * 16 + ".json"])


class TestGalleryPress(unittest.TestCase):
    def test_the_gallery_page_presses_the_record_s_own_and_readers_pages(self):
        page = (OUT / "front-pages" / "index.html").read_text()
        self.assertIn("<h1>Front pages</h1>", page)
        self.assertIn("Nobody signs — the record keeps no names", page)
        # the record's own first, then the door, then readers' newest first
        own = page.count('data-by="own"')
        self.assertGreaterEqual(own, 2, "the press's own pages are listed")
        self.assertEqual(page.count('data-by="readers"'), 2)
        self.assertLess(page.index('data-by="own"'), page.index('class="bs-fpdoor"'))
        self.assertLess(page.index('class="bs-fpdoor"'), page.index('data-by="readers"'))
        self.assertLess(page.index("The board, in one night"), page.index("Overrides, watched"))
        self.assertIn("pressed nightly", page)
        self.assertIn("shared as a link, September 30 · no name, by design", page)
        self.assertIn("made from 2 meetings · 1 issue · a timeline, a reel of 2 clips, a search box, 2 paragraphs", page)
        # the bad rows and the pre-release page made no card; no ISO timestamp reaches the page
        for bad in ("cccccccccccccccc", "dddddddddddddddd", "eeeeeeeeeeeeeeee", "ffffffffffffffff", "1111111111111111",
                    "Before the button said so", "not-an-id", "{not json", "2026-09-30T09"):
            self.assertNotIn(bad, page)
        # the filters are pressed hidden (a control that did nothing with the
        # script off would be a lie) and the reader's script shows them; the
        # pressed page shows every card; the count line is pressed and speaks
        self.assertIn('<nav class="bs-filters" aria-label="which front pages" hidden>', page)
        self.assertIn('<a class="bs-filter" href="#everything" data-filter="all" aria-current="true">Everything</a>', page)
        self.assertIn('id="bs-gallery-count" role="status"', page)
        for f in ('data-filter="by:own"', 'data-filter="by:readers"', 'data-filter="town:testville"', 'data-filter="week"',
                  'data-filter="kind:an-issue-over-time"', 'data-filter="kind:one-meeting"'):
            self.assertIn(f, page)
        self.assertNotIn("hidden", page[page.index('id="bs-gallery-grid"'):page.index("bs-gallery-foot")])
        self.assertRegex(page, r'data-all="\d+ front pages · the record’s own \d+ · readers’ 2"')
        self.assertIn("a steward can take one down · the record’s bytes are never copied, only referenced", page)
        # content, not chrome: no studio class, no button, no script inline
        body = page[page.index("<body>"):page.rindex("<script")]
        for bad in ("cz-", "<button", "onclick", "#a855f7"):
            self.assertNotIn(bad, body)

    def test_the_front_page_s_strip_seats_the_newest_reader_s_page(self):
        home = (OUT / "index.html").read_text()
        strip = home[home.index('class="bs-frontpages"'):home.index("</section>", home.index('class="bs-frontpages"'))]
        self.assertEqual(strip.count('data-by="readers"'), 1)
        # the strip seats the newest page a night's press has already listed —
        # the one shared today waits for the gallery's night (and the steward's glance)
        self.assertIn("Overrides, watched", strip)
        self.assertNotIn("The board, in one night", strip)
        # the masthead's word points at the gallery, and the gallery marks it current
        self.assertIn('class="navlink" href="/app/front-pages/">Front pages</a>', home)
        self.assertIn('class="navlink active" href="/app/front-pages/">Front pages</a>', (OUT / "front-pages" / "index.html").read_text())
        # the worker's key carries the listed set, so a quiet week's takedown reaches returning readers
        sw = (OUT / "sw.js").read_text()
        self.assertRegex(sw, r'const CACHE = \'cz-record-9\.9\.9-[0-9a-f]{16}-[0-9a-f]{8}\'')
        self.assertIn('href="/app/front-pages/"', strip)         # all front pages →
        self.assertIn('class="bs-fpdoor" href="/app/p#edit"', strip)
        sw = (OUT / "sw.js").read_text()
        self.assertIn('"/app/front-pages/"', sw)

    def test_the_strip_seats_only_a_page_that_cites_the_record(self):
        """The moderation stance (decided 2026-09-24): the day a page waits is
        the steward's window, and the strip seats only a page made from
        something the record holds — a seasoned page that cites nothing is
        listed in the gallery but never leads the front page."""
        bare = {"id": "1" * 16, "seasoned": True, "cites": False, "title": "shout"}
        cites = {"id": "2" * 16, "seasoned": True, "cites": True, "title": "a night"}
        fresh = {"id": "3" * 16, "seasoned": False, "cites": True, "title": "today"}
        self.assertEqual([c["id"] for c in gallery.strip_cards([fresh, bare, cites])], ["2" * 16])
        self.assertEqual(gallery.strip_cards([fresh, bare]), [])
        # cites, from the bytes: a held meeting, a record-wide block, or neither
        mk = lambda blocks: gallery.card_of({"schema": gallery.SCHEMA, "title": "t", "blocks": blocks}, "4" * 16,
                                            "2026-09-20T00:00:00+00:00", {"vid1": {"pid": "vid1", "town": "Boston"}}, {}, {}, "/app", TODAY)
        self.assertTrue(mk([{"kind": "story", "story": "meeting", "pid": "vid1"}])["cites"])
        self.assertTrue(mk([{"kind": "chart", "chart": "votes"}])["cites"])                       # drawn from the whole record
        self.assertTrue(mk([{"kind": "week", "town": "boston"}])["cites"])                          # scoped to a town the pressing holds
        self.assertFalse(mk([{"kind": "week", "town": "salem"}])["cites"])                          # …or to one it lacks
        self.assertFalse(mk([{"kind": "chart", "chart": "numbers", "pid": "gone"}])["cites"])     # a wide kind scoped to a meeting it lacks
        self.assertFalse(mk([{"kind": "names", "who": "p-nobody"}])["cites"])                     # a person is a scope the card cannot vouch for
        self.assertFalse(mk([{"kind": "note", "text": "a shout"}])["cites"])                       # a title over paragraphs
        self.assertFalse(mk([{"kind": "story", "story": "meeting", "pid": "gone"}])["cites"])     # names nothing this pressing holds

    def test_two_presses_of_one_store_are_identical_and_a_moved_store_presses(self):
        from web import bake
        from record.press import needs_press, shared_digest
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); db = root / "corpus.db"
            TestBakeEdition._seed(db)
            bake.bake(str(db), str(root / "a"), "1.0.0", "https://x.org", shared=SHARED, today=TODAY)
            bake.bake(str(db), str(root / "b"), "1.0.0", "https://x.org", shared=SHARED, today=TODAY)
            for rel in ("front-pages/index.html", "index.html", "sw.js"):
                self.assertEqual((root / "a" / rel).read_bytes(), (root / "b" / rel).read_bytes(), rel)
        self.assertEqual(shared_digest(None), "")
        self.assertEqual(shared_digest([]), "")
        d1 = shared_digest(SHARED, TODAY); d2 = shared_digest(list(reversed(SHARED)), TODAY)
        self.assertTrue(d1.startswith("|s") and d1 == d2)                    # order-blind
        self.assertNotEqual(d1, shared_digest(SHARED[:-1], TODAY))           # a page gone is a change
        # needs_press reads the store's digest off the recorded fingerprint
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / "pressing.json"
            from record.press import corpus_fingerprint
            from memory.store import Corpus
            db = Path(tmp) / "c.db"; TestBakeEdition._seed(db)
            c = Corpus(str(db))
            try:
                p.write_text(json.dumps({"fingerprint": corpus_fingerprint(c) + shared_digest(SHARED, TODAY)}))
                self.assertFalse(needs_press(c, str(p), shared=SHARED, today=TODAY))
                self.assertTrue(needs_press(c, str(p), shared=SHARED[:-1], today=TODAY))
                self.assertTrue(needs_press(c, str(p), shared=SHARED, today=TODAY + dt.timedelta(days=2)))   # a page turns seasoned
                self.assertTrue(needs_press(c, str(p), today=TODAY))
            finally:
                c.close()

    def test_a_day_passing_moves_the_gate_and_the_key(self):
        """The strip seats a page once a previous press has listed it and a
        card leaves this week after seven — bits that change with nobody touching the store —
        so the pressing's fingerprint and the worker's key carry them: the
        night they flip presses and reaches returning readers, and a quiet
        night after that is quiet again (a skeptic's catch)."""
        from web import bake
        from record.press import shared_digest
        day = dt.timedelta(days=1)
        self.assertEqual(gallery.age_bits(TODAY, TODAY), (True, False, False))
        self.assertEqual(gallery.age_bits(TODAY - day, TODAY), (True, False, False))       # first listed at age one: not yet seated
        self.assertEqual(gallery.age_bits(TODAY - 2 * day, TODAY), (True, True, False))    # a press has listed it: seasoned
        self.assertEqual(gallery.age_bits(TODAY - 7 * day, TODAY), (False, True, False))
        self.assertEqual(gallery.age_bits(TODAY + day, TODAY), (False, False, False))
        self.assertEqual(gallery.age_bits(None, TODAY), (False, False, False))
        self.assertEqual(gallery.age_bits(dt.date(2026, 12, 20), dt.date(2027, 1, 1)), (False, True, True))   # the year is said
        # with the last pressing's moment at hand the rule is exact: listed by
        # a previous press AND a day old — a skipped night seats nothing early,
        # a same-day re-press seats nothing that only the morning's press showed
        utc = dt.timezone.utc
        press = lambda day, h=8, m=30: dt.datetime(day.year, day.month, day.day, h, m, tzinfo=utc)
        after = "2026-09-30T10:00:00+00:00"                                             # shared after TODAY's 08:30 press
        self.assertFalse(gallery.seasoned_at(after, TODAY, press(TODAY)))               # age 0
        self.assertFalse(gallery.seasoned_at(after, TODAY + day, press(TODAY)))         # first listed tonight — the last press ran before it
        self.assertTrue(gallery.seasoned_at(after, TODAY + 2 * day, press(TODAY + day)))  # last night's press listed it
        self.assertFalse(gallery.seasoned_at(after, TODAY + 2 * day, press(TODAY)))     # a skipped night: no press has listed it yet
        before = "2026-09-30T02:00:00+00:00"                                            # shared before TODAY's press
        self.assertFalse(gallery.seasoned_at(before, TODAY, press(TODAY, 12)))          # a re-press the same day: a day old is still required
        self.assertTrue(gallery.seasoned_at(before, TODAY + day, press(TODAY)))         # one night in the gallery, then the strip
        self.assertEqual(gallery.age_bits(after, TODAY + day, press(TODAY))[1], False)
        self.assertEqual(gallery.age_bits(after, TODAY + 2 * day, press(TODAY + day))[1], True)
        rows = [{"id": "e" * 16, "created": after, "data": b"{}"}]
        self.assertNotEqual(shared_digest(rows, TODAY + 2 * day, press(TODAY)),
                            shared_digest(rows, TODAY + 2 * day, press(TODAY + day)))   # the moment a press listed it moves the gate
        self.assertNotEqual(shared_digest(SHARED, TODAY + day), shared_digest(SHARED, TODAY + 2 * day))   # a page shared TODAY turns seasoned
        self.assertEqual(shared_digest(SHARED, TODAY + 8 * day), shared_digest(SHARED, TODAY + 9 * day))   # both past every flip: quiet
        old = [{"id": "c" * 16, "created": "2026-09-20T00:00:00+00:00", "data": b"{}"}]        # before LISTED_SINCE: never listed
        for d in (dt.date(2026, 9, 20), dt.date(2026, 9, 21), dt.date(2026, 9, 27), dt.date(2027, 1, 1)):
            self.assertEqual(shared_digest(old, d), shared_digest(old, dt.date(2026, 9, 30)))   # its flips move nothing
        dec = [{"id": "d" * 16, "created": "2026-12-20T00:00:00+00:00", "data": b"{}"}]
        self.assertNotEqual(shared_digest(dec, dt.date(2026, 12, 31)), shared_digest(dec, dt.date(2027, 1, 1)))   # New Year: "December 20, 2026"
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); db = root / "corpus.db"
            TestBakeEdition._seed(db)
            bake.bake(str(db), str(root / "a"), "1.0.0", "https://x.org", shared=SHARED, today=TODAY)
            bake.bake(str(db), str(root / "b"), "1.0.0", "https://x.org", shared=SHARED, today=TODAY + 2 * day)
            key = lambda d: re.search(r"cz-record-[\w.-]+", (root / d / "sw.js").read_text()).group(0)
            self.assertNotEqual(key("a"), key("b"))                                                   # the worker's key moves with the day
            self.assertNotEqual((root / "a" / "index.html").read_bytes(), (root / "b" / "index.html").read_bytes())   # the strip seats the newer page
            self.assertIn("shared_hash", json.loads((root / "a" / "manifest.json").read_text()))       # a press with a store carries the digest
            bake.bake(str(db), str(root / "c"), "1.0.0", "https://x.org", today=TODAY)
            self.assertNotIn("shared_hash", json.loads((root / "c" / "manifest.json").read_text()))   # a desk manifest is what it was

    def test_the_share_hint_says_what_a_short_link_does(self):
        for token in ("⚡ short link — on the front pages after tonight’s press",
                      "A short link lists your page among the record’s front pages after the next nightly press, unsigned; a steward can take it down.",
                      "function bsGallery(", "nav.hidden = false;", 'window.addEventListener("hashchange", fromHash);',
                      'const take = from === "stored"', "a steward reads the ask, and a page taken down is gone at the next night’s press",
                      'minted.includes(location.search)', 'map(a => a.search)', 'if (r.status === 410) { copyText(paperShareURL(p), said + " — full link copied instead"); return; }'):
            self.assertIn(token, JS)
        self.assertIn("bsSpine(); bsScore(); bsYear(); bsRiver(); bsGallery();", JS)


if __name__ == "__main__":
    unittest.main()
