# Session prompt — publicrecord-studio: the new home, and everything not done

**Open this session in `~/publicrecord-studio`** — the record's own repo
(github.com/amateurmenace/publicrecord-studio, public, AGPL), extracted
2026-09-23 from the control-z monorepo at `6abb278` and now **the ONE dev
home for the record**. `CLAUDE.md` at the root carries the laws; `README.md`
the shape; `record/OPERATING.md` the ops truth; `specs/` the paper trail.
This prompt supersedes control-z's `specs/vision-session-prompt.md`.

Your job: **ship every requested feature that isn't done** — finish
specs/22 (the cutting room, settled by Stephen 2026-07-22), complete the
repo's openness mechanics (his repo request's second half), and make the
record grow again — with his checkpoints where marked.

## Memory — it does NOT follow you here (do this first)

This is a NEW project directory: your memory starts empty. The record's
hard-won memory lives under the OLD project. Read these three files by
absolute path before acting, then write your OWN memory fresh in this
project as you go (the laws themselves are already in `CLAUDE.md`):

- `/Users/amateurmenace/.claude/projects/-Users-amateurmenace-control-z/memory/specs21-web-studio.md`
  — the shipped arc + P3's traps (aria-attribute CSS pairing, bare
  `var(--focus-ring)`, painted-truth controls, `n_of()`, minted namespaces,
  the twice-encoded `b=` free text, `cut()` at every cap).
- `/Users/amateurmenace/.claude/projects/-Users-amateurmenace-control-z/memory/publicrecord-verify-harness.md`
  — the verify loop (pane is localhost-only; unregister the SW between
  same-version presses; HEADLESS-390 screenshots LIE, trust pane JS
  geometry; a hidden pane no-ops focus(); renderer-blank; the slate).
- `/Users/amateurmenace/.claude/projects/-Users-amateurmenace-control-z/memory/specs20-newspaper-shipped.md`
  — the record arc + the SW-STALENESS law (every deploy bumps `--version`).

## The two-repo rule (the fork is real)

control-z remains the DESK's home; this repo is the RECORD's. The record
halves of control-z (`web/ record/ memory/ czcore/`) are frozen history
from today — do not edit them there. `czcore` now diverges: a shared fix
that matters to both is ported deliberately, named in the commit. One
loose end lives in control-z: **~531 uncommitted lines of a specs/22 P0
partial** in its working tree (app.js +328, css +60, test_web_bake +185 —
`toggleCut`/`wireSegTicks`/`wireBeadTicks`/`searchTick`,
`parseSegTimes`/`segBounds`/`stepEdge`, `writeTray`/`trayAct`,
`TestCuttingRoom` ×5). It was built by an unknown session after specs/22
settled — no review, never committed. **Read it in place
(`git -C ~/control-z diff`), triage against the spec, and port what
survives reading into THIS repo as your own work. Never commit it blind;
never edit it in control-z; when your port has SHIPPED, ask Stephen
whether to discard the control-z working-tree copy — don't discard it
yourself.**

## Establish state (verify, don't trust)

- `curl -s https://publicrecord.studio/app/manifest.json` → version 2.1.10,
  corpus `66c05a9544c70585` — and note `edition_date` 2026-06-18: the
  corpus has been FROZEN for three months (Arc "grow" below).
- This repo: `git log --oneline -3` → `f2c7ff0` CLAUDE.md, `1713ceb` the
  extraction; clean tree; origin = github.com/amateurmenace/publicrecord-studio.
- Set up: `python3 -m venv .venv && .venv/bin/pip install -r
  requirements.txt`, then `.venv/bin/python -m unittest discover -s tests
  -t . -q` → **536 tests** (108 skip without PG/node). If a test needs a
  dep requirements.txt lacks, add it deliberately with a comment. For the
  PG-backed tests: the test Postgres container listens on 55433 when up
  (`docker ps -a` to find/start it), DSN
  `postgresql://record:record@localhost:55433/record_test`.
- `gh auth status` → amateurmenace; the Pages deploy artifact is the
  SEPARATE repo `amateurmenace/publicrecord`.

## Build — in this order, one deploy per phase

