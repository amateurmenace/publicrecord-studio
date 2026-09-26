"""The week in the record (v2.2.11): a calendar week of the record's
meetings, Monday to Sunday, counted into a page of its own at its Monday's
address — the meetings, what was decided, the sums named, the threads that
moved, how the week talked — with /app/week/ the latest, a feed with an
item per week, and the front page's week linking to it. Counted, never a
model's; nothing stored."""

import re
import shutil
import tempfile
import unittest
from pathlib import Path

from tests import test_web_bake   # the module, not the class: its tests are its own to run
from web import emit, week

REPO = Path(__file__).resolve().parents[1]
CSS = (REPO / "web" / "static" / "app.web.css").read_text()
MANIFEST = {"version": "9", "corpus_hash": "x", "edition_date": "2026-09-24", "counts": {}, "schema": 1}


def _m(pid, date, town="Brookline", body="Select Board", dur=3600.0, votes=(), moments=(), money=(), lenses=()):
    return {"pid": pid, "id": pid, "date": date, "town": town, "body": body, "title": f"{body} — {date}",
            "duration": dur, "votes": list(votes), "moments": list(moments), "still": "",
            "analysis": {"entities": {"money": list(money)}, "framing": {"total": sum(c for _, c in lenses),
                         "lenses": [{"lens": l, "count": c, "drift": "steady"} for l, c in lenses]}}}


