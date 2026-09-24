# 25 — A word, over time: the search, told as a story

**Status:** v1.0 · **Stage:** BUILT on branch `topic-story` (on top of
v2.1.19 / r42), 623 tests green, pane-checked on a local twin of the live
corpus (15 meetings, 40 issues, 27 roll calls). Targets **v2.1.21 / r44** (v2.1.20 / r43 is the embed-budget deploy).
**Owner:** Stephen Walter (Weird Machine) · **Related:** specs/24 (the front
page is the story), specs/22 (the cutting room), specs/20 §6/§7 (the reel
viewer), `CLAUDE.md` (the laws), `record/OPERATING.md` §5 (deploy).

## 1. Problem — the powerful half was hard to find, and nothing showed what it was for

Stephen's verdict (2026-09-23, after v2.1.18): *there are still so many
things wrong with the UX. There are powerful features — the search, the
reel creator — yet they are hard to know how to activate, and their UI is
unclear. Think about the value to a citizen of searching for "AI" and then
seeing visualizations of how it has been said over the last year, six
months, a month — and quickly creating a supercut of all of it, and sharing
it publicly. Take from Community Highlighter: the progress animation when a
search runs, the share player that shows progress through its clips and
lets you go clip to clip. I like the site's style, but it does not help a
user know how to use it, nor model what effective use looks like. Lead the
landing page with a real case study — how AI is mentioned across time in
Brookline's public meetings — as a beautiful, data-driven story. And bring
most of Community Highlighter into the record, cleanly, in the new
aesthetic.*

Read against the code, every point held. The search page listed lines and
nothing else: a reader who typed "AI" got eighty hits and no sense of the
shape of the thing — when it started, the night it peaked, who said it.
The reel was reachable only through a small unlabeled tick on each hit,
and the viewer played clip to clip with no transport, no bar, no way to
step. The front page told two stories, neither of which showed a citizen
what a search could become. Nothing on the site said, in three lines, how
to use it.

## 2. What was built — build to this, extend from this

The whole feature is one idea told three times: **a search is a story**.
The press tells it for a featured word at press time; the search page tells
it live for any word; the reel viewer plays it.

### 2.1 The engine (`web/topic.py`)

Pure over the pressed meetings — sorted everywhere, no wall-clock, no
randomness, so two presses agree byte for byte:

