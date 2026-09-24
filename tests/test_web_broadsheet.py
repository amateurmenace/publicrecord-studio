"""The civic broadsheet (specs/29 P0): the planes carry the score, the press
presses pictures, the pictures are pure, and the reader's re-lighting agrees
with the press — node twins over the pressed numbers, decodeReel's law for
every new codec, the no-script submit, and the byte-clean scan of every
pressed page. Offline and hermetic: the fixture corpus is tests/test_web_bake's.
"""

import json
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from tests.test_web_bake import TestBakeEdition

REPO = Path(__file__).resolve().parents[1]
JS = (REPO / "web" / "static" / "app.js").read_text()

# the fixture corpus is test_web_bake's, pressed once for this module (that
# module tears its own pressing down before this one runs)
_TMP = None
OUT = None


def setUpModule():
    global _TMP, OUT
    from web import bake
    _TMP = tempfile.TemporaryDirectory()
    root = Path(_TMP.name)
    db = root / "corpus.db"
    TestBakeEdition._seed(db)
    OUT = root / "app"
    bake.bake(str(db), str(OUT), "9.9.9", "https://example.org")


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


PRELUDE = "\n".join([
    'const hms = t => { t = Math.max(0, +t || 0); const h = t / 3600 | 0, m = (t % 3600) / 60 | 0, s = t % 60 | 0, p = n => String(n).padStart(2, "0"); return h ? `${h}:${p(m)}:${p(s)}` : `${m}:${p(s)}`; };',
    'const BASE = "/app"; const r1 = n => Math.round((+n || 0) * 10) / 10;',
    'const tpN = (n, one, many) => `${n} ${n === 1 ? one : (many || one + "s")}`;',
    'const TP_DAY = /^\\d{4}-\\d{2}-\\d{2}/;',
    'const tpDay = d => { const m = /^(\\d{4})-(\\d\\d)-(\\d\\d)/.exec(String(d || "")); if (!m) return "an undated meeting"; return `${["","January","February","March","April","May","June","July","August","September","October","November","December"][+m[2]]} ${+m[3]}, ${m[1]}`; };',
    "function fail(m){ console.log('FAIL', m); process.exit(1); }",
])


# --------------------------------------------------------------------------
# the planes
# --------------------------------------------------------------------------

class TestThePlanesCarryTheScore(unittest.TestCase):
    def test_the_track_sums_to_the_lens_count(self):
        """analysis.framing.track: sixty slices per lens, counted with the
        lenses' own word lists over the same tape length — a lane's bins sum
        to the lens's count, so the score and the framing never disagree."""
        from highlighter import insight
        from memory import analyze
        segs = [{"start": i * 7.0, "end": i * 7.0 + 6.0,
                 "text": ("the budget and the tax dollars" if i % 3 == 0 else
                          "police safety on the street sidewalk" if i % 3 == 1 else "we adjourn")}
                for i in range(40)]
        track = analyze.framing_track(segs)
        counts = {l["lens"]: l["count"] for l in insight.framing(segs)["lenses"]}
        for lens, bins in track.items():
            self.assertEqual(len(bins), 60, lens)
            self.assertEqual(sum(bins), counts.get(lens, 0), lens)
        self.assertGreater(sum(track["financial"]), 0)
        self.assertGreater(sum(track["infrastructure"]), 0)
        # empty and odd inputs: never a throw, always the shape
        self.assertEqual(sum(sum(v) for v in analyze.framing_track([]).values()), 0)
        self.assertEqual(len(analyze.framing_track(segs, bins=0)["financial"]), 1)

    def test_the_pressed_plane_carries_the_track_and_the_still(self):
        m = json.loads((OUT / "meetings" / "vid1.json").read_text())
        lenses = m["analysis"]["framing"]["lenses"]
        self.assertTrue(lenses)
        for l in lenses:
            self.assertEqual(len(l["track"]), 60)
            self.assertEqual(sum(l["track"]), l["count"])
            self.assertLessEqual(len(l["moments"]), 6)     # a sample, capped — never a count
        self.assertEqual(m["still"], "")                   # a test bake presses no stills
        self.assertEqual(m["frames"], 0)
        meta = json.loads((OUT / "search" / "meta.json").read_text())
        self.assertEqual({x["still"] for x in meta}, {0})


