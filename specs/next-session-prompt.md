# Session prompt — publicrecord-studio: after v2.2.0, what is Stephen's

**Open this session in a checkout of github.com/amateurmenace/publicrecord-studio**
(`main`, at or after the merge of PR #1 — v2.1.21 / r44 is live)
(on a new machine: `gh repo clone amateurmenace/publicrecord-studio`, then
`python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt` —
system python may be 3.14, too new). `CLAUDE.md` carries the laws;
`specs/24-two-paths.md` is the newest scope (BUILT + LIVE); `specs/23` is
done. **Memory from the last machine does not travel — this file is the
state.** Written 2026-09-23, late; the topic-story branch noted later that night.

## Where things stand

- **LIVE: v2.1.21 / r44** (2026-09-24; PR #1 merged as 3e06db7; tag
  `v2.1.21` at 049eba5, the commit the image was built from; the service
  and all four jobs on r44; the press at `--version 2.1.21`). **A word,
  over time** (`specs/25-a-word-over-time.md`) — Stephen's UX verdict of
  2026-09-23 answered: the front page leads with *How Brookline talks about
  AI* (a counted story pressed from the transcripts by `web/topic.py` +
  `web/story.py::topic` + three new pictures in `web/charts.py`, with a
  supercut in the viewer's own link grammar and a "make one of these"
  close); the story has its own page (`/app/topic/ai/`) and plane
  (`topics/ai.json`); the search page tells the same story live for any
  word (`app.js` tpAggregate / sqStory — a node twin holds it equal to the
  press's `aggregate`), with a progress line that moves at real stages, a
  range switch (month · six months · year · all), ▶ play all as a reel, ✂
  put every clip on my tray, and an empty state that explains search in
  three steps; the reel viewer has the Highlighter's transport (prev · play
  · next, the counter, a segment per clip that fills with the tape's own
  time reports, keys, share, an end card). `search/meta.json` carries
  `duration`. Reviewed adversarially (fourteen findings folded, the folds
  re-reviewed, six more folded). 623 tests. Then **the meeting, cut and
  found** (`specs/26-the-meeting-cut-and-found.md`, `web/cuts.py`): the
  night cut as pressed reels on the meeting page and the latest story,
  find in this meeting (folds the transcript, sparkline, ▶ the mentions as
  a reel, ✂ tray), the word cloud on every meeting page, a jump bar, the
  `?` keys sheet, the bodies filter under the stories — reviewed the same
  way (eleven findings folded, five more on re-review). 658 tests. The
  parity list is now eleven files (`web/topic.py` and `web/cuts.py` joined
  it). **Next** (Stephen's, below): a second featured word; the follow-ons
  specs/25 §4 and specs/26 §4 name; read the live front page's three tabs
  and the search for "AI" on a phone, and say what is still unclear.
- **LIVE: v2.1.20 / r43** — tag `v2.1.20` at the deployed commit. v2.1.20:
  the first night with every switch on landed one meeting and sat silent for
  an hour — the embedding endpoint had slowed to a batch a minute, one
  meeting's vectors outran the job's hour, and a dozen approved tapes were
  never reached. A landed meeting now spends `RECORD_EMBED_BUDGET_S` (120 s)
  on its vectors inside the pipeline and no longer; `record-embed` is
  scheduled nightly at 05:45 ET (`record-nightly-embed`) to drain the rest;
  the nightly-edition workflow proved its federated sign-in, press and
  bucket sync, and ignores a night whose only change is the press's own
  `pressed_at` stamp. A job killed mid-ingest no longer strands its
  submission (`reclaim_stale`; a stale in-flight shell is not a dedupe hit). The standing rule approved thirteen waiting tapes on
  its first poll (10 Boston, 3 Brookline). 631 tests. v2.1.19:
  the nightly drain asks again for every meeting that parked without words
  in the last week (`retry_parked`) — Brookline's meetings are live streams
  and their auto captions arrive hours later. v2.1.18:
  a hosted meeting keeps its title and day (the feed's title from the
  submission's note, YouTube's own `videos.list` when the key is at hand —
  the pipeline job carries `RECORD_YOUTUBE_API_KEY` too); the pipeline
  bridges `RECORD_GEMINI_KEY` to the model seam so hosted summaries are the
  labeled Gemini paragraphs the constitution names; **the reading is
  drafted** at ingest (`analysis.draft`, specs/24 §4) and shown under the
  model's name on the meeting page, the front page and in papers; the
  ledger's summaries row names the earlier desk lane; the seam's default
  Gemini model is the one the API names (`gemini-3.6-flash` — the old
  default had been retired and the hosted lane failed silently). v2.1.17 was the
  toggle/scope hot fix. v2.1.16 shipped two things together:
  1. **The front page is the story** (specs/24): two pressed stories behind a
     toggle — *the record, over time* (counted headline and lede, the record
     by the numbers, votes as dots, the six widest threads month by month, the
     eight lenses as a heat strip, recurring topics, the record in words, what
     changed) and *the latest meeting, what happened* (the labeled summary,
     a counted commentary, the meeting in numbers, the shape of the tape, the
     moments that decided it, roll calls, framing, questions, words,
     sparklines, names, filings). `web/story.py` writes the words,
     `web/charts.py` the pictures — pure functions of the planes, no model,
     byte-identical press to press. The studio's two path templates (one
     meeting · over time) on five new ref-only kinds (`chart·numbers`,
     `chart·shape`, `chart·ledger`, `chart·votes`+pid, `reading`; links at
     `v=4`), the writing desk beside every note, and a Read / Edit mode bar
     under the section line.
  2. **Nightly intake** (OPERATING §5 "Nightly intake"): a per-source
     standing rule (`auto_approve`, a checkbox in the console) approves a
     rule-matched candidate only when YouTube's own caption list names a
     track; the probe asks Data API `captions.list` when
     `RECORD_YOUTUBE_API_KEY` is set (verified: a key alone answers, the
     auto track counts, `videos.list`'s flag lies). The relay caption route
     was **proven from inside Cloud Run** (7,842 cues in 5.7 s). Every Cloud
     Run job now moves with each deploy — the poll and pipeline had sat on
     r18 since July.
- v2.1.15 / r37 shipped the same day: the v2.1.14 folds, the second review
  folded (thirteen findings), a re-review of the fixes. 584 tests at HEAD.
- `main` = what is live, plus docs. Branches `fold-v2.1.15`, `nightly-intake`
  and `story-paths` are merged and can be deleted (Stephen's).

## 2026-09-24, 05:28Z — v2.2.0 / r47 IS LIVE: the civic broadsheet (specs/29 P0)

The front page is a paper. specs/29 is the design (and its canvas,
<https://claude.ai/artifact/HgMxn4cApHgdYqu5P1aGJy>, is the spec for the
colours, type, grid and copy); the CHANGELOG entry says what shipped. The
shape of the build, for whoever touches it next:

- **The planes**: `analysis.framing.track` — sixty slices per lens, counted
  at press time by `memory.analyze.framing_track` with the lenses' own word
  lists (a lane's bins sum to its lens's count; a test holds it). No
  pipeline backfill was needed: the framing was always computed at press
  time from the transcript, and so is the track. `entities.people/places`
  already carry their first mention's `t` where the captions allow (Boston's
  all-caps captions yield none — a limit of the analyzer, not of the press).
  The `/app/ai` ledger did not change: nothing new is written by a model.
- **The pictures**: `record/stills.py` presses the poster and three in-tape
  frames per meeting into `app/stills/` (`<pid>.jpg`, `<pid>-1..3.jpg`),
  fetched once from YouTube, cached under `RECORD_STILLS_DIR`
  (`/tmp/record-stills`) and seeded from the edition bucket before each
  cloud press, so a still is fetched on the night its meeting lands and never
  again. A desk bake presses none unless `web.bake --stills`; the pages
  show the town's colour where a still is missing (determinism holds). The
  meeting plane carries `still` and `frames`; `search/meta.json` carries
  `still` (1/0). `bake_stills` is the first stage in both presses (the
  parity test holds the sequences equal).
- **The pictures of the page** (`web/charts.py`, appended): `score` (with
  `score_data` / `score_state`), `filmstrip`, `year_tapes` (with
  `year_layout`), `butterfly`, `who_when`, `vote_grid`, `lens_river`,
  `thread_spark`, `timeline_dots` — pure, deterministic, each with its
  numbers beside it as `data-bs-*` JSON and a table twin; every one
  downloads as an .svg through the other session's `web/pictures.py`.
  The words are `web/story.py` (appended): `tonight`, `chapters`,
  `vocab_words`, `names_words`, `rolls_words`, `thread_words`,
  `river_words` — counted, never modeled. `web/broadsheet.py` lays the page
  out and owns the masthead's pieces (`topbar`, `nameplate`, `municipality`,
  `spine`, `primary_nav`); `emit.masthead` calls them on every page.
- **The reader** (`app.js`, the section headed THE CIVIC BROADSHEET):
  `paintModeBar` now paints the READ/EDIT stamp (`#bs-stamp`) from
  `shownMode()`; `bsSpine` is the type-ahead over the shipped index
  (`bsGroup` is the pure grouping; ↑↓ move, ⇥ next group, ↵ opens, ⌘↵ the
  reel, Esc closes); `bsScore` re-lights the score (`bsScoreState` is the
  twin of `charts.score_state`) and, on the meeting page, seeks the tape
  and follows it (`BS_FOLLOW` from `tick`); `bsYear` (`bsYearState`),
  `bsRiver`, `bsSearchExtras` (`bsTimeline` is the twin of
  `charts.timeline_dots`). `wireFind` adopts the pressed find form.
- **The look**: `brand/tokens/broadsheet.css` is the single source (paper,
  ink, rust, the two towns' colours, the three faces); `emit._brand_tokens`
  re-points the old semantic tokens at it, so every older rule reads on
  paper. Fraunces (roman + italic, variable), IBM Plex Sans (variable) and
  IBM Plex Mono (400/500) are vendored in `web/static/fonts/` with their
  OFL texts (209 KB in all; Inter and JetBrains Mono are gone). The
  namespace is `bs-`.
- **Tests**: `tests/test_web_broadsheet.py` (its own pressing of the fixture
  corpus; the node twins lift `bsScoreState`, `bsYearState`, `bsMonthX`,
  `bsGroup` and `bsScore` from the reader and run them against the press's
  answers; decodeReel's law for the score's JSON; the no-script submit; the
  byte-clean and zero-fuchsia scans of every pressed page; the stills desk
  with a fake fetcher). The older pins were rewritten to the broadsheet.
  852 tests. Tag `v2.2.0` at 2e0e907; the service and all SIX jobs on r47
  (`record-press`, `record-pipeline`, `record-poll`, `record-embed`, and the
  two hand-run ones, `record-migrate` and `record-seed` — a peer session
  found those two left on r45; OPERATING §5's loop now names all six);
  the press at `--version 2.2.0`; Pages cf14c4d (the workflow carried it).
- **Reviewed**: four lenses (press-time Python; the reader; the stills, press
  and deploy seams; CSS, design conformance and accessibility), 53 findings — the two-towns reading that collapsed to a period on the live record, a calendar-invalid day that would have stopped a press, a night that could have emptied the bucket's stills, the spine's Tab trap, the stamp rebuilt under the reader's focus, a search box with no focus ring — 44 folded, the folds re-reviewed by two skeptics.
- **Still Stephen's / next (P1, then P2 — specs/29)**: the studio restyled
  as the board (block shelf, rust block frames, the writing desk), five more
  templates, the issue-over-time template redrawn, new ref-only kinds
  (`lead:<pid>`, `week`, `threads`, `strip`, `names`, `search`), `v=5`
  links — version 2.2.1; then the gallery — 2.2.2. Read the live front page
  on a phone and say what is still unclear. The CSP still allows
  `img-src https://i.ytimg.com` because the studio's paper cards and the
  reel viewer's facade still read `thumb`; the pressed reader pages load no
  third-party image — narrowing the CSP is a follow-on once those two read
  `still`. Left as noted, not folded: the standalone year picture (.svg) references
  the edition's stills by URL, so it draws them only where the file is opened
  as a document; the nightly seed downloads the whole still set because a
  job's disk is new each night (≈8 MB now, ≈30 MB at 300 meetings — a GCS
  volume at `RECORD_STILLS_DIR` is the cheap fix when it matters); a missed
  still is retried only when the record moves (`--force` presses now); the
  try chips and the stamp's words sit under a 44 px target (links in running
  text); the money figures stay in Fraunces and the nav carries six reading
  words (the glossary joined) — both the board's call to revisit; the find
  box sits under the score (board 4) rather than over the transcript
  (specs/27 §2.4) — its found panel now carries a jump to the lines.

## 2026-09-24, 04:03Z — v2.1.23 / r46 IS LIVE: the model's words whole; the desk's last pieces in the paper

specs/28 has it all (the verdict read on a phone, what answered it, three
rounds of review, the deploy's numbers). In short:

- **The seam** (`czcore/llm.py`): Gemini's thinking had spent the whole
  output budget — every hosted summary and every drafted reading on the
  record was stored cut off mid-sentence ("At the September 22, 2026,").
  A thinking model now gets `thinkingLevel: low` (3.x) / a 1,024 budget
  (2.5) / no field for a name the file does not know, 8,192 tokens of room
  on top of the answer, and any answer that did not end whole is refused
  (`CutOff`) and never stored. The API took `thinkingLevel: low` (the probe).
- **The repair ran** (`record/repair.py`; OPERATING "Repairing a model's cut
  answers"): `REPAIR DONE — 26 updated, 0 unchanged, 0 could not be asked`;
  16 summaries and 26 readings asked again, every one whole (700–2,450
  characters), no fallback. The log (`record-pipeline-8xzj4`) holds a
  `BACKUP` line per meeting with what it replaced. Its rule, for any later
  run: only an answer refused as a fragment twice licenses a fallback; a
  failed call writes nothing; a meeting is written whole or not at all.
- **The reader**: Markdown read, receipts linked; the search counts a
  featured or glossary word by its story's own rule; every reel link holds
  at most 240 clips (the host refuses past ~8 KB); capped cuts spread from
  the first dated night to the latest; *housing* is the second featured
  word; every picture downloads as an .svg (`app/pictures/`); tray clips
  drag; the glossary (`/app/glossary/`, 47 entries); the desktop app's DMG
  beside every step that needs the desk.
- **Stephen's, new**: read the glossary against its sources and flip
  `glossary.REVIEWED`; the co-author trailer (CLAUDE.md asks for it, this
  session's instructions forbade it, the constitution page says the work is
  "co-authored in the open" — one of them should change); mirror the seam
  fix into control-z's `czcore/llm.py` (the desk's Gemini lane still cuts);
  per-clip thumbnails and `chart·topic` still wait on him (specs/28 §4).
- `search/segs.json` is 2,057 KB gzipped at 26 meetings — the press warns it
  is past the design envelope (specs/13 §P2's "Bureau conversation").

## 2026-09-24, 02:30Z — v2.1.22 / r45 IS LIVE: the steward's desk; the database resized

- **The desk** (specs/27): `/steward` opens on Tonight (what is running with its
  own log lines, the record counted, the chain step by step with *Run now* on
  poll/pipeline/embed), a municipality bar scoping every screen, Meetings,
  Log (audit filters + any execution's own sentences), Settings (read-only,
  with where each thing is set), a link back to the record. `record/ops.py`
  reads Cloud Run and Cloud Logging with the service's identity; the
  service carries `RECORD_CLOUD_PROJECT` / `RECORD_CLOUD_REGION`. Proven
  from the cloud: executions listed, a log tail read, the edition manifest
  fetched. **Not yet seen through a signed-in browser** — Stephen should
  open it; anything wrong on screen is the first thing to fix.
- **Cloud SQL `record-pg` is `db-g1-small`** (from `db-f1-micro`, 02:09–02:14Z,
  Stephen's call; ~+$18/mo). Measured on it, same probe as before: the
  100-row SELECT 1.3 s (was 9.5), the embed call 0.95 s, the 100 UPDATEs
  **16.7 s** (was 341 s; median 73 ms a row, max 1.3 s), the behind-count
  0.37 s with the new partial index `002_neural_todo`. Twenty times faster,
  not free: **103,779 segments still have no vector** (the night's 11 new
  tapes added ~35K), which is ~5 hours of `record-embed` at this pace —
  a few nights at 05:45 ET, or run it from the desk. If that is too slow,
  `db-custom-1-3840` (~$49/mo) is the next step; measure a batch first.
- **The first full night landed 11 tapes** (15 → 26 live). The two the
  hour-kills interrupted sit `queued`/mid-flight until the 03:30 ET drain
  reclaims them (by design, v2.1.20).
- ~~Another session ships v2.1.23 / r46 next~~ — shipped (below). A third
  session is building **specs/29 — the broadsheet** on `broadsheet-p0`, and
  takes **r47 / 2.2.0**; it rebases on v2.1.23.

0. **`PAGES_TOKEN` cannot write.** The 2026-09-23 dispatch cloned the Pages
   repo with it and the push was refused (`Permission to
   amateurmenace/publicrecord.git denied`, 403). A fine-grained token needs
   *Contents: read and write* on `amateurmenace/publicrecord` (a classic
   token: `repo`). Until then the carry step fails every night after a
   successful press, and a hand carries the edition (OPERATING §5).
1. ~~Store the YouTube Data API key~~ done 2026-09-23 (`youtube-data-api-key`, on the poll and the pipeline). The original: (he made one on 2026-09-23 and pasted it
   in chat — treat it as exposed: restrict to YouTube Data API v3, rotate):
   `printf '%s' 'KEY' | gcloud secrets create youtube-data-api-key --data-file=- --project=publicrecord-studio`
   then `gcloud run jobs update record-poll --region=us-east1 --update-secrets=RECORD_YOUTUBE_API_KEY=youtube-data-api-key:latest`.
   Without it the probe reads the walled watch page and a standing rule
   approves nothing from the cloud.
2. ~~Flip the standing rule~~ ticked 2026-09-23 on all three sources (Boston City TV, Boston City Council, Brookline Interactive Group). The original: (the console's intake
   screen, per source). The audit names the rule. The constitution page
   already says a standing rule may gate the record.
3. ~~Provision the nightly-edition workflow's three secrets~~ all three exist; see 0 — the token cannot push. The original:
   so ingested meetings reach readers without a hand: until then a press +
   Pages sync is manual (§5), and `edition_date` stays where the last hand
   left it.
4. **Work the steward queue** meanwhile (69 `submitted` on 2026-09-23 after
   the rule's first pass: 58 Boston, 11 Brookline — the older ones a rule
   never re-asks about; `REPROBE_DAYS = 7`).
5. ~~A model-drafted analysis~~ shipped (v2.1.18). The issue-level draft (the
   arc across meetings) is a follow-on and needs a column on `issues`.
6. ~~The ledger sentence about the desk lane~~ shipped (v2.1.18).
7. Still his alone: stored free text beyond title + notes, re-pointing
   sources, spend over $100/mo, paper-as-homepage (declined), brand questions,
   deleting anything, a `record` template for the over-time story.
8. ~~Ship `topic-story`~~ shipped (v2.1.21 / r44, 2026-09-24). Read the
   live front page's three tabs, the search for "AI", a meeting page's find
   box and night cut, and `?` — on a phone — and say what is still unclear;
   that verdict is the next session's brief.
9. **A second featured word** — one line in `web/topic.py::FEATURED` (a
   name, a search, its phrases); the front page grows a fourth tab. And a
   `chart·topic` paper block (a new stored kind — his sign-off first).

## The embed pace — measured, and it is the database (2026-09-24)

Not the API and not a quota: in eight hours the Generative Language API
answered all 72 embedding calls with 200 (no 429s), billing is on, and a
probe from Cloud Run embeds 100 texts in **0.8 s**. One batch of the backfill
loop, timed phase by phase against the live corpus (`record-embed` one-off,
00:40Z): the SELECT of 100 NULL rows **9.5 s**, the embedding call **1.0 s**,
the 100 `UPDATE segments SET emb_neural = …` in one transaction **341 s**
(per row min/median/max 0.5 / 3.0 / 9.3 s). `segments` is 601 MB, 111,712
rows, **70,698 still NULL**, with two HNSW indexes (`idx_seg_emb` on the
lexical `emb`, `idx_seg_emb_neural` on `emb_neural`, both m=16,
ef_construction=64) on Cloud SQL **`db-f1-micro`** (shared core, ~0.6 GB,
10 GB disk): an HNSW insert on an index that cannot sit in memory is
random I/O, seconds per row. The same cost is paid on every ingest, because
`replace_segments` writes `emb` — a 4,800-segment meeting spends minutes in
"placing it on the long view". At this pace the nightly embed job clears
~1,000 rows an hour; the backlog is a month of nights.

**Stephen's decision, not the next session's alone** (it is spend): a
larger instance (`db-g1-small`, 1.7 GB, ~+$17/mo; or `db-custom-1-3840`)
is the plain fix. **Without spend**, the next session can: (1) drop
`idx_seg_emb_neural` for the backfill and rebuild it once (HNSW build on the
micro is itself slow — measure first); (2) index the backfill's own SELECT
(`(meeting_id, id) WHERE emb_neural IS NULL`); (3) consider IVFFlat for
`emb_neural`, or no index at all — an exact scan over ~110K × 768 floats is
~0.5–1 s a query, and search traffic is small; (4) lower `ef_construction`.
Whatever is chosen: measure a batch the same way before and after. The
120 s budget in the pipeline is what keeps a night moving meanwhile —
note the deadline is checked between batches, so the first batch always
runs and costs ~4–6 min at today's pace; `RECORD_EMBED_BUDGET_S` cannot
skip it (0 means no budget).

## Another session, same checkout

On 2026-09-23 a second session was building **specs/25 — the topic story**
(`web/topic.py`, `tests/test_web_topic.py`, `tp-`/`tq-`/`sq-`/`rp-` CSS)
uncommitted on branch `topic-story` **in the main checkout**. v2.1.20 was
built from a worktree on `embed-budget` and landed on `main` without
touching it. Whoever ships `topic-story`: rebase on `main` first (server
files, the workflow, docs and `tests/test_record_metadata.py` moved), take
the next image tag and press version, and move every job.

## Do, in order (a normal session)

1. Suite (`.venv/bin/python -m unittest discover -s tests -t . -q` → 631; PG
   tests skip without `RECORD_TEST_PG_DSN`).
2. Read the live front page first (`https://publicrecord.studio/app/`), both
   stories; then the console's queue. The nightly logs:
   `gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="record-poll"' --limit=40 --freshness=1d`.
3. Any change: review (lenses → skeptics → fold → re-review the fixes,
   executed twins over token pins), deploy by OPERATING §5 — **one image tag
   per deploy, every job moved, press `--version` bumped**, parity-check the
   eleven files (`web/static/app.js`, `web/static/app.web.css`, `web/emit.py`,
   `web/bake.py`, `web/story.py`, `web/charts.py`, `web/topic.py`, `web/cuts.py`,
   `record/papers.py`, `record/press.py`, `record/connectors/youtube.py`),
   Pages sync with the gunzip loop, verify `sw.js`, tag, push.

## Repairing a meeting (a one-off pipeline execution, never from a Mac)

A meeting that landed nameless, undated, or with an extractive summary on
the hosted lane is repaired in place with the pipeline job's own image and
secrets — `gcloud run jobs execute record-pipeline --region=us-east1 --wait
--args='^|^-c|<script>'` — where the script bridges the model key
(`record.pipeline.bridge_model_key(os.environ, Settings().gemini_key)`),
asks `record.connectors.youtube.video_meta(video_id, data_api_key())` for
the title, posting day and length, derives the day with
`highlighter.insight.meeting_day(title, published)`, re-runs
`memory.analyze.summary` where `summary_origin == 'extractive'` and
`memory.analyze.draft` where `analysis.draft` is missing, and upserts the
row. Then press and carry the edition (§5). The 2026-09-23 run repaired four
meetings and drafted the reading for fifteen.

## Verifying locally

Seed a corpus from the LIVE edition (the last session's `seed.py` recipe:
fetch `search/meta.json`, each `meetings/<pid>.json` + `m/<pid>/transcript.txt`,
the top issue planes; parse `[H:MM:SS] text` into segments; upsert meetings,
votes, documents, issues with `link_segments` on the nearest segment; then
`web.bake.bake(db, out, "9.9.9-x", "http://localhost:8765")`), symlink the
output as `app/` under a served root, `python3 -m http.server`. The pane is
narrow (phone width) — use `find` + `scroll_to`; headless Chrome
`--screenshot` works against a copy without `sw.js` (it may hang on exit;
the file is written first).

## Traps this arc taught

- A key pasted in chat is never stored by the assistant; give the commands.
- `--include=*.py` under zsh needs quotes (`--include='*.py'`); `grep` is
  ugrep here — use `/usr/bin/grep` for `-P`-free sanity.
- f-strings cannot hold a backslash in the expression (3.11); build the piece
  first. JS strings in test twins: use ’ not \\'.
- The `both` engine twin stubs the reel engine; the executed twins in
  `TestReviewFoldTwins` are the pattern for new fixes.
- The video flag in `videos.list` is not a captions answer; `captions.list`
  is.
- Headless renders of the front page may show both stories (the toggle runs
  on DOMContentLoaded); the pane shows one, as readers see.
- The press stamps `pressed_at` into `app/pressing.json` on every run and is
  byte-identical otherwise; a carry that diffs the whole tree commits every
  night. Two embedders at once (a pipeline and a backfill) share one
  throttled endpoint and both crawl — the `spend` ledger shows the pace, one
  row per batch. A pipeline execution killed by its timeout is retried once
  (`maxRetries: 1`); the meeting is marked live before its embed, so a kill
  in the embed stage loses vectors only, never the meeting.
- The main checkout may be on someone else's branch with uncommitted work —
  check `git worktree list` and `git status` before anything; build from a
  worktree on a branch of your own.
- The pane keeps the service worker between local presses: a re-press at
  a new local version still served the old `app.js` until the SW was
  unregistered and the caches deleted from the page
  (`navigator.serviceWorker.getRegistrations()` + `caches.keys()`), then a
  fresh navigation. Do that before trusting any pane check of new JS.
- The pane's screenshots of a scrolled front page come back blank (the fake
  clipping CLAUDE.md names); JS geometry (`getBoundingClientRect`,
  `scrollWidth > clientWidth`) is the check that tells the truth.
- In `buildViewer` the viewer's state (`REELPLAY = {…}`) is assigned AFTER
  the stage's HTML — anything wired into the stage that reads `REELPLAY`
  must be built after that line (a live catch: the transport threw and the
  cite list never rendered).
- The reviewer's story counts differ by search: the pressed AI story counts
  "AI" or "artificial intelligence"; the search page's story counts the
  word typed. Both say what they counted beneath the lede.
