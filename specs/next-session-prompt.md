# Session prompt — publicrecord-studio: after v2.1.16, what is Stephen's

**Open this session in a checkout of github.com/amateurmenace/publicrecord-studio**
(on a new machine: `gh repo clone amateurmenace/publicrecord-studio`, then
`python3.11 -m venv .venv && .venv/bin/pip install -r requirements.txt` —
system python may be 3.14, too new). `CLAUDE.md` carries the laws;
`specs/24-two-paths.md` is the newest scope (BUILT + LIVE); `specs/23` is
done. **Memory from the last machine does not travel — this file is the
state.** Written 2026-09-23, late.

## Where things stand

- **LIVE: v2.1.16 / r38** — tag `v2.1.16` at the deployed commit, SW cache
  `cz-record-2.1.16-…`. Two things shipped together:
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

1. **Store the YouTube Data API key** (he made one on 2026-09-23 and pasted it
   in chat — treat it as exposed: restrict to YouTube Data API v3, rotate):
   `printf '%s' 'KEY' | gcloud secrets create youtube-data-api-key --data-file=- --project=publicrecord-studio`
   then `gcloud run jobs update record-poll --region=us-east1 --update-secrets=RECORD_YOUTUBE_API_KEY=youtube-data-api-key:latest`.
   Without it the probe reads the walled watch page and a standing rule
   approves nothing from the cloud.
2. **Flip the standing rule** on the sources he trusts (the console's intake
   screen, per source). The audit names the rule. The constitution page
   already says a standing rule may gate the record.
3. **Provision the nightly-edition workflow's three secrets** (OPERATING §5)
   so ingested meetings reach readers without a hand: until then a press +
   Pages sync is manual (§5), and `edition_date` stays where the last hand
   left it.
4. **Work the steward queue** meanwhile (3 Boston submissions filed
   2026-09-23; 0 approved).
5. **A model-drafted analysis** beside the summary (specs/24 §4) — spend and
   a ledger row in the same commit; the `reading` block is where it renders.
6. The ledger names Gemini Flash as the hosted summary lane, but the twelve
   live meetings' summaries are labeled `ai:gpt-4o-mini` (desk-drafted, before
   the hosted lane). A sentence on `/app/ai` about lanes past and present is
   his call.
7. Still his alone: stored free text beyond title + notes, re-pointing
   sources, spend over $100/mo, paper-as-homepage (declined), brand questions,
   deleting anything, a `record` template for the over-time story.

## Do, in order (a normal session)

1. Suite (`.venv/bin/python -m unittest discover -s tests -t . -q` → 584; PG
   tests skip without `RECORD_TEST_PG_DSN`).
2. Read the live front page first (`https://publicrecord.studio/app/`), both
   stories; then the console's queue. The nightly logs:
   `gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="record-poll"' --limit=40 --freshness=1d`.
3. Any change: review (lenses → skeptics → fold → re-review the fixes,
   executed twins over token pins), deploy by OPERATING §5 — **one image tag
   per deploy, every job moved, press `--version` bumped**, parity-check the
   nine files (`web/static/app.js`, `web/static/app.web.css`, `web/emit.py`,
   `web/bake.py`, `web/story.py`, `web/charts.py`, `record/papers.py`,
   `record/press.py`, `record/connectors/youtube.py`), Pages sync with the
   gunzip loop, verify `sw.js`, tag, push.

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
