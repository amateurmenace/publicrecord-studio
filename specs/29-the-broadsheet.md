# 29 — The civic broadsheet: the record as a front page, search as its spine, writing in the same style

**Status: P0 BUILT + LIVE (2026-09-24, v2.2.0 / r47); P1 BUILT + LIVE
(2026-09-24, v2.2.1 / r48 — the studio as the board, six blocks, five
templates); P2 BUILT (2026-09-24, v2.2.2 / r49 — the gallery); the four open decisions made and shipped (2026-09-24, v2.2.3 / r50); *said alongside it* built (2026-09-24, v2.2.4 / r51) — specs/29 whole.** The mockup is a design canvas:
<https://claude.ai/artifact/HgMxn4cApHgdYqu5P1aGJy> (nine boards; private to
Stephen until shared). This file says what the boards say, so a session can
build without the canvas, and ends with the prompt that starts that session.

## Why

Stephen, 2026-09-24: the site is "too lifeless, too much text down a single
column, too stacked, too confusing." He liked the broadsheet direction and
asked for three more things: **more interactivity — search built into the
read version**; **the interface for writing a front page in the same style**,
balancing what the record and other readers have made against a reader's
own; and **more templates**, the issue-over-time story first.

## The look (one nameable system)

- **Type.** Fraunces (display; headlines, card titles, the wordmark "The
  Public Record"), IBM Plex Sans (reading), IBM Plex Mono (numbers, kickers,
  receipts). Self-hosted in the edition, never a font CDN on the reader page.
- **Colour.** Paper `#F3EEE3`, card `#FBF9F4`, ink `#191712`, ink-2
  `#4B473E`, muted `#6F6A5B`, rule `#D9D1BF`. **Boston blue `#1F4E79`** (light
  `#DEE8F3`), **Brookline green `#1E5E3F`** (light `#DDEBE1`) — a
  municipality's colour is on every card top, kicker and dot that belongs to
  it. **Rust `#B23A1D`** is the one action colour and it means *writing*:
  the Edit stamp, the "Write your own" nav item, receipts `[1:46:50]`, block
  frames in the studio. The eight lens colours stay `analytics.lens_color`.
  Zero fuchsia on the record; the studio's purples never reach a pressed page.
- **Grid.** 1440 wide, 56 px margins, twelve columns, 24 px gutters; section
  rules are a 2 px ink line with a Fraunces heading and a mono link at the
  right. Phone (390) stacks the same order.