- **Matching** is whole-word and case-blind (`phrase_re`): `ai` matches
  "AI." and "ai," and never "said" or "aim". A caption line is short and a
  phrase can break across two ("…it uses artificial" / "intelligence
  cameras"), so a line is read with the next joined on, and only a match
  that *starts* inside the line counts for it — no line is counted twice
  (`mentions_in`; the JS twin is `mentionsIn`).
- **The count** (`aggregate(meetings, hits, topic, town, floor)`): the town
  with the most lines leads (or the reader's scope pins one); per meeting,
  the lines, the mentions, the first and last time, 48 slices of the tape,
  the merged clips; months contiguous from the first to the last month the
  town met (a silent month is a visible gap); the bodies; the first word,
  the latest, the peak night and its span; the meetings that passed in
  silence after the first word; the other towns as *elsewhere*; the words
  said beside it (each hit's line and its two neighbours, civic stopwords
  and the topic's own words out); the chapters (the first time it came up,
  each night); and the two reels.
- **The reels** (`merge_windows`, `reel_url`): a hit is a clip of its line
  and the twelve seconds after it — the tray's own rule for a search hit —
  and hits inside the clip before them extend it rather than replay the
  same footage, up to ninety seconds; never past the tape's end. The links
  are the viewer's own grammar, byte for byte (`v=1&m=<pid>&c=…` for one
  meeting, `v=2&c=<pid>:<start>-<end>,…` across meetings; `_r1` is JS r1's
  formatting twin). The **supercut** is one clip per night (the chapter's
  run); the **full cut** is every clip.
- **The floor**: a story presses only where the leading town has three
  lines across two meetings — a word said once is not a story yet.
- **`FEATURED`** names the case studies (today: AI — phrases "AI",
  "artificial intelligence"). A second entry is a second story tab; the
  order is the list's.

### 2.2 The front page leads with it (`web/story.py::topic`, `tabs`)

A third story, first, behind the tab strip (2.4's toggle generalizes to
every story the strip names; the first tab is the default; a remembered
choice that no longer exists falls back). **How Brookline talks about AI**:
a counted headline and lede — *the first time anyone said "AI" on
Brookline's record was December 9, 2025, 4:01:19 into a Select Board
meeting: "…how quickly AI is developing…". 2 meetings then passed without
it. It peaked on March 24, 2026, when the Select Board said it 31 times in
9 minutes — 39% of every mention on the record. In all, 79 mentions across
9 of Brookline's 11 meetings, by the Select Board and the School Committee;
the words said beside it most: use, policy, companion, zoom. The latest was
June 30, 2026: "…the potential for harm with AI is so high…". Boston's
bodies said it in 25 lines across 2 meetings — the whole record's search
reads them together.* Then, each with a line of commentary:

| picture | what it is |
|---|---|
| "AI", by the numbers | mentions · meetings of the town's · bodies · first said · latest · the supercut's length — each a receipt |
| mentions, month by month | one column per month, contiguous; a bar for the mentions with its count; under it a dot per meeting (filled where the word came up, hollow where not, none where the town did not meet); a bar opens the tape at the month's first mention; a table twin |
| where it fell | the highlighter's sparkline search, one term across every tape: a row per night that said it, 48 slices, every bar a deep link; a twin |
| the words beside it | magnitude bars; each word opens the search for the pair ("AI policy") |
| the first time it came up, each night | one quotable line per meeting (the line before and after joined), the count that night, the time on the tape — and, hydrated by the script, the search hit's own **＋ reel** tick (`hydrateTopicTicks`): the front page's moments cut like any search result |
| the supercut | ▶ play the supercut (one clip per night · its length) · the full cut (every clip · its length) — the viewer's links |
| make one of these | the three steps — search a word · see how it was said · cut it, share it — and six of the record's own words to try |

It closes with *search "AI" yourself →* (the town-scoped search), *this
story's own page →* and, when the record tracks a thread under the word,
*the thread the record tracks: Artificial Intelligence →*. Every number is
a receipt; the commentary is counted, never modeled, and says so beneath
the lede, naming every phrase it counted.

### 2.3 The story's own page and its plane

`/app/topic/<slug>/` presses the same story with its own title and
description, so it travels as a link; `topics/<slug>.json` and
`topics/index.json` are the plane (`bake_topics`, mirrored in
`record/press.py`; the parity test holds the stage sequence equal). The
search index's `meta.json` now carries each tape's `duration` — the live
story needs it to place a hit and end a clip.

### 2.4 The search page tells it live (`app.js` tpAggregate · sqStory)

For any word a reader types, the same story, drawn with the same classes:

- **The progress line** (`sqProgress`): real stages at real await
  boundaries — *opening the record's index… · 95,125 lines open — reading
  the ones that say "ai"… · 89 lines — counting, month by month… · 89 lines
  counted* — a thin bar that fills by stage and goes when the count is
  done; `aria-live="polite"`; never a timer pretending to be work.
- **The story** above the hits: the headline, the range switch (**count:
  the last month · six months · a year · the whole record** — a radiogroup,
  aria-checked, arrow keys, the story re-counted from the record's latest
  day, the town fixed so the headline does not change town as the stretch
  narrows), the counted lede, then **▶ play all N clips as a reel**, **✂
  put every clip on my tray** (appended by identity, never doubled) and
  **⧉ copy the link to this search**; the numbers, the months, the tapes,
  the words beside it. Counted in the browser from the record's own index
  — the words themselves, whole-word, whatever the Studio's meaning-search
  listed — and labeled so.
- The list keeps its ticks; **j / k** walk the hits, **Enter** opens the
  tape, **c** cuts the one under the cursor.
- **The empty state** says what a search can do here: the three steps, six
  words to try, the featured story as the worked example, the keys.

`tpAggregate` is the press's `aggregate` twin: the node twin test feeds
both the same meetings and hits and holds their answers equal — months,
bodies, first/latest/peak, the gap, elsewhere, the co-words, the chapters,
the clips, the bins and both reel links.

### 2.5 The reel viewer plays it (`app.js` rpBar · rpPaint · rpState)

Community Highlighter's reel player, in the paper: under the tape a
transport — **◀ · ▶ play / ❚❚ pause / ▶ go on / ↺ replay · ▶|** — the
counter (*clip 3 of 9 · 0:31 / 1:48*), and **one segment per clip, sized
by its length**, filled by the tape's own time reports as it plays (never a
timer), done segments filled, the current one outlined; any segment is a
button that jumps there (before play, it starts there). **Space** toggles,
**← →** step. The now-playing line names the clip, its quote, its meeting
and day; at the end it grows **↺ play it again · ⧉ share the reel · ✂ make
this reel yours**. **⧉ share the reel** joins the cite list's row: the
device's own share sheet when it has one, the link copied when it does not
— nothing else is called. A play pressed in the frame after the transport
paused goes on with the reel. The engine underneath is unchanged: one
engine seeks, the armed gate, the settle window, the preview stage's pause.

