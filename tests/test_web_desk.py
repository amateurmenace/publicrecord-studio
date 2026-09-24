"""The desk's last pieces, in the paper (specs/27 §3): drag to reorder on
the tray, and the glossary. Executed twins over token pins — the reader's
own functions lifted and run in node against a small fake of the DOM they
touch, the way the review folds before this one were pinned."""

import json
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
        self.assertEqual(got[0], {"order": ["b", "c", "a", "d"], "focus": {"act": "row", "i": 2}, "origin": "tray"})
        self.assertEqual(got[1], "clip moved to 3 of 4")
        self.assertEqual(got[2]["order"], ["d", "b", "c", "a"])
        self.assertIsNone(got[3])
        self.assertEqual(got[4]["order"], ["b", "c", "a"])
        self.assertIsNone(got[5])

    def test_a_drag_drops_cancels_and_ignores_what_it_should(self):
        body = "\n".join([
            FAKE_DOM,
            "const r1 = x => Math.round(x * 10) / 10;",
            lift(r"  const clipKey = .+?;\n"),
            "let CLIPS = ['a', 'b', 'c'].map(p => ({ pid: p, kind: 'hit', t: 1 }));",
            "const trayClips = () => CLIPS.map(c => ({ ...c }));",
            lift(r"  const dgSlot = .+?;\n"),
            lift(r"  function wireDrag\(list, rowSel, onMove\) \{.+?\n  \}\n"),
            "const MOVES = []; wireDrag(LIST, '.row', (f, t, k) => MOVES.push([f, t, k]));",
            "const setRows = n => { ROWS = Array.from({ length: n }, (_, i) => rowAt(i, i * 50)); for (const r of ROWS) { r.closest = closestOf(r); r.grip.closest = closestOf(r.grip); } };",
            "const press = (i, extra) => LIST.fire('pointerdown', { target: ROWS[i].grip, pointerType: 'mouse', button: 0, pointerId: 1, clientY: ROWS[i].rect.top + 5, preventDefault() {}, ...(extra || {}) });",
            "const out = {};",
            # a drag from the first row to below the third drops it at the end
            "setRows(3); press(0); ROWS[0].grip.fire('pointermove', { clientY: 130 });",
            "out.lifted = ROWS[0].classList.contains('dg-lift'); out.line = LIST.kids.length === 1 && !LIST.kids[0].hidden;",
            "out.lineTop = LIST.kids[0].style.top;",
            "ROWS[0].grip.fire('pointerup', { type: 'pointerup', clientY: 130 });",
            "out.drop = MOVES.slice(); out.cleaned = !ROWS[0].classList.contains('dg-lift') && LIST.kids.length === 0;",
            # Esc puts it back: no move, everything cleaned
            "MOVES.length = 0; setRows(3); press(2); ROWS[2].grip.fire('pointermove', { clientY: 10 });",
            "DOC.fire('keydown', { key: 'Escape', preventDefault() {} });",
            "ROWS[2].grip.fire('pointerup', { type: 'pointerup', clientY: 10 });",
            "out.esc = MOVES.slice(); out.escClean = LIST.kids.length === 0;",
            # a right-click is not a drag, and one clip has nowhere to go
            "setRows(3); press(0, { button: 2 }); out.right = LIST.kids.length;",
            "setRows(1); press(0); out.alone = LIST.kids.length;",
            # a drop back where it started moves nothing
            "setRows(3); press(1); ROWS[1].grip.fire('pointermove', { clientY: 70 }); ROWS[1].grip.fire('pointerup', { type: 'pointerup' }); out.same = MOVES.length;",
            "console.log(JSON.stringify(out));",
        ])
        r = run_node(body)
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        got = json.loads(r.stdout)
        self.assertTrue(got["lifted"])
        self.assertTrue(got["line"])
        self.assertEqual(got["lineTop"], "141px")            # under the last other row
        self.assertEqual(got["drop"], [[0, 2, "a@hit@1"]])
        self.assertTrue(got["cleaned"])
        self.assertEqual(got["esc"], [])
        self.assertTrue(got["escClean"])
        self.assertEqual(got["right"], 0)
        self.assertEqual(got["alone"], 0)
        self.assertEqual(got["same"], 0)

    def test_both_trays_carry_the_grip_and_keep_their_arrows(self):
        tray = lift(r"  function buildTray\(focus\) \{.+?\n  \}\n")
        self.assertIn('data-grip title="drag to move this clip — or use ↑ ↓"', tray)
        self.assertIn('data-act="up"', tray)
        self.assertIn('data-act="down"', tray)
        wire = lift(r"  function wireTray\(\) \{.+?\n  \}\n")
        self.assertIn('wireDrag($(".rt-clips", tray), ".rt-clip", (from, to, key) => trayMove(from, to, "tray", key));', wire)
        panel = lift(r"  function refreshReelSummary\(focus\) \{.+?\n  \}\n")
        self.assertIn('data-grip title="drag to move this clip — or use ↑ ↓"', panel)
        self.assertIn('wireDrag($(".cz-rclips", body), ".cz-rclip", (from, to, key) => trayMove(from, to, undefined, key));', panel)
        css = (REPO / "web" / "static" / "app.web.css").read_text(encoding="utf-8")
        self.assertIn("[data-grip]{cursor:grab;touch-action:none", css)   # a finger drags; the page does not scroll instead



