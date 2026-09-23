# 24 — The front page is the story: one meeting, or the record over time

**Status:** v1.0 · **Stage:** BUILT on branch `story-paths` (on top of
`nightly-intake`, on top of the v2.1.15 fold), 584 tests green, pane-checked
on a local twin of the live corpus (12 meetings, 60 issues, 27 roll calls).
Targets **v2.1.16 / r38** together with the nightly-intake change.
**Owner:** Stephen Walter (Weird Machine) · **Related:** specs/20 (the reader),
specs/21 (the studio + your paper), specs/23 (the open newsroom — A–C live),
`CLAUDE.md` (the laws), `record/OPERATING.md` (deploy, nightly intake).

## 1. Problem — the making half was findable, and the front page said nothing

specs/23 A put a real door on the front page; C gave the paper a rich tier.
Stephen's verdict (2026-09-23, after v2.1.14, then sharpened the same
evening): *the front page leads with an embedded video and no narrative; the
studio does not feel customizable; a citizen cannot see what a data story
from the record looks like, so cannot want to make one; the two ways of
reading the record — one meeting, or many over time — are not named; and a
reader cannot tell when they are reading and when they are editing.* Then:
*"I want a full front page story crafted, complete with data visualizations
and commentary of meetings over time, and a toggle for one that is just the
most recent meeting … extremely rich and detailed stories to inspire others
to use powerful search and visualization features … make the navigation
clearer so a user knows when they are in read mode vs edit mode."*

Read against the code, every point held: `page_home` led with a 960×540
still and two pull-moments; the templates were one card, one chart and an
empty note; the meeting plane's decisions, questions, pushback, moments,
roll calls, filings, framing and labeled summary went unused on the front
page; and the mode lived in a corner pill.

## 2. What was built — build to this, extend from this

### 2.1 The front page IS the story (`web/story.py`, `web/charts.py`, `page_home`)

Two stories, pressed whole at press time, both real HTML with the script
off; with it on, a tab strip shows one at a time and remembers the choice in
this browser (`cz-front-story`) and nowhere else.