- **Stamps.** Every screen's top bar carries a mode stamp: ink `READ · the
  record`, rust `EDIT · your front page · nothing here changes the record`.
  The nav has five words on the reading side and one rust word on the
  writing side, with a mono hint between them.

## The boards

1. **Front page — read** (`Main`, interactive — press Play). Masthead: wordmark, one-line promise,
   the municipality switch (Boston · Brookline · The whole record, with
   counts). **The search spine**: a 56 px search box under the wordmark
   ("Search the record — a word, a name, a street, a vote. Every hit is a
   moment you can play."), six "try" chips, and the sentence *everything you
   see is a search — click a name, a place, a thread*. Then, on the grid:
   - **Tonight's tape** — the video is the sun and the record reads it
     around and beneath it. Cols 1–8: the frame, large (880×495), with a
     "Play from …" chip and the current caption in italic over its foot;
     under it **the score of the night**: the tape as a timeline with the
     decisions as dots sized by weight, tension in rust, every dollar figure
     the room named as a labelled tick, and eight thin lanes — one per lens —
     showing where that lens's words fell; a rust playhead. Cols 9–12: the
     headline, the counted lede, a *now at …* card (the nearest moment's
     caption and why the record marked it), and **money named on the tape**
     as a clickable list ($1 million, said 8 times, at 15:59 …). Across all
     twelve: **the filmstrip** — three real frames from inside the tape
     (YouTube's own hq1/hq2/hq3), each with the decisions that fall in its
     third. Clicking anything — a lane tick, a dollar, a decision, a frame —
     moves the playhead, the caption and the frame together. State: `t`.
   - **The year in tapes**: every meeting as its own still, placed on a
     December-to-September axis and sized by its length, town-coloured on
     its top edge; four chapter pills (December — the budget night · Winter
     into spring — the roll calls · June — the marathons · September — Boston
     arrives) re-light the strip and set an italic counted paragraph; click a
     still and it names the meeting. State: `chapter`, `pick`.
   - **Four columns — each a story you can delve into** (the newspaper
     band, hairlines between): *Two towns, two vocabularies* (a butterfly of
     each town's lens shares — Boston gives community twice Brookline's
     share; Brookline gives money 37%), *Who, and when* (names and streets
     as a dot matrix over the months), *The roll calls* (27 squares by
     month, the ayes in each, the one that failed in rust), *Warrant season*
     (five tiny stills and the sparkline). Each ends in a rust "delve →".
   - **How the talk flowed, meeting by meeting**: the eight-lens river,
     refined — bands separated by a hair of paper, each lens labelled at its
     widest point, a dashed line where Boston joins the record.
   - **Front pages — the record's own, and readers'**: five cards — tonight's
     meeting covered, the roll calls watched, the longest thread watched (the
     three `featured_papers` that exist today), one reader's page, and the
     ink door *Write your own front page*.
   - **This week on the record**: meeting cards with stills, town-coloured.
   - **Threads**: six small multiples (`analytics.topics`, artifacts
     filtered), each with *tell its story →*.
   - **How they talked** (the lens heat strip; cells are links) beside **Who,
     and where** (names and places; each a search).
   - **Now tell yours**: One meeting · An issue over time · Five more
     templates, with the rust line *everything past this line is writing*.
2. **Search as you type** (`Typeahead`). The spine's panel, drawn open for
   "housing trust": three columns — *moments that say it* (▶ timestamp,
   the caption, who/when; ↑↓ ↵ ⇥ keys; "all N moments, as a reel →"),
   *meetings that took it up* (still, title, first said at) and *threads*,
   and *over time* (a sparkline, "Tell it as a story", "Start a front page
   from it"), with the line *searches never leave your browser: the index
   ships with the edition*.
3. **Front page — phone** (`Phone`): the same order, the spine second.
4. **A meeting — read** (`Meeting`): town-coloured header, the still, **the
   shape of the tape** as a jump bar (decisions as dots above, questions as
   ticks, tension as rust marks, lens moments coloured on the bar; click to
   jump), *Find in this meeting*, the moments that decided it, and a rail:
   what happened (labeled), in numbers, the framing, what they kept saying,
   questions on the record.
5. **A word over time — read** (`Search`): the query as a Fraunces field,
   town filter, a counted headline, the timeline of meetings (town-coloured
   dots, click to jump), the reel with stills, said-alongside, *Tell it*.
6. **A reader's front page — issue over time, read** (`IssueOverTime`): the
   filled template as readers get it: kicker, headline, counted lede, three
   labels, the timeline, *What it means — the writer* (three paragraphs
   with receipts), the reel, the framing, said-alongside, *search inside
   this front page's meetings*, the ink door *Make your own from the same
   receipts*. Footer: what is the record's, what is the writer's, no model.
7. **Templates — edit** (`Templates`): eight cards — One meeting · An issue
   over time · A vote and its history · A person on the record · A place on
   the record · Two towns, side by side · The year so far · Blank broadsheet
   — each with what it draws, the three questions it asks, a mini chart.
8. **Writing a front page — the studio, edit** (`Studio`): rust stamp; the
   title as a Fraunces field; *stored: the title, your notes, and references
   — nothing else*. Three columns: the **block shelf** (Lead story, Over
   time, This week, Threads, How they talked, Who and where, A reel, A quote,
   Roll calls, In numbers, Your paragraph, Search box — drag handles); the
   **page** in the broadsheet style with rust dashed **block frames** (a
   label pill, ↑ ↓ ×) and a *+ add a block here*; the **writing desk**
   (facts you can cite — click to insert; a labeled draft on request; the
   template's three questions). Buttons: Preview as readers see it · Share
   as a link.
9. **Front pages — the gallery, read** (`FrontPages`): filters (Everything ·
   The record's own · Readers' · Boston · Brookline · This week · Issues over
   time · One meeting), one card design for both kinds, unsigned by design,
   judged by receipts; a steward can take one down.

## The rules the build keeps

- The reader is static files the press writes; the toggles are links; a
  page reads with scripts off. The opening's interactivity (chapters, the
  picked dot, the isolated lens) is `app.js` over numbers the press already
  ships in `analytics.json`; with scripts off the chart shows the last
  chapter and all eight lenses, and the chapter buttons are anchors. The search spine and type-ahead are
  progressive: the box submits to the search page without scripts, and
  `app.js` adds the panel over the index that already ships.
- Stills are **pressed into the edition** (`app/stills/<pid>.jpg` plus the
  three in-tape frames `<pid>-1..3.jpg`, fetched by the press from the
  video's poster and storyboard frames) — never hot-linked, so the reader
  page still loads nothing from a third party. Sizes: ~20 KB each.
- The store stays strict: a front page stores its title, the writer's
  notes and refs. New blocks are ref-only kinds (`lead:<pid>`, `week`,
  `threads`, `strip`, `names`, `search`). Any new stored free text is
  Stephen's sign-off first. Shared pages are unsigned — the record keeps no
  reader identity; a writer who wants a name types it in the title.
- `/app/ai`'s ledger changes in the same commit as any change to what a
  model does (the desk's draft is already there).
- Every deploy bumps the press `--version`; every job moves; tag, push.

## Build plan (three deploys)

**P0 — the broadsheet read.** `web/emit.py::page_home` re-laid on the grid
with the sections above; `web/story.py` keeps the words, `web/charts.py`
gains the stills, the jump bar and the timeline; `record/press.py` presses
stills; the municipality switch everywhere (it exists; make it the masthead
control); the mode stamps (`paintModeBar` becomes the stamp); the search
spine + type-ahead in `web/static/app.js` over the shipped index (the topic
story's `tpAggregate` is the over-time sparkline); the meeting page's jump
bar and find-in-meeting; phone. Tests: twins for the new charts, the
type-ahead grouping, the spine's no-script submit, byte-clean pressed pages,
zero fuchsia. Version 2.2.0.

**P1 — writing in the same style.** The studio restyled as the board: the
block shelf, block frames, the desk; `applyPaperTemplate` grows five
templates (vote history, person, place, two towns, year so far) as block
lists + three questions each; the issue-over-time template redrawn to board
6; new ref-only kinds in `record/papers.py`; `v=5` links; decoders keep
decodeReel's law. Version 2.2.1.

**P2 — the gallery.** The press lists shared pages from the store and
presses cards (title, made-from counts, refs → the first still) beside the
record's own; the gallery page with filters; takedown stays the steward's;
the front page's strip reads from it. Version 2.2.2.

Each: review (lenses → skeptics → fold → re-review), deploy by OPERATING §5.

---

## The prompt for the session that builds it

Open a session in a checkout of github.com/amateurmenace/publicrecord-studio
(`.venv` on python3.11 — `python3.11 -m venv .venv && .venv/bin/pip install
-r requirements.txt`; system python is 3.14). Read, in this order: `CLAUDE.md`
(the laws), `specs/29-the-broadsheet.md` (the design in words, the rules, the
plan), `specs/next-session-prompt.md` (where things stand), `record/OPERATING.md`
§5 (the deploy). The design canvas is
<https://claude.ai/artifact/HgMxn4cApHgdYqu5P1aGJy>: read it with the Artifact
tool's read action — its `project/*.dc.html` files are the boards, real HTML
with real numbers from the live edition; `project/Main.dc.html` is the front
page and its `<script data-dc-script>` block shows exactly how the score, the
year in tapes and the filmstrip respond to clicks. The colours, type, grid and
copy on the boards are the spec. Every number on them is the live record's;
never invent one when you build.

**Before anything.** `git worktree list` and `git status` — other sessions
work in the main checkout; build in a worktree on your own branch
(`broadsheet-p0`). Run `ListAgents`; if a session named for publicrecord is
listed, tell it which image tag and press version you are taking and ask
what it has in flight. Suite green first
(`.venv/bin/python -m unittest discover -s tests -t . -q`). Read the live
front page and one meeting page at <https://publicrecord.studio/app/> so you
know what you are replacing.

**Build P0 — the broadsheet read — in this order.**

1. **The planes carry what the score needs.** `memory/analyze.py` today
   keeps six sample moments per lens, twelve decisions and twenty-four
   questions per meeting (caps — never present them as counts). Add
   `analysis.framing.track`: for each lens, the count of its words in each
   of 60 equal bins along the tape; keep `entities.money` (already there)
   and add `entities.people`/`places` times where the captions allow.
   Backfill live meetings with the repair recipe in
   `specs/next-session-prompt.md` (a one-off `record-pipeline` execution,
   never from a Mac). The `/app/ai` ledger does not change: nothing new is
   written by a model.
2. **The press presses pictures.** `record/press.py` fetches each meeting's
   poster (`hqdefault.jpg`) and three in-tape frames (`hq1.jpg`, `hq2.jpg`,
   `hq3.jpg`) from `i.ytimg.com` into `app/stills/<pid>.jpg` and
   `<pid>-1..3.jpg`, once, cached across pressings; the reader page loads
   them from the edition, never from a third party. Sizes ~10–20 KB each.
3. **`web/charts.py`** gains pure, deterministic SVG: `score(meeting)` (the
   tape as a timeline: decisions as dots sized by score, tension in rust,
   money entities as labelled ticks, eight lanes from `framing.track`, a
   playhead group), `filmstrip(meeting)` (three frames, each with the
   decisions in its third), `year_tapes(meetings)` (stills on a month axis,
   sized by hours, town-coloured top edge, rows to avoid overlap),
   `butterfly(town_shares)`, `who_when(names, months)`, `vote_grid(votes)`,
   `lens_river(framing)` (bands separated by a hair of paper, labels at the
   widest point, a dashed line where the second town joins). Each writes
   its numbers alongside as `data-*` JSON for `app.js` to re-light.
4. **`web/emit.py::page_home`** on the twelve-column grid, in the order of
   board 1: masthead with the municipality switch and the READ stamp; the
   search spine (a real form that submits to the search page without
   scripts; six "try" chips; the sentence *everything you see is a search*);
   **Tonight's tape** (the frame large with the "Play from" chip and the
   current caption; the score beneath; the headline, the counted lede, the
   *now at* card and *money named on the tape* at the right; the filmstrip
   across); **The year in tapes** with the four chapter pills and the
   counted paragraph (`web/story.py::chapters` writes them from the counts);
   **Four columns** (two towns' vocabularies, who and when, the roll calls,
   warrant season — each ending in a rust *delve →*); **How the talk
   flowed** (the river with its italic reading); the front-pages strip from
   `featured_papers`; this week as cards; threads as small multiples; *Now
   tell yours* with the three doors; the footer. Every name, place, topic
   and chart element is a link into the search page or the meeting.
5. **The meeting page** gets the score as its jump bar (click to seek) and
   *Find in this meeting*; the search page gets the timeline of
   town-coloured dots and the reel with stills (boards 4 and 5).
6. **`web/static/app.js`** adds, progressively: the search spine's
   type-ahead over the shipped index, grouped as board 2 (moments · meetings
   · threads · over time), keyboard-first, no network; the score's
   interactivity (click a tick, a dollar, a decision or a frame → the
   playhead, the caption card and the frame move together; on the meeting
   page the same click seeks the video); the year's chapter pills and still
   picking; the READ/EDIT stamp replaces the mode bar (`paintModeBar`).
   With scripts off every chart is a still picture and every control an
   anchor.
7. **Phone** (board 3): the same order at 390, the spine second, the river
   static.
8. **The CSS system**: Fraunces, IBM Plex Sans and IBM Plex Mono
   self-hosted in the edition; tokens on `:root`; the namespace `bs-` for
   everything new (grep `web/static/app.web.css` for the namespaces already
   minted: `cz-`, `pb-`, `rt-`, `pf-`, `fp-`, `sp-`, `tp-`, `tq-`, `sq-`,
   `rp-`); zero fuchsia and no studio hue on a pressed page.
9. **Tests**: node twins in `tests/test_web_bake.py` for every new chart
   and codec (lift the functions by regex and run them, as
   `TestReviewFoldTwins` does); a byte-clean scan of every pressed page; a
   zero-fuchsia scan; the no-script search submit; the score's data-JSON
   round-trip; `decodeReel`'s law for anything new.
10. **Review**: lenses → skeptics → fold every confirmed finding → re-review
    your own fixes (the fixes have regressed this codebase four times).
11. **Deploy** per OPERATING §5 as version 2.2.0: build the image, push,
    move every job and the service, bump the press `--version`, press,
    carry (the nightly-edition workflow pushes on its own — dispatch it),
    verify `sw.js`'s cache key and the front page live, tag, push main. Then
    update `specs/next-session-prompt.md`, `specs/PARALLEL.md`,
    `CHANGELOG.md`.

**Then P1 — writing in the same style** (boards 7 and 8): the studio
restyled as the board — the block shelf, rust block frames with ↑ ↓ ×, the
writing desk (facts to cite, a labeled draft on request, the template's
three questions); `applyPaperTemplate` gains five templates (a vote and its
history, a person, a place, two towns side by side, the year so far) as
block lists plus three questions each; the issue-over-time template redrawn
to board 6; new ref-only kinds in `record/papers.py` (`lead:<pid>`, `week`,
`threads`, `strip`, `names`, `search`); `v=5` links; every decoder keeps
decodeReel's law. Version 2.2.1.

**Then P2 — the gallery** (board 9): the press lists shared pages from the
store and presses cards (title, made-from counts, the first still) beside
the record's own; the gallery page with its filters; takedown stays the
steward's; the front page's strip reads from it. Version 2.2.2.

**Stephen's decisions — ask before doing:** any new stored free text beyond
title and notes; naming writers on shared pages (default: unsigned — the
record keeps no reader identity); the takedown flow's words; spend over
$100/mo. Everything else in specs/29 is decided — build it.

**Traps.** Pressed pages stay byte-clean of studio markup. Every decoder:
malformed → fewer blocks, never a throw. Counted nouns through `n_of()`.
Controls describe the painted state. The SW cache key must change every
deploy. `--include='*.py'` needs quotes under zsh; f-strings cannot hold a
backslash in an expression on 3.11. The live summaries were cut mid-sentence
on 2026-09-24 (Gemini thinking tokens against `maxOutputTokens`); another
session shipped the fix as v2.1.23 — check a meeting page before quoting a
summary anywhere. The `questions` and `decisions` lists are capped, not
counts. YouTube's `hq1–3.jpg` frames exist for every public video; the
poster is `hqdefault.jpg`.