class TestThePressPressesPictures(unittest.TestCase):
    def test_stills_are_fetched_once_cached_and_placeholders_refused(self):
        from record.stills import Stills, is_still, still_path
        good = b"\xff\xd8" + b"x" * 3000
        placeholder = b"\xff\xd8" + b"x" * 500
        calls = []
        def fetcher(url):
            calls.append(url)
            if "hq3" in url:
                return placeholder      # YouTube's "no such frame" card
            if "hq2" in url:
                return None             # a failed fetch
            return good
        with tempfile.TemporaryDirectory() as d:
            cache, out = Path(d) / "cache", Path(d) / "out"
            st = Stills(cache=cache, fetch=True, fetcher=fetcher)
            have = st.press([("abc", "abcdefghijk"), ("", "xxxxxxxxxxx"), ("nov", "")], out)
            self.assertEqual(have, {"abc": {"poster": True, "frames": [1]}})
            self.assertTrue((out / "abc.jpg").is_file() and (out / "abc-1.jpg").is_file())
            self.assertFalse((out / "abc-2.jpg").exists() or (out / "abc-3.jpg").exists())
            self.assertEqual(len(calls), 4)
            # the second pressing asks YouTube only for what the cache lacks
            st2 = Stills(cache=cache, fetch=True, fetcher=fetcher)
            have2 = st2.press([("abc", "abcdefghijk")], Path(d) / "out2")
            self.assertEqual(have2, have)
            self.assertEqual(st2.copied, 2)
            # the network miss is asked again; the placeholder was remembered and is not
            self.assertEqual(len(calls), 5)
            self.assertEqual(st2.remembered, 1)
            # a press told not to fetch presses what the cache holds and nothing else
            st3 = Stills(cache=cache, fetch=False, fetcher=fetcher)
            self.assertEqual(st3.press([("abc", "abcdefghijk"), ("zzz", "zzzzzzzzzzz")], Path(d) / "out3"), have)
            self.assertEqual(len(calls), 5)
        self.assertFalse(is_still(None) or is_still(b"GIF89a" + b"x" * 5000) or is_still(placeholder))
        self.assertEqual(still_path("p"), "/app/stills/p.jpg")
        self.assertEqual(still_path("p", 2), "/app/stills/p-2.jpg")

    def test_the_desk_stops_asking_a_host_that_does_not_answer(self):
        """A walled picture host must not eat the press: after a run of
        misses the desk stops fetching and presses what the cache holds; a
        budget of wall-clock does the same; a frame YouTube said it lacks is
        remembered and not asked again; an id that is not a YouTube id is
        never put in a URL."""
        from record.stills import Stills
        calls = []
        none = lambda url: (calls.append(url), None)[1]
        with tempfile.TemporaryDirectory() as d:
            st = Stills(cache=Path(d) / "c", fetch=True, fetcher=none, breaker=5)
            have = st.press([(f"p{i:02d}", f"v{i:02d}xxxxxxxx"[:11]) for i in range(10)], Path(d) / "o")
            self.assertEqual(have, {})
            self.assertEqual(len(calls), 5)
            self.assertIn("misses in a row", st.stopped)
            # a placeholder is an ANSWER — it never trips the breaker (a skeptic's catch)
            cards = []
            card = lambda url: (cards.append(url), b"\xff\xd8" + b"x" * 500)[1]
            st0 = Stills(cache=None, fetch=True, fetcher=card, breaker=3)
            st0.press([(f"c{i}", f"c{i}xxxxxxxxx"[:11]) for i in range(6)], Path(d) / "o0")
            self.assertEqual(len(cards), 24)
            self.assertEqual(st0.stopped, "")
            self.assertIn("stopped early", st.note())
            # the wall clock: a fetcher that "takes" a minute each trips a 100 s budget
            now = [0.0]
            slow = lambda url: (calls.append(url), now.__setitem__(0, now[0] + 60.0), None)[2]
            st2 = Stills(cache=Path(d) / "c2", fetch=True, fetcher=slow, breaker=99, budget_s=100, clock=lambda: now[0])
            st2.press([(f"q{i}", f"w{i}xxxxxxxxx"[:11]) for i in range(10)], Path(d) / "o2")
            self.assertIn("budget ran out", st2.stopped)
            # a placeholder answer is remembered; the next press does not ask again
            placeholder = b"\xff\xd8" + b"x" * 500
            asked = []
            card = lambda url: (asked.append(url), placeholder)[1]
            st3 = Stills(cache=Path(d) / "c3", fetch=True, fetcher=card)
            st3.press([("abc", "abcdefghijk")], Path(d) / "o3")
            n = len(asked)
            st4 = Stills(cache=Path(d) / "c3", fetch=True, fetcher=card)
            st4.press([("abc", "abcdefghijk")], Path(d) / "o4")
            self.assertEqual(len(asked), n)
            self.assertEqual(st4.remembered, 4)
            # an id that is not YouTube's shape never reaches the fetcher
            bad = []
            st5 = Stills(cache=None, fetch=True, fetcher=lambda u: (bad.append(u), None)[1])
            st5.press([("x", "not a video id"), ("y", "../../etc/passwd"), ("z", "abcdefghijk")], Path(d) / "o5")
            self.assertEqual(len(bad), 4)
            self.assertTrue(all("abcdefghijk" in u for u in bad))

    def test_the_sync_never_deletes_the_stills(self):
        """The keep rule (a fold): the delete pass leaves the bucket's stills
        alone, so a night whose seed failed cannot empty the cache the
        edition depends on."""
        from record import press
        self.assertIn("stills/", press.KEEP_PREFIXES)
        import inspect
        src = inspect.getsource(press.sync_to_gcs)
        self.assertIn("if name.startswith(keep):", src)
        self.assertIn("kept", src)

    def test_a_bake_without_a_picture_desk_touches_no_network_and_says_so(self):
        """The test corpus presses no stills: every place a still would stand
        shows the town's colour, and nothing on a pressed page loads from a
        third party."""
        home = (OUT / "index.html").read_text()
        self.assertIn('class="bs-nostill"', home)
        self.assertFalse((OUT / "stills").exists())
        for rel in ("index.html", "m/vid1/index.html", "m/vid2/index.html", "s/index.html", "k/index.html"):
            page = (OUT / rel).read_text()
            self.assertNotIn("i.ytimg.com", page.split("</head>")[1], rel)   # the CSP line may still allow it; the page uses none

    def test_the_stage_is_in_both_presses_before_the_meetings(self):
        """A stage in web/bake.py is a stage in record/press.py too, and the
        stills come first so every plane can say whether its still exists."""
        import inspect
        from record import press
        from web import bake
        for fn in (bake.bake, press.press):
            src = inspect.getsource(fn)
            calls = re.findall(r"\bb\.(bake_\w+)\s*\(", src)
            self.assertEqual(calls[:2], ["bake_stills", "bake_meetings"], fn.__name__)


