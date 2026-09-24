"""A word, over time (specs/25) — the topic story: the engine, the pressed
story, the search page's twin, the reel links.

Offline and hermetic, like test_web_bake: a throwaway corpus with three
meetings that say the word (and one in another town that says it more
quietly), pressed to a temp dir. The JS twins are lifted from the reader by
regex and executed in node, the pattern TestReel set."""

import json
import re
import subprocess
import shutil
import tempfile
import unittest
from pathlib import Path

from web import topic

REPO = Path(__file__).resolve().parents[1]


class TestTopicEngine(unittest.TestCase):
    """The pure half: matching, merging, months, the link grammar."""

    def test_whole_word_matching_across_a_caption_break(self):
        pats = [topic.phrase_re("AI"), topic.phrase_re("artificial intelligence")]
        self.assertEqual(topic.mentions_in("the AI. AI, said aim", "", pats), 2)   # never "said", "aim"
        self.assertEqual(topic.mentions_in("it uses artificial", "intelligence cameras", pats), 1)
        self.assertEqual(topic.mentions_in("intelligence cameras", "", pats), 0)   # not counted twice
        self.assertEqual(topic.mentions_in("said", "AI next line", pats), 0)     # a match that starts after the line is the next line's

    def test_merge_windows_extends_a_run_and_caps_it(self):
        hits = [{"pid": "p", "t": 10.0}, {"pid": "p", "t": 15.0}, {"pid": "p", "t": 40.0}]
        clips = topic.merge_windows(hits, duration=44.0)
        self.assertEqual([(c["start"], c["end"], c["n"]) for c in clips], [(10.0, 27.0, 2), (40.0, 44.0, 1)])
        # a run longer than the cap breaks into a new clip; never past the tape
        run = [{"pid": "p", "t": float(t)} for t in range(0, 200, 5)]
        clips = topic.merge_windows(run, duration=150.0)
        self.assertTrue(all(c["end"] - c["start"] <= topic.MERGE_CAP for c in clips))
        self.assertTrue(all(c["end"] <= 150.0 for c in clips))
        self.assertEqual(topic.merge_windows([{"pid": "p", "t": 150.0}], duration=150.0), [])

    def test_month_range_is_contiguous(self):
        self.assertEqual(topic.month_range(["2025-12", "2026-03"]), ["2025-12", "2026-01", "2026-02", "2026-03"])
        self.assertEqual(topic.month_range([]), [])

    def test_a_malformed_date_is_undated_never_a_crash(self):
        """Dates enter the store as a submitter typed them; the story must
        not take the press down over "2026-1-5" (a review catch)."""
        self.assertEqual(topic.month_range(["2026-1-5", "2026-03", "x", "2026-13", ""]), ["2026-03"])
        meetings = [{"pid": "a", "title": "A", "date": "2026-1-5", "body": "B", "town": "T", "duration": 50.0},
                    {"pid": "b", "title": "B", "date": "2026-03-24", "body": "B", "town": "T", "duration": 50.0}]
        hits = [{"pid": "a", "t": 1.0, "text": "AI", "before": "", "after": "", "mentions": 1},
                {"pid": "a", "t": 9.0, "text": "AI", "before": "", "after": "", "mentions": 1},
                {"pid": "b", "t": 2.0, "text": "AI", "before": "", "after": "", "mentions": 1}]
        d = topic.aggregate(meetings, hits, {"slug": "ai", "phrases": ["AI"]})
        self.assertEqual([m["month"] for m in d["months"]], ["2026-03"])
        self.assertEqual(d["undated"], 1)
        # the undated night sorts last: the first word on the record is the
        # dated one — and so is the latest (a chronological claim)
        self.assertEqual((d["first"]["pid"], d["latest"]["pid"]), ("b", "b"))
        self.assertEqual(d["chapters"][-1]["pid"], "a")
        from web import charts
        tapes = charts.term_tapes(d["meetings"])
        self.assertIn('>undated · B</a>', tapes)
        self.assertNotIn('>ed · B</a>', tapes)
        self.assertIn("<label>?", charts.month_bars([{"month": "2026-1", "meetings": 1, "said": 1, "mentions": 1}], []))

    def test_an_untowned_meeting_never_leads_and_is_named_as_such(self):
        meetings = [{"pid": "u1", "title": "U", "date": "2026-02-01", "body": "B", "town": "", "duration": 50.0},
                    {"pid": "u2", "title": "U", "date": "2026-02-02", "body": "B", "town": "", "duration": 50.0},
                    {"pid": "t1", "title": "T", "date": "2026-03-01", "body": "B", "town": "Testville", "duration": 50.0},
                    {"pid": "t2", "title": "T", "date": "2026-03-02", "body": "B", "town": "Testville", "duration": 50.0}]
        hit = lambda pid, t: {"pid": pid, "t": t, "text": "AI", "before": "", "after": "", "mentions": 1}
        hits = [hit("u1", 1.0), hit("u1", 9.0), hit("u2", 1.0), hit("u2", 9.0), hit("u2", 20.0),
                hit("t1", 1.0), hit("t1", 9.0), hit("t2", 1.0)]
        d = topic.aggregate(meetings, hits, {"slug": "ai", "phrases": ["AI"]})
        self.assertEqual(d["town"], "Testville")             # the untowned five never lead
        self.assertEqual(d["elsewhere"], [{"town": "", "moments": 5, "meetings": 2}])
        self.assertIsNone(topic.aggregate(meetings[:2], hits[:5], {"slug": "ai", "phrases": ["AI"]}))
        from web import story
        html = story.topic(d, issues=[], examples=[])
        self.assertIn("meetings with no town recorded said it in 5 lines across 2 meetings", html)
        self.assertNotIn("’s bodies said it in 5 lines", html)

    def test_search_url_keeps_the_query_whole(self):
        from web import charts
        self.assertEqual(charts.search_url("Item #5 & Q+A", "Brookline"), "/app/s?q=Item%20%235%20%26%20Q%2BA&town=Brookline")
        self.assertEqual(topic.search_url("AI"), "/app/s?q=AI")

    def test_reel_url_is_the_viewers_grammar(self):
        one = topic.reel_url([{"pid": "a", "start": 1.0, "end": 13.0}, {"pid": "a", "start": 20.25, "end": 32.0}])
        self.assertEqual(one, "/app/r?v=1&m=a&c=1-13,20.3-32")
        two = topic.reel_url([{"pid": "a", "start": 1.0, "end": 13.0}, {"pid": "b-c_d", "start": 2.55, "end": 14.0}])
        self.assertEqual(two, "/app/r?v=2&c=a:1-13,b-c_d:2.6-14")
        self.assertEqual(topic.reel_url([]), "")

    def _fixture(self):
        meetings = [
            {"pid": "m1", "title": "Board — Dec", "date": "2025-12-09", "body": "Board", "town": "Testville", "duration": 120.0},
            {"pid": "m2", "title": "Board — Jan", "date": "2026-01-13", "body": "Board", "town": "Testville", "duration": 120.0},
            {"pid": "m3", "title": "Board — Mar", "date": "2026-03-24", "body": "Board", "town": "Testville", "duration": 700.0},
            {"pid": "m4", "title": "School — Mar", "date": "2026-03-30", "body": "School", "town": "Testville", "duration": 200.0},
            {"pid": "x1", "title": "Council", "date": "2026-02-02", "body": "Council", "town": "Otherton", "duration": 100.0},
        ]
        hits = [
            {"pid": "m1", "t": 30.0, "text": "how quickly AI is developing", "before": "frankly", "after": "and the policy", "mentions": 1},
            {"pid": "m3", "t": 500.0, "text": "the AI use policy", "before": "so", "after": "and AI agents", "mentions": 1},
            {"pid": "m3", "t": 505.0, "text": "and AI agents", "before": "the AI use policy", "after": "for the policy", "mentions": 1},
            {"pid": "m3", "t": 600.0, "text": "zoom AI companion", "before": "", "after": "", "mentions": 1},
            {"pid": "m4", "t": 10.0, "text": "AI and digital literacy", "before": "", "after": "policy", "mentions": 1},
            {"pid": "x1", "t": 5.0, "text": "AI literacy", "before": "", "after": "", "mentions": 1},
        ]
        return meetings, hits

    def test_aggregate_counts_the_story(self):
        meetings, hits = self._fixture()
        d = topic.aggregate(meetings, hits, {"slug": "ai", "name": "AI", "q": "AI", "phrases": ["AI"]})
        self.assertEqual(d["town"], "Testville")
        self.assertEqual((d["moments"], d["mentions"], d["n_meetings"], d["n_town_meetings"]), (5, 5, 3, 4))
        self.assertEqual([m["month"] for m in d["months"]], ["2025-12", "2026-01", "2026-02", "2026-03"])
        self.assertEqual([(m["meetings"], m["said"], m["mentions"]) for m in d["months"]],
                         [(1, 1, 1), (1, 0, 0), (0, 0, 0), (2, 2, 4)])
        self.assertEqual(d["first"]["pid"], "m1"); self.assertEqual(d["latest"]["pid"], "m4")
        self.assertEqual((d["peak"]["pid"], d["peak"]["n"], d["peak"]["span"]), ("m3", 3, 100.0))
        self.assertEqual(d["gap"], 1)                       # January passed without it
        self.assertEqual(d["elsewhere"], [{"town": "Otherton", "moments": 1, "meetings": 1}])
        self.assertEqual([b["body"] for b in d["bodies"]], ["Board", "School"])
        self.assertEqual(d["cowords"][0], {"word": "policy", "count": 5})
        self.assertEqual([c["pid"] for c in d["chapters"]], ["m1", "m3", "m4"])
        # the supercut: one clip per night; the full cut merges the run at 500/505
        self.assertEqual(d["reel"]["short_n"], 3)
        self.assertEqual(d["reel"]["full_n"], 4)
        self.assertEqual(d["reel"]["full"], "/app/r?v=2&c=m1:30-42,m3:500-517,m3:600-612,m4:10-22")
        # the floor: a word said once is not a story
        self.assertIsNone(topic.aggregate(meetings, hits[:1], {"slug": "ai", "phrases": ["AI"]}))
        # pinned to the other town, no floor: its own story
        o = topic.aggregate(meetings, hits, {"slug": "ai", "phrases": ["AI"]}, town="Otherton", floor=False)
        self.assertEqual((o["town"], o["moments"]), ("Otherton", 1))


