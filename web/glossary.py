"""The words the record uses, explained (specs/27 §3.4).

A four-hour meeting says "warrant article", "free cash" and "override" a
hundred times and never once says what they mean; a resident who does not
already know is locked out of the room they are reading. The glossary is
the key: each entry says what the word means in plain language, where it
applies (Brookline, Boston, the Commonwealth), where to read the public
source, and — the record's own contribution — how often the record says
it, when it first did, and the search that finds every line.

Two halves, labeled apart. The definitions were written with Claude
(Anthropic's model), through the coding assistant the developers used while
writing this code, paraphrasing the public source each entry names — never
at press time, never in a reader's browser; the ledger on /app/ai says so,
and so does the page. The counts are the press's, whole-word (web/topic.py's
own rule) over the transcripts of the towns each word belongs to, and no
model counts them. Corrections annotate, like everything on the record.

No person is defined here — the covenant keeps no person pages; bodies and
offices only.
"""

from __future__ import annotations

import re
from typing import Dict, List, Optional, Sequence

from .charts import esc, n_of

MGL = "https://malegislature.gov/Laws/GeneralLaws/PartI"
DLS = ("the state’s Municipal Finance Glossary", "https://www.mass.gov/info-details/municipal-finance-glossary")
BK_TM = ("Brookline — Town Meeting", "https://www.brooklinema.gov/264/Town-Meeting")
BK_SB = ("Brookline — Select Board", "https://www.brooklinema.gov/343/Select-Board")
BK_AC = ("Brookline — Advisory Committee", "https://www.brooklinema.gov/166/Advisory-Committee")
BK_HB = ("Brookline — Town Meeting Handbook", "https://www.brooklinema.gov/277/Town-Meeting-Handbook-PDF")
BK_OV = ("Brookline — the FY 2027–2029 override guide", "https://www.brooklinema.gov/3590/FY2024-26-Override-Central")
BOS_CC = ("Boston — City Council", "https://www.boston.gov/departments/city-council")
OML = ("the Attorney General — the Open Meeting Law", "https://www.mass.gov/the-open-meeting-law")
BOS_EA = ("Boston — the Enabling Act (St. 1956, c. 665)",
          "https://www.bostonplans.org/getattachment/f44de6aa-8b2b-4cae-b110-0dd502ebc2bd")


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
     "phrases": ["select board", "selectboard", "board of selectmen"], "sources": [BK_SB]},
    {"slug": "town-meeting", "group": "who", "term": "Town Meeting", "where": ["Brookline", "Massachusetts"],
     "says": "The town’s legislature. Brookline’s is a representative Town Meeting: 255 members elected by "
             "precinct — fifteen from each of seventeen, for three-year terms — joined by members who sit by "
             "office (the Select Board, the Moderator, the Town Clerk, and any state legislator who lives in town). "
             "It passes the budget and every bylaw. The annual meeting comes in late spring and a special one "
             "usually in the fall; anyone may watch, only members vote.",
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
     "phrases": ["planning board"],
     "sources": [law("M.G.L. c. 40A § 5 (zoning changes)", "TitleVII/Chapter40A/Section5"),
                 law("c. 41 § 81D (the master plan)", "TitleVII/Chapter41/Section81D")]},
    {"slug": "zoning-board-of-appeals", "group": "who", "term": "Zoning Board of Appeals (ZBA)", "where": ["Massachusetts"],
     "says": "The board that hears requests for variances, special permits and Chapter 40B comprehensive permits, "
             "and appeals of a building official’s zoning decisions — each at a public hearing. Boston’s Zoning "
             "Board of Appeal does the same work under the city’s own zoning law.",
     "phrases": ["zoning board of appeals", "zoning board of appeal", "ZBA"],
     "sources": [law("M.G.L. c. 40A § 14", "TitleVII/Chapter40A/Section14"),
                 law("c. 40B § 21 (comprehensive permits)", "TitleVII/Chapter40B/Section21"),
                 BOS_EA]},
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
     "short": "favorable action / no action",
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
             "simple majority, unless a law, a charter or a bylaw sets a different number.",
     "phrases": ["quorum"], "sources": [law("M.G.L. c. 30A § 18", "TitleIII/Chapter30A/Section18")]},
    {"slug": "roll-call", "group": "meeting", "term": "roll call", "where": ["Massachusetts"],
     "says": "A vote taken by calling each member by name, so that how each one voted — yes, no, abstain — is on "
             "the record. The record reads the roll calls it can hear on the tape; the official minutes are the "
             "last word.",
     "phrases": ["roll call", "roll-call"], "sources": [("the record — the votes", "/app/officials"), OML]},
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
             "lists, among them a person’s reputation, negotiations with staff outside a union, and — when an open "
             "meeting would hurt the body’s position and the chair says so — strategy for collective bargaining "
             "or litigation and the purchase or lease of real estate — entered by a roll-call vote in open "
             "session, with the reason stated.",
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
     "phrases": ["fiscal year", "FY26", "FY27", "FY28", "FY29", "FY30"], "sources": [DLS]},
    {"slug": "appropriation", "group": "money", "term": "appropriation", "where": ["Massachusetts"],
     "says": "A vote of Town Meeting or a city council that authorizes spending a set amount for a set purpose. "
             "Most public money is spent only as an appropriation allows; grants, gifts and revolving funds have "
             "rules of their own.",
     "phrases": ["appropriation", "appropriations"],
     "sources": [DLS, law("c. 44 § 53A (grants and gifts)", "TitleVII/Chapter44/Section53A")]},
    {"slug": "proposition-2-half", "group": "money", "term": "Proposition 2½", "where": ["Massachusetts"],
     "says": "The 1980 state law that caps a community’s property taxes. The most it may levy in a year — its "
             "levy limit — may grow by 2.5 percent plus new growth, and the limit may never pass 2.5 percent of the "
             "full value of all its taxable property, the levy ceiling. Voters can raise the limit with an "
             "override, or tax beyond it — even beyond the ceiling — for one project’s debt with a debt exclusion.",
     "phrases": ["proposition two and a half", "prop two and a half", "proposition 2 and a half",
                 "prop 2 and a half", "proposition 2 1/2", "prop 2 1/2", "proposition 2½", "prop 2½"],
     "sources": [law("M.G.L. c. 59 § 21C", "TitleIX/Chapter59/Section21C"), DLS]},
    {"slug": "levy", "group": "money", "term": "levy, levy limit", "where": ["Massachusetts"],
     "says": "The levy is what a community raises in property taxes in a year. The levy limit is the most "
             "Proposition 2½ lets it raise: last year’s limit, plus 2.5 percent, plus new growth, plus any "
             "override its voters approved. A debt exclusion’s payments ride on top of the limit, only while the "
             "debt lasts — so the law reads; the state’s glossary counts exclusions into the limit.",
     "phrases": ["levy"], "sources": [law("M.G.L. c. 59 § 21C", "TitleIX/Chapter59/Section21C"), DLS]},
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
     "says": "A community’s savings for the future — an emergency, a lean year, a large capital cost. Creating a "
             "fund or changing its purpose takes a two-thirds vote of Town Meeting or the council. Spending from the "
             "general stabilization fund takes two thirds; a fund set up for one named purpose can be spent by a "
             "simple majority. Putting money in takes a simple majority.",
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
     "says": "Usually a voluntary payment an institution exempt from property tax — a university, a hospital — "
             "makes to the city or town it sits in, in place of the taxes it does not owe; some are contracts "
             "instead. Boston asks its large nonprofits for one every year.",
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
     "says": "The rules for what may be built where — uses, heights, setbacks, parking. A town sets them in its "
             "zoning bylaw under the state’s Zoning Act; most changes take a two-thirds vote of Town Meeting (in "
             "another city, of its council), some housing changes a simple majority. Boston is the exception: its "
             "zoning code rests on a state law of its own, and its Zoning Commission, with the mayor — not the "
             "City Council — adopts changes.",
     "phrases": ["zoning"],
     "sources": [law("M.G.L. c. 40A (the Zoning Act)", "TitleVII/Chapter40A"), BOS_EA]},
    {"slug": "overlay-district", "group": "built", "term": "overlay district", "where": ["Massachusetts"],
     "says": "A zone drawn over the existing zoning that adds rules or allows more — denser housing near transit, "
             "a historic area’s protections — without erasing the zoning beneath it.",
     "phrases": ["overlay district", "overlay districts", "overlay zoning"], "aka": ["overlay"],
     "sources": [law("M.G.L. c. 40A", "TitleVII/Chapter40A")]},
    {"slug": "special-permit", "group": "built", "term": "special permit", "where": ["Massachusetts"],
     "says": "Permission for a use or a building the zoning allows only case by case, granted by a named board "
             "after a public hearing — often with conditions.",
     "phrases": ["special permit", "special permits"], "sources": [law("M.G.L. c. 40A § 9", "TitleVII/Chapter40A/Section9")]},
    {"slug": "variance", "group": "built", "term": "variance", "where": ["Massachusetts"],
     "says": "Permission to depart from the zoning’s own terms — a setback, a height — granted only where the "
             "soil, shape or topography of that particular lot, and not the district around it, would make the "
             "rule a substantial hardship, and only if the relief does no substantial harm to the public good or "
             "to the bylaw’s purpose. A use the district forbids needs a bylaw that allows use variances at all.",
     "phrases": ["variance", "variances"], "sources": [law("M.G.L. c. 40A § 10", "TitleVII/Chapter40A/Section10")]},
    {"slug": "chapter-40b", "group": "built", "term": "Chapter 40B", "where": ["Massachusetts"],
     "says": "The state law that lets a developer who sets aside a share of new homes as affordable ask the Zoning "
             "Board of Appeals for one comprehensive permit in place of the separate local approvals. If the board "
             "refuses, or sets conditions that make the homes uneconomic, the developer can appeal to the state’s "
             "Housing Appeals Committee, which can overrule it — unless the community has met the law’s safe "
             "harbors, chiefly 10 percent of its housing counted as affordable.",
     "phrases": ["40B"],
     "sources": [law("M.G.L. c. 40B §§ 20–23", "TitleVII/Chapter40B/Section20"),
                 law("§ 22 (the appeal)", "TitleVII/Chapter40B/Section22")]},
    {"slug": "mbta-communities", "group": "built", "term": "MBTA Communities (Section 3A)", "where": ["Massachusetts"],
     "says": "The 2021 state law that requires 177 cities and towns in and around the MBTA’s service area — "
             "Boston, served by the MBTA but outside the Zoning Act, is not one of them — to have at least one "
             "zoning district of reasonable size (at least 15 homes an acre, and where a town has a station, in "
             "part within half a mile of it) where multifamily housing open to families is allowed as of right, "
             "without a special permit.",
     "phrases": ["MBTA communities", "section 3A"],
     "sources": [("Massachusetts — the MBTA Communities law", "https://www.mass.gov/info-details/multi-family-zoning-requirement-for-mbta-communities"),
                 law("M.G.L. c. 40A § 3A", "TitleVII/Chapter40A/Section3A")]},
    {"slug": "housing-trust", "group": "built", "term": "affordable housing trust", "where": ["Massachusetts", "Brookline"],
     "says": "A fund a city or town sets up to create and keep homes that people of modest means can afford, "
             "governed by its own board of trustees.",
     "phrases": ["housing trust"], "sources": [law("M.G.L. c. 44 § 55C", "TitleVII/Chapter44/Section55C")]},
    {"slug": "article-80", "group": "built", "term": "Article 80", "where": ["Boston"],
     "says": "The part of Boston’s zoning code that sets how a larger development is reviewed — small projects "
             "over 20,000 square feet or 15 homes, large ones over 50,000, planned development areas and "
             "institutions’ master plans: its public meetings, the city’s review of its design and impacts, and "
             "the vote that approves it.",
     "phrases": ["article 80"], "sources": [("Boston — what is Article 80", "https://www.bostonplans.org/projects/development-review/what-is-article-80")]},
    {"slug": "vision-zero", "group": "built", "term": "Vision Zero", "where": ["Boston", "Brookline"],
     "says": "A traffic-safety policy with one goal — no one killed or seriously hurt on the streets (Boston’s "
             "target is 2030) — pursued through lower speeds, safer street design and close study of where "
             "crashes happen.",
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

# Has a person read these definitions against their sources? Until one has,
# the page says so (Our AI Constitution: AI drafts, people decide).
REVIEWED = False
# The model that wrote them, named the way every other ledger row names one
# (web/emit.py page_ai reads MODEL — the ledger and the page cannot differ).
MODEL = "claude-opus-5-5"
WRITTEN_WITH = f"Claude (Anthropic, {MODEL})"


def q_of(e: dict) -> str:
    """The search an entry's count is a receipt for: its first phrase."""
    return e["phrases"][0]


def towns_of(e: dict) -> Optional[set]:
    """Where an entry's word means what it says: None (every town) for a
    Massachusetts word; else only its own towns — a Brookline word said in
    Boston's council (\"the advisory committee\") is another thing."""
    return None if "Massachusetts" in e["where"] else set(e["where"])


# an acronym that spells an ordinary word matches only as written ("PILOT"
# the payment, never "pilot" the program); every other one is the same word
# in any case — the analyzer's topic names are lowercase ("zba", "40b")
_AS_WRITTEN = {"PILOT"}


def _names(e: dict) -> set:
    """The phrases a lede may name an entry by: its counted phrases, the
    names in its heading, and any it is also called (`aka`, never counted)
    — lowercased, but for an acronym that spells a word."""
    names = {p.lower() for p in e["phrases"] if p not in _AS_WRITTEN}
    for t in e["term"].split(","):
        t = t.split("(")[0].strip()
        if t and t not in _AS_WRITTEN:
            names.add(t.lower())
    return names | {a.lower() for a in e.get("aka", ())}


def _acronyms(e: dict) -> set:
    """An entry's all-capital names (PILOT, ZBA, DESE), which match only as
    written."""
    heads = {t.split("(")[0].strip() for t in e["term"].split(",")}
    return {x for x in heads | set(e["phrases"]) if x and x.isupper()}


def entry_for(phrase: str) -> Optional[dict]:
    """The entry that explains a phrase the record uses — one of its phrases
    or heading names, a plural folded ("warrant articles", "levies"); an
    acronym only as written. None when the glossary has no such word."""
    raw = " ".join(str(phrase or "").split())
    k = raw.lower()
    if not k:
        return None
    # the plural folded both ways: "levies" → levy, "MBTA community" → communities
    keys = [k]
    if k.endswith("ies"):
        keys.append(k[:-3] + "y")
    elif k.endswith("s"):
        keys.append(k[:-1])
    if k.endswith("y"):
        keys.append(k[:-1] + "ies")
    elif not k.endswith("s"):
        keys.append(k + "s")
    for e in ENTRIES:
        if raw in _acronyms(e):
            return e
    for key in keys:
        for e in ENTRIES:
            if key in _names(e):
                return e
    return None


def _search(q: str, base: str, town: str = "") -> str:
    from .charts import search_url
    return search_url(q, town, base)


def _lines(m: dict) -> List[tuple]:
    """A meeting's lines as the search index holds them: blank ones skipped
    (web/bake.py bake_search), so a count here and a count there agree."""
    return [(float(s.get("start") or 0), str(s.get("text") or ""))
            for s in (m.get("segments") or []) if str(s.get("text") or "").strip()]


def _night(lines: List[tuple]) -> tuple:
    """A meeting's lines lowercased, where each starts, and the whole night
    joined by single spaces — built once a meeting, read by every entry."""
    texts = [t.lower() for _, t in lines]
    starts, pos = [], 0
    for t in texts:
        starts.append(pos)
        pos += len(t) + 1
    return texts, starts, " ".join(texts)


def _night_counts(lines: List[tuple], pats: Sequence, night: Optional[tuple] = None) -> tuple:
    """(mentions, first_t) for one meeting — the story engine's rule
    (web/topic.py mentions_in: a line read with the next joined on, a match
    counted for the line it starts in) done in one pass per phrase over the
    whole night rather than one per line: each match placed on its line by
    offset, and a match that runs past the next line dropped (mentions_in
    never sees a third line). A phrase is trimmed (a test holds it), so no
    match starts on a joining space. Identical counts; a twin test holds
    them to the per-line rule."""
    import bisect
    texts, starts, joined = night or _night(lines)
    n, first_i = 0, None
    for pat, lit in pats:
        if lit not in joined:
            continue
        for mt in pat.finditer(joined):
            li = bisect.bisect_right(starts, mt.start()) - 1
            last = li + 1 if li + 1 < len(texts) else li
            if mt.end() > starts[last] + len(texts[last]):
                continue                                  # runs past the next line
            n += 1
            first_i = li if first_i is None else min(first_i, li)
    return n, (lines[first_i][0] if first_i is not None else None)


def count(meetings: Sequence[dict]) -> Dict[str, dict]:
    """How often the record says each entry's words — whole-word, case-blind,
    by the story engine's rule — town by town, only in the towns the word
    belongs to, with the meetings and where it first came up. Pure."""
    from .topic import phrase_re
    pats = {e["slug"]: [(phrase_re(p), p.lower()) for p in e["phrases"]] for e in ENTRIES}
    out: Dict[str, dict] = {e["slug"]: {"mentions": 0, "meetings": 0, "towns": {}, "by": {}} for e in ENTRIES}
    # a day that is not a whole date ("2026", "TBD") is undated, and sorts last:
    # it can never be where a word was "first" said
    dated = sorted(meetings, key=lambda m: (_whole_day(m.get("date")) or "9999", str(m.get("pid") or "")))
    for m in dated:
        lines = _lines(m)
        if not lines:
            continue
        night = _night(lines)
        town = str(m.get("town") or "")
        for e in ENTRIES:
            scope = towns_of(e)
            if scope is not None and town not in scope:
                continue
            n, first_t = _night_counts(lines, pats[e["slug"]], night)
            if not n:
                continue
            r = out[e["slug"]]
            r["mentions"] += n
            r["meetings"] += 1
            r["by"][m["pid"]] = n
            t = r["towns"].setdefault(town, {"mentions": 0, "meetings": 0, "first": None})
            t["mentions"] += n
            t["meetings"] += 1
            if t["first"] is None:
                t["first"] = {"pid": m["pid"], "date": _whole_day(m.get("date")), "t": first_t}
    return out


def index(counts: Dict[str, dict]) -> List[dict]:
    """glossary/index.json — what the search page needs to count an entry's
    words the glossary's way: the query each count links to, its phrases,
    the towns it was counted in. Only entries the record says."""
    return [{"slug": e["slug"], "q": q_of(e), "phrases": list(e["phrases"]),
             "towns": sorted(counts[e["slug"]]["towns"]),
             "only": sorted(towns_of(e) or ())}          # [] = every town
            for e in ENTRIES if counts[e["slug"]]["mentions"]]


def _short(e: dict) -> str:
    """An entry's first name, for a line of names ("warrant", not
    "warrant, warrant article" — a comma in a list of names reads as two) —
    or its own short name, where the names are two different words."""
    return e.get("short") or e["term"].split(",")[0].strip()


def terms_on(m: dict, counts: Dict[str, dict], top: int = 6) -> List[dict]:
    """The glossary's words one meeting says most — for the line on its page
    that says where they are explained."""
    rows = [(counts[e["slug"]]["by"].get(m["pid"], 0), e) for e in ENTRIES]
    rows = [(n, e) for n, e in rows if n]
    rows.sort(key=lambda r: (-r[0], r[1]["term"].lower()))
    return [{"slug": e["slug"], "term": _short(e), "n": n} for n, e in rows[:top]]


_DAY = re.compile(r"^\d{4}-\d{2}-\d{2}")


def _whole_day(d) -> str:
    """A meeting's day when it is a whole date (YYYY-MM-DD…), else ""."""
    d = str(d or "")
    return d[:10] if _DAY.match(d) else ""


def _day(d: str) -> str:
    from .story import day_name
    return f"on {day_name(d)}" if _whole_day(d) else "in an undated meeting"


def _entry(e: dict, c: dict, base: str) -> str:
    def src(name: str, u: str) -> str:
        rel = "" if u.startswith("/") else ' rel="noopener"'     # built first: an f-string holds no backslash
        return f'<a href="{esc(u)}"{rel}>{esc(name)}</a>'
    srcs = " · ".join(src(name, u) for name, u in e["sources"])
    where = "".join(f'<span class="gl-where">{esc(w)}</span>' for w in e["where"])
    towns = sorted(c["towns"].items(), key=lambda kv: (-kv[1]["mentions"], kv[0]))
    if towns:
        # every count opens the search that finds it — but meetings with no
        # town recorded: no search can be pinned to them, so theirs is said
        def said(t: str, r: dict) -> str:
            n = n_of(r["mentions"], "time")
            return f'<a href="{esc(_search(q_of(e), base, t))}">{n}</a>' if t else n
        rec = " · ".join(
            f'{esc(t or "meetings with no town recorded")}: {said(t, r)} in '
            f'{n_of(r["meetings"], "meeting")}, first '
            f'<a href="{base}/m/{esc(r["first"]["pid"])}#t{int(r["first"]["t"] or 0)}">{esc(_day(r["first"]["date"]))}</a>'
            for t, r in towns)
    else:
        rec = "not yet — the record has not heard it said"
    notes = "".join(f'<p class="gl-note"><span class="kicker">corrected {esc(d)}</span> {esc(t)}</p>'
                    for d, t in e.get("notes") or [])
    return (f'<section class="gl-entry" id="{esc(e["slug"])}">'
            f'<h3 class="gl-term">{esc(e["term"])}</h3><p class="gl-wheres">{where}</p>'
            f'<p class="gl-says">{esc(e["says"])}</p>{notes}'
            f'<p class="gl-src"><span class="kicker">read the source</span> {srcs}</p>'
            f'<p class="gl-rec"><span class="kicker">on the record</span> {rec}</p></section>')


def body(meetings: Sequence[dict], base: str = "/app", counts: Optional[Dict[str, dict]] = None) -> str:
    counts = counts if counts is not None else count(meetings)
    az = sorted(ENTRIES, key=lambda e: e["term"].lower())
    idx = " ".join(f'<a href="#{esc(e["slug"])}">{esc(e["term"])}</a>' for e in az)
    groups = []
    for key, title in GROUPS:
        es = [e for e in ENTRIES if e["group"] == key]
        groups.append(f'<section class="gl-group" id="gl-{key}"><h2 class="gl-gtitle">{esc(title)}</h2>'
                      + "".join(_entry(e, counts[e["slug"]], base) for e in es) + "</section>")
    said = sum(1 for e in ENTRIES if counts[e["slug"]]["mentions"])
    reviewed = ("A person has read every entry against its source."
                if REVIEWED else
                "No person has yet read them against their sources — until one has, read each "
                "entry as a first draft and its source as the definition.")
    return f"""
  <section class="glpage">
    <a class="back" href="{base}/">← the record</a>
    <h1>The words the record uses</h1>
    <p class="presslede">A meeting says “warrant article” and “free cash” dozens of times and never
      stops to say what they mean. These are words the record uses and seldom explains —
      {n_of(len(ENTRIES), "entry", "entries")}, {said} of them said on this edition’s tapes —
      each in plain language, with where it applies, the public source to read, and how often the
      record says it, town by town. Every count opens the search that finds it.</p>
    <p class="gl-label">The definitions were written with {esc(WRITTEN_WITH)} — on Anthropic’s
      servers, through the coding assistant the developers used while writing this code; never at
      press time, never in your browser. Each names the public source it draws on, and where the
      two differ the source is the authority. {reviewed} A correction is dated beside the entry it
      changes. The counts are the record’s own, whole-word over the transcripts of the towns each
      word belongs to: no model counts them. <a href="{base}/ai">Our AI Constitution</a> keeps the
      ledger.</p>
    <nav class="gl-index" aria-label="every word, A to Z"><span class="kicker">A to Z</span> {idx}</nav>
    {"".join(groups)}
  </section>
"""