# --------------------------------------------------------------------------
# the pictures — pure, deterministic, their numbers beside them
# --------------------------------------------------------------------------

class TestTheChartsArePure(unittest.TestCase):
    def setUp(self):
        self.m = json.loads((OUT / "meetings" / "vid2.json").read_text())
        self.analytics = json.loads((OUT / "analytics.json").read_text())
        self.meta = json.loads((OUT / "search" / "meta.json").read_text())

    def test_the_scores_numbers_round_trip(self):
        """The score writes its numbers beside it as data-bs-score JSON;
        what comes back out is what went in, and the pressed playhead is
        where score_state puts it."""
        from web import charts
        html_ = charts.score(self.m)
        raw = re.search(r'data-bs-score="([^"]+)"', html_).group(1)
        import html as _html
        d = json.loads(_html.unescape(raw))
        self.assertEqual(d, charts.score_data(self.m))
        st = charts.score_state(d, d["t"])
        self.assertIn(f'<line x1="{st["x"]}" y1="32" x2="{st["x"]}"', html_)
        self.assertIn(f'>{st["mmss"]}</text>', html_)
        # the same meeting presses the same bytes
        self.assertEqual(html_, charts.score(self.m))
        # a lane is one path; every mark is an anchor into the tape
        self.assertRegex(html_, r'<path class="bs-lane" data-lens="financial"')
        self.assertRegex(html_, r'<a href="/app/m/vid2#t\d+" class="bs-dec"')

    def test_score_state_is_total_over_odd_input(self):
        from web import charts
        self.assertEqual(charts.score_state({"dur": 0, "w": 0, "decisions": []}, -5)["near"], None)
        self.assertEqual(charts.score_state({"dur": 100, "w": 100, "decisions": [{"t": 10}, {"t": 30}]}, 20)["near"], 0)   # ties to the earlier
        self.assertEqual(charts.score_state({"dur": 100, "w": 100, "decisions": [{"t": 10}, {"t": 30}]}, 999)["x"], 100)

    def test_the_year_is_one_window_for_the_strip_and_its_chapters(self):
        """Fifteen months of tapes: the strip shows the last twelve, and the
        chapters, the count and the sub read the same window (a skeptic's
        catch — the strip was windowed and the chapters were not)."""
        from web import charts, story, broadsheet
        ms = [{"pid": f"p{i:02d}", "date": f"{2025 + (i + 3) // 12}-{(i + 3) % 12 + 1:02d}-10", "town": "Boston",
               "body": "B", "title": f"t{i}", "duration": 3600, "votes": []} for i in range(15)]
        months, dated, windowed = charts.year_window(ms)
        self.assertTrue(windowed)
        self.assertEqual(len(months), 12)
        self.assertEqual(len(dated), 12)
        chs = story.chapters(dated, [], [])
        self.assertTrue(all(m in months for c in chs for m in c["months"]))
        html_ = broadsheet.year_section(ms, [], {}, None)
        self.assertIn("the last twelve months", html_)
        self.assertIn("twelve meetings", html_)
        self.assertEqual(len(re.findall(r'class="bs-tape( bs-dim)?"', html_)), 12)

    def test_the_pressed_picture_keeps_the_scores_own_coordinates(self):
        """The score is drawn from x = -100 (its lane labels); the picture
        file keeps that viewBox, or the download clips the labels off."""
        svg = (OUT / "pictures" / "m-vid1-shape.svg").read_text()
        self.assertRegex(svg, r'<svg x="\d+" y="44" width="\d+" height="168" viewBox="-100 0 \d+ 168">')
        self.assertIn(">financial</text>", svg)

    def test_the_year_lays_every_dated_tape_without_overlap(self):
        from web import charts
        ms = [{"pid": f"p{i}", "date": f"2026-0{1 + i % 9}-{10 + i % 15:02d}", "town": "Boston" if i % 2 else "Brookline",
               "body": "B", "title": f"t{i}", "duration": 3600 * (1 + i % 6)} for i in range(24)]
        months, tapes = charts.year_layout(ms)
        self.assertEqual(len(tapes), 24)
        self.assertEqual(months, [f"2026-0{k}" for k in range(1, 10)])
        for a in tapes:
            for b in tapes:
                if a is b:
                    continue
                overlap = a["x"] < b["x"] + b["w"] and a["x"] + a["w"] > b["x"] and a["y"] < b["y"] + b["h"] and a["y"] + a["h"] > b["y"]
                self.assertFalse(overlap, (a["pid"], b["pid"]))
        self.assertGreaterEqual(min(t["y"] for t in tapes), 0)
        # undated tapes do not sit on the year; the same input, the same layout
        self.assertEqual(charts.year_layout(ms + [{"pid": "u", "date": "", "duration": 1}])[1], tapes)

    def test_the_river_the_butterfly_the_grid_and_the_dots_are_deterministic_svg(self):
        from web import charts
        tb = {x["pid"]: x["town"] for x in self.meta}
        rows = self.analytics["framing"]
        for fn in (lambda: charts.lens_river(rows, tb),
                   lambda: charts.butterfly(charts.town_shares(rows, tb)),
                   lambda: charts.who_when([{"name": "Ann Chair", "kind": "people", "count": 4, "meetings": [{"pid": "vid1", "date": "2026-03-10"}, {"pid": "vid2", "date": "2026-06-18"}]},
                                            {"name": "Main Street", "kind": "places", "count": 2, "meetings": [{"pid": "vid2", "date": "2026-06-18"}]}],
                                           ["2026-03", "2026-04", "2026-05", "2026-06"], tb),
                   lambda: charts.vote_grid([{**v, "pid": "vid1", "date": "2026-03-10"} for v in json.loads((OUT / "meetings" / "vid1.json").read_text())["votes"]]),
                   lambda: charts.timeline_dots([{"pid": "vid1", "date": "2026-03-10", "n": 2, "first_t": 12, "town": "Testville", "body": "Board", "title": "x"}], q="budget")):
            a, b = fn(), fn()
            self.assertEqual(a, b)
            self.assertIn("<svg", a)
        river = charts.lens_river(rows, tb)
        self.assertIn('data-bs-river="', river)
        self.assertEqual(river.count('class="bs-band"'), 8)
        self.assertIn("the same, as a table", river)
        # a failed vote is rust; the ayes are read from the roll
        grid = charts.vote_grid([{"pid": "p", "date": "2026-01-02", "t": 5, "outcome": "fails", "tally": "0–2–1",
                                  "roll": [{"vote": "no"}, {"vote": "no"}, {"vote": "abstain"}]}])
        self.assertIn(f'fill="{charts.RUST}"', grid)
        self.assertIn('text-anchor="middle" style="font-family:var(--font-mono)">0</text>', grid)

    def test_money_and_thirds_read_the_plane(self):
        from web import charts
        self.assertEqual(charts.money_label("$97 MILLION"), "$97 million")
        self.assertEqual(charts.money_label("$1,000"), "$1,000")
        th = charts.thirds_of({"duration": 10001.858, "moments": []})
        self.assertEqual([t["label"] for t in th], ["The first hour", "The second hour", "The last hour"])
        th2 = charts.thirds_of({"duration": 1800, "moments": []})
        self.assertEqual(th2[2]["label"], "The last 10 minutes")


