# Session prompt — publicrecord-studio: the open newsroom (specs/23, A → D)

**Open this session in `~/publicrecord-studio`** — the record's one dev home
(github.com/amateurmenace/publicrecord-studio, public, AGPL; extracted from
control-z@`6abb278`). `CLAUDE.md` carries the laws; **`specs/23-open-newsroom.md`
is THE scope — settled with Stephen 2026-09-23, all four answers on the
record.** This prompt orients; the spec governs.

The mandate, in Stephen's words: *"i really need publicrecord.studio to
work… i don't see any clear way for users to customize their newspaper
front pages… make the web app as feature rich and powerful as it can be."*
The diagnosis (verified live 2026-09-23, v2.1.10): nothing is broken — the
making half is INVISIBLE. One corner pill and one quiet sentence carry the
product's entire second half. specs/23 fixes that in four phases, all
settled: **A** the front door + the real on-page editor → **B** the cutting
room (specs/22, settled 2026-07-22) → **C** the rich tier (layout, multiple
papers, richer blocks, print) → **D** openness mechanics + the record grows
again. One deploy per phase; Phase A targets **v2.1.11/r33**; tags advance
one per deploy.

## Memory — it does NOT follow you here (do this first)

New project directory ⇒ empty memory. Read the old project's memory by
absolute path, then build your own here as you go:

- `/Users/amateurmenace/.claude/projects/-Users-amateurmenace-control-z/memory/specs21-web-studio.md`
  — the shipped arc + its traps (aria-attribute CSS pairing; bare
  `var(--focus-ring)` = outline:none; painted-truth controls; `n_of()`;
  twice-encoded `b=` free text; `cut()` at every cap; minted namespaces
  `cz- pb- rt- pf- .featline cz-tpl*` — grep the sheet before minting).
- `…/memory/publicrecord-verify-harness.md` — the verify loop (the in-app
  pane is localhost-ONLY; unregister the SW between same-version local
  presses; HEADLESS-390 screenshots LIE — trust pane JS geometry; a hidden
  pane no-ops `element.focus()`; renderer-blank after scroll; the slate —
  real moments sit past it).
- `…/memory/specs20-newspaper-shipped.md` — the SW-STALENESS LAW: every
  deploy bumps the press `--version` or returning readers get cached JS.

## Establish state (verify, don't trust)

- Live: `curl -s https://publicrecord.studio/app/manifest.json` → 2.1.10,
  `edition_date` **2026-06-18** (the freeze — Phase D2's metric).
- This repo: clean tree on `main`; `.venv` exists (server deps);
  `.venv/bin/python -m unittest discover -s tests -t . -q` → **536 tests OK
  (110 skipped: PG, node, PIL — each guard says why)**.
- The test Postgres: `docker ps -a | grep 55433` to find/start it. **A DSN
  pointing at a DOWN PG errors ~108 tests instead of skipping** — start it
  BEFORE exporting `RECORD_TEST_PG_DSN=postgresql://record:record@localhost:55433/record_test`.
- `gh auth status` → amateurmenace. Pages artifact = the SEPARATE repo
  `amateurmenace/publicrecord`. Never rebake the public edition locally.

## The two-repo rule + the control-z partial

control-z stays the desk's home; its record halves are frozen history —
never edit them there; `czcore` diverges from today, shared fixes ported
deliberately. One loose end: **~531 uncommitted lines of a specs/22 P0
partial** in control-z's working tree (`git -C ~/control-z diff`):
`toggleCut/wireSegTicks/wireBeadTicks/searchTick`,
`parseSegTimes/segBounds/stepEdge`, `writeTray/trayAct`, `TestCuttingRoom`
×5. Its non-PG suite passed alongside HEAD; it has had NO review arc.
When Phase B starts: triage it against specs/22, port what survives into
THIS repo as your own work, never commit it blind — and after your port
SHIPS, ask Stephen whether to discard the control-z copy; never discard it
yourself.

## Build (specs/23 §4 is the full detail — this is the shape)

- **A — the front door + the editor (v2.1.11/r33).** A real baked
  front-page section (benefit copy, **Start your paper** → `/app/p#edit`,
  template starts, the featured papers grown into cards — paper palette,
  new namespace, grep first); script-added "＋ your paper" affordances on
  meeting/issue cards in preview+studio modes (NEVER baked, never in paper
  mode — extend the byte-clean guard to prove both); `/app/p` in studio
  mode becomes the DRAFT's on-page editor (drag handles + the panel as the
  keyboard path, per-block ✕, in-place title, an insertion-point add with
  INLINE lexical search over the static index — no new API doors, the
  door-count guard stays); the empty draft teaches; the pill says the
  thing itself ("✎ Your paper — edit"; update pinned copy tests). Shared/
  stored papers stay read-only until B's make-this-yours.
