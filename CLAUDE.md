# publicrecord.studio — project instructions

This is **the record's public home**: the press, the corpus engine, the API,
and the studio behind [publicrecord.studio](https://publicrecord.studio).
Extracted 2026-09-23 from the `control-z` monorepo at `6abb278` — the exact
closure `record/Dockerfile` ships, so what you read here is what runs.
READ `README.md` first; the ops truth is `record/OPERATING.md`; the paper
trail is `specs/` (17–22 + PARALLEL + the session prompts).

## The relationship with control-z (check before building)

As of the extraction, **development history lives in `~/control-z`** (46
commits ahead of its own GitHub remote, by design) and this repo is the
release surface. The monorepo's working tree also holds an uncommitted
partial of specs/22 P0. Until Stephen settles the source-of-truth question
(the vision prompt's Arc C — export-on-release vs. this repo becoming the
dev home), **do not develop the same feature in both trees**: check
`git -C ~/control-z log --oneline -3` and ask him where this session's work
should land. Changes made here must be mirrored or migrated deliberately,
never assumed.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -t . -q   # 766 tests; PG-backed ones
                                                          # skip without RECORD_TEST_PG_DSN
```

Local press + read: `web.bake` to a scratch dir, symlink it as `app/` under
a served root (pages use absolute `/app/…` paths), `python3 -m http.server`.
API: `uvicorn record.app:app --port 8330` (optional — the edition reads
without it). **Never rebake the public edition from a local corpus.**

## The laws (each has a guard test — keep them passing)

- **The covenant is load-bearing**: the reader is static files; the make
  path (compose/curate) touches NO server — a test scans the studio and
  paper sections of `web/static/app.js` for `fetch(`/`/api/`. The store and
  search are ADDITIVE; every decoder follows decodeReel's law (malformed →
  fewer blocks, never a throw). No cookies, no analytics, no reader
  identity, ever.
- **Palette**: publicrecord takes **zero fuchsia**. Studio hues (`#a855f7`,
  `#7c3aed`, `#22c55e`) exist only under `html.cz-m-studio`; a rendered,
  shared, or baked paper carries none of them. The pressed pages are
  byte-clean of studio markup (script-built, never baked).
- **The store is strict, not corrective**: free text stored = the title +
  notes ONLY (length-capped, control-chars refused); everything else is
  exact-shaped refs; canonical bytes are decided SERVER-side only
  (`record/papers.py`) — the client never hashes. Any new stored field
  needs Stephen's explicit sign-off first.
- **The SW-staleness law**: every deploy bumps the press `--version` or
  returning readers get cached JS. It bites local preview loops too —
  unregister the SW between same-version presses.
- **A search is a story, counted** (specs/25): `web/topic.py` and its JS
  twin `tpAggregate` must answer alike (a node twin test holds it); the
  pressed topic story is content (no button, no `cz-`), its reel links are
  the viewer's own grammar, and the front page leads with it only above
  the floor (three lines, two meetings).
- **Our AI Constitution is a promise with a page**
  (`/app/ai` · publicrecord.studio/constitution): when the use of AI
  changes, `web/emit.py::page_ai`'s ledger changes **in the same commit**.
- **Controls describe the painted state**, not storage (`shownMode`, not
  `readMode`, where they diverge); an aria-attribute migration moves its
  CSS selector with it; `var(--focus-ring)` needs its `var(--state)`
  fallback or the ring silently dies; counted nouns go through `n_of()`.
- CSS namespaces already minted: `cz-*` (studio), `pb-` (papers), `rt-`
  (tray), `pf-` (featured), `.featline`, `cz-tpl*` — grep the sheet before
  minting more. Plus `tp-`/`tq-` (the topic story, pressed and
  live), `sq-` (the search page's story + progress), `rp-` (the reel
  viewer's transport) — specs/25; `mp-` (the meeting page's cut, find,
  words, jump bar), `kb-` (the keys sheet) — specs/26; `rd-` (a model's
  prose, read: its heading lines and lists), `pic-` (a picture's download
  line), `dg-` (drag to reorder), `gl-` (the glossary) — specs/27. Plus `bs-` (the civic
  broadsheet: the masthead, the spine and its type-ahead, the score, the
  year, the columns, the river, the strips, the doors) — specs/29.
- **A model's answer is whole or it is nothing** (specs/27): the seam gives
  a thinking model its own room (`GEMINI_THINKING_ROOM`) and refuses an
  answer cut off at its length limit on every provider; a caller's fallback
  stands instead. A model's prose is rendered by `receipt_paras` and its JS
  twin `receiptParas` only — escaped first, a node twin holds them equal.
- **The glossary's definitions are model-written and say so** (`web/glossary.py`,
  the page's label, the ledger row on `/app/ai`); its counts are the press's.
  A new entry names a public source it paraphrases; no person is defined.

## Verifying

Prefer JS geometry over screenshots (headless Chrome at narrow widths
shows FAKE clipping — a tool artifact); the Claude-in-app browser pane is
localhost-only and its hidden document no-ops `element.focus()`. Play
anything reel-shaped against a real video — real civic tapes open with a
dead-air slate; real moments sit past it. Node twins pin every JS codec
(`tests/test_web_bake.py` lifts functions by regex and runs them — extend
the twin when you touch a codec).

## Shipping

Suite green first, always. Deploy is `record/OPERATING.md` §5 (build the
container, press from the cloud, rsync to the `amateurmenace/publicrecord`
Pages repo, gunzip gzip-magic in place, KEEP the root hand-files: CNAME,
index.html, constitution/). Per feature: an adversarial review pass, fold
every confirmed finding, then re-review your own fixes — the fixes have
introduced regressions four consecutive times in this codebase's history.
Commits in the house voice (essayistic, lowercase domains, benefit-forward),
ending `Co-Authored-By: Claude <noreply@anthropic.com>`.

## Licensing + credit

Code AGPL-3.0; the record's content CC BY-SA 4.0 (`LICENSING.md` says which
covers what). Credit: designed + developed by Stephen Walter with Brookline
Interactive Group & Neighborhood AI.