class TestTheWordsAreCounted(unittest.TestCase):
    def test_tonight_and_chapters_and_the_columns_read_from_the_planes(self):
        from web import story
        m = json.loads((OUT / "meetings" / "vid2.json").read_text())
        t = story.tonight(m)
        self.assertIn("and money was the frame", t["headline"])       # the fixture talks budget
        self.assertIn("words the record files under a lens", t["lede"])
        self.assertIn('href="/app/m/vid2"', t["lede"])
        self.assertEqual(t["labels"][0], "summary drawn from the tape")
        self.assertEqual(story.hours_prose(10001), "two hours and forty-six minutes")
        # the count line capitalises the number, never lowercases the town (a fold's regression)
        two = [{"town": "Brookline", "color": "", "n": 14, "shares": {l: 0.1 for l in story.charts.LENS_ORDER}},
               {"town": "Boston", "color": "", "n": 12, "shares": {l: 0.1 for l in story.charts.LENS_ORDER}}]
        two[0]["shares"]["financial"] = 0.4; two[1]["shares"]["community"] = 0.3
        _h, _s, line = story.vocab_words(two)
        self.assertTrue(line.startswith("Twelve Boston tapes against fourteen from Brookline"), line)
        one = [{"town": "Boston", "color": "", "n": 1, "shares": {l: 0.1 for l in story.charts.LENS_ORDER}}] + two[:1]
        self.assertIn("One Boston tape against", story.vocab_words([two[0], dict(two[1], n=1)])[2])
        self.assertEqual(story.hours_prose(0), "under a minute")
        ms = [json.loads((OUT / "meetings" / f"{p}.json").read_text()) for p in ("vid1", "vid2")]
        votes = [{**v, "pid": "vid1", "date": "2026-03-10"} for v in ms[0]["votes"]]
        analytics = json.loads((OUT / "analytics.json").read_text())
        chs = story.chapters(ms, votes, analytics["framing"])
        self.assertEqual([c["i"] for c in chs], [0, 1, 2, 3])
        self.assertEqual([m_ for c in chs for m_ in c["months"]], ["2026-03", "2026-04", "2026-05", "2026-06"])
        self.assertIn("the roll calls", chs[0]["title"])
        self.assertIn("were taken here", chs[0]["blurb"])
        self.assertNotIn("<", chs[0]["blurb"])                        # the plain blurb, for the script's line
        # the pressed paragraphs carry receipts (the longest tape, named with its link)
        self.assertTrue(any(re.search(r'href="/app/m/vid[12]"', c["html"]) for c in chs), [c["html"] for c in chs])
        self.assertTrue(any("longest tape" in c["html"] for c in chs))
        self.assertEqual(story.chapters([], [], []), [])
        head, say, line = story.rolls_words(votes, {"vid1": ms[0]})
        self.assertEqual(head, "1 vote, 1 passed, none failed")
        self.assertIn("the number in each square is the ayes", say)
        self.assertTrue(story.river_words(story.charts.river_data(analytics["framing"], {"vid1": "Testville", "vid2": "Testville"})))


