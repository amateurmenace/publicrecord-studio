"""The desk's last pieces, in the paper (specs/27 §3): drag to reorder on
the tray, and the glossary. Executed twins over token pins — the reader's
own functions lifted and run in node against a small fake of the DOM they
touch, the way the review folds before this one were pinned."""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
JS = (REPO / "web" / "static" / "app.js").read_text(encoding="utf-8")


def lift(pattern):
    m = re.search(pattern, JS, re.S)
    if not m:
        raise AssertionError(f"{pattern!r} not found in the reader — did it move?")
    return m.group(0)


def run_node(body):
    node = shutil.which("node")
    if not node:
        raise unittest.SkipTest("node not available")
    return subprocess.run([node, "-e", body], capture_output=True, text=True)


FAKE_DOM = r"""
function El(name, rect) { this.name = name; this.rect = rect || { top: 0, height: 0, bottom: 0 };
  this.L = {}; this.cls = new Set(); this.style = {}; this.hidden = false; this.kids = [];
  this.classList = { add: c => this.cls.add(c), remove: c => this.cls.delete(c), contains: c => this.cls.has(c) }; }
El.prototype.addEventListener = function (t, f) { (this.L[t] ||= []).push(f); };
El.prototype.removeEventListener = function (t, f) { this.L[t] = (this.L[t] || []).filter(x => x !== f); };
El.prototype.fire = function (t, ev) { for (const f of (this.L[t] || []).slice()) f(ev); };
El.prototype.getBoundingClientRect = function () { return this.rect; };
El.prototype.setPointerCapture = function () {};
El.prototype.appendChild = function (k) { this.kids.push(k); k.parent = this; };
El.prototype.remove = function () { if (this.parent) this.parent.kids = this.parent.kids.filter(k => k !== this); };
const rowAt = (i, top) => { const r = new El("row" + i, { top, height: 40, bottom: top + 40 }); r.grip = new El("grip" + i); r.grip.row = r; return r; };
let ROWS = [];
const LIST = new El("list", { top: 0, height: 400, bottom: 400 });
LIST.scrollHeight = 400; LIST.clientHeight = 400; LIST.scrollTop = 0;
LIST.contains = el => !!el && (el === LIST || ROWS.includes(el) || ROWS.some(r => r.grip === el));
for (const r of []) {}
const closestOf = el => sel => sel === "[data-grip]" ? (el.row ? el : null) : sel === ".row" ? (el.row || (ROWS.includes(el) ? el : null)) : null;
const $$ = (sel, root) => root === LIST && sel === ".row" ? ROWS.slice() : [];
const DOC = new El("document");
const document = { createElement: () => new El("line"), addEventListener: (t, f, c) => DOC.addEventListener(t, f),
                   removeEventListener: (t, f, c) => DOC.removeEventListener(t, f) };
const requestAnimationFrame = () => 1, cancelAnimationFrame = () => {}, innerHeight = 800, scrollBy = () => {};
"""


