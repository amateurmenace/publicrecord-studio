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
        dash = {"m1": {"segments": [{"start": 0, "text": "free cash - housing trust fund -- well-known water main"},
                                    {"start": 5, "text": "free cash - housing trust fund -- well-known water main"}]}}
        got = [g["phrase"] for g in beside.beside([{"meeting_id": "m1", "pid": "p1", "beads": [{"t": 0}]}], dash, set())]
        self.assertNotIn("cash housing", got); self.assertNotIn("fund well", got)          # a dash between words is a clause break
        self.assertIn("free cash", got); self.assertIn("water main", got)                  # a hyphen inside a word is not
        # a pair inside one of the issue's longer names is the issue said beside itself
        longer = {"m1": {"segments": [{"start": 0, "text": "the affordable housing trust fund voted"},
                                      {"start": 5, "text": "the affordable housing trust fund voted"}]}}
        own = beside.own_words({"name": "Housing Trust Fund", "aliases": ["Affordable Housing Trust Fund"]})
        self.assertEqual(beside.beside([{"meeting_id": "m1", "pid": "p1", "beads": [{"t": 0}]}], longer, own), [])   # no "fund voted" either: the name's edge
        # …while the same pair said apart from the name still counts
        apart = {"m1": {"segments": [{"start": 0, "text": "affordable housing needs money; the housing trust fund voted"},
                                     {"start": 5, "text": "affordable housing needs money; the housing trust fund voted"}]}}
        got = [g["phrase"] for g in beside.beside([{"meeting_id": "m1", "pid": "p1", "beads": [{"t": 0}]}], apart, own)]
        self.assertIn("affordable housing", got); self.assertIn("needs money", got)
        self.assertNotIn("fund voted", got); self.assertNotIn("trust fund", got)

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


    def test_a_phrase_said_in_both_numbers_shows_once_with_its_own_count(self):
        """"complete street" and "complete streets" were two chips on one live
        issue. A phrase said both ways shows once, the way it was said most,
        with that form's own count and meetings — never a sum: the chip opens
        the record's search, which reads words exactly, so a summed count would
        promise lines its search cannot open. The form given up frees its place."""
        said = (["complete streets on harvard"] * 3 + ["a complete street here"] * 2 + ["the water main broke"] * 2
                + ["property taxes rose", "property tax relief", "housing policy now", "housing policies then"]
                + ["bike lane plan", "bike lanes plan"] * 2 + ["the bus stop moved"] * 2 + ["bus stops moved"] * 2)
        meetings = {"m1": {"segments": [{"start": i * 5.0, "text": s} for i, s in enumerate(said)]}}
        timeline = [{"meeting_id": "m1", "pid": "p1", "beads": [{"t": i * 5.0} for i in range(0, len(said), 3)]}]
        got = [(g["phrase"], g["n"]) for g in beside.beside(timeline, meetings, set(), top=20)]
        self.assertIn(("complete streets", 3), got)
        self.assertNotIn("complete street", [g[0] for g in got])            # given up to the form said more
        self.assertIn(("bike lane", 2), got)                                 # a tie keeps the one first in the alphabet
        self.assertNotIn("bike lanes", [g[0] for g in got])
        self.assertIn(("bus stop", 2), got)
        self.assertNotIn("bus stops", [g[0] for g in got])
        self.assertIn(("water main", 2), got)
        # a form said once shows nowhere, and gives nothing up ("property tax" / "taxes", "policy" / "policies")
        self.assertFalse({"property tax", "property taxes", "housing policy", "housing policies"} & {g[0] for g in got})
        # the cap counts what is shown: "bike lanes", given up, frees its place for "bus stop"
        top3 = beside.beside(timeline, meetings, set(), top=3)
        self.assertEqual([g["phrase"] for g in top3], ["complete streets", "bike lane", "bus stop"])
        # the candidates are only candidates: every English ending, matched against what was counted
        self.assertLessEqual({"complete streets"}, beside._numbers("complete street"))
        self.assertLessEqual({"complete street"}, beside._numbers("complete streets"))
        self.assertLessEqual({"property taxes"}, beside._numbers("property tax"))
        self.assertLessEqual({"property tax"}, beside._numbers("property taxes"))
        self.assertLessEqual({"housing policies"}, beside._numbers("housing policy"))
        self.assertLessEqual({"housing policy"}, beside._numbers("housing policies"))
        self.assertNotIn("public acces", beside._numbers("public access"))   # a double s is no plural
        self.assertNotIn("school bu", beside._numbers("school bus"))
        # a short word's other number too, and either word of the pair (review catches:
        # "dark sky" beside "dark skies"; "lane plan" beside "lanes plan")
        self.assertIn("dark skies", beside._numbers("dark sky"))
        self.assertIn("dark sky", beside._numbers("dark skies"))
        self.assertIn("lanes plan", beside._numbers("lane plan"))
        self.assertIn("lane plan", beside._numbers("lanes plan"))
        self.assertNotIn("lanes plan", [g[0] for g in got])                   # "lane plan", tied, first in the alphabet
        # -es only after a hiss: "rates" is not "rat"'s, nor "cares" "car"'s (a re-review catch)
        self.assertNotIn("rates", beside._numbers("rat"))
        self.assertNotIn("car", beside._numbers("cares"))
        self.assertIn("care", beside._numbers("cares"))
        self.assertNotIn("plan", beside._numbers("planes"))
        self.assertIn("buses", beside._numbers("bus"))
        self.assertIn("bus", beside._numbers("buses"))
        self.assertIn("church", beside._numbers("churches"))
        self.assertIn("mayoral vetoes", beside._numbers("mayoral veto"))       # -es after an o too
        self.assertIn("hometown hero", beside._numbers("hometown heroes"))
        self.assertEqual(beside._other("'s"), set())                           # a stray "'s" is no word
        self.assertNotIn("meter ", beside._numbers("meter 's"))
        self.assertTrue(all(v.split() == v.split(" ") for v in beside._numbers("meter 's")))
        # the possessive is another form of the word
        self.assertIn("historical society's", beside._numbers("historical society"))
        self.assertIn("historical society", beside._numbers("historical society's"))
        self.assertIn("residents", beside._numbers("residents'"))
        sky = {"m1": {"segments": [{"start": i * 5.0, "text": s} for i, s in enumerate(
            ["dark sky rules"] * 2 + ["dark skies again"] * 3)]}}
        both = [g["phrase"] for g in beside.beside([{"meeting_id": "m1", "pid": "p1", "beads": [{"t": 0.0}, {"t": 15.0}]}], sky, set())]
        self.assertIn("dark skies", both)
        self.assertNotIn("dark sky", both)

    def test_the_issue_s_own_name_is_left_out_in_either_number(self):
        """The live "Complete Streets" issue (alias "complete streets") showed
        "complete street" beside itself, under words that say its own names
        are left out (a review catch): its names, and its name's words, are
        left out in either number — where said, and as a phrase."""
        own = beside.own_words({"name": "Complete Streets", "aliases": ["complete streets"]})
        said = ["the complete street design here", "a complete street design again", "street design matters",
                "street design matters", "the traffic calming plan", "the traffic calming plan"]
        meetings = {"m1": {"segments": [{"start": i * 5.0, "text": s} for i, s in enumerate(said)]}}
        got = [g["phrase"] for g in beside.beside([{"meeting_id": "m1", "pid": "p1", "beads": [{"t": 0.0}, {"t": 15.0}, {"t": 25.0}]}],
                                                  meetings, own)]
        self.assertNotIn("complete street", got)                            # the name, in the other number
        self.assertIn("traffic calming", got)
        # "street design" said twice on its own counts; its two edges of the name, said, do not
        self.assertEqual([g for g in beside.beside([{"meeting_id": "m1", "pid": "p1", "beads": [{"t": 0.0}, {"t": 15.0}, {"t": 25.0}]}],
                                                   meetings, own) if g["phrase"] == "street design"],
                         [{"phrase": "street design", "n": 2, "meetings": 1}])
        # the name's words alone, in the other number: "complete street" is the name's own words
        self.assertEqual(beside.beside([{"meeting_id": "m1", "pid": "p1", "beads": [{"t": 0.0}]}],
                                       {"m1": {"segments": [{"start": 0.0, "text": "complete street"}, {"start": 5.0, "text": "complete street"}]}},
                                       {"phrases": set(), "tokens": {"complete", "streets"}}), [])
        # own_words itself is unchanged: the other numbers are the counting's, not the issue's
        self.assertEqual(own["phrases"], {"complete streets"})
        # nor the possessive: the live "historical society's" beside a historical society
        soc = beside.own_words({"name": "Brookline Historical Society", "aliases": ["historical society"]})
        said = {"m1": {"segments": [{"start": 0.0, "text": "the historical society's archive"},
                                    {"start": 5.0, "text": "our historical society's archive"}]}}
        self.assertEqual(beside.beside([{"meeting_id": "m1", "pid": "p1", "beads": [{"t": 0.0}]}], said, soc), [])