# --------------------------------------------------------------------------
# the reader's re-lighting agrees with the press — node twins
# --------------------------------------------------------------------------

class TestBroadsheetTwins(unittest.TestCase):
    def ok(self, r):
        self.assertEqual(r.stdout.strip(), "ok", r.stdout + r.stderr)

    def test_bs_score_state_agrees_with_the_press(self):
        """The playhead's x, the nearest decision and the frame's third, at
        forty times along the tape — the same on both sides of the wire."""
        from web import charts
        m = json.loads((OUT / "meetings" / "vid2.json").read_text())
        m["moments"] = m["moments"] + [{"t": 33.3, "kind": "tension", "quote": "no", "reason": "pushback", "score": 0.4, "start": 30, "end": 40}]
        d = charts.score_data(m)
        ts = [d["dur"] * i / 39 for i in range(40)] + [-3, d["dur"] + 50]
        want = [charts.score_state(d, t) for t in ts]
        self.ok(node("\n".join([
            PRELUDE,
            lift(r"  function bsScoreState\(D, t\) \{.+?\n  \}"),
            f"const D = {json.dumps(d)}; const TS = {json.dumps(ts)}; const WANT = {json.dumps(want)};",
            "TS.forEach((t, i) => { const got = bsScoreState(D, t), w = WANT[i];",
            "  for (const k of ['x', 'near', 'third', 'mmss']) if (got[k] !== w[k]) fail(`t=${t} ${k}: ${got[k]} vs ${w[k]}`); });",
            "const e = bsScoreState({ decisions: [] }, 5); if (e.near !== null || e.x !== 880) fail('empty: ' + JSON.stringify(e));",
            "console.log('ok');"])))

    def test_bs_year_state_reads_the_pressed_numbers(self):
        home = (OUT / "index.html").read_text()
        import html as _html
        raw = _html.unescape(re.search(r'data-bs-year="([^"]+)"', home).group(1))
        D = json.loads(raw)
        last = len(D["chapters"]) - 1
        self.ok(node("\n".join([
            PRELUDE,
            lift(r"  function bsYearState\(D, chapter, pick\) \{.+?\n  \}"),
            f"const D = {json.dumps(D)};",
            f"const st = bsYearState(D, {last}, null);",
            f"if (st.line !== D.chapters[{last}].blurb) fail('the last chapter is the pressed line');",
            "const lit = new Set(D.chapters[D.chapters.length - 1].months);",
            "const dimWant = D.tapes.filter(t => !lit.has(t.month)).map(t => t.pid);",
            "if (JSON.stringify(st.dim) !== JSON.stringify(dimWant)) fail('dimmed tapes: ' + JSON.stringify(st.dim));",
            "const p = bsYearState(D, 0, D.tapes[0].pid);",
            "if (p.line !== D.tapes[0].title || !p.href.endsWith('/m/' + encodeURIComponent(D.tapes[0].pid))) fail('a picked tape names itself');",
            "const none = bsYearState({ tapes: [], chapters: [] }, 3, 'zz'); if (none.line !== '' || none.dim.length) fail('empty year');",
            "console.log('ok');"])))

    def test_bs_month_x_agrees_with_month_axis(self):
        from web import charts
        months = ["2025-12", "2026-01", "2026-02", "2026-03"]
        x = charts.month_axis(months, 1000)
        dates = ["2025-12-01", "2025-12-31", "2026-01-15", "2026-02-28", "2026-03-10", "2026-03-31", "", "2027-01-01", "2020-01-01", "2026-02"]
        want = [round(x(d), 3) for d in dates]
        self.ok(node("\n".join([
            PRELUDE,
            "const tpIsMonth = d => /^\\d{4}-(0[1-9]|1[0-2])/.test(String(d || ''));",
            lift(r"  const BS_MDAYS = [^\n]+"),
            lift(r"  function bsMonthX\(months, width\) \{.+?\n  \}"),
            f"const x = bsMonthX({json.dumps(months)}, 1000); const D = {json.dumps(dates)}; const W = {json.dumps(want)};",
            "D.forEach((d, i) => { const g = Math.round(x(d) * 1000) / 1000; if (Math.abs(g - W[i]) > 0.001) fail(d + ': ' + g + ' vs ' + W[i]); });",
            "console.log('ok');"])))

    def test_bs_timeline_agrees_with_the_press(self):
        """The search page's timeline and the pressed topic page's are one
        picture: the same rows draw the same bytes on both sides."""
        from web import charts
        rows = [{"pid": "vid1", "date": "2026-03-10", "n": 2, "first_t": 12.97, "town": "Testville", "body": "Mayor's Office & Board", "title": "Select Board — March \"quoted\""},
                {"pid": "vid2", "date": "2026-06-18", "n": 1, "first_t": 40.0, "town": "Boston", "body": "School Committee of the City", "title": "School Committee — June"},
                {"pid": "vid3", "date": "2026-05-02", "n": 0, "first_t": None, "town": "Testville", "body": "Board", "title": "silent"},
                {"pid": "vid4", "date": "", "n": 3, "first_t": 1.0, "town": "Testville", "body": "Board", "title": "undated"}]
        want = charts.timeline_dots(rows, q="budget")
        self.ok(node("\n".join([
            PRELUDE,
            "const TP_MON = ['', 'Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];",
            'const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", \'"\': "&quot;" }[c]));',
            "const tpIsMonth = d => /^\\d{4}-(0[1-9]|1[0-2])/.test(String(d || ''));",
            lift(r"  const tpMonthRange = months => \{.+?\n  \};"),
            lift(r"  const tpCutWords = \(s, n\) => \{.+?\n  \};"),
            lift(r"  const BS_TOWNS = [^\n]+"),
            lift(r"  const bsTown = [^\n]+"),
            lift(r"  const BS_MDAYS = [^\n]+"),
            lift(r"  function bsMonthX\(months, width\) \{.+?\n  \}"),
            lift(r"  const bsDayShort = [^\n]+"),
            lift(r"  const bsEsc = [^\n]+"),
            lift(r"  function bsTimeline\(rows, q, width, height\) \{.+?\n  \}"),
            f"const got = bsTimeline({json.dumps(rows)}, 'budget'); const want = {json.dumps(want)};",
            "if (got !== want) { let i = 0; while (i < got.length && got[i] === want[i]) i++; fail('drift at ' + i + ': ' + got.slice(i, i + 160) + ' vs ' + want.slice(i, i + 160)); }",
            "if (bsTimeline([], 'x') !== '') fail('no rows, no picture');",
            "console.log('ok');"])))

    def test_the_score_survives_a_malformed_plane(self):
        """decodeReel's law for the score's JSON: a broken attribute paints
        nothing and throws nothing — the still stays a still."""
        self.ok(node("\n".join([
            PRELUDE,
            "const $ = () => null; const $$ = () => [];",
            "const boxes = [{ dataset: { bsScore: '{not json' } }, { dataset: { bsScore: '{\"decisions\": 3}' } }, { dataset: {} }];",
            "const _$$ = sel => sel === '.bs-score' ? boxes : [];",
            lift(r"  function bsScore\(\) \{.+?\n  \}").replace("$$(\".bs-score\")", "_$$('.bs-score')"),
            "let BS_FOLLOW = null;",
            "try { bsScore(); } catch (e) { fail('threw: ' + e.message); }",
            "console.log('ok');"])))

    def test_bs_group_groups_the_index_as_the_board(self):
        """The spine's grouping over a tiny index: moments newest meeting
        first, meetings with their first mention, threads by name, the
        over-time counts per month, clips merged per meeting."""
        self.ok(node("\n".join([
            PRELUDE,
            "const PAPER_REF = /^[\\w-]{1,128}$/;",
            "const SCOPE = { town: '', body: '' }; const inScope = () => true;",
            lift(r"  const TP_WINDOW = [^\n]+"),
            lift(r"  const phraseRe = [^\n]+\n[^\n]+"),
            lift(r"  function mentionsIn\(text, after, pats\) \{.+?\n  \}"),
            "const TP_MONTH = /^\\d{4}-(0[1-9]|1[0-2])/;",
            lift(r"  const tpIsMonth = [^\n]+"),
            lift(r"  const tpMonthRange = months => \{.+?\n  \};"),
            lift(r"  function tpMerge\(hits, duration\) \{.+?\n  \}"),
            lift(r"  function sqHits\(idx, ids, phrases\) \{.+?\n  \}"),
            lift(r"  const BS_TA_MOMENTS = [^\n]+"),
            lift(r"  function bsGroup\(idx, ids, q, issues\) \{.+?\n  \}"),
            "const idx = { meta: [{ pid: 'a', title: 'A', date: '2026-01-05', town: 'T', body: 'B', duration: 100, still: 1 },",
            "                     { pid: 'b', title: 'B', date: '2026-03-09', town: 'T', body: 'B', duration: 100, still: 0 }],",
            "  segs: [[0, 10, '', 'the housing trust fund'], [0, 50, '', 'a housing trust grant'], [1, 5, '', 'housing trust again'], [1, 90, '', 'nothing here']] };",
            "const g = bsGroup(idx, [0, 1, 2], 'housing trust', [{ slug: 'i1', name: 'Housing Trust Fund', n_meetings: 3 }, { slug: 'i2', name: 'Parking', n_meetings: 9 }, 7, { slug: '../x', name: 'housing trust' }]);",
            "if (g.total !== 3) fail('three moments');",
            "if (g.moments[0].pid !== 'b') fail('newest meeting first');",
            "if (JSON.stringify(g.meetings.map(m => [m.pid, m.n, m.first_t, m.still])) !== JSON.stringify([['b', 1, 5, false], ['a', 2, 10, true]])) fail('meetings: ' + JSON.stringify(g.meetings));",
            "if (JSON.stringify(g.threads) !== JSON.stringify([{ slug: 'i1', name: 'Housing Trust Fund', n_meetings: 3 }])) fail('threads by name, malformed dropped: ' + JSON.stringify(g.threads));",
            "if (JSON.stringify(g.months) !== JSON.stringify(['2026-01', '2026-02', '2026-03']) || JSON.stringify(g.counts) !== JSON.stringify([1, 0, 1])) fail('over time');",
            "if (g.clips.length !== 3 || g.clips[0].pid !== 'a') fail('clips merged per meeting: ' + JSON.stringify(g.clips));",
            "const e = bsGroup(idx, [], 'zzz', null); if (e.total !== 0 || e.clips.length) fail('empty');",
            "console.log('ok');"])))