class TestTopicTwins(unittest.TestCase):
    """The reader's tpAggregate answers what the press's aggregate answers on
    the same (meetings, hits) — and the press's reel links decode with the
    reader's own decodeReel."""

    JS = (REPO / "web" / "static" / "app.js").read_text()
    PRELUDE = "\n".join([
        'const BASE = "/app";',
        'const location = { origin: "" };',
    ])

    def node(self, body):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        return subprocess.run([node, "-e", body], capture_output=True, text=True)

    def lift(self, pattern):
        m = re.search(pattern, self.JS, re.S)
        self.assertTrue(m, f"{pattern!r} not found in the reader — did it move?")
        return m.group(0)

    def helpers(self):
        return "\n".join([
            self.lift(r"const hms = t => \{.+?\};"),
            self.lift(r"const REEL_V = .+?;"),
            self.lift(r"const r1 = .+?;"),
            self.lift(r"const encodeClips = .+?;"),
            self.lift(r"const encodeClipsX = .+?;"),
            self.lift(r"const REEL_LINK_CAP = .+?;"),
            self.lift(r"function shareURL\(pid, clips\) \{.+?\n  \}"),
            self.lift(r"function reelShareURL\(clips\) \{.+?\n  \}"),
            self.lift(r"function decodeReel\(search\) \{.+?\n  \}"),
            self.lift(r"const TP_WINDOW = .+?;"),
            self.lift(r"const TP_FLOOR_LINES = .+?;"),
            self.lift(r"const tpSpread = .+?\n  \};"),
            self.lift(r"const tpCapSpread = .+?\n  \};"),
            self.lift(r"const phraseRe = .+?;\n"),
            self.lift(r"function mentionsIn\(text, after, pats\) \{.+?\n  \}"),
            self.lift(r"const TP_MONTH = .+?;\n"),
            self.lift(r"const tpIsMonth = .+?;\n"),
            self.lift(r"const tpMonthRange = .+?\n  \};"),
            self.lift(r"const tpCutWords = .+?\n  \};"),
            self.lift(r"const tpContext = .+?;\n"),
            self.lift(r"function tpMerge\(hits, duration\) \{.+?\n  \}"),
            self.lift(r"const TP_STOP = .+?;\n"),
            self.lift(r"const TP_ART = .+?;\n"),
            self.lift(r"const tpStopish = .+?\n  \};"),
            self.lift(r"function tpCowords\(hits, phrases, top\) \{.+?\n  \}"),
            self.lift(r"function tpAggregate\(meetings, hits, topic, town, floor\) \{.+?\n  \}"),
        ])

    def test_the_count_is_one_count_in_python_and_the_reader(self):
        meetings, hits = TestTopicEngine()._fixture()
        t = {"slug": "ai", "name": "AI", "q": "AI", "phrases": ["AI"]}
        py = topic.aggregate(meetings, hits, t)
        keep = ("town", "moments", "mentions", "n_meetings", "n_town_meetings", "months", "bodies",
                "first", "latest", "peak", "gap", "elsewhere", "cowords", "chapters", "reel")
        want = {k: py[k] for k in keep}
        want["clips"] = [c for r in py["meetings"] for c in r["clips"]]
        want["bins"] = [r["bins"] for r in py["meetings"]]
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            f"const meetings = {json.dumps(meetings)}; const hits = {json.dumps(hits)};",
            f"const d = tpAggregate(meetings, hits, {json.dumps(t)}, '', true);",
            f"const keep = {json.dumps(keep)};",
            "const out = {}; for (const k of keep) out[k] = d[k];",
            "out.clips = [].concat(...d.meetings.map(r => r.clips)); out.bins = d.meetings.map(r => r.bins);",
            "console.log(JSON.stringify(out));",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0, f"tpAggregate threw:\n{r.stdout}{r.stderr}")
        got = json.loads(r.stdout.strip().splitlines()[-1])
        # numbers compare as numbers (python floats vs js), lists in order
        self.assertEqual(json.loads(json.dumps(want)), got)

    def test_the_readers_word_lists_are_the_presss(self):
        """tpStopish and TP_ART must drop exactly what the press drops, or
        the live co-words differ from the pressed ones (a review catch:
        "councilor" was missing from the reader's set)."""
        from highlighter.insight import STOPWORDS
        from web.charts import ARTIFACTS
        stop = self.lift(r'const TP_STOP = new Set\(\("(.+?)"\)\.split\(" "\)\);')
        words = set(re.search(r'"(.+?)"', stop).group(1).split(" "))
        self.assertEqual(words, STOPWORDS)
        art = self.lift(r"const TP_ART = new Set\((\[.+?\])\);")
        self.assertEqual(set(json.loads(re.search(r"(\[.+\])", art).group(1))), ARTIFACTS)

    def test_the_count_agrees_on_the_edges_too(self):
        """An undated night, an untowned meeting, a tape of no length, an
        artifact beside the word, a tie — the same answer from both twins."""
        meetings = [
            {"pid": "m1", "title": "Board — Dec", "date": "2025-12-09", "body": "Board", "town": "Testville", "duration": 0},
            {"pid": "m2", "title": "Board — ?", "date": "2026-1-5", "body": "Board", "town": "Testville", "duration": 120.0},
            {"pid": "m3", "title": "Board — Mar", "date": "2026-03-24", "body": "Board", "town": "Testville", "duration": 700.0},
            {"pid": "u1", "title": "No town", "date": "2026-02-02", "body": "Council", "town": "", "duration": 100.0},
        ]
        hits = [
            {"pid": "m1", "t": 30.0, "text": "AI councilor policy", "before": "", "after": "", "mentions": 1},
            {"pid": "m2", "t": 5.0, "text": "AI policy", "before": "", "after": "policy", "mentions": 1},
            {"pid": "m3", "t": 500.0, "text": "the AI use policy", "before": "so", "after": "and AI agents", "mentions": 1},
            {"pid": "m3", "t": 505.0, "text": "and AI agents", "before": "the AI use policy", "after": "", "mentions": 1},
            {"pid": "u1", "t": 5.0, "text": "AI literacy", "before": "", "after": "", "mentions": 1},
        ]
        t = {"slug": "ai", "name": "AI", "q": "AI", "phrases": ["AI"]}
        py = topic.aggregate(meetings, hits, t)
        self.assertEqual(py["town"], "Testville")
        self.assertEqual(py["elsewhere"], [{"town": "", "moments": 1, "meetings": 1}])
        self.assertEqual([m["month"] for m in py["months"]], ["2025-12", "2026-01", "2026-02", "2026-03"])
        self.assertEqual(py["undated"], 1)
        self.assertEqual((py["first"]["pid"], py["latest"]["pid"]), ("m1", "m3"))   # the undated night is last, and never "the latest"
        self.assertNotIn("councilor", [w["word"] for w in py["cowords"]])
        keep = ("town", "moments", "mentions", "n_meetings", "n_town_meetings", "months", "bodies",
                "first", "latest", "peak", "gap", "elsewhere", "cowords", "chapters", "reel", "undated")
        want = {k: py[k] for k in keep}
        want["clips"] = [c for r in py["meetings"] for c in r["clips"]]
        want["bins"] = [r["bins"] for r in py["meetings"]]
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            f"const meetings = {json.dumps(meetings)}; const hits = {json.dumps(hits)};",
            f"const d = tpAggregate(meetings, hits, {json.dumps(t)}, '', true);",
            f"const keep = {json.dumps(keep)};",
            "const out = {}; for (const k of keep) out[k] = d[k];",
            "out.clips = [].concat(...d.meetings.map(r => r.clips)); out.bins = d.meetings.map(r => r.bins);",
            "console.log(JSON.stringify(out));",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0, f"tpAggregate threw:\n{r.stdout}{r.stderr}")
        self.assertEqual(json.loads(json.dumps(want)), json.loads(r.stdout.strip().splitlines()[-1]))

    def test_mentions_in_agrees_across_the_caption_break(self):
        cases = [("it uses artificial", "intelligence cameras"), ("intelligence cameras", ""),
                 ("the AI. AI, said aim", ""), ("said", "AI next"), ("A.I. and ai-driven", "")]
        pats = [topic.phrase_re("AI"), topic.phrase_re("artificial intelligence")]
        want = [topic.mentions_in(a, b, pats) for a, b in cases]
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "const pats = ['AI', 'artificial intelligence'].map(phraseRe);",
            f"console.log(JSON.stringify({json.dumps(cases)}.map(([a, b]) => mentionsIn(a, b, pats))));",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout.strip().splitlines()[-1]), want)

    def test_the_pressed_reel_links_decode_with_the_reader(self):
        clips = [{"pid": "zao1HCiJNr4", "start": 14479.0, "end": 14491.0},
                 {"pid": "-QALuuia_bE", "start": 6466.25, "end": 6478.0},
                 {"pid": "-QALuuia_bE", "start": 9260.0, "end": 9302.4}]
        url2 = topic.reel_url(clips)
        url1 = topic.reel_url(clips[1:])
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            f"const a = decodeReel({json.dumps(url2[url2.index('?'):])});",
            f"const b = decodeReel({json.dumps(url1[url1.index('?'):])});",
            "console.log(JSON.stringify([a, b]));",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0, r.stderr)
        a, b = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(a["v"], "2")
        self.assertEqual([(c["pid"], c["start"], c["end"]) for c in a["clips"]],
                         [("zao1HCiJNr4", 14479, 14491), ("-QALuuia_bE", 6466.3, 6478), ("-QALuuia_bE", 9260, 9302.4)])
        self.assertEqual((b["v"], b["pid"], len(b["clips"])), ("1", "-QALuuia_bE", 2))