**Story one — the record, over time.** A counted headline ("12 meetings,
63.9 hours, 27 roll calls — the record since December 2025"), a counted
lede (the bodies and towns, the longest thread, the roll calls passed and
failed with the latest one quoted, the busiest month, the lean of the talk
across the record, what keeps coming back), then, each with a line of
commentary that says what the picture says:

| picture | what it is | from |
|---|---|---|
| the record, by the numbers | six counts, each a receipt; meetings by month | `stats` |
| votes over time | one dot per roll call, stacked by meeting, filled passes / hollow fails / half-tone other; the latest four as a teaser | `meetings[].votes` |
| the long view, month by month | small multiples: the six widest issues, a bar per month, each a receipt into that month's meeting | `issues[].timeline` |
| how the talk was framed | a heat strip: eight lenses × every meeting, depth = share | `analytics.framing` |
| what keeps coming back | magnitude bars of the record-wide topics; each name is the record's search for it | `analytics.topics` |
| the record in words | a word cloud, deterministic (a fixed spiral, monospace metrics), every word a search | every meeting's transcript, the analyzer's counter |
| what changed, last time | the resurfacings | `stats.resurfacings` |

It closes with *make this story yours →* (the roll-calls template) and four
issue starts (path two).

**Story two — the latest meeting, what happened.** The labeled summary as
the lede (an AI summary, labeled / a summary drawn from the tape), then a
counted commentary — how long the night ran, what the analyzer found, the
loudest moment quoted with its time and kind, the lean of the talk and its
drift, the money on the table, who was named more than once, what the town
filed — then: the meeting in numbers; **the shape of the meeting** (the tape
as one strip, a bar for a roll call, a triangle for a decision, a diamond
for pushback, a dot for a question, each a deep link, with a table twin);
the moments that decided it; the roll calls (or the honest line); the eight
lenses with drift; the questions by type; the meeting in words (a cloud;
each word opens the tape at its first mention); **where the words fell**
(the highlighter's sparkline search, pressed: the night's topics slice by
slice, each bar a deep link); who and what was named; the filings; the
still at card size with *▶ the tape · loads only when you press it*. It
closes with *make this story yours →* (the meeting template) and *read the
meeting →*.

Every number in both stories is a receipt into the page that holds it.
Every sentence is a rule over the pressed planes — the commentary is
**counted, never modeled**, and each story says so beneath its lede. The
only model-drafted words on the page are the summary, labeled as they are
everywhere on the record. The pictures are pressed SVG or HTML in the paper
palette (deep green measurement, slate labels, ink text; no studio hue,
no chrome — the byte-clean guard sweeps the page), byte-identical press to
press (idempotence holds: no randomness anywhere).

### 2.2 The two paths, in the studio (`applyPaperTemplate`, the new kinds)

*Make this story yours* opens the same story as a draft, block for block:

- **Path one — one meeting, what happened**: the story (lead), the meeting
  in numbers, the shape of the meeting, the three moments that decided it
  (the loudest roll call / decision / pushback, never two from one second)
  as pull-quotes, this meeting's roll calls, how it was framed, the record's
  reading, up to three filings, the note. A block whose plane holds nothing
  is not written.
- **Path two — over time, how it moved**: the issue (lead), the issue in
  numbers, its reach, what changed (a digest of six), every roll call along
  the way, *then and now* (the first appearance's bead and the latest's, as
  half-width quotes), the record's reading meeting by meeting, the note.

The paper's new kinds — refs and enums like every kind before them, exact
keys, no new free text (`record/papers.py`): `chart·numbers` (a pid or a
slug, exactly one), `chart·shape` (pid), `chart·ledger` (slug), `chart·votes`
with a pid (one meeting's roll calls), and `reading` (a pid or a slug). Link
forms: `c.numbers.m%3A<pid>` / `c.numbers.i%3A<slug>`, `c.shape.<pid>`,
`c.ledger.<slug>`, `c.votes.<pid>`, `a.m%3A<pid>` / `a.i%3A<slug>`; a paper
carrying one travels `v=4`. The shipped reader drops what it does not know
(fewer blocks, never a throw). Renderers in the reader: the numbers strip,
the shape (the JS twin of the pressed one), one meeting's roll calls, an
issue's ledger, and **the record's reading** — decisions with their
outcomes, questions by type, the pushback, who and what was named (a
meeting); the milestones in order (an issue) — extractive, receipts
throughout, no model. The panel's chart menu, the on-page add-search's hit
buttons (▤ numbers · ▤ shape / ▤ ledger · ✎ the reading) and the export
(`paper.json`, each block with its record URL) carry them all.

### 2.3 The writing desk

Beside every note in the on-page editor: three prompts rotate in the
placeholder (*what was decided, and who moved it? · what changed since the
last time? · what should a neighbor watch for next?*), and a **facts at
hand** drawer — the numbers, the loudest moments, the roll calls, an issue's
span and its latest word — drawn from the planes this paper's own blocks
already fetched (`PAPER_PLANES`), nothing fetched for it. A press cites a
fact at the caret as a receipt (`[1:52:55] “…” — Brookline School Committee,
2026-06-18`); the sentence around it stays the editor's. No draft is ever
inserted into a note by the software.

### 2.4 The mode bar

Under the section line, in preview and studio modes (paper mode carries no
chrome): **READING THE RECORD — nothing here changes until you press Edit**
/ **EDITING — THE STUDIO — what you add lands in your paper, in this browser
— nothing is uploaded**, with a Read / Edit radiogroup (aria-checked, roving
tabindex, arrow keys — the footprint control's own contract), painted from
`shownMode()` (the painted truth), never from storage. In the studio the bar
takes the studio's own accents, and only there.

## 3. Bounds — the laws, precisely

- **Byte-clean**: the stories and the paths are baked content (`fp-`, `stab`,
  `sp-` namespaces — grep-checked free); the mode bar and every affordance
  are script-added; the guard sweeps the page.
- **Store**: enum values and ref-only kinds only. No new free text.
- **Covenant**: the make path touches no server; the desk reads what the
  paper already fetched; the door count is unchanged.
- **Palette**: deep green measurement everywhere on the pressed page; the
  studio's accents only under `html.cz-m-studio` (the mode bar included).
- **Idempotence**: every picture is a pure function of the planes.
- **A11y**: every mark is an `<a>` with a name and a table twin; the tabs are
  links that work without the script; the desk's facts are buttons.
- **The constitution**: no AI use changed. The ledger's "no model at all" row
  still reads true of the front page, the reading, the desk and the pictures.

## 4. What is Stephen's (never unprompted)

- **Ship it**: v2.1.16 / r38 — this branch, which carries the nightly-intake
  change too (OPERATING §5; press `--version 2.1.16`; all five jobs and the
  service to r38; the Pages sync; the tag).
- **A model-drafted analysis** beside the summary (*what it means, who moved
  it, what to watch*, with receipts) — spend and a ledger row in the same
  commit; the `reading` block is where it would render, under its own label.
  The extractive reading ships now.
- **A `record` template** (the over-time story as a draft in one press,
  beyond the roll-calls shape) — a small follow-on once the story has been
  read on the live record.

## 5. Verification

584 tests: the store accepts each new block and refuses each malformed
neighbour; the link codec round-trips every new form and drops every mangle;
the featured papers match the JS codec byte for byte; the front page bakes
both stories with every picture and the toggle, in the paper palette, with
the counted sentences; the constitution's wording is pinned; the mode
control stays a radiogroup. Pane-checked on the local twin at phone width:
the tabs toggle and remember; the votes dots, the small multiples, the heat
strip, the topic bars and the cloud read; the latest story's shape, pulls,
lenses, questions, cloud and sparklines read; Edit opens the studio with
its accents; Read returns.