class TestDragToReorder(unittest.TestCase):
    def test_the_drop_slot_is_the_rows_passed(self):
        r = run_node(lift(r"  const dgSlot = .+?;\n") + """
const R = [{ top: 0, height: 40 }, { top: 50, height: 40 }, { top: 100, height: 40 }];
console.log(JSON.stringify([0, 19, 21, 75, 119, 121, 900].map(y => dgSlot(y, R))));""")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertEqual(json.loads(r.stdout), [0, 0, 1, 2, 2, 3, 3])

    def test_a_move_finds_its_clip_by_identity_and_lands_focus_on_its_row(self):
        body = "\n".join([
            "const r1 = x => Math.round(x * 10) / 10;",
            lift(r"  const clipKey = .+?;\n"),
            "let CLIPS = [], WROTE = null, TOAST = '';",
            "const trayClips = () => CLIPS.map(c => ({ ...c }));",
            "const writeTray = (clips, focus, origin) => { WROTE = { order: clips.map(c => c.pid), focus, origin }; CLIPS = clips; };",
            "const toast = m => { TOAST = m; };",
            lift(r"  function trayMove\(from, to, origin, key\) \{.+?\n  \}"),
            "const mk = p => ({ pid: p, kind: 'hit', t: 1 });",
            "const out = [];",
            "CLIPS = ['a', 'b', 'c', 'd'].map(mk); trayMove(0, 2, 'tray', clipKey(mk('a'))); out.push(WROTE, TOAST);",
            # another tab rewrote the tray mid-drag: the lifted clip moves, not whatever sits at its old index
            "CLIPS = ['d', 'a', 'b', 'c'].map(mk); WROTE = null; trayMove(0, 3, undefined, clipKey(mk('a'))); out.push(WROTE);",
            # the clip is gone: nothing is written
            "CLIPS = ['b', 'c'].map(mk); WROTE = null; trayMove(0, 1, 'tray', clipKey(mk('a'))); out.push(WROTE);",
            # past the end clamps to the end; a drop where it started writes nothing
            "CLIPS = ['a', 'b', 'c'].map(mk); trayMove(0, 99, 'tray', clipKey(mk('a'))); out.push(WROTE);",
            "CLIPS = ['a', 'b'].map(mk); WROTE = null; trayMove(1, 1, 'tray', clipKey(mk('b'))); out.push(WROTE);",
            "console.log(JSON.stringify(out));",
        ])
        r = run_node(body)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)
        self.assertEqual(got[0], {"order": ["b", "c", "a", "d"], "focus": {"act": "row", "i": 2, "quiet": True}, "origin": "tray"})
        self.assertEqual(got[1], "clip moved to 3 of 4")
        self.assertEqual(got[2]["order"], ["d", "b", "c", "a"])
        self.assertIsNone(got[3])
        self.assertEqual(got[4]["order"], ["b", "c", "a"])
        self.assertIsNone(got[5])

    def test_the_drag_survives_what_a_browser_does_to_it(self):
        """The review's routing harness (tests/drag_harness.js): capture lost
        when the grip leaves the page, events hit-tested after, a rAF queue,
        scroll moving the rects. v1 left a drag running forever after a
        repaint mid-drag (the page scrolled on its own until a reload), let a
        still press at an edge reorder a clip, took a second finger for a
        second drag, a pen's barrel for a drag, and Escape from the find box."""
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        r = subprocess.run([node, str(REPO / "tests" / "drag_harness.js")], capture_output=True, text=True,
                           env={**os.environ, "APPJS": str(REPO / "web" / "static" / "app.js")})
        self.assertEqual(r.returncode, 0, r.stderr)
        o = json.loads(r.stdout)
        # a plain drag commits once, lands focus quietly, and leaves nothing listening
        self.assertEqual(o["plain"]["order"], "bac")
        self.assertEqual(len(o["plain"]["writes"]), 1)
        self.assertEqual(o["plain"]["writes"][0]["focus"], {"act": "row", "i": 1, "quiet": True})
        self.assertEqual((o["plain"]["raf"], o["plain"]["listeners"]), (0, 0))
        # a repaint mid-drag ends it: no drop, no loop, no page scrolling on its own, Escape freed
        self.assertEqual(o["repaint"], {"moves": 0, "raf": 0, "scrolls": 0, "keyListeners": 0, "laterEscapePrevented": False})
        self.assertEqual(o["stillPress"], ["0:abcdef"] * 3)
        self.assertEqual(o["slot0"], {"top": "0px", "hidden": False, "order": "bac"})
        self.assertEqual(o["twoFingers"], {"lines": 1, "lifted": 1, "moves": 1, "raf": 0, "scrolls": 0})
        self.assertEqual(o["buttons"], {"penBarrel": "ignored", "penEraser": "ignored", "ctrlClick": "ignored",
                                        "right": "ignored", "pen": "drag"})
        self.assertEqual(o["escape"], {"cancelled": True, "otherRan": False, "prevented": True})
        self.assertEqual(o["duplicates"], "A A' B")
        self.assertEqual(o["lostRelease"], {"moves": 0, "raf": 0, "lifted": 0})
        self.assertEqual(o["blur"], {"raf": 0, "lifted": 0})
        # a finger or a pen on the number scrolls the page; only the ⠿ lifts a clip
        # (a pen there lifted the row, then the browser cancelled it — a re-review catch)
        self.assertEqual(o["touch"], {"number": "scrolls", "glyph": "drag", "penNumber": "scrolls"})
        self.assertEqual(o["fixed"], {"scrolls": 0})
        # a list hidden mid-drag (the panel collapsed, its mode switched) ends the
        # drag: every row measured nothing, and a drop landed anywhere ("acdefb")
        self.assertEqual(o["hidden"], {"moves": 0, "order": "abcd", "raf": 0, "lifted": 0})
        # a getComputedStyle that answers null neither throws nor leaves the drag stuck
        self.assertEqual(o["noStyle"], {"first": "bac", "second": "abc", "moves": 2})
        # a scroller half off the screen scrolls at the screen's edge
        self.assertGreater(o["offscreen"]["scrolled"], 0)
        # the last slot's line stays inside the rows of a list that does not scroll
        self.assertFalse(o["lastSlot"]["hidden"])
        self.assertLessEqual(o["lastSlot"]["top"], o["lastSlot"]["lowest"] - 3)

    def test_both_trays_carry_the_grip_and_keep_their_arrows(self):
        tray = lift(r"  function buildTray\(focus\) \{.+?\n  \}\n")
        self.assertIn('data-grip title="drag to move this clip — or use ↑ ↓"', tray)
        self.assertIn('data-act="up"', tray)
        self.assertIn('data-act="down"', tray)
        wire = lift(r"  function wireTray\(\) \{.+?\n  \}\n")
        self.assertIn('wireDrag($(".rt-clips", tray), ".rt-clip", (from, to, key) => trayMove(from, to, "tray", key));', wire)
        panel = lift(r"  function refreshReelSummary\(focus\) \{.+?\n  \}\n")
        self.assertIn('data-grip title="drag to move this clip — or use ↑ ↓"', panel)
        self.assertIn('wireDrag(rl, ".cz-rclip", (from, to, key) => trayMove(from, to, undefined, key));', panel)
        # the panel list keeps its scroll across the repaint a move makes
        self.assertIn('const keepScroll = ($(".cz-rclips", body) || {}).scrollTop || 0;', panel)
        self.assertIn("if (t) t.focus(focus.quiet ? { preventScroll: true } : undefined);", panel)
        css = (REPO / "web" / "static" / "app.web.css").read_text(encoding="utf-8")
        # a drop (or a removal) lands the meeting tray's focus on the row's
        # quote, never its first button (◀ start earlier: a Space would trim)
        self.assertIn('<div class="rt-quote" tabindex="-1">', tray)
        self.assertIn('focus.act === "row" ? $(".rt-quote", row)', tray)
        # only the glyph refuses the page's scroll: a finger on the number still scrolls
        self.assertIn("[data-grip]{cursor:grab;user-select:none", css)
        self.assertNotIn("[data-grip]{cursor:grab;touch-action:none", css)
        self.assertRegex(css, r"\.dg-grip\{[^}]*touch-action:none")



