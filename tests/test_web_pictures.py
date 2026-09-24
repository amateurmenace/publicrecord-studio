"""Every picture the press draws downloads as a file (specs/27 §3.3).

The pictures were the record's most shareable thing and the one thing on the
front page that did not download. These pin the files (written once, from
emit_stubs, so the desk bake and the hosted press carry the same ones), the
pressed links to them (an anchor with a download name — content, no script),
what a file says (its title, its source, its licence; its marks still links,
made absolute), and the JS twins that draw the live story's pictures the same
way, byte for byte.
"""

import json
import re
import shutil
import subprocess
import tempfile
import unittest
import xml.etree.ElementTree as ET
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent


class TestTheDrawersAndTheirTwins(unittest.TestCase):
    MONTHS = [
        {"month": "2025-12", "meetings": 1, "said": 1, "moments": 1, "mentions": 1},
        {"month": "2026-01", "meetings": 2, "said": 0, "moments": 0, "mentions": 0},
        {"month": "2026-02", "meetings": 0, "said": 0, "moments": 0, "mentions": 0},
        {"month": "2026-03", "meetings": 7, "said": 3, "moments": 47, "mentions": 51},
        {"month": "2027-01", "meetings": 1, "said": 1, "moments": 2, "mentions": 2},
    ]
    GARBAGE_MONTHS = [None, "x", {"month": "2026-13"}, {"month": "nope"},
                      {"month": "2026-04", "meetings": "3", "said": "9", "mentions": "4.7"},
                      {"month": "2026-05", "meetings": -2, "said": None, "mentions": float("nan")},
                      {"month": "2026-06", "meetings": 99, "said": 50, "mentions": "1e3"},
                      {"month": "2026-07", "meetings": [3], "mentions": {"a": 1}, "said": True},
                      {"month": "2026-08", "meetings": "0x10", "mentions": "1_000", "said": " 2 "},
                      {"month": "2026-09", "meetings": "Infinity", "mentions": 1e300, "said": "-3"},
                      {"month": 202610}, {"month": ["2026-11"]},
                      {"month": "2026-12", "meetings": 25, "said": 40, "mentions": 3}]
    ROWS = [
        {"pid": "a", "date": "2026-03-24", "body": "Select Board", "n": 27, "bins": [0] * 40 + [1, 3, 0, 27] + [0] * 4},
        {"pid": "b", "date": "", "body": "A body with a very long name indeed that runs on", "n": 1, "bins": [1] + [0] * 47},
        {"pid": "c", "date": "2026-04-14", "body": "Zoning 🏠 Board of Appeal and more", "n": 2, "bins": "not a list"},
        {"pid": "d", "date": "2026-05-12", "body": "Silent", "n": 0, "bins": [0] * 48},
        {"pid": "e", "date": 20260601, "body": ["x"], "n": "3", "bins": [True, "2", None, -1, 5.9]},
        {"pid": "f", "date": "2026-06-02", "body": "Ctrl\x1bBody\x0c 🏠 \ud800", "n": 1, "bins": [1]},
        None, "row",
    ]
    WORDS = [{"word": "use", "count": 16}, {"word": "  policy\t", "count": "9"}, {"word": "", "count": 5},
             {"word": "surveillance-and-more-words", "count": 5}, {"word": "<b>&", "count": 4}, None,
             {"word": " nbsp", "count": 2}, {"count": 3}, {"word": 7, "count": 1}, {"word": ["x"], "count": 1}]

    def test_a_months_file_is_a_picture_with_its_title_and_source(self):
        from web import pictures
        svg = pictures.months_svg(self.MONTHS, "How Brookline talks about AI — mentions, month by month",
                                  "https://publicrecord.studio/app/topic/ai/ · counted · CC BY-SA 4.0")
        root = ET.fromstring(svg.split("\n", 1)[1])          # valid XML past the declaration
        self.assertEqual(root.tag, "{http://www.w3.org/2000/svg}svg")
        self.assertIn(">How Brookline talks about AI — mentions, month by month</text>", svg)
        self.assertIn("CC BY-SA 4.0</text>", svg)
        self.assertEqual(svg.count('fill="#052e16"/>'), 3 + 5)        # three bars, five filled dots
        self.assertEqual(svg.count('stroke="#052e16"/>'), 2 + 4)      # the hollow dots
        self.assertIn(">51</text>", svg)
        self.assertIn(">2026</text>", svg)
        self.assertIn(">2027</text>", svg)
        for bad in ("cz-", "#a855f7", "#7c3aed", "#22c55e", "<script"):
            self.assertNotIn(bad, svg)

    def test_the_js_twins_draw_the_same_bytes(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        from web import pictures
        js = (REPO / "web" / "static" / "app.js").read_text(encoding="utf-8")
        esc = re.search(r"  const esc = s => .+?\n.+?\n", js).group(0)
        mon = re.search(r"  const TP_MON = .+?;\n", js).group(0)
        block = re.search(r"  const TP_PIC = .+?\n  function tpWordsSvg\(words, title, source, legend = TP_LEGEND\.words\) \{.+?\n  \}\n", js, re.S)
        tpn = re.search(r"  const tpN = .+?;\n", js).group(0)
        self.assertTrue(block, "the picture twins moved — re-point the test")
        title, source = "How <Town> & co talk\x07 about “AI” 🗳", 'https://x.test/app/s?q=AI&town="T" · CC BY-SA 4.0\x0b'
        cases = [("months", self.MONTHS), ("months", self.GARBAGE_MONTHS), ("months", []),
                 ("tapes", self.ROWS), ("tapes", []), ("words", self.WORDS), ("words", [])]
        prog = (esc + mon + tpn + block.group(0)
                + "const C = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
                  "const f = { months: tpMonthsSvg, tapes: tpTapesSvg, words: tpWordsSvg };"
                  "console.log(JSON.stringify(C.cases.map(([k, d]) => f[k](d, C.title, C.source))));")
        # NaN does not survive JSON: the JS side reads it as null, as the page would
        payload = json.dumps({"cases": cases, "title": title, "source": source}).replace("NaN", "null")
        r = subprocess.run([node, "-e", prog], input=payload, capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)
        py = {"months": pictures.months_svg, "tapes": pictures.tapes_svg, "words": pictures.words_svg}
        for (k, d), js_out in zip(json.loads(payload)["cases"], got):
            self.assertEqual(js_out, py[k](d, title, source), f"the {k} twins differ")

    def test_a_downloads_name_is_the_same_in_both_twins(self):
        from web import pictures
        names = ["The record’s roll calls, meeting by meeting", "How Brookline talks about AI mentions month by month",
                 "Don't — “quoted” & 42", "", "   ", "ÉCOLE Été"]
        r = subprocess.run([shutil.which("node") or "node", "-e",
                            re.search(r"  const tpPicSlug = .+?;\n", (REPO / "web" / "static" / "app.js").read_text()).group(0)
                            + f"console.log(JSON.stringify({json.dumps(names)}.map(tpPicSlug)));"],
                           capture_output=True, text=True)
        if r.returncode:
            self.skipTest(r.stderr[:200])
        self.assertEqual(json.loads(r.stdout), [pictures.slug(n) for n in names])
        self.assertEqual(pictures.slug(names[0]), "the-records-roll-calls-meeting-by-meeting")

    def test_a_file_parses_whatever_its_text_held_and_says_how_to_read_it(self):
        """A control character in a caption or a title made a file nothing
        could open (a review catch); past twenty meetings a month's dots were
        a silent twenty; the files carried no key and no <title>."""
        from web import pictures
        svg = pictures.months_svg([{"month": "2026-03", "meetings": 30, "said": 25, "mentions": 51}],
                                  "How \x1bTown\x0c talks \ud800about it", "https://x/app/ · counted\x08 · CC BY-SA 4.0")
        ET.fromstring(svg.split("\n", 1)[1].encode("utf-8"))
        self.assertIn(">25/30</text>", svg)
        self.assertNotIn("<circle", svg)
        self.assertIn("<title>How Town talks about it</title>", svg)
        self.assertIn(">" + pictures.LEGEND["months"].replace("'", "'") + "</text>", svg)
        # the page is as wide as its longest line
        long_title = "How Brookline talks about affordable housing in the whole record — mentions, month by month"
        w = int(re.search(r'width="(\d+)"', pictures.months_svg([], long_title, "a · b")).group(1))
        self.assertGreaterEqual(w, 32 + len(long_title) * 8)
        # the legends are the JS twin's, word for word
        js = (REPO / "web" / "static" / "app.js").read_text(encoding="utf-8")
        for k in ("months", "tapes", "words"):
            self.assertIn(f'{k}: "{pictures.LEGEND[k]}"', js)

    def test_a_meetings_file_keeps_its_ids_case(self):
        """YouTube ids are case-sensitive: lowercased, two tapes could share a
        file and one meeting's picture would overwrite another's."""
        from web import pictures
        self.assertNotEqual(pictures.key("abcDEF-_12"), pictures.key("ABCdef-_12"))
        self.assertEqual(pictures.key("-AuKbG4lTgc"), "-AuKbG4lTgc")
        self.assertEqual(pictures.key("a/b c"), "a_b_c")
        self.assertEqual(pictures.key(""), "_")

    def test_a_pressed_svg_is_wrapped_with_its_links_made_absolute(self):
        from web import charts, pictures
        pictures.reset("https://publicrecord.studio", "2026-09-22")
        cloud = charts.word_cloud([{"word": "override", "count": 9, "t": 12}, {"word": "budget", "count": 4, "t": 40}],
                                  href=lambda w: f'#t{int(w["t"])}')
        link = pictures.take("m-x-words", cloud, "The meeting in words — X", "/app/m/x", hash_page="/app/m/x")
        self.assertEqual(link, '<p class="pic-dl"><a href="/app/pictures/m-x-words.svg" '
                               'download="the-meeting-in-words-x.svg" aria-label="this picture, as .svg — The meeting in words — X">'
                               '↓ this picture, as .svg</a></p>')
        svg = pictures._PENDING["m-x-words"]
        self.assertIn('href="https://publicrecord.studio/app/m/x#t12"', svg)
        self.assertNotIn('href="#', svg)
        # the source in two lines — where it lives, then how it was made — so neither runs off the page
        self.assertIn('fill="#475569">https://publicrecord.studio/app/m/x</text>', svg)
        self.assertIn(">counted from the record’s transcripts, no model · the record of 2026-09-22 · CC BY-SA 4.0</text>", svg)
        ET.fromstring(svg.split("\n", 1)[1])
        # an honest empty line draws no file and no link
        self.assertEqual(pictures.take("none", '<p class="hint">no words counted yet</p>', "T", "/app/"), "")
        pictures.reset("https://publicrecord.studio")


class TestThePressWritesThePictures(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from tests.test_web_topic import TestTopicPress
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.db = root / "corpus.db"
        TestTopicPress._seed(cls.db)
        from web import bake
        cls.out = root / "app"
        bake.bake(str(cls.db), str(cls.out), "9.9.9", "https://example.org")
        cls.out2 = root / "app2"
        bake.bake(str(cls.db), str(cls.out2), "9.9.9", "https://example.org")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def test_the_topic_pictures_are_files_the_story_links(self):
        # the topic story lives on its own page now (specs/29): its three
        # pictures are linked from there
        home = (self.out / "topic" / "ai" / "index.html").read_text()
        titles = {"months": "mentions, month by month", "tapes": "where it fell, night by night", "words": "the words beside it"}
        names = []
        for kind, what in (("months", "mentions-month-by-month"), ("tapes", "where-it-fell"), ("words", "the-words-beside-it")):
            f = self.out / "pictures" / f"topic-ai-{kind}.svg"
            self.assertTrue(f.exists(), f"no {f.name}")
            svg = f.read_text()
            ET.fromstring(svg.split("\n", 1)[1])
            self.assertIn("How Testville talks about AI", svg)
            self.assertIn(">https://example.org/app/topic/ai/</text>", svg)
            self.assertIn(">counted from the record’s transcripts, no model · the record of", svg)
            # each link names its picture, its visible words first (WCAG 2.5.3:
            # a voice user says "click this picture"; ten links must not read alike)
            self.assertIn(f'<a href="/app/pictures/topic-ai-{kind}.svg" download="how-testville-talks-about-ai-{what}.svg" '
                          f'aria-label="this picture, as .svg — How Testville talks about AI — {titles[kind]}">'
                          "↓ this picture, as .svg</a>", home)
            names.append(titles[kind])
        # no two download links on the front page share a name
        labels = re.findall(r'<a href="/app/pictures/[^"]+" download="[^"]+"( aria-label="[^"]+")?>', home)
        self.assertTrue(labels and all(labels), "a picture link without a name")
        self.assertEqual(len(labels), len(set(labels)))
        page = (self.out / "topic" / "ai" / "index.html").read_text()
        self.assertIn('href="/app/pictures/topic-ai-months.svg"', page)

    def test_the_record_and_the_meeting_pictures_are_files_too(self):
        pics = sorted(p.name for p in (self.out / "pictures").iterdir())
        # the broadsheet's own pictures download too (specs/29 + specs/28 §3.3)
        for name in ("year-in-tapes.svg", "how-the-talk-flowed.svg", "m-t3-score.svg"):
            self.assertIn(name, pics, name)
        home = (self.out / "index.html").read_text()
        self.assertIn('href="/app/pictures/year-in-tapes.svg" download="the-year-in-tapes.svg"', home)
        self.assertIn('href="/app/pictures/how-the-talk-flowed.svg"', home)
        mt = (self.out / "m" / "t3" / "index.html").read_text()
        self.assertIn('href="/app/pictures/m-t3-words.svg"', mt)
        svg = (self.out / "pictures" / "m-t3-words.svg").read_text()
        self.assertIn('href="https://example.org/app/m/t3#t', svg)
        # every linked picture exists; every file is linked from somewhere pressed
        pressed = "".join(p.read_text() for p in self.out.rglob("index.html"))
        linked = set(re.findall(r'href="/app/pictures/([^"]+)"', pressed))
        self.assertEqual(linked, set(pics))

    def test_two_presses_press_the_same_pictures_and_the_pages_stay_byte_clean(self):
        a = {p.name: p.read_bytes() for p in (self.out / "pictures").iterdir()}
        b = {p.name: p.read_bytes() for p in (self.out2 / "pictures").iterdir()}
        self.assertEqual(a, b)
        home = (self.out / "index.html").read_text()
        for m in re.finditer(r'<p class="pic-dl">.*?</p>', home):
            self.assertNotIn("<button", m.group(0))
            self.assertNotIn("cz-", m.group(0))

    def test_the_live_story_offers_the_same_three(self):
        js = (REPO / "web" / "static" / "app.js").read_text(encoding="utf-8")
        story = js[js.index("async function sqStory("):js.index("function sqTray(")]
        for kind in ("months", "tapes", "words"):
            self.assertIn(f'picBtn("{kind}")', story)
        self.assertIn("tpPicSave(draws[k](),", story)


if __name__ == "__main__":
    unittest.main()
