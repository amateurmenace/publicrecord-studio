"""The night, cut (specs/26 §2.1): the press's reels from one meeting's
moments — the loudest five in tape order, one reel per kind, in the
viewer's own link grammar."""

import json
import re
import shutil
import subprocess
import unittest
from pathlib import Path

from web import cuts

REPO = Path(__file__).resolve().parents[1]


def _moments():
    return [
        {"t": 100.0, "start": 96.0, "end": 118.0, "kind": "question", "score": 0.4, "quote": "how much"},
        {"t": 300.0, "start": 296.0, "end": 330.0, "kind": "vote", "score": 0.95, "quote": "the motion"},
        {"t": 500.0, "start": 497.0, "end": 520.0, "kind": "decision", "score": 0.7, "quote": "so decided"},
        {"t": 700.0, "start": 690.0, "end": 730.0, "kind": "tension", "score": 0.5, "quote": "I disagree"},
        {"t": 900.0, "start": 898.0, "end": 910.0, "kind": "question", "score": 0.45, "quote": "and why"},
        {"t": 1100.0, "start": 1090.0, "end": 1120.0, "kind": "vote", "score": 0.93, "quote": "the second motion"},
        {"t": 1300.0, "start": 1290.0, "end": 1310.0, "kind": "question", "score": 0.41, "quote": "when"},
    ]


