# Session prompt — publicrecord-studio: after v2.1.20, what is Stephen's

**Open this session in a checkout of github.com/amateurmenace/publicrecord-studio**
(on a new machine: `gh repo clone amateurmenace/publicrecord-studio`, then
`python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt` —
system python may be 3.14, too new). `CLAUDE.md` carries the laws;
`specs/24-two-paths.md` is the newest scope (BUILT + LIVE); `specs/23` is
done. **Memory from the last machine does not travel — this file is the
state.** Written 2026-09-23, late; the topic-story branch noted later that night.

## Where things stand

- **BUILT, on branch `topic-story` (not merged, not deployed): a word, over
  time** (`specs/25-a-word-over-time.md`) — Stephen's UX verdict of
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
  way (eleven findings folded, five more on re-review). 629 tests. **Next:
  rebase on main, deploy as v2.1.21 / r44** (v2.1.20 / r43 is
  the embed-budget deploy; OPERATING §5 — press `--version 2.1.21`; the version bump is the cache
  key; parity-check the ten files, now including `web/topic.py`).
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

## Stephen's decisions (never unprompted) — the switches that make the night run

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
8. **Ship `topic-story`** (specs/25 §4): rebase on main, press `--version
   2.1.21`, r44 (every job moved), the Pages sync, the tag. Then read the live front page's three tabs
   and the search for "AI" on a phone.
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
   ten files (`web/static/app.js`, `web/static/app.web.css`, `web/emit.py`,
   `web/bake.py`, `web/story.py`, `web/charts.py`, `web/topic.py`,
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
