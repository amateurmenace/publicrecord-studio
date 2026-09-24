"""The words the record uses, explained (specs/27 §3.4).

A four-hour meeting says "warrant article", "free cash" and "override" a
hundred times and never once says what they mean; a resident who does not
already know is locked out of the room they are reading. The glossary is
the key: each entry says what the word means in plain language, where it
applies (Brookline, Boston, the Commonwealth), where to read the public
source, and — the record's own contribution — how often the record says
it, when it first did, and the search that finds every line.

Two halves, labeled apart. The definitions were written at the desk with
Claude (Anthropic's model), paraphrasing the public source each entry
names — never at press time, never in a reader's browser; the ledger on
/app/ai says so, and so does the page. The counts are the press's, whole-
word over every transcript (web/topic.py's own rule), and no model counts
them. Corrections annotate, like everything on the record.

No person is defined here — the covenant keeps no person pages; bodies and
offices only.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence
from urllib.parse import quote

from .charts import esc, n_of

MGL = "https://malegislature.gov/Laws/GeneralLaws/PartI"
DLS = ("the state’s Municipal Finance Glossary", "https://www.mass.gov/info-details/municipal-finance-glossary")
BK_TM = ("Brookline — Town Meeting", "https://www.brooklinema.gov/264/Town-Meeting")
BK_SB = ("Brookline — Select Board", "https://www.brooklinema.gov/343/Board-of-Selectmen")
BK_AC = ("Brookline — Advisory Committee", "https://www.brooklinema.gov/166/Advisory-Committee")
BK_HB = ("Brookline — Town Meeting Handbook", "https://www.brooklinema.gov/277/Town-Meeting-Handbook-PDF")
BK_OV = ("Brookline — the override guide", "https://www.brooklinema.gov/3590/FY2024-26-Override-Central")
BOS_CC = ("Boston — City Council", "https://www.boston.gov/departments/city-council")
OML = ("the Attorney General — the Open Meeting Law", "https://www.mass.gov/the-open-meeting-law")


def law(cite: str, path: str):
    return (cite, f"{MGL}/{path}")


# (group, title) — the page reads in this order
GROUPS = [
    ("who", "Who decides"),
    ("meeting", "How a meeting runs"),
    ("money", "The money"),
    ("built", "What gets built, and where"),
    ("schools", "The schools"),
]

# every entry: slug, the term as a heading, where it applies, the plain
# meaning, the phrases the press counts (whole-word, case-blind — the
# story engine's rule), the public sources. Kept in the order each group
# reads; the page adds an A–Z index.
ENTRIES: List[dict] = [
    # -- who decides ---------------------------------------------------------
    {"slug": "select-board", "group": "who", "term": "Select Board", "where": ["Brookline", "Massachusetts"],
     "says": "The town’s elected executive: in Brookline, five members elected to three-year terms. It calls "
             "Town Meeting and writes its warrant, hires the Town Administrator, sets the budget’s guidelines, "
             "appoints most boards, grants licenses and serves as the police commissioners. Many towns once "
             "called it the Board of Selectmen.",
     "phrases": ["select board", "board of selectmen"], "sources": [BK_SB]},
    {"slug": "town-meeting", "group": "who", "term": "Town Meeting", "where": ["Brookline", "Massachusetts"],
     "says": "The town’s legislature. Brookline’s is a representative Town Meeting: 255 members elected by "
             "precinct — fifteen from each of seventeen — who pass the budget and every bylaw. The annual meeting "
             "comes in late spring and a special one usually in the fall; anyone may watch, only members vote.",
     "phrases": ["town meeting"], "sources": [BK_TM]},
    {"slug": "town-administrator", "group": "who", "term": "Town Administrator", "where": ["Brookline"],
     "says": "The town’s chief appointed manager, hired by the Select Board to run its departments and its "
             "daily business.",
     "phrases": ["town administrator"], "sources": [BK_SB]},
    {"slug": "advisory-committee", "group": "who", "term": "Advisory Committee", "where": ["Brookline"],
     "says": "Town Meeting’s finance committee: twenty to thirty residents, appointed by the Moderator, who hold "
             "hearings on every warrant article — the budget included — and recommend how Town Meeting should "
             "vote. It alone may approve a transfer from the reserve fund.",
     "phrases": ["advisory committee"], "sources": [BK_AC]},
    {"slug": "city-council", "group": "who", "term": "City Council", "where": ["Boston"],
     "says": "Boston’s legislature: thirteen councilors — nine elected by district, four at large — elected "
             "every two years. It passes the city’s ordinances, approves its budget each year and holds hearings "
             "on what comes before it.",
     "phrases": ["city council"], "sources": [BOS_CC]},
    {"slug": "planning-board", "group": "who", "term": "Planning Board", "where": ["Massachusetts"],
     "says": "The board that plans a community’s growth — its master plan, subdivisions, the design of large "
             "projects — and holds a hearing and reports on every proposed change to the zoning.",
     "phrases": ["planning board"], "sources": [law("M.G.L. c. 41 § 81A", "TitleVII/Chapter41/Section81A")]},
    {"slug": "zoning-board-of-appeals", "group": "who", "term": "Zoning Board of Appeals (ZBA)", "where": ["Massachusetts"],
     "says": "The board that hears requests for variances, special permits and Chapter 40B comprehensive permits, "
             "and appeals of a building official’s zoning decisions — each at a public hearing.",
     "phrases": ["zoning board of appeals", "zoning board of appeal", "ZBA"],
     "sources": [law("M.G.L. c. 40A § 12", "TitleVII/Chapter40A/Section12")]},
    {"slug": "bpda", "group": "who", "term": "BPDA", "where": ["Boston"],
     "says": "The Boston Planning & Development Agency, which planned the city’s growth and reviewed its "
             "development. Its staff and most of its work have moved into the City of Boston’s Planning "
             "Department; the agency’s board of directors still meets — the record carries its meetings — to vote "
             "on projects, land and contracts.",
     "phrases": ["BPDA", "Boston Planning"], "sources": [("Boston — Planning Department", "https://www.bostonplans.org/about-us")]},
    # -- how a meeting runs -----------------------------------------------------
    {"slug": "warrant", "group": "meeting", "term": "warrant, warrant article", "where": ["Brookline", "Massachusetts"],
     "says": "The warrant is the official list of what a Town Meeting may act on, issued by the Select Board; "
             "each item on it is a warrant article — the budget, a bylaw, a zoning change, a resolution. An "
             "article reaches the warrant from the Select Board or by a petition of the town’s voters, and Town "
             "Meeting may act only on what its warrant says.",
     "phrases": ["warrant"], "sources": [BK_TM, law("M.G.L. c. 39 § 10", "TitleVII/Chapter39/Section10")]},
    {"slug": "favorable-action", "group": "meeting", "term": "favorable action, no action", "where": ["Brookline"],
     "says": "How a board recommends a warrant article to Town Meeting: favorable action — adopt it, usually in "
             "the words of a motion it offers — or no action. The recommendation is advice; Town Meeting decides "
             "by its own vote.",
     "phrases": ["favorable action", "no action"], "sources": [BK_HB]},
    {"slug": "reconsideration", "group": "meeting", "term": "reconsideration", "where": ["Massachusetts"],
     "says": "A motion to take up again a question already voted, so the body can decide it anew — allowed only "
             "as the body’s own rules of procedure permit.",
     "phrases": ["reconsideration", "reconsider"], "sources": [BK_HB]},
    {"slug": "quorum", "group": "meeting", "term": "quorum", "where": ["Massachusetts"],
     "says": "The number of members who must be present before a body may act — under the Open Meeting Law, a "
             "simple majority, unless another law sets a different number.",
     "phrases": ["quorum"], "sources": [law("M.G.L. c. 30A § 18", "TitleIII/Chapter30A/Section18")]},
    {"slug": "roll-call", "group": "meeting", "term": "roll call", "where": ["Massachusetts"],
     "says": "A vote taken by calling each member by name, so that how each one voted — yes, no, abstain — is on "
             "the record. The record reads the roll calls it can hear on the tape; the official minutes are the "
             "last word.",
     "phrases": ["roll call", "roll-call"], "sources": [("the record — the votes", "/app/officials")]},
    {"slug": "public-hearing", "group": "meeting", "term": "public hearing", "where": ["Massachusetts"],
     "says": "A session a board must advertise in advance and open to anyone before it decides certain things — a "
             "zoning change, a permit, a license — so that the people affected can be heard.",
     "phrases": ["public hearing", "public hearings"], "sources": [law("M.G.L. c. 40A § 11", "TitleVII/Chapter40A/Section11")]},
    {"slug": "public-comment", "group": "meeting", "term": "public comment", "where": ["Massachusetts"],
     "says": "Time a board sets aside for anyone to speak, on the board’s own rules — usually a few minutes each. "
             "The Open Meeting Law requires a meeting to be open to the public; whether and when the public "
             "speaks is the chair’s to decide.",
     "phrases": ["public comment", "public comments"], "sources": [BK_SB, OML]},
    {"slug": "executive-session", "group": "meeting", "term": "executive session", "where": ["Massachusetts"],
     "says": "The part of a meeting a public body may hold in private — only for a reason the Open Meeting Law "
             "lists, among them collective bargaining, litigation, the purchase of real estate and a person’s "
             "reputation — entered by a roll-call vote in open session, with the reason stated.",
     "phrases": ["executive session"], "sources": [law("M.G.L. c. 30A § 21", "TitleIII/Chapter30A/Section21")]},
    {"slug": "open-meeting-law", "group": "meeting", "term": "Open Meeting Law", "where": ["Massachusetts"],
     "says": "The state law that requires a public body to meet in the open, to post each meeting forty-eight "
             "hours ahead (weekends and holidays aside), and to keep minutes — with a short list of reasons it may "
             "meet in executive session.",
     "phrases": ["open meeting law"], "sources": [OML, law("M.G.L. c. 30A §§ 18–25", "TitleIII/Chapter30A/Section18")]},
    {"slug": "docket", "group": "meeting", "term": "docket", "where": ["Boston"],
     "says": "A numbered item before the Boston City Council — an ordinance, an order for a hearing, a "
             "resolution, an appointment, a grant to accept. The council refers it to a committee, passes it, or "
             "places it on file.",
     "phrases": ["docket", "dockets"], "sources": [BOS_CC]},
    # -- the money ------------------------------------------------------------------
    {"slug": "fiscal-year", "group": "money", "term": "fiscal year (FY)", "where": ["Massachusetts"],
     "says": "The budget year. Massachusetts cities and towns run theirs from July 1 to June 30 and name it for "
             "the year it ends: FY2027 began on July 1, 2026.",
     "phrases": ["fiscal year"], "sources": [DLS]},
    {"slug": "appropriation", "group": "money", "term": "appropriation", "where": ["Massachusetts"],
     "says": "A vote of Town Meeting or a city council that authorizes spending a set amount for a set purpose. "
             "Public money is spent only as an appropriation allows.",
     "phrases": ["appropriation", "appropriations"], "sources": [DLS]},
    {"slug": "proposition-2-half", "group": "money", "term": "Proposition 2½", "where": ["Massachusetts"],
     "says": "The 1980 state law that caps a community’s property taxes. The total it may levy in a year — its "
             "levy limit — may grow by 2.5 percent plus new growth, and may never pass 2.5 percent of the full "
             "value of all its taxable property. Voters can raise the limit with an override, or step past it for "
             "one project with a debt exclusion.",
     "phrases": ["proposition two and a half", "prop two and a half", "proposition 2 and a half",
                 "prop 2 and a half", "proposition 2 1/2", "prop 2 1/2", "proposition 2½", "prop 2½"],
     "sources": [DLS, law("M.G.L. c. 59 § 21C", "TitleIX/Chapter59/Section21C")]},
    {"slug": "levy", "group": "money", "term": "levy, levy limit", "where": ["Massachusetts"],
     "says": "The levy is what a community raises in property taxes in a year. The levy limit is the most "
             "Proposition 2½ lets it raise: last year’s limit, plus 2.5 percent, plus new growth, plus any "
             "override or exclusion its voters approved.",
     "phrases": ["levy"], "sources": [DLS]},
    {"slug": "new-growth", "group": "money", "term": "new growth", "where": ["Massachusetts"],
     "says": "Tax from property new to the tax rolls — new buildings, additions, renovations — which a community "
             "may add to its levy limit on top of the 2.5 percent. A rise in market values alone is not new growth.",
     "phrases": ["new growth"], "sources": [DLS]},
    {"slug": "override", "group": "money", "term": "override", "where": ["Massachusetts", "Brookline"],
     "says": "A ballot question that asks voters to raise the levy limit permanently, by a stated amount for a "
             "stated purpose. It needs a majority at the polls, and it can never lift the levy past the levy "
             "ceiling. The money it raises is then appropriated like any other.",
     "phrases": ["override", "overrides"], "sources": [DLS, BK_OV]},
    {"slug": "debt-exclusion", "group": "money", "term": "debt exclusion", "where": ["Massachusetts"],
     "says": "A ballot question that lets a community tax above its levy limit only to pay the debt on one project "
             "— a school, a fire station — and only until that debt is paid. Unlike an override, it ends.",
     "phrases": ["debt exclusion", "debt exclusions"], "sources": [DLS]},
    {"slug": "free-cash", "group": "money", "term": "free cash", "where": ["Massachusetts"],
     "says": "Unrestricted money left over from the last fiscal year — revenue above its estimate, budget lines "
             "not spent — once the state certifies the amount. It is often spent on one-time costs or put into "
             "reserves, by a vote of Town Meeting or the council.",
     "phrases": ["free cash"], "sources": [DLS]},
    {"slug": "stabilization-fund", "group": "money", "term": "stabilization fund", "where": ["Massachusetts"],
     "says": "A community’s savings for the future — an emergency, a lean year, a large capital cost. Money goes "
             "in and comes out only by a vote of Town Meeting or the council, and spending from it takes two thirds.",
     "phrases": ["stabilization fund", "stabilization funds"],
     "sources": [DLS, law("M.G.L. c. 40 § 5B", "TitleVII/Chapter40/Section5B")]},
    {"slug": "reserve-fund", "group": "money", "term": "reserve fund", "where": ["Massachusetts", "Brookline"],
     "says": "A small sum set aside in the budget — no more than 5 percent of the last year’s levy — for costs no "
             "one could foresee. In a town the finance committee approves each transfer from it; in Brookline, "
             "the Advisory Committee.",
     "phrases": ["reserve fund"], "sources": [DLS, law("M.G.L. c. 40 § 6", "TitleVII/Chapter40/Section6")]},
    {"slug": "capital-improvement-plan", "group": "money", "term": "capital improvement plan (CIP)", "where": ["Massachusetts", "Brookline"],
     "says": "The long-range list of what a community means to build, repair or buy — roofs, roads, schools, "
             "fire trucks — year by year, with how each will be paid for. Brookline’s runs six years; its first "
             "year is the capital budget Town Meeting votes.",
     "phrases": ["capital improvement", "capital improvements", "CIP"], "sources": [DLS, BK_SB]},
    {"slug": "state-aid", "group": "money", "term": "state aid, Chapter 70", "where": ["Massachusetts"],
     "says": "The money the Commonwealth sends each city and town every year. Chapter 70 is the largest part — "
             "the state’s formula aid for public schools. Each community learns its amounts from the cherry "
             "sheet, named for the cherry-colored paper it was once printed on.",
     "phrases": ["state aid", "chapter 70", "cherry sheet"], "sources": [DLS, law("M.G.L. c. 70", "TitleXII/Chapter70")]},
    {"slug": "pilot", "group": "money", "term": "PILOT (payment in lieu of taxes)", "where": ["Massachusetts", "Boston"],
     "says": "A voluntary payment an institution exempt from property tax — a university, a hospital — makes to "
             "the city or town it sits in, in place of the taxes it does not owe. Boston asks its large "
             "nonprofits for one every year.",
     "phrases": ["payment in lieu of taxes", "payments in lieu of taxes", "PILOT payment", "PILOT payments",
                 "PILOT agreement", "PILOT agreements"],
     "sources": [("Boston — the PILOT program", "https://www.boston.gov/departments/assessing/payment-lieu-tax-pilot-program"), DLS]},
    {"slug": "community-preservation-act", "group": "money", "term": "Community Preservation Act (CPA)", "where": ["Massachusetts"],
     "says": "A state law a community may adopt by ballot: a surcharge of up to 3 percent on property taxes, "
             "matched in part by the state, spent only on open space, historic preservation, affordable housing "
             "and outdoor recreation, on the advice of a local Community Preservation Committee.",
     "phrases": ["community preservation"],
     "sources": [("the Community Preservation Coalition", "https://www.communitypreservation.org/about"),
                 law("M.G.L. c. 44B", "TitleVII/Chapter44B")]},
    {"slug": "collective-bargaining", "group": "money", "term": "collective bargaining", "where": ["Massachusetts"],
     "says": "Negotiation between a public employer and the union that represents its workers — over wages, hours "
             "and working conditions — under the state’s public-employee bargaining law. A board plans its side "
             "in executive session.",
     "phrases": ["collective bargaining"], "sources": [DLS, law("M.G.L. c. 150E", "TitleXXI/Chapter150E")]},
    # -- what gets built -----------------------------------------------------------
    {"slug": "bylaw", "group": "built", "term": "bylaw", "where": ["Massachusetts"],
     "says": "A town’s own local law — its general bylaws and its zoning bylaw — adopted or changed by Town "
             "Meeting. A city’s local laws are ordinances, passed by its council.",
     "phrases": ["bylaw", "bylaws", "by-law", "by-laws"], "sources": [BK_TM]},
    {"slug": "zoning", "group": "built", "term": "zoning, zoning bylaw", "where": ["Massachusetts"],
     "says": "The rules for what may be built where — uses, heights, setbacks, parking — set in a town by its "
             "zoning bylaw (in Boston, its zoning code) under the state’s Zoning Act. Most changes take a "
             "two-thirds vote of Town Meeting or the council; some housing changes, a simple majority.",
     "phrases": ["zoning"], "sources": [law("M.G.L. c. 40A", "TitleVII/Chapter40A")]},
    {"slug": "overlay-district", "group": "built", "term": "overlay district", "where": ["Massachusetts"],
     "says": "A zone drawn over the existing zoning that adds rules or allows more — denser housing near transit, "
             "a historic area’s protections — without erasing the zoning beneath it.",
     "phrases": ["overlay"], "sources": [law("M.G.L. c. 40A", "TitleVII/Chapter40A")]},
    {"slug": "special-permit", "group": "built", "term": "special permit", "where": ["Massachusetts"],
     "says": "Permission for a use or a building the zoning allows only case by case, granted by a named board "
             "after a public hearing — often with conditions.",
     "phrases": ["special permit", "special permits"], "sources": [law("M.G.L. c. 40A § 9", "TitleVII/Chapter40A/Section9")]},
    {"slug": "variance", "group": "built", "term": "variance", "where": ["Massachusetts"],
     "says": "Permission to depart from the zoning’s own terms — a setback, a height — granted only where a lot’s "
             "shape, soil or topography makes the rule a hardship and the departure harms no one. The law makes "
             "variances hard to get on purpose.",
     "phrases": ["variance", "variances"], "sources": [law("M.G.L. c. 40A § 10", "TitleVII/Chapter40A/Section10")]},
    {"slug": "chapter-40b", "group": "built", "term": "Chapter 40B", "where": ["Massachusetts"],
     "says": "The state law that lets a developer who sets aside a share of new homes as affordable ask the Zoning "
             "Board of Appeals for one comprehensive permit in place of local zoning — with an appeal to the state "
             "— in any community where less than 10 percent of the housing counts as affordable.",
     "phrases": ["40B"], "sources": [law("M.G.L. c. 40B § 20", "TitleVII/Chapter40B/Section20")]},
    {"slug": "mbta-communities", "group": "built", "term": "MBTA Communities (Section 3A)", "where": ["Massachusetts"],
     "says": "The state law that requires every city and town the MBTA serves to have at least one zoning "
             "district, near transit where it can be, where multifamily housing is allowed as of right — without "
             "a special permit.",
     "phrases": ["MBTA communities", "section 3A"],
     "sources": [("Massachusetts — the MBTA Communities law", "https://www.mass.gov/info-details/multi-family-zoning-requirement-for-mbta-communities"),
                 law("M.G.L. c. 40A § 3A", "TitleVII/Chapter40A/Section3A")]},
    {"slug": "housing-trust", "group": "built", "term": "affordable housing trust", "where": ["Massachusetts", "Brookline"],
     "says": "A fund a city or town sets up to create and keep homes that people of modest means can afford, "
             "governed by its own board of trustees.",
     "phrases": ["housing trust"], "sources": [law("M.G.L. c. 44 § 55C", "TitleVII/Chapter44/Section55C")]},
    {"slug": "article-80", "group": "built", "term": "Article 80", "where": ["Boston"],
     "says": "The part of Boston’s zoning code that sets how a large development is reviewed — its public "
             "meetings, the city’s review of its design and impacts, and the vote that approves it.",
     "phrases": ["article 80"], "sources": [("Boston — what is Article 80", "https://www.bostonplans.org/projects/development-review/what-is-article-80")]},
    {"slug": "vision-zero", "group": "built", "term": "Vision Zero", "where": ["Boston", "Brookline"],
     "says": "A traffic-safety policy with one goal — no one killed or seriously hurt on the streets — pursued "
             "through lower speeds, safer street design and a study of every crash.",
     "phrases": ["vision zero"], "sources": [("Boston — Vision Zero", "https://www.boston.gov/departments/transportation/vision-zero")]},
    # -- the schools ----------------------------------------------------------------
    {"slug": "school-committee", "group": "schools", "term": "School Committee", "where": ["Massachusetts"],
     "says": "The board that governs a district’s public schools: it sets their policy, adopts the school budget "
             "and hires the superintendent.",
     "phrases": ["school committee"], "sources": [law("M.G.L. c. 71 § 37", "TitleXII/Chapter71/Section37")]},
    {"slug": "superintendent", "group": "schools", "term": "superintendent", "where": ["Massachusetts"],
     "says": "The school district’s chief executive, appointed by the School Committee to run the schools day to day.",
     "phrases": ["superintendent"], "sources": [law("M.G.L. c. 71 § 59", "TitleXII/Chapter71/Section59")]},
    {"slug": "metco", "group": "schools", "term": "METCO", "where": ["Massachusetts", "Boston", "Brookline"],
     "says": "The Metropolitan Council for Educational Opportunity: since 1966, a voluntary program through which "
             "Boston students attend the public schools of suburban towns, Brookline among them.",
     "phrases": ["METCO"], "sources": [("METCO, Inc.", "https://metcoinc.org/")]},
    {"slug": "dese", "group": "schools", "term": "DESE", "where": ["Massachusetts"],
     "says": "The Massachusetts Department of Elementary and Secondary Education — the state agency that oversees "
             "public schools: their standards, the MCAS tests, the state’s school aid.",
     "phrases": ["DESE"], "sources": [("the Department of Elementary and Secondary Education", "https://www.doe.mass.edu/")]},
]

BY_SLUG: Dict[str, dict] = {e["slug"]: e for e in ENTRIES}


def entry_for(phrase: str) -> Optional[dict]:
    """The entry that explains a phrase the record uses — by one of its
    counted phrases, or a name in its heading ("warrant article"), a plural
    folded ("warrant articles"). None when the glossary has no such word."""
    k = " ".join(str(phrase or "").lower().split())
    if not k:
        return None
    for key in (k, k[:-1] if k.endswith("s") else k):
        for e in ENTRIES:
            names = {p.lower() for p in e["phrases"]}
            names |= {t.split("(")[0].strip().lower() for t in e["term"].split(",")}
            if key in names:
                return e
    return None


def _search(q: str, base: str) -> str:
    return f"{base}/s?q={quote(str(q), safe='')}"


def count(meetings: Sequence[dict]) -> Dict[str, dict]:
    """How often the record says each entry's words — whole-word, case-blind,
    a line read with the next joined on (the story engine's own rule) — in
    how many meetings, and where it first did. Pure over the meetings."""
    from .topic import mentions_in, phrase_re
    pats = {e["slug"]: [phrase_re(p) for p in e["phrases"]] for e in ENTRIES}
    out: Dict[str, dict] = {e["slug"]: {"mentions": 0, "meetings": 0, "first": None, "by": {}} for e in ENTRIES}
    dated = sorted(meetings, key=lambda m: (str(m.get("date") or "9999"), str(m.get("pid") or "")))
    for m in dated:
        segs = m.get("segments") or []
        texts = [str(s.get("text") or "") for s in segs]
        night = " ".join(texts).lower()
        for e in ENTRIES:
            # the night read whole first: a word it never says costs one
            # search, not a pass over every line
            if not any(p.search(night) for p in pats[e["slug"]]):
                continue
            n, first_t = 0, None
            ps = pats[e["slug"]]
            for i, t in enumerate(texts):
                k = mentions_in(t, texts[i + 1] if i + 1 < len(texts) else "", ps)
                if k:
                    n += k
                    if first_t is None:
                        first_t = float(segs[i].get("start") or 0)
            if n:
                r = out[e["slug"]]
                r["mentions"] += n
                r["meetings"] += 1
                r["by"][m["pid"]] = n
                if r["first"] is None:
                    r["first"] = {"pid": m["pid"], "date": str(m.get("date") or ""), "t": first_t}
    return out


def terms_on(m: dict, counts: Dict[str, dict], top: int = 6) -> List[dict]:
    """The glossary's words one meeting says most — for the line on its page
    that says where they are explained."""
    rows = [(counts[e["slug"]]["by"].get(m["pid"], 0), e) for e in ENTRIES]
    rows = [(n, e) for n, e in rows if n]
    rows.sort(key=lambda r: (-r[0], r[1]["term"]))
    return [{"slug": e["slug"], "term": e["term"], "n": n} for n, e in rows[:top]]


def _day(d: str) -> str:
    from .story import day_name
    return day_name(d) if d else "an undated meeting"


def _entry(e: dict, c: dict, base: str) -> str:
    def src(name: str, u: str) -> str:
        rel = "" if u.startswith("/") else ' rel="noopener"'     # built first: an f-string holds no backslash
        return f'<a href="{esc(u)}"{rel}>{esc(name)}</a>'
    srcs = " · ".join(src(name, u) for name, u in e["sources"])
    where = "".join(f'<span class="gl-where">{esc(w)}</span>' for w in e["where"])
    if c["mentions"]:
        f = c["first"]
        rec = (f'<a href="{esc(_search(e["phrases"][0], base))}">{n_of(c["mentions"], "time")}</a> in '
               f'{n_of(c["meetings"], "meeting")} — first on '
               f'<a href="{base}/m/{esc(f["pid"])}#t{int(f["t"] or 0)}">{esc(_day(f["date"]))}</a>')
    else:
        rec = "not yet — the record has not heard it said"
    return (f'<section class="gl-entry" id="{esc(e["slug"])}">'
            f'<h3 class="gl-term">{esc(e["term"])}</h3><p class="gl-wheres">{where}</p>'
            f'<p class="gl-says">{esc(e["says"])}</p>'
            f'<p class="gl-src"><span class="kicker">read the source</span> {srcs}</p>'
            f'<p class="gl-rec"><span class="kicker">on the record</span> {rec}</p></section>')


def body(meetings: Sequence[dict], base: str = "/app", counts: Optional[Dict[str, dict]] = None) -> str:
    counts = counts if counts is not None else count(meetings)
    az = sorted(ENTRIES, key=lambda e: e["term"].lower())
    index = " ".join(f'<a href="#{esc(e["slug"])}">{esc(e["term"])}</a>' for e in az)
    groups = []
    for key, title in GROUPS:
        es = [e for e in ENTRIES if e["group"] == key]
        groups.append(f'<section class="gl-group" id="gl-{key}"><div class="sectionhead"><span class="kicker">{esc(title)}</span></div>'
                      + "".join(_entry(e, counts[e["slug"]], base) for e in es) + "</section>")
    said = sum(1 for e in ENTRIES if counts[e["slug"]]["mentions"])
    return f"""
  <section class="glpage">
    <a class="back" href="{base}/">← the record</a>
    <h1>The words the record uses</h1>
    <p class="presslede">A meeting says “warrant article” and “free cash” a hundred times and never
      stops to say what they mean. These are the words the record hears most often and explains
      least — {n_of(len(ENTRIES), "entry", "entries")}, {said} of them said on this edition’s tapes —
      each in plain language, with where it applies, the public source to read, and how often the
      record says it. Every count opens the search for it.</p>
    <p class="gl-label">The definitions were written with Claude, Anthropic’s model, at the desk —
      not at press time and not in your browser — from the public source each entry names. If one
      reads wrong, the source is the authority, and a correction annotates the entry. The counts
      are the record’s own, whole-word over every transcript: no model counts them.
      <a href="{base}/ai">Our AI Constitution</a> keeps the ledger.</p>
    <nav class="gl-index" aria-label="every word, A to Z"><span class="kicker">A to Z</span> {index}</nav>
    {"".join(groups)}
  </section>
"""