- **B — the cutting room (specs/22, then B2 the scoped preview stage).**
  The five settled answers verbatim: all three cutting surfaces; ONE tray
  + file-into-paper; append-or-replace explicit; segment-snapped trim with
  cross-page bounds from the clip's meeting `transcript.txt`; new-tab
  preview now, the scoped stage as B2 (a bounded machine — if it cannot be
  bounded without destabilizing the `/app/r` page-singleton, propose the
  alternative to Stephen before building).
- **C — the rich tier (C1 then C2).** C1: multiple named papers
  (`cz-papers` + active pointer, one-time migration of `cz-paper` — the
  loadReel-migration pattern) + layout ENUMS per block (lead / section
  header / half-width pair) carried in doc+link+export+store; version by
  `paperV`'s rule, old links keep reading; store extension is enums-only
  with strict refusal. C2: pull-quote block (text fetched from the plane
  at render — REFS ONLY, nothing new stored), document block, "what
  changed" digest block; `record/papers.py::_block` extends with the same
  strictness — **free text stored stays title+notes; anything more is
  Stephen's sign-off**; plus the print stylesheet (a rendered paper prints
  as a real newspaper page).
- **D — openness + growth.** D1: repoint `SOURCE_REPO` in `web/emit.py`
  to this repo; OPERATING §5 gains push+tag-at-deploy; minimal CI (the
  no-PG 536 run on push/PR). D2: diagnose the freeze (`gcloud run jobs
  executions list`; poll previews — zero filed + zero unmatched = the feed
  returned nothing, check `record/sources.py` channel ids; the steward
  queue); fix what's ours — **re-pointing sources or new spend is
  Stephen's (AskUserQuestion)**; prove ONE meeting lands
  ingest→press→live; then the growth checkpoint (towns, backfill depth,
  the $100/mo stands unless he raises it). Success: edition_date moves
  weekly, untouched.

## Deploy (proven 10×; pre-authorized per phase once its checkpoint is settled)

From THIS repo's root (the Dockerfile copies exactly this tree): suite
green → `docker build --platform linux/amd64 -f record/Dockerfile -t
us-east1-docker.pkg.dev/publicrecord-studio/record/api:rNN .` → push →
verify in-container → `gcloud run jobs update record-press
--region=us-east1 --image=…:rNN --args="^|^-m|record.press|--version|2.1.N"`
→ `gcloud run deploy record-api --image=…:rNN --region=us-east1` →
`gcloud run jobs execute record-press --region=us-east1 --wait` → clone
`amateurmenace/publicrecord`, `gcloud storage rsync -r
--delete-unmatched-destination-objects gs://publicrecord-edition/app app`,
gunzip gzip-magic in place, KEEP the root hand-files (CNAME, index.html,
constitution/) → commit+push → verify live (curls + headless desktop +
pane geometry at 375/390) → push + tag THIS repo at the deployed commit.
A code-only change still needs the version bump or the SW serves stale JS.

## House rules

Per phase: an adversarial review workflow (this sentence is your
authorization) — lenses: covenant, brand+a11y (AA numeric from computed
styles), backcompat (reader AND studio AND store AND wild v1/v2 links),
JS-off/mobile degrade, logic edges — fold every confirmed finding, then a
**focused re-review of your own fixes** (the fixes have regressed four
consecutive times in this codebase's history). PLAY reel-shaped things
against a real video. Tests for every codec/plane/store change; node twins
pin every JS codec. The invitation may be visible; paper mode and every
RENDERED paper stay exactly as quiet as today — zero fuchsia, ever. Any
change to AI use updates `/app/ai` in the same commit. Commits in the
house voice, ending `Co-Authored-By: Claude <noreply@anthropic.com>`.
After each phase: CHANGELOG, the spec's status line, `specs/PARALLEL.md`,
your own memory, and tell Stephen what's live with links.

## Still Stephen's — never unprompted

Discarding control-z's partial (ask after the port ships). Free text in
the store beyond title+notes. Re-pointing ingest sources; spend beyond
$100/mo; the classification tail. Paper-as-homepage (offered, declined).
Studio hue on a rendered paper; paper mode louder. Editing control-z's
record halves. The brand open questions. Deleting anything.