## 3. Bounds — the laws, precisely

- **Byte-clean**: the pressed story is content in the paper palette
  (`tp-`, `tq-` namespaces; `sq-` for the search page, `rp-` for the
  transport — grep-checked free); no `<button`, no `cz-`, no studio hue;
  the ticks, the transport, the range switch and the progress line are
  script-built.
- **Covenant**: the make path touches no server — the search page's story
  reads the record's own static planes (the index is fetched once per
  edition per browser; the service worker keeps it), the reel is a link,
  the tray is localStorage. The share sheet is the device's. No new door.
- **Store**: nothing. No new stored field, no new paper kind.
- **Counted, never modeled**: every sentence is a rule over the transcript;
  the AI constitution's ledger is unchanged, and the story says beneath its
  lede what it counted.
- **Idempotence**: pure functions of the planes; the twin test pins the
  count.
- **A11y**: every mark an `<a>` with a name and a table twin; the range
  switch and the transport are proper controls; the progress line is a
  polite live region; the reel's segments are buttons with names.
- **Controls describe the painted state**: the transport paints from
  `REELPLAY` as it stands; the range switch's aria-checked is the count
  shown.

## 4. What is Stephen's (never unprompted)

- **Ship it**: v2.1.21 / r44 (OPERATING §5; press `--version 2.1.21`; the
  Pages sync; the tag). The SW-staleness law: the version bump is the
  cache key.
- **A second featured word** — one line in `topic.FEATURED` (a name, a
  search, its phrases); the front page grows a fourth tab.
- **The topic as a paper block** (`chart·topic`, a slug) — a new stored kind
  needs his sign-off; the plane already exists for it.
- **A month filter on the search page's list** (the story counts by range;
  the list is the whole record, and says so).

## 5. Verification

An adversarial review (lenses → skeptics, the repo's rule) found fourteen
defects; every one is folded and pinned by a test: the story's own page
hydrates its ticks from the router; a malformed date is undated, never a
crash; a meeting with no town never leads and is named as such; a word
said on an audio-only first clip still replays; the transport paints the
tape's own pause; prototype names are data; the reader's stopword and
artifact sets are the press's; a body scope counts only its bodies; the
range is a true month; the empty box restores the guide; the try links
keep their query whole; the keys leave controls alone. The folds were
re-reviewed and six more findings folded: a cite pressed while the
transport (or the frame) paused the reel goes on from that clip; a segment
pressed before play starts its own meeting's tape; the range admits dated
nights only; an empty answer names its scope and its reason; a garbage
date is undated in both twins; "the latest" is the last dated night.

The suite (`tests/test_web_topic.py` + the guards): whole-word matching
across a caption break; merged windows and their cap; contiguous months;
the reel grammar; the aggregate on a fixture (months, bodies, first/peak/
latest, the gap, elsewhere, co-words, chapters, both cuts, the floor, a
pinned town); the node twins (`tpAggregate` = `aggregate`, `mentionsIn` =
`mentions_in`, the press's links decode with `decodeReel`); the pressed
story (the tab strip leads with it, every picture and its twin, the
receipts, the chapters' data, the supercut links, the close, byte-clean,
"no model wrote a line of it"); the story's own page and plane; the search
page's guide; a word said once presses no story and the front page keeps
its two tabs; the press-parity stage sequence. Pane-checked on the local
twin at phone width: the three tabs toggle and remember; the story's
pictures read with no horizontal overflow; the chapters carry ＋ reel ticks;
the search for "AI" runs its progress line and draws the story with the
range switch re-counting; ▶ play all opens the viewer; the transport plays,
steps and jumps with the bar painting.