class TestTheGlossary(unittest.TestCase):
    """"What is a warrant article?" — answered on the record's own page, with
    its source and the record's count of it town by town, each count landing
    on its own number in the search, and one press from any meeting that
    says it."""

    @classmethod
    def setUpClass(cls):
        from memory.store import Corpus
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        db = root / "corpus.db"
        c = Corpus(str(db))
        nights = {
            "g1": ("2026-03-10", "Testville", "Select Board", ["we open the meeting", "the warrant article on free cash",
                                                               "free cash again and the override", "the reserve fund", "adjourned"]),
            "g2": ("2026-01-13", "Testville", "Select Board", ["the override question", "Town Meeting will vote",
                                                               "the warrant articles", "", "adjourned"]),
            "g3": ("2026-02-02", "Testville", "Select Board", ["we discuss parking", "and parking again", "adjourned"]),
            # a Boston council says Brookline's word and Boston's own
            "b1": ("2026-02-20", "Otherton", "City Council", ["the advisory committee of the port", "docket 1317",
                                                              "free cash", "adjourned"]),
        }
        for mid, (date, town, body, ls) in nights.items():
            segs = [{"start": i * 10.0, "end": i * 10 + 9, "speaker": "", "text": t} for i, t in enumerate(ls)]
            c.replace_segments(mid, segs)
            c.upsert_meeting({"id": mid, "title": f"{body} — {date}", "date": date, "town": town, "body": body,
                              "source_kind": "youtube", "video_id": mid, "url": f"https://youtube.com/watch?v={mid}",
                              "url_canon": f"youtube:{mid}", "duration": 10.0 * len(ls), "n_segments": len(segs),
                              "status": "live", "summary": "", "analysis_json": "{}"})
        from web import bake
        cls.out = root / "app"
        bake.bake(str(db), str(cls.out), "9.9.9", "https://example.org")
        cls.page = (cls.out / "glossary" / "index.html").read_text()

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def entry(self, slug):
        e = self.page[self.page.index(f'id="{slug}"'):]
        return e[:e.index("</section>")]

    def test_the_page_explains_every_word_with_its_source_and_its_count(self):
        from web import glossary
        page = self.page
        self.assertIn("<h1>The words the record uses</h1>", page)
        self.assertIn('<h2 class="gl-gtitle">The money</h2>', page)          # h1, h2, h3 — no skipped level
        for e in glossary.ENTRIES:
            self.assertIn(f'<section class="gl-entry" id="{e["slug"]}">', page)
            self.assertIn(f'<a href="#{e["slug"]}">', page)            # the A–Z index reaches it
        # a Massachusetts word, counted town by town — each count its town's search
        free = self.entry("free-cash")
        self.assertIn('Testville: <a href="/app/s?q=free%20cash&amp;town=Testville">2 times</a> in 1 meeting, '
                      'first <a href="/app/m/g1#t10">on March 10, 2026</a>', free)
        self.assertIn('Otherton: <a href="/app/s?q=free%20cash&amp;town=Otherton">1 time</a> in 1 meeting', free)
        self.assertIn('href="https://www.mass.gov/info-details/municipal-finance-glossary" rel="noopener"', free)
        # "warrant article" and "warrant articles" both say "warrant"; a blank caption line is no line
        self.assertIn("2 times</a> in 2 meetings, first <a href=\"/app/m/g2#t20\">", self.entry("warrant"))
        self.assertIn("not yet — the record has not heard it said", page)

    def test_a_town_word_is_counted_only_in_its_town(self):
        """Brookline's Advisory Committee is not a Boston port's advisory
        committee, and Boston's docket is not a town's (a review catch: the
        City Council entry's first mention was a Brookline aside)."""
        from web import glossary
        from web.bake import Bake
        from czcore.paths import media_dir
        from memory.store import Corpus
        meetings = [
            {"pid": "bk", "date": "2026-01-01", "town": "Brookline", "segments": [{"start": 0, "text": "the advisory committee votes"}, {"start": 5, "text": "the docket for town meeting"}]},
            {"pid": "bo", "date": "2026-01-02", "town": "Boston", "segments": [{"start": 0, "text": "the advisory committee of the port"}, {"start": 5, "text": "docket 1317 is placed on file"}]},
        ]
        c = glossary.count(meetings)
        self.assertEqual(sorted(c["advisory-committee"]["towns"]), ["Brookline"])
        self.assertEqual(sorted(c["docket"]["towns"]), ["Boston"])
        self.assertEqual(glossary.terms_on(meetings[1], c), [{"slug": "docket", "term": "docket", "n": 1}])

    def test_the_fast_count_is_the_story_engines_rule_line_for_line(self):
        """One regex pass over the night instead of one per line (the count
        took 43% of a press): held to the per-line rule on the edges — a
        phrase broken across two lines, one run across three, a blank line,
        a match on the joining space, the night's first and last lines."""
        from web import glossary, topic
        lines = ["free", "cash and free cash", "", "the free", "short", "cash", "Free Cash.", "free-cash free cashier",
                 "overlay", "district", "and overlay districts", "tax free", "cash"]
        segs = [{"start": float(i), "text": t} for i, t in enumerate(lines)]
        for phrases in (["free cash"], ["overlay district", "overlay districts", "overlay zoning"], ["cash"], ["free"]):
            pats = [(topic.phrase_re(p), p.lower()) for p in phrases]
            got = glossary._night_counts(glossary._lines({"segments": segs}), pats)
            kept = [t for _, t in glossary._lines({"segments": segs})]
            ps = [topic.phrase_re(p) for p in phrases]
            want = sum(topic.mentions_in(t, kept[i + 1] if i + 1 < len(kept) else "", ps) for i, t in enumerate(kept))
            self.assertEqual(got[0], want, phrases)

    def test_each_count_lands_on_its_own_number_in_the_search(self):
        """The search page reads glossary/index.json and counts an entry's
        words its way — executed over the pressed index, as the featured
        words' test does."""
        from tests.test_web_topic import TestTopicTwins
        idx = json.loads((self.out / "glossary" / "index.json").read_text())
        free = next(r for r in idx if r["slug"] == "free-cash")
        self.assertEqual(free, {"slug": "free-cash", "q": "free cash", "phrases": ["free cash"], "towns": ["Otherton", "Testville"],
                                "only": []})
        self.assertFalse(any(r["slug"] == "variance" for r in idx))      # an unsaid word is not indexed
        tw = TestTopicTwins()
        body = "\n".join([
            tw.PRELUDE, tw.helpers(),
            "const fs = require('fs');",
            f"const OUT = {json.dumps(str(self.out))};",
            "const getJSON = async u => { try { return JSON.parse(fs.readFileSync(OUT + u.slice(4), 'utf8')); } catch (e) { return null; } };",
            "let SCOPE = { town: 'Testville', body: '' };",
            tw.lift(r"const inScope = \(town, body\) =>.+?;\n"),
            tw.lift(r"  function sqHits\(idx, ids, phrases\) \{.+?\n  \}"),
            tw.lift(r"  async function sqIds\(idx, terms, q\) \{.+?\n  \}"),
            tw.lift(r"  async function sqFeatured\(q\) \{.+?\n  \}"),
            tw.lift(r"  async function sqPhraseIds\(idx, phrases\) \{.+?\n  \}"),
            "(async () => {",
            "  const idx = { meta: await getJSON('/app/search/meta.json'), segs: await getJSON('/app/search/segs.json') };",
            "  const meetings = idx.meta.filter(m => inScope(m.town || '', m.body || '')).map(m => ({ pid: m.pid, title: m.title, date: m.date, body: m.body, town: m.town, duration: +m.duration || 0 }));",
            "  const feat = await sqFeatured('free cash');",
            "  const d = tpAggregate(meetings, sqHits(idx, await sqPhraseIds(idx, feat.phrases), feat.phrases), { slug: '', name: 'free cash', q: 'free cash', phrases: feat.phrases }, 'Testville', false);",
            "  console.log(JSON.stringify({ kind: feat.kind, mentions: d.mentions, meetings: d.n_meetings }));",
            "})().catch(e => { console.log('THREW ' + e.stack); process.exit(1); });",
        ])
        r = tw.node(body)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        got = json.loads(r.stdout.strip().splitlines()[-1])
        self.assertEqual(got, {"kind": "glossary", "mentions": 2, "meetings": 1})     # the glossary's Testville: 2 in 1

    def test_the_page_says_which_half_a_model_wrote_and_that_no_person_has_read_it(self):
        from web import glossary
        self.assertIn(f"written with {glossary.WRITTEN_WITH}", self.page)
        self.assertIn("on Anthropic’s\n      servers", self.page)
        self.assertIn("never at\n      press time, never in your browser", self.page)
        self.assertFalse(glossary.REVIEWED)
        self.assertIn("No person has yet read them against their sources", self.page)
        self.assertIn("no model counts them", self.page)
        self.assertIn("the developers used while writing this code", self.page)
        self.assertIn("over the transcripts of the towns each\n      word belongs to", self.page)
        ai = (self.out / "ai" / "index.html").read_text()
        row = ai[ai.index("<tr><td>the glossary</td>"):]
        row = row[:row.index("</tr>")]
        self.assertIn("Anthropic <code>Claude</code>", row)
        self.assertIn("never at press time", row)
        self.assertNotIn("the desk,", row)                          # the desk means your machine; Claude is not there
        # the ledger names the glossary's own model — they cannot drift apart
        self.assertIn(f"(<code>{glossary.MODEL}</code>)", row)
        self.assertIn(glossary.MODEL, glossary.WRITTEN_WITH)
        self.assertIn("used while writing this code", row)

    def test_every_source_is_a_public_one_it_names(self):
        from web import glossary
        allowed = ("https://malegislature.gov/Laws/GeneralLaws/", "https://www.mass.gov/", "https://www.brooklinema.gov/",
                   "https://www.boston.gov/", "https://www.bostonplans.org/", "https://www.communitypreservation.org/",
                   "https://metcoinc.org/", "https://www.doe.mass.edu/", "/app/")
        for e in glossary.ENTRIES:
            self.assertTrue(e["sources"], f"{e['slug']} names no source")
            for name, url in e["sources"]:
                self.assertTrue(url.startswith(allowed), f"{e['slug']}: {url}")
                self.assertTrue(name.strip())
            self.assertTrue(e["phrases"] and e["where"] and e["says"].endswith("."), e["slug"])
            self.assertIn(e["group"], dict(glossary.GROUPS))
        self.assertEqual(len({e["slug"] for e in glossary.ENTRIES}), len(glossary.ENTRIES))
        # the facts a review corrected stay corrected
        says = {e["slug"]: e["says"] for e in glossary.ENTRIES}
        self.assertIn("a fund set up for one named purpose can be spent by a simple majority", says["stabilization-fund"])
        self.assertIn("Boston is the exception", says["zoning"])
        self.assertIn("safe harbors", says["chapter-40b"])
        # the 177 already leave Boston out, and only part of a district sits near a station
        self.assertIn("177 cities and towns in and around the MBTA’s service area — Boston, served by the MBTA "
                      "but outside the Zoning Act, is not one of them", says["mbta-communities"])
        self.assertIn("in part within half a mile of it", says["mbta-communities"])
        self.assertIn("ride on top of the limit", says["levy"])
        self.assertIn("the state’s glossary counts exclusions into the limit", says["levy"])
        self.assertNotIn("harms no one", says["variance"])
        self.assertIn("Putting money in takes a simple majority", says["stabilization-fund"])
        self.assertIn("strategy for collective bargaining or litigation", says["executive-session"])
        # where the two differ the source is the authority: the statute is named first
        src = {e["slug"]: e["sources"] for e in glossary.ENTRIES}
        for slug in ("levy", "proposition-2-half"):
            self.assertTrue(src[slug][0][0].startswith("M.G.L. c. 59 § 21C"), slug)
        # Boston's zoning rests on its Enabling Act, and its sentence cites it
        for slug in ("zoning", "zoning-board-of-appeals"):
            self.assertIn(glossary.BOS_EA, src[slug], slug)

    def test_every_phrase_is_trimmed_and_every_query_is_its_own(self):
        """A phrase with a space at either end would count a match on the
        joining space (the fast count assumes none) and the reader trims what
        the press does not; and a glossary query that equals another's, or a
        featured word's, would send its count link to the other's number."""
        from web import glossary, topic
        for e in glossary.ENTRIES:
            for ph in e["phrases"]:
                self.assertEqual(ph, " ".join(ph.split()), f"{e['slug']}: {ph!r}")
        qs = [glossary.q_of(e).strip().lower() for e in glossary.ENTRIES]
        self.assertEqual(len(qs), len(set(qs)))
        featured = {str(t.get("q") or t.get("name") or t["slug"]).strip().lower() for t in topic.FEATURED}
        self.assertFalse(featured & set(qs), featured & set(qs))

    def test_a_count_with_no_town_is_said_not_linked_and_an_undated_night_is_never_first(self):
        """No search can be pinned to "meetings with no town recorded", so
        that count is said, not linked (it could never land on its number);
        and a day that is not a whole date ("2026", "TBD") is undated — it
        sorts last and is never where a word was first said."""
        from web import glossary
        meetings = [
            {"pid": "nt", "date": "2026-02-02", "town": "", "segments": [{"start": 4, "text": "free cash here"}]},
            {"pid": "yr", "date": "2026", "town": "Testville", "segments": [{"start": 1, "text": "free cash first?"}]},
            {"pid": "ok", "date": "2026-03-03", "town": "Testville", "segments": [{"start": 7, "text": "free cash"}]},
        ]
        c = glossary.count(meetings)
        self.assertEqual(c["free-cash"]["towns"]["Testville"]["first"], {"pid": "ok", "date": "2026-03-03", "t": 7.0})
        html = glossary.body(meetings, "/app", c)
        e = html[html.index('id="free-cash"'):]
        e = e[:e.index("</section>")]
        self.assertIn("meetings with no town recorded: 1 time in 1 meeting", e)
        self.assertNotIn('href="/app/s?q=free%20cash"', e)             # no town-less search link
        self.assertIn('href="/app/s?q=free%20cash&amp;town=Testville"', e)
        self.assertEqual(glossary._day("TBD"), "in an undated meeting")
        self.assertEqual(glossary._day("2026"), "in an undated meeting")
        self.assertEqual(glossary._day("2026-03-03"), "on March 3, 2026")
        # a meeting that said only "no action" is not named "favorable action"
        n = [{"pid": "na", "date": "2026-01-01", "town": "Brookline", "segments": [{"start": 0, "text": "no action on it"}]}]
        self.assertEqual(glossary.terms_on(n[0], glossary.count(n)),
                         [{"slug": "favorable-action", "term": "favorable action / no action", "n": 1}])

    def test_the_search_page_credits_the_glossary_only_where_its_count_applies(self):
        """A Boston search for Brookline's "advisory committee" counts lines
        the glossary leaves out on purpose — the page does not credit the
        glossary's count there (a re-review catch)."""
        from web import glossary
        idx = {r["slug"]: r for r in glossary.index(glossary.count([
            {"pid": "bk", "date": "2026-01-01", "town": "Brookline", "segments": [{"start": 0, "text": "the advisory committee"}]}]))}
        self.assertEqual(idx["advisory-committee"]["only"], ["Brookline"])
        story = JS[JS.index("async function sqStory("):JS.index("function sqTray(")]
        self.assertIn('(!feat.only.length || feat.only.includes(SCOPE.town || "") ? `, the words <a href="${BASE}/glossary/#', story)

    def test_a_phrase_finds_the_entry_that_explains_it(self):
        from web import glossary
        self.assertEqual(glossary.entry_for("warrant article")["slug"], "warrant")
        self.assertEqual(glossary.entry_for("Warrant Articles")["slug"], "warrant")
        self.assertEqual(glossary.entry_for("  free   cash ")["slug"], "free-cash")
        self.assertEqual(glossary.entry_for("levies")["slug"], "levy")
        self.assertEqual(glossary.entry_for("capital improvement plan")["slug"], "capital-improvement-plan")
        # an acronym that spells a word stands only as written: a pilot program is not a PILOT
        self.assertIsNone(glossary.entry_for("pilot"))
        self.assertEqual(glossary.entry_for("PILOT")["slug"], "pilot")
        # every other acronym is the same word in any case — the analyzer's topics are lowercase
        for word, slug in (("40b", "chapter-40b"), ("zba", "zoning-board-of-appeals"), ("cip", "capital-improvement-plan"),
                           ("bpda", "bpda"), ("dese", "dese"), ("metco", "metco"), ("fy27", "fiscal-year"), ("FY27", "fiscal-year"),
                           ("overlay", "overlay-district"), ("overlays", "overlay-district"),
                           ("MBTA community", "mbta-communities")):
            self.assertEqual((glossary.entry_for(word) or {}).get("slug"), slug, word)
        self.assertIsNone(glossary.entry_for("parking"))
        self.assertIsNone(glossary.entry_for(""))

    def test_a_meeting_page_names_the_words_it_uses_and_where_they_are_explained(self):
        g1 = (self.out / "m" / "g1" / "index.html").read_text()
        line = g1[g1.index('<p class="mp-terms">'):]
        line = line[:line.index("</p>")]
        # most-said first; ties by name, case-blind; a heading's first name only
        self.assertIn('<a href="/app/glossary/#free-cash">free cash</a> · <a href="/app/glossary/#override">override</a> · '
                      '<a href="/app/glossary/#reserve-fund">reserve fund</a> · <a href="/app/glossary/#warrant">warrant</a>', line)
        self.assertIn('<a href="/app/glossary/">the glossary</a> says what they mean', line)
        g3 = (self.out / "m" / "g3" / "index.html").read_text()
        self.assertNotIn('class="mp-terms"', g3)                      # parking is not a glossary word
        b1 = (self.out / "m" / "b1" / "index.html").read_text()
        self.assertNotIn("#advisory-committee", b1)                  # a Brookline word is not Otherton's

    def test_the_section_line_carries_it_and_the_page_is_byte_clean(self):
        home = (self.out / "index.html").read_text()
        self.assertIn('<a class="navlink" href="/app/glossary/">The glossary</a>', home)
        self.assertIn('<a class="navlink active" href="/app/glossary/">The glossary</a>', self.page)
        body = self.page[self.page.index('<section class="glpage">'):self.page.index("</main>")]
        for bad in ("<button", "cz-", "#a855f7", "#7c3aed", "#22c55e", "onclick"):
            self.assertNotIn(bad, body)


