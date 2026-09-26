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
                 money=[{"name": "$5 million", "t": 40.0, "count": 1}, {"name": "$146,000", "t": 50.0, "count": 3}],
                 lenses=[("financial", 60), ("community", 40)]),
              _m("b", "2026-09-24", town="Boston", body="City Council", dur=7200.0, money=[{"name": "$2 MILLION", "t": 10.0, "count": 2}],
                 lenses=[("community", 90), ("financial", 10)]),
              _m("c", "2026-09-14", lenses=[("financial", 10), ("safety", 90)])]
        issues = [{"slug": "i1", "name": "Budget", "timeline": [{"pid": "a", "beads": [{"t": 1}, {"t": 2}]}, {"pid": "c", "beads": [{"t": 1}]}]},
                  {"slug": "i2", "name": "Parking", "timeline": [{"pid": "a", "beads": [{"t": 1}]}, {"pid": "b", "beads": [{"t": 1}, {"t": 2}, {"t": 3}]}]},
                  {"slug": "i3", "name": "Elsewhere", "timeline": [{"pid": "c", "beads": [{"t": 1}]}]}, "junk"]
        d = week.week_data("2026-09-21", ms, issues)
        self.assertEqual([m["pid"] for m in d["meetings"]], ["a", "b"])
        self.assertEqual(d["seconds"], 10800.0)
        self.assertEqual(d["towns"], ["Boston", "Brookline"])
        self.assertEqual([(r["motion"], r["outcome"], r["tally"]) for r in d["rolls"]], [("move to adopt the budget", "passes", "5-0-0")])
        self.assertEqual([x["kind"] for x in d["decisions"]], ["tension", "decision"])     # loudest first; no vote, no question
        self.assertEqual([(s["label"], s["count"]) for s in d["sums"]], [("$146,000", 3), ("$2 million", 2), ("$5 million", 1)])
        self.assertEqual([(t["name"], t["said"], t["week"], t["all"]) for t in d["threads"]], [("Parking", 4, 2, 2), ("Budget", 2, 1, 2)])
        lz = d["lens"]
        self.assertEqual((lz["loudest"], round(lz["loudest_week"], 3)), ("community", round(130 / 200, 3)))
        self.assertEqual(lz["words"], 200)
        self.assertEqual((d["newer"], d["older"]), (None, "2026-09-14"))
        self.assertEqual(week.week_data("2026-09-14", ms, issues)["newer"], "2026-09-21")
        self.assertIsNone(week.week_data("2026-09-14", [_m("z", "2026-09-15")], [])["lens"])       # nothing framed, nothing claimed
        # the page: every part, every number a link into the tape; nothing of the studio
        counts = {"2026-09-21": 2, "2026-09-14": 1}
        page = emit.page_week(d, counts, MANIFEST, "https://example.org")
        self.assertIn("<h1 class=\"wk-title\">The week of September 21, 2026</h1>", page)
        self.assertIn("Two meetings, three hours of tape, in Boston and Brookline.", page)
        self.assertIn('href="/app/m/a#t30"', page)                               # the roll call opens its tape
        self.assertIn(">passed 5-0-0<", page)
        self.assertIn("<b class=\"wk-sum\">$146,000</b>", page)
        self.assertIn('href="/app/i/i2"><b>Parking</b>', page)
        self.assertIn("said 4 times this week, in 2 of its 2 meetings · 2 meetings on the record", page)
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
            bake.bake(str(db), str(d / "app"), "9.9.9", "https://example.org")
            out = d / "app"
            import json
            meta = json.loads((out / "search" / "meta.json").read_text())
            ks = week.weeks(meta)
            self.assertTrue(ks)
            for k in ks:
                self.assertTrue((out / "week" / k / "index.html").exists(), k)
            self.assertEqual((out / "week" / "index.html").read_text(), (out / "week" / ks[0] / "index.html").read_text())
            feed = (out / "feeds" / "week.xml").read_text()
            self.assertEqual(len(re.findall(r"<item>", feed)), min(12, len(ks)))
            self.assertIn(f"<link>https://example.org/app/week/{ks[0]}/</link>", feed)
            home = (out / "index.html").read_text()
            latest = max((m["date"] for m in meta if m.get("date")), default="")
            self.assertIn(f'<p class="wk-link"><a href="/app/week/{week.monday_of(latest)}/">', home)
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


if __name__ == "__main__":
    unittest.main()