**Phase 1 — the cutting room, P0 (specs/22 → v2.1.11/r33).** Read
`specs/22-cutting-room.md` v0.2: Stephen settled all five §6 answers, every
proposal taken — new-tab preview NOW (the scoped stage is a LATER phase);
ONE tray + file-into-paper (no reel library); append-or-replace EXPLICIT
when a shared reel opens; ALL THREE cutting surfaces in P0 (transcript
rows, search hits, issue beads); sub-segment trims OUT — trim stays
segment-snapped, cross-page bounds fetched from the clip's meeting
`transcript.txt`. Port the triaged partial, finish P0, extend the node
twins for every codec change, keep the covenant scans green (the make path
gains NO fetch beyond the record's own planes). Then the review arc, then
deploy.

**Phase 2 — the cutting room, the scoped preview stage.** The settled
"later": a preview stage that plays a clip in place without leaving the
page — WITHOUT destabilizing the `/app/r` page-singleton (armed gate,
settling, global onYT). Design it as its own bounded machine; if it cannot
be bounded, propose the alternative to Stephen before building.

**Phase 3 — the openness mechanics (finishes the repo request).**
(a) Repoint `SOURCE_REPO` in `web/emit.py` to
`https://github.com/amateurmenace/publicrecord-studio` — the covenant and
constitution pages then point at the tree that actually runs. (b) Amend
`record/OPERATING.md` §5: the release step is now native — every deploy
pushes this repo and tags `vX.Y.Z` at the deployed commit. (c) Add minimal
CI (GitHub Actions: the suite without PG — the 536-run with skips — on
push/PR). (d) The constitution's law is now fully checkable: when the use
of AI changes, `page_ai`'s ledger changes in the same commit.

**Phase 4 — the record grows again.** Diagnose the freeze: `gcloud run
jobs executions list` for the nightly schedulers, poll previews (zero
filed + zero unmatched = the feed itself returned nothing — check channel
ids in `record/sources.py`), the steward queue. Fix what's yours to fix;
**re-pointing sources or any new spend is Stephen's call
(AskUserQuestion)**. Prove ONE new meeting lands end-to-end (ingest →
press → live, edition_date moves). Then checkpoint with him: which
towns/bodies next, how far to backfill (captions-first; ASR only where
transcripts are missing; the $100/mo budget stands unless he raises it).
Success metric: edition_date moves weekly, untouched.

**Checkpointed extras (ask, don't assume):** the empty planes
(`described: 0, languages: 0` — wiring Captioner/Translator into the press
is real scope); anything the review arcs surface that smells like new
product.

## Deploy (proven 10×; pre-authorized per phase once its checkpoint is settled)

From THIS repo's root (the Dockerfile copies exactly this tree): suite
green → `docker build --platform linux/amd64 -f record/Dockerfile -t
us-east1-docker.pkg.dev/publicrecord-studio/record/api:rNN .` → push →
verify the new code in-container → `gcloud run jobs update record-press
--region=us-east1 --image=…:rNN --args="^|^-m|record.press|--version|2.1.N"`
→ `gcloud run deploy record-api --image=…:rNN --region=us-east1` →
`gcloud run jobs execute record-press --region=us-east1 --wait` → clone
`amateurmenace/publicrecord`, `gcloud storage rsync -r
--delete-unmatched-destination-objects gs://publicrecord-edition/app app`,
gunzip gzip-magic files in place, KEEP the root hand-files (CNAME,
index.html, constitution/ — OPERATING §5 lists them) → commit + push →
verify live (curls + headless Chrome DESKTOP + pane geometry at 375/390)
→ push + tag THIS repo at the deployed commit. Never rebake the public
edition on this Mac. A code-only change still needs the version bump or
the SW serves stale JS.

## House rules

Per phase: an adversarial review workflow (this sentence is your
authorization to use workflows) — lenses: covenant, brand+a11y (AA
verified numerically from computed styles), backcompat (the shipped
reader AND studio AND store AND the wild v1/v2 links), JS-off/mobile
degrade, logic edges — fold every confirmed finding, then a **focused
re-review of your own fixes** (the fixes have introduced regressions four
consecutive times in this codebase's history). PLAY anything reel-shaped
against a real video (mind the slate — real moments sit past it). Tests
for every codec/plane/store change; node twins pin every JS codec. Commits
in the house voice, ending `Co-Authored-By: Claude
<noreply@anthropic.com>`. After each phase: CHANGELOG, the spec's status
line, `specs/PARALLEL.md`, and YOUR OWN memory (this project's).

## Still Stephen's — do not do unprompted

Discarding control-z's working-tree partial (ask after the port ships).
Store fields or free text beyond title+notes. Re-pointing ingest sources;
spend beyond the $100 budget; the classification tail's model spend.
Studio hue on a rendered paper; paper mode louder. Editing control-z's
record halves. The brand open questions (Command-Z, the Translator
prefix, Neighborhood AI's URL, Control-Z's mark). Deleting anything.
