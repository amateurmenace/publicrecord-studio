"""The web edition bake — canon twin, idempotence, structure, budgets.

Offline and hermetic: a tiny throwaway corpus.db is built with two meetings
and one cross-meeting issue, pressed to a temp dir, and checked. No network,
no real corpus, no suite server.
"""

import json
import re
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from web import canon, emit, tools

REPO = Path(__file__).resolve().parents[1]

# The golden table — the ONE truth both twins answer (web/canon.py and the
# canon() in web/static/app.js). specs/16 §P0.4.
GOLDEN = [
    ("https://www.youtube.com/watch?v=2YhgO14jXys", "youtube:2YhgO14jXys"),
    ("https://youtu.be/2YhgO14jXys?si=abcDEF", "youtube:2YhgO14jXys"),
    ("https://www.youtube.com/watch?v=2YhgO14jXys&list=PL&index=3", "youtube:2YhgO14jXys"),
    ("https://youtube.com/live/wAFa8pUa4IQ", "youtube:wAFa8pUa4IQ"),
    ("2YhgO14jXys", "youtube:2YhgO14jXys"),
    ("https://brooklinema.portal.civicclerk.com/event/1234/overview",
     "url:https://brooklinema.portal.civicclerk.com/event/1234/overview"),
    ("https://example.org/mtg?utm_source=x&feature=y", "url:https://example.org/mtg"),
    ("https://example.org/mtg#t=90", "url:https://example.org/mtg"),
    ("", ""),
]


class TestCanonTwin(unittest.TestCase):
    def test_python_canon_matches_golden(self):
        for url, want in GOLDEN:
            self.assertEqual(canon.canon(url), want, f"canon({url!r})")

    def test_js_twin_regexes_match_python(self):
        """A cheap structural guard: the strip-param set and the video-id host
        markers appear in both twins. (The rigorous check is
        test_js_canon_runs_the_golden_table, which executes the real reader
        code; JS regex literals escape '/' as '\\/', so a verbatim string
        compare would false-fail — this checks the slash-free parts.)"""
        js = (REPO / "web" / "static" / "app.js").read_text()
        py = (REPO / "web" / "canon.py").read_text()
        strip = r"(utm_[^=&]+|feature|si|list|index|t)=[^&]*"
        for token in (strip, "youtu", "shorts", "embed", r"([\w-]{11})"):
            self.assertIn(token, py, f"{token!r} missing from web/canon.py")
            self.assertIn(token, js, f"{token!r} drifted in web/static/app.js")

    def test_js_canon_runs_the_golden_table(self):
        """Actually execute the reader's canon() in node against the table —
        the real twin check, not just a structural one. Skips if node absent."""
        import shutil
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        js = (REPO / "web" / "static" / "app.js").read_text()
        # lift the three regexes + videoId + canon out of the IIFE
        grab = lambda name, pat: re.search(pat, js).group(0)
        body = "\n".join([
            re.search(r"const VIDEO_ID = .+?;", js).group(0),
            re.search(r"const BARE_ID = .+?;", js).group(0),
            re.search(r"const STRIP = .+?;", js).group(0),
            re.search(r"function videoId\(s\) \{.+?\n  \}", js, re.S).group(0),
            re.search(r"function canon\(url\) \{.+?\n  \}", js, re.S).group(0),
            "const T=" + json.dumps(GOLDEN) + ";",
            "for (const [u,w] of T){ if(canon(u)!==w){ "
            "console.log('FAIL',u,'->',canon(u),'want',w); process.exit(1);} }",
            "console.log('ok');",
        ])
        r = subprocess.run([node, "-e", body], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0,
                         f"JS canon disagreed with the golden table:\n{r.stdout}{r.stderr}")


class TestScopeResolution(unittest.TestCase):
    """The reader's `resolve()` decides which town every page obeys, and it is
    the one place specs/17 §14's trap is either sprung or defused. So it is
    executed for real in node against a table, rather than trusted to reading
    — the same treatment canon() gets, for the same reason."""

    # (label, edition towns, stored choice, query string, expected fields)
    TABLE = [
        ("two towns, first visit: nothing is presumed",
         ["Brookline", "Boston"], None, "", {"town": "", "from": "none"}),
        ("the stored choice governs",
         ["Brookline", "Boston"], "Brookline", "", {"town": "Brookline", "from": "stored"}),
        ("a ?town= link overrides the choice WITHOUT replacing it",
         ["Brookline", "Boston"], "Brookline", "?town=Boston",
         {"town": "Boston", "from": "link", "stored": "Brookline"}),
        ("the link's town is matched case-insensitively",
         ["Brookline", "Boston"], None, "?town=bOsToN",
         {"town": "Boston", "from": "link"}),
        ("a ?town= naming a town this edition lacks scopes to nothing, "
         "rather than to a town that looks close",
         ["Brookline", "Boston"], "Brookline", "?town=Cambridge",
         {"town": "", "from": "link", "stored": "Brookline"}),
        ("one town: scoped without ever being asked",
         ["Brookline"], None, "", {"town": "Brookline", "from": "only"}),
        ("a stored town this pressing dropped is reported, not obeyed",
         ["Boston"], "Brookline", "", {"town": "", "lost": "Brookline"}),
        ("?town= empty means the whole record for this visit",
         ["Brookline", "Boston"], "Brookline", "?town=",
         {"town": "", "from": "link-all"}),
        ("the body filter rides alongside the town",
         ["Brookline"], None, "?body=Select+Board",
         {"town": "Brookline", "body": "Select Board"}),
    ]

    def test_resolve_runs_in_node(self):
        import shutil
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        js = (REPO / "web" / "static" / "app.js").read_text()
        fn = re.search(r"  function resolve\(ed\) \{.+?\n  \}", js, re.S)
        self.assertTrue(fn, "resolve() not found in the reader — did it move?")
        cases = [{"label": l, "towns": t, "stored": s, "qs": q, "want": w}
                 for l, t, s, q, w in self.TABLE]
        body = "\n".join([
            "let STORED = null, QS = '';",
            "const readTown = () => STORED || '';",
            "const location = { get search() { return QS; } };",
            fn.group(0),
            "const CASES = " + json.dumps(cases) + ";",
            "let bad = 0;",
            "for (const c of CASES) {",
            "  STORED = c.stored; QS = c.qs;",
            "  const ed = { towns: c.towns.map(t => ({ town: t })) };",
            "  const got = resolve(ed);",
            "  for (const [k, v] of Object.entries(c.want)) {",
            "    if ((got[k] || '') !== v) {",
            "      console.log('FAIL [' + c.label + '] ' + k + ' = ' +",
            "        JSON.stringify(got[k]) + ' want ' + JSON.stringify(v));",
            "      bad++; } } }",
            "process.exit(bad ? 1 : 0);",
        ])
        r = subprocess.run([node, "-e", body], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0,
                         f"the reader's scope resolution is wrong:\n{r.stdout}{r.stderr}")

    def test_an_override_never_writes_the_choice(self):
        """The rule that keeps a shared link from silently re-homing a reader:
        only chooseTown() may touch storage, and it is only ever called from a
        click. resolve() and banner() must never write."""
        js = (REPO / "web" / "static" / "app.js").read_text()
        # Walk back from each call site to the thing that owns it. Only a
        # deliberate act of choosing may reach storage.
        ALLOWED = {"const writeTown", "function chooseTown", "b.onclick"}
        sites = [m.start() for m in re.finditer(r"writeTown\(", js)]
        self.assertTrue(sites, "writeTown disappeared")
        for at in sites:
            before = js[:at]
            owner = max(
                ((before.rfind(k), k) for k in
                 ("const writeTown", "function chooseTown", "b.onclick",
                  "function resolve", "function banner", "function paintScope",
                  "function initScope", "function runSearch")),
                key=lambda kv: kv[0])[1]
            self.assertIn(owner, ALLOWED,
                          f"writeTown reached from {owner} — the choice must "
                          f"only be written when the reader makes one")
        # and resolve() itself is pure over (edition, location, storage)
        fn = re.search(r"  function resolve\(ed\) \{.+?\n  \}", js, re.S).group(0)
        for forbidden in ("writeTown", "localStorage.setItem", "fetch("):
            self.assertNotIn(forbidden, fn,
                             f"resolve() must not {forbidden} — it is read-only")


class TestMomentQualityGates(unittest.TestCase):
    """The newspaper's moment plane holds a higher bar than the shared
    analyzer (specs/20 §6 quality pass): stored decisions are re-validated on
    a word boundary, and soft tension words have to be *owned* to count."""

    def test_real_decisions_drops_the_substring_false_positives(self):
        from web.bake import _real_decisions
        stored = [
            {"t": 10.0, "text": "staff who have devoted three decades", "outcome": "discussed"},
            {"t": 20.0, "text": "I heard a commotion in the hallway", "outcome": "discussed"},
            {"t": 30.0, "text": "the motion carries, unanimous", "outcome": "passed"},
            {"t": 40.0, "text": "and the chair votes I", "outcome": "passed"},
        ]
        kept = _real_decisions(stored)
        texts = [d["text"] for d in kept]
        self.assertIn("the motion carries, unanimous", texts)   # real motion
        self.assertIn("and the chair votes I", texts)           # real roll call
        self.assertNotIn("staff who have devoted three decades", texts)
        self.assertNotIn("I heard a commotion in the hallway", texts)

    def test_weak_tension_keeps_the_felt_and_drops_the_incidental(self):
        from web.bake import _is_weak_tension
        felt = [
            ("I am deeply concerned about the plan", ["concern", "concerned"]),
            ("but I'm a little concerned that this fails kids", ["concern"]),
            ("we strongly oppose this cut", ["oppose", "opposed"]),
            ("the concern was that the language was vague", ["concern"]),
        ]
        incidental = [
            ("training to invent new things and solve problems", ["problem"]),
            ("as capable problem solvers", ["problem"]),
            ("my next question concerns equity", ["concern"]),
            ("fees as opposed to fines", ["oppose", "opposed"]),
            ("and there aren't crises on the finance side", ["concern"]),
            ("you don't concern yourself with opinion", ["concern"]),
        ]
        for text, words in felt:
            self.assertFalse(_is_weak_tension(text, words),
                             f"real pushback dropped: {text!r}")
        for text, words in incidental:
            self.assertTrue(_is_weak_tension(text, words),
                            f"incidental mention kept: {text!r}")

    def test_narrated_decisions_and_bare_vote_tokens_are_not_decisions(self):
        """A decision word inside narration (a death, a described process) or a
        lone roll-call token is not a decision made — the audit's finds."""
        from web.bake import _is_narrated_decision, _build_moments
        for narration in ("the original author passed away last spring",
                          "it is submitted and then approved by PSB Finance",
                          "signed by the superintendent and sent to DESE for approval",
                          "as we try to find resolutions we keep working"):
            self.assertTrue(_is_narrated_decision(narration),
                            f"narration read as a decision: {narration!r}")
        self.assertFalse(_is_narrated_decision("I move that we approve the budget"))
        # a bare "Aye." window is a vote cast, not a decision card
        segs = [{"start": 50.0, "end": 53.0, "text": "Aye."},
                {"start": 200.0, "end": 204.0, "text": "the board voted to adopt the budget"}]
        decisions = [{"t": 50.0, "text": "Aye.", "outcome": "discussed"},
                     {"t": 200.0, "text": "the board voted to adopt the budget",
                      "outcome": "passed"}]
        ms = _build_moments(segs, [], decisions, [], [])
        quotes = " || ".join(m["quote"] for m in ms if m["kind"] == "decision")
        self.assertNotIn("Aye", quotes)
        self.assertIn("adopt the budget", quotes)

    def test_moments_gate_procedural_roll_call_and_own_tension(self):
        """A decision that is pure roll-call mechanics ("how do you vote?")
        is procedure, not a moment; a tension word owned a segment away from
        its subject still lands, because the gate reads the windowed sentence."""
        from web.bake import _build_moments
        segs = [
            {"start": 100.0, "end": 103.0, "text": "Okay, want to vote?"},
            {"start": 200.0, "end": 203.0, "text": "we have a consent agenda to vote on"},
            {"start": 300.0, "end": 303.0, "text": "So, so I understand, but I'm a little"},
            {"start": 303.0, "end": 306.0, "text": "concerned that this eliminates a class."},
        ]
        decisions = [
            {"t": 100.0, "text": "Okay, want to vote?", "outcome": "discussed"},
            {"t": 200.0, "text": "we have a consent agenda to vote on", "outcome": "discussed"},
        ]
        tension = [{"t": 303.0, "text": "concerned that this eliminates a class.",
                    "words": ["concern", "concerned"]}]
        ms = _build_moments(segs, [], decisions, [], tension)
        quotes = " || ".join(m["quote"] for m in ms)
        self.assertNotIn("want to vote", quotes)                  # procedure gated
        self.assertIn("consent agenda", quotes)                   # real decision kept
        te = [m for m in ms if m["kind"] == "tension"]
        self.assertTrue(te, "owned tension one segment from its subject should land")
        self.assertIn("concerned", te[0]["quote"])