# --------------------------------------------------------------------------
# the page: no-script submit, byte-clean, zero fuchsia, the chrome everywhere
# --------------------------------------------------------------------------

class TestTheBroadsheetPage(unittest.TestCase):
    def test_the_spine_submits_to_the_search_page_without_scripts(self):
        home = (OUT / "index.html").read_text()
        form = home[home.index('<form class="bs-spineform"'):home.index("</form>", home.index('<form class="bs-spineform"'))]
        self.assertIn('action="/app/s" method="get"', form)
        self.assertIn('name="q"', form)
        self.assertNotIn("onsubmit", form)
        self.assertNotIn("<script", form)
        # the six words to try are the record's own, each a search
        self.assertRegex(home, r'<a class="bs-try" href="/app/s\?q=[^"]+">')
        # on the search page the form is the same shape
        search = (OUT / "s" / "index.html").read_text()
        self.assertIn('<form class="askform bs-searchform" id="searchform" action="/app/s" method="get">', search)

    def test_every_pressed_page_is_byte_clean_and_takes_zero_fuchsia(self):
        """The pressed pages carry no studio class, no studio hue and no
        inline handler; the pressed stylesheet keeps the studio's purples
        under html.cz-m-studio and shows no fuchsia anywhere."""
        for stub in OUT.rglob("index.html"):
            html_ = stub.read_text()
            if 'http-equiv="refresh"' in html_:
                continue
            main = html_[html_.index("<body>"):]
            main = main[:main.rindex("<script")]        # the reader's one script tag closes the page
            for bad in ("cz-", "#a855f7", "#7c3aed", "#d946ef", "#22c55e", "onclick=", "<script"):
                self.assertNotIn(bad, main, f"{bad!r} in {stub.relative_to(OUT)}")
        css = re.sub(r"/\*.*?\*/", "", (OUT / "app.css").read_text(), flags=re.S).lower()
        self.assertNotIn("#d946ef", css)
        self.assertNotIn("fuchsia", css)
        block = css[css.index(".bs-sechead{"):]        # the broadsheet's rules, comments already gone
        for pop in ("#a855f7", "#7c3aed", "#22c55e", "#a97a16", "#7e5b8e", "#c77ba6", "#b0542d", "#3fa9d0"):
            self.assertNotIn(pop, block, f"{pop!r} in the broadsheet's rules")

    def test_the_stamp_and_the_switch_are_on_every_page(self):
        for rel in ("index.html", "s/index.html", "m/vid1/index.html", "officials/index.html", "p/index.html", "ai/index.html"):
            page = (OUT / rel).read_text()
            self.assertIn('id="bs-stamp" data-mode="read"', page, rel)
            self.assertIn('id="scope"', page, rel)
            self.assertIn('class="navlink bs-write" href="/app/p#edit"', page, rel)
        home = (OUT / "index.html").read_text()
        self.assertIn('class="bs-nameplate"', home)
        self.assertNotIn('class="bs-nameplate"', (OUT / "s" / "index.html").read_text())

    def test_the_meeting_page_carries_the_score_as_its_jump_bar(self):
        page = (OUT / "m" / "vid1" / "index.html").read_text()
        self.assertIn('<section class="card bs-scorecard mp-score" id="score">', page)
        self.assertIn('href="#score">the shape of the tape</a>', page)
        self.assertIn('data-bs-score="', page)
        self.assertRegex(page, r'<a href="/app/m/vid1#t\d+" class="bs-dec"')
        self.assertIn('href="/app/pictures/m-vid1-shape.svg"', page)
        self.assertTrue((OUT / "pictures" / "m-vid1-shape.svg").is_file())
        # the front page's score is its own picture, under its own name (a fold: two pictures shared one file)
        self.assertTrue((OUT / "pictures" / "tonight-score.svg").is_file())
        self.assertIn("The score of the night", (OUT / "pictures" / "tonight-score.svg").read_text())
        self.assertIn("The shape of the tape", (OUT / "pictures" / "m-vid1-shape.svg").read_text())
        # the town's colour rides the header's rule; the facade shows the still or the town's colour
        self.assertIn('class="mhead bs-mhead" style="--town:', page)

    def test_the_reader_wires_the_broadsheet_and_the_stamp_replaces_the_mode_bar(self):
        boot = JS[JS.index('document.addEventListener("DOMContentLoaded"'):JS.index("registerSW();")]
        self.assertIn("bsSpine(); bsScore(); bsYear(); bsRiver();", boot)
        bar = lift(r"  function paintModeBar\(\) \{.+?\n  \}")
        self.assertIn('$("#bs-stamp")', bar)
        self.assertIn("shownMode()", bar)                 # controls describe the painted state
        self.assertNotIn(".cz-modebar", bar)
        self.assertIn('data-czmode="studio"', bar)
        # the find box adopts the pressed form; the meeting page's score follows the tape
        self.assertIn('let form = $("form.mp-find");', JS)
        self.assertIn("if (BS_FOLLOW) { try { BS_FOLLOW(t); }", JS)
        # the search page's story gains the timeline and the reel rows
        self.assertIn("${bsSearchExtras(d, q, idx)}", JS)


if __name__ == "__main__":
    unittest.main()
