"""Said alongside it (specs/29 board 6): the phrases said in the same breath
as an issue — counted on the press (web/beside.py), carried on the issue's
plane, pressed on the issue page, and rendered on a paper as a block of its
own (kind `beside`, part `e.<slug>`, v=6) whose chips are the press's, byte
for byte. Nothing is stored but a slug; nothing here calls a model."""

import json
import tempfile
import unittest
from pathlib import Path

from record.papers import PaperError, canonical
from tests.test_paper_store import portable
from tests.test_web_bake import TestBakeEdition
from web import beside, charts

SEGS = [{"start": 0, "text": "good evening everyone"},
        {"start": 5, "text": "the free cash balance is healthy"},
        {"start": 10, "text": "the housing trust fund and free cash again"},
        {"start": 15, "text": "affordable housing needs the trust fund"},
        {"start": 20, "text": "moving on to the water main"},
        {"start": 25, "text": "clears throat free cash"},
        {"start": 30, "text": ""}]                                   # a blank caption line is no line
ISSUE = {"name": "Housing trust fund", "aliases": ["the trust"], "keywords": ["housing trust"]}


class TestCounting(unittest.TestCase):
    def test_the_phrases_beside_an_issue_are_counted_once_per_line(self):
        """Every bead's line and the lines either side are the issue's breath;
        a line two beads touch is counted once; a phrase made only of the
        issue's own words is out, a stopword or an artifact is out, and only
        what came up twice is said."""
        meetings = {"m1": {"segments": SEGS}}
        skip = beside.own_words(ISSUE)
        self.assertEqual(skip, {"phrases": {"housing trust fund", "the trust", "housing trust"}, "tokens": {"housing", "trust", "fund"}})
        timeline = [{"meeting_id": "m1", "pid": "p1", "beads": [{"t": 10.0}, {"t": 15.0}]}]
        # the breath: lines 5, 10, 15, 20 (10 and 15 once each, though both beads touch them);
        # "housing trust" and "trust fund" are the issue's own name — out; "affordable housing"
        # shares a word with it and stays (once, so dropped by n > 1)
        self.assertEqual(beside.beside(timeline, meetings, skip), [{"phrase": "free cash", "n": 2, "meetings": 1}])
        twice = {"m1": {"segments": SEGS + [{"start": 35, "text": "affordable housing once more"}]}}
        got = beside.beside([{"meeting_id": "m1", "pid": "p1", "beads": [{"t": 15.0}, {"t": 35.0}]}], twice, skip)
        self.assertIn({"phrase": "affordable housing", "n": 2, "meetings": 1}, got)
        self.assertNotIn("trust fund", [g["phrase"] for g in got])
        # an alias is one of the issue's other names: out even when its words are not the name's —
        # while "trust fund", not this issue's name, now counts (its lines 10 and 15)
        other = [g["phrase"] for g in beside.beside([{"meeting_id": "m1", "pid": "p1", "beads": [{"t": 15.0}, {"t": 35.0}]}], twice,
                                                    beside.own_words({"name": "The fund", "aliases": ["affordable housing"]}))]
        self.assertNotIn("affordable housing", other)
        self.assertIn("trust fund", other)
        # a bead between two lines belongs to the line before it
        timeline = [{"meeting_id": "m1", "pid": "p1", "beads": [{"t": 12.0}]}]
        self.assertEqual(beside.beside(timeline, meetings, skip), [{"phrase": "free cash", "n": 2, "meetings": 1}])
        # a cough is not a word: "clears throat" never counts, the phrase beside it does
        timeline = [{"meeting_id": "m1", "pid": "p1", "beads": [{"t": 10.0}, {"t": 25.0}]}]
        got = beside.beside(timeline, meetings, skip)
        self.assertEqual(got[0], {"phrase": "free cash", "n": 3, "meetings": 1})
        self.assertNotIn("clears throat", [g["phrase"] for g in got])
        # a meeting the pressing lacks, a bead with no time or a time that is not a number, a node
        # that is not a dict: fewer phrases, never a throw — and never the tape's opening lines
        head = {"m1": {"segments": [{"start": 0, "text": "water main water main"}, {"start": 5, "text": "water main again"}] + SEGS[2:]}}
        odd = [{"meeting_id": "gone", "pid": "p9", "beads": [{"t": 1}]}, "junk",
               {"meeting_id": "m1", "beads": [{"x": 1}, None, {"t": "abc"}, {"t": True}, {"t": None}]}]
        self.assertEqual(beside.beside(odd, head, skip), [])
        self.assertEqual(beside.beside([{"meeting_id": "m1", "beads": [{"t": 0}]}], head, skip)[0]["phrase"], "water main")
        # a phrase never crosses a full stop, and a civic stopword is no phrase
        cut = {"m1": {"segments": [{"start": 0, "text": "we need it free. Cash flow matters, the select board voted"},
                                   {"start": 5, "text": "free. cash again; the select board voted again"}]}}
        got = beside.beside([{"meeting_id": "m1", "pid": "p1", "beads": [{"t": 0}]}], cut, set())
        self.assertEqual(got, [])                                                    # no "free cash", no "select board"

    def test_ranking_is_by_count_then_alphabet_and_the_cap_holds(self):
        segs = [{"start": i * 5, "text": f"zoning bylaw and water main and zoning bylaw"} for i in range(3)]
        meetings = {"m1": {"segments": segs}, "m2": {"segments": [{"start": 0, "text": "water main again water main"}]}}
        timeline = [{"meeting_id": "m1", "pid": "p1", "beads": [{"t": 5.0}]},
                    {"meeting_id": "m2", "pid": "p2", "beads": [{"t": 0.0}]}]
        got = beside.beside(timeline, meetings, set())
        self.assertEqual([(g["phrase"], g["n"], g["meetings"]) for g in got][:2],
                         [("zoning bylaw", 6, 1), ("water main", 5, 2)])
        self.assertEqual(beside.beside(timeline, meetings, set(), top=1), got[:1])
        # deterministic: the same input says the same twice, whatever the order of the timeline
        self.assertEqual(beside.beside(list(reversed(timeline)), meetings, set()), got)
        # the cache is shared across issues of one press and changes nothing
        prepared = {}
        self.assertEqual(beside.beside(timeline, meetings, set(), prepared=prepared), got)
        self.assertEqual(set(prepared), {"m1", "m2"})
        self.assertEqual(beside.beside(timeline, meetings, set(), prepared=prepared), got)


