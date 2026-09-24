# 27 — The verdict, read on a phone; the desk's last pieces

**Status:** v1.0 · **Stage:** BUILT on branch `desk-in-the-paper` (on top of
v2.1.21 / r44). Targets **v2.1.22 / r45**. **Owner:** Stephen Walter (Weird
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
4. **Meaning-search never answers in time.** The live API's neural search
   takes 13–27 s at `limit=80` (lexical: 2 s); the reader's bell is 6 s, so
   every live search says "Meaning-search … not answering". The database
   (`db-f1-micro`, the HNSW index on `emb_neural` that cannot sit in memory)
   — the same diagnosis as the embed pace. **Stephen's** (spend, or an index
   change on the production database); not changed here.
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

Forty-seven words the record hears most and explains least, in five groups
— who decides, how a meeting runs, the money, what gets built, the schools
— each in plain language, with where it applies, the public source (the
General Laws, the state's Municipal Finance Glossary, Brookline's and
Boston's own pages), and the record's own count, linked to the search. The
definitions were written with Claude at the desk from the sources named;
the page says so and the ledger on `/app/ai` carries the row. It sits in the
section line; the front page's lede links its phrase; every meeting page
names the words it uses that the glossary explains. No person is defined.

## 4. What is Stephen's

- **Ship**: v2.1.22 / r45 (OPERATING §5), then the repair (§2.1), then the
  press and the carry.
- **Meaning-search is too slow to answer** (§1.4) — spend (a larger Cloud SQL
  tier) or an index change on the production database.
- **Per-clip thumbnails** on the tray — still his call. Measured: the front
  page's meeting cards already load `i.ytimg.com` stills (lazy); YouTube's
  static stills are per video (three auto frames), not per moment, so a
  "per-clip" still is the meeting's own still — no new host, one request per
  meeting.
- **A `chart·topic` paper block** — a new stored kind; his sign-off first.
- **The glossary's words** — read them; the sources are the authority, and a
  correction annotates.
- A month filter on the search page's list (specs/25 §4) stands.

## 5. Verification

(filled in after the adversarial review)