class TestTopicPress(unittest.TestCase):
    """The story, pressed: the front page leads with it, its own page stands,
    its plane is written, and the laws hold (byte-clean, receipts, counted)."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.db = root / "corpus.db"
        cls._seed(cls.db)
        cls.out = root / "app"
        from web import bake
        cls.report = bake.bake(str(cls.db), str(cls.out), "9.9.9", "https://example.org")
        cls.home = (cls.out / "index.html").read_text()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @staticmethod
    def _seed(db):
        from memory.store import Corpus
        c = Corpus(str(db))
        lines = {
            "t1": ["we open the meeting", "frankly with how quickly AI is developing", "the budget is next",
                   "the road repair item", "adjourned"],
            "t2": ["we open the meeting", "the parking study", "the road repair item", "adjourned", "goodnight"],
            "t3": ["the AI use policy and the security policy", "we added an AI section", "zoom AI companion was not useful",
                   "the budget is next", "artificial", "intelligence cameras were asked about", "adjourned"],
            "t4": ["the school opens", "AI and digital literacy", "the budget", "adjourned", "goodnight"],
            "x1": ["the council opens", "AI literacy programming", "AI literacy again", "AI basics", "adjourned"],
        }
        dates = {"t1": "2025-12-09", "t2": "2026-01-13", "t3": "2026-03-24", "t4": "2026-03-30", "x1": "2026-02-02"}
        for mid, ls in lines.items():
            segs = [{"start": i * 10.0, "end": i * 10 + 9, "speaker": "", "text": t} for i, t in enumerate(ls)]
            c.replace_segments(mid, segs)
            town = "Otherton" if mid.startswith("x") else "Testville"
            body = "Council" if mid.startswith("x") else ("School Committee" if mid == "t4" else "Select Board")
            c.upsert_meeting({"id": mid, "title": f"{body} — {dates[mid]}", "date": dates[mid],
                              "town": town, "body": body, "source_kind": "youtube", "video_id": mid,
                              "url": f"https://youtube.com/watch?v={mid}", "url_canon": f"youtube:{mid}",
                              "duration": 10.0 * len(ls), "n_segments": len(segs), "status": "live",
                              "summary": "A meeting.", "analysis_json": json.dumps({"decisions": []})})
        c.upsert_issue({"id": "issue:testville:artificial-intelligence", "town": "Testville",
                        "name": "Artificial Intelligence", "status": "active",
                        "keywords": ["artificial intelligence", "ai"], "aliases": ["AI"], "related": []})
        rows = c.segments_of("t3")
        c.link_segments("issue:testville:artificial-intelligence", [(r["id"], "t3", 1.0, "alias") for r in rows[:3]])

    def test_the_front_page_leads_with_the_word_over_time(self):
        """specs/25 on the broadsheet (specs/29): the featured word leads the
        Threads section — its card first, its search and its own page linked
        — and the story itself is pressed whole on that page."""
        home = self.home
        threads = home[home.index('id="threads"'):home.index("</section>", home.index('id="threads"'))]
        first = threads[threads.index('<article class="bs-thread">'):threads.index("</article>")]
        self.assertIn('class="bs-thread-name" href="/app/s?q=AI&amp;town=Testville"', first)
        self.assertIn('href="/app/topic/ai/"', first)
        page = (self.out / "topic" / "ai" / "index.html").read_text()
        home = page
        story = home[home.index('id="topic-ai"'):home.index('</article>', home.index('id="topic-ai"'))]
        self.assertIn("How Testville talks about AI", story)
        # the lede, counted: the first word, the silent meeting, the peak, the total, the latest, elsewhere
        self.assertIn('The first time anyone said “AI” on Testville’s record was <a href="/app/m/t1#t10">December 9, 2025</a>, 0:10 into a Select Board meeting', story)
        self.assertIn("The next meeting passed without it.", story)
        self.assertIn('It peaked on <a href="/app/m/t3#t0">March 24, 2026</a>, when the Select Board said it 4 times in under two minutes', story)
        self.assertIn('<a href="/app/s?q=AI&amp;town=Testville">6 mentions</a> across 3 of Testville’s <a href="/app/s">4 meetings</a>', story)
        self.assertIn("by the Select Board and the School Committee", story)
        self.assertIn('The latest was <a href="/app/m/t4#t10">March 30, 2026</a>', story)
        self.assertIn("Otherton’s bodies said it in 3 lines across 1 meeting", story)
        # every picture, in the paper palette, with its twin
        for kicker in ("“AI”, by the numbers", "mentions, month by month", "where it fell", "the words beside it",
                       "the first time it came up, each night", "the supercut", "make one of these"):
            self.assertIn(kicker, story, f"the topic story lost '{kicker}'")
        self.assertIn('class="tp-months"', story)
        self.assertIn('class="tp-dot on"', story)
        self.assertIn('<a class="tp-mcol" href="/app/m/t1#t10"', story)          # a bar is a receipt
        self.assertIn('class="fp-sparks tp-tapes"', story)
        self.assertIn('href="/app/s?q=AI%20policy&amp;town=Testville"', story)   # a co-word searches the pair, encoded whole
        self.assertIn('the same, as a table', story)
        # the chapters carry what a tick needs, and no button of their own
        self.assertIn('<a class="tq" href="/app/m/t3#t0" data-pid="t3" data-t="0"', story)
        self.assertIn("4 lines that night", story)
        # the supercut is the viewer's own link: one clip per night, and the full cut
        # (the first night's clip is its run: the hits at 0, 10 and 20 merge to one 32-second cut)
        self.assertIn('href="/app/r?v=2&amp;c=t1:10-22,t3:0-32,t4:10-22">▶ play the supercut', story)
        self.assertIn('href="/app/r?v=2&amp;c=t1:10-22,t3:0-32,t3:40-52,t4:10-22">the full cut — 4 clips', story)
        # a number's receipt is escaped once, not twice
        self.assertIn('<a class="ln" href="/app/s?q=AI&amp;town=Testville"><b>6</b><span>mentions</span></a>', story)
        self.assertNotIn("&amp;amp;", story)
        self.assertIn("the full cut — 4 clips", story)
        # the close: the search itself, the story's own page, the thread the record tracks
        self.assertIn('href="/app/s?q=AI&amp;town=Testville">search “AI” yourself →', story)
        self.assertIn('href="/app/">← the record’s front page', story)   # on its own page the close leads home
        self.assertIn('href="/app/i/issue_testville_artificial-intelligence">the thread the record tracks: Artificial Intelligence →', story)
        # the laws: counted, never modeled — and byte-clean of the studio
        self.assertIn("no model wrote a line of it", story)
        for bad in ("cz-", "#a855f7", "#7c3aed", "#d946ef", "<button", "onclick"):
            self.assertNotIn(bad, story, f"{bad!r} in the pressed story")

    def test_the_story_has_its_own_page_and_its_plane(self):
        page = (self.out / "topic" / "ai" / "index.html").read_text()
        self.assertIn("<title>How Testville talks about AI — publicrecord.studio</title>", page)
        self.assertIn("How Testville talks about AI", page)
        self.assertIn('href="/app/">← the record’s front page', page)
        self.assertNotIn("this story’s own page", page)
        for bad in ("cz-", "<button", "onclick"):
            body = page[page.index('id="topic-ai"'):page.index("</article>")]
            self.assertNotIn(bad, body)
        plane = json.loads((self.out / "topics" / "ai.json").read_text())
        # six lines say it — "artificial" / "intelligence cameras" broke across two, and counts once
        self.assertEqual((plane["town"], plane["moments"], plane["mentions"], plane["n_meetings"]), ("Testville", 6, 6, 3))
        idx = json.loads((self.out / "topics" / "index.json").read_text())
        self.assertEqual(idx, [{"slug": "ai", "name": "AI", "q": "AI", "town": "Testville",
                                "phrases": ["AI", "artificial intelligence"], "mentions": 6, "n_meetings": 3}])
        # the search index carries each tape's length now (the live story's clip cap)
        meta = json.loads((self.out / "search" / "meta.json").read_text())
        self.assertEqual({m["pid"]: m["duration"] for m in meta}["t3"], 70.0)

    def test_the_search_for_a_featured_word_counts_what_its_story_counts(self):
        """The live front page's "80 mentions" opened a search that said 73: the
        pressed story counts AI or artificial intelligence, the search counted
        the word typed (specs/27 §2.3). Now the search page reads the featured
        words' phrases from topics/index.json and gathers their lines by the
        press's own rule — executed here over the pressed index itself: the
        story's six lines (one of them broken across a caption, "artificial" /
        "intelligence cameras") are the search's six."""
        tw = TestTopicTwins()
        js = tw.JS
        lift = tw.lift
        body = "\n".join([
            tw.PRELUDE, tw.helpers(),
            "const fs = require('fs');",
            f"const OUT = {json.dumps(str(self.out))};",
            "const getJSON = async u => { try { return JSON.parse(fs.readFileSync(OUT + u.slice(4), 'utf8')); } catch (e) { return null; } };",
            "let SCOPE = { town: '', body: '' };",
            lift(r"const inScope = \(town, body\) =>.+?;\n"),
            lift(r"  function sqHits\(idx, ids, phrases\) \{.+?\n  \}"),
            lift(r"  async function sqIds\(idx, terms, q\) \{.+?\n  \}"),
            lift(r"  async function sqFeatured\(q\) \{.+?\n  \}"),
            lift(r"  async function sqPhraseIds\(idx, phrases\) \{.+?\n  \}"),
            "(async () => {",
            "  const idx = { meta: await getJSON('/app/search/meta.json'), segs: await getJSON('/app/search/segs.json') };",
            "  const meetings = idx.meta.map(m => ({ pid: m.pid, title: m.title, date: m.date, body: m.body, town: m.town, duration: +m.duration || 0 }));",
            "  const count = async (q, feat) => { const ph = feat ? feat.phrases : [q];",
            "    const ids = feat ? await sqPhraseIds(idx, ph) : await sqIds(idx, (q.toLowerCase().match(/[a-z0-9]+/g) || []), q);",
            "    const d = tpAggregate(meetings, sqHits(idx, ids, ph), { slug: '', name: q, q, phrases: ph }, '', false);",
            "    return [d.town, d.moments, d.mentions, d.n_meetings]; };",
            "  const feat = await sqFeatured('ai');",
            "  console.log(JSON.stringify({ feat, featured: await count('AI', feat), typed: await count('AI', null),",
            "    other: await sqFeatured('parking') }));",
            "})().catch(e => { console.log('THREW ' + e.stack); process.exit(1); });",
        ])
        r = tw.node(body)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        got = json.loads(r.stdout.strip().splitlines()[-1])
        plane = json.loads((self.out / "topics" / "ai.json").read_text())
        self.assertEqual(got["featured"], [plane["town"], plane["moments"], plane["mentions"], plane["n_meetings"]])
        self.assertEqual(got["feat"]["phrases"], ["AI", "artificial intelligence"])
        self.assertEqual(got["feat"]["terms"], ["ai", "artificial", "intelligence"])
        # the word alone misses the line the phrase broke across — the old 73
        self.assertEqual(got["typed"][1], plane["moments"] - 1)
        self.assertIsNone(got["other"])
        # and the page says which words it counted, pointing at the pressed story
        self.assertIn("the words <a href=\"${BASE}/topic/${encodeURIComponent(feat.slug)}/\">the front page’s story</a> counts", js)

    def test_the_full_cut_is_capped_under_a_hosts_url_limit_in_both_twins(self):
        """Housing's full cut was 320 clips and a 7,322-character link — GitHub
        Pages' CDN refuses past 8 KB (a review catch). Both twins cap it, and
        the capped cut is spread from the first night to the latest — "the
        first 120 of 623" never reached the latest nights of a word over time
        (a re-review catch). Executed in both, the same clips and links."""
        meetings = [{"pid": f"p{i:03d}", "title": "T", "date": f"2026-{1 + i % 9:02d}-{1 + i % 27:02d}", "body": "Select Board",
                     "town": "Testville", "duration": 5000.0} for i in range(150)]
        hits = [{"pid": m["pid"], "t": 100.0 * k, "text": "housing", "before": "", "after": "", "mentions": 1}
                for m in meetings for k in (1, 5)]
        t = {"slug": "h", "name": "housing", "q": "housing", "phrases": ["housing"]}
        d = topic.aggregate(meetings, hits, t)
        self.assertEqual((d["reel"]["full_n"], d["reel"]["full_all"]), (topic.FULL_CAP, 300))
        self.assertLess(len(d["reel"]["full"]), 6000)
        every = [c for r in d["meetings"] if r["n"] for c in r["clips"]]
        full = topic.spread(every, topic.FULL_CAP)
        self.assertEqual((full[0], full[-1]), (every[0], every[-1]))   # first to latest
        tw = TestTopicTwins()
        body = "\n".join([
            tw.PRELUDE, tw.helpers(),
            f"const meetings = {json.dumps(meetings)}; const hits = {json.dumps(hits)};",
            f"const d = tpAggregate(meetings, hits, {json.dumps(t)}, '', true);",
            "console.log(JSON.stringify([d.reel.full, d.reel.full_n, d.reel.full_all, d.reel.short, d.reel.short_n]));",
        ])
        r = tw.node(body)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout.strip().splitlines()[-1]),
                         [d["reel"]["full"], d["reel"]["full_n"], d["reel"]["full_all"], d["reel"]["short"], d["reel"]["short_n"]])
        story = (REPO / "web" / "story.py").read_text()
        self.assertIn("first to latest", story)
        # past the link's cap the pressed supercut says it is not every night
        self.assertIn("nights, one clip each, first to latest' if nights > reel[\"short_n\"]", story)

    def test_every_reel_link_stays_under_the_hosts_limit(self):
        """A link past ~8 KB is a dead page (414): the reader's reelShareURL
        and the press's reel_url hold at most the same number of clips, the
        spread picks the same clips in both, and the trays say when a link
        plays fewer than they hold."""
        clips = [{"pid": f"vid{i % 7:08d}", "start": 10.0 * i, "end": 10.0 * i + 12} for i in range(400)]
        py = topic.reel_url(clips)
        self.assertLess(len(py), 8000)
        items = list(range(1000))
        want = [topic.spread(items, k) for k in (0, 1, 2, 3, 120, 999, 1000, 1001)]
        tw = TestTopicTwins()
        body = "\n".join([
            tw.PRELUDE, tw.helpers(),
            f"const clips = {json.dumps(clips)};",
            "const items = Array.from({ length: 1000 }, (_, i) => i);",
            "console.log(JSON.stringify([reelShareURL(clips), [0, 1, 2, 3, 120, 999, 1000, 1001].map(k => tpSpread(items, k))]));",
        ])
        r = tw.node(body)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got, [py, want])
        self.assertEqual(topic.LINK_CAP, int(re.search(r"const REEL_LINK_CAP = (\d+);", TestTopicTwins.JS).group(1)))
        js = TestTopicTwins.JS
        self.assertEqual(js.count("a link plays the first ${REEL_LINK_CAP}"), 2)
        tray = js[js.index("function sqTray("):js.index("async function search()")]
        self.assertIn("tpCapSpread(clips, dated, TP_FULL_CAP)", tray)
        story = js[js.index("async function sqStory("):js.index("function sqTray(")]
        self.assertIn('✂ put ${d.reel.full_all > TP_FULL_CAP ? `${TP_FULL_CAP} of ${tpN(d.reel.full_all, "clip")}` : "every clip"} on my tray', story)
        panel = js[js.index("function refreshReelSummary("):]
        self.assertIn("the first ${REEL_LINK_CAP} of ${n} clips", panel[:panel.index("\n  }\n")])

    def test_the_latest_night_is_the_last_of_a_capped_cut_even_with_an_undated_one(self):
        """Undated nights sort last, so the spread's last pick was the undated
        night — "first to latest" left out the night the story calls the
        latest (a second re-review's catch). The dated nights are spread
        first to latest, the undated take the room left, in both twins."""
        meetings = [{"pid": f"p{i:03d}", "title": "T", "date": f"2025-{1 + i % 12:02d}-{1 + i // 12:02d}", "body": "Board",
                     "town": "Testville", "duration": 9000.0} for i in range(60)]
        meetings.append({"pid": "tbd", "title": "T", "date": "TBD", "body": "Board", "town": "Testville", "duration": 9000.0})
        latest = max(meetings[:60], key=lambda m: m["date"])
        hits = [{"pid": m["pid"], "t": 100.0 * k, "text": "housing", "before": "", "after": "", "mentions": 1}
                for m in meetings for k in (range(1, 2) if m is latest else range(1, 11))]
        t = {"slug": "h", "name": "housing", "q": "housing", "phrases": ["housing"]}
        d = topic.aggregate(meetings, hits, t)
        self.assertEqual(d["latest"]["pid"], latest["pid"])
        tw = TestTopicTwins()
        body = "\n".join([
            tw.PRELUDE, tw.helpers(),
            f"const meetings = {json.dumps(meetings)}; const hits = {json.dumps(hits)};",
            f"const d = tpAggregate(meetings, hits, {json.dumps(t)}, '', true);",
            "const pids = decodeReel(new URL(d.reel.full, 'http://x').search).clips.map(c => c.pid);",
            "console.log(JSON.stringify([d.reel.full, pids[pids.length - 1], d.reel.short]));",
        ])
        r = tw.node(body)
        self.assertEqual(r.returncode, 0, r.stderr)
        js_full, last_pid, js_short = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual([js_full, js_short], [d["reel"]["full"], d["reel"]["short"]])
        self.assertEqual(last_pid, latest["pid"])                       # the latest dated night closes the cut
        self.assertNotIn("tbd", d["reel"]["full"])
        self.assertEqual(topic.cap_spread(list("abcde"), [True, False, True, True, False], 3), ["a", "c", "d"])
        self.assertEqual(topic.cap_spread(list("abcde"), [True, False, False, True, False], 4), ["a", "d", "b", "c"])

    def test_a_blank_caption_line_is_no_line_as_the_index_reads_it(self):
        """The index skips blank lines; the press now does too, so a phrase a
        blank line splits is one line in both (a review catch)."""
        m = {"pid": "b", "segments": [{"start": 0.0, "text": "we use artificial"}, {"start": 3.0, "text": "  "},
                                      {"start": 5.0, "text": "intelligence cameras"}]}
        hits = topic.find_hits(m, ["artificial intelligence"])
        self.assertEqual([(h["t"], h["after"]) for h in hits], [(0.0, "intelligence cameras")])

    def test_a_phrase_broken_across_captions_is_marked_where_it_starts(self):
        """A line listed for "select board" because the phrase ran on into
        the next caption showed nothing marked (17 of 80); its opening words
        are marked now — only when the next line finishes the phrase (never a
        lone "artificial" before "turf"). Executed, as the reader runs it."""
        tw = TestTopicTwins()
        body = "\n".join([
            'const esc = s => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");',
            tw.lift(r"  function mark\(text, terms, after\) \{.+?\n  \}"),
            "console.log(JSON.stringify([",
            "  mark('we asked the Select', ['select board'], 'Board to vote'),",
            "  mark('we asked the Select', ['select board'], 'committee'),",
            "  mark('we asked the Select', ['select board']),",
            "  mark('AI and artificial', ['ai', 'artificial intelligence'], 'turf fields'),",
            "  mark('AI and artificial', ['ai', 'artificial intelligence'], 'intelligence.'),",
            "  mark('the Select Board voted', ['select board'], ''),",
            "  mark('a <b> & c', ['c'], ''),",
            "]));",
        ])
        r = tw.node(body)
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [
            "we asked the <mark>Select</mark>", "we asked the Select", "we asked the Select",
            "<mark>AI</mark> and artificial", "<mark>AI</mark> and <mark>artificial</mark>",
            "the <mark>Select Board</mark> voted", "a &lt;b&gt; &amp; <mark>c</mark>"])
        static = tw.JS[tw.JS.index("async function staticSearch("):tw.JS.index("function peek(")]
        self.assertIn("mark(text, marks, segs[id + 1] && segs[id + 1][0] === mi ? segs[id + 1][3] : \"\")", static)

    def test_the_list_counts_untowned_lines_over_its_whole_scope_and_says_counts_in_words(self):
        """The header's count is the whole scope's, so its "no town recorded"
        must be too (it was over the 80 shown — the header said nothing while
        the story beneath said 129); the live list waits on no static file;
        a picture of a stretch names one only when a start date applied."""
        js = TestTopicTwins.JS
        static = js[js.index("async function staticSearch("):js.index("function peek(")]
        self.assertLess(static.index("const noTown = SCOPE.town"), static.index("hits = hits.slice(0, 80);"))
        self.assertIn('${tpN(noTown, "line")} from meetings with no town recorded', static)
        self.assertIn('${tpN(total, "line")} elsewhere on the record.', static)
        self.assertIn('It holds ${tpN(meta.length, "meeting")}.', static)
        for bad in ("moment(s)", "meeting(s)"):
            self.assertNotIn(bad, static)
        live = js[js.index("async function liveSearch("):js.index("async function sqStoryFor(")]
        self.assertLess(live.index("sqFeatured(q)"), live.index("await askStudio("))    # asked beside the API, not after
        self.assertIn("setTimeout(() => res(null), 2500)", live)
        self.assertIn('${tpN(r.hits.length, "line")}', live)
        story = js[js.index("async function sqStory("):js.index("function sqTray(")]
        self.assertIn("const stretch = since ? ", story)

    def test_the_list_says_its_scopes_own_count_and_that_it_shows_the_newest(self):
        js = (REPO / "web" / "static" / "app.js").read_text()
        static = js[js.index("async function staticSearch("):js.index("function peek(")]
        self.assertIn('box.innerHTML = `<p class="hint">${tpN(cut, "line")} `', static)
        self.assertIn('(cut > hits.length ? ` — the newest ${hits.length} below` : "")', static)
        self.assertIn("const marks = feat ? feat.phrases : terms;", static)   # phrases highlight whole
        self.assertIn("const [idx, feat] = await Promise.all([sqIndex(), sqFeatured(q)]);", static)
        story = js[js.index("async function sqStory("):js.index("function sqTray(")]
        self.assertIn('the ${tpN(hitsAll.length, "line")} themselves', story)
        banner = js[js.index("function banner(ed) {"):js.index("const inScope = ")]
        self.assertIn("You chose the whole record", banner)

    def test_the_supercut_is_one_thing_on_both_stories(self):
        """The front page's numbers called the one-clip-a-night cut "the
        supercut" (2:08); the search page put the every-clip runtime (12:07)
        under the same label — one link apart (specs/27 §1.3)."""
        js = (REPO / "web" / "static" / "app.js").read_text()
        cell = re.search(r'\[hms\(d\.reel\.(\w+)_runtime\), "the supercut", d\.reel\.(\w+)\]', js)
        self.assertTrue(cell, "the search story's supercut cell moved")
        story = (REPO / "web" / "story.py").read_text()
        pressed = re.search(r'\(hms\(reel\["(\w+)_runtime"\]\), "the supercut", reel\["(\w+)"\]\)', story)
        self.assertTrue(pressed, "the pressed story's supercut cell moved")
        self.assertEqual((cell.group(1), cell.group(2)), (pressed.group(1), pressed.group(2)))
        self.assertEqual(pressed.group(1), "short")

    def test_the_search_page_says_what_a_search_can_do(self):
        page = (self.out / "s" / "index.html").read_text()
        self.assertIn('id="sq-guide"', page)
        self.assertIn("Search a word.", page)
        self.assertIn("See how it was said.", page)
        self.assertIn("Cut it, share it.", page)
        self.assertIn('id="sq-prog" hidden aria-live="polite"', page)
        self.assertIn('id="sq-story"', page)
        self.assertIn('href="/app/topic/ai/"><b>How Testville talks about AI</b>', page)
        self.assertIn('href="/app/s?q=Artificial%20Intelligence"', page)     # a try is the query, whole
        # the story's own page grows its ticks from the router, not the toggle
        # (a review catch: the page has no tab strip, and never hydrated)
        js = (REPO / "web" / "static" / "app.js").read_text()
        boot = js[js.index('document.addEventListener("DOMContentLoaded"'):js.index("registerSW();")]
        self.assertIn("hydrateTopicTicks();", boot)

    def test_a_word_said_once_presses_no_story(self):
        """The floor: the test corpus of test_web_bake says nothing twice,
        and its front page keeps two tabs with the record over time first."""
        from web import bake as _bake
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "c.db"
            from memory.store import Corpus
            c = Corpus(str(db))
            c.replace_segments("v", [{"start": 0.0, "end": 5.0, "speaker": "", "text": "AI once"}])
            c.upsert_meeting({"id": "v", "title": "One", "date": "2026-03-10", "town": "T", "body": "B",
                              "source_kind": "youtube", "video_id": "v", "url": "u", "url_canon": "youtube:v",
                              "duration": 5.0, "n_segments": 1, "status": "live", "summary": "",
                              "analysis_json": "{}"})
            _bake.bake(str(db), str(Path(d) / "app"), "9.9.9", "https://example.org")
            home = (Path(d) / "app" / "index.html").read_text()
            self.assertNotIn('data-story="topic-ai"', home)
            self.assertNotIn('href="/app/topic/ai/"', home)
            self.assertFalse((Path(d) / "app" / "topic").exists())
            self.assertEqual(json.loads((Path(d) / "app" / "topics" / "index.json").read_text()), [])


if __name__ == "__main__":
    unittest.main()