class TestMeetingCuts(unittest.TestCase):
    def test_the_loudest_five_in_tape_order_and_one_reel_per_kind(self):
        d = cuts.meeting_cuts({"pid": "vid1", "moments": _moments()})
        self.assertEqual(d["n_moments"], 7)
        # the five loudest by score — the two votes, the decision, the pushback, the 0.45 question — in tape order
        self.assertEqual(d["loudest"]["n"], 5)
        self.assertEqual(d["loudest"]["url"], "/app/r?v=1&m=vid1&c=296-330,497-520,690-730,898-910,1090-1120")
        self.assertEqual(d["loudest"]["runtime"], 34 + 23 + 40 + 12 + 30)
        self.assertEqual([(k["kind"], k["n"], k["total"]) for k in d["kinds"]],
                         [("vote", 2, 2), ("decision", 1, 1), ("tension", 1, 1), ("question", 3, 3)])
        self.assertEqual(d["kinds"][3]["url"], "/app/r?v=1&m=vid1&c=96-118,898-910,1290-1310")
        self.assertEqual(d["kinds"][3]["clips"], 3)
        self.assertEqual(d["kinds"][0]["label"], "the roll calls")

    def test_overlapping_windows_play_once(self):
        """A vote and the decision seconds after it share tape: one clip,
        counted as two moments (a review catch: the night replayed itself)."""
        d = cuts.meeting_cuts({"pid": "p", "moments": [
            {"t": 12.0, "start": 0.0, "end": 40.0, "kind": "vote", "score": 0.9, "quote": "m"},
            {"t": 30.0, "start": 28.5, "end": 68.5, "kind": "decision", "score": 0.7, "quote": "d"},
            {"t": 100.0, "start": 96.0, "end": 110.0, "kind": "question", "score": 0.4, "quote": "q"}]})
        self.assertEqual(d["loudest"]["url"], "/app/r?v=1&m=p&c=0-68.5,96-110")
        self.assertEqual((d["loudest"]["n"], d["loudest"]["clips"], d["loudest"]["runtime"]), (3, 2, 82.5))

    def test_a_long_run_of_moments_stays_a_reel_of_clips(self):
        """Sixteen moments thirty seconds apart with forty-second windows
        would chain into one eight-minute clip; the supercut's cap keeps
        the night clip to clip (a re-review catch)."""
        run = [{"t": float(i * 30 + 10), "start": float(i * 30), "end": float(i * 30 + 40), "kind": "question",
                "score": 0.4, "quote": "q"} for i in range(16)]
        d = cuts.meeting_cuts({"pid": "p", "moments": run})
        q = d["kinds"][0]
        self.assertGreaterEqual(q["clips"], 5)
        self.assertEqual(q["n"], 16)
        from web import topic
        for c in cuts.clips_of("p", run):
            self.assertLessEqual(c["end"] - c["start"], topic.MERGE_CAP)

    def test_a_kind_reel_is_capped_and_says_so(self):
        many = [{"t": float(i * 60), "start": float(i * 60), "end": float(i * 60 + 10), "kind": "question",
                 "score": 0.4, "quote": "q"} for i in range(40)]
        d = cuts.meeting_cuts({"pid": "p", "moments": many})
        q = d["kinds"][0]
        self.assertEqual((q["n"], q["total"]), (cuts.KIND_CAP, 40))
        self.assertEqual(d["loudest"]["n"], 5)

    def test_no_moments_no_cut(self):
        self.assertIsNone(cuts.meeting_cuts({"pid": "p", "moments": []}))
        self.assertIsNone(cuts.meeting_cuts({"pid": "", "moments": _moments()}))
        # a moment without a window is its line and twelve seconds
        d = cuts.meeting_cuts({"pid": "p", "moments": [{"t": 10.0, "kind": "vote", "score": 0.9, "quote": "m"}]})
        self.assertEqual(d["loudest"]["url"], "/app/r?v=1&m=p&c=10-22")
        # an empty window is not a clip
        self.assertIsNone(cuts.meeting_cuts({"pid": "p", "moments": [{"t": 10.0, "start": 10.0, "end": 10.0, "kind": "vote"}]}))

    def test_the_links_decode_with_the_reader(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        js = (REPO / "web" / "static" / "app.js").read_text()
        lift = lambda pat: re.search(pat, js, re.S).group(0)
        helpers = "\n".join([lift(r"const r1 = .+?;"), lift(r"function decodeReel\(search\) \{.+?\n  \}")])
        d = cuts.meeting_cuts({"pid": "vid-1_x", "moments": _moments()})
        url = d["loudest"]["url"]
        body = "\n".join([helpers, f"const d = decodeReel({json.dumps(url[url.index('?'):])});", "console.log(JSON.stringify(d));"])
        r = subprocess.run([node, "-e", body], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual((got["v"], got["pid"], len(got["clips"])), ("1", "vid-1_x", 5))
        self.assertEqual(got["clips"][0], {"pid": "vid-1_x", "start": 296, "end": 330})



class TestMeetingCutAndFound(unittest.TestCase):
    """The meeting page (specs/26): the night cut, the words, the jump bar,
    the downloads; the front page's latest story closes with the night; the
    bodies filter sits beside the list it filters. Pressed, byte-clean."""

    @classmethod
    def setUpClass(cls):
        import tempfile
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.db = root / "corpus.db"
        cls._seed(cls.db)
        cls.out = root / "app"
        from web import bake
        bake.bake(str(cls.db), str(cls.out), "9.9.9", "https://example.org")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @staticmethod
    def _seed(db):
        from memory.store import Corpus
        c = Corpus(str(db))
        lines = ["we open the meeting on the budget", "the budget override is the item tonight",
                 "I move to approve the budget override", "all in favor say aye", "aye", "the motion passes",
                 "but I am concerned the budget leaves the schools short and I disagree with the timing",
                 "how much does the override raise for the schools this year", "we adjourn"]
        segs = [{"start": i * 10.0, "end": i * 10 + 9, "speaker": "", "text": t} for i, t in enumerate(lines)]
        c.replace_segments("vid1", segs)
        c.upsert_meeting({"id": "vid1", "title": "Select Board — March", "date": "2026-03-10",
                          "town": "Testville", "body": "Board", "source_kind": "youtube", "video_id": "vid1",
                          "url": "https://youtube.com/watch?v=vid1", "url_canon": "youtube:vid1",
                          "duration": 90.0, "n_segments": len(segs), "status": "live",
                          "summary": "A budget override was discussed.",
                          "analysis_json": json.dumps({"decisions": [{"t": 50.0, "text": "the motion passes", "outcome": "passed"}]})})
        c.replace_votes("vid1", [{"t": 20.0, "motion": "to approve the budget override", "outcome": "passes",
                                  "tally": "3–0", "origin": "extractive",
                                  "roll": [{"name": "Chair Alpha", "vote": "yes", "t": 40.0, "quote": "aye"}]}])

    def test_the_meeting_page_carries_the_night_cut_the_words_and_a_jump_bar(self):
        page = (self.out / "m" / "vid1" / "index.html").read_text()
        plane = json.loads((self.out / "meetings" / "vid1.json").read_text())
        self.assertTrue(plane["moments"], "the seed must score at least one moment")
        # the night, cut: the loudest reel and one per kind, as the viewer's own links
        self.assertIn('<section class="card mp-cut" id="cut">', page)
        self.assertIn('href="/app/r?v=1&amp;m=vid1&amp;c=', page)
        self.assertIn("▶ the night in ", page)
        self.assertIn('class="btn mp-kind"', page)
        self.assertIn("the roll calls", page)
        # the words: the cloud, each word a deep link into the tape
        self.assertIn('<section class="card mp-words" id="words">', page)
        self.assertIn('class="fp-cloud"', page)
        self.assertIn('<a href="#t', page[page.index('id="words"'):page.index('id="downloads"')])
        # the jump bar names only what the page has, in page order
        jump = page[page.index('class="mp-jump"'):page.index("</nav>", page.index('class="mp-jump"'))]
        for k in ("#tape", "#summary", "#cut", "#moments", "#votes", "#words", "#transcript", "#downloads"):
            self.assertIn(f'href="{k}"', jump)
        self.assertNotIn('href="#paper"', jump)          # no filings on this meeting
        self.assertIn('<div id="tape">', page)
        self.assertIn('<div class="tbar" id="downloads">', page)
        self.assertIn('href="/app/kits/vid1.json" download>kit .json', page)
        self.assertTrue((self.out / "kits" / "vid1.json").exists())   # the link is a file
        # content, not chrome: the pressed page holds no studio class, no script hooks
        body = page[page.index('class="mp-jump"'):page.index('id="transcript"')]
        for bad in ("cz-", "onclick", "#a855f7", "#7c3aed"):
            self.assertNotIn(bad, body)
        # the find box is the script's, never pressed (a pressed box that did nothing would lie)
        # the find box is pressed under the score now (specs/29 board 4): a
        # real form that searches the record without the script
        self.assertIn('<form class="mp-find bs-find" id="find" role="search" action="/app/s" method="get">', page)
        self.assertIn('id="score"', page)

    def test_a_taped_meeting_the_analyzer_scored_nothing_on_offers_no_kit(self):
        """The kit link stands only where a kit was pressed (video AND a
        moment) — a link that 404s is not a download (a review catch); and a
        meeting whose summary is a model's draft alone still has a summary
        jump that lands (a review catch)."""
        from web import emit, bake
        m = {"pid": "q1", "id": "q1", "title": "Quiet", "body": "Board", "town": "T", "date": "2026-03-10",
             "duration": 30.0, "video_id": "q1", "url": "u", "source_kind": "youtube", "origin": "", "n_segments": 1,
             "n_speakers": 0, "uploader": "", "summary": "", "summary_origin": "", "thumb": "", "tracks": [], "ad": False,
             "votes": [], "documents": [], "moments": [],
             "analysis": {"decisions": [], "topics": [], "entities": {}, "participation": [],
                          "framing": {"total": 0, "lenses": []}, "questions": [], "tension": [],
                          "draft": {"text": "Nothing moved at [0:05].", "origin": "ai:test"}},
             "segments": [{"start": 5.0, "end": 9.0, "speaker": "", "text": "we adjourn early tonight"}]}
        self.addCleanup(emit.set_edition, dict(emit._EDITION))
        emit.set_edition({"towns": [], "bodies": [], "untowned": 0})
        page = emit.page_meeting(m, {"version": "9.9.9", "edition_date": "2026-03-10"}, "https://example.org")
        self.assertNotIn("kit .json", page)
        self.assertNotIn('id="cut"', page)
        self.assertIn('<section class="card summary draft" id="summary">', page)
        self.assertIn('href="#summary">the reading</a>', page)
        self.assertNotIn('href="#cut"', page)

    def test_the_front_page_closes_the_latest_story_with_the_night(self):
        # the night's cut is the meeting page's (specs/26); the broadsheet's
        # front page opens on the tape itself, with Play from its loudest moment
        page = (self.out / "m" / "vid1" / "index.html").read_text()
        self.assertIn("▶ the night in ", page)
        self.assertIn('href="/app/r?v=1&amp;m=vid1&amp;c=', page)
        home = (self.out / "index.html").read_text()
        self.assertIn('class="bs-playfrom"', home)
        # the bodies filter sits in the week, beside the cards it filters
        self.assertLess(home.index('id="week"'), home.index('id="bodyfilter"'))
        self.assertLess(home.index('id="bodyfilter"'), home.index("bs-weekrow"))

    def test_the_reader_finds_in_the_meeting_and_names_the_keys(self):
        js = (REPO / "web" / "static" / "app.js").read_text()
        for fn in ("function wireFind()", "function mpFind(q)", "function mpTray()", "function wireKeys()", "function keysFor()"):
            self.assertIn(fn, js)
        boot = js[js.index('document.addEventListener("DOMContentLoaded"'):js.index("registerSW();")]
        self.assertIn("wireFind();", boot)
        self.assertIn("wireKeys();", js[js.index("registerSW();"):js.index("registerSW();") + 200])
        css = (REPO / "web" / "static" / "app.web.css").read_text()
        self.assertIn(".transcript.mp-finding .seg:not(.mp-hit){display:none}", css)
        self.assertIn(".kb-sheet{", css)
        for pop in ("#a855f7", "#7c3aed", "#22c55e"):
            self.assertNotIn(pop, css[css.index("the meeting, cut and found"):])

if __name__ == "__main__":
    unittest.main()