class TestTheDeskIsOneClickAway(unittest.TestCase):
    """Wherever the record says a step needs the desk — render a reel, cut a
    kit, run a model locally — it hands over the desk: Civic Media Studio's
    DMG, one click (Stephen, 2026-09-24; specs/28 §3.5)."""

    DMG = "https://github.com/amateurmenace/control-z/releases/download/v2.1.0/civicmedia-studio-2.1.0-macos-arm64.dmg"

    def test_one_address_in_the_press_and_the_reader(self):
        from web import emit
        self.assertEqual(emit.DESK_DMG, self.DMG)
        self.assertIn(f'const DESK_DMG = "{self.DMG}";', JS)
        self.assertIn('rel="noopener"', emit.desk_button())
        self.assertNotIn("<button", emit.desk_button())             # a pressed anchor, content in the paper

    def test_the_pages_that_need_the_desk_hand_it_over(self):
        from tests.test_web_topic import TestTopicPress
        from web import bake
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "c.db"
            TestTopicPress._seed(db)
            out = Path(d) / "app"
            bake.bake(str(db), str(out), "9.9.9", "https://example.org")
            for page in ("press/index.html", "r/index.html", "ai/index.html", "k/index.html"):
                html = (out / page).read_text()
                self.assertIn(f'href="{self.DMG}"', html, page)
            press = (out / "press" / "index.html").read_text()
            self.assertIn("↓ Get the desktop app — macOS</a>", press)
            # the reel page says it once, and true of any reel: one meeting's renders at the desk
            reel = (out / "r" / "index.html").read_text()
            self.assertIn("A reel of one meeting renders as a video at the desk", reel)
            self.assertIn('every release →</a>', press)                 # the releases page stays one link on

    def test_a_single_meeting_reel_offers_the_desk_and_a_reel_across_meetings_does_not(self):
        viewer = JS[JS.index('cites.innerHTML = head + `<div class="reelcitelist">'):]
        viewer = viewer[:viewer.index("</p>`;")]
        self.assertIn('${multi ? "" : deskBtn()}', viewer)
        # the page's pressed line says the desk renders one meeting's reel; the viewer does not say it twice
        self.assertNotIn("Rendering it as a video needs the desk", viewer)
        self.assertIn("rendering one video across meetings is a desk step still to come", viewer)
        tray = lift(r"  function buildTray\(focus\) \{.+?\n  \}\n")
        self.assertIn('${multi ? "" : deskBtn()}', tray)
        panel = lift(r"  function refreshReelSummary\(focus\) \{.+?\n  \}\n")
        self.assertIn('(meets > 1 ? "" : deskBtn("↓ the desktop app"))', panel)
        r = run_node("const esc = s => String(s == null ? '' : s);" + lift(r"  const DESK_DMG = .+?;\n") + lift(r"  const deskBtn = .+?;\n")
                     + "console.log(deskBtn());")
        self.assertEqual(r.returncode, 0, r.stderr)
        self.assertIn(f'href="{self.DMG}"', r.stdout)


if __name__ == "__main__":
    unittest.main()