class TestTheGlossary(unittest.TestCase):
    """"What is a warrant article?" — answered on the record's own page, with
    its source and the record's count of it, and one press from any meeting
    that says it."""

    @classmethod
    def setUpClass(cls):
        from memory.store import Corpus
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        db = root / "corpus.db"
        c = Corpus(str(db))
        nights = {
            "g1": ("2026-03-10", "Select Board", ["we open the meeting", "the warrant article on free cash",
                                                  "free cash again and the override", "the reserve fund", "adjourned"]),
            "g2": ("2026-01-13", "Select Board", ["the override question", "Town Meeting will vote",
                                                  "the warrant articles", "adjourned"]),
            "g3": ("2026-02-02", "Select Board", ["we discuss parking", "and parking again", "adjourned"]),
        }
        for mid, (date, body, ls) in nights.items():
            segs = [{"start": i * 10.0, "end": i * 10 + 9, "speaker": "", "text": t} for i, t in enumerate(ls)]
            c.replace_segments(mid, segs)
            c.upsert_meeting({"id": mid, "title": f"{body} — {date}", "date": date, "town": "Testville", "body": body,
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

    def test_the_page_explains_every_word_with_its_source_and_its_count(self):
        from web import glossary
        page = self.page
        self.assertIn("<h1>The words the record uses</h1>", page)
        for e in glossary.ENTRIES:
            self.assertIn(f'<section class="gl-entry" id="{e["slug"]}">', page)
            self.assertIn(f'<a href="#{e["slug"]}">', page)            # the A–Z index reaches it
        free = page[page.index('id="free-cash"'):]
        free = free[:free.index("</section>")]
        self.assertIn('<a href="/app/s?q=free%20cash">2 times</a> in 1 meeting — first on '
                      '<a href="/app/m/g1#t10">', free)
        self.assertIn('href="https://www.mass.gov/info-details/municipal-finance-glossary" rel="noopener"', free)
        # the warrant is counted whole-word: "warrant article" and "warrant articles" both say it
        warrant = page[page.index('id="warrant"'):]
        self.assertIn("2 times</a> in 2 meetings — first on <a href=\"/app/m/g2#t20\">", warrant[:warrant.index("</section>")])
        # a word the record never said says so, and is not a link to nothing
        self.assertIn("not yet — the record has not heard it said", page)

    def test_the_page_says_which_half_a_model_wrote(self):
        self.assertIn("written with Claude, Anthropic’s model, at the desk", self.page)
        self.assertIn("no model counts them", self.page)
        ai = (self.out / "ai" / "index.html").read_text()
        row = ai[ai.index("<tr><td>the glossary</td>"):]
        row = row[:row.index("</tr>")]
        self.assertIn("Anthropic <code>Claude</code>", row)
        self.assertIn("never at press time", row)

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
            self.assertEqual(e["group"], e["group"].strip())
            self.assertIn(e["group"], dict(glossary.GROUPS))
        self.assertEqual(len({e["slug"] for e in glossary.ENTRIES}), len(glossary.ENTRIES))

    def test_a_phrase_finds_the_entry_that_explains_it(self):
        from web import glossary
        self.assertEqual(glossary.entry_for("warrant article")["slug"], "warrant")
        self.assertEqual(glossary.entry_for("Warrant Articles")["slug"], "warrant")
        self.assertEqual(glossary.entry_for("  free   cash ")["slug"], "free-cash")
        self.assertEqual(glossary.entry_for("capital improvement plan")["slug"], "capital-improvement-plan")
        self.assertIsNone(glossary.entry_for("parking"))
        self.assertIsNone(glossary.entry_for(""))

    def test_a_meeting_page_names_the_words_it_uses_and_where_they_are_explained(self):
        g1 = (self.out / "m" / "g1" / "index.html").read_text()
        line = g1[g1.index('<p class="mp-terms">'):]
        line = line[:line.index("</p>")]
        # most-said first: free cash (3), then override, reserve fund, warrant (1 each, by name)
        self.assertIn('<a href="/app/glossary/#free-cash">free cash</a> · <a href="/app/glossary/#override">override</a>', line)
        self.assertIn('<a href="/app/glossary/">the glossary</a> says what they mean', line)
        g3 = (self.out / "m" / "g3" / "index.html").read_text()
        self.assertNotIn('class="mp-terms"', g3)                      # parking is not a glossary word

    def test_the_section_line_carries_it_and_the_page_is_byte_clean(self):
        home = (self.out / "index.html").read_text()
        self.assertIn('<a class="navlink" href="/app/glossary/">The glossary</a>', home)
        self.assertIn('<a class="navlink active" href="/app/glossary/">The glossary</a>', self.page)
        body = self.page[self.page.index('<section class="glpage">'):self.page.index("</main>")]
        for bad in ("<button", "cz-", "#a855f7", "#7c3aed", "#22c55e", "onclick"):
            self.assertNotIn(bad, body)


if __name__ == "__main__":
    unittest.main()