class TestChips(unittest.TestCase):
    def test_the_chips_link_each_phrase_into_the_issue_s_own_meetings(self):
        html = charts.beside_chips([{"phrase": "free cash", "n": 3, "meetings": 2}, {"phrase": "town's & budget", "n": 2, "meetings": 1}], ["p1", "p2"])
        self.assertIn('<a class="pb-chip" href="/app/s?q=free%20cash&amp;m=p1,p2" title="“free cash” in 2 meetings — search them"', html)
        self.assertIn('title="“town&#x27;s &amp; budget” in 1 meeting — search them"', html)
        # the search page reads 64 pids off m= — the chips name no more
        many = charts.beside_chips([{"phrase": "x y", "n": 2}], [f"p{i}" for i in range(70)])
        self.assertIn("&amp;m=" + ",".join(f"p{i}" for i in range(64)) + '"', many)
        self.assertNotIn("p64", many)
        self.assertIn('>free cash <span class="pb-chip-n">3</span></a>', html)
        self.assertIn("q=town's%20%26%20budget", html)                       # encodeURIComponent's own spelling
        self.assertIn("town&#x27;s &amp; budget <span", html)                # escaped for the page
        self.assertEqual(charts.beside_chips([], ["p1"]), "")
        self.assertEqual(charts.beside_chips([{"phrase": "", "n": 1}, "junk"], ["p1"]), "")
        self.assertNotIn("&amp;m=", charts.beside_chips([{"phrase": "x y", "n": 2}], []))   # no meetings: the whole record


class TestStoreAndPlane(unittest.TestCase):
    def test_the_store_keeps_a_slug_and_nothing_else(self):
        doc = json.loads(canonical(portable(blocks=[{"kind": "beside", "slug": "issue_brookline_x"}])))
        self.assertEqual(doc["blocks"], [{"kind": "beside", "slug": "issue_brookline_x"}])
        for bad in ({"kind": "beside", "slug": "has space"}, {"kind": "beside"},
                    {"kind": "beside", "slug": "issue_x", "phrases": ["free cash"]}):
            with self.assertRaises(PaperError):
                canonical(portable(blocks=[bad]))

    def test_the_issue_page_presses_the_chips_it_is_given(self):
        """The pressed issue page carries the chips exactly as charts spells
        them, and no card at all when nothing counted twice."""
        from web import emit
        doc = {"id": "issue:brookline:x", "slug": "issue_brookline_x", "name": "X", "name_origin": "", "status": "active",
               "aliases": [], "related": [], "keywords": [], "n_meetings": 1, "n_segments": 2, "first_seen": "2026-06-16",
               "last_seen": "2026-06-16", "timeline": [{"meeting_id": "m1", "pid": "vid1", "title": "T", "date": "2026-06-16",
               "body": "Board", "town": "Brookline", "video_id": "", "source_kind": "", "n": 0, "beads": [], "milestones": [], "documents": []}],
               "ledger": [], "beside": [{"phrase": "free cash", "n": 3, "meetings": 1}]}
        manifest = {"version": "1.0.0", "corpus_hash": "abc", "edition_date": "2026-06-16", "counts": {}}
        page = emit.page_issue(doc, manifest, "https://x.org")
        self.assertIn(charts.beside_chips(doc["beside"], ["vid1"], base="/app"), page)
        self.assertIn("said alongside it — the phrases in the same breath", page)
        self.assertIn("one of its other names, is left out", page)
        bare = emit.page_issue({**doc, "beside": []}, manifest, "https://x.org")
        self.assertNotIn("pb-chips", bare); self.assertNotIn("said alongside it", bare)

    def test_the_press_carries_the_phrases_on_the_issue_plane_and_the_page(self):
        from web import bake
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); db = root / "corpus.db"
            TestBakeEdition._seed(db)
            bake.bake(str(db), str(root / "out"), "1.0.0", "https://x.org")
            planes = sorted((root / "out" / "issues").glob("*.json"))
            planes = [p for p in planes if p.name != "index.json"]
            self.assertTrue(planes)
            for p in planes:
                doc = json.loads(p.read_text())
                self.assertIn("beside", doc)
                self.assertIsInstance(doc["beside"], list)
                for w in doc["beside"]:
                    self.assertEqual(set(w), {"phrase", "n", "meetings"})
                    self.assertGreater(w["n"], 1)
                page = (root / "out" / "i" / doc["slug"] / "index.html").read_text()
                chips = charts.beside_chips(doc["beside"], [n["pid"] for n in doc["timeline"]], base="/app")
                if chips:
                    self.assertIn(chips, page)
                    self.assertIn("said alongside it", page)
                else:
                    self.assertNotIn("pb-chips", page)


if __name__ == "__main__":
    unittest.main()
