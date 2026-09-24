# 28 — The verdict, read on a phone; the desk's last pieces

**Status:** v1.0 · **Stage:** BUILT on branch `desk-in-the-paper`, rebased on
v2.1.22 / r45 (specs/27, the steward's desk, shipped by a parallel session
the same night). Ships as **v2.1.23 / r46**. **Owner:** Stephen Walter (Weird
Machine) · **Related:** specs/25 (a word, over time), specs/26 (the meeting,
cut and found), specs/24 §4 (the reading, drafted), `CLAUDE.md` (the laws),
`record/OPERATING.md` §5 (deploy).

## 1. The verdict — read on a phone, 2026-09-23

The session's brief asked for Stephen's phone verdict on the live site; the
line came through unfilled, so the session read publicrecord.studio itself
at 375 px — the front page's three tabs, the search for "AI", a meeting
page's find box and night cut, the reel's transport, `?` — and measured what
it saw. What was wrong, in order of harm:

1. **Every model-written summary and reading on the live site was cut off
   mid-sentence.** Ten of twenty meetings' summaries (every one the Gemini
   lane wrote — "At the September 22, 2026,") and all twenty drafted
   readings (43–184 characters: "…an upcoming Proposition 2½ override vote
   on"). The front page's *latest meeting* story led with one. Cause:
   Gemini's thinking models spend their thought from the same budget as the
   answer (`maxOutputTokens`), the calls asked for 400 and 700, and the seam
   never read why an answer stopped.
2. **The readings showed raw Markdown** — `**What it means**`, `*   Motion/
   Vote:` — and summaries' receipts (`[69:48]`, `[264:28]`) were plain text
   in minutes-past-the-hour.
3. **The front page's "80 mentions" opened a search that said 73.** The
   pressed story counts "AI" or "artificial intelligence"; the search counted
   the word typed. Same story, two numbers, one link apart. (And "the
   supercut" meant the one-clip-a-night cut on the front page, the every-clip
   cut on the search page.)
4. **Meaning-search never answered in time.** The live API's neural search
   took 13–27 s at `limit=80` (lexical: 2 s); the reader's bell is 6 s, so
   every live search said "Meaning-search … not answering". The database
   (`db-f1-micro`, the HNSW index on `emb_neural` that could not sit in
   memory). **Resolved the same night by Stephen's decision**, carried out by
   the parallel session: `record-pg` resized to `db-g1-small` (02:09–02:14Z).
   Re-timed after: 0.3–1.3 s at `limit=80`.
5. **Unclear on a phone:** the town question was asked on every page, even
   after "the whole record" (an answer that stored nothing left no trace),
   and on shared meetings and reels; the find box sat two phone-screens above
   the lines it folds (the reading panels stacked between); a shared reel put
   a paragraph before its player; the keys sheet was pinned to the top-left
   corner (the sheet's `margin:0` reset); the tab strip's subtitles truncated
   to "how Brooklin…" at three tabs and would not hold four.

Noted, not changed (the next session's): the lede's quotes are raw captions
("the the tracker in I think…") — a tighter window around the word would
read better; search hits repeat the meeting's whole title per line (seven in
a row) — grouping by meeting; "the night in 1:14" of the March 24 meeting is
five procedural votes ("Two hot dogs" scored as a vote) — the analyzer's
scorer; "Meetings by month" skips a month with no meeting where the topic
story shows the gap; the "10 of 14" number wraps; the studio pill sits over
the text on every phone screen (it is the designed invitation; a phone could
reserve its height).

## 2. The verdict, answered

### 2.1 The seam (`czcore/llm.py`)

- Gemini gets **thinking room**: `maxOutputTokens = max_tokens +
  GEMINI_THINKING_ROOM` (8192) — the caller's number stays the answer's
  length. The same for the vision door.
- **A cut answer is no answer**, on all three providers: Gemini
  `finishReason: MAX_TOKENS`, OpenAI `finish_reason: "length"`, Anthropic
  `stop_reason: "max_tokens"` raise after the call is recorded. The callers
  already fall back: a summary to the extractive one, a draft to none, a
  label to its keyword name, a translation chunk to its source lines.
- The audit bills the thought (`thoughtsTokenCount` joins `tokens_out`);
  thought parts are never the answer.
- The prompts (`memory/analyze.py`) ask for plain text, the reading's three
  paragraphs begin *What it means: / Who moved it: / What to watch:*, and the
  passages carry `[H:MM:SS]` past the hour so a model echoes a time a
  resident can find.
- The ledger on `/app/ai` says a cut answer is refused, never pressed.
- **The repair** (after deploy, the pipeline job's own image): every Gemini
  summary that ends mid-sentence is asked again; every model draft that ends
  mid-sentence or shows Markdown is drafted again, or removed when it cannot
  be drafted whole. Safe to re-run.

### 2.2 A model's prose, read (`web/charts.py receipt_paras`, `app.js receiptParas`)

Escaped first, then the subset of Markdown the models write: a heading line
(`**X**`, `## X`) is a small head (`rd-h`), bullets are a list (`rd-list`),
`**bold**` and `*italic*` are read, every other asterisk and backtick is
dropped (an asterisk with a space either side is text). Every time in a
receipt group — `[1:52:55]`, `[13:15-13:44]`, `[12:12, 17:13]` — is its own
link, said the way the record says a time (`[264:28]` reads `[4:24:28]`); a
group holding anything that is not a real time stays as written. Summaries
use it too (their receipts were plain text); the front page's latest story
keeps whole lines up to 900 characters instead of cutting at 600. The two
twins are held equal byte for byte by a node test over adversarial fixtures.

### 2.3 A featured word counts the same everywhere

`topics/index.json` carries each featured word's phrases; the search page
(`sqFeatured`, `sqPhraseIds`) counts a featured query by its story's own
rule — each phrase's first word's postings, kept where the phrase starts in
the line read with the next joined on — and says which words it counted,
linking the pressed story. Executed in a node test over the pressed index:
the story's six lines are the search's six, including the one a caption
break split. The search page's "the supercut" is the one-clip-a-night cut,
as the front page's is.

### 2.4 The phone

The town question is asked once, and only on the front page and the search
page (`cz-town-asked`; "the whole record" is an answer); the find box sits
over the lines it folds and the reading panels go above the transcript's
bar; a reel leads with its player; the keys sheet is centred and scrolls
within the screen; the tab strip names each story (*"AI", over time*) and
wraps two by two.

## 3. The desk's last pieces

### 3.1 A second featured word — housing

`FEATURED` gains *housing* — the word every town's record carries: on
Brookline's, 448 mentions in 13 of 14 meetings, peaking the night the
affordable housing trust came up (Boston's bodies said it in 71 lines). The
front page grows its fourth tab. (*override* — Brookline's 2026 story, 326
mentions, no Boston lines — is the obvious third.)

### 3.2 Drag to reorder (`app.js wireDrag`, `trayMove`; `dg-`)

Both trays — the meeting page's and the studio panel's — drag: the grip is
a row's own number, a line says where it lands, held near an edge the list
or the page scrolls, Esc puts it back. The lifted clip is re-found by its
identity at the drop. Pointer events, so a finger drags as a mouse does.
The ↑ ↓ buttons stand; they are the keyboard's way, and the grip says so.

### 3.3 Picture downloads as SVG (`web/pictures.py`; `pic-`)

Every picture the press draws is a file too: the votes as dots, the word
clouds and the shape of a meeting wrapped as they are; the topic story's
months, tapes and words drawn again as SVG. Each file: a white page, the
story's title, the picture, its marks still links (made absolute), and two
source lines — where it lives; how it was made, the record it was pressed
from, CC BY-SA 4.0. Collected as pages render, written once from
`emit_stubs` (the desk bake and the hosted press share it). The search
page's live story draws its three with JS twins, byte-equal.

### 3.4 The glossary (`web/glossary.py`; `gl-`, `mp-terms`)

Forty-seven civic words the record uses and seldom explains, in five
groups — who decides, how a meeting runs, the money, what gets built, the
schools — each in plain language, with where it applies, the public source
(the General Laws, the state's Municipal Finance Glossary, Brookline's and
Boston's own pages, Boston's Enabling Act), and the record's own count, town
by town, only in the towns a word belongs to, each count linked to the
search that lands on that number. The definitions were written with Claude
(`claude-opus-5-5`), through the coding assistant the developers used while
writing this code, from the sources named — never at press time, never in a
reader's browser; the page says so, says no person has yet read them against
their sources, and the ledger on `/app/ai` carries the row (its model name is
read from `web/glossary.py`, so the two cannot drift). It sits in the section
line; the front page's lede links its phrase; every meeting page names the
words it uses that the glossary explains. No person is defined.

### 3.5 The desk, one click away (Stephen, 2026-09-24)

Wherever the record says a step needs the desk — render a reel, cut a kit,
run a model locally — it hands over the desk: Civic Media Studio's DMG
(`emit.DESK_DMG`, `app.js DESK_DMG`, held equal by a test), beside every
reel.json on the reel viewer, the meeting tray and the studio's panel, on
both kit pages, on the press page (the direct download first, every release
beside it) and in the constitution's "use AI that stays local". Pressed as
anchors; a link, not a load.

## 4. What is Stephen's

- **Ship**: v2.1.23 / r46 (OPERATING §5), then the repair (§2.1; OPERATING
  "Repairing a model's cut answers"), then the press and the carry.
- **Per-clip thumbnails** on the tray — still his call. Measured: the front
  page's meeting cards already load `i.ytimg.com` stills (lazy); YouTube's
  static stills are per video (three auto frames), not per moment, so a
  "per-clip" still is the meeting's own still — no new host, one request per
  meeting.
- **A `chart·topic` paper block** — a new stored kind; his sign-off first.
- **The glossary's words** — read them against their sources, then flip
  `glossary.REVIEWED` so the page stops saying no person has; a correction is
  a dated note beside the entry (`notes`).
- **A labeled model "what changed"** — the delta is extractive now because a
  model's was stored with no origin; labeling one needs its origin stored
  beside it (a stored-field decision).
- A month filter on the search page's list (specs/25 §4) stands.
- **The co-author trailer.** CLAUDE.md asks every commit to end
  `Co-Authored-By: Claude`, and the constitution page says the AI-assisted
  work is "co-authored in the open" — but this session's instructions forbid
  attribution lines in commits, so none of v2.1.23's carry one (nor the ~30
  before them). Either the instruction or the page's sentence should change;
  the commits' bodies say what was written with a model either way.
- **control-z's `czcore/llm.py`** has neither the thinking room nor the
  refusal of a cut answer; the desk's Gemini lane cuts the same way until
  the fix is mirrored there (deliberately — CLAUDE.md's rule).

## 5. Verification

**Reviewed in three rounds.** Six adversarial lenses first (the seam and the
repair, the renderer and the summaries, the drag, the glossary's facts and
code, the pictures and the search, the desk links); every finding folded
with a test (b37f56f). Then five re-reviews of those folds — and the folds
had regressed again, as the last five features' did: 49 findings, 48 folded
with tests (ee37799). Then three re-reviews of THAT fold, and it had
regressed too: 24 findings, 23 folded with tests — the repair could write
one half of a meeting and strand the other (a written row is newer than the
cutoff, so its failed half was never planned again; now a meeting is written
whole or not at all), took a timeout and one cut for "refused twice", and
would have asked a desk model's whole draft again for its age; the lede
dropped a bullet that was all bold (a decision, read as a heading — 10.5k of
120k fuzz cases lost items); "overlay" alone had been pointed at the zoning
entry, when on a budget night it is the assessors' reserve for abatements;
a capped cut ended on an undated night instead of the latest dated one. The
one left to a person: a prompt the model declines every time keeps that
meeting's fragment until someone decides (OPERATING says how). The gravest was the repair: on ANY failed call (a quota, a key,
a rejected request) it would have written the extractive summary over every
Gemini summary and removed every draft, printed `REPAIR DONE` and exited 0,
past any re-run's reach. Now only a cut answer licenses a fallback; a failed
call changes nothing, two in a row stop the run, it exits 1, and each row's
old values are logged (`BACKUP`) before it is written. The others: the
ledger's issue-names row said the keywords named the record's threads when
all 215 carry `ai:gpt-4o-mini` (checked against the live planes); a model
name the seam did not know (`gemini-flash-latest`) lost the thinking room;
a renamed thread lost its "what changed" history; a lede lost to an
unclosed "[inaudible", or ended on a lone label; a receipt past the tape's
end highlighted its last line; the search list's untowned count was over
the 80 shown; three reel links could pass the host's 8 KB limit (a 414, a
dead page) — every link now holds at most 240 clips in both twins, the
capped cuts spread from the first night to the latest, and the trays say
when a link plays fewer than they hold; a phrase broken across two captions
was listed with nothing marked; five glossary entries' wording or sources
(the MBTA 177, the exclusions' framing, the stabilization fund's deposits,
executive session's declaration, Boston's Enabling Act); a pen could no
longer drag from a row's number; a hidden list's drag dropped anywhere; a
drop focused a trim button. One is Stephen's, not a fold: the reviewers
note the commits carry no `Co-Authored-By` trailer, which CLAUDE.md asks for
and the constitution page's "co-authored in the open" implies; this
session's instructions forbid the trailer, so the question is his (§4).

766 tests (110 PG-backed skip without `RECORD_TEST_PG_DSN`). Pressed locally
from a corpus seeded off the live edition and read in the pane with the
service worker unregistered: the search for "select board" marks all 80 lines
it lists (17 showed nothing before), its reel is "120 of 623 clips, first to
latest" in a 2.8 KB link that runs from 2025-12-09 to 2026-09-16, the tray
takes 120 and says so, a receipt past a tape's end highlights nothing, the ten
picture links on the front page carry ten names, and no page scrolls sideways
at 375 px.

**Deployed 2026-09-24, 04:03Z** — image `r46` (built from 02d4e8b) on
`record-api` (revision `record-api-00038-6p9`) and all four jobs; the press at
`--version 2.1.23`. No pipeline execution was running on the old image (the
last ended 02:09Z), so the repair's cutoff was the deploy itself,
`--before 2026-09-24T04:03:14Z`. The dry run planned all 26 live meetings (16
summary + draft, 10 draft only — their gpt-4o-mini summaries are whole). The
probe on one (`tj-9c8c_wC0`) came back whole on both calls (a 1,643-character
summary in 11.3 s — 2,048 tokens out, the thought included — and a
1,491-character reading in 9.0 s), which is also the proof that the API takes
`thinkingLevel: low`. The repair: `REPAIR DONE — 26 updated, 0 unchanged, 0
could not be asked` — 16 summaries and 26 readings, every one whole
(700–2,450 characters, median 1,496; 9.0 s a call, 388 s in all), 26 `BACKUP`
lines in its log, no fallback. Before it, the live edition's ten Gemini
summaries ran 26–95 characters and its twenty readings 43–184, every one cut
mid-sentence. The press (26 meetings, 215 issues, 145,593 lines indexed)
synced to the bucket; carried to Pages (bc0dab0) with the gzip loop, the
hand-files kept.
