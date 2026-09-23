# Session prompt — publicrecord-studio: ship the v2.1.15 fold, then what is Stephen's

**Open this session in a checkout of github.com/amateurmenace/publicrecord-studio**
(on a new machine: `gh repo clone amateurmenace/publicrecord-studio`, then
`python3 -m venv .venv && .venv/bin/pip install -r requirements.txt`).
`CLAUDE.md` carries the laws; `specs/23-open-newsroom.md` is the scope (A–C
live, D1 live, D2 diagnosed). **Memory from the last machine does not travel —
this file is the state.** Written 2026-09-23 at the end of the day.

## Where things stand

- **LIVE: v2.1.14** — image `record/api:r36`, tag `v2.1.14` at `a1b2515`,
  SW cache `cz-record-2.1.14-…`. specs/23 A–C: the front door and the on-page
  editor (A), the cutting room and its preview stage (B, B2), the rich tier —
  a shelf of papers, layouts, pull-quote / filing / digest refs, print (C).
  `main` = what is live, plus docs.
- **READY, NOT DEPLOYED: branch `fold-v2.1.15`** (`b3f9a04` the code,
  `93e32f6` its changelog entry). It folds a focused re-review of v2.1.14's
  two folds: fourteen findings (twelve distinct), all folded — live print
  twins for the editor's note and title; halves painted at half width only
  where the reader's page pairs them; the add-search's lines appended in
  place and no premature "no match"; undated digests shown as undated; an
  empty tape's quote said as "not in this pressing"; a real "try again" in
  the document chooser; on /app/r, a second cite of a stashed switch's
  meeting moves the switch, and a page-frame ▶ resumes a paused reel from
  where the frame stands; the stage cues a stopped clip at its exact start
  and a trim reaches the clip a stop left behind. 560 tests green; a
  mutation pass reverted each of the seventeen fixes and every revert fails
  the suite; pane-checked on a local preview. Review tally: eight findings
  reached their skeptics (fifteen votes, all standing); six were read
  against the code by hand (their skeptics hit the account's spend limit).

## Do, in order

1. `git fetch && git checkout fold-v2.1.15`; run the suite
   (`.venv/bin/python -m unittest discover -s tests -t . -q` → 560; the
   Postgres-backed tests skip without `RECORD_TEST_PG_DSN` — none of them
   cover what this fold touches). Read `git show b3f9a04`.
2. If credits allow, a lean adversarial review of `b3f9a04` (three lenses,
   ≤ 5 findings each, two skeptics per finding). Verifiers read the working
   tree — don't edit it while they run — and they share the Browser pane, so
   stay out of the pane until they finish. Fold what they confirm, then
   re-review your own fixes (fixes have introduced regressions here before).
3. **Deploy v2.1.15** by `record/OPERATING.md` §5 (pre-authorized):
   - `docker build --platform linux/amd64 -f record/Dockerfile -t us-east1-docker.pkg.dev/publicrecord-studio/record/api:r37 .`
     from the branch tip; parity-check sha256 of `web/static/app.js`,
     `web/static/app.web.css`, `web/emit.py`, `web/bake.py`,
     `record/papers.py`, `record/press.py` inside the image against the
     tree (in zsh, list the files literally); `docker push`.
   - `gcloud run jobs update record-press --region=us-east1 --image=…:r37 --args="^|^-m|record.press|--version|2.1.15"`,
     `gcloud run deploy record-api --image=…:r37 --region=us-east1 --quiet`,
     `gcloud run jobs execute record-press --region=us-east1 --wait`.
   - Clone `amateurmenace/publicrecord`;
     `gcloud storage rsync -r --delete-unmatched-destination-objects gs://publicrecord-edition/app app`;
     gunzip every gzip-magic file in place (the Python loop in §5); keep the
     root hand-files (`CNAME`, `index.html`, `constitution/`, `.nojekyll`);
     confirm the pressed HTML is byte-clean (no `cz-`/`pb-pv`/`pb-quote`/
     studio hues); commit and push.
   - Poll `https://publicrecord.studio/app/sw.js` until it names
     `cz-record-2.1.15-…`; confirm the live `app.js` carries the fold
     (`function reelNext`, `const halfPairs`, `notePrint`).
   - `git checkout main && git merge --ff-only fold-v2.1.15`;
     `git tag -a v2.1.15 <deployed commit> -m "v2.1.15 / r37 — …"`;
     `git push origin main --tags`. Update specs/23's status line,
     `specs/PARALLEL.md`'s "State of main", and replace this prompt.
4. Report what is live, and Stephen's decisions (below).

## Tooling on a new machine

- gcloud authenticated as **swalter4669@gmail.com** (project
  `publicrecord-studio`, region `us-east1`); a second account on the old
  machine could not refresh non-interactively. `gcloud auth configure-docker us-east1-docker.pkg.dev`.
- Docker Desktop running; `gh auth status` able to push both repos.
- **Never rebake the public edition from a local corpus.** Every deploy
  bumps `--version` (the service worker's cache key).

## Verifying locally

A preview needs a corpus. Seed one from the LIVE record: fetch
`https://publicrecord.studio/app/search/meta.json` and
`/app/m/<pid>/transcript.txt` for a few meetings, parse `[H:MM:SS] text`
lines into segments, upsert meetings and issues into `memory.store.Corpus`,
then `web.bake.bake(db, out, "9.9.9-x", "http://localhost:8765")`; symlink the
output as `app/` under a served root; `python3 -m http.server`. Unregister the
service worker between same-version presses. In the Browser pane, post
`{event:'command',func:'playVideo'}` to an iframe to stand in for the
reader's own ▶ on the real YouTube embed, and log messages by `e.source`
per frame. Call `resize_window` before any geometry (a hidden pane reports
`innerWidth: 0`). Print checks: headless Chrome `--print-to-pdf` against a
copy of the edition without `sw.js` (it hangs otherwise), under a subprocess
timeout; the Read tool renders the PDF.

## Traps this arc taught

- YouTube's widget: a `pauseVideo` sent before playback begins is ignored;
  `cueVideoById` replaces a pending autoplay; `initialDelivery` and
  `onReady` arrive together (ready work runs once); `infoDelivery` carries
  `playerState` only when it changes.
- The two engines — the page player (`YT`) and the preview stage (`PV`) —
  hold a frame silent after the other speaks until it is SEEN paused or
  cued; a play meanwhile with no reader focus in the frame is paused again.
  Every door into one engine pauses the other.
- Node twins lift functions by regex: lift every helper a lifted function
  calls (`reelNext` beside `reelAdvance`); `helpers()` already defines `r1`,
  and `PRELUDE` defines `BASE` and `location`.
- A token pin can survive a revert — prefer twins that execute the code,
  and mutation-check each new fix.
- Worktree branches: `.gitignore` lists `.venv` (a symlink) as well as
  `.venv/`; check `git ls-tree -r HEAD | grep .venv` before pushing one.

## Stephen's decisions (never unprompted)

- Work the steward queue — the pipeline finds 0 approved submissions, which
  is why `edition_date` still reads 2026-06-18.
- A YouTube Data API key (spend) or a desk-side caption step — Cloud Run's
  address is served YouTube's bot wall, so a hosted caption fetch fails.
- Provision the nightly-edition workflow's three secrets (OPERATING §5).
- Discard control-z's uncommitted specs/22 partial (ported here); delete
  stale branches and worktrees (`c1f`, and `fold-v2.1.15` once merged).
- Still his alone: stored free text beyond title + notes, re-pointing
  sources, spend over $100/mo, paper-as-homepage (declined), the brand
  questions, deleting anything.