class TestBakeEdition(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        cls.db = root / "corpus.db"
        cls._seed(cls.db)
        cls.out = root / "app"
        from web import bake
        cls.report = bake.bake(str(cls.db), str(cls.out), "9.9.9",
                               "https://example.org")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    @staticmethod
    def _seed(db):
        from memory.store import Corpus
        c = Corpus(str(db))
        for mid, title, date in [("vid1", "Select Board — March", "2026-03-10"),
                                 ("vid2", "School Committee — June", "2026-06-18")]:
            # .97 fractional starts exercise the anchor/deep-link rounding
            # invariant: int(12.97)=12 but round(12.97,1)=13.0 — a producer
            # that rounded up would mint a #t13 link with no t13 anchor.
            segs = [{"start": i * 10.0 + 0.97, "end": i * 10 + 9, "speaker": "Chair",
                     "text": f"we discuss the budget override item {i} at length"}
                    for i in range(6)]
            c.replace_segments(mid, segs)
            c.upsert_meeting({"id": mid, "title": title, "date": date,
                              "town": "Testville", "body": "Board",
                              "source_kind": "youtube", "video_id": mid,
                              "url": f"https://youtube.com/watch?v={mid}",
                              "url_canon": f"youtube:{mid}", "duration": 60,
                              "n_segments": len(segs), "status": "live",
                              "summary": "A budget override was discussed.",
                              "analysis_json": json.dumps({"decisions": [
                                  {"t": 12.0, "text": "override passes", "outcome": "passed"}]})})
        # a cross-meeting issue by hand (both meetings share "budget override")
        c.upsert_issue({"id": "issue:testville:budget-override", "town": "Testville",
                        "name": "budget override", "status": "active",
                        "keywords": ["budget override"], "aliases": [], "related": []})
        for mid in ("vid1", "vid2"):
            rows = c.segments_of(mid)
            c.link_segments("issue:testville:budget-override",
                            [(r["id"], mid, 1.0, "alias") for r in rows[:3]])
        # a document on vid1, linked to the issue by a keyword its chunk names
        c.upsert_document({"id": "doc:budget", "meeting_id": "vid1",
                           "town": "Testville", "kind": "Agenda",
                           "title": "Agenda", "date": "2026-03-10",
                           "url": "https://example.org/agenda.pdf", "pages": 2})
        c.replace_doc_chunks("doc:budget", [
            {"page": 1, "text": "the budget override public hearing"},
            {"page": 2, "text": "unrelated permit boilerplate"}])
        from memory import documents
        documents.assign_document(c, "doc:budget")
        # a roll-call vote on vid1, near the issue's first bead (t≈0.97)
        c.replace_votes("vid1", [{
            "t": 12.0, "motion": "to approve the budget override",
            "outcome": "passes", "tally": "3–0", "origin": "extractive",
            "roll": [{"name": "Chair Alpha", "vote": "yes", "t": 12.0, "quote": "aye"},
                     {"name": "Member Beta", "vote": "yes", "t": 13.0, "quote": "aye"},
                     {"name": "Member Gamma", "vote": "no", "t": 14.0, "quote": "no"}]}])

    def _read(self, rel):
        return json.loads((self.out / rel).read_text())

    def test_the_constitution_names_the_standing_rule(self):
        """When the use of the gate changes, /app/ai changes in the same
        commit (CLAUDE.md): a standing rule may now approve a channel's
        rule-matched meetings, only where YouTube lists captions, and the
        page says so beside the promise it qualifies."""
        ai = (self.out / "ai" / "index.html").read_text()
        self.assertIn("People gate the record.", ai)
        self.assertIn("standing", ai)
        self.assertIn("approves only a", ai)
        self.assertIn("never touches", ai)

    def test_manifest_and_counts(self):
        m = self._read("manifest.json")
        self.assertEqual(m["schema"], 1)
        self.assertEqual(m["version"], "9.9.9")
        self.assertEqual(m["counts"]["meetings"], 2)
        self.assertEqual(m["edition_date"], "2026-06-18")  # corpus-derived, not wall-clock
        self.assertTrue(m["corpus_hash"])

    def test_featured_papers_press_into_the_stub_and_the_front_page(self):
        """specs/21 P3: the press builds example papers as plain /app/p
        links. On the stub they must sit OUTSIDE #paperbody — the renderer
        owns that node's innerHTML, and anything pressed inside it would be
        torn down on the first render. On the front page: one quiet line."""
        stub = (self.out / "p" / "index.html").read_text()
        self.assertIn('id="pfeat"', stub)
        # paperbody holds only its JS-off hint, so the first </div> past its
        # open tag is its close — pfeat must land beyond it
        pb = stub.index('id="paperbody"')
        self.assertGreater(stub.index('id="pfeat"'), stub.index("</div>", pb))
        # this corpus holds a roll call → the rolls paper leads, and every
        # featured link travels v=2 (each carries a chart — paperV's rule;
        # & rides HTML-escaped in an attribute)
        self.assertIn("/app/p?v=2&amp;t=the%20roll%20calls%2C%20watched", stub)
        self.assertIn("b=c.votes,c.framing", stub)
        # on the front page they are CARDS now, inside the front door
        # (specs/23 A1 grew the one quiet line into the section)
        home = (self.out / "index.html").read_text()
        self.assertNotIn('class="featline"', home)
        door = home[home.index('class="sp-paths"'):home.index("</section>", home.index('class="sp-paths"'))]
        self.assertIn('class="pf-card"', door)
        self.assertIn("/app/p?v=2&amp;t=the%20roll%20calls%2C%20watched", door)
        self.assertIn("the press built from the record", door)
        # the latest-meeting paper names the latest meeting (vid2, June)
        # …as the shape of path one: its numbers, its shape, its framing,
        # the record's reading, and what keeps coming back (a v=4 link)
        self.assertIn("b=m.vid2,c.numbers.m%3Avid2,c.shape.vid2,c.framing.vid2,a.m%3Avid2,c.topics", stub)

    def test_the_two_paths_are_baked_content_in_the_paper_palette(self):
        """specs/24 (after specs/23 A1): the front page carries the two paths
        into a story of your own — path one from the latest meetings, path
        two from the issues with the longest reach — as the record's own
        prose: real links (JS-off follows them to the stub's honest hint),
        no studio class, no studio hue, no button, no script; the byte-clean
        guard below sweeps the same page for cz- markers."""
        home = (self.out / "index.html").read_text()
        self.assertIn('class="sp-paths"', home)
        door = home[home.index('class="sp-paths"'):home.index("</section>", home.index('class="sp-paths"'))]
        self.assertIn("your paper — be the editor", door)
        self.assertIn("Two ways in.", door)
        self.assertIn("No account. Nothing uploaded.", door)
        self.assertIn('href="/app/p#edit"', door)
        self.assertIn("What happened", door)
        self.assertIn("How it moved", door)
        # the starts are the record's own refs: the latest meetings, the
        # widest issues, the roll calls
        self.assertIn('href="/app/p#edit&amp;tpl=meeting&amp;ref=vid2"', door)
        self.assertIn('href="/app/p#edit&amp;tpl=issue&amp;ref=issue_testville_budget-override"', door)
        self.assertIn('href="/app/p#edit&amp;tpl=rolls"', door)
        self.assertIn("Testville Board · 2026-06-18", door)
        # the paths sit after the two stories and before the briefs: home
        # stays the record's front page, and the stories lead it
        self.assertLess(home.index('id="over-time"'), home.index('id="latest"'))
        self.assertLess(home.index('id="latest"'), home.index('class="sp-paths"'))
        self.assertLess(home.index('class="sp-paths"'), home.index("also on the record"))
        # content, not chrome: nothing studio-namespaced, nothing scripted
        for bad in ("cz-", "<button", "onclick"):
            self.assertNotIn(bad, door, f"{bad!r} in the baked paths")
        css = (self.out / "app.css").read_text()
        self.assertIn(".sp-paths{", css)
        block = css[css.index(".sp-paths{"):css.index(".sp-pressed .kicker")]
        for pop in ("#a855f7", "#7c3aed", "studio"):
            self.assertNotIn(pop, block, f"{pop!r} reached the two paths")

    def test_the_front_page_is_two_stories_with_a_toggle(self):
        """specs/24 §2.4: the front page IS the story — the record over time
        and the latest meeting, both pressed whole (JS-off complete), a tab
        strip of two links between the record's controls and the stories,
        and every picture computed at press time in the paper palette."""
        home = (self.out / "index.html").read_text()
        self.assertIn('<nav class="stab" aria-label="the front page’s two stories">', home)
        self.assertIn('href="#over-time" data-story="over-time" aria-current="true"', home)
        self.assertIn('href="#latest" data-story="latest"', home)
        over = home[home.index('id="over-time"'):home.index('id="latest"')]
        latest = home[home.index('id="latest"'):home.index('class="sp-paths"')]
        # the record over time: counted headline and lede, every picture
        self.assertIn("2 meetings, 0.0 hours, 1 roll call — the record since March 2026", over)
        self.assertIn("the record holds <a href=\"/app/s\">2 meetings</a> of the Board in Testville", over)
        self.assertIn("1 roll call</a> were read from the tapes: 1 passed, 0 failed", over)
        for kicker in ("the record, by the numbers", "votes over time", "the long view",
                       "how the talk was framed", "what keeps coming back", "the record in words",
                       "what changed, last time", "the latest roll calls"):
            self.assertIn(kicker, over, f"the over-time story lost '{kicker}'")
        self.assertIn('<svg width="', over)                       # the votes dots
        self.assertIn('href="/app/m/vid1#t12"', over)             # the vote's receipt
        self.assertIn('class="fp-cloud"', over)                   # the record in words
        self.assertIn('class="fp-heat"', over)                    # the framing strip
        self.assertIn('class="fp-multiples"', over)               # the threads by month
        self.assertIn('href="/app/p#edit&amp;tpl=rolls">make this story yours', over)
        # the latest meeting: the labeled lede, the counted commentary, the shape
        self.assertIn("the latest meeting on the record — what happened", latest)
        self.assertIn("a summary drawn from the tape", latest)      # the test corpus has no model
        self.assertIn('The night ran <a href="/app/m/vid2">1 min</a>.', latest)
        for kicker in ("the meeting in numbers", "the shape of the meeting", "the moments that decided it",
                       "the roll calls", "the meeting in words"):
            self.assertIn(kicker, latest, f"the latest story lost '{kicker}'")
        self.assertIn('href="/app/p#edit&amp;tpl=meeting&amp;ref=vid2">make this story yours', latest)
        # the pictures are content in the paper palette — no studio hue, no chrome
        for bad in ("cz-", "#a855f7", "#7c3aed", "#d946ef", "<button", "onclick"):
            self.assertNotIn(bad, over + latest, f"{bad!r} in a pressed story")
        # the commentary is counted, never modeled — and says so
        self.assertIn("no model wrote a line of it", over)
        self.assertIn("no model wrote a line of it", latest)

    def test_issues_index_plane_names_every_issue(self):
        """specs/23 A3: the editor's add-search reads the record's own
        static index — every meeting is already in search/meta.json; every
        issue now sits in issues/index.json, written inside bake_issues so
        the hosted press mirrors it without a new stage."""
        idx = self._read("issues/index.json")
        self.assertEqual([i["slug"] for i in idx], ["issue_testville_budget-override"])
        self.assertEqual(idx[0]["name"], "budget override")
        self.assertEqual(idx[0]["n_meetings"], 2)
        for k in ("aliases", "first_seen", "last_seen"):
            self.assertIn(k, idx[0])
        # and the SW shell precaches both, so a paper assembles offline
        sw = (self.out / "sw.js").read_text()
        self.assertIn('"/app/search/meta.json"', sw)
        self.assertIn('"/app/issues/index.json"', sw)

    def test_meeting_json_and_stub(self):
        mj = self._read("meetings/vid1.json")
        self.assertEqual(mj["title"], "Select Board — March")
        self.assertNotIn("segments", mj)  # transcript lives in the stub, not here
        stub = (self.out / "m" / "vid1" / "index.html").read_text()
        self.assertIn('property="og:title"', stub)
        self.assertIn("budget override item", stub)   # JS-off readable transcript
        self.assertIn('class="seg"', stub)
        # transcript .txt download exists
        self.assertTrue((self.out / "m" / "vid1" / "transcript.txt").exists())

    def test_issue_timeline(self):
        # find the issue file — by name, not by directory order: issues/ also
        # holds index.json (specs/23 A3), and ext4 lists it first where APFS
        # did not (the first CI run's catch)
        files = [f for f in (self.out / "issues").glob("*.json") if f.name != "index.json"]
        self.assertEqual(len(files), 1, [f.name for f in files])
        ij = json.loads(files[0].read_text())
        self.assertEqual(ij["name"], "budget override")
        self.assertEqual(ij["n_meetings"], 2)
        self.assertEqual(len(ij["timeline"]), 2)
        self.assertTrue(all(n["beads"] for n in ij["timeline"]))

    def test_urls_dedup_keys(self):
        urls = self._read("urls.json")
        self.assertEqual(urls.get("youtube:vid1"), "vid1")

    def test_search_index(self):
        shards = self._read("search/shards.json")
        self.assertGreater(shards["segments"], 0)
        segs = self._read("search/segs.json")
        # "budget" appears -> its prefix shard has it, pointing at real segments
        sh = self._read("search/t-b.json")
        self.assertIn("budget", sh)
        sid = sh["budget"][0]
        self.assertIn("budget", segs[sid][3].lower())

    def test_deeplink_anchors_resolve(self):
        """The HIGH bug: a search/cite deep-link is #t<floor(segTime)>, and the
        transcript anchor is id=t<int(start)>. If the two used different
        rounding, ~5% of deep-links would land on no element. Assert every
        search segment's floored time matches a real anchor in its stub."""
        segs = self._read("search/segs.json")
        meta = self._read("search/meta.json")
        # anchor ids present in each meeting stub
        anchors = {}
        for mi, mrec in enumerate(meta):
            html = (self.out / "m" / mrec["pid"] / "index.html").read_text()
            anchors[mi] = set(re.findall(r'id="t(\d+)"', html))
            # data-t must floor to its own anchor id (never round up past it)
            for aid, dt in re.findall(r'id="t(\d+)" data-t="([^"]+)"', html):
                self.assertEqual(int(float(dt)), int(aid),
                                 f"data-t {dt} floors past anchor t{aid}")
        for mi, t, spk, text in segs:
            self.assertIn(str(int(t)), anchors[mi],
                          f"search deep-link #t{int(t)} has no anchor in meeting {mi}")

    def test_covenant_and_the_press_present(self):
        self.assertTrue((self.out / "covenant" / "index.html").exists())
        # the desk tools no longer own a door each; their URLs redirect to the
        # press, and memory (a web surface) never had one
        self.assertTrue((self.out / "t" / "stencil" / "index.html").exists())
        self.assertFalse((self.out / "t" / "memory").exists())
        stub = (self.out / "t" / "stencil" / "index.html").read_text()
        self.assertIn('http-equiv="refresh"', stub)
        self.assertIn("/app/press#stencil", stub)
        self.assertIn("Content-Security-Policy", stub)   # a real page, CSP intact
        # the press page is where they land: the tool, and the one download
        press = (self.out / "press" / "index.html").read_text()
        self.assertIn('id="stencil"', press)
        self.assertIn("Civic Media Studio", press)
        self.assertIn("Get the desktop app", press)
        self.assertIn("communityai.studio", press)   # the cross-link, done once

    def test_kits_plane_pressed_and_indexed(self):
        """Publisher's reading half (specs/20 §7.9 P2): a kit per meeting with a
        video and moments, as a real Publisher kit and an index that lists it."""
        kit = self._read("kits/vid1.json")
        self.assertEqual(kit["slug"], "vid1")
        self.assertEqual(kit["version"], 1)
        self.assertTrue(kit["clips"])
        self.assertIn("extractive", kit["copy"]["origin"])
        self.assertEqual(kit["files"], [])            # nothing rendered — desk work
        # the clip carries the reel model's identity (kind, t)
        self.assertTrue(all("kind" in c and "t" in c for c in kit["clips"]))
        idx = self._read("kits/index.json")
        slugs = {k["slug"] for k in idx["kits"]}
        self.assertEqual(slugs, {"vid1", "vid2"})
        self.assertTrue(all(k["n_clips"] >= 1 for k in idx["kits"]))

    def test_kit_page_reads_with_js_off_and_stays_at_the_desk(self):
        html = (self.out / "k" / "vid1" / "index.html").read_text()
        self.assertIn("publish kit", html)
        self.assertIn("mo-quote", html)                       # the clips render
        self.assertIn("/app/kits/vid1.json", html)            # the download
        self.assertIn("/app/r?v=1&amp;m=vid1&amp;c=", html)   # play-as-reel handoff
        # the covenant sentence: rendering stays at the desk, and it says so
        self.assertIn("Rendering the clips as video needs the desk", html)
        self.assertIn("Content-Security-Policy", html)        # a real page
        # the index lists both meetings' kits
        kidx = (self.out / "k" / "index.html").read_text()
        self.assertEqual(kidx.count('class="mcard"'), 2)

    def test_meeting_page_surfaces_its_kit_and_cross_meeting_reels(self):
        """The moments panel is the produce-zone: it links a meeting to its kit
        (P2-A) and says a reel can span meetings (P2-B), so both are findable."""
        stub = (self.out / "m" / "vid1" / "index.html").read_text()
        self.assertIn("/app/k/vid1", stub)
        self.assertIn("publish kit for this meeting", stub)
        self.assertIn("a reel can span the record", stub)

    def test_press_publisher_row_points_at_the_kits(self):
        """The door stays honest until kits press (specs/20 §6): this edition has
        kits, so Publisher's line now cross-links into /app/k."""
        press = (self.out / "press" / "index.html").read_text()
        self.assertIn("/app/k", press)
        self.assertIn("a publish kit for every meeting", press)

    def test_all_thirteen_door_urls_still_answer_as_stubs(self):
        """A citation never dies (specs/20 §5): every /app/t/<tool>/ URL the old
        doors answered is a redirect stub now — 200, CSP, pointed at the press."""
        doors = [t["id"] for t in tools.TOOLS if t["surface"] != "web"]
        self.assertEqual(len(doors), 13)
        press = (self.out / "press" / "index.html").read_text()
        for tid in doors:
            p = self.out / "t" / tid / "index.html"
            self.assertTrue(p.is_file(), f"/app/t/{tid}/ vanished")
            html = p.read_text()
            self.assertIn(f"/app/press#{tid}", html)
            self.assertIn('http-equiv="refresh"', html)
            self.assertIn(f'id="{tid}"', press, f"the press has no anchor for {tid}")

    def test_nothing_references_the_slides_that_never_travelled(self):
        """The broken door images leave this domain structurally (specs/20 §5):
        no pressed file references site/content/assets, and no /app/assets/slide
        survives anywhere — so there is no broken image on the domain."""
        for p in self.out.rglob("*"):
            if p.is_file() and p.suffix in (".html", ".css", ".js", ".json"):
                txt = p.read_text(errors="ignore")
                self.assertNotIn("site/content/assets", txt, str(p))
                self.assertNotIn("/app/assets/slide-", txt, str(p))

    def test_covenant_explains_the_licence_and_links_the_source(self):
        """The covenant page named AGPL-3.0 for a year while the repository was
        MIT — a claim nobody could check because the page never said where to
        look. Both licences are named, both are explained in words a resident
        reads without a lawyer, and the source and LICENSING.md are one click
        away. A regression back to the bare word fails here."""
        cov = (self.out / "covenant" / "index.html").read_text()
        self.assertIn("AGPL-3.0", cov)
        self.assertIn("CC BY-SA 4.0", cov)
        # the consequence, not the mechanism: what a resident actually gets
        self.assertIn("run their own copy", cov)
        self.assertIn("owes those people the changed program", cov)
        # the record and the code are told apart, and the town's own record
        # is not claimed by either
        self.assertIn("The meetings belong to the town", cov)
        # a claim with a dead link behind it is worse than no claim
        self.assertIn(f'href="{emit.SOURCE_REPO}"', cov)
        self.assertIn(f'href="{emit.LICENSING_DOC}"', cov)
        self.assertIn("LICENSING.md", cov)
        # it must read with JavaScript off, like the rest of the edition: the
        # prose is baked into the document, not injected by app.js, and nothing
        # holds it back with hidden
        body = cov.split('<section class="covpage">')[1].split("</section>")[0]
        self.assertIn("The software is AGPL-3.0", body)
        self.assertNotIn("hidden", body)

    def test_feeds(self):
        self.assertTrue((self.out / "feeds" / "firehose.xml").exists())
        fh = (self.out / "feeds" / "firehose.xml").read_text()
        self.assertIn("<rss", fh)

    def test_within_budget(self):
        self.assertEqual(self.report["busts"], 0, "an edition busted its budget")

    def test_csp_on_every_stub(self):
        for stub in self.out.rglob("index.html"):
            html = stub.read_text()
            self.assertIn("Content-Security-Policy", html, f"{stub} lacks CSP")
            self.assertIn("script-src 'self'", html)

    # -- the coat: publicrecord's own face, drawn from brand/ (specs/20 §20.1) --

    def test_pressed_css_bans_the_desk_and_scopes_the_studio_pop(self):
        """publicrecord is the quietest property: neutrals + deep green, and no
        cream, oxblood, amber, or the lens hues may survive in the pressed
        stylesheet — not even as an unused variable (specs/20 §4, the law).

        The studio-mode amendment (specs/21 §6.1) is the one bounded exception:
        the two purples it uses — #a855f7 (surfaces/borders) and #7c3aed (text at
        AA) — may appear, but ONLY inside a rule scoped to html.cz-m-studio, so
        they light the editor's own chrome and can never reach the paper, the
        preview, or the shared masthead. Fuchsia is still forbidden everywhere —
        the amendment admitted purple, it did not repeal the fuchsia line.
        Comments are stripped first so a note does not count."""
        css = (self.out / "app.css").read_text()
        css = re.sub(r"/\*.*?\*/", "", css, flags=re.S).lower()
        FORBIDDEN = [
            "#f3f0e7", "#8e4a55", "#a97a16", "#a97e22",   # cream, oxblood, amber
            "#d946ef",                                     # fuchsia — still nowhere
            "#7e5b8e", "#c77ba6", "#b0542d", "#3fa9d0",    # the lens hues
            "--cream", "--memory", "--amber", "--forest", "--ide-",
        ]
        for bad in FORBIDDEN:
            self.assertNotIn(bad, css, f"forbidden token {bad!r} in the pressed CSS")
        # the studio purples are admitted, but every occurrence must be
        # studio-mode-scoped: the governing selector (the text opening the rule it
        # sits in) names the mode.
        for purple in ("#a855f7", "#7c3aed"):
            at = -1
            while (at := css.find(purple, at + 1)) != -1:
                open_brace = css.rfind("{", 0, at)
                selector = css[css.rfind("}", 0, open_brace) + 1:open_brace]
                self.assertIn("cz-m-studio", selector,
                              f"purple {purple!r} appears outside a studio-mode "
                              f"rule (selector {selector.strip()!r}) — it must "
                              f"never reach the paper (specs/21 §6.1)")
        # the shared :root token block stays pure — no studio accent leaks upward
        root = css[css.index(":root{"):css.index("}", css.index(":root{"))]
        for pop in ("#a855f7", "#7c3aed", "#d946ef", "fuchsia", "purple"):
            self.assertNotIn(pop, root, f"{pop!r} leaked into the shared :root")
        # and the record's own accents ARE there
        for good in ("#052e16", "#059669", "#f8fafc"):
            self.assertIn(good, css, f"{good} (brand) missing from the pressed CSS")

    def test_the_studio_is_script_built_never_baked(self):
        """specs/21 P0: the three-mode studio is added by app.js at runtime, so
        the pressed pages stay byte-for-byte the specs/20 paper. No studio class
        and no mode class may appear in any baked stub — a reader with app.js
        removed gets exactly the reader, which is what 'paper mode never gets
        louder' and 'JS-off degrades to paper' require. The studio lives only in
        the shipped script and stylesheet."""
        MARKERS = ("cz-studio", "cz-m-", "cz-mode", "cz-panel", "cz-tab",
                   "cz-pill", "cz-enter",
                   # specs/23 A2/A3: the card affordances and the on-page
                   # editor are script-added in preview/studio only
                   "cz-mk", "cz-ed", "cz-drop",
                   # specs/22 (phase B): the cut ticks on transcript rows,
                   # search hits and issue beads, the panel tray, and the
                   # viewer's make-this-yours chooser are hydration only
                   "seg-tick", "btick", 'class="stick"', "data-czcut",
                   "cz-rclip", "rv-take", "data-rv=",
                   # B2: the preview stage and a paper's ▶ beside each cite
                   "cz-stage", "pb-pv", "data-pvpid")
        for stub in self.out.rglob("index.html"):
            html = stub.read_text()
            for m in MARKERS:
                self.assertNotIn(m, html,
                    f"{m!r} was baked into {stub.relative_to(self.out)} — the "
                    f"studio must be built by app.js, not pressed into the paper")
        self.assertIn("cz-m-studio", (self.out / "app.js").read_text())
        self.assertIn("cz-m-studio", (self.out / "app.css").read_text())

    def test_your_paper_stub_is_pressed(self):
        """specs/21 P1: /app/p is one static stub for every paper (the /app/r
        pattern) — the paper itself arrives in the link, the browser's draft,
        or a store id, so the stub must say honestly what JS-off cannot do and
        point at the record instead. And it stays paper-quiet: no studio class
        is baked (the guard above already sweeps it), and the rendered-paper
        rule — no studio hue — is CSS-scoped, so this page carries none."""
        stub = (self.out / "p" / "index.html").read_text()
        self.assertIn("A paper, edited from the record", stub)
        self.assertIn("needs JavaScript", stub)
        # C2: the JS-off copy and the description name the ref-only kinds
        self.assertIn("pull-quotes, filings and what-changed digests", stub)
        self.assertIn("charts, pull-quotes, filings and digests an editor arranged", stub)
        self.assertIn('href="/app/"', stub)          # the honest fallback
        self.assertIn('id="paperbody"', stub)        # the renderer's mount
        # the paper's own classes ship in the stylesheet the stub loads
        css = (self.out / "app.css").read_text()
        for cls in (".phead", ".ptitle", ".pb-gone", ".cz-ptitle", ".cz-prow",
                    # C1/C2: the layouts, the three ref blocks, and a print
                    # sheet that makes a rendered paper a printable page
                    ".pb-lead", ".pb-head", ".pb-pair", ".pb-quote", ".pb-doc",
                    ".pb-digest", ".pb-pair{display:grid;grid-template-columns:1fr 1fr;gap:20px}"):
            self.assertIn(cls, css, f"{cls} missing from the pressed CSS")
        prn_start = css.index("@media print{")
        prn = css[prn_start:css.index("\n}\n", prn_start)]   # the block's own brace, not the file's end
        for rule in (".cz-studio", ".paperbody>*{break-inside:avoid}", 'content:" " attr(href)'):
            self.assertIn(rule, prn, f"the print sheet lost {rule!r}")
        # the make surfaces belong to the offline shell (specs/21 §5: the
        # covenant's own case is composing with the servers gone) — the SW
        # precaches /app/p and /app/r beside the sibling stubs, in the
        # trailing-slash canonical form (the bare form 301s, and a cached
        # redirect served to a navigation is a browser error, not a page)
        sw = (self.out / "sw.js").read_text()
        for url in ('"/app/p/"', '"/app/r/"', '"/app/s/"'):
            self.assertIn(url, sw, f"{url} missing from the SW shell")
        self.assertNotIn('"/app/s",', sw, "a bare stub URL crept back into the shell")
        self.assertIn("!res.redirected", sw,
                      "the SW must never cache a redirected response")
        self.assertIn("url.pathname + '/'", sw,
                      "bare-path navigations must fall to the slash form offline")

    def test_the_ai_constitution_is_pressed_and_the_footer_names_it(self):
        """/app/ai says when a model touches the record, whose model it is,
        where it runs, and what stands without it — every claim checkable —
        and the footer on every page carries the recredit and the link; the
        about (covenant) and settings (town scope) surfaces carry the button.
        Interactivity is native (details/summary), so the page is complete
        with JavaScript off."""
        page = (self.out / "ai" / "index.html").read_text()
        for claim in ("Our AI Constitution", "gemini-embedding-001",
                      "Whisper-family", "no model at all",
                      "part of the Community AI Project", "communityai.studio",
                      "your machine only", "check it yourself",
                      "civicmedia.studio", "control-z.org", "/constitution"):
            self.assertIn(claim, page, f"{claim!r} missing from /app/ai")
        # the shareable spelling redirects, canonical intact
        alias = (self.out / "constitution" / "index.html").read_text()
        self.assertIn('url=/app/ai/', alias)
        self.assertIn('rel="canonical"', alias)
        self.assertIn("Our AI Constitution", alias)
        self.assertIn("<details>", page)
        self.assertIn("aria-label", page)      # the diagram speaks to AT
        home = (self.out / "index.html").read_text()
        for frag in ("weird machine", "brookline interactive group",
                     "Our AI Constitution", 'href="/app/ai"',
                     'class="scopeai"'):
            self.assertIn(frag, home, f"{frag!r} missing from the front page")
        self.assertNotIn("a Community AI Project tool", home,
                         "the old footer credit survived the recredit")
        cov = (self.out / "covenant" / "index.html").read_text()
        self.assertIn('href="/app/ai"', cov, "the about surface lost its button")
        self.assertIn('"/app/ai/"', (self.out / "sw.js").read_text(),
                      "the constitution should read offline too")

    def test_pressed_css_draws_its_tokens_from_brand(self):
        """The drift-guard, repointed at brand/ (specs/20 §8): the pressed
        :root carries the brand's own values, byte-faithful — the accent is
        green-deep, the state light is green-emerald, the page is off-white."""
        brand = (REPO / "brand" / "tokens" / "colors.css").read_text()
        val = lambda n: re.search(rf"--{n}:\s*(#[0-9A-Fa-f]{{6}})", brand).group(1)
        css = (self.out / "app.css").read_text()
        root = css[css.index(":root{"):css.index("}", css.index(":root{"))]
        for token, source in [("--accent", "green-deep"),
                              ("--state", "green-emerald"),
                              ("--surface-page", "offwhite"),
                              ("--text-primary", "ink"),
                              ("--text-secondary", "slate")]:
            self.assertIn(f"{token}:{val(source)}", root,
                          f"{token} drifted from brand --{source}")

    def test_fonts_are_vendored_and_within_budget(self):
        """Real Inter + JetBrains Mono, self-hosted (specs/20 §4): six subset
        woff2 with their OFL texts ship in the edition, the @font-face block is
        pressed, the CSP stays font-src 'self', and the whole face set is under
        its ~250 KB budget — thumbnails are remote, fonts are the only new
        bytes."""
        fonts = self.out / "fonts"
        faces = ["inter-400", "inter-500", "inter-700",
                 "jetbrains-mono-400", "jetbrains-mono-700", "jetbrains-mono-800"]
        total = 0
        for f in faces:
            p = fonts / f"{f}.woff2"
            self.assertTrue(p.is_file(), f"{f}.woff2 not vendored")
            total += p.stat().st_size
        self.assertTrue((fonts / "OFL-Inter.txt").is_file())
        self.assertTrue((fonts / "OFL-JetBrainsMono.txt").is_file())
        self.assertLess(total, 260_000, f"font set is {total//1024} KB (budget ~250)")
        css = (self.out / "app.css").read_text()
        self.assertIn("@font-face", css)
        self.assertIn("font-display:swap", css.replace(" ", ""))
        self.assertIn("/app/fonts/inter-400.woff2", css)
        home = (self.out / "index.html").read_text()
        self.assertIn("font-src 'self'", home)           # CSP unwidened
        self.assertIn('rel="preload"', home)             # critical faces preloaded
        self.assertNotIn("fonts.googleapis.com", home)   # nothing third-party
        self.assertNotIn("fonts.gstatic.com", css)

    def test_masthead_carries_the_brand_mark_byte_equal(self):
        """The keycap is read from brand/logos and never redrawn (specs/20 §4).
        Its three deep-green minute-lines, at their exact coordinates, appear in
        the masthead of every page and in the favicon."""
        mark = (REPO / "brand" / "logos" / "publicrecord-mark.svg").read_text().strip()
        line = '<rect x="22" y="28" width="52" height="8" fill="#052e16">'
        self.assertIn(line, mark, "the brand mark itself changed shape")
        home = (self.out / "index.html").read_text()
        self.assertIn(line, home, "the masthead mark is not the brand mark")
        self.assertEqual((self.out / "favicon.svg").read_text().strip(), mark)

    def test_front_page_is_a_newspaper(self):
        """The front page reads like a paper, not a dashboard: a lead story, a
        briefs column, by-the-numbers, the long view, the access ledger and the
        latest roll calls — all real HTML, so it reads linearly with JS off
        (specs/20 §5)."""
        home = (self.out / "index.html").read_text()
        for kicker in ("the latest meeting on the record", "also on the record",
                       "by the numbers", "the long view", "the access ledger",
                       "the latest roll calls"):
            self.assertIn(kicker, home, f"front page missing '{kicker}'")
        # the latest meeting (vid2, June) is told as a real article — the
        # second of the front page's two stories (specs/24 §2.4)
        self.assertIn('<article class="lead fp-story fp-latest" id="latest"', home)
        self.assertIn("School Committee — June", home)
        # briefs are the scope-filterable meeting cards
        self.assertIn('class="mcard"', home)
        # by-the-numbers, and every figure is a link (roll calls → the votes)
        self.assertIn('class="lead-nums"', home)
        self.assertIn('<a class="ln" href="/app/officials">', home)

    def test_front_page_pull_moments_link_into_the_tape(self):
        """The lead's pull-moments come from the moments plane and deep-link
        into the tape — nothing hand-typed."""
        home = (self.out / "index.html").read_text()
        self.assertIn('class="pull"', home)
        self.assertRegex(home, r'class="pull" href="/app/m/vid2#t\d+"')

    def test_meeting_carries_the_moments_plane(self):
        """Each meeting.json carries the pressed moments (specs/20 §6): a ranked,
        chronological list of {t, end, kind, score, reason, quote}. vid1 has a
        roll call, so it carries a VOTE moment scored above everything else."""
        mj = self._read("meetings/vid1.json")
        self.assertIn("moments", mj)
        ms = mj["moments"]
        self.assertTrue(ms, "vid1 should have moments")
        for mo in ms:
            self.assertEqual(set(mo),
                             {"t", "start", "end", "kind", "score", "reason", "quote"})
            # the anchor sits inside its own padded clip window
            self.assertLessEqual(mo["start"], mo["t"])
            self.assertGreaterEqual(mo["end"], mo["t"])
            self.assertGreaterEqual(mo["end"] - mo["start"], 6.0)   # min clip
        votes = [mo for mo in ms if mo["kind"] == "vote"]
        self.assertTrue(votes, "the roll call should press as a VOTE moment")
        self.assertGreaterEqual(votes[0]["score"], 0.9)
        # chronological
        self.assertEqual([mo["t"] for mo in ms], sorted(mo["t"] for mo in ms))

    def test_moments_window_the_sentence_and_gate_procedure(self):
        """specs/20 §6 P1 follow-up: a moment is the whole sentence around its
        anchor (padded into a watchable clip), and procedure is gated out — a
        reel is built from meaning, not from 'right, Betsy?'."""
        from web.bake import _build_moments
        segs = [
            {"start": 100.0, "end": 103.0, "text": "Right, Betsy?"},
            {"start": 200.0, "end": 203.0, "text": "How much will this override"},
            {"start": 203.0, "end": 206.0, "text": "cost the average household this year?"},
            {"start": 300.0, "end": 303.0, "text": "I am deeply concerned about the plan"},
            {"start": 303.0, "end": 306.0, "text": "to eliminate a kindergarten classroom."},
        ]
        questions = [
            {"t": 100.0, "text": "Right, Betsy?", "type": "information"},
            {"t": 200.0, "text": "How much will this override cost the average "
                                 "household this year?", "type": "budget"},
        ]
        tension = [{"t": 300.0, "text": "I am deeply concerned about the plan",
                    "words": ["concern"]}]
        ms = _build_moments(segs, [], [], questions, tension)
        quotes = " || ".join(m["quote"] for m in ms)
        self.assertNotIn("Right, Betsy", quotes)   # procedure gated out
        q = next(m for m in ms if m["kind"] == "question")
        self.assertIn("cost the average household", q["quote"])   # full sentence
        self.assertLessEqual(q["start"], q["t"])                  # padded clip
        self.assertGreaterEqual(q["end"] - q["start"], 6.0)
        te = next(m for m in ms if m["kind"] == "tension")
        self.assertIn("eliminate a kindergarten", te["quote"])    # fragment → sentence

    def test_search_is_instant_and_peeks_over_the_static_floor(self):
        """Instant search (debounced, never under three characters), hover peeks
        from the segs plane, and a `/` focus — all pure enhancement over the
        R1.6 static index, which stays untouched (specs/20 §4). The peek reads
        the plane the static path already loaded, so it never fetches and never
        burdens the live path."""
        js = (REPO / "web" / "static" / "app.js").read_text()
        self.assertIn("val.length < 3", js)             # no query under 3 chars
        self.assertIn('addEventListener("input"', js)   # instant
        self.assertIn("function wireSlashFocus", js)    # `/` focuses search
        self.assertIn("function selMove", js)           # j/k walk hits
        peek = re.search(r"function peek\(segs, id, mi\) \{.+?\n  \}",
                         js, re.S).group(0)
        for forbidden in ("fetch", "getJSON", "/api/", "askStudio"):
            self.assertNotIn(forbidden, peek,
                             f"the peek reached for {forbidden!r} — it must read "
                             "only the plane already in hand")

    def test_meeting_page_renders_moments_js_off(self):
        """The Moments panel is baked into the meeting stub, so it reads with
        JavaScript off (specs/20 §6 acceptance): scored cards, each a deep link
        into the transcript below, differing by a mono kicker not by colour."""
        stub = (self.out / "m" / "vid1" / "index.html").read_text()
        self.assertIn("the moments", stub)
        self.assertIn('class="moment"', stub)
        self.assertIn('class="mo-kind"', stub)
        self.assertRegex(stub, r'class="moment" href="#t\d+"')
        self.assertIn("salience", stub)   # the score bar is a measurement

    def test_moment_cards_carry_the_reel_composer_hooks(self):
        """Each moment card wraps in .mo-card and the anchor carries the whole
        moment (end, kind, quote), so the reel composer (specs/20 §6, P1) can
        cut a clip from a tick without a second fetch — and the card stays a
        plain deep link with JavaScript off."""
        stub = (self.out / "m" / "vid1" / "index.html").read_text()
        self.assertIn('class="mo-card"', stub)
        self.assertRegex(stub, r'class="moment"[^>]*data-end="[^"]+"[^>]*data-kind="')
        self.assertRegex(stub, r'data-quote="')

    def test_reel_viewer_stub_and_its_js_off_fallback(self):
        """/app/r is one static stub for every reel — the reel lives in the
        link, not the page (specs/20 §7). It has the mount points app.js
        hydrates, and a JS-off fallback that is honest about needing JavaScript
        and sends the reader to the record where the moments read in place."""
        stub = (self.out / "r" / "index.html").read_text()
        self.assertIn('id="reelstage"', stub)
        self.assertIn('id="reelcites"', stub)
        # honest JS-off degradation: it names the dependency and points home
        self.assertIn("needs JavaScript", stub)
        self.assertIn('href="/app/"', stub)
        # and it states the one desk-bound step plainly
        self.assertIn("needs the desk", stub)
        # the route exists in the reader
        js = (REPO / "web" / "static" / "app.js").read_text()
        self.assertIn(r"/\/app\/r$/.test(path)", js)

    def test_the_reel_path_touches_no_server(self):
        """The covenant, on the reel path: composing and playing a reel reach no
        backend (specs/20 §7 hard constraint). The viewer's only fetch is the
        meeting's own plane under /app/, and none of the reel code reaches the
        Studio helper."""
        js = (REPO / "web" / "static" / "app.js").read_text()
        # the reel path ends where the paper's own section (with its own
        # covenant test, TestPaper) begins
        block = js[js.index("THE REEL — compose here"):
                   js.index("YOUR PAPER — the curated document")]
        for forbidden in ("askStudio", "API +", "/api/", "http://", "run.app"):
            self.assertNotIn(forbidden, block,
                             f"the reel path reached for {forbidden!r}")
        # every plane the reel reads is a same-origin edition path — the
        # JSON planes, and the one raw fetch (transcript.txt, specs/22 §5.6)
        for plane in re.findall(r"getJSON\(`([^`]+)`", block):
            self.assertTrue(plane.startswith("${BASE}/"),
                            f"{plane} is not an edition path")
        raw = re.findall(r"fetch\(`([^`]+)`", block)
        self.assertTrue(raw, "the trim's transcript.txt fetch left the reel section?")
        for url in raw:
            self.assertTrue(url.startswith("${BASE}/m/"),
                            f"a raw fetch reaches past the edition: {url}")

    def test_the_thirteen_tool_doors_left_the_masthead(self):
        """The desk tools no longer share the record's masthead: the rail is
        gone and the section line is the paper's own (specs/20 §5). The tools
        live on /app/press now, reachable from the section nav and the footer."""
        home = (self.out / "index.html").read_text()
        self.assertNotIn('class="rail-item"', home)
        self.assertNotIn("civic media suite", home)   # the old rail heading
        self.assertIn('class="sectionnav"', home)
        self.assertIn('href="/app/press"', home)

    # -- documents, votes, officials, and the PWA (waves 2/3) --------------

    def test_meeting_carries_votes_and_documents(self):
        mj = self._read("meetings/vid1.json")
        self.assertEqual(len(mj["votes"]), 1)
        self.assertEqual(mj["votes"][0]["tally"], "3–0")
        self.assertEqual(len(mj["documents"]), 1)
        self.assertEqual(mj["documents"][0]["kind"], "Agenda")
        # the roll call and the paper are readable JS-off in the stub
        stub = (self.out / "m" / "vid1" / "index.html").read_text()
        self.assertIn("the vote ledger", stub)
        self.assertIn("the town", stub)   # "the town's paper"

    def test_issue_carries_ledger_and_document_lane(self):
        ij = json.loads((self.out / "issues" /
                         "issue_testville_budget-override.json").read_text())
        self.assertTrue(ij["ledger"], "the issue should carry a roll-call ledger")
        self.assertEqual(ij["ledger"][0]["tally"], "3–0")
        # a timeline node interleaves the document
        withdocs = [n for n in ij["timeline"] if n.get("documents")]
        self.assertTrue(withdocs, "a document should interleave on the timeline")
        self.assertEqual(withdocs[0]["documents"][0]["kind"], "Agenda")
        # the milestone is a real vote (not just a heuristic decision)
        votes = [m for n in ij["timeline"] for m in n["milestones"]
                 if m.get("kind") == "vote"]
        self.assertTrue(votes)

    def test_officials_plane_is_officials_only(self):
        off = self._read("officials.json")
        names = {o["name"] for o in off["officials"]}
        self.assertEqual(names, {"Chair Alpha", "Member Beta", "Member Gamma"})
        gamma = next(o for o in off["officials"] if o["name"] == "Member Gamma")
        self.assertEqual(gamma["no"], 1)
        # every cell is a receipt into the tape
        self.assertTrue(all("pid" in v for v in gamma["votes"]))
        # and the page renders JS-off
        page = (self.out / "officials" / "index.html").read_text()
        self.assertIn("The people", page)

    def test_votes_plane_restates_the_meetings_own_roll_calls(self):
        """specs/21 P2: votes.json gathers the roll calls the meeting planes
        already show — one date-ordered plane, one fetch at any corpus size,
        receipts by (pid, t). It must never disagree with the meeting pages
        (officials.json is per-member and deliberately different)."""
        plane = self._read("votes.json")
        self.assertEqual(plane["n_meetings"], 1)
        vs = plane["votes"]
        self.assertEqual(len(vs), self._read("manifest.json")["counts"]["votes"])
        v = vs[0]
        self.assertEqual(set(v), {"pid", "date", "body", "town", "t",
                                  "motion", "outcome", "tally"})
        self.assertEqual((v["outcome"], v["tally"]), ("passes", "3–0"))
        # the receipt resolves: the same vote, at the same second, on the
        # meeting page the dot links to
        m = self._read(f"meetings/{v['pid']}.json")
        self.assertIn(v["t"], [x["t"] for x in m["votes"]])
        self.assertEqual(v["motion"], m["votes"][0]["motion"])

    def test_stats_count_documents_and_votes(self):
        s = self._read("stats.json")
        self.assertEqual(s["counts"]["documents"], 1)
        self.assertEqual(s["counts"]["votes"], 1)

    def test_pwa_manifest_and_service_worker(self):
        wm = self._read("manifest.webmanifest")
        self.assertEqual(wm["scope"], "/app/")
        self.assertTrue((self.out / "sw.js").exists())
        sw = (self.out / "sw.js").read_text()
        self.assertIn("cz-record-", sw)          # cache keyed by corpus hash
        self.assertNotIn("Date.now", sw)         # deterministic, no wall-clock
        # the manifest + RSS autodiscovery ride in every page head
        home = (self.out / "index.html").read_text()
        self.assertIn('rel="manifest"', home)
        self.assertIn('type="application/rss+xml"', home)

    def test_still_watching_page_present(self):
        self.assertTrue((self.out / "watching" / "index.html").exists())

    # -- the analytical eye: framing, analytics, the graph (wave 3) --------

    def test_meeting_carries_the_analyzer_read(self):
        mj = self._read("meetings/vid1.json")
        an = mj["analysis"]
        # framing lenses + questions computed at press time from the transcript
        self.assertIn("framing", an)
        self.assertIn("questions", an)
        self.assertIsInstance(an["framing"].get("lenses"), list)
        stub = (self.out / "m" / "vid1" / "index.html").read_text()
        self.assertIn("eight civic lenses", stub)   # JS-off readable

    def test_analytics_plane_and_page(self):
        a = self._read("analytics.json")
        self.assertIn("framing", a)         # meetings × lenses matrix
        self.assertIn("lens_order", a)
        self.assertEqual(len(a["framing"]), 2)   # one row per live meeting
        self.assertTrue((self.out / "analytics" / "index.html").exists())
        page = (self.out / "analytics" / "index.html").read_text()
        self.assertIn("The record, drawn", page)

    def test_graph_plane_and_page(self):
        g = self._read("graph.json")
        self.assertIn("nodes", g)
        self.assertIn("edges", g)
        # our two seeded meetings share the budget-override issue, but a single
        # shared issue across 2 meetings is real co-occurrence data
        self.assertTrue((self.out / "graph" / "index.html").exists())
        page = (self.out / "graph" / "index.html").read_text()
        self.assertIn("The issue graph", page)
        # the SVG is inline (no external lib — CSP holds) and has a table twin
        self.assertIn("<svg", page)
        self.assertIn("the same, as a table", page)


    # -- the scope plane: towns and bodies (specs/17 §8) -------------------

    def test_towns_plane_is_observed_not_configured(self):
        """towns.json is derived from the pressed meetings. The steward's
        source rules can name a body that has never met; the reader's filter
        must not, because an option that always returns nothing is a promise a
        static edition has no way to explain."""
        t = self._read("towns.json")
        self.assertEqual([x["town"] for x in t["towns"]], ["Testville"])
        town = t["towns"][0]
        self.assertEqual(town["meetings"], 2)
        self.assertEqual(town["first"], "2026-03-10")
        self.assertEqual(town["last"], "2026-06-18")
        self.assertEqual([b["body"] for b in town["bodies"]], ["Board"])
        self.assertEqual(town["bodies"][0]["meetings"], 2)
        self.assertEqual([b["body"] for b in t["bodies"]], ["Board"])
        self.assertEqual(t["bodies"][0]["towns"], ["Testville"])
        self.assertEqual(t["untowned"], 0)      # every seeded meeting has a town

    def test_search_meta_carries_town_for_scoping(self):
        """A scoped search filters its own hits from the meta plane; without
        town on each meeting it would have to fetch a document per hit."""
        meta = self._read("search/meta.json")
        self.assertTrue(all(m["town"] == "Testville" for m in meta))
        self.assertTrue(all(m["body"] == "Board" for m in meta))

    def test_coverage_carries_town_body_cells(self):
        """The strip has to be redrawable under a scope, or it contradicts the
        scoped list beside it."""
        s = self._read("stats.json")
        cov = s["coverage"]
        self.assertTrue(cov)
        for month in cov:
            self.assertIn("cells", month)
            self.assertEqual(sum(month["cells"].values()), month["total"])
        self.assertIn("Testville␟Board", cov[0]["cells"])
        # the home rail's cards carry their town, so the filter needs no fetch
        self.assertTrue(all("town" in m for m in s["new"]))

    def test_single_town_edition_names_it_and_does_not_nag(self):
        """One town is not a question. The bar states it; there is no picker,
        no prompt, and nothing that blocks the page."""
        home = (self.out / "index.html").read_text()
        self.assertIn('class="scope one"', home)
        self.assertIn("the only town on this edition", home)
        self.assertNotIn('class="scopetown"', home)
        self.assertNotIn("scopelink", home)      # no footer re-chooser either
        # and the picker is on every page, not just home
        for rel in ("s/index.html", "m/vid1/index.html", "officials/index.html"):
            self.assertIn('id="scope"', (self.out / rel).read_text(), rel)

    def test_scope_banner_slot_on_every_page(self):
        """The un-trapping banner lands above what the reader came for, on
        every readable page — so it is markup, not something script invents
        late. A door redirect stub is not a page the reader lands on, so it is
        the one exception (it carries a meta refresh instead)."""
        for stub in self.out.rglob("index.html"):
            html = stub.read_text()
            if 'http-equiv="refresh"' in html:
                continue
            self.assertIn('id="scopebanner"', html, str(stub))

    def test_body_filter_degrades_to_a_readable_sentence(self):
        """JS-off there is no dead control: the filter rail is empty and
        hidden, and the same fact ships as prose with checkable counts."""
        home = (self.out / "index.html").read_text()
        self.assertIn('id="bodyfilter"', home)
        self.assertIn('hidden', home)
        self.assertRegex(home, r'class="bodylist"[^>]*>Board <b>2</b>')
        self.assertIn("With JavaScript off this page lists the whole record",
                      home)
        # every card carries what the filter needs
        self.assertIn('data-body="Board"', home)
        self.assertIn('data-town="Testville"', home)

    def test_meeting_stub_declares_its_town(self):
        """The deep-link trap without a query string: a meeting from another
        town. The banner needs the meeting's own town in the markup."""
        stub = (self.out / "m" / "vid1" / "index.html").read_text()
        self.assertIn('data-town="Testville"', stub)
        self.assertIn('data-body="Board"', stub)

    def test_officials_cards_carry_town(self):
        page = (self.out / "officials" / "index.html").read_text()
        self.assertIn('class="offcard" data-town="Testville"', page)

    def test_search_filters_appear_only_when_they_can_do_something(self):
        """One town and one body: a select with a single option is a control
        that cannot change anything, so it is not emitted."""
        page = (self.out / "s" / "index.html").read_text()
        self.assertNotIn('id="townsel"', page)
        self.assertNotIn('id="bodysel"', page)

    def test_reader_still_reads_with_the_backend_dark(self):
        """The load-bearing property, stated more precisely than it used to be.

        This asserted that `/api/` appeared nowhere in the reader — a blanket
        rule that was exactly right while the reader had no server to call.
        specs/19 R1.6 gives it one, so the blanket rule would now have to be
        deleted or the feature abandoned, and neither is the point. The
        property worth keeping was never "no API string in the file"; it was
        **nothing on the path to reading the record depends on a server**.

        So: the edition's own planes are same-origin paths under /app/, the
        API's address is never hardcoded here (it arrives per-pressing from a
        meta tag, so a desk edition has no address to call), and the sole
        outbound call is funnelled through one guarded helper. That the search
        box actually falls back when that helper fails is proven by executing
        the code, in TestReaderDegradesToStatic.
        """
        js = (REPO / "web" / "static" / "app.js").read_text()
        self.assertIn("towns.json", js)
        self.assertNotIn("http://", js.replace("http://www.w3.org", ""))
        self.assertNotIn("localhost", js)
        self.assertTrue((self.out / "towns.json").exists())

        # No API host is baked into the reader. The address comes from the
        # pressing, which is what makes a desk edition serverless by default
        # rather than by everyone remembering.
        self.assertNotIn("run.app", js)
        self.assertNotIn("https://record-api", js)

        # Exactly the sanctioned outbound paths, every one guarded. The search
        # door is askStudio; specs/21 §6.2 added the paper store's two touches
        # — a POST behind the explicit "short link" button and a GET for `?p=`
        # addresses — both additive and both fail-soft (losing the store loses
        # short links, never a paper). Any other `/api/` would be a door
        # nobody wrote a fallback for.
        self.assertEqual(js.count("API + path"), 1)
        self.assertEqual(js.count("/api/papers"), 2,
                         "the paper store's two touches drifted")
        self.assertEqual(js.count("/api/"), 3, "an unsanctioned API call appeared")
        ask = re.search(r"  async function askStudio\(path\) \{.+?\n  \}",
                        js, re.S).group(0)
        self.assertIn("if (!API || API_DOWN) return null;", ask)
        # both store touches are timed, caught, and no-API-safe — executing
        # their fallbacks is TestPaper's and the browser's job; the shape is
        # pinned here beside the door count
        for fn in ("paperShortLink", "fetchStoredPaper"):
            src = re.search(rf"  async function {fn}\(.*?\n  \}}", js, re.S)
            self.assertTrue(src, f"{fn} moved")
            for guard in ("API_TIMEOUT_MS", "catch", "if (!API)"):
                self.assertIn(guard, src.group(0),
                              f"{fn} lost its {guard!r} guard")

        # Every edition plane the reader reads is a path under /app/.
        for plane in re.findall(r"getJSON\(`([^`]+)`", js):
            self.assertTrue(plane.startswith("${BASE}/"),
                            f"{plane} is not an edition path")


class TestScopeOnTwoTowns(unittest.TestCase):
    """A second town changes the shape of the chrome, and only a second town
    can exercise the trap specs/17 §14 leaves open — so it gets its own
    pressing rather than a bolt-on to the single-town corpus."""

    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory()
        root = Path(cls.tmp.name)
        db = root / "two.db"
        TestBakeEdition._seed(db)
        from memory.store import Corpus
        c = Corpus(str(db))
        segs = [{"start": i * 10.0, "end": i * 10 + 9, "speaker": "Chair",
                 "text": f"the zoning appeal item {i}"} for i in range(4)]
        c.replace_segments("vid3", segs)
        c.upsert_meeting({"id": "vid3", "title": "Zoning Board — July",
                          "date": "2026-07-02", "town": "Otherville",
                          "body": "Zoning Board of Appeals",
                          "source_kind": "youtube", "video_id": "vid3",
                          "url": "https://youtube.com/watch?v=vid3",
                          "url_canon": "youtube:vid3", "duration": 60,
                          "n_segments": len(segs), "status": "live"})
        # a meeting the record never learned a town for — it must not vanish
        c.replace_segments("vid4", segs)
        c.upsert_meeting({"id": "vid4", "title": "Unknown provenance",
                          "date": "2026-07-03", "town": "", "body": "",
                          "source_kind": "youtube", "video_id": "vid4",
                          "url": "https://youtube.com/watch?v=vid4",
                          "url_canon": "youtube:vid4", "duration": 60,
                          "n_segments": len(segs), "status": "live"})
        cls.out = root / "app"
        from web import bake
        bake.bake(str(db), str(cls.out), "9.9.9", "https://example.org")

    @classmethod
    def tearDownClass(cls):
        cls.tmp.cleanup()

    def _read(self, rel):
        return json.loads((self.out / rel).read_text())

    def test_untowned_meeting_is_counted_never_filed_under_a_town(self):
        t = self._read("towns.json")
        self.assertEqual([x["town"] for x in t["towns"]],
                         ["Otherville", "Testville"])
        self.assertEqual(t["untowned"], 1)
        self.assertEqual(t["meetings"], 4)
        # it belongs to no town, so it is in no town's bucket
        self.assertEqual(sum(x["meetings"] for x in t["towns"]), 3)
        # but its (empty) body is still a real filter option
        self.assertIn("", [b["body"] for b in t["bodies"]])

    def test_picker_offers_every_town_plus_the_whole_record(self):
        home = (self.out / "index.html").read_text()
        self.assertIn('data-town="Testville"', home)
        self.assertIn('data-town="Otherville"', home)
        self.assertIn("the whole record", home)
        self.assertNotIn("the only town on this edition", home)
        # re-choosable from the footer, and the anchor works JS-off
        self.assertIn('class="scopelink" href="#scope"', home)

    def test_search_gets_real_filters_when_there_is_a_choice(self):
        page = (self.out / "s" / "index.html").read_text()
        self.assertIn('<select name="town" id="townsel"', page)
        self.assertIn('<select name="body" id="bodysel"', page)
        self.assertIn("every town", page)
        self.assertIn("no body recorded", page)   # the untowned meeting's body

    def test_bodies_are_per_town_not_a_flat_list(self):
        t = self._read("towns.json")
        other = next(x for x in t["towns"] if x["town"] == "Otherville")
        self.assertEqual([b["body"] for b in other["bodies"]],
                         ["Zoning Board of Appeals"])
        test = next(x for x in t["towns"] if x["town"] == "Testville")
        self.assertEqual([b["body"] for b in test["bodies"]], ["Board"])

    def test_coverage_cells_separate_the_towns(self):
        cov = self._read("stats.json")["coverage"]
        july = next(m for m in cov if m["month"] == "2026-07")
        self.assertEqual(july["cells"]["Otherville␟Zoning Board of Appeals"], 1)
        self.assertEqual(july["cells"]["␟"], 1)   # the untowned meeting
        self.assertEqual(july["total"], 2)

    def test_two_town_edition_presses_idempotently(self):
        """The scope plane is derived from the corpus; nothing in it may vary
        between two pressings of the same record."""
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = root / "two.db"
            TestBakeEdition._seed(db)
            from memory.store import Corpus
            c = Corpus(str(db))
            c.replace_segments("vid3", [{"start": 0.0, "end": 9, "text": "zoning"}])
            c.upsert_meeting({"id": "vid3", "title": "Zoning Board — July",
                              "date": "2026-07-02", "town": "Otherville",
                              "body": "Zoning Board of Appeals",
                              "source_kind": "youtube", "video_id": "vid3",
                              "url_canon": "youtube:vid3", "duration": 60,
                              "n_segments": 1, "status": "live"})
            from web import bake
            bake.bake(str(db), str(root / "a"), "1.0.0", "https://x.org")
            bake.bake(str(db), str(root / "b"), "1.0.0", "https://x.org")
            for p in sorted((root / "a").rglob("*")):
                if p.is_file():
                    rel = p.relative_to(root / "a")
                    self.assertEqual(p.read_bytes(), (root / "b" / rel).read_bytes(),
                                     f"{rel} differs between two bakes")


class TestIdempotence(unittest.TestCase):
    def test_same_corpus_byte_identical(self):
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = root / "c.db"
            TestBakeEdition._seed(db)
            from web import bake
            bake.bake(str(db), str(root / "a"), "1.0.0", "https://x.org")
            bake.bake(str(db), str(root / "b"), "1.0.0", "https://x.org")
            a = sorted((root / "a").rglob("*"))
            for p in a:
                if p.is_file():
                    rel = p.relative_to(root / "a")
                    self.assertEqual(p.read_bytes(), (root / "b" / rel).read_bytes(),
                                     f"{rel} differs between two bakes")

    def test_byte_identical_across_hash_seeds(self):
        """The rsync deploy re-uploads on any diff, and a real press runs in a
        fresh container process — so "press today == press tomorrow" spans
        Python hash seeds. The in-process test above shares one seed and cannot
        see set/dict-iteration order leaking into edition bytes; this presses
        the SAME corpus in two subprocesses with different PYTHONHASHSEED and
        byte-compares, which is the determinism the deploy actually needs."""
        import os
        import subprocess
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = root / "c.db"
            TestBakeEdition._seed(db)

            def press(dst, seed):
                r = subprocess.run(
                    [sys.executable, "-m", "web.bake", "--corpus", str(db),
                     "--out", str(root / dst), "--base", "https://x.org"],
                    cwd=str(REPO), env={**os.environ, "PYTHONHASHSEED": seed},
                    capture_output=True, text=True)
                self.assertEqual(r.returncode, 0, r.stderr)

            press("a", "0")
            press("b", "1")
            for p in sorted((root / "a").rglob("*")):
                if p.is_file():
                    rel = p.relative_to(root / "a")
                    self.assertEqual(
                        p.read_bytes(), (root / "b" / rel).read_bytes(),
                        f"{rel} differs across hash seeds — nondeterministic press")


class TestTombstones(unittest.TestCase):
    """A steward's forget leaves an explanation, not a bare 404 (specs/20 §6).
    The date comes from the audit ledger — stored state, never a wall clock —
    so the tombstone presses idempotently."""

    def test_press_writes_a_tombstone_with_the_audit_date(self):
        from memory.store import Corpus
        from web import bake
        with tempfile.TemporaryDirectory() as td:
            root = Path(td)
            db = root / "c.db"
            TestBakeEdition._seed(db)
            forget = [{"id": "issue:testville:gone-issue", "name": "a gone issue",
                       "town": "Testville", "date": "2026-05-01"}]
            # the desk store has no audit ledger; stand one in for this press so
            # the emission path is exercised end to end
            orig = Corpus.list_forgotten
            Corpus.list_forgotten = lambda self, limit=1000: list(forget)
            try:
                bake.bake(str(db), str(root / "app"), "1.0.0", "https://x")
            finally:
                Corpus.list_forgotten = orig
            p = root / "app" / "i" / "issue_testville_gone-issue" / "index.html"
            self.assertTrue(p.is_file(), "no tombstone was written")
            html = p.read_text()
            self.assertIn("removed from the record by a steward on 2026-05-01", html)
            self.assertIn("a gone issue", html)
            self.assertIn("Content-Security-Policy", html)   # a real page
            # the live issue's own page still stands, untouched
            self.assertTrue((root / "app" / "i" /
                             "issue_testville_budget-override" / "index.html").is_file())

    def test_a_live_issue_wins_its_old_grave(self):
        """A re-created issue must not be buried by its own tombstone: a slug a
        live issue occupies is never tombstoned."""
        from web import bake

        class Forgetful:
            def list_forgotten(self, limit=1000):
                return [{"id": "issue:x:thing", "name": "thing", "date": "2026-07-01"}]
        b = bake.Bake(Forgetful(), Path("/tmp/none"), "1.0.0", None)
        self.assertEqual(b.bake_tombstones({bake.islug("issue:x:thing")}), [])
        # but with no live claimant, the grave stands
        got = b.bake_tombstones(set())
        self.assertEqual(got[0]["slug"], bake.islug("issue:x:thing"))
        self.assertEqual(got[0]["date"], "2026-07-01")

    def test_the_desk_store_keeps_no_audit_ledger(self):
        from memory.store import Corpus
        with tempfile.TemporaryDirectory() as td:
            c = Corpus(str(Path(td) / "c.db"))
            self.assertEqual(c.list_forgotten(), [])


# TestRegistryMatchesDesk lives in the control-z monorepo: it pins the web
# registry to the DESK's core.js, a pairing that has no second half here.


class TestLiveFirstEdition(unittest.TestCase):
    """`--api`: the one pressing that has a Studio behind it.

    Two promises are under test, and the second is the load-bearing one.

    **A desk edition does not change.** Press without `--api` and the bytes are
    what they were before the flag existed — no meta tag, no widened policy, no
    extra manifest key. The desk is the common case and it must not pay for a
    feature it does not have.

    **A Studio edition is still complete without its Studio.** The API is an
    upgrade on a static floor: every meeting, issue, timeline and the whole
    prebuilt lexical index are in the edition either way. This was proven once
    by stopping Postgres and walking the site, and it is asserted here so it
    stays true.
    """

    API = "https://record-api-907309358085.us-east1.run.app"

    def press(self, out, api=""):
        from web import bake
        return bake.bake(str(self.db), str(out), "1.0.0", "https://x.org",
                         api=api)

    def setUp(self):
        self.td = tempfile.TemporaryDirectory()
        self.addCleanup(self.td.cleanup)
        self.root = Path(self.td.name)
        self.db = self.root / "c.db"
        TestBakeEdition._seed(self.db)
        # `emit` holds the API as module state; leaving it set would leak into
        # every later test in the process.
        from web import emit
        self.addCleanup(emit.set_api, "")

    # -- the desk pays nothing ---------------------------------------------

    def test_without_api_no_trace_of_one(self):
        out = self.root / "desk"
        self.press(out)
        html = (out / "s" / "index.html").read_text(encoding="utf-8")
        self.assertNotIn("record-api", html)
        self.assertIn("connect-src 'self';", html)
        self.assertNotIn("api", json.loads(
            (out / "manifest.json").read_text(encoding="utf-8")))

    def test_a_desk_press_is_byte_identical_either_side_of_a_studio_press(self):
        """The module-state trap: press with an API, then without, and the
        second must not inherit the first's."""
        a, b, c = self.root / "a", self.root / "b", self.root / "c"
        self.press(a)
        self.press(b, api=self.API)
        self.press(c)
        for p in sorted(a.rglob("*")):
            if p.is_file():
                rel = p.relative_to(a)
                self.assertEqual(p.read_bytes(), (c / rel).read_bytes(),
                                 f"{rel} changed after a Studio press")

    # -- the Studio edition -------------------------------------------------

    def test_with_api_the_address_and_the_permission_arrive_together(self):
        out = self.root / "studio"
        self.press(out, api=self.API)
        html = (out / "s" / "index.html").read_text(encoding="utf-8")
        self.assertIn(f'<meta name="record-api" content="{self.API}">', html)
        # the policy names exactly that origin, and nothing else moved
        self.assertIn(f"connect-src 'self' {self.API};", html)
        self.assertIn("script-src 'self';", html)
        self.assertIn("img-src 'self' https://i.ytimg.com data:;", html)

    def test_the_policy_names_an_origin_never_a_path(self):
        out = self.root / "path"
        self.press(out, api=self.API + "/some/path")
        html = (out / "s" / "index.html").read_text(encoding="utf-8")
        self.assertIn(f"connect-src 'self' {self.API};", html)

    def test_the_manifest_records_which_studio_pressed_it(self):
        out = self.root / "m"
        self.press(out, api=self.API)
        man = json.loads((out / "manifest.json").read_text(encoding="utf-8"))
        self.assertEqual(man["api"], self.API)

    def test_the_search_note_stops_promising_what_it_cannot_do(self):
        """The sentence that was wrong for a month, both ways round."""
        desk, studio = self.root / "d2", self.root / "s2"
        self.press(desk)
        self.press(studio, api=self.API)
        self.assertIn("Meaning-search needs the Studio",
                      (desk / "s" / "index.html").read_text(encoding="utf-8"))
        self.assertIn("two ways at once",
                      (studio / "s" / "index.html").read_text(encoding="utf-8"))

    # -- the covenant: complete without the Studio --------------------------

    def test_a_studio_edition_carries_the_whole_static_record_anyway(self):
        """If the API vanished, this edition still reads. Same files, same
        index, same meetings as a desk pressing — the API adds a way to ask,
        never a thing to hold."""
        desk, studio = self.root / "d3", self.root / "s3"
        self.press(desk)
        self.press(studio, api=self.API)
        names = lambda r: {str(p.relative_to(r)) for p in r.rglob("*")
                           if p.is_file()}
        self.assertEqual(names(desk), names(studio))
        for rel in ("search/segs.json", "search/meta.json", "stats.json",
                    "urls.json", "towns.json"):
            self.assertEqual((desk / rel).read_bytes(),
                             (studio / rel).read_bytes(), rel)

    def test_a_studio_press_is_idempotent_too(self):
        a, b = self.root / "i1", self.root / "i2"
        self.press(a, api=self.API)
        self.press(b, api=self.API)
        for p in sorted(a.rglob("*")):
            if p.is_file():
                rel = p.relative_to(a)
                self.assertEqual(p.read_bytes(), (b / rel).read_bytes(),
                                 f"{rel} differs between two Studio bakes")


class TestReaderDegradesToStatic(unittest.TestCase):
    """The reader's half of live-first, and the promise underneath it.

    specs/17 §6.2 is a covenant, not a preference: if Cloud Run and Postgres
    both vanish, the record still reads. So the interesting cases are not the
    ones where the Studio answers — they are the ones where it does not.
    """

    JS = (REPO / "web" / "static" / "app.js").read_text()

    def node(self, body):
        import shutil
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        return subprocess.run([node, "-e", body], capture_output=True, text=True)

    def lift(self, pattern):
        m = re.search(pattern, self.JS, re.S)
        self.assertTrue(m, f"{pattern!r} not found in the reader — did it move?")
        return m.group(0)

    # -- structure: the fallback cannot be removed by accident -------------

    def test_search_falls_through_to_the_static_index(self):
        """`runSearch` may prefer the Studio; it must always be able to answer
        without one. If someone deletes the fallback, this fails rather than
        the record quietly needing a backend."""
        run = self.lift(r"  async function runSearch\(q\) \{.+?\n  \}")
        self.assertIn("staticSearch", run,
                      "runSearch no longer reaches the static index")
        self.assertIn("async function staticSearch", self.JS)

    def test_the_static_path_touches_no_api(self):
        """The prebuilt index answers from this origin and nowhere else."""
        static = self.lift(r"  async function staticSearch\(q, terms, box\) \{.+?\n  \}")
        for forbidden in ("askStudio", "API +", "/api/search"):
            self.assertNotIn(forbidden, static,
                             f"the static path reached for {forbidden!r}")

    def test_a_missing_meta_tag_means_a_desk_edition(self):
        """No tag, no API, no attempt — every desk edition's condition."""
        self.assertIn('$(\'meta[name="record-api"]\') || {}', self.JS)

    # -- behaviour: a dead Studio is one timed attempt, then silence -------

    def test_a_dead_studio_returns_null_and_is_not_asked_twice(self):
        body = "\n".join([
            "let calls = 0;",
            "const AbortController = globalThis.AbortController;",
            "const fetch = () => { calls++; return Promise.reject(new Error('down')); };",
            'const API = "https://api.example";',
            "const API_TIMEOUT_MS = 50;",
            "let API_DOWN = false;",
            self.lift(r"  async function askStudio\(path\) \{.+?\n  \}"),
            "(async () => {",
            "  const a = await askStudio('/api/search?q=x');",
            "  const b = await askStudio('/api/search?q=y');",
            "  if (a !== null || b !== null) { console.log('FAIL: returned a value'); process.exit(1); }",
            "  if (calls !== 1) { console.log('FAIL: asked ' + calls + ' times, want 1'); process.exit(1); }",
            "  if (!API_DOWN) { console.log('FAIL: API_DOWN not set'); process.exit(1); }",
            "  console.log('ok');",
            "})();",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"askStudio mishandled a dead Studio:\n{r.stdout}{r.stderr}")

    def test_a_slow_studio_is_abandoned_rather_than_waited_on(self):
        """A cold Cloud Run instance must not hold the reader hostage."""
        body = "\n".join([
            "const AbortController = globalThis.AbortController;",
            "const fetch = (u, o) => new Promise((res, rej) => {",
            "  o.signal.addEventListener('abort', () => rej(new Error('aborted')));",
            "});",
            'const API = "https://api.example";',
            "const API_TIMEOUT_MS = 60;",
            "let API_DOWN = false;",
            self.lift(r"  async function askStudio\(path\) \{.+?\n  \}"),
            "(async () => {",
            "  const t0 = Date.now();",
            "  const a = await askStudio('/api/search?q=x');",
            "  const dt = Date.now() - t0;",
            "  if (a !== null) { console.log('FAIL: returned a value'); process.exit(1); }",
            "  if (dt > 2000) { console.log('FAIL: waited ' + dt + 'ms'); process.exit(1); }",
            "  console.log('ok');",
            "})();",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"askStudio did not give up:\n{r.stdout}{r.stderr}")

    def test_no_reader_request_ever_carries_credentials(self):
        """Readers are never identified. The fetch says so explicitly rather
        than relying on the default, because the default is a thing that can
        change under you."""
        ask = self.lift(r"  async function askStudio\(path\) \{.+?\n  \}")
        self.assertIn('credentials: "omit"', ask)

    # -- the four chips -----------------------------------------------------

    def test_every_provenance_the_server_can_send_has_a_chip(self):
        """The vocabulary is set in two places and read in a third.

        `memory.policy.blend` emits `word` / `related` / `both`; the hosted
        store renames `related` to `meaning` when the neural half answered, so
        the reader can tell "a related word" from "what you meant". A value
        the reader has no chip for would render a blank badge, so the two ends
        are compared rather than trusted."""
        from memory import policy
        kw = [{"seg_id": 1, "score": 1.0}, {"seg_id": 2, "score": 0.9}]
        vec = [({"seg_id": 2, "score": 0.9}, 0.8), ({"seg_id": 3}, 0.7)]
        produced = {h["why"] for h in policy.blend(kw, vec, 10)}
        self.assertEqual(produced, {"word", "both", "related"})

        says = self.lift(r"  const WHY_SAYS = \{.+?\};")
        # `meaning` is the fourth, added by record/store.py in the neural space
        for w in produced | {"meaning"}:
            self.assertIn(f"{w}:", says, f"no chip for provenance {w!r}")
        self.assertIn('h["why"] = "meaning"',
                      (REPO / "record" / "store.py").read_text(),
                      "the hosted store no longer produces `meaning`")

    def test_an_unknown_provenance_renders_nothing_rather_than_an_empty_badge(self):
        body = "\n".join([
            "const esc = s => String(s == null ? '' : s);",
            self.lift(r"  const WHY_SAYS = \{.+?\};"),
            self.lift(r"  function why\(w\) \{.+?\n  \}"),
            "if (why('nonsense') !== '') { console.log('FAIL:', why('nonsense')); process.exit(1); }",
            "if (!why('meaning').includes('prov-meaning')) { console.log('FAIL: no class'); process.exit(1); }",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"why() mishandled an unknown value:\n{r.stdout}{r.stderr}")


class TestReel(unittest.TestCase):
    """The reel's client-only machinery (specs/20 §6/§7, P1), executed for real
    in node. A share link is a covenant with whoever you send it to: it must
    round-trip. So the encode/decode, the cite sheet, and the reel.json the desk
    opens are lifted from the reader and run — the same treatment canon() and
    resolve() get, and for the same reason.
    """

    JS = (REPO / "web" / "static" / "app.js").read_text()
    PRELUDE = "\n".join([
        'const BASE = "/app";',
        'const location = { origin: "https://publicrecord.studio" };',
    ])

    def node(self, body):
        import shutil
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
            self.lift(r"const REEL_VS = .+?;"),
            self.lift(r"const r1 = .+?;"),
            self.lift(r"const clipLen = .+?;"),
            self.lift(r"const reelRuntime = .+?;"),
            self.lift(r"const encodeClips = .+?;"),
            self.lift(r"const encodeClipsX = .+?;"),
            self.lift(r"function shareURL\(pid, clips\) \{.+?\n  \}"),
            self.lift(r"function reelShareURL\(clips\) \{.+?\n  \}"),
            self.lift(r"const reelPids = .+?;"),
            self.lift(r"function decodeReel\(search\) \{.+?\n  \}"),
            self.lift(r"function citeSheet\(meta, clips\) \{.+?\n  \}"),
            self.lift(r"function reelJSON\(meta, clips\) \{.+?\n  \}"),
        ])

    def test_share_link_round_trips(self):
        """encode → decode is the identity on a reel's clips, and a link that
        lost a character in an email degrades to fewer clips, never a throw."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "const clips = [{start:900.2,end:907.3},{start:1147.6,end:1151.2},{start:12.0,end:24.0}];",
            "const url = shareURL('2Yhg', clips);",
            "const back = decodeReel(url.slice(url.indexOf('?')));",
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "if (back.v !== '1') fail('v='+back.v);",
            "if (back.pid !== '2Yhg') fail('pid='+back.pid);",
            "if (back.clips.length !== 3) fail('len='+back.clips.length);",
            "for (let i=0;i<3;i++){ if (back.clips[i].start!==clips[i].start || back.clips[i].end!==clips[i].end)",
            "  fail('clip'+i+' '+JSON.stringify(back.clips[i])); }",
            # 'garbage' has no pair; '5-3' has end<=start — both dropped, 2 remain
            "const bad = decodeReel('?v=1&m=x&c=1-2,garbage,5-3,7-9');",
            "if (bad.clips.length !== 2) fail('bad drop '+JSON.stringify(bad.clips));",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"reel round-trip failed:\n{r.stdout}{r.stderr}")

    def test_cite_sheet_carries_every_clip_with_a_deep_link(self):
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "const meta = {pid:'2Yhg', title:'Select Board — March', town:'Brookline', "
            "body:'Select Board', date:'2026-03-10'};",
            "const clips = [{start:900.2,end:907.3,kind:'vote',quote:'the override passes',speaker:'Chair:'},"
            "{start:12.0,end:24.0,kind:'question',quote:'how much is the levy'}];",
            "const s = citeSheet(meta, clips);",
            "function fail(m){ console.log('FAIL', m, '\\n', s); process.exit(1); }",
            "for (const n of ['Select Board — March','a reel of 2 moments','the override passes',"
            "'how much is the levy','https://publicrecord.studio/app/m/2Yhg#t900','#t12',"
            "'Select Board · Brookline · 2026-03-10','— Chair'])",
            "  if (!s.includes(n)) fail('missing '+JSON.stringify(n));",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"cite sheet malformed:\n{r.stdout}{r.stderr}")

    def test_reel_json_maps_onto_the_desk_renderer(self):
        """The reel.json's clips carry the {start,end} highlighter/reel.py's
        render_reel needs, in reel order, plus the media locator and the plain
        hand-off sentence. The one desk-bound step, made openable."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "const meta = {pid:'2Yhg', title:'Select Board — March', town:'Brookline', "
            "body:'Select Board', date:'2026-03-10', video_id:'2YhgO14jXys', "
            "url:'https://youtube.com/watch?v=2YhgO14jXys'};",
            "const clips = [{start:900.2,end:907.3,kind:'vote',quote:'passes',t:900.2},"
            "{start:12.0,end:24.0,kind:'question',quote:'how much',t:12.0}];",
            "const j = reelJSON(meta, clips);",
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "if (j.schema !== 'publicrecord.reel/1') fail('schema '+j.schema);",
            "if (j.clips.length !== 2) fail('clips '+j.clips.length);",
            "if (j.clips[0].start !== 900.2 || j.clips[0].end !== 907.3) fail('clip0 '+JSON.stringify(j.clips[0]));",
            "if (j.clips[1].start !== 12 || j.clips[1].end !== 24) fail('clip1 '+JSON.stringify(j.clips[1]));",
            "if (j.meeting.video_id !== '2YhgO14jXys') fail('video_id '+j.meeting.video_id);",
            "if (typeof j.runtime !== 'number' || j.runtime <= 0) fail('runtime '+j.runtime);",
            "if (!/desk/i.test(j.note)) fail('note lacks the desk hand-off');",
            "if (!j.share.includes('/app/r?v=1&m=2Yhg')) fail('share '+j.share);",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"reel.json malformed:\n{r.stdout}{r.stderr}")

    def test_the_viewer_advances_clip_to_clip_even_out_of_order(self):
        """The acceptance's hard half, executed: the reel plays clip to clip
        (specs/20 §7). Clips play in reel order, not chronological, so the next
        clip can be *earlier* in the tape. A short clip reached by a backward
        seek is the trap: while the seek buffers, the facade repeats the old
        (past-the-clip) time, and TWO such stale reports must not arm-then-skip
        the clip. The `armed` gate — which arms only on a report inside the clip
        and before its end — is what proves the short clip actually plays."""
        adv = (self.lift(r"  function reelAdvance\(t\) \{.+?\n  \}") + "\n"
               + self.lift(r"  function reelNext\(\) \{.+?\n  \}"))
        rseek = self.lift(r"  function reelSeek\(c\) \{.+?\n  \}")
        body = "\n".join([
            "const seeks = [];",
            "const YT = {};",   # no player window → reelSeek falls to ytSeek
            "function ytSeek(t){ seeks.push(t); }",
            "function ytSend(){}",
            "function reelShow(){}",
            "const reelPids = clips => [...new Set(clips.map(c => c.pid).filter(Boolean))];",
            rseek,
            "function fail(m){ console.log('FAIL', m, 'seeks='+JSON.stringify(seeks),"
            " 'i='+REELPLAY.i, 'armed='+REELPLAY.armed, 'active='+REELPLAY.active); process.exit(1); }",
            # clip 1 is a 1s clip {19,20} placed AFTER {10,20}: reaching it is a
            # backward seek of 1s, so the two stale 20s sit inside the arm window.
            # all one meeting (video X) → reelSeek is a plain same-tape ytSeek.
            "let REELPLAY = { active:true, armed:false, i:0, vid:'X', clips:"
            "[{start:10,end:20,video_id:'X'},{start:19,end:20,video_id:'X'},{start:30,end:35,video_id:'X'}] };",
            adv,
            # play clip0 to its end, then TWO stale 20s while the seek to 19 buffers
            "[10,11,19,20, 20,20].forEach(t => reelAdvance(t));",
            # the fix holds here: still on clip1, NOT armed by a stale time, not skipped
            "if (REELPLAY.i !== 1) fail('a stale time skipped the short clip');",
            "if (REELPLAY.armed !== false) fail('a stale time armed the short clip');",
            "if (JSON.stringify(seeks) !== JSON.stringify([19])) fail('advanced too far on stale time');",
            # now the real clip1 times arrive and it plays through to clip2, then stops
            "[19,19.5,20, 20, 30,31,35].forEach(t => reelAdvance(t));",
            "if (JSON.stringify(seeks) !== JSON.stringify([19,30])) fail('wrong seeks');",
            "if (REELPLAY.active !== false) fail('did not stop after the last clip');",
            "if (REELPLAY.i !== 2) fail('final clip index');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"the seek engine misfired:\n{r.stdout}{r.stderr}")

    def test_a_cross_meeting_reel_carries_each_clips_own_meeting(self):
        """specs/20 §7.9 P2-B. A reel of one meeting stays the v1 link every
        existing share + kit page already carries; the moment it spans two, it
        becomes v2 (`<pid>:<start>-<end>`), and decode restores each clip's own
        meeting. v1 remains readable — its clips inherit the single `m=`."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            # one meeting → v1, byte-identical to before
            "const one = [{pid:'AAA',start:10,end:20},{pid:'AAA',start:30,end:40}];",
            "const u1 = reelShareURL(one);",
            "if (!u1.includes('/app/r?v=1&m=AAA&c=10-20,30-40')) fail('single-meeting not v1: '+u1);",
            # two meetings → v2, each clip prefixed with its meeting
            "const two = [{pid:'AAA',start:10,end:20},{pid:'B-b_9',start:5,end:9}];",
            "const u2 = reelShareURL(two);",
            "if (!u2.includes('/app/r?v=2&c=')) fail('cross-meeting not v2: '+u2);",
            "const d = decodeReel(u2.slice(u2.indexOf('?')));",
            "if (d.v !== '2') fail('v='+d.v);",
            "if (d.clips.length !== 2) fail('len='+d.clips.length);",
            "if (d.clips[0].pid !== 'AAA' || d.clips[1].pid !== 'B-b_9') fail('pids '+JSON.stringify(d.clips));",
            "if (d.clips[1].start !== 5 || d.clips[1].end !== 9) fail('range '+JSON.stringify(d.clips[1]));",
            # a v1 link still decodes, its clips inheriting the single m=
            "const v1 = decodeReel('?v=1&m=Z9&c=1-2,3-4');",
            "if (v1.clips.length !== 2 || v1.clips[0].pid !== 'Z9' || v1.clips[1].pid !== 'Z9') fail('v1 inherit '+JSON.stringify(v1.clips));",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"cross-meeting link failed:\n{r.stdout}{r.stderr}")

    def test_reel_seek_switches_the_tape_only_across_meetings(self):
        """The viewer plays clip to clip within one tape, and loads a new tape
        (loadVideoById) only when the next clip is from another meeting — so a
        cross-meeting reel actually crosses, and a same-meeting reel never
        needlessly reloads the player."""
        rseek = self.lift(r"  function reelSeek\(c\) \{.+?\n  \}")
        body = "\n".join([
            "const sent = []; const seeks = [];",
            "const YT = { win: {}, ready: true };",
            "function ytSend(kind, func, args){ sent.push([func, args]); }",
            "function ytSeek(t){ seeks.push(t); }",
            "let REELPLAY = { vid: 'AAA' };",
            rseek,
            "function fail(m){ console.log('FAIL', m, JSON.stringify({sent,seeks})); process.exit(1); }",
            # same meeting → a plain seek, no tape reload
            "reelSeek({video_id:'AAA', start:42});",
            "if (seeks.length !== 1 || seeks[0] !== 42) fail('same-tape should seek');",
            "if (sent.length !== 0) fail('same-tape must not reload');",
            # another meeting → loadVideoById at the clip start, vid updated
            "reelSeek({video_id:'BBB', start:7});",
            "if (sent.length !== 1 || sent[0][0] !== 'loadVideoById') fail('cross should loadVideoById');",
            "if (sent[0][1][0].videoId !== 'BBB' || sent[0][1][0].startSeconds !== 7) fail('bad load args '+JSON.stringify(sent[0]));",
            "if (REELPLAY.vid !== 'BBB') fail('vid not updated');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"reel tape-switch failed:\n{r.stdout}{r.stderr}")

    def test_a_tape_less_clip_is_skipped_never_played_on_the_wrong_tape(self):
        """A cross-meeting reel can include a clip whose meeting has no video
        (audio-only civic tape). It must NOT play on the previous meeting's tape
        under a label naming another — reelAdvance skips it to the next clip that
        has a tape, and reelSeek never falls back to the loaded video."""
        adv = (self.lift(r"  function reelAdvance\(t\) \{.+?\n  \}") + "\n"
               + self.lift(r"  function reelNext\(\) \{.+?\n  \}"))
        rseek = self.lift(r"  function reelSeek\(c\) \{.+?\n  \}")
        body = "\n".join([
            "const sent = []; const seeks = [];",
            "const YT = { win:{}, ready:true };",
            "function ytSend(kind, func, args){ sent.push([func, args]); }",
            "function ytSeek(t){ seeks.push(t); }",
            "function reelShow(){}",
            # clip1 has NO video_id (cite-only); clip2 is meeting Y
            "let REELPLAY = { active:true, armed:false, i:0, vid:'X', clips:"
            "[{start:10,end:20,video_id:'X'},{start:30,end:40},{start:5,end:9,video_id:'Y'}] };",
            rseek, adv,
            "function fail(m){ console.log('FAIL', m, JSON.stringify({i:REELPLAY.i,sent,seeks})); process.exit(1); }",
            # play clip0 to its end → advance must SKIP the tape-less clip1 → clip2
            "[10,15,20].forEach(t => reelAdvance(t));",
            "if (REELPLAY.i !== 2) fail('did not skip the tape-less clip');",
            "if (!sent.some(s => s[0]==='loadVideoById' && s[1][0].videoId==='Y')) fail('did not switch to the playable clip');",
            # reelSeek on a tape-less clip is a no-op — no seek onto the wrong tape
            "seeks.length = 0; sent.length = 0;",
            "reelSeek({start:30,end:40});",
            "if (seeks.length || sent.length) fail('a tape-less clip seeked the wrong tape');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"tape-less clip handling failed:\n{r.stdout}{r.stderr}")

    def test_a_clip_is_identified_by_kind_and_time_not_time_alone(self):
        """A contested roll call is emitted as two moments — a vote and a
        tension — anchored to the same segment start (web/bake.py dedups on
        `(kind, int(t))`, not time). The composer must tell them apart, or
        ticking one silently toggles the other. Its identity key must match the
        bake's, plus the meeting (P2-B): (meeting, kind, time)."""
        body = "\n".join([
            self.lift(r"const r1 = .+?;"),
            "const CREEL = { pid: 'M' };",   # a moment read off the page stands for this meeting
            self.lift(r"  const clipId = c => .+?;"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const vote = {kind:'vote', t:100.0}, tension = {kind:'tension', t:100.0};",
            "if (clipId(vote) === clipId(tension)) fail('same-second twins collide');",
            # the same moment ticked twice is the same identity (toggle off works)
            "if (clipId(vote) !== clipId({kind:'vote', t:100.04})) fail('rounding split one moment in two');",
            # the same kind+second from two meetings is NOT the same clip (P2-B)
            "if (clipId({pid:'A',kind:'vote',t:100}) === clipId({pid:'B',kind:'vote',t:100})) fail('two meetings collided');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"clip identity is wrong:\n{r.stdout}{r.stderr}")


class TestCuttingRoom(unittest.TestCase):
    """specs/22 P0: cut from anywhere, executed in node. The ticks put clips
    on the tray from three new surfaces; the tray acts on the STORED reel
    from any page; trims snap to the record's own segment bounds fetched
    from the pressed transcript.txt. The pieces with edges — the timestamp
    parser, the trim step, the segment tick's bounds, the mid-fetch race —
    are lifted and run, decodeReel's-law style."""

    JS = (REPO / "web" / "static" / "app.js").read_text()
    PRELUDE = "\n".join([
        'const BASE = "/app";',
        'const location = { origin: "https://publicrecord.studio" };',
    ])

    def node(self, body):
        import shutil
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        return subprocess.run([node, "-e", body], capture_output=True, text=True)

    def lift(self, pattern):
        m = re.search(pattern, self.JS, re.S)
        self.assertTrue(m, f"{pattern!r} not found in the reader — did it move?")
        return m.group(0)

    def test_transcript_times_parse_both_shapes_and_drop_garbage(self):
        """parseSegTimes is total over the pressed transcript.txt: [M:SS]
        under an hour, [H:MM:SS] over, and every other line — the title, the
        date, ASR noise, a blank — is simply not a bound."""
        body = "\n".join([
            self.lift(r"  function parseSegTimes\(tx\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const tx = ['Brookline School Committee - June 18, 2026',",
            "  '2026-06-18', '', '[0:22] [music]', '[3:54] Mhm.',",
            "  '[59:59] almost an hour', '[1:03:45] over an hour',",
            "  '[5:04:03] the long tape', 'no stamp here', '[bad] stamp',",
            "  '[12] lonely'].join('\\n');",
            "const got = parseSegTimes(tx);",
            "const want = [22, 234, 3599, 3825, 18243];",
            "if (JSON.stringify(got) !== JSON.stringify(want))",
            "  fail(JSON.stringify(got) + ' want ' + JSON.stringify(want));",
            "if (parseSegTimes(null).length || parseSegTimes('').length)",
            "  fail('empty input must parse to no bounds');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"parseSegTimes drifted:\n{r.stdout}{r.stderr}")

    def test_step_edge_snaps_to_bounds_and_nudges_without_them(self):
        """One honest trim step: with bounds, the next/previous segment
        start; past the poles or without bounds, the two-second nudge,
        clamped to the tape."""
        body = "\n".join([
            self.lift(r"  function stepEdge\(t, dir, segs, dur\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const segs = [10, 20, 30];",
            "const CASES = [",
            "  [15, '+', segs, 100, 20],",   # snap forward
            "  [20, '+', segs, 100, 30],",   # from a bound, the next one
            "  [15, '-', segs, 100, 10],",   # snap back
            "  [30, '+', segs, 100, 32],",   # past the last bound → nudge
            "  [10, '-', segs, 100, 8],",    # no bound before the first → nudge
            "  [5, '-', segs, 100, 3],",     # before first bound → nudge
            "  [15, '+', [], 100, 17],",     # no bounds → nudge
            "  [99.5, '+', [], 100, 100],",  # nudge clamps to the tape
            "  [1, '-', [], 100, 0],",       # nudge clamps to zero
            "];",
            "for (const [t, dir, s, dur, want] of CASES) {",
            "  const got = stepEdge(t, dir, s, dur);",
            "  if (got !== want) fail(`stepEdge(${t},${dir}) -> ${got}, want ${want}`);",
            "}",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"stepEdge drifted:\n{r.stdout}{r.stderr}")

    def test_a_segment_tick_cuts_the_rows_own_bounds(self):
        """The transcript tick's contract: the clip is the row's own segment
        — start at the row's time, end at the NEXT row's (the record's own
        unit), the words as the quote — and a second press removes it."""
        body = "\n".join([
            self.PRELUDE,
            "const r1 = t => Math.round(t * 10) / 10;",
            "const MIN_CLIP = 1.0;",
            "const cut = (s, n) => String(s).slice(0, n);",
            "const clipKey = c => (c.pid || '') + '@' + (c.kind || 'moment') + '@' + r1(c.t);",
            "let store = [];",
            "const readReel = () => JSON.parse(JSON.stringify(store));",
            "const REEL_KEY = 'cz-reel';",
            "let toasts = [];",
            "const toast = m => toasts.push(m);",
            "function writeTray(clips) { store = clips; CREEL.clips = clips; }",
            "const CREEL = { pid: 'vidX', segs: [0.9, 10.9, 20.9], clips: [],",
            "  meta: { duration: 300, video_id: 'vX', title: 'Select Board',",
            "          body: 'Board', town: 'Testville', date: '2026-03-10' } };",
            "const getJSON = async () => null;",
            "const row = { dataset: { t: '10.9' },",
            "  querySelector: () => ({ textContent: '  the override passes  ' }) };",
            "const btn = { dataset: { czcut: 'segment' }, closest: () => row };",
            self.lift(r"  const trayClips = .+?;"),
            self.lift(r"  const cutKey = .+?;"),
            self.lift(r"  async function toggleCut\(b\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "(async () => {",
            "await toggleCut(btn);",
            "if (store.length !== 1) fail('tick did not cut: ' + JSON.stringify(store));",
            "const c = store[0];",
            "if (c.start !== 10.9 || c.end !== 20.9) fail('bounds ' + c.start + '-' + c.end);",
            "if (c.kind !== 'segment') fail('kind ' + c.kind);",
            "if (c.quote !== 'the override passes') fail('quote ' + JSON.stringify(c.quote));",
            "if (c.pid !== 'vidX' || c.mtitle !== 'Select Board') fail('meta lost');",
            "await toggleCut(btn);",
            "if (store.length !== 0) fail('second press did not remove');",
            # the LAST row: no next bound → 12s window, capped by the tape
            "row.dataset.t = '20.9';",
            "await toggleCut(btn);",
            "if (store[0].end !== 32.9) fail('last-row end ' + store[0].end);",
            "console.log('ok');",
            "})();",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"the segment tick misbehaved:\n{r.stdout}{r.stderr}")

    def test_tray_trim_survives_a_reorder_that_landed_mid_fetch(self):
        """trayAct's trims await a bounds fetch, and the reel is RE-READ and
        the clip RE-FOUND by identity after the await — so a reorder (or a
        tick) that landed meanwhile is never overwritten, and the trim lands
        on the clip that was pressed, wherever it now sits."""
        body = "\n".join([
            "const r1 = t => Math.round(t * 10) / 10;",
            "const MIN_CLIP = 1.0;",
            "const clipKey = c => (c.pid || '') + '@' + (c.kind || 'moment') + '@' + r1(c.t);",
            "const REEL_KEY = 'cz-reel';",
            "const A = { pid: 'p1', kind: 'segment', t: 10, start: 10, end: 20 };",
            "const B = { pid: 'p1', kind: 'segment', t: 30, start: 30, end: 40 };",
            "let reads = 0;",
            # first read: [A, B]; during the await another tab reorders to [B, A]
            "const readReel = () => JSON.parse(JSON.stringify(++reads === 1 ? [A, B] : [B, A]));",
            "const segBounds = async () => [8, 10, 30];",
            "const SEGB_SAID = new Set();",
            "const CREEL = null;",
            "const toast = () => {};",
            "let wrote = null;",
            "function writeTray(clips) { wrote = clips; }",
            "function stepEdge(t, dir, segs, dur) {",
            "  if (segs && segs.length) {",
            "    if (dir === '+') { const nx = segs.find(s => s > t + 0.05);",
            "      return nx == null ? Math.min(dur, t + 2) : nx; }",
            "    const pv = segs.filter(s => s < t - 0.05).pop();",
            "    return pv == null ? Math.max(0, t - 2) : pv;",
            "  }",
            "  return dir === '+' ? Math.min(dur, t + 2) : Math.max(0, t - 2);",
            "}",
            self.lift(r"  const trayClips = .+?;"),
            self.lift(r"  async function trayAct\(i, act, origin\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "(async () => {",
            "  await trayAct(0, 's-');",   # pressed on A at index 0
            "  if (!wrote) fail('nothing written');",
            # after the await the list is [B, A]; A re-found at index 1
            "  if (wrote[0].start !== 30) fail('B was disturbed: ' + JSON.stringify(wrote[0]));",
            "  if (wrote[1].start !== 8) fail('A did not trim to the bound: ' + JSON.stringify(wrote[1]));",
            "  console.log('ok');",
            "})();",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"the mid-fetch race lost a change:\n{r.stdout}{r.stderr}")

    def test_make_this_yours_is_explicit_and_never_silent(self):
        """specs/22 §5.4, settled §6.3: an empty tray just receives the reel;
        a tray with clips is asked — append (clips already held, by
        identity, are not doubled) or replace (only past a confirm) or keep.
        takeMerge is the pure half; a refusal returns null and the tray is
        untouched."""
        body = "\n".join([
            "const r1 = t => Math.round(t * 10) / 10;",
            "const clipKey = c => (c.pid || '') + '@' + (c.kind || 'moment') + '@' + r1(c.t);",
            self.lift(r"  function takeMerge\(answer, have, clips, confirmed\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const A = { pid: 'p1', kind: 'moment', t: 10, start: 9, end: 20 };",
            "const B = { pid: 'p1', kind: 'moment', t: 30, start: 29, end: 40 };",
            "const C = { pid: 'p2', kind: 'segment', t: 5, start: 5, end: 12 };",
            "let out = takeMerge('append', [A], [A, B, C], false);",
            "if (out.map(clipKey).join('|') !== [A, B, C].map(clipKey).join('|')) fail('append doubled or dropped: ' + JSON.stringify(out));",
            "out = takeMerge('append', [B], [A, B], false);",
            "if (out.length !== 2 || out[0] !== B) fail('append must keep mine first: ' + JSON.stringify(out));",
            # the same CUT under a reconstructed identity (a taken reel's kind
            # and t come from the moments plane) is still already held
            "const A2 = { pid: 'p1', kind: 'tension', t: 12, start: 9, end: 20 };",
            "out = takeMerge('append', [A], [A2, C], false);",
            "if (out.length !== 2 || out[1] !== C) fail('the same cut was doubled: ' + JSON.stringify(out));",
            "if (takeMerge('replace', [A], [B, C], false) !== null) fail('replace without a confirm wrote');",
            "out = takeMerge('replace', [A], [B, C], true);",
            "if (!out || out.length !== 2 || out[0] !== B) fail('replace with a confirm: ' + JSON.stringify(out));",
            "if (takeMerge('keep', [A], [B], true) !== null) fail('keep wrote');",
            "if (takeMerge('nonsense', [A], [B], true) !== null) fail('an unknown answer wrote');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"make-this-yours misbehaved:\n{r.stdout}{r.stderr}")

    def test_the_preview_stage_keeps_its_laws(self):
        """specs/22 P2 / specs/23 B2: the stage is its own bounded machine.
        pvStep — its armed gate — is pure: arm only on a report inside the
        clip and before the end, stop once armed at the end, nothing while
        settling or ended or without a clip. And the laws are pinned by
        token: the page player hears only its own frame, the stage only its
        own; every page seek pauses the stage; the stage's start pauses the
        page; leaving the studio or collapsing the rail pauses it; the stage
        markup lives outside the repainted reel body."""
        body = "\n".join([
            self.lift(r"  function pvStep\(pv, t\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const clip = { start: 100, end: 110 };",
            "const S = (o) => Object.assign({ clip, armed: false, settling: false, ended: false }, o);",
            "if (pvStep(S({ clip: null }), 105) !== null) fail('no clip, no action');",
            "if (pvStep(S({}), 50) !== null) fail('far before the clip must not arm');",
            "if (pvStep(S({}), 99.5) !== 'arm') fail('inside the lead-in must arm');",
            "if (pvStep(S({}), 105) !== 'arm') fail('inside the clip must arm');",
            "if (pvStep(S({}), 109.95) !== null) fail('a stale report at the end must not arm');",
            "if (pvStep(S({}), 120) !== null) fail('past the end, unarmed, must not arm');",
            "if (pvStep(S({ armed: true }), 105) !== null) fail('armed and inside: keep playing');",
            "if (pvStep(S({ armed: true }), 109.9) !== 'stop') fail('armed at the end must stop');",
            "if (pvStep(S({ armed: true }), 200) !== 'stop') fail('armed and past must stop');",
            "if (pvStep(S({ settling: true }), 105) !== null) fail('settling ignores reports');",
            "if (pvStep(S({ armed: true, ended: true }), 200) !== null) fail('an ended clip stays stopped');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"the stage's gate misbehaved:\n{r.stdout}{r.stderr}")
        for token in ("if (e.source !== YT.win) return;",      # the page player's gate
                      "if (e.source !== PV.win) return;",      # the stage's gate
                      # the review's folds: a stop before the frame is ready
                      # silences its autoplay; the page player hushes on ready
                      # when the stage spoke during its load gap; a native play
                      # in either frame yields the other; the stage follows a
                      # trim; the mark is programmatic; a tape-less clip's ▶ is
                      # disabled; the stage opens the studio and the rail first
                      "PV.stopped = true", "if (PV.stopped || !PV.clip)",
                      "YT.hold = true;", "if (YT.hold) {",
                      "if (PV.clip || PV.free) pvPause();",
                      "function pvRetrim(clips)", 'b.setAttribute("aria-current", "true")',
                      '${c.video_id ? "" : " disabled"}',
                      'if (shownMode() !== "studio") { writeRail(false); setMode("studio"); }\n    else if (shownRail()) toggleRail();',
                      "REELPLAY.paused = true; reelShow();",
                      'PV.blocked ? "the tape hasn’t started',
                      "if (now && now.textContent !== line) now.textContent = line;",
                      "function pvPlay(clip)", "function pagePause()", "function pvPause()",
                      'if (m !== "studio") pvPause();',        # leaving the studio
                      "if (v) pvPause();",                     # collapsing the rail
                      'class="cz-block cz-stagebox" id="cz-stagebox" hidden',
                      'data-cz="pvplay"', 'data-cz="pvstop"',
                      'window.addEventListener("message", onPV, false)'):
            self.assertIn(token, self.JS, f"{token!r} drifted — a stage law is loose")
        # every page seek pauses the stage — the three doors into the page player
        for fn in ("function loadTape(vid, seekTo) {\n    pvPause();",
                   "function ytSeek(t) {\n    pvPause();",
                   "function startReel(clips) {\n    pvPause();"):
            self.assertIn(fn, self.JS, f"a page seek no longer pauses the stage: {fn[:30]!r}")
        # the stage's start pauses the page
        play = self.JS[self.JS.index("function pvPlay(clip)"):self.JS.index("function onPV(e)")]
        self.assertIn("pagePause();", play)
        # the stage markup is a sibling of the reel body, never inside it
        markup = self.JS[self.JS.index("function studioMarkup()"):self.JS.index("let STUDIO = null;")]
        self.assertLess(markup.index('class="cz-reelbody"'), markup.index('id="cz-stagebox"'))
        self.assertIn("</section>\n          <section class=\"cz-block cz-stagebox\"", markup)
        # the paper's ▶ paints only in the studio, in the paper palette
        css = (REPO / "web" / "static" / "app.web.css").read_text()
        self.assertIn(".pb-pv{display:none}", css)
        self.assertIn("html.cz-m-studio .pb-pv{display:inline-flex", css)
        pv = css[css.index("html.cz-m-studio .pb-pv{"):css.index("html.cz-m-studio .pb-pv:focus-visible")]
        self.assertNotIn("studio-accent", pv, "the paper's ▶ wears a studio hue")

    def test_one_engine_holds_through_load_gaps_and_the_frames_own_presses(self):
        """The B2 re-review fold. Both frames are HELD silent after the other
        engine speaks until they are seen silent (a paused or cued report); a
        play reported meanwhile with no reader's hand in the frame is an
        autoplay landing late and is paused again, and a play after that is
        the reader's own press. A stop before a frame is ready CUES its tape
        (a pause before playback is ignored by the player). The ready work
        runs once. The stage's status says what its frame is doing —
        previewing, paused on the frame, played, playing the tape outside
        any clip — and a trim never flips a played clip back to previewing.
        Node twins drive the real functions through each reviewed case."""
        stage = self.node("\n".join([
            "const FRAME = { f: 'stage' }, ELSE = { f: 'else' };",
            "const document = { activeElement: ELSE };",
            "let SENT = [], PAGEPAUSED = 0;",
            "const pvSend = (f, a) => SENT.push([f, a]); const sent = f => SENT.filter(x => x[0] === f);",
            "const pagePause = () => { PAGEPAUSED++; }; const pvPlay = () => {};",
            "const NOW = { textContent: '' }, OPEN = { href: '', hidden: false };",
            "const $ = s => s === '#cz-stagenow' ? NOW : s === '.cz-stageopen' ? OPEN : null;",
            "const $$ = () => []; const hms = t => String(t); const cut = (x, n) => String(x).slice(0, n);",
            "const clipKey = c => c.pid + '|' + c.kind + '|' + c.t; const BASE = '/app';",
            "const PV = {};",
            self.lift(r"  const inFrame = [^\n]+"),
            self.lift(r"  function pvStep\(pv, t\) \{.+?\n  \}"),
            self.lift(r"  function pvAdvance\(t\) \{.+?\n  \}"),
            self.lift(r"  function pvShow\(\) \{.+?\n  \}"),
            self.lift(r"  function onPV\(e\) \{.+?\n  \}"),
            self.lift(r"  function pvStarted\(\) \{.+?\n  \}"),
            self.lift(r"  function pvState\(s, t\) \{.+?\n  \}"),
            self.lift(r"  function pvPause\(\) \{.+?\n  \}"),
            self.lift(r"  function pvRetrim\(clips\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m, JSON.stringify(PV), JSON.stringify(SENT)); process.exit(1); }",
            "const A = { pid: 'p1', kind: 'cut', t: 100, start: 100, end: 110, video_id: 'v1' };",
            "function reset(o) { Object.assign(PV, { win: {}, el: FRAME, ready: true, clip: null, armed: false,",
            "  settling: false, ended: false, vid: 'v1', pending: null, wired: true, playing: false, paused: false,",
            "  free: false, stopped: false, blocked: false, hold: false, watch: 0, state: 2, t: 0, last: null }, o);",
            "  SENT = []; PAGEPAUSED = 0; NOW.textContent = ''; document.activeElement = ELSE; }",
            "const says = w => NOW.textContent.startsWith(w);",
            # a late autoplay after a stop, no hand in the frame: silenced, the page untouched
            "reset({ last: A, hold: true, state: 3 }); pvState(1, 101);",
            "if (!sent('pauseVideo').length || PAGEPAUSED || PV.clip || PV.free) fail('a late autoplay must be paused again, the page left alone');",
            # the reader's hand in the frame while held: the preview goes on, unarmed
            "reset({ last: A, hold: true, state: 3 }); document.activeElement = FRAME; pvState(1, 104);",
            "if (PV.clip !== A || PV.armed || !PV.playing || PAGEPAUSED !== 1 || sent('pauseVideo').length || !says('previewing')) fail('the hand in the frame resumes the preview, unarmed, and the page yields');",
            # seen silent, then a press: no hand needed; the next report inside arms
            "reset({ last: A }); pvState(1, 104); pvAdvance(104.5);",
            "if (PV.clip !== A || !PV.armed) fail('a press after the frame was seen silent resumes the clip; a report inside arms it');",
            # a press outside the clip: the tape plays, unbounded and said so
            "reset({ last: A }); pvState(1, 500);",
            "if (PV.clip || !PV.free || PAGEPAUSED !== 1 || !says('playing the tape')) fail('a press outside the clip is free play, said so, the page yielding');",
            "pvAdvance(500); if (sent('pauseVideo').length) fail('free play is not gated');",
            # free play through a buffer, focus elsewhere, crossing the old clip: stays free
            "reset({ last: A, free: true }); pvState(1, 104);",
            "if (sent('pauseVideo').length || !PV.free || PV.clip) fail('free play buffering must not be silenced or re-adopted');",
            # played, the reader's ▶ at the end: free play past the clip
            "reset({ clip: A, ended: true }); pvState(1, 109.95);",
            "if (PV.clip || !PV.free || PV.last !== A) fail('▶ after the gate stopped plays on past the clip, as free play');",
            # played but not yet seen paused: a stale play with no hand is paused again
            "reset({ clip: A, ended: true, hold: true, state: 1 }); pvState(1, 109.95);",
            "if (!sent('pauseVideo').length || PV.clip !== A || !PV.ended) fail('the gate\\'s stop holds until it is seen');",
            # played, scrubbed back in, ▶: the clip again, bounded
            "reset({ clip: A, ended: true }); pvState(1, 102);",
            "if (PV.clip !== A || PV.ended || PV.armed || !PV.playing) fail('▶ inside a played clip previews it again');",
            # the reader pauses mid-preview, then goes on
            "reset({ clip: A, playing: true, armed: true, state: 1 }); pvState(2, 105);",
            "if (!PV.paused || PV.playing || !says('paused on the frame')) fail('a pause on the frame is said as such');",
            "pvState(1, 105); if (PV.paused || !PV.playing || !says('previewing') || PAGEPAUSED !== 1) fail('the frame\\'s ▶ goes on');",
            # the tape's own end, and the gate's stop
            "reset({ clip: A, playing: true }); pvState(0, 110);",
            "if (!PV.ended || PV.playing || !says('played')) fail('the tape\\'s end ends the preview');",
            "reset({ clip: A, playing: true, armed: true }); pvAdvance(109.9);",
            "if (!sent('pauseVideo').length || !PV.ended || PV.playing || !PV.hold || !says('played')) fail('the gate stops, holds, and says played');",
            "reset({ clip: A, blocked: true }); pvShow(); if (!says('the tape hasn’t started')) fail('blocked is said');",
            # the dispatcher: ready once; a stop before ready CUES the last clip's tape
            "reset({ ready: false, stopped: true, last: A, state: -2 });",
            "const ev = d => ({ source: PV.win, origin: 'https://www.youtube-nocookie.com', data: JSON.stringify(d) });",
            "onPV(ev({ event: 'initialDelivery', info: { playerState: -1 } })); onPV(ev({ event: 'onReady' }));",
            "const cue = sent('cueVideoById');",
            "if (cue.length !== 1 || cue[0][1][0].videoId !== 'v1' || cue[0][1][0].startSeconds !== 100 || sent('listening').length !== 1) fail('the ready work runs once and cues the stopped clip');",
            "if (sent('pauseVideo').length || sent('playVideo').length) fail('a cue, not a pause or a play');",
            # a message from another frame is not the stage's
            "reset({ ready: false, clip: A, pending: A, state: -2 }); onPV({ source: {}, origin: 'https://www.youtube-nocookie.com', data: JSON.stringify({ event: 'onReady' }) });",
            "if (PV.ready || SENT.length) fail('the stage hears only its own frame');",
            # time moving under a playing state is the preview playing (a seek in a playing tape)
            "reset({ clip: A, state: 1 }); onPV(ev({ event: 'infoDelivery', info: { currentTime: 104 } }));",
            "if (!PV.playing || !PV.armed || !says('previewing')) fail('time moving under state 1 is playing');",
            # a paused or cued report releases the hold
            "reset({ hold: true, state: 1, last: A }); onPV(ev({ event: 'infoDelivery', info: { playerState: 2 } }));",
            "if (PV.hold) fail('seen paused releases the hold');",
            "reset({ hold: true, state: -1, last: A }); onPV(ev({ event: 'infoDelivery', info: { playerState: 5 } }));",
            "if (PV.hold) fail('seen cued releases the hold');",
            # a stop before ready cues the EXACT start (a clip at x.9): the
            # frame's own ▶ at the cue point re-adopts the clip, bounded
            "const A9 = { pid: 'p9', kind: 'cut', t: 100.9, start: 100.9, end: 110.9, video_id: 'v1' };",
            "reset({ ready: false, stopped: true, hold: true, last: A9, state: -2 }); onPV(ev({ event: 'onReady' }));",
            "const cue9 = sent('cueVideoById');",
            "if (cue9.length !== 1 || cue9[0][1][0].startSeconds !== 100.9) fail('the cue lands at the exact start');",
            "onPV(ev({ event: 'infoDelivery', info: { playerState: 5 } }));",
            "onPV(ev({ event: 'infoDelivery', info: { playerState: 1, currentTime: 100.95 } }));",
            "if (PV.clip !== A9 || PV.free || !PV.armed) fail('the frame\\'s ▶ at the cue point resumes the clip');",
            "onPV(ev({ event: 'infoDelivery', info: { currentTime: 110.85 } }));",
            "if (!PV.ended || !sent('pauseVideo').length) fail('…and the gate stops it at its end');",
            # a stop leaves its clip behind; a trim reaches it; the frame's ▶
            # resumes the TRIMMED clip and the gate stops at the new end
            "reset({ clip: A, playing: true, armed: true, state: 1 }); pvPause();",
            "if (PV.clip || PV.last !== A || !PV.hold) fail('a stop leaves its clip behind, held until seen silent');",
            "onPV(ev({ event: 'infoDelivery', info: { playerState: 2 } }));",
            "pvRetrim([Object.assign({}, A, { end: 106 })]);",
            "if (PV.last.end !== 106) fail('a trim reaches the clip a stop left behind');",
            "onPV(ev({ event: 'infoDelivery', info: { playerState: 1, currentTime: 104 } }));",
            "if (!PV.clip || PV.clip.end !== 106) fail('the frame\\'s ▶ resumes the trimmed clip');",
            "onPV(ev({ event: 'infoDelivery', info: { currentTime: 105.9 } }));",
            "if (!PV.ended) fail('the gate stops at the new end');",
            # a trim of a played clip keeps it played; nothing is sent
            "reset({ clip: A, ended: true }); pvRetrim([Object.assign({}, A, { end: 120 })]);",
            "if (!PV.ended || PV.clip.end !== 120 || SENT.length) fail('a trim of a played clip keeps it played');",
            "console.log('ok');",
        ]))
        self.assertEqual(stage.stdout.strip(), "ok", stage.stdout + stage.stderr)
        page = self.node("\n".join([
            "const WIN = {}, EL = { f: 'page' }, ELSE = { f: 'else' };",
            "const document = { activeElement: ELSE };",
            "let SENT = [], PVPAUSED = 0, SEEKS = [], SHOWN = 0;",
            "const ytSend = (k, f, a) => SENT.push(k === 'listening' ? ['listening'] : [f, a]);",
            "const sent = f => SENT.filter(x => x[0] === f);",
            "const ytSeek = t => SEEKS.push(t); const pvPause = () => { PVPAUSED++; };",
            "const reelShow = () => { SHOWN++; };",
            "const followAlong = () => {}, strip = () => {}, tick = () => {}, reelAdvance = () => {};",
            "const PV = { clip: null, free: false };",
            "let REELPLAY = null; let YT = {};",
            "let NEXT = 0, RSEEKS = []; const reelNext = () => { NEXT++; }; const reelSeek = c => { RSEEKS.push(c.start); };",
            self.lift(r"  const inFrame = [^\n]+"),
            self.lift(r"  function onYT\(e\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m, JSON.stringify(YT), JSON.stringify(SENT)); process.exit(1); }",
            "function reset(y, r) { YT = Object.assign({ win: WIN, el: EL, vid: 'v1', loaded: true, ready: false,",
            "  time: 0, pending: null, hold: false, state: -2 }, y); REELPLAY = r || null;",
            "  SENT = []; PVPAUSED = 0; SEEKS = []; SHOWN = 0; NEXT = 0; RSEEKS = []; document.activeElement = ELSE; PV.clip = null; PV.free = false; }",
            "const ev = d => ({ source: WIN, origin: 'https://www.youtube-nocookie.com', data: JSON.stringify(d) });",
            "const ready = () => { onYT(ev({ event: 'initialDelivery', info: { playerState: -1 } })); onYT(ev({ event: 'onReady' })); };",
            # held in the load gap: cued at the kept place, never played; ready runs once
            "reset({ hold: true, pending: 720 }); ready();",
            "const c1 = sent('cueVideoById');",
            "if (c1.length !== 1 || c1[0][1][0].videoId !== 'v1' || c1[0][1][0].startSeconds !== 720) fail('a held page is cued where it was asked to be');",
            "if (SEEKS.length || sent('playVideo').length || YT.pending !== null || sent('listening').length !== 1) fail('once, and no play');",
            # not held: the stashed seek plays, once
            "reset({ pending: 30 }); ready(); if (SEEKS.join() !== '30') fail('a stashed seek applies once: ' + SEEKS);",
            # a cross-meeting switch stashed with a same-tape seek: the switch loads, the seek is dropped
            "reset({ pending: 100 }, { pending: { vid: 'v2', start: 50 }, settling: false, paused: false, active: true }); ready();",
            "const l = sent('loadVideoById');",
            "if (l.length !== 1 || l[0][1][0].videoId !== 'v2' || SEEKS.length || YT.pending !== null || YT.vid !== 'v2') fail('the switch loads once; the abandoned tape\\'s seek is dropped');",
            # held with a stashed cross-meeting cite: that tape is cued, not loaded
            "reset({ hold: true, pending: 100 }, { pending: { vid: 'v2', start: 50 }, paused: true });  ready();",
            "const c2 = sent('cueVideoById');",
            "if (c2.length !== 1 || c2[0][1][0].videoId !== 'v2' || c2[0][1][0].startSeconds !== 50 || sent('loadVideoById').length || REELPLAY.pending || YT.vid !== 'v2') fail('a held page cues the stashed cite\\'s tape');",
            # a late autoplay while held, no hand: paused again, the stage untouched
            "reset({ ready: true, hold: true, state: 3 }); PV.clip = { x: 1 };",
            "onYT(ev({ event: 'infoDelivery', info: { playerState: 1 } }));",
            "if (sent('pauseVideo').length !== 1 || PVPAUSED || !YT.hold) fail('a late autoplay of a held page is paused again');",
            # seen paused: the hold goes; then the reader's own press makes the page the engine
            "onYT(ev({ event: 'infoDelivery', info: { playerState: 2 } })); if (YT.hold) fail('seen paused releases the hold');",
            "REELPLAY = { paused: true, active: false, armed: true }; SENT = [];",
            "onYT(ev({ event: 'infoDelivery', info: { playerState: 1 } }));",
            "if (sent('pauseVideo').length || PVPAUSED !== 1) fail('the reader\\'s press on the page: the stage yields');",
            "if (REELPLAY.paused || !REELPLAY.active || REELPLAY.armed || SHOWN !== 1) fail('a reel the stage paused goes on from its clip');",
            # held, but the hand is in the page frame: the reader's press, at once
            "reset({ ready: true, hold: true, state: 3 }); PV.clip = { x: 1 }; document.activeElement = EL;",
            "onYT(ev({ event: 'infoDelivery', info: { playerState: 1 } }));",
            "if (sent('pauseVideo').length || YT.hold || PVPAUSED !== 1) fail('the hand in the page frame is the reader\\'s press');",
            # the page frame's ▶ resumes a paused reel from where it stands:
            # at the clip's end (the gate never saw it) → on to the next clip;
            # before the clip → to its start; inside → where it stands
            "const R = () => ({ paused: true, active: false, armed: true, i: 0, clips: [{ start: 10, end: 20 }, { start: 40, end: 50 }] });",
            "reset({ ready: true, state: 2 }, R()); onYT(ev({ event: 'infoDelivery', info: { playerState: 1, currentTime: 19.95 } }));",
            "if (NEXT !== 1 || REELPLAY.paused || !REELPLAY.active || RSEEKS.length) fail('a resume at the clip\\'s end advances the reel');",
            "reset({ ready: true, state: 2 }, R()); onYT(ev({ event: 'infoDelivery', info: { playerState: 1, currentTime: 3 } }));",
            "if (NEXT || RSEEKS.join() !== '10' || SHOWN !== 1) fail('a resume before the clip seeks its start');",
            "reset({ ready: true, state: 2 }, R()); onYT(ev({ event: 'infoDelivery', info: { playerState: 1, currentTime: 15 } }));",
            "if (NEXT || RSEEKS.length || SHOWN !== 1 || REELPLAY.armed) fail('a resume inside the clip goes on from where it stands, unarmed');",
            # another frame's message is not the page player's
            "reset({}); onYT({ source: {}, origin: 'https://www.youtube-nocookie.com', data: JSON.stringify({ event: 'onReady' }) });",
            "if (YT.ready || SENT.length) fail('the page hears only its own frame');",
            "console.log('ok');",
        ]))
        self.assertEqual(page.stdout.strip(), "ok", page.stdout + page.stderr)
        # two cites of ANOTHER meeting pressed in the page's load gap: the
        # second moves the stashed switch's start — the reader's last press
        # is the one that loads (or, held, the one that is cued)
        cites = self.node("\n".join([
            "const WIN = {}, EL = {};",
            "const document = { activeElement: {} };",
            "let SENT = [], SEEKS = [];",
            "const ytSend = (k, f, a) => SENT.push(k === 'listening' ? ['listening'] : [f, a]);",
            "const sent = f => SENT.filter(x => x[0] === f);",
            "const ytSeek = t => SEEKS.push(t); const pvPause = () => {}; const reelShow = () => {};",
            "const followAlong = () => {}, strip = () => {}, tick = () => {}, reelAdvance = () => {}, reelNext = () => {};",
            "const PV = { clip: null, free: false };",
            "let REELPLAY, YT;",
            self.lift(r"  const inFrame = [^\n]+"),
            self.lift(r"  function reelSeek\(c\) \{.+?\n  \}"),
            self.lift(r"  function onYT\(e\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m, JSON.stringify({ SENT, SEEKS, YT, REELPLAY })); process.exit(1); }",
            "const ev = d => ({ source: WIN, origin: 'https://www.youtube-nocookie.com', data: JSON.stringify(d) });",
            "function run(held) {",
            "  YT = { win: WIN, el: EL, vid: 'v1', loaded: true, ready: false, time: 0, pending: 10, hold: false, state: -2 };",
            "  REELPLAY = { vid: 'v1', pending: null, clips: [] }; SENT = []; SEEKS = [];",
            "  reelSeek({ video_id: 'v2', start: 300 });",
            "  reelSeek({ video_id: 'v2', start: 100 });",
            "  if (held) YT.hold = true;",
            "  onYT(ev({ event: 'initialDelivery', info: { playerState: -1 } })); onYT(ev({ event: 'onReady' }));",
            "}",
            "run(false); const l = sent('loadVideoById');",
            "if (SEEKS.length || l.length !== 1 || l[0][1][0].videoId !== 'v2' || l[0][1][0].startSeconds !== 100) fail('the last press loads, once');",
            "run(true); const c = sent('cueVideoById');",
            "if (c.length !== 1 || c[0][1][0].videoId !== 'v2' || c[0][1][0].startSeconds !== 100 || sent('loadVideoById').length || SEEKS.length) fail('held: the last press is cued');",
            "console.log('ok');",
        ]))
        self.assertEqual(cites.stdout.strip(), "ok", cites.stdout + cites.stderr)
        # the holds are SET by the real stops: the real pagePause and pvPause,
        # the real dispatchers, and only the two frames' postMessage stubbed
        both = self.node("\n".join([
            "const STAGE = { f: 'stage' }, PAGE = { f: 'page' }, ELSE = { f: 'else' };",
            "const document = { activeElement: ELSE };",
            "const SW = {}, PW = {};",
            "let SENT = [];",
            "const pvSend = (f, a) => SENT.push(['stage', f, a]);",
            "const ytSend = (k, f, a) => SENT.push(['page', k === 'listening' ? 'listening' : f, a]);",
            "const sent = (fr, f) => SENT.filter(x => x[0] === fr && x[1] === f);",
            "const NOW = { textContent: '' }; const $ = s => s === '#cz-stagenow' ? NOW : null; const $$ = () => [];",
            "const hms = t => String(t); const cut = (x, n) => String(x).slice(0, n); const clipKey = c => c.pid + '|' + c.t; const BASE = '/app';",
            "let REELPLAY = null; const reelShow = () => {}; const reelNext = () => {}; const reelSeek = () => {};",
            "const followAlong = () => {}, strip = () => {}, tick = () => {}, reelAdvance = () => {};",
            self.lift(r"  const inFrame = [^\n]+"),
            self.lift(r"  const PV = \{.+?\};"),
            self.lift(r"  let YT = \{.+?\};"),
            self.lift(r"  function pagePause\(\) \{.+?\n  \}"),
            self.lift(r"  function pvPause\(\) \{.+?\n  \}"),
            self.lift(r"  function pvShow\(\) \{.+?\n  \}"),
            self.lift(r"  function onPV\(e\) \{.+?\n  \}"),
            self.lift(r"  function pvStarted\(\) \{.+?\n  \}"),
            self.lift(r"  function pvState\(s, t\) \{.+?\n  \}"),
            self.lift(r"  function pvStep\(pv, t\) \{.+?\n  \}"),
            self.lift(r"  function pvAdvance\(t\) \{.+?\n  \}"),
            self.lift(r"  function ytSeek\(t\) \{.+?\n  \}"),
            self.lift(r"  function onYT\(e\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m, JSON.stringify(SENT)); process.exit(1); }",
            "const A = { pid: 'p1', kind: 'cut', t: 100, start: 100, end: 110, video_id: 'v1' };",
            "const pe = d => ({ source: PW, origin: 'https://www.youtube-nocookie.com', data: JSON.stringify(d) });",
            "const se = d => ({ source: SW, origin: 'https://www.youtube-nocookie.com', data: JSON.stringify(d) });",
            # 1. the page loading (a #t720 stashed), the stage speaks: the page is
            #    held, and its ready CUES it at 720 — no seek, no play, and the
            #    preview the reader started survives
            "Object.assign(YT, { win: PW, el: PAGE, vid: 'v1', loaded: true, ready: false, pending: 720 });",
            "pagePause();",
            "if (!YT.hold) fail('a page still loading is held when the stage speaks');",
            "Object.assign(PV, { win: SW, el: STAGE, ready: true, clip: A, state: 3 });",
            "onYT(pe({ event: 'initialDelivery', info: { playerState: 3 } })); onYT(pe({ event: 'onReady' }));",
            "const cue = sent('page', 'cueVideoById');",
            "if (cue.length !== 1 || cue[0][2][0].startSeconds !== 720 || sent('page', 'seekTo').length || sent('page', 'playVideo').length) fail('the held page is cued, never played');",
            "if (PV.clip !== A) fail('the preview survives the page\\'s ready');",
            "onYT(pe({ event: 'infoDelivery', info: { playerState: 1 } }));",
            "if (sent('page', 'pauseVideo').length !== 1 || PV.clip !== A) fail('a late page autoplay while held is paused again, the stage untouched');",
            # 2. the stage ready but not yet playing; the reader seeks the page:
            #    the real pvPause holds the stage, and its late play is silenced
            #    without pausing the page the reader chose
            "SENT = []; Object.assign(YT, { ready: true, hold: false, state: 2 }); Object.assign(PV, { clip: A, state: 3, hold: false, ready: true });",
            "ytSeek(300);",
            "if (!PV.hold || PV.clip) fail('a page seek stops the stage and holds it');",
            "onPV(se({ event: 'infoDelivery', info: { playerState: 1, currentTime: 101 } }));",
            "if (sent('stage', 'pauseVideo').length !== 2) fail('the stage\\'s late play is paused again');",
            "if (sent('page', 'pauseVideo').length) fail('the stage\\'s late play must not pause the page the reader chose');",
            "console.log('ok');",
        ]))
        self.assertEqual(both.stdout.strip(), "ok", both.stdout + both.stderr)
        for token in ("const inFrame = el => !!el && document.activeElement === el;",
                      "if (!PV.free && PV.hold && !inFrame(PV.el)) { pvSend(\"pauseVideo\"); return; }",
                      "if (YT.hold && !inFrame(YT.el)) ytSend(\"cmd\", \"pauseVideo\", []);",
                      "if ((d.event === \"onReady\" || d.event === \"initialDelivery\") && !YT.ready) {",
                      "if ((d.event === \"onReady\" || d.event === \"initialDelivery\") && !PV.ready) {",
                      "PV.blocked = false; PV.paused = false; PV.free = false; PV.hold = false;",
                      "clearTimeout(PV.watch); PV.blocked = false;",
                      "if (typeof YT !== \"undefined\") YT.hold = false;",
                      "YT.el = ifr; YT.vid = vid; YT.hold = false;",
                      "? $(`.cz-rclip[data-i=\"${focus.i}\"] .cz-rprev`, body)",
                      "if (!t || t.disabled) t = $(\".cz-reelacts .btn\", body);",
                      "if (ae.classList.contains(\"pb-pv\")) return { act: \"pbpv\", key: ae.dataset.pvkey };",
                      'ifr.className = "cz-stagefr"; PV.el = ifr;'):
            self.assertTrue(token in self.JS, f"{token!r} drifted — the B2 re-review fold was reverted")
        retrim = self.JS[self.JS.index("function pvRetrim(clips)"):self.JS.index("function pvPlay(clip)")]
        self.assertNotIn("PV.ended = false", retrim, "a trim must never flip a played clip back to previewing")
        css = (REPO / "web" / "static" / "app.web.css").read_text()
        for rule in (".cz-rplay.on:focus-visible{outline:var(--border-w-strong) solid var(--focus-ring, var(--state))",
                     "html.cz-m-studio .pb-pv.on{outline:var(--border-w) solid var(--accent)"):
            self.assertIn(rule, css)
        # the focus ring outranks each mark: it comes later at equal specificity
        self.assertLess(css.index(".cz-rplay.on{"), css.index(".cz-rplay.on:focus-visible{"))
        self.assertLess(css.index("html.cz-m-studio .pb-pv.on{outline"), css.index("html.cz-m-studio .pb-pv:focus-visible{"))

    def test_the_cutting_markers_are_present(self):
        """The drift guard: the pieces the stylesheet, the hydrators and the
        panel lean on keep their names — and the preview stays a NEW-TAB
        deep link (the settled §6.1 answer; the /app/r singleton untouched)."""
        for token in ("function toggleCut(", "function paintCutTicks(",
                      "function wireSegTicks(", "function wireBeadTicks(",
                      "function trayAct(", "function writeTray(",
                      "function segBounds(", "function parseSegTimes(",
                      'b.dataset.czcut = "segment"', 'data-czcut="hit"',
                      'b.dataset.czcut = "bead"', 'data-cz="rtact"',
                      'target="_blank" rel="noopener"',
                      # P1 — the remix loop: make this yours on /app/r, and
                      # the tray's outputs offered from the panel
                      'data-rv="mine"', "function takeReel(", "function takeMerge(",
                      'data-cz="reelcite"', 'data-cz="reeljson"',
                      "const trayMeta = reelMeta",
                      # a transcript tick is a press, never a seek (a pane catch)
                      'if (e.target.closest("[data-czcut]")) return;'):
            self.assertIn(token, self.JS, f"{token!r} drifted in app.js")
        # the panel's reel block offers file-into-paper right where the tray is
        panel = self.JS[self.JS.index("function refreshReelSummary("):
                        self.JS.index("function clearReel(")]
        self.assertIn('data-cz="preel"', panel, "the tray does not offer file-into-paper")
        css = (REPO / "web" / "static" / "app.web.css").read_text()
        for token in (".seg-tick", ".stick", ".btick", ".cz-rclip",
                      ".cz-rprev"):
            self.assertIn(token, css, f"{token!r} missing from the sheet")


class TestPaper(unittest.TestCase):
    """specs/21 P1: the curated paper's client machinery, executed in node.
    A paper's link and its paper.json are covenants with whoever receives
    them — the codec must round-trip exactly, and a link that lost a
    character in an email must degrade to fewer blocks, never a throw
    (decodeReel's law, inherited by every decoder)."""

    JS = (REPO / "web" / "static" / "app.js").read_text()
    PRELUDE = "\n".join([
        'const BASE = "/app";',
        'const location = { origin: "https://publicrecord.studio" };',
    ])

    def node(self, body):
        import shutil
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
            self.lift(r"const REEL_VS = .+?;"),
            self.lift(r"const r1 = .+?;"),
            self.lift(r"const clipLen = .+?;"),
            self.lift(r"const reelRuntime = .+?;"),
            self.lift(r"const encodeClips = .+?;"),
            self.lift(r"const encodeClipsX = .+?;"),
            self.lift(r"function shareURL\(pid, clips\) \{.+?\n  \}"),
            self.lift(r"function reelShareURL\(clips\) \{.+?\n  \}"),
            self.lift(r"const reelPids = .+?;"),
            self.lift(r"const PAPER_V = .+?;"),
            self.lift(r"const PAPER_VS = .+?;"),
            self.lift(r"const PAPER_TITLE_MAX = .+?;"),
            self.lift(r"const PAPER_MAX_BLOCKS = .+?;"),
            self.lift(r"const PAPER_MAX_CLIPS = .+?;"),
            self.lift(r"const PAPER_REF = .+?;"),
            self.lift(r"const PAPER_NOTE_MAX = .+?;"),
            self.lift(r"const PAPER_CHARTS = .+?;"),
            self.lift(r"const paperV = .+?;"),
            self.lift(r"const paperHasLive = .+?;"),
            self.lift(r"const cut = .+?;"),
            self.lift(r"const noteText = .+?;"),
            self.lift(r"const PAPER_LAYOUTS = .+?;"),
            self.lift(r"const LAYOUT_LABEL = .+?;"),
            self.lift(r"const C2_KINDS = .+?;"),
            self.lift(r"const DOC_REF = .+?;"),
            self.lift(r"const DIGEST_MAX = .+?;"),
            self.lift(r"const withLayout = .+?;"),
            self.lift(r"function chartRecordURL\(b\) \{.+?\n  \}"),
            self.lift(r"function normalizePaper\(p\) \{.+?\n  \}"),
            self.lift(r"function normalizeBlock\(b\) \{.+?\n  \}"),
            self.lift(r"function normalizeKind\(b\) \{.+?\n  \}"),
            self.lift(r"function decodePart\(kind, rest, out\) \{.+?\n  \}"),
            self.lift(r"function portablePaper\(p\) \{.+?\n  \}"),
            self.lift(r"function encodePaperQS\(p\) \{.+?\n  \}"),
            self.lift(r"function paperShareURL\(p\) \{.+?\n  \}"),
            self.lift(r"function decodePaper\(search\) \{.+?\n  \}"),
            self.lift(r"function paperJSON\(p\) \{.+?\n  \}"),
        ])

    DRAFT = ('{ title: "Overrides, watched", blocks: ['
             '{kind:"story",story:"meeting",pid:"vid1",title:"Select Board",'
             'date:"2026-03-10",town:"Testville"},'
             '{kind:"story",story:"issue",slug:"budget-override",'
             'name:"budget override",n_meetings:2},'
             '{kind:"reel",clips:[{pid:"vid1",start:900.2,end:907.3,'
             'kind:"vote",quote:"the override passes"},'
             '{pid:"vid2",start:12,end:24}]}]}')

    def test_the_link_round_trips_the_whole_paper(self):
        """portable(decode(encode(p))) === portable(p): the link carries the
        paper exactly — title and all three block kinds — and carries no
        ride-along meta (a paper may not assert what the record's planes
        would not)."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            f"const draft = {self.DRAFT};",
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const url = paperShareURL(draft);",
            "if (url.indexOf('https://publicrecord.studio/app/p?') !== 0) fail('url '+url);",
            "if (url.includes('+') || url.includes(' ')) fail('unsafe chars in '+url);",
            "if (url.includes('Select')) fail('ride-along meta leaked into the link');",
            "const back = decodePaper(url.slice(url.indexOf('?')));",
            "if (back.v !== '1') fail('v='+back.v);",
            "if (back.id !== '') fail('id='+back.id);",
            "if (back.title !== 'Overrides, watched') fail('title='+back.title);",
            "const a = JSON.stringify(portablePaper(draft));",
            "const b = JSON.stringify(portablePaper({title: back.title, blocks: back.blocks}));",
            "if (a !== b) fail('round-trip drifted:\\n'+a+'\\n'+b);",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"paper round-trip failed:\n{r.stdout}{r.stderr}")

    def test_a_mangled_link_degrades_and_never_throws(self):
        """Hostile queries → fewer blocks, never an exception. The exact table
        a forwarding email client would write."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const CASES = [",
            "  ['?v=1&b=,,,,', 0],",
            "  ['?v=1&b=m.', 0],",
            "  ['?v=1&b=x.abc', 0],",
            "  ['?v=1&b=m.has%20space', 0],",
            "  ['?v=1&b=m.%E0%A4%A', 0],",          # bad URI escape → dropped
            "  ['?v=1&b=r.', 0],",
            "  ['?v=1&b=r.vid1:5-3', 0],",           # end <= start
            "  ['?v=1&b=r.vid1:9-x', 0],",
            "  ['?v=1&b=r.vid1:-2-4', 0],",          # negative start
            "  ['?v=1&b=m.vid1,garbage,i.slug-ok,r.vid1:1-2~junk', 3],",
            "  ['', 0],",
            "  [null, 0],",
            "];",
            "for (const [q, want] of CASES) {",
            "  let got;",
            "  try { got = decodePaper(q).blocks.length; }",
            "  catch (e) { fail('THREW on '+JSON.stringify(q)+': '+e); }",
            "  if (got !== want) fail(JSON.stringify(q)+' -> '+got+' blocks, want '+want);",
            "}",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"decodePaper is fragile:\n{r.stdout}{r.stderr}")

    def test_normalize_is_total_and_caps_hold(self):
        """Whatever localStorage or a stored paper hands over leaves as a
        valid paper: junk drops, the title truncates at its cap, block and
        clip counts clamp."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "for (const junk of [null, 7, 'hi', [], {title: 9},",
            "     {blocks: 'no'}, {title: null, blocks: [null, 3, {}, {kind:'x'}]}]) {",
            "  const p = normalizePaper(junk);",
            "  if (p.title !== '' || p.blocks.length !== 0)",
            "    fail('junk survived: '+JSON.stringify(junk)+' -> '+JSON.stringify(p));",
            "}",
            "const long = normalizePaper({title: 'x'.repeat(999), blocks: []});",
            "if (long.title.length !== PAPER_TITLE_MAX) fail('title cap '+long.title.length);",
            "const many = normalizePaper({blocks: Array.from({length: 99},",
            "  (_, i) => ({kind:'story',story:'meeting',pid:'m'+i}))});",
            "if (many.blocks.length !== PAPER_MAX_BLOCKS) fail('block cap '+many.blocks.length);",
            "const fat = normalizeBlock({kind:'reel', clips: Array.from({length: 999},",
            "  (_, i) => ({pid:'vid1', start:i, end:i+1}))});",
            "if (fat.clips.length !== PAPER_MAX_CLIPS) fail('clip cap '+fat.clips.length);",
            "const meta = normalizeBlock({kind:'story',story:'meeting',pid:'vid1',",
            "  title:'kept', evil:'<script>'});",
            "if (meta.title !== 'kept') fail('ride-along meta lost');",
            "if ('evil' in meta) fail('unknown keys must not survive normalize');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"normalizePaper is leaky:\n{r.stdout}{r.stderr}")

    def test_a_store_address_decodes_as_an_id_and_nothing_else(self):
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const good = decodePaper('?p=0123456789abcdef');",
            "if (good.id !== '0123456789abcdef') fail('id lost: '+good.id);",
            "if (good.blocks.length) fail('an id link carries no blocks');",
            "for (const bad of ['?p=xyz', '?p=0123456789ABCDEF', '?p=0123',",
            "     '?p=0123456789abcdef0']) {",
            "  if (decodePaper(bad).id !== '') fail('accepted '+bad);",
            "}",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"store-id decode wrong:\n{r.stdout}{r.stderr}")

    def test_real_length_refs_survive_the_link(self):
        """The bake mints pids to 80 chars and issue slugs to 96 — the link
        codec must carry what the record actually names (the 64-char cap a
        review lens caught would have dropped real adds with a success
        toast)."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const pid80 = 'p'.repeat(80), slug96 = 's'.repeat(96);",
            "const draft = { title: '', blocks: [",
            "  {kind:'story',story:'meeting',pid:pid80},",
            "  {kind:'story',story:'issue',slug:slug96},",
            "  {kind:'reel',clips:[{pid:pid80,start:1,end:2}]}]};",
            "const port = portablePaper(draft);",
            "if (port.blocks.length !== 3) fail('normalize dropped a real ref: '+JSON.stringify(port.blocks));",
            "const url = paperShareURL(draft);",
            "const back = decodePaper(url.slice(url.indexOf('?')));",
            "if (JSON.stringify(portablePaper({title:'',blocks:back.blocks})) !== JSON.stringify(port))",
            "  fail('long refs did not round-trip');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"long refs dropped:\n{r.stdout}{r.stderr}")

    def test_paper_json_is_the_receipt_the_desk_can_trust(self):
        """schema pinned, the share link included, every story with its record
        URL, every reel with its play link (v1 for one meeting — byte-shaped
        like every reel link already in the wild)."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            f"const draft = {self.DRAFT};",
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const j = paperJSON(draft);",
            "if (j.schema !== 'publicrecord.paper/1') fail('schema '+j.schema);",
            "if (j.share !== paperShareURL(draft)) fail('share drifted');",
            "if (j.blocks.length !== 3) fail('blocks '+j.blocks.length);",
            "if (j.blocks[0].url !== 'https://publicrecord.studio/app/m/vid1') fail('story url '+j.blocks[0].url);",
            "if (j.blocks[1].url !== 'https://publicrecord.studio/app/i/budget-override') fail('issue url');",
            "const play = j.blocks[2].play;",
            "if (!play.includes('/app/r?v=2&c=vid1')) fail('cross-meeting reel must be v2: '+play);",
            "const one = paperJSON({title:'', blocks:[{kind:'reel',",
            "  clips:[{pid:'vid1',start:1,end:2},{pid:'vid1',start:5,end:9}]}]});",
            "if (!one.blocks[0].play.includes('/app/r?v=1&m=vid1')) fail('one-meeting reel must stay v1: '+one.blocks[0].play);",
            "if (one.blocks[0].runtime !== 5) fail('runtime '+one.blocks[0].runtime);",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"paperJSON malformed:\n{r.stdout}{r.stderr}")

    P2_DRAFT = ('{ title: "P2, watched", blocks: ['
                '{kind:"chart",chart:"votes"},'
                '{kind:"chart",chart:"framing"},'
                '{kind:"chart",chart:"framing",pid:"vid1",title:"Select Board"},'
                '{kind:"chart",chart:"reach",slug:"budget-override",name:"budget override"},'
                '{kind:"chart",chart:"topics"},'
                '{kind:"note",text:"Watch the tally, not the speeches. '
                '100% real — plus+comma, dots. ¿unicode?\\nSecond line."}]}')

    def test_p2_blocks_round_trip_the_link(self):
        """Charts and notes travel in the link like every other block — the
        note twice-encoded so its own commas and percents survive
        URLSearchParams's early decode, and no ride-along label leaks."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            f"const draft = {self.P2_DRAFT};",
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const url = paperShareURL(draft);",
            "if (url.includes('Select') || url.includes('budget%20override'))",
            "  fail('ride-along meta leaked into the link: '+url);",
            "const back = decodePaper(url.slice(url.indexOf('?')));",
            "if (back.blocks.length !== 6) fail('blocks '+back.blocks.length);",
            "const a = JSON.stringify(portablePaper(draft));",
            "const b = JSON.stringify(portablePaper({title: back.title, blocks: back.blocks}));",
            "if (a !== b) fail('round-trip drifted:\\n'+a+'\\n'+b);",
            "const note = back.blocks[5];",
            "if (note.kind !== 'note') fail('note lost');",
            "if (!note.text.includes('plus+comma,')) fail('note text mangled: '+note.text);",
            "if (!note.text.includes('100%')) fail('percent mangled: '+note.text);",
            "if (!note.text.includes('¿unicode?')) fail('unicode mangled');",
            "if (!note.text.includes('\\nSecond line')) fail('newline lost');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"P2 round-trip failed:\n{r.stdout}{r.stderr}")

    def test_mangled_p2_links_degrade_and_never_throw(self):
        """decodeReel's law, extended to charts and notes: a lost character
        reads as fewer blocks, never a crash — and a chart shape the record
        never writes (a bare reach, a reffed votes) is a mangle, dropped."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const CASES = [",
            "  ['?v=1&b=n.', 0],",
            "  ['?v=1&b=n.%2520', 0],",           # a lone space — trims away
            "  ['?v=1&b=n.%E0%A4%A', 0],",        # bad escape at the 2nd decode
            "  ['?v=1&b=c.', 0],",
            "  ['?v=1&b=c.sparkline', 0],",
            "  ['?v=1&b=c.reach', 0],",           # reach needs its issue
            "  ['?v=1&b=c.votes.vid1', 1],",      # one meeting's roll calls (specs/24)
            "  ['?v=1&b=c.numbers', 0],",         # numbers needs its ref
            "  ['?v=1&b=c.numbers.vid1', 0],",    # …and the ref says m: or i:
            "  ['?v=1&b=c.shape', 0],",
            "  ['?v=1&b=a.vid1', 0],",            # a reading's ref says m: or i:
            "  ['?v=1&b=a.m%3Avid1', 1],",
            "  ['?v=1&b=c.topics.vid1', 0],",
            "  ['?v=1&b=c.framing.', 0],",        # an empty ref is a mangle
            "  ['?v=1&b=c.framing.has%2520space', 0],",
            "  ['?v=1&b=c.votes,n.hi,garbage', 2],",
            "];",
            "for (const [q, want] of CASES) {",
            "  let got;",
            "  try { got = decodePaper(q).blocks.length; }",
            "  catch (e) { fail('THREW on '+JSON.stringify(q)+': '+e); }",
            "  if (got !== want) fail(JSON.stringify(q)+' -> '+got+' blocks, want '+want);",
            "}",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"P2 decodePaper is fragile:\n{r.stdout}{r.stderr}")

    def test_note_normalize_is_total_and_the_empty_note_is_draft_only(self):
        """The client cleans (total); the store refuses (strict) — and the
        one place an empty note may live is the draft being typed into:
        portablePaper and paperJSON carry none."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const long = normalizeBlock({kind:'note', text: 'a'.repeat(9999)});",
            "if (long.text.length !== PAPER_NOTE_MAX) fail('cap '+long.text.length);",
            "const ctl = normalizeBlock({kind:'note', text: 'a\\u0000b\\rc\\td'});",
            "if (ctl.text !== 'ab\\ncd') fail('control clean: '+JSON.stringify(ctl.text));",
            "if (normalizeBlock({kind:'note', text: 7}) !== null) fail('non-string note');",
            "const empty = normalizeBlock({kind:'note', text: ''});",
            "if (!empty || empty.text !== '') fail('the draft must keep an empty note');",
            "const p = {title:'', blocks:[{kind:'note',text:'  '},{kind:'note',text:'kept'}]};",
            "if (portablePaper(p).blocks.length !== 1) fail('portable must drop empty notes');",
            "if (paperJSON(p).blocks.length !== 1) fail('paperJSON must drop empty notes');",
            "if (normalizeBlock({kind:'chart', chart:'sparkline'}) !== null) fail('junk chart');",
            "if (normalizeBlock({kind:'chart', chart:'reach'}) !== null) fail('bare reach');",
            "if (normalizeBlock({kind:'chart', chart:'framing', pid:'has space'}) !== null) fail('bad pid');",
            "const stray = normalizeBlock({kind:'chart', chart:'votes', slug:'x'});",
            "if (JSON.stringify(stray) !== '{\"kind\":\"chart\",\"chart\":\"votes\"}')",
            "  fail('stray ref survived: '+JSON.stringify(stray));",
            "const keep = normalizeBlock({kind:'chart', chart:'reach', slug:'ok', name:'N', junk:1});",
            "if (keep.junk !== undefined || keep.name !== 'N') fail('ride-along wrong');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"P2 normalize leaky:\n{r.stdout}{r.stderr}")

    def test_p2_papers_travel_as_v2_and_p1_papers_stay_byte_stable(self):
        """A paper carrying kinds the shipped v1 reader cannot represent
        (notes, charts) must not travel under v=1 — the old reader would
        silently render a mutilated paper instead of its honest
        newer-version message (a review catch). And a stories+reels paper
        must keep encoding EXACTLY as P1 did, byte for byte — every P1 link
        and address in the wild depends on it."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            f"const p1 = {self.DRAFT};",
            f"const p2 = {self.P2_DRAFT};",
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const q1 = encodePaperQS(p1);",
            "if (!q1.startsWith('v=1&')) fail('P1 paper drifted off v=1: '+q1.slice(0,20));",
            "const expect = 'v=1&t=Overrides%2C%20watched'",
            "  + '&b=m.vid1,i.budget-override,r.vid1:900.2-907.3~vid2:12-24';",
            "if (q1 !== expect) fail('P1 bytes drifted:\\n'+q1+'\\n'+expect);",
            "const q2 = encodePaperQS(p2);",
            "if (!q2.startsWith('v=2&')) fail('P2 paper must travel as v=2: '+q2.slice(0,20));",
            "if (!PAPER_VS.includes('2')) fail('the new reader must accept v=2');",
            "const back = decodePaper('?' + q2);",
            "if (back.v !== '2' || back.blocks.length !== 6) fail('v=2 decode broke');",
            "// an empty-note-only draft has nothing traveling — it stays v=1",
            "if (paperV(portablePaper({title:'', blocks:[{kind:'note',text:'  '}]})) !== '1')",
            "  fail('an empty note must not force v=2');",
            "// and the one live-truth the share row + both typing handlers read:",
            "// an empty note is not live, a typed one is, a title alone is",
            "if (paperHasLive({title:'', blocks:[{kind:'note',text:' \\n '}]})) fail('empty note read as live');",
            "if (!paperHasLive({title:'', blocks:[{kind:'note',text:'watch the tally'}]})) fail('a real note must be live');",
            "if (!paperHasLive({title:'t', blocks:[]})) fail('a title alone is live');",
            "if (!paperHasLive({title:'', blocks:[{kind:'chart',chart:'votes'}]})) fail('a chart is live');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"version gate broken:\n{r.stdout}{r.stderr}")

    def test_chart_votes_never_draws_an_outcome_the_record_does_not_hold(self):
        """The record mints more than passes/fails (tabled, tied; desk
        imports carry their own words). A binarized chart drew a tabled
        motion as a FAILED one (a review catch): now passes = filled dot,
        fails = hollow dot, anything else = the half-tone square, with the
        exact word in the tooltip and the legend naming the third class only
        when it appears."""
        extra = "\n".join([
            'const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g,',
            '  c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", \'"\': "&quot;" }[c]));',
            self.lift(r"function chartShell\(kicker, sub, body, twin, src\) \{.+?\n  \}"),
            self.lift(r"const chartUnfetched = .+?;"),
            self.lift(r"const chartDay = .+?;"),
            self.lift(r"function chartVotes\(plane\) \{.+?\n  \}"),
        ])
        body = "\n".join([
            self.PRELUDE, self.helpers(), extra,
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const mixed = chartVotes({ n_meetings: 1, votes: [",
            "  {pid:'vid1', date:'2026-03-10', t:10, motion:'a', outcome:'passes', tally:'3–0'},",
            "  {pid:'vid1', date:'2026-03-10', t:20, motion:'b', outcome:'fails', tally:'0–3'},",
            "  {pid:'vid1', date:'2026-03-10', t:30, motion:'c', outcome:'tabled', tally:''},",
            "]});",
            "if ((mixed.match(/<circle/g) || []).length !== 2) fail('two circles expected');",
            "if (!/fill=\"#ffffff\" stroke=\"#052e16\"/.test(mixed)) fail('fails must stay hollow');",
            "if (!/<rect[^>]*fill-opacity=\"\\.5\"/.test(mixed)) fail('tabled must be the half-tone square');",
            "if (!mixed.includes('other outcomes')) fail('legend must name the third class');",
            "if (!mixed.includes('tabled')) fail('the exact word must ride the twin/tooltip');",
            "if (!mixed.includes('role=\"group\"')) fail('role=img would hide every receipt from AT');",
            "if (!mixed.includes('pb-twinwrap')) fail('the twin needs its scroll container');",
            "const plain = chartVotes({ n_meetings: 1, votes: [",
            "  {pid:'vid1', date:'2026-03-10', t:10, motion:'a', outcome:'passes', tally:'3–0'},",
            "]});",
            "if (plain.includes('other outcomes')) fail('no third class → no third legend entry');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"chartVotes outcomes broken:\n{r.stdout}{r.stderr}")

    def test_a_cap_cut_never_strands_half_an_emoji(self):
        """PAPER_NOTE_MAX and PAPER_TITLE_MAX count UTF-16 units; a bare
        slice at the cap can split a surrogate pair, and encodeURIComponent
        THROWS on the stranded half — a copy-link click would die on a
        paper whose emoji landed on the boundary. cut() gives the pair up
        instead (decodeReel's law: never a throw)."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const noted = { title: '', blocks: [",
            "  {kind:'note', text: 'x'.repeat(PAPER_NOTE_MAX - 1) + '\\u{1F600}'}]};",
            "const titled = { title: 'y'.repeat(PAPER_TITLE_MAX - 1) + '\\u{1F600}',",
            "  blocks: [] };",
            "let url;",
            "try { url = paperShareURL(noted); }",
            "catch (e) { fail('note at the cap THREW: ' + e); }",
            "try { url = paperShareURL(titled); }",
            "catch (e) { fail('title at the cap THREW: ' + e); }",
            "const back = decodePaper('?v=1&t=' + 'z'.repeat(300));",
            "if (back.title.length !== PAPER_TITLE_MAX) fail('title cap ' + back.title.length);",
            "const n = normalizeBlock({kind:'note', text: 'x'.repeat(PAPER_NOTE_MAX - 1) + '\\u{1F600}'});",
            "if (n.text.length !== PAPER_NOTE_MAX - 1) fail('the pair must be given up whole: ' + n.text.length);",
            "// a hand-edited draft can hold a lone surrogate ANYWHERE (JSON",
            "// round-trips it) — the encoders must survive that too",
            "for (const dirty of ['a\\uDC00b', 'a\\uD800b', '\\uDC00', 'ok \\uD800'])",
            "  try {",
            "    const u = paperShareURL({ title: dirty, blocks: [{kind:'note', text: dirty}] });",
            "    if (/%ED/i.test(u)) fail('a lone half leaked into the link: '+u);",
            "  } catch (e) { fail('interior lone surrogate THREW: '+e); }",
            "if (cut('a\\uDC00b\\uD800c', 99) !== 'abc') fail('lone halves must drop: '+JSON.stringify(cut('a\\uDC00b\\uD800c', 99)));",
            "if (cut('a\\u{1F600}b', 99) !== 'a\\u{1F600}b') fail('a whole pair must survive cut');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"surrogate cut broken:\n{r.stdout}{r.stderr}")

    def test_paper_json_charts_carry_their_record_urls(self):
        """Provenance for a chart is the page a reader can recount it on —
        every chart block in the receipt names its record page."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            f"const draft = {self.P2_DRAFT};",
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const j = paperJSON(draft);",
            "const urls = j.blocks.filter(b => b.kind === 'chart').map(b => b.url);",
            "const want = ['https://publicrecord.studio/app/officials',",
            "  'https://publicrecord.studio/app/analytics',",
            "  'https://publicrecord.studio/app/m/vid1',",
            "  'https://publicrecord.studio/app/i/budget-override',",
            "  'https://publicrecord.studio/app/analytics'];",
            "if (JSON.stringify(urls) !== JSON.stringify(want))",
            "  fail('chart urls drifted: '+JSON.stringify(urls));",
            "const note = j.blocks[5];",
            "if (note.kind !== 'note' || !note.text.includes('tally')) fail('note lost from receipt');",
            "if ('url' in note) fail('a note has no record URL — it is the editor’s words');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"paperJSON P2 malformed:\n{r.stdout}{r.stderr}")

    def test_the_caps_and_kinds_match_the_store(self):
        """One cap, one enum, two languages — the reader's constants must
        equal the store's or a paper the panel accepts gets a 422 at share."""
        from record.papers import CHARTS, NOTE_MAX
        m = re.search(r"const PAPER_NOTE_MAX = (\d+);", self.JS)
        self.assertTrue(m and int(m.group(1)) == NOTE_MAX,
                        "PAPER_NOTE_MAX drifted from record.papers.NOTE_MAX")
        m = re.search(r"const PAPER_CHARTS = \[(.+?)\];", self.JS)
        self.assertEqual(tuple(re.findall(r'"(\w+)"', m.group(1))), CHARTS,
                         "PAPER_CHARTS drifted from record.papers.CHARTS")

    def test_featured_papers_match_the_js_codec_byte_for_byte(self):
        """specs/21 P3: the press builds featured-paper links in PYTHON
        (emit.featured_papers); the JS codec is the law. Decode each pressed
        query in node, re-encode it with encodePaperQS — the bytes must be
        identical, and the pressed v= must equal paperV's own judgement on
        the decoded paper. A drift here ships front-door links the reader
        reads differently than the press intended."""
        feats = emit.featured_papers(
            [{"pid": "vid1", "title": "Select Board — March",
              "date": "2026-03-10",
              "votes": [{"t": 12.0, "outcome": "passes"}]},
             {"pid": "vid2", "title": "École — Réunion & vote",
              "date": "2026-04-02", "votes": []}],
            [],
            # unicode + & + ' in the one dynamic title, so the two
            # encoders' charsets are exercised, not just ASCII
            {"loud": [{"slug": "budget-override",
                       "name": "l'école & the override", "n_meetings": 2}]})
        self.assertEqual(len(feats), 3, feats)
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "const FEATS = " + json.dumps([f["qs"] for f in feats]) + ";",
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "for (const qs of FEATS) {",
            "  const back = decodePaper('?' + qs);",
            "  if (!back.blocks.length) fail('nothing decoded from '+qs);",
            "  const re = encodePaperQS({ title: back.title, blocks: back.blocks });",
            "  if (re !== qs) fail('byte drift\\npy '+qs+'\\njs '+re);",
            "  const v = new URLSearchParams(qs).get('v');",
            "  if (v !== paperV(portablePaper({title: back.title, blocks: back.blocks})))",
            "    fail('v drifted on '+qs);",
            "}",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         "the Python link-builder drifted from the JS codec:\n"
                         f"{r.stdout}{r.stderr}")

    def test_a_template_writes_the_draft_and_never_overwrites_without_asking(self):
        """specs/21 P3: a template is a pre-shaped draft, and the overwrite
        rule is load-bearing — a draft that grew between paint and press
        (another tab) is replaced only past a confirm. Executed with the
        panel stubbed; the planes dark, so the refs must stand on their own."""
        tpl = self.lift(r"  async function applyPaperTemplate\(t, ref, where\) \{.+?\n  \}")
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            self.lift(r"  function afterAdd\(i, at, focus\) \{.+?\n  \}"),
            "let PAGE_FOCUS = null; const renderPaperNow = () => {};",
            "let saved = null, confirms = 0, confirmAnswer = false;",
            "const window = { confirm: () => { confirms++; return confirmAnswer; } };",
            "const getJSON = async () => null;",
            "let cur = { title: '', blocks: [] };",
            "const readPaper = () => normalizePaper(cur);",
            "const savePaper = p => { saved = p; return true; };",
            "const pageStoryRef = () => ({ story: 'issue', slug: 'budget-override' });",
            "const refreshPaperSummary = () => {};",
            "const schedulePaperRender = () => {};",
            "const toast = () => {};",
            tpl,
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "(async () => {",
            "  await applyPaperTemplate('rolls');",
            "  if (!saved) fail('empty draft: the template did not write');",
            "  if (saved.title !== 'the roll calls, watched') fail('title '+saved.title);",
            "  if (JSON.stringify(saved.blocks.map(b => b.kind + ':' + (b.chart || '')))",
            "      !== JSON.stringify(['chart:votes','chart:framing','note:']))",
            "    fail('rolls shape '+JSON.stringify(saved.blocks));",
            "  if (saved.blocks[2].text !== '') fail('a template wrote the editor’s words');",
            "  if (confirms) fail('asked for consent on an empty draft');",
            "  saved = null;",
            "  await applyPaperTemplate('issue');",
            "  if (!saved) fail('issue template did not write');",
            "  if (saved.title !== 'budget-override — how it moved') fail('issue title '+saved.title);",
            # the planes are dark here (getJSON → null): the story and its
            # numbers stand on the ref alone; reach, digest, ledger, the
            # quotes and the reading wait for a timeline (specs/24 §2.2)
            "  if (saved.blocks[0].slug !== 'budget-override' || saved.blocks[1].chart !== 'numbers'",
            "      || saved.blocks[1].slug !== 'budget-override' || saved.blocks[2].kind !== 'note'",
            "      || saved.blocks.length !== 3) fail('issue shape '+JSON.stringify(saved.blocks));",
            # a title-only draft (named first, shaped second — the on-page
            # editor's order): the name stays, the shape arrives, no question
            "  cur = { title: 'mine', blocks: [] }; saved = null; confirmAnswer = false;",
            "  await applyPaperTemplate('rolls');",
            "  if (confirms) fail('asked before shaping a draft that is only a title');",
            "  if (!saved || saved.title !== 'mine') fail('a title-only draft lost its name: ' + JSON.stringify(saved));",
            "  if (saved.blocks.length !== 3) fail('the shape did not arrive');",
            # blocks are work: asked about, and refused means untouched
            "  cur = { title: 'mine', blocks: [{kind:'note',text:'kept'}] }; saved = null; confirmAnswer = false;",
            "  await applyPaperTemplate('rolls');",
            "  if (!confirms) fail('never asked before replacing a live draft');",
            "  if (saved) fail('replaced a draft the editor refused to lose');",
            "  confirmAnswer = true;",
            "  await applyPaperTemplate('rolls');",
            "  if (!saved) fail('consent given, nothing written');",
            "  console.log('ok');",
            "})();",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"the template misbehaved:\n{r.stdout}{r.stderr}")

    def test_the_on_page_editor_touches_no_server(self):
        """The covenant, extended to specs/23 A3 (a review catch: the make-
        path scan ended at PART 2, and the whole editor sat past it). The
        on-page editor — its add-search included — reads localStorage,
        strings and the record's own static planes; every plane it asks for
        is a same-origin edition path, and no server is reached."""
        block = self.JS[self.JS.index("PART 3: the on-page editor"):
                        self.JS.index("================= SEARCH =================")]
        for forbidden in ("fetch(", "XMLHttpRequest", "sendBeacon", "/api/",
                          "askStudio", "API_TIMEOUT", "document.cookie",
                          "new Image(", "run.app"):
            self.assertNotIn(forbidden, block,
                             f"the on-page editor reached for {forbidden!r} — "
                             f"composing must not touch a server (specs/23 §3)")
        planes = re.findall(r"getJSON\(`([^`]+)`", block)
        self.assertTrue(planes, "the add-search reads no static plane at all?")
        for plane in planes:
            self.assertTrue(plane.startswith("${BASE}/"),
                            f"{plane} is not an edition path")
        # the two index planes it reads are the pressed ones — no new door
        self.assertIn("${BASE}/search/meta.json", block)
        self.assertIn("${BASE}/issues/index.json", block)

    def test_the_editor_door_and_its_focus_rules_are_pinned(self):
        """The review's folds, pinned by token so a revert shows: the hash
        door is consumed once and dropped from the address (a reload keeps
        the mode the reader chose); a same-document #edit click is heard;
        on a phone the door opens the studio collapsed to its rail; the
        teaching surface and the block editor both put the caret back after
        a repaint; a block dropped on the title is a cancelled move, never a
        payload typed into the field; the reader's own drags outside the
        editor rows are left alone; the visible words lead every
        accessible name (WCAG 2.5.3)."""
        for token in ('history.replaceState(null, "", location.pathname + location.search); }',
                      'window.addEventListener("hashchange"',
                      'window.matchMedia("(max-width: 720px)").matches',
                      "writeRail(narrow); setMode(\"studio\");",
                      "clearTimeout(PAPER_RERENDER);\n          }",
                      "restoreEdFocus(el, PAGE_FOCUS || keep2)",
                      "const keep2 = captureEdFocus(el) || keep;",
                      "function edForget(dark)",
                      "captureEdFocus(el) || captureEdPanel(el)",
                      "if (!row && !slot) { e.preventDefault(); ED_DRAG = -1; edClearDrop(el); return; }",
                      "if (!row) return;\n      if (!row.draggable) { e.preventDefault(); return; }",
                      "`in your paper — remove “${name}”`",
                      "`your paper — add “${name}”`",
                      'aria-label="add here${at',
                      'if (m === "studio") schedulePaperRender(); else renderPaperNow();'):
            self.assertIn(token, self.JS, f"{token!r} drifted — a review fold was reverted")
        # the hit list is not a live region; one short status line is
        self.assertNotIn('class="cz-edhits" aria-live', self.JS)
        self.assertIn('class="cz-edcount" role="status"', self.JS)
        css = (REPO / "web" / "static" / "app.web.css").read_text()
        for rule in (".pf-lede a{color:var(--text-primary);text-decoration:underline",
                     "html:not(.cz-m-paper) .cz-mkwrap-lead>.lead>.kicker{padding-right:112px}",
                     "html.cz-m-studio .cz-edq::placeholder{color:var(--text-secondary)}",
                     ".tnode .thead .cz-mk{display:inline-block",
                     "html.cz-m-studio.cz-rail body{padding-left:44px}"):
            self.assertIn(rule, css, f"{rule!r} missing from the sheet")

    def test_the_shelf_migrates_the_old_draft_once_and_is_total(self):
        """specs/23 C1: `cz-papers` holds every paper and which one is open.
        The single P1 draft migrates in exactly once (kept whole, then its
        key removed, the loadReel way); garbage on the shelf drops; an
        empty shelf grows one blank paper; a dangling pointer falls to the
        first; readPaper/savePaper address the OPEN paper; new/switch/
        delete keep the shelf never empty."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "const STORE = {}; const localStorage = { getItem: k => (k in STORE ? STORE[k] : null),",
            "  setItem: (k, v) => { STORE[k] = String(v); }, removeItem: k => { delete STORE[k]; } };",
            "let PAPER_SHORT = ''; const toast = () => {}; const retireShortOut = () => {};",
            "const refreshPaperSummary = () => {}; const renderPaperNow = () => {}; const schedulePaperRender = () => {};",
            "const window = { confirm: () => true };",
            self.lift(r"  const PAPER_KEY = .+?;"),
            self.lift(r"  const PAPERS_KEY = .+?;"),
            self.lift(r"  const PAPERS_MAX = .+?;"),
            self.lift(r"  let PAPERS_BLANK = .+?;"),
            self.lift(r"  const PAPER_ID = .+?;"),
            self.lift(r"  const paperId = .+?;"),
            self.lift(r"  function readPapers\(\) \{.+?\n  \}"),
            self.lift(r"  function writePapers\(sh\) \{.+?\n  \}"),
            self.lift(r"  function readPaper\(\) \{.+?\n  \}"),
            self.lift(r"  function savePaper\(p\) \{.+?\n  \}"),
            self.lift(r"  function newPaper\(\) \{.+?\n  \}"),
            self.lift(r"  function switchPaper\(id\) \{.+?\n  \}"),
            self.lift(r"  function deletePaper\(\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            # a fresh browser: a READ writes nothing (no id minted into storage
            # for a reader who never makes anything) and keeps one id
            "const fresh1 = readPapers(), fresh2 = readPapers();",
            "if (Object.keys(STORE).length) fail('a read must write nothing: ' + JSON.stringify(STORE));",
            "if (fresh1.active !== fresh2.active || fresh1.papers.length !== 1) fail('one blank paper, one id, for the page');",
            "savePaper({ title: 'first save', blocks: [] });",
            "if (JSON.parse(STORE['cz-papers']).active !== fresh1.active) fail('the first save writes the shelf under the same id');",
            "for (const k of Object.keys(STORE)) delete STORE[k];",
            # the old draft migrates once
            "STORE['cz-paper'] = JSON.stringify({ title: 'mine', blocks: [{kind:'note',text:'kept'}] });",
            "let p = readPaper();",
            "if (p.title !== 'mine' || p.blocks.length !== 1) fail('the P1 draft did not migrate: ' + JSON.stringify(p));",
            "if ('cz-paper' in STORE) fail('the old key must go once the shelf holds it');",
            "const sh1 = JSON.parse(STORE['cz-papers']);",
            "if (sh1.papers.length !== 1 || sh1.active !== sh1.papers[0].id) fail('shelf shape ' + STORE['cz-papers']);",
            # save addresses the open paper
            "savePaper({ title: 'renamed', blocks: [] });",
            "if (readPaper().title !== 'renamed') fail('save did not address the open paper');",
            # new, switch, delete
            "newPaper(); const sh2 = readPapers();",
            "if (sh2.papers.length !== 2 || readPaper().title !== '') fail('new paper did not open blank');",
            "switchPaper(sh2.papers[0].id);",
            "if (readPaper().title !== 'renamed') fail('switch did not open the first paper');",
            "deletePaper();",
            "if (readPapers().papers.length !== 1 || readPaper().title !== '') fail('delete left the wrong paper open');",
            "deletePaper();",
            "if (readPapers().papers.length !== 1) fail('the shelf must never stand empty');",
            # total over garbage
            "STORE['cz-papers'] = JSON.stringify({ active: 'nope', papers: [null, 7, {id:'BAD ID'}, {id:'ok1234', title:'t', blocks:'x'}, {id:'ok1234', title:'dup'}] });",
            "const sh3 = readPapers();",
            "if (sh3.papers.length !== 1 || sh3.papers[0].id !== 'ok1234' || sh3.active !== 'ok1234') fail('garbage on the shelf: ' + JSON.stringify(sh3));",
            "STORE['cz-papers'] = 'not json';",
            "if (!readPapers().papers.length) fail('unreadable shelf must grow a blank paper');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"the shelf misbehaved:\n{r.stdout}{r.stderr}")

    def test_layouts_travel_the_link_the_export_and_the_store_form(self):
        """specs/23 C1: a layout is an enum on a block; it rides `l=` in the
        link (index:layout pairs, so v1/v2 `b=` never changes shape), lifts
        the link to v=3, survives the round trip, sits in the portable form
        and the receipt; an unknown layout is dropped by the reader (total),
        a mangled `l=` costs a layout never a throw, and a layout names its
        block by the LINK's part index — a dropped part does not shift it."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const p = { title: 'laid out', blocks: [",
            "  {kind:'story',story:'meeting',pid:'vid1',layout:'lead'},",
            "  {kind:'chart',chart:'votes',layout:'half'},",
            "  {kind:'chart',chart:'topics',layout:'half'},",
            "  {kind:'note',text:'words',layout:'bogus'},",
            "  {kind:'story',story:'issue',slug:'s1'} ] };",
            "const n = normalizePaper(p);",
            "if (n.blocks[3].layout) fail('an unknown layout must drop');",
            "if (n.blocks[0].layout !== 'lead' || n.blocks[1].layout !== 'half') fail('layouts lost in normalize');",
            "const qs = encodePaperQS(p);",
            "if (!qs.startsWith('v=3')) fail('a laid-out paper travels as v=3: ' + qs);",
            "if (!qs.includes('&l=0:lead,1:half,2:half')) fail('l= grammar: ' + qs);",
            "const d = decodePaper('?' + qs);",
            "const lays = d.blocks.map(b => b.layout || '');",
            "if (lays.join(',') !== 'lead,half,half,,') fail('round trip: ' + lays.join(','));",
            "if (JSON.stringify(portablePaper(p).blocks[0]) !== JSON.stringify({kind:'story',story:'meeting',pid:'vid1',layout:'lead'})) fail('portable form: ' + JSON.stringify(portablePaper(p).blocks[0]));",
            "if (paperJSON(p).blocks[1].layout !== 'half') fail('the receipt lost the layout');",
            # a paper with no layout stays v=1/v=2 byte-stable
            "const plain = { title: 't', blocks: [{kind:'story',story:'meeting',pid:'vid1'}] };",
            "if (encodePaperQS(plain) !== 'v=1&t=t&b=m.vid1') fail('a plain paper changed shape: ' + encodePaperQS(plain));",
            # mangled l= never throws; a layout follows the LINK index
            "for (const l of ['', 'x', '0:', ':lead', '0:lead,,9:half', '1:LEAD', '0:lead;1:half', 'NaN:lead']) {",
            "  const dd = decodePaper('?v=3&b=m.vid1,c.votes&l=' + l);",
            "  if (dd.blocks.length !== 2) fail('mangled l= dropped a block: ' + l);",
            "}",
            # part 1 is a mangle (dropped); the layout at link index 2 must land on the votes chart
            "const dz = decodePaper('?v=3&b=m.vid1,zz.bad,c.votes&l=2:head');",
            "if (dz.blocks.length !== 2 || dz.blocks[1].layout !== 'head' || dz.blocks[0].layout) fail('layout index shifted: ' + JSON.stringify(dz.blocks));",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"layouts misbehaved:\n{r.stdout}{r.stderr}")

    def test_the_rich_tier_fold_is_pinned(self):
        """The C review fold (specs/23 C1+C2): a tape that did not load is
        DARK, not empty, and a quote says so; the lines AT a second are the
        quote (two short lines can share one whole-second stamp); the digest
        ranks dated appearances newest first and counts the undated; a
        section head paints for the three ref kinds and is additive for a
        block with a body; deletePaper re-reads the shelf after its blocking
        confirm; the add-search paints the index at once and the lines under
        a generation stamp; printed citations spell the site; the note
        prints whole from the editor."""
        for token in ("const linesAt = (lines, t) => {",
                      "for (const l of (lines || [])) {",
                      '.then(r => r.ok ? r.text() : null).catch(() => null)',
                      "if (tx == null) return null;",
                      "const lines = {}; for (const [pid, l] of lineSets) lines[pid] = l;",
                      "if (lines === null) return paperDark(",
                      "const paperDark = (what, where) =>",
                      '<figure class="pb-quote"><blockquote>',
                      "<figcaption>",
                      "const nodes = dated.length ? dated.slice(0, b.n) : tl.slice(-b.n).reverse();",
                      "undated appearance${undated === 1 ? \"\" : \"s\"} not ranked here",
                      'else if (b.kind === "quote") {\n      const m = mby[b.pid]; if (!m) return null;',
                      '} else if (b.kind === "doc") {\n      const m = mby[b.pid]; if (!m) return null;',
                      '} else if (b.kind === "digest") {\n      const it = iby[b.slug]; if (!it) return null;',
                      'return head ? (b.kind === "story" ? head : head + html) : html;',
                      "const id = cur.id;",
                      'if (!sh.papers.some(p => p.id === id)) { toast("that paper was already deleted in another tab");',
                      "const gen = slot._edgen = (slot._edgen || 0) + 1;",
                      "if (slot._edgen !== gen || !box2) return;",
                      'el.style.setProperty("--site", JSON.stringify(location.origin));',
                      '<div class="cz-ednote-print" aria-hidden="true">',
                      'data-layout="${esc(b.layout || "")}"',
                      "const first = $(\"button, [tabindex]\", span); if (first) first.focus();",
                      "if (!m) delete _cache[url];",
                      'aria-label="try again — load this meeting’s documents">try again</button>',
                      '(btn.closest(".cz-eddocs") || btn).replaceWith(span);',
                      '<p class="ptitle cz-edtitle-print" aria-hidden="true">${esc(printTitle(doc.title))}</p>',
                      'const tw = $(".cz-edtitle-print", el); if (tw) tw.textContent = printTitle(d.title);',
                      "if (tw) tw.innerHTML = notePrint(d.blocks[i].text);",
                      'window.addEventListener("beforeprint", () => {',
                      "const paired = halfPairs(doc.blocks);",
                      '${pair ? \' data-pair="1"\' : ""}',
                      '"searching the tape’s own lines…" : countLine([]);',
                      'aria-label="quote — the line at ${hms(l.t)} of ${esc(l.title)}, in your paper"',
                      "(opens in a new tab)"):
            self.assertTrue(token in self.JS, f"{token!r} drifted — the C fold was reverted")
        self.assertTrue("docChooserHTML" not in self.JS)   # the dead second chooser is gone
        # the tape's lines land in place: appending never rebuilds the hits a
        # reader may already have tabbed onto
        self.assertIn('box2.insertAdjacentHTML("beforeend", `<span class="cz-edgroup">lines of the tape</span>', self.JS)
        self.assertNotIn("box2.innerHTML +=", self.JS)
        # part 3: a clear that did not hold says only that; a read writes nothing
        clear = self.JS[self.JS.index("function clearPaper()"):]
        clear = clear[:clear.index("\n  }\n")]
        self.assertIn('toast("this browser blocks storage — the change didn’t hold"); return; }', clear)
        self.assertIn("if (raw != null && writePapers(sh))", self.JS)
        css = (REPO / "web" / "static" / "app.web.css").read_text()
        prn_start = css.index("@media print{")
        prn = css[prn_start:css.index("\n}\n", prn_start)]   # the block's own brace, not the file's end
        for rule in ('content:" " var(--site,"") attr(href)',
                     ".pb-dg::after{grid-column:1/-1}",
                     "html.cz-m-studio body,html.cz-m-studio.cz-rail body{padding-left:0 !important}",
                     "word-break:normal;overflow-wrap:anywhere",
                     '.reelcite[href^="/"]::after',
                     ".cz-editing .cz-ednote{display:none}",
                     ".cz-editing .cz-ednote-print{display:block}",
                     '.cz-editing .cz-edrow[data-pair]{display:inline-block;width:48%;margin:0 1%',
                     "html.cz-m-studio .cz-editing .cz-edtitle{display:none}",
                     "html.cz-m-studio .cz-editing .cz-edtitle-print{display:block"):
            self.assertIn(rule, prn, f"the print sheet lost {rule!r}")
        self.assertIn(".cz-ednote-print,.cz-edtitle-print{display:none}", css)
        self.assertNotIn("word-break:break-all", prn)       # an address breaks only when it must
        self.assertIn(".cz-shelf .btn{font-size:var(--text-xs);padding:5px 9px;display:inline-flex;align-items:center;min-height:24px}", css)
        self.assertIn('@media (min-width:721px){html.cz-m-studio .cz-edrow[data-pair] .cz-edbody{width:50%', css)
        self.assertNotIn('.cz-edrow[data-layout="half"]', css)   # never every half — only the paired
        self.assertIn(".pb-quote figcaption{", css)
        self.assertNotIn(".pb-quote cite", css)
        # the lines at a second — the twin
        r = self.node("\n".join([
            self.PRELUDE,
            self.lift(r"  const lineAt = \(lines, t\) => \{.+?return hit; \};"),
            self.lift(r"  const linesAt = \(lines, t\) => \{.+?\n  \};"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const L = [{t:5,spk:'A',text:'one'},{t:9,spk:'B',text:'two'},{t:9,spk:'C',text:'three'},{t:30,spk:'',text:''}];",
            "if (linesAt(L, 9.4).map(l => l.text).join('|') !== 'two|three') fail('both lines at the second: ' + JSON.stringify(linesAt(L, 9.4)));",
            "if (linesAt(L, 12).map(l => l.text).join('|') !== 'three') fail('the line running through 12 is the last one that started at 9');",
            "if (linesAt(L, 6.9).map(l => l.text).join('|') !== 'one') fail('one line running through 6.9');",
            "if (linesAt(L, 31).length !== 0) fail('an empty line at 30 is no quote');",
            "if (linesAt(L, 2).length !== 0) fail('before the first line: nothing');",
            "if (linesAt(null, 9).length !== 0 || linesAt([], 9).length !== 0) fail('total over null and []');",
            "if (lineAt(null, 9) !== null) fail('lineAt is total over null');",
            "console.log('ok');"]))
        self.assertEqual(r.stdout.strip(), "ok", r.stdout + r.stderr)
        # the renderer's facts, executed: a dark tape, a tape past the page's
        # fetch cap, and a tape with no lines are three different sentences;
        # a head is additive for every kind with a body, and IS a story
        r = self.node("\n".join([
            self.PRELUDE,
            "const esc = x => String(x == null ? '' : x).replace(/[&<>\"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;' }[c]));",
            "const hms = t => String(t); const chartRowLabel = b => '▤ ' + (b.chart || 'chart');",
            self.lift(r"  const paperGone = what => .+?</p>`;"),
            self.lift(r"  const paperDark = \(what, where\) => .+?</p>`;"),
            self.lift(r"  const paperBudget = what => .+?</p>`;"),
            self.lift(r"  const lineAt = \(lines, t\) => \{.+?return hit; \};"),
            self.lift(r"  const linesAt = \(lines, t\) => \{.+?\n  \};"),
            self.lift(r"  function renderQuote\(b, mby, aux\) \{.+?\n  \}"),
            self.lift(r"  function renderHead\(b, mby, iby\) \{.+?\n  \}"),
            self.lift(r"  function withLayoutHTML\(html, b, mby, iby\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const M = { p1: { title: 'Board', documents: [{ doc_id: 'doc:m', title: 'Minutes', url: 'https://ex.test/m.pdf' }] } };",
            "const I = { z: { name: 'Zoning' } };",
            "const T = { m: new Set(['p1']), i: new Set() };",
            "const q = { kind: 'quote', pid: 'p1', t: 54 };",
            "if (!renderQuote(q, M, { lines: { p1: null }, tried: T }).includes('didn’t load here')) fail('a dark tape is said as dark');",
            "if (!renderQuote(q, M, { lines: {}, tried: T }).includes('left unfetched')) fail('past the cap is said as such');",
            "if (!renderQuote(q, M, { lines: { p1: [] }, tried: T }).includes('isn’t in this pressing')) fail('a tape with no lines: the line is not in this pressing');",
            "const two = renderQuote(q, M, { lines: { p1: [{ t: 54, spk: 'A', text: 'My vote.' }, { t: 54, spk: 'B', text: 'Aye.' }] }, tried: T });",
            "if ((two.match(/<p>/g) || []).length !== 2 || !two.includes('<figcaption>') || two.includes('data-cite')) fail('two lines at the second, one figure: ' + two);",
            "const W = b => withLayoutHTML('<BODY>', Object.assign({}, b, { layout: 'head' }), M, I);",
            "if (W({ kind: 'story', story: 'meeting', pid: 'p1' }).includes('<BODY>')) fail('a story\\'s head is the story');",
            "for (const b of [{ kind: 'note', text: 'Line one\\nline two' }, { kind: 'chart', chart: 'votes' }, { kind: 'reel', clips: [{}, {}] }, q,",
            "                 { kind: 'doc', pid: 'p1', doc: 'doc:m' }, { kind: 'digest', slug: 'z', n: 3 }]) {",
            "  const out = W(b); if (!out.includes('<h3 class=\"pb-head\">') || !out.includes('<BODY>')) fail('head + body for ' + b.kind + ': ' + out); }",
            "if (!W({ kind: 'note', text: 'Line one\\nline two' }).includes('>Line one</h3>')) fail('a note\\'s head is its first line');",
            "console.log('ok');",
        ]))
        self.assertEqual(r.stdout.strip(), "ok", r.stdout + r.stderr)
        # the editor pairs halves by the reader's own rule (paintLayouts):
        # two consecutive halves, taken two at a time
        r = self.node("\n".join([
            self.lift(r"  const halfPairs = blocks => \{.+?return s; \};"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const L = s => s.split('').map(c => ({ layout: c === 'h' ? 'half' : c === 'l' ? 'lead' : '' }));",
            "const P = s => [...halfPairs(L(s))].sort((a, b) => a - b).join();",
            "if (P('hh') !== '0,1') fail('two halves pair');",
            "if (P('h') !== '' || P('h.h') !== '' || P('hl') !== '') fail('a half with no half beside it is not paired');",
            "if (P('hhh') !== '0,1') fail('three halves: the first two pair, the third stands alone');",
            "if (P('hhhh') !== '0,1,2,3') fail('four halves: two pairs');",
            "if (P('.hh.hh') !== '1,2,4,5') fail('pairs anywhere in the paper');",
            "console.log('ok');"]))
        self.assertEqual(r.stdout.strip(), "ok", r.stdout + r.stderr)
        self.assertIn('if (b.layout === "half" && pairs[i + 1] && pairs[i + 1][0].layout === "half") {', self.JS)
        # a digest of an issue whose appearances are all undated shows them,
        # said as undated — never "curated away"; an empty timeline is gone
        r = self.node("\n".join([
            self.PRELUDE,
            "const esc = x => String(x == null ? '' : x).replace(/[&<>\"]/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '\"': '&quot;' }[c]));",
            "const paperGone = w => 'GONE ' + w; const paperBudget = w => 'BUDGET ' + w;",
            self.lift(r"  function renderDigest\(b, iby, tried\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const T = { m: new Set(), i: new Set() };",
            "const I = tl => ({ z: { name: 'Zoning', timeline: tl } });",
            "const node = (pid, date) => ({ pid, date, body: 'Board', n: 1, beads: [] });",
            "let h = renderDigest({ slug: 'z', n: 3 }, I([node('a', ''), node('b', '')]), T);",
            "if (h.startsWith('GONE') || !h.includes('2 undated appearances') || (h.match(/>undated</g) || []).length !== 2) fail('all undated: ' + h);",
            "if (!h.includes('none of its appearances is dated')) fail('the source line says why');",
            "h = renderDigest({ slug: 'z', n: 2 }, I([node('a', '2026-01-02'), node('b', '2026-03-04'), node('c', '')]), T);",
            "const d = [...h.matchAll(/pb-dg-d\">([^<]*)</g)].map(m => m[1]).join();",
            "if (d !== '2026-03-04,2026-01-02' || !h.includes('1 undated appearance not ranked here')) fail('dated newest first, the undated counted: ' + d);",
            "if (!renderDigest({ slug: 'z', n: 3 }, I([]), T).startsWith('GONE')) fail('an empty timeline is gone');",
            "console.log('ok');"]))
        self.assertEqual(r.stdout.strip(), "ok", r.stdout + r.stderr)
        # deletePaper re-reads the shelf after the confirm: another tab's
        # paper, written while the dialog stood, survives the delete
        r = self.node("\n".join([
            self.PRELUDE, self.helpers(),
            "const STORE = {}; const localStorage = { getItem: k => (k in STORE ? STORE[k] : null),",
            "  setItem: (k, v) => { STORE[k] = String(v); }, removeItem: k => { delete STORE[k]; } };",
            "let PAPER_SHORT = ''; const toasts = []; const toast = m => toasts.push(m); const retireShortOut = () => {};",
            "const refreshPaperSummary = () => {}; const renderPaperNow = () => {}; const schedulePaperRender = () => {};",
            self.lift(r"  const PAPER_KEY = .+?;"),
            self.lift(r"  const PAPERS_KEY = .+?;"),
            self.lift(r"  const PAPERS_MAX = .+?;"),
            self.lift(r"  let PAPERS_BLANK = .+?;"),
            self.lift(r"  const PAPER_ID = .+?;"),
            self.lift(r"  const paperId = .+?;"),
            self.lift(r"  function readPapers\(\) \{.+?\n  \}"),
            self.lift(r"  function writePapers\(sh\) \{.+?\n  \}"),
            self.lift(r"  function readPaper\(\) \{.+?\n  \}"),
            self.lift(r"  function deletePaper\(\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "STORE['cz-papers'] = JSON.stringify({ active: 'aaaa11', papers: [{id:'aaaa11', title:'mine', blocks:[]}, {id:'bbbb22', title:'other', blocks:[]}] });",
            "// while the dialog stands, another tab adds a paper and opens it",
            "const window = { confirm: () => { STORE['cz-papers'] = JSON.stringify({ active: 'cccc33', papers: [{id:'aaaa11', title:'mine', blocks:[]}, {id:'bbbb22', title:'other', blocks:[]}, {id:'cccc33', title:'new in tab two', blocks:[{kind:'note',text:'x'}]}] }); return true; } };",
            "deletePaper();",
            "const sh = JSON.parse(STORE['cz-papers']);",
            "if (sh.papers.map(p => p.id).join(',') !== 'bbbb22,cccc33') fail('the other tab\\'s paper must survive: ' + STORE['cz-papers']);",
            "if (sh.active !== 'cccc33') fail('the other tab\\'s open paper stays open: ' + sh.active);",
            "// the paper was already deleted elsewhere: nothing is written, the reader is told",
            "window.confirm = () => { STORE['cz-papers'] = JSON.stringify({ active: 'cccc33', papers: [{id:'cccc33', title:'new in tab two', blocks:[]}] }); return true; };",
            "STORE['cz-papers'] = JSON.stringify({ active: 'bbbb22', papers: [{id:'bbbb22', title:'other', blocks:[]}, {id:'cccc33', title:'t', blocks:[]}] });",
            "deletePaper();",
            "if (JSON.parse(STORE['cz-papers']).papers.length !== 1 || !toasts.some(t => /already deleted/.test(t))) fail('a vanished paper is reported, not re-deleted: ' + STORE['cz-papers'] + ' ' + toasts);",
            "console.log('ok');"]))
        self.assertEqual(r.stdout.strip(), "ok", r.stdout + r.stderr)

    def test_the_c2_kinds_are_refs_that_travel_and_never_carry_words(self):
        """specs/23 C2: a pull-quote is (pid, t) — its words ride the DRAFT
        for the panel's label and no traveling form; a document is (pid,
        doc id); a digest is (slug, n) with n clamped to 1..12. Each rides
        the link in its own grammar (q.<pid>:<t>, d.<pid>~<doc>, g.<slug>:<n>),
        lifts the link to v=3, round-trips, and degrades — a mangled part
        drops, never throws. The receipt names each block's record page."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const p = { title: 'refs', blocks: [",
            "  {kind:'quote',pid:'vid1',t:907.44,text:'the words',title:'Select Board'},",
            "  {kind:'doc',pid:'vid1',doc:'doc:budget',title:'Agenda',dkind:'Agenda'},",
            "  {kind:'digest',slug:'budget-override',n:99,name:'budget override'},",
            "  {kind:'digest',slug:'other',n:'x'},",
            "  {kind:'quote',pid:'bad id',t:1}, {kind:'doc',pid:'vid1',doc:'a b'}, {kind:'digest',slug:''} ] };",
            "const n = normalizePaper(p);",
            "if (n.blocks.length !== 4) fail('bad refs must drop: ' + JSON.stringify(n.blocks));",
            "if (n.blocks[0].t !== 907.4 || n.blocks[0].text !== 'the words') fail('quote normalize: ' + JSON.stringify(n.blocks[0]));",
            "if (n.blocks[2].n !== 12 || n.blocks[3].n !== 3) fail('digest window clamp: ' + n.blocks[2].n + '/' + n.blocks[3].n);",
            "const port = portablePaper(p);",
            "if (JSON.stringify(port.blocks[0]) !== JSON.stringify({kind:'quote',pid:'vid1',t:907.4})) fail('a quote must travel as a ref only: ' + JSON.stringify(port.blocks[0]));",
            "if (JSON.stringify(port.blocks[1]) !== JSON.stringify({kind:'doc',pid:'vid1',doc:'doc:budget'})) fail('doc portable: ' + JSON.stringify(port.blocks[1]));",
            "if (JSON.stringify(port.blocks[2]) !== JSON.stringify({kind:'digest',slug:'budget-override',n:12})) fail('digest portable: ' + JSON.stringify(port.blocks[2]));",
            "const qs = encodePaperQS(p);",
            "if (!qs.startsWith('v=3')) fail('C2 kinds travel as v=3: ' + qs);",
            "if (!qs.includes('b=q.vid1:907.4,d.vid1~doc%3Abudget,g.budget-override:12,g.other:3')) fail('grammar: ' + qs);",
            "const d = decodePaper('?' + qs);",
            "if (JSON.stringify(d.blocks) !== JSON.stringify(port.blocks)) fail('round trip: ' + JSON.stringify(d.blocks));",
            "for (const bad of ['q.vid1', 'q.vid1:-1', 'q.vid1:abc', 'q.%E0:1', 'd.vid1', 'd.vid1~', 'd.vid1~a%20b', 'g.slug', 'g.slug:0', 'g.slug:13', 'g.slug:x', 'q.:1', 'd.~x']) {",
            "  const dd = decodePaper('?v=3&b=' + bad + ',m.vid1');",
            "  if (dd.blocks.length !== 1 || dd.blocks[0].kind !== 'story') fail('a mangled part must drop alone: ' + bad + ' → ' + JSON.stringify(dd.blocks));",
            "}",
            "const j = paperJSON(p);",
            "if (!j.blocks[0].url.endsWith('/app/m/vid1#t907') || j.blocks[0].text) fail('receipt quote: ' + JSON.stringify(j.blocks[0]));",
            "if (!j.blocks[2].url.endsWith('/app/i/budget-override')) fail('receipt digest: ' + JSON.stringify(j.blocks[2]));",
            "const plain = { title: 't', blocks: [{kind:'story',story:'meeting',pid:'vid1'},{kind:'note',text:'n'}] };",
            "if (!encodePaperQS(plain).startsWith('v=2')) fail('a paper without C2 kinds or layouts stays v=2');",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"the C2 kinds misbehaved:\n{r.stdout}{r.stderr}")

    def test_the_editor_helpers_are_pure_and_total(self):
        """specs/23 A3: the on-page editor's three pure helpers, in node —
        insertBlock lands at the index it is given (or the end) and refuses
        a full paper; moveBlock moves a block to a drop slot counted before
        the move and no-ops out of range; lexRank requires every term, ranks
        word-start hits over inside-word hits, then the item's own order,
        and answers everything for no terms (the browse start)."""
        body = "\n".join([
            self.PRELUDE, self.helpers(),
            self.lift(r"  function insertBlock\(p, nb, at\) \{.+?\n  \}"),
            self.lift(r"  function moveBlock\(blocks, from, to\) \{.+?\n  \}"),
            self.lift(r"  const lexTerms = .+?;"),
            self.lift(r"  function lexRank\(terms, items\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const p = { title: '', blocks: [{kind:'note',text:'a'},{kind:'note',text:'b'}] };",
            "if (insertBlock(p, {kind:'note',text:'x'}, 1) !== 1 || p.blocks[1].text !== 'x') fail('insert at 1');",
            "if (insertBlock(p, {kind:'note',text:'y'}) !== 3 || p.blocks[3].text !== 'y') fail('insert at end');",
            "if (insertBlock(p, {kind:'note',text:'z'}, 99) !== 4) fail('past the end clamps to the end');",
            "if (insertBlock(p, {kind:'note',text:'w'}, -3) !== 5) fail('a negative index means the end');",
            "const full = { title: '', blocks: Array.from({length: PAPER_MAX_BLOCKS}, () => ({kind:'note',text:''})) };",
            "if (insertBlock(full, {kind:'note',text:''}, 0) !== -1 || full.blocks.length !== PAPER_MAX_BLOCKS) fail('the cap');",
            "const L = () => ['a','b','c','d'];",
            "let b = L(); if (!moveBlock(b, 0, 4) || b.join('') !== 'bcda') fail('0→end ' + b.join(''));",
            "b = L(); if (!moveBlock(b, 3, 0) || b.join('') !== 'dabc') fail('end→0 ' + b.join(''));",
            "b = L(); if (!moveBlock(b, 0, 2) || b.join('') !== 'bacd') fail('0→slot2 ' + b.join(''));",
            "b = L(); if (!moveBlock(b, 2, 1) || b.join('') !== 'acbd') fail('2→slot1 ' + b.join(''));",
            "b = L(); if (moveBlock(b, 1, 1) || moveBlock(b, 1, 2) || b.join('') !== 'abcd') fail('a no-op move must say so');",
            "b = L(); if (moveBlock(b, 4, 0) || moveBlock(b, -1, 0) || moveBlock(b, 0, 5) || b.join('') !== 'abcd') fail('out of range');",
            "const items = [",
            "  { ref: 'm1', text: 'Select Board Meeting - March 10, 2026 Select Board Brookline 2026-03-10', sort: '2026-03-10' },",
            "  { ref: 'm2', text: 'School Committee Meeting - June 18, 2026 School Committee Brookline 2026-06-18', sort: '2026-06-18' },",
            "  { ref: 'm3', text: 'Reselection hearing 2025-12-09', sort: '2025-12-09' },",
            "];",
            "const ids = (t) => lexRank(lexTerms(t), items).map(i => i.ref).join(',');",
            "if (ids('') !== 'm2,m1,m3') fail('no terms = everything, newest first: ' + ids(''));",
            "if (ids('select') !== 'm1,m3') fail('word-start (Select) outranks inside-word (Reselection): ' + ids('select'));",
            "if (ids('board march') !== 'm1') fail('every term must match: ' + ids('board march'));",
            "if (ids('brookline') !== 'm2,m1') fail('ties fall to the item order: ' + ids('brookline'));",
            "if (ids('nothing-here') !== '') fail('a miss is empty, not a throw');",
            "if (lexTerms('a b c d e f g h i j').length !== 8) fail('terms are capped');",
            "if (lexTerms('Über—Straße!').join(',') !== 'ber,stra,e') fail('terms are ascii word runs: ' + lexTerms('Über—Straße!'));",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"an editor helper misbehaved:\n{r.stdout}{r.stderr}")

    def test_the_paper_make_path_touches_no_api(self):
        """The covenant, extended to P1 (specs/21 §5): composing, arranging,
        encoding and exporting a paper read localStorage, strings and the
        record's own static planes — never the API. The store appears only
        past the PART 2 marker, behind the explicit share actions."""
        block = self.JS[self.JS.index("YOUR PAPER — the curated document"):
                        self.JS.index("PART 2: SHARING")]
        for forbidden in ("fetch(", "XMLHttpRequest", "sendBeacon", "/api/",
                          "askStudio", "API_TIMEOUT", "document.cookie",
                          "new Image("):
            self.assertNotIn(forbidden, block,
                             f"the paper's make path reached for {forbidden!r} "
                             f"— composing must not touch a server (specs/21 §5)")
        # and the draft is localStorage, the same private preference the mode is
        self.assertIn("localStorage.setItem(PAPERS_KEY", block)

    def test_the_paper_markers_are_present(self):
        """The drift guard, extended: the pieces the stylesheet, the stub and
        the studio panel lean on keep their names."""
        for token in ("function paper(", 'const PAPER_KEY = "cz-paper"',
                      "function refreshPaperSummary(",
                      "function paperShortLink(", "function decodePaper(",
                      'test(path)) paper()',
                      # P3: the templates and the featured papers' hide hook
                      "function applyPaperTemplate(", 'data-cz="ptpl"',
                      '$("#pfeat")',
                      # specs/23 A2/A3: adds by ref, the card affordances,
                      # the on-page editor and its hash door
                      "function addStoryRef(", "function removeStoryRef(",
                      "function paintMakeAffordances(", "function wireEditor(",
                      "function lexRank(", "function moveBlock(",
                      "function insertBlock(", "function paperTeach(",
                      'hp.has("edit")', 'hp.get("tpl")', "cz-edrow",
                      "restoreEdFocus(el, PAGE_FOCUS || keep)",
                      # C1: the shelf and the layouts
                      'const PAPERS_KEY = "cz-papers"', "function readPapers(",
                      "function newPaper(", "function switchPaper(", "function deletePaper(",
                      'data-cz="pnew"', 'data-cz="pdelete"', "function paintLayouts(",
                      "function renderHead(", "function setBlockLayout(", "cz-edlayout",
                      # C2: the three ref kinds, their renders and adds, the
                      # lines search over the static index, the print sheet
                      "function renderQuote(", "function renderDoc(", "function renderDigest(",
                      "function addQuoteRef(", "function addDocRef(", "function addDigestRef(",
                      "function linesSearch(", "function docChooser(", "function segLines(",
                      'data-cz="pquote"',
                      "const PAPER_VS = [\"1\", \"2\", \"3\"]"):
            self.assertIn(token, self.JS, f"{token!r} drifted in app.js")


class TestStudioFootprint(unittest.TestCase):
    """specs/21 P0: the studio's mode state is the reader's own — localStorage and
    nothing else, defaulting to preview, validated on the way in, and NEVER a
    server call. Lifted from app.js and executed in node, the same treatment
    resolve() and decodeReel() get, and for the same reason."""

    JS = (REPO / "web" / "static" / "app.js").read_text()

    def node(self, body):
        import shutil
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        return subprocess.run([node, "-e", body], capture_output=True, text=True)

    def lift(self, pattern):
        m = re.search(pattern, self.JS, re.S)
        self.assertTrue(m, f"{pattern!r} not found in the reader — did it move?")
        return m.group(0)

    def test_read_mode_defaults_to_preview_and_validates(self):
        """Absent, empty, or unknown → preview (the quiet default the resident
        gets). Only an exact one of the three modes is honoured — no coercion, so
        a corrupted value can never silently open the loud studio."""
        cases = [
            [None, "preview"], ["preview", "preview"], ["studio", "studio"],
            ["paper", "paper"], ["", "preview"], ["cockpit", "preview"],
            ["STUDIO", "preview"], [" studio", "preview"],
        ]
        body = "\n".join([
            "let STORE = null;",
            "const localStorage = { getItem: () => STORE };",
            self.lift(r'const MODE_KEY = .+?;'),
            self.lift(r"const MODES = .+?;"),
            self.lift(r'const readMode = .+?catch \{ return "preview"; \} \};'),
            "const CASES = " + json.dumps(cases) + ";",
            "let bad = 0;",
            "for (const [stored, want] of CASES) {",
            "  STORE = stored;",
            "  const got = readMode();",
            "  if (got !== want) { console.log('FAIL', JSON.stringify(stored), '->', got, 'want', want); bad++; }",
            "}",
            "process.exit(bad ? 1 : 0);",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"readMode is wrong:\n{r.stdout}{r.stderr}")

    def test_the_studio_path_touches_no_server(self):
        """The make path stays client-only: the studio's own functions read and
        write localStorage and compose pure links, and never reach a network —
        the covenant, and a test that proves it (specs/21 §5)."""
        block = self.JS[self.JS.index("THE STUDIO — the three-mode footprint"):
                        self.JS.index("SCOPE: the town")]
        for forbidden in ("fetch(", "XMLHttpRequest", "sendBeacon", "/api/",
                          "askStudio", "document.cookie", "new Image("):
            self.assertNotIn(forbidden, block,
                             f"the studio reached for {forbidden!r} — the make "
                             f"path must never touch a server (specs/21 §5)")
        # the mode is stored in localStorage, the same private preference the town
        # scope keeps — no cookie, no account, no sync
        self.assertIn("localStorage.setItem(MODE_KEY", block)

    def test_the_studio_markers_are_present(self):
        """A cheap drift guard: the pieces the stylesheet and the P0 contract lean
        on are present under their expected names."""
        for token in ("function initStudio(", "function markMode(",
                      'classList.toggle("cz-m-"', 'const MODE_KEY = "cz-studio-mode"',
                      "function refreshReelSummary(", "function setMode("):
            self.assertIn(token, self.JS, f"{token!r} drifted in app.js")

    def test_the_mode_control_is_a_radiogroup_with_roving_tabindex(self):
        """specs/21 P3's a11y contract: the mode control is one choice of
        three — role=radiogroup on the group, role=radio + aria-checked on
        each button, a roving tabindex (the checked radio is the group's one
        tab stop), and arrow keys that move the choice. aria-pressed leaves
        the studio block entirely (the reel tick elsewhere keeps its own —
        that one really is a toggle)."""
        for token in ('role="radiogroup"', 'role="radio"', "aria-checked",
                      "b.tabIndex = on ? 0 : -1",
                      "ArrowLeft", "ArrowRight", "ArrowUp", "ArrowDown",
                      '"Home"', '"End"'):
            self.assertIn(token, self.JS,
                          f"{token!r} missing from the mode control")
        studio_block = self.JS[
            self.JS.index("THE STUDIO — the three-mode footprint"):
            self.JS.index("SCOPE: the town")]
        self.assertNotIn("aria-pressed", studio_block,
                         "the mode control still speaks aria-pressed — a "
                         "radio is checked, not pressed")
        # the stylesheet must move WITH the attribute: the checked-state fill
        # keyed on [aria-pressed] shipped orphaned once (the P3 review's HIGH
        # — every mode radio painted identical), so pin the pair here
        css = (REPO / "web" / "static" / "app.web.css").read_text()
        self.assertIn('.cz-mode[aria-checked="true"]', css,
                      "the checked radio has no selected-state style")
        self.assertNotIn('.cz-mode[aria-pressed', css,
                         "a checked-state rule still keys on aria-pressed — "
                         "it can never match the radio the JS paints")

    def test_the_pill_says_the_thing_itself_and_the_cards_never_paint_in_paper_mode(self):
        """specs/23 A2/A4: the preview pill names the product's second half
        ("✎ Your paper — edit", not a room to enter), and the card
        affordances are gated on the PAINTED mode — removed from the page
        in paper mode by the JS, and hidden by the stylesheet as a belt, so
        the resident who hid the studio sees exactly the specs/20 paper."""
        self.assertIn("✎ Your paper — edit", self.JS)
        self.assertNotIn("Enter the studio", self.JS)
        block = self.JS[self.JS.index("function paintMakeAffordances("):
                        self.JS.index("function pageStoryRef(")]
        self.assertIn('const hide = shownMode() === "paper";', block)
        self.assertIn("b.hidden = hide;", block)
        # a card is wrapped, never nested: no button inside the <a>
        self.assertIn("card.replaceWith(wrap); wrap.appendChild(card);", block)
        css = (REPO / "web" / "static" / "app.web.css").read_text()
        self.assertIn("html.cz-m-paper .cz-mk{display:none}", css)
        # the affordance wears the paper palette (deep green), not the studio's
        mk = css[css.index(".cz-mk{"):css.index(".tnode .thead .cz-mk")]
        self.assertNotIn("studio", mk)
        self.assertIn("var(--accent)", mk)
        # the scope filter hides the row WITH the card it wraps
        self.assertIn('if (w && w.classList.contains("cz-mkwrap")) w.hidden = !ok;', self.JS)

    def test_the_control_speaks_about_the_painted_mode_not_the_stored_one(self):
        """The fold's fix: in a storage-blocked browser readMode() answers
        "preview" while the page visibly sits in the studio (markMode painted
        the class; writeMode's refused write was swallowed). shownMode() —
        what updateModeButtons and the arrow keys read — derives from the
        painted class first, storage second."""
        body = "\n".join([
            "const MODES = ['preview', 'studio', 'paper'];",
            "const readMode = () => 'preview';",
            "const cls = new Set(['cz-m-studio']);",
            "const document = { documentElement: { classList: { contains: c => cls.has(c) } } };",
            self.lift(r"const shownMode = .+?readMode\(\);"),
            "if (shownMode() !== 'studio') { console.log('FAIL painted', shownMode()); process.exit(1); }",
            "cls.clear();",
            "if (shownMode() !== 'preview') { console.log('FAIL fallback', shownMode()); process.exit(1); }",
            "console.log('ok');",
        ])
        r = self.node(body)
        self.assertEqual(r.returncode, 0,
                         f"shownMode reads the wrong truth:\n{r.stdout}{r.stderr}")
        # …and the CALL SITES are the fix (the re-review's catch: a revert to
        # readMode() at any of them would lie again while this test stayed
        # green). All four painted-truth consumers, pinned by token:
        for token in ("const m = shownMode();",          # updateModeButtons
                      "MODES.indexOf(shownMode())",      # the arrow keys
                      "const v = !shownRail();",         # toggleRail's next state
                      'shownMode() === "studio" && v',   # toggleRail's gate
                      "const railed = shownRail();"):    # the handle's glyph
            self.assertIn(token, self.JS,
                          f"{token!r} left the painted truth — a control may "
                          "be describing storage again")


class TestReviewFoldTwins(unittest.TestCase):
    """The second review of v2.1.15's fold — three lenses, two skeptics on
    every finding, thirteen findings, none refuted, all folded. These twins
    EXECUTE the fixes: a token pin can survive a revert (the lenses' own
    catch — the editor's pair marks, the print twins, the engines' partial
    reverts all passed the suite on tokens alone)."""

    JS = (REPO / "web" / "static" / "app.js").read_text()
    ESC = ('const esc = s => String(s == null ? "" : s).replace(/[&<>"]/g, '
           "c => ({\"&\": \"&amp;\", \"<\": \"&lt;\", \">\": \"&gt;\", '\"': \"&quot;\"})[c]);")

    def node(self, body):
        import shutil
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        return subprocess.run([node, "-e", body], capture_output=True, text=True)

    def lift(self, pattern):
        m = re.search(pattern, self.JS, re.S)
        self.assertTrue(m, f"{pattern!r} not found in the reader — did it move?")
        return m.group(0)

    def ok(self, r):
        self.assertEqual(r.stdout.strip(), "ok", r.stdout + r.stderr)

    # -- L1-1: the pair mark, at the call site ------------------------------
    def test_the_editor_marks_exactly_the_pairs_the_reader_pairs_at_the_call_site(self):
        """halfPairs had a twin; the statement that USES it did not — marking
        every half (the v2.1.14 bug) or an off-by-one passed the suite."""
        self.ok(self.node("\n".join([
            "const edSlot = i => ''; const withLayoutHTML = h => h;",
            "const renderPaperBlock = () => 'b'; const paperGone = () => 'g';",
            "const edRow = (html, b, i, n, pair) => pair ? 'P' : 'x';",
            "const mby = {}, iby = {}, tried = {}, aux = {};",
            self.lift(r"  const halfPairs = blocks => \{.+?return s; \};"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const L = s => s.split('').map(c => ({ kind: 'note', layout: c === 'h' ? 'half' : '' }));",
            "function rowsOf(s) { const doc = { blocks: L(s) }; const n = doc.blocks.length;",
            self.lift(r'      const paired = halfPairs\(doc\.blocks\);\n      const rows = doc\.blocks\.map\(.+?\.join\(""\) \+ edSlot\(n\);'),
            "  return rows; }",
            "if (rowsOf('hhh') !== 'PPx') fail('three halves: the first two pair, the third stands alone — got ' + rowsOf('hhh'));",
            "if (rowsOf('.h') !== 'xx') fail('a lone half is not marked — got ' + rowsOf('.h'));",
            "if (rowsOf('.hh.hh') !== 'xPPxPP') fail('pairs anywhere — got ' + rowsOf('.hh.hh'));",
            "console.log('ok');"])))

    # -- L1-2 + L1-5: the print twins run ------------------------------------
    def test_the_print_twins_execute(self):
        """notePrint escapes before the innerHTML write and splits paragraphs;
        the beforeprint body re-reads the live fields; an untitled draft
        prints what the reader's page prints for it."""
        self.ok(self.node("\n".join([
            self.ESC,
            "const PAPER_TITLE_MAX = 200; const cut = (s, n) => String(s).slice(0, n); const noteText = s => String(s).trim();",
            self.lift(r"  const notePrint = [^\n]+\n"),
            self.lift(r"  const printTitle = [^\n]+\n"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const np = notePrint('<script>alert(1)</script>\\n\\nsecond & third');",
            "if (np !== '<p>&lt;script&gt;alert(1)&lt;/script&gt;</p><p>second &amp; third</p>') fail('escaped, and split on blank lines: ' + np);",
            "if (printTitle('') !== 'Untitled paper' || printTitle('  ') !== 'Untitled paper' || printTitle('A') !== 'A') fail('an untitled draft prints Untitled paper');",
            "const NOTE = { value: 'typed since <render>', parentElement: {} }; const NTW = { innerHTML: 'stale' };",
            "const TI = { value: 'x'.repeat(300) }; const TTW = { textContent: 'stale' };",
            "const el = { isConnected: true }; let HOOK = null;",
            "const $$ = (sel, root) => sel === '.cz-ednote' ? [NOTE] : [];",
            "const $ = (sel, root) => sel === '.cz-ednote-print' && root === NOTE.parentElement ? NTW : sel === '.cz-edtitle' ? TI : sel === '.cz-edtitle-print' ? TTW : null;",
            "const window = { addEventListener: (ev, fn) => { HOOK = fn; fn(); } };",
            self.lift(r'    window\.addEventListener\("beforeprint", \(\) => \{\n.+?\n    \}\);'),
            "if (NTW.innerHTML !== notePrint(noteText(NOTE.value)) || !NTW.innerHTML.includes('&lt;render&gt;')) fail('the note twin re-reads the live field on beforeprint: ' + NTW.innerHTML);",
            "if (TTW.textContent !== 'x'.repeat(200)) fail('the title twin re-reads the live field, capped: ' + TTW.textContent.length);",
            "TI.value = '   '; HOOK(); if (TTW.textContent !== 'Untitled paper') fail('an untitled draft prints Untitled paper on beforeprint too');",
            "el.isConnected = false; NTW.innerHTML = 'left'; NOTE.value = 'changed'; HOOK(); if (NTW.innerHTML !== 'left') fail('a detached editor is left alone');",
            "console.log('ok');"])))

    # -- L2-1 + L2-3: the lines search -----------------------------------------
    def test_a_query_holding_constructor_neither_throws_nor_strands_the_line(self):
        """`sh[t]` on a plain object read Object.prototype.constructor for the
        one word that survives lexTerms' lowercase; new Set(Object) threw;
        the add-search and the search page were left on "searching…"."""
        self.assertEqual(self.JS.count("Object.prototype.hasOwnProperty.call(sh, t)"), 2,
                         "the own-postings guard belongs at both shard lookups")
        self.ok(self.node("\n".join([
            "const BASE = '/app';",
            "const getJSON = async u => u.endsWith('meta.json') ? [] : u.endsWith('segs.json') ? [] : { contractor: [1] };",
            self.lift(r"  async function linesSearch\(terms, q\) \{.+?\n  \}"),
            "(async () => {",
            "  let out; try { out = await linesSearch(['constructor'], 'the constructor bid'); }",
            "  catch (e) { console.log('FAIL threw ' + e.message); process.exit(1); }",
            "  if (!Array.isArray(out) || out.length) { console.log('FAIL not an empty answer'); process.exit(1); }",
            "  const own = await linesSearch(['contractor'], 'contractor');",
            "  if (!Array.isArray(own)) { console.log('FAIL own postings must still read'); process.exit(1); }",
            "  console.log('ok');",
            "})();"])))
        # a broken lines search is said, never painted as "no match"; the
        # lines gate is one predicate for the status line, the wait, the body
        for token in ("try { ls = await linesSearch(terms, q.value); } catch { broke = true; }",
                      "const linesOK = terms.length > 0 && q.value.trim().length >= 3;",
                      "if (!linesOK) { if (!ms.length && !is.length) box.innerHTML = nothing(false); return; }",
                      "the tape’s lines couldn’t be read"):
            self.assertIn(token, self.JS, token)

    # -- L3-2 + L3-4: the load's forgetting, the hold a second press releases --
    def engine(self, extra):
        return "\n".join([
            "const WIN = {}, EL = {}, ELSE = {};",
            "const document = { activeElement: ELSE };",
            "let SENT = [], SEEKS = [], CALLS = [];",
            "const ytSend = (k, f, a) => SENT.push(k === 'listening' ? ['listening'] : [f, a]);",
            "const sent = f => SENT.filter(x => x[0] === f);",
            "const ytSeek = t => SEEKS.push(t); const pvPause = () => CALLS.push('pvPause');",
            "const reelShow = () => CALLS.push('reelShow'); const reelNext = () => CALLS.push('reelNext');",
            "const followAlong = () => {}, strip = () => {}, tick = () => {}, reelAdvance = () => {};",
            "const PV = { clip: null, free: false };",
            "let REELPLAY, YT;",
            self.lift(r"  const inFrame = [^\n]+"),
            self.lift(r"  function reelSeek\(c\) \{.+?\n  \}"),
            self.lift(r"  function onYT\(e\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m, JSON.stringify({ SENT, SEEKS, CALLS, YT, REELPLAY })); process.exit(1); }",
            "const ev = d => ({ source: WIN, origin: 'https://www.youtube-nocookie.com', data: JSON.stringify(d) });",
            extra, "console.log('ok');"])

    def test_a_second_press_on_the_stashed_meeting_releases_a_hold_set_between(self):
        self.assertNotIn('if (typeof YT !== "undefined") { YT.hold = false; YT.pending = null; }', self.JS,
                         "the stash branch's dead YT.pending = null is gone")
        self.ok(self.node(self.engine("\n".join([
            "YT = { win: WIN, el: EL, vid: 'v1', loaded: true, ready: false, time: 0, pending: 10, hold: false, state: -2 };",
            "REELPLAY = { vid: 'v1', pending: null, clips: [], settling: false };",
            "reelSeek({ video_id: 'v2', start: 300 });",
            "YT.hold = true;                       // the stage spoke between the two presses",
            "reelSeek({ video_id: 'v2', start: 100 });",
            "if (YT.hold) fail('the reader asked the page for a tape: the hold is released');",
            "onYT(ev({ event: 'initialDelivery', info: { playerState: -1 } })); onYT(ev({ event: 'onReady' }));",
            "const l = sent('loadVideoById');",
            "if (l.length !== 1 || l[0][1][0].startSeconds !== 100 || sent('cueVideoById').length) fail('unheld, the last press LOADS — it is not cued');",
            "if (YT.state !== -1) fail('the onReady load forgets the old tape’s rest: state -1');"]))))
        # (YT.time is set beside it and overwritten by the same message's own
        # currentTime a few lines on — the state is what the hold reads)

    def test_a_load_in_flight_forgets_the_old_tapes_rest_and_time(self):
        self.ok(self.node(self.engine("\n".join([
            "YT = { win: WIN, el: EL, vid: 'v1', loaded: true, ready: true, time: 1500, pending: null, hold: false, state: 2 };",
            "REELPLAY = { vid: 'v1', pending: null, clips: [], settling: false };",
            "reelSeek({ video_id: 'v2', start: 300 });",
            "if (sent('loadVideoById').length !== 1) fail('a cross-meeting cite loads the tape');",
            "if (YT.state !== -1) fail('a load in flight is not a seen silence: state is -1, not the old rest');",
            "if (YT.time !== 300) fail('the old tape’s time is forgotten: time = the clip start');"]))))
        self.assertIn("PV.state = -1;   // a load in flight is not a seen silence", self.JS)

    # -- L3-1: the resume branch waits out the settling beat -----------------------
    def test_the_page_frame_resume_waits_out_the_settling_beat(self):
        self.ok(self.node(self.engine("\n".join([
            "function start(settling, time) {",
            "  YT = { win: WIN, el: EL, vid: 'v2', loaded: true, ready: true, time: 0, pending: null, hold: false, state: 2 };",
            "  REELPLAY = { vid: 'v2', pending: null, paused: true, active: false, armed: false, i: 1, settling,",
            "               clips: [{ video_id: 'v1', start: 40, end: 60 }, { video_id: 'v2', start: 300, end: 320 }] };",
            "  SENT = []; SEEKS = []; CALLS = [];",
            "  onYT(ev({ event: 'infoDelivery', info: { playerState: 1, currentTime: time } }));",
            "}",
            "start(true, 1500);   // the swapped-out tape's time, inside the beat",
            "if (CALLS.includes('reelNext') || SEEKS.length || sent('loadVideoById').length) fail('settling: the reel resumes in place — no advance, no seek');",
            "if (!CALLS.includes('reelShow') || !REELPLAY.active || REELPLAY.paused) fail('settling: the reel is back on, painted');",
            "start(false, 319.95);",
            "if (!CALLS.includes('reelNext')) fail('settled, at the clip’s end: on to the next clip');",
            "start(false, 9);",
            "if (!SEEKS.includes(300)) fail('settled, before the clip: from its start');",
            "start(false, 310);",
            "if (SEEKS.length || CALLS.includes('reelNext')) fail('settled, inside the clip: on from where the frame stands');"]))))

    # -- L3-3: a trim reaches the clip a stop left behind, and repaints ------------
    def test_a_trim_reaches_the_pending_clip_and_the_one_a_stop_left_behind(self):
        self.ok(self.node("\n".join([
            "const clipKey = c => c.pid + '|' + c.kind + '|' + c.t; let SHOWN = 0; const pvShow = () => SHOWN++;",
            "let PV;",
            self.lift(r"  function pvRetrim\(clips\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m, JSON.stringify(PV)); process.exit(1); }",
            "const A = { pid: 'p1', kind: 'vote', t: 100, start: 100, end: 110 };",
            "PV = { clip: A, pending: A, last: null }; pvRetrim([{ ...A, start: 95 }]);",
            "if (PV.pending.start !== 95 || PV.clip.start !== 95 || SHOWN !== 1) fail('a clip still loading follows the trim, and the stage repaints');",
            "PV = { clip: null, pending: null, last: A }; SHOWN = 0; pvRetrim([{ ...A, start: 96 }]);",
            "if (PV.last.start !== 96 || SHOWN !== 1) fail('the clip a stop left behind follows the trim, and the link repaints');",
            "SHOWN = 0; pvRetrim([{ ...A, start: 96 }]);",
            "if (SHOWN !== 0) fail('an unchanged clip repaints nothing');",
            "console.log('ok');"])))

    # -- the re-review's coverage gaps: the digest order, the chooser's re-ask --
    def test_the_all_undated_digest_paints_latest_added_first_and_says_so(self):
        self.ok(self.node("\n".join([
            self.ESC,
            "const BASE = '/app'; const paperGone = w => 'GONE:' + w; const paperBudget = w => 'BUDGET:' + w;",
            self.lift(r"  function renderDigest\(b, iby, tried\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "const iby = { z: { name: 'zoning', timeline: [{ pid: 'a', body: 'B' }, { pid: 'b', body: 'B' }, { pid: 'c', body: 'B' }] } };",
            "const out = renderDigest({ kind: 'digest', slug: 'z', n: 2 }, iby, { i: new Set() });",
            "const pids = [...out.matchAll(/href=\"\\/app\\/m\\/([a-z])\"/g)].map(m => m[1]);",
            "if (pids.join() !== 'c,b') fail('the timeline’s last two, latest-added first — got ' + pids.join());",
            "if (!out.includes('latest-added first')) fail('the sentence says what is painted');",
            "if (!out.includes('2 undated appearances')) fail('the kicker counts them as undated');",
            "console.log('ok');"])))

    def test_the_document_chooser_re_asks_once_only_for_a_cached_null(self):
        """A null the paper's own render cached is not this press's answer:
        one re-ask, only then; a fresh failure costs one fetch; a cached
        good answer costs none; the retry after a failure fetches again."""
        self.ok(self.node("\n".join([
            "const BASE = '/app';", self.ESC,
            "const cut = (s, n) => String(s).slice(0, n);",
            "let FETCHES = 0, ANSWER = null;",
            "const fetch = async u => { FETCHES++; return ANSWER ? { ok: true, json: async () => ANSWER } : { ok: false }; };",
            self.lift(r"  const _cache = \{\};\n"),
            self.lift(r"  const getJSON = [^\n]+\n"),
            "const document = { createElement: () => ({ className: '', innerHTML: '' }) };",
            "const $ = () => null;",
            "const mkBtn = () => ({ isConnected: true, closest: () => null, replaced: null, replaceWith(s) { this.replaced = s; } });",
            self.lift(r"  async function docChooser\(btn, pid\) \{.+?\n  \}"),
            "function fail(m){ console.log('FAIL', m); process.exit(1); }",
            "(async () => {",
            "  const url = BASE + '/meetings/p1.json';",
            "  FETCHES = 0; ANSWER = null; let b = mkBtn(); await docChooser(b, 'p1');",
            "  if (FETCHES !== 1 || !b.replaced.innerHTML.includes('didn’t load') || url in _cache) fail('a fresh failure: one fetch, didn’t load, nothing kept');",
            "  FETCHES = 0; b = mkBtn(); await docChooser(b, 'p1'); if (FETCHES !== 1) fail('the retry fetches again, once');",
            "  delete _cache[url]; ANSWER = null; await getJSON(url); FETCHES = 0; ANSWER = { documents: [{ doc_id: 'd1', kind: 'agenda', title: 'T' }] };",
            "  b = mkBtn(); await docChooser(b, 'p1');",
            "  if (FETCHES !== 1 || !b.replaced.innerHTML.includes('agenda')) fail('a cached null: one re-ask, and the documents paint');",
            "  FETCHES = 0; b = mkBtn(); await docChooser(b, 'p1'); if (FETCHES !== 0) fail('a cached good answer costs no fetch');",
            "  delete _cache[url]; ANSWER = null; await getJSON(url); FETCHES = 0; b = mkBtn(); await docChooser(b, 'p1');",
            "  if (FETCHES !== 1 || !b.replaced.innerHTML.includes('didn’t load') || url in _cache) fail('a cached null whose re-ask fails: one fetch, didn’t load, nothing kept');",
            "  console.log('ok');",
            "})();"])))