class TestTheWeek(unittest.TestCase):
    def test_a_week_is_monday_to_sunday_by_the_meetings_own_dates(self):
        self.assertEqual(week.monday_of("2026-09-21"), "2026-09-21")          # a Monday
        self.assertEqual(week.monday_of("2026-09-27"), "2026-09-21")          # its Sunday
        self.assertEqual(week.monday_of("2026-09-28"), "2026-09-28")          # the next Monday
        self.assertEqual(week.monday_of("2026-01-01"), "2025-12-29")          # a week across the year
        for bad in ("", None, "2026-02-30", "soon", "2026-9-1"):
            self.assertIsNone(week.monday_of(bad), bad)                          # undated is no week, never a crash
        ms = [_m("a", "2026-09-22"), _m("b", "2026-09-27"), _m("c", "2026-09-14"), _m("d", ""), _m("e", "2026-02-30")]
        self.assertEqual(week.weeks(ms), ["2026-09-21", "2026-09-14"])

    def test_a_week_is_counted_from_what_the_press_already_builds(self):
        ms = [_m("a", "2026-09-22", votes=[{"t": 30.0, "motion": "move to adopt the budget", "outcome": "passes", "tally": "5-0-0"}],
                 moments=[{"t": 30.0, "kind": "vote", "quote": "all in favor", "score": 0.9},
                          {"t": 90.0, "kind": "decision", "quote": "so moved", "score": 0.4},
                          {"t": 120.0, "kind": "tension", "quote": "I object", "score": 0.8},
                          {"t": 150.0, "kind": "question", "quote": "why?", "score": 0.99}],
                 money=[{"name": "$5 million", "t": 40.0, "count": 1}, {"name": "$146,000", "t": 50.0, "count": 3},
                        {"name": "$50.", "t": 70.0, "count": 1}, {"name": "$50", "t": 60.0, "count": 2}],
                 lenses=[("financial", 60), ("community", 40)]),
              _m("b", "2026-09-24", town="Boston", body="City Council", dur=7200.0, money=[{"name": "$2 MILLION", "t": 10.0, "count": 2}],
                 lenses=[("community", 90), ("financial", 10)]),
              _m("c", "2026-09-14", lenses=[("financial", 10), ("safety", 90)])]
        bk = lambda pid, n: {"pid": pid, "town": "Brookline", "beads": [{"t": i} for i in range(n)]}
        issues = [{"slug": "issue_brookline_budget", "name": "Budget", "name_origin": "ai:gpt-4o-mini", "timeline": [bk("a", 2), bk("c", 1)]},
                  {"slug": "issue_brookline_parking", "name": "Parking", "name_origin": "keywords", "timeline": [bk("a", 1), bk("b", 3)]},
                  {"slug": "issue_brookline_elsewhere", "name": "Elsewhere", "timeline": [bk("c", 1)]}, "junk"]
        import datetime as dt
        d = week.week_data("2026-09-21", ms, issues, today=dt.date(2026, 9, 28))
        self.assertEqual([m["pid"] for m in d["meetings"]], ["a", "b"])
        self.assertEqual(d["seconds"], 10800.0)
        self.assertEqual(d["towns"], ["Boston", "Brookline"])
        self.assertEqual([(r["motion"], r["outcome"], r["tally"]) for r in d["rolls"]], [("move to adopt the budget", "passes", "5-0-0")])
        self.assertEqual([x["kind"] for x in d["decisions"]], ["tension", "decision"])     # loudest first; no vote, no question
        # "$50" and "$50." are one sum said three times, from its first saying (a review's catch)
        self.assertEqual([(s["label"], s["count"]) for s in d["sums"]], [("$146,000", 3), ("$50", 3), ("$2 million", 2), ("$5 million", 1)])
        self.assertEqual([s["t"] for s in d["sums"] if s["label"] == "$50"], [60.0])
        self.assertEqual([(t["name"], t["moments"], t["week"], t["all"], t["model"]) for t in d["threads"]],
                         [("Parking", 4, 2, 2, ""), ("Budget", 2, 1, 2, "gpt-4o-mini")])
        self.assertFalse(d["so_far"])                                              # the press ran after its Sunday
        self.assertTrue(week.week_data("2026-09-21", ms, issues, today=dt.date(2026, 9, 27))["so_far"])   # on its Sunday: still going
        lz = d["lens"]
        self.assertEqual((lz["loudest"], round(lz["loudest_week"], 3)), ("community", round(130 / 200, 3)))
        self.assertEqual(lz["words"], 200)
        self.assertEqual((d["newer"], d["older"]), (None, "2026-09-14"))
        self.assertEqual(week.week_data("2026-09-14", ms, issues)["newer"], "2026-09-21")
        # a week of towns whose threads the record does not follow says whose it follows, not that nothing moved
        boston = week.week_data("2026-09-28", [_m("x", "2026-09-29", town="Boston", body="City Council")], issues, today=dt.date(2026, 10, 9))
        self.assertIn("The threads the record follows are Brookline’s; this week’s meetings were Boston’s.",
                      emit.page_week(boston, {"2026-09-28": 1}, MANIFEST, "https://example.org"))
        self.assertIsNone(week.week_data("2026-09-14", [_m("z", "2026-09-15")], [])["lens"])       # nothing framed, nothing claimed
        # the page: every part, every number a link into the tape; nothing of the studio
        counts = {"2026-09-21": 2, "2026-09-14": 1}
        page = emit.page_week(d, counts, MANIFEST, "https://example.org")
        self.assertIn("<h1 class=\"wk-title\">The week of September 21, 2026</h1>", page)
        self.assertIn("Two meetings, three hours of tape, in Boston and Brookline.", page)
        self.assertIn('href="/app/m/a#t30"', page)                               # the roll call opens its tape
        self.assertIn(">passed 5-0-0<", page)
        self.assertIn("<b class=\"wk-sum\">$146,000</b>", page)
        self.assertIn('href="/app/i/issue_brookline_parking"><b>Parking</b>', page)
        self.assertIn("4 moments filed under it this week, in 2 of its 2 meetings · 2 meetings on the record", page)
        # each thread says who named it, as its page does: the model's Budget, not the keywords' Parking (a re-review's catch)
        self.assertIn('<b>Budget</b><span class="wk-origin">named by a model</span>', page)
        self.assertIn('<b>Parking</b><span class="wk-when">', page)
        self.assertIn("no model counted any of it; a thread a model named says so", page)
        self.assertNotIn("no model wrote a word", page)
        keywords_only = emit.page_week(week.week_data("2026-09-21", ms, [issues[1]], today=dt.date(2026, 9, 28)), counts, MANIFEST, "https://example.org")
        self.assertNotIn("named by a model", keywords_only)                    # no model's name listed, no claim of one
        self.assertNotIn("a thread a model named", keywords_only)
        # an untowned week never says "were ’s"
        untowned = week.week_data("2026-10-05", [_m("u", "2026-10-06", town="")], issues, today=dt.date(2026, 10, 20))
        self.assertIn("No thread the record follows came up this week.", emit.page_week(untowned, {"2026-10-05": 1}, MANIFEST, "https://example.org"))
        self.assertEqual(page.count('<nav class="wk-nav"'), 1)                   # one landmark for the weeks around it
        so_far = emit.page_week(week.week_data("2026-09-21", ms, issues, today=dt.date(2026, 9, 23)), counts, MANIFEST, "https://example.org")
        self.assertIn("the week in the record — so far", so_far)
        self.assertIn("Two meetings so far, three hours of tape", so_far)
        self.assertIn('href="/app/week/2026-09-14/" rel="prev"', page)
        self.assertIn('<link rel="canonical" href="https://example.org/app/week/2026-09-21/">', page)
        self.assertIn('href="/app/feeds/week.xml"', page)
        self.assertNotIn("cz-", page.split("<main", 1)[1].split("</main>", 1)[0])  # no studio markup in the week's pressed bytes
        for hue in ("#a855f7", "#7c3aed", "#22c55e", "fuchsia"):
            self.assertNotIn(hue, page)
        self.assertIn('aria-current="page">September 21, 2026', page)

    def test_the_press_presses_every_week_the_latest_and_the_feed(self):
        d = Path(tempfile.mkdtemp())
        try:
            db = d / "c.db"
            test_web_bake.TestBakeEdition._seed(db)
            from web import bake
            import datetime as dt
            import json
            # the press's day falls inside the latest week: that week is still going
            bake.bake(str(db), str(d / "app"), "9.9.9", "https://example.org", today=dt.date(2026, 6, 19))
            out = d / "app"
            meta = json.loads((out / "search" / "meta.json").read_text())
            ks = week.weeks(meta)
            self.assertEqual(ks, ["2026-06-15", "2026-03-09"])
            for k in ks:
                self.assertTrue((out / "week" / k / "index.html").exists(), k)
            self.assertEqual((out / "week" / "index.html").read_text(), (out / "week" / ks[0] / "index.html").read_text())
            feed = (out / "feeds" / "week.xml").read_text()
            # an item a FINISHED week: the week still going is on its page, not in the feed (a review's catch)
            self.assertEqual(re.findall(r"<link>(https://example.org/app/week/[^<]+)</link>", feed), ["https://example.org/app/week/2026-03-09/"])
            home = (out / "index.html").read_text()
            self.assertIn('<a href="/app/week/2026-06-15/">The week of June 15, 2026 — 1 meeting so far — in the record:', home)
            self.assertIn('<p class="wk-link" data-scope="[[&quot;', home)                  # its meetings' town and body, for the scope
            # the worker's key carries the week still going; the night it ends, the key changes (a re-review's catch)
            manifest = json.loads((out / "manifest.json").read_text())
            self.assertEqual(manifest["week_state"], "w20260615")
            self.assertIn("-w20260615", (out / "sw.js").read_text())
            after = d / "after"
            bake.bake(str(db), str(after), "9.9.9", "https://example.org", today=dt.date(2026, 6, 22))
            self.assertNotIn("week_state", json.loads((after / "manifest.json").read_text()))
            self.assertNotIn("-w2026", (after / "sw.js").read_text())
            self.assertIn("so far", (out / "week" / "index.html").read_text())
            self.assertNotIn("so far", (after / "week" / "index.html").read_text())
            self.assertEqual(re.findall(r"<link>(https://example.org/app/week/[^<]+)</link>", (after / "feeds" / "week.xml").read_text()),
                             ["https://example.org/app/week/2026-06-15/", "https://example.org/app/week/2026-03-09/"])
            # and a press is still a function of its corpus and its day: the same day presses the same bytes
            again = d / "again"
            bake.bake(str(db), str(again), "9.9.9", "https://example.org", today=dt.date(2026, 6, 22))
            for rel in ("week/index.html", "week/2026-06-15/index.html", "feeds/week.xml", "sw.js", "index.html"):
                self.assertEqual((after / rel).read_bytes(), (again / rel).read_bytes(), rel)
        finally:
            shutil.rmtree(d, ignore_errors=True)

    def test_a_wrapped_week_card_keeps_its_last_lines(self):
        """The studio wraps a card in a column; the card's 250 px basis — a width
        in the week's row — was its height in the column, and cut its last lines
        (11–59 px on the live front page). The wrap takes the width now."""
        studio = CSS[:CSS.index("THE CIVIC BROADSHEET")]                     # the studio's own rules, before the broadsheet's
        for rule in (".bs-weekrow>.cz-mkwrap-card{width:250px;flex:0 0 250px}", ".cz-mkwrap-card>.mcard.bs-week-card{flex:1 0 auto;width:100%}",
                     "@media (max-width:720px){.bs-weekrow>.cz-mkwrap-card{width:230px;flex:0 0 230px}}", ".wk-cards>.cz-mkwrap-card{width:auto;flex:none}"):
            self.assertIn(rule, studio)
            self.assertEqual(CSS.count(rule), 1, rule)
        self.assertNotIn(".cz-", CSS[CSS.index("THE CIVIC BROADSHEET"):])       # nothing of the studio's among the broadsheet's rules
        self.assertIn(".wk-cards>.mcard.bs-week-card{width:auto;flex:none}", CSS)   # only a card the grid holds itself: a wrapped one fills its wrap
        self.assertIn("@media print{.wk-cards>*,.wk-list li{break-inside:avoid}", CSS)

    def test_the_constitution_names_the_week_beside_the_models_names(self):
        """The week lists threads a model named; the AI Constitution's ledger
        says so in the same commit (CLAUDE.md: a promise with a page)."""
        page = emit.page_ai(MANIFEST, "https://example.org")
        self.assertIn("as the week in the record says beside the threads it\n            lists", page)


if __name__ == "__main__":
    unittest.main()