def _meeting(pid, lines, town="Brookline", people=()):
    return {"pid": pid, "id": pid, "town": town,
            "segments": [{"start": i * 5.0, "text": t} for i, t in enumerate(lines)],
            "analysis": {"entities": {"people": [{"name": p, "count": 1, "t": 0} for p in people]}}}


# a mixed-case transcript: ordinary words said in lower case, names capitalised mid-sentence
CASED = ["Good evening. We talked about the free cash and the budget tonight.",
         "Joe Quillon said the free cash covers the budget, and Paul Warren agreed.",
         "The board heard from Joe Quillon again about free cash and the budget.",
         "Paul Warren moved it, and the budget passed with free cash.",
         "We will talk about the police budget in Brookline next week."]


class TestNames(unittest.TestCase):
    """Officials-only aggregation (specs/17): the phrases beside an issue name
    no one the record does not already show — learned from the record's own
    captions, so an ALL-CAPS council caption and an all-lower-case one are
    covered as well as a mixed-case one."""

    def test_ordinary_words_are_learned_from_captions_whose_casing_means_something(self):
        shout = _meeting("b", ["WE HEARD FROM MARK TOLLET ABOUT THE FREE CASH.", "MARK TOLLET SPOKE AGAIN."], town="Boston")
        hush = _meeting("c", ["mark tollet said quillon and tollet and quillon again", "tollet quillon tollet quillon"], town="Boston")
        names = beside.names_of([_meeting("a", CASED), shout, hush])
        for w in ("free", "cash", "budget", "brookline", "boston"):
            self.assertIn(w, names["common"], w)                 # said in lower case twice or more — or a town the record holds
        self.assertNotIn("police", names["common"])              # said once: too little to learn from, so it is not vouched for
        # the calendar and acronyms are capitalised by rule, never a name; a word written in lower
        # case at least a quarter as often as it is capitalised is ordinary ("street", not "Beacon")
        cal = _meeting("d", ["The CPA funds are due July 4th and the CPA board meets on Monday.",
                             "We walked Beacon Street and Harvard Street and Kent Street and Pond Street,",
                             "and the street was closed, the street was quiet, and the CPA said so."])
        names = beside.names_of([cal])
        for w in ("cpa", "july", "monday", "street"):
            self.assertIn(w, names["common"], w)
        self.assertNotIn("beacon", names["common"])
        # a transcript that is ALL CAPS but for a stray capitalised word never votes: its shouting is not "acronyms"
        loud = _meeting("e", ["WE HEARD FROM MARK TOLLET ABOUT FREE CASH, Tollet said.", "MARK TOLLET AGAIN ON FREE CASH."] * 20)
        self.assertNotIn("tollet", beside.names_of([loud])["common"])
        self.assertNotIn("mark", beside.names_of([loud])["common"])
        for w in ("quillon", "warren", "paul", "joe", "tollet", "mark"):
            self.assertNotIn(w, names["common"], w)              # capitalised mid-sentence, or never heard where casing speaks

    def test_a_name_the_record_does_not_show_is_never_counted(self):
        m = _meeting("a", CASED, people=["Joe Quillon", "Paul Warren"])
        meetings = {"a": m}
        timeline = [{"meeting_id": "a", "pid": "a", "beads": [{"t": 5.0}, {"t": 15.0}]}]    # lines 0-4
        free = beside.beside(timeline, meetings, set())
        self.assertIn("joe quillon", [g["phrase"] for g in free])                          # without the rule, the name is counted
        plane = [{"name": "Paul Warren", "kind": "people"}]                              # the names plane shows Paul Warren only
        names = beside.names_of([m], roster=["Bernard Greene"], plane=plane)
        got = [g["phrase"] for g in beside.beside(timeline, meetings, set(), names=names)]
        self.assertNotIn("joe quillon", got)                                               # not shown: never counted
        self.assertIn("paul warren", got)                                                # shown: counted
        self.assertIn("free cash", got)                                                  # ordinary words: counted
        # a roll-call name is an official by construction
        names = beside.names_of([m], roster=["Joe Quillon"], plane=[])
        got = [g["phrase"] for g in beside.beside(timeline, meetings, set(), names=names)]
        self.assertIn("joe quillon", got); self.assertNotIn("paul warren", got)

    def test_all_caps_and_a_person_made_of_ordinary_words(self):
        # Boston's council captions are ALL CAPS: the casing says nothing, the vocabulary still does
        shout = _meeting("b", ["WE HEARD FROM MARK TOLLET ABOUT FREE CASH.", "MARK TOLLET ON FREE CASH AGAIN.",
                               "THANK YOU, MARK TOLLET."], town="Boston")
        names = beside.names_of([_meeting("a", CASED), shout], plane=[])
        got = [g["phrase"] for g in beside.beside([{"meeting_id": "b", "pid": "b", "beads": [{"t": 5.0}]}], {"b": shout}, set(), names=names)]
        self.assertIn("free cash", got); self.assertNotIn("mark tollet", got)
        # a person the analyzer found whose name is made of ordinary words: still a person's name
        plain = _meeting("d", ["the free cash and bill green spoke", "bill green and the free cash again",
                               "free cash for the budget and bill green"], people=["Bill Green"])
        names = beside.names_of([_meeting("a", CASED + ["the bill was green and the bill passed, green again"]), plain], plane=[])
        self.assertIn("bill", names["common"]); self.assertIn("green", names["common"])
        got = [g["phrase"] for g in beside.beside([{"meeting_id": "d", "pid": "d", "beads": [{"t": 5.0}]}], {"d": plain}, set(), names=names)]
        self.assertIn("free cash", got); self.assertNotIn("bill green", got)
        # …unless the names plane shows them
        names = beside.names_of([plain], plane=[{"name": "Bill Green", "kind": "people"}])
        self.assertNotIn("bill green", names["unshown"])

    def test_a_name_of_everyday_words_is_known_by_its_capitals(self):
        """A reviewer's catch: "Grace Park" is two everyday words, and still a
        name — the captions write it Capital Capital mid-sentence, twice and
        four times as often as in lower case, so it is held back unless the
        record lists it; while a pair the captions write in lower case is no
        one's name, whatever the analyzer filed it under."""
        lines = ["We thank Grace Park for her work on the free cash plan tonight.",
                 "Then Grace Park spoke again about the free cash and the park and the grace period.",
                 "the park was open and grace was shown, the park again and grace again"]
        m = _meeting("g", lines, people=["Vision Zero"])
        names = beside.names_of([m])
        self.assertIn("grace", names["common"]); self.assertIn("park", names["common"])
        self.assertIn("grace park", names["named"])
        beads = [{"meeting_id": "g", "pid": "g", "beads": [{"t": 0}, {"t": 5}]}]
        self.assertIn("grace park", [g["phrase"] for g in beside.beside(beads, {"g": m}, set())])          # counted without the rule
        got = [g["phrase"] for g in beside.beside(beads, {"g": m}, set(), names=names)]
        self.assertNotIn("grace park", got); self.assertIn("free cash", got)
        self.assertNotIn("grace park", beside.names_of([m], plane=[{"name": "Grace Park", "kind": "places"}])["named"])
        # the analyzer filed "Vision Zero" under people; the captions write it in lower case twice: no one's name
        v = _meeting("v", lines + ["the vision zero plan and the vision zero map"], people=["Vision Zero"])
        self.assertNotIn("vision zero", beside.names_of([v])["unshown"])
        self.assertIn("vision zero", beside.names_of([m])["unshown"])                     # …not vouched for without it
        # a person the analyzer found, captioned three times as a name and twice in lower case: still held back
        hope = _meeting("h", lines + ["We heard from Hope Wood today, and then Hope Wood again, and Hope Wood once more.",
                                      "the hope wood said and hope wood again"], people=["Hope Wood"])
        names = beside.names_of([hope])
        self.assertIn("hope wood", names["unshown"])
        # a day on the calendar is never a person, even written Capital Capital
        day = _meeting("d", lines + ["We honor Memorial Day, and Memorial Day again, the memorial and the day."])
        self.assertNotIn("memorial day", beside.names_of([day])["named"])

    def test_what_counts_as_a_capital(self):
        """Lower case is evidence wherever it stands; a capital only
        mid-sentence and mid-line; a full stop after "Mr." ends no sentence;
        and a caption that capitalises only each line's first word says
        nothing about names (a reviewer's catch: it once taught them)."""
        c = _meeting("c", ["We will begin.", "commence construction by July 4th, the Select Board said.", "Then we commence the work,"])
        self.assertIn("commence", beside.names_of([c])["common"])            # lower case at a line's start still counts
        # ten capitals after "Mr." against two in lower case: not ordinary (4 × 2 < 10)
        h = _meeting("h", ["We heard from Mr. Quillon tonight, and the budget passed."] * 10 + ["the quillon plan and the quillon map"])
        self.assertNotIn("quillon", beside.names_of([h])["common"])
        # capitals only at each line's start, names in lower case: the gate stays shut, nothing is learned
        shy = _meeting("s", [f"Joe quillon said the free cash was fine {i}" for i in range(20)])
        self.assertEqual(beside.names_of([shy])["common"] - beside.CALENDAR, {"brookline"})
        # …nor does "I'm" mid-line, a month or a town: every captioner capitalises those (a skeptic's catch)
        chatty = _meeting("t", [f"Joe quillon said I'm sure the free cash in Brookline was fine in July {i}" for i in range(20)])
        self.assertEqual(beside.names_of([chatty])["common"] - beside.CALENDAR, {"brookline"})

    def test_the_press_hands_the_rule_the_names_plane_and_the_roll_calls(self):
        """The issue stage reads the same forty names the names plane shows
        (web/bake.py names_plane) and the corpus's roll-call names: a name
        said twice beside an issue that neither shows is never counted,
        while ordinary phrases beside it are."""
        from memory.store import Corpus
        from web import bake
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); db = root / "corpus.db"
            TestBakeEdition._seed(db)
            c = Corpus(str(db))
            try:
                from record.press import _no_sidecars
                (root / "out").mkdir()
                b = bake.Bake(c, root / "out", "1.0.0", _no_sidecars)
                meetings = b.bake_meetings()
                said = ["Good evening, the free cash and Joe Quillon on the override.",
                        "Joe Quillon said the free cash covers the override, and we agreed.",
                        "The free cash again, with Joe Quillon, before the vote."]
                for m in meetings:
                    for i, s in enumerate(m["segments"]):
                        s["text"] = said[i % 3] + " " + s["text"]
                issues = b.bake_issues({m["id"]: m for m in meetings})
                got = [w["phrase"] for i in issues for w in i["beside"]]
                self.assertIn("free cash", got)
                self.assertNotIn("joe quillon", got)
                self.assertEqual(bake.names_plane(meetings), b.bake_analytics(meetings)["names"])   # one list, two readers
            finally:
                c.close()


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
        self.assertIn("its own names are left out, and so is any other name the record does not already list — a name is known by its capitals", page)
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
