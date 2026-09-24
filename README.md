# publicrecord.studio

**The Public Record — what local government said, on the record.**
Track it across years of meetings: read every meeting as a document, follow
the issues that span them, watch the votes, cut the moments that matter into
reels, and edit your own paper from the record's raw material.

Live at **[publicrecord.studio](https://publicrecord.studio)** ·
an open source project from [weird machine](https://weirdmachine.org) and
[brookline interactive group](https://brooklineinteractive.org) ·
part of the [Community AI Project](https://communityai.studio).

This project uses AI in accordance with
**[Our AI Constitution](https://publicrecord.studio/constitution)** — when a
model touches the record, whose model it is, where it runs, and what stands
when it is gone. Every promise on that page is checkable against this
repository; when our use of AI changes, the page changes in the same commit.

## The shape of the thing

The reader is **static**. That is not a limitation being worked around; it is
the resilience answer and the cost answer in one move. A nightly **press**
bakes the whole record — meetings, transcripts, issues, timelines, votes,
analytics, a lexical search index — into an envelope of plain files, and
that envelope reads with the server dead, the database gone, and the
aeroplane mode on.

| Piece | What it is |
|---|---|
| `web/` | The press: `bake.py` reads the corpus and `emit.py` writes the edition — every page, plane and stub the reader touches; `story.py`, `charts.py` and `topic.py` tell the front page's stories (the record over time, the latest meeting, a word over time), counted, never modeled. `web/static/app.js` is the whole client (no build step): reading, search told as a story, the reel composer and player, the studio, your paper. |
| `record/` | The hosted half: the FastAPI service (semantic search, freshness, submissions, the shared-paper store, the steward console), the nightly press job, ingest pipeline, and the ops manual (`record/OPERATING.md`). |
| `memory/` | The corpus engine: ingest, the issue engine, votes, documents, analysis, embeddings — SQLite at the desk, Postgres+pgvector hosted, one seam. |
| `czcore/` | The shared core the record draws from (moment scoring, kits, the LLM seam, jobs). |
| `highlighter/` | One analytical module (`insight.py`) the summarizer leans on; the full Highlighter desk app lives elsewhere. |
| `brand/` | The design tokens and marks the press bakes in. |
| `specs/` | The paper trail: specs 17–22, the session prompts, and the state of main. |
| `tests/` | The record's suite. The strict-covenant tests are the interesting ones: the pressed paper is byte-clean of studio chrome, the studio palette cannot reach a rendered page, the make path touches no server, and the API surface is counted. |

**The covenant** (see it live at
[/app/covenant](https://publicrecord.studio/app/covenant)): static files
only; no cookies, analytics, or telemetry; reader state lives in the
browser; embeds are click-to-load; no person pages; corrections annotate;
everything downloads. If the servers vanish, the record still reads *and*
composes.

## Run it

```bash
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
.venv/bin/python -m unittest discover -s tests -t . -q     # the suite
```

Press a local edition and read it:

```bash
.venv/bin/python -m web.bake path/to/corpus.db /tmp/edition 0.0.1 http://localhost:8899
mkdir -p /tmp/serve && ln -sfn /tmp/edition /tmp/serve/app
(cd /tmp/serve && python3 -m http.server 8899)   # → http://localhost:8899/app/
```

Run the API (optional — the edition reads without it):

```bash
uvicorn record.app:app --port 8330
```

Hosting, deployment, budgets, and the takedown path are in
`record/OPERATING.md`; infrastructure in `record/INFRA.md`. The container
(`record/Dockerfile`) copies this repository's packages whole — what you
read here is what runs there.

## Licensing

- **Code: AGPL-3.0** — a license whose whole purpose is that a public thing
  stays public. Anyone can run their own record: the town, the library, a
  neighbor with a laptop. Anyone who changes it and runs it as a service
  owes those readers the changed program too.
- **The record's content: CC BY-SA 4.0.** The meetings belong to the town.

Which license covers which part, in full: [LICENSING.md](LICENSING.md).

## Provenance

Extracted 2026-09-23 from the `control-z` monorepo at commit `6abb278`,
where this app was designed and built (specs/17 → specs/22, the whole arc in
`specs/` and `CHANGELOG.md`). This repository is the record's public home;
the pressed editions deploy from
[`amateurmenace/publicrecord`](https://github.com/amateurmenace/publicrecord).

designed + developed by Stephen Walter with Brookline Interactive Group &
Neighborhood AI · CC BY-SA 4.0
