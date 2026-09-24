# Running publicrecord.studio

Everything you need to run the record, find out what it is doing, and fix it
when it stops. Written to be read at 11pm by someone who did not build it.

**Provisioned 2026-07-19.** Project `publicrecord-studio`, region `us-east1`,
billed to *Firebase Payment*, budget **$100/mo** scoped to this project alone.

---

## 1. The consoles

| What | Where |
|---|---|
| **Project home** | <https://console.cloud.google.com/home/dashboard?project=publicrecord-studio> |
| **The service** (logs, revisions, traffic) | <https://console.cloud.google.com/run/detail/us-east1/record-api/metrics?project=publicrecord-studio> |
| **The jobs** (migrate, seed, press, poll) | <https://console.cloud.google.com/run/jobs?project=publicrecord-studio> |
| **The database** | <https://console.cloud.google.com/sql/instances/record-pg/overview?project=publicrecord-studio> |
| **The edition bucket** | <https://console.cloud.google.com/storage/browser/publicrecord-edition?project=publicrecord-studio> |
| **Secrets** | <https://console.cloud.google.com/security/secret-manager?project=publicrecord-studio> |
| **The bill** | <https://console.cloud.google.com/billing/01BA3F-D33117-58BB2B/reports?project=publicrecord-studio> |
| **Logs, everything** | <https://console.cloud.google.com/logs/query?project=publicrecord-studio> |
| **The image** | <https://console.cloud.google.com/artifacts/docker/publicrecord-studio/us-east1/record?project=publicrecord-studio> |

**The API:** <https://record-api-907309358085.us-east1.run.app>
**The steward console:** <https://record-api-907309358085.us-east1.run.app/steward>
**The reader:** <https://publicrecord.studio> — **live** (2026-07-19). The
live-first edition: 12 meetings, meaning-search from the API, degrading to its
own prebuilt index when the API is dark. Served from GitHub Pages on its own
repo, `amateurmenace/publicrecord` (see §11 for how it is deployed and
refreshed).
**The reader (the older edition):** <https://control-z.org/app> — the desk's
static 1.9.0 pressing, 10 meetings, no meaning-search. Left in place so every
citation minted against it survives; the eventual tools-site move (specs/18,
R1.8) is what retires `/app` from this domain.

---

## 2. Is it alive?

One command answers most questions:

```bash
curl -s https://record-api-907309358085.us-east1.run.app/api/health | python3 -m json.tool
```

It is deliberately honest about **halves**. A green light over a dead neural
index is how a degraded search ships for a month, so this never reports one.

- `ok: true` and a `record` block with counts — the corpus is reachable
- `neural.available: true` — the key is wired. If this ever reads `false`, the
  `reason` names the cause, and search silently falls back to words with an
  honest line rather than erroring.
- `steward_console: true` — the console is wired. A steward route without a
  valid token answers **401** ("sign in"); a verified Google account that is not
  on the allowlist gets **403** ("you may not"), because retrying the sign-in
  cannot help and the message should not send someone round a loop. If this
  key ever reads a sentence instead of `true`, that sentence names the missing
  variable and every steward route is 503 — it fails *closed*, never open.
- HTTP 503 with `"the corpus is unreachable"` — the database is down or the
  connector is broken. Go to §6.

---

## 3. The shape of the thing

Two halves, and the split is the whole design.

**The reader is static.** A pressed edition — JSON and HTML, no backend — that
carries the meetings, issues, timelines, ledgers and a prebuilt search index.
It reads with the database gone, the API dead, and the aeroplane mode on. This
was tested by stopping Postgres and walking the site; it searched all 16,443
segments and never noticed.

**The API is small on purpose.** It carries only what an envelope of files
structurally cannot: semantic search (needs a vector index at query time),
freshness, live submissions, and the steward console. If the API is down,
**the record still reads.** That is not a consolation, it is the architecture.

So: *the API being down is not an outage of the record.* It is an outage of
search-by-meaning and of intake. Fix it calmly.

---

## 4. Adding meetings

Nothing ingests on its own say-so. A video becomes a meeting in three steps,
and a human is in the middle on purpose.

**1. The intake rules decide what is even a candidate.** A municipal channel
is not a meeting feed — Brookline posts *TV on TV* beside the Select Board;
Boston City TV posts a library dedication beside the BPDA. The rules are
**default-deny**: a video enters the queue only if its title matches a rule
that *names a public body*. No rule, no entry, no spend.

**2. Preview before you poll.** In the console, or:

```bash
curl -s -X POST $API/api/steward/preview \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"source": {...}, "limit": 15}'
```

It returns three lists — would-file, excluded, unmatched — and `would_cost`,
the number of meetings a real poll would file. **Nothing is written.** On
Boston City TV this reads: polled 15, would file 4.

**3. Approve.** The queue is at `/api/steward/submissions`; approving marks a
row for the pipeline rather than transcribing inline, so you are never holding
a browser open while a meeting processes.

### When a title is missed

Unmatched titles come back as **suggested rules** with the body name inferred
from the title's stable head. One click adds it. The taxonomy gets learned
from what the town actually posts instead of guessed in advance — which is
what the live polls proved necessary: Boston's council never says "Committee
on", it titles sessions `<Name> on <Date>`, and a literal rule missed five
real committees.

### The ceiling you will hit first

**YouTube's RSS feed is hard-capped at 15 items.** Not configurable. So:

- Nightly polling is **mandatory**, not a preference. Boston City TV posts
  about five items a day, so its window is roughly three days. A weekly poll
  loses meetings permanently.
- **Backfill is impossible through RSS.** Historical meetings need either a
  per-body playlist (low volume, high signal — `channel_feed_url` already
  accepts `PL…` ids) or the YouTube Data API.

---

## 5. Deploying a change

```bash
# from the repo root, after your commit
docker build --platform linux/amd64 -f record/Dockerfile \
  -t us-east1-docker.pkg.dev/publicrecord-studio/record/api:NEXT .
docker push us-east1-docker.pkg.dev/publicrecord-studio/record/api:NEXT
gcloud run deploy record-api \
  --image=us-east1-docker.pkg.dev/publicrecord-studio/record/api:NEXT \
  --region=us-east1
```

**`--platform linux/amd64` is not optional on an Apple-silicon Mac.** Without
it you build an arm64 image, Cloud Run refuses it, and the error names the
architecture rather than the flag.

**The jobs run the same image, and every deploy moves all of them.** The
service and the press were moved on each deploy; the poll, the pipeline and
the embed job were found still on `r18`/`r20` on 2026-09-23 — two months of
connector fixes never reached the night. One line per job, every time:

```bash
for j in record-press record-pipeline record-poll record-embed record-migrate record-seed; do
  gcloud run jobs update $j --region=us-east1 \
    --image=us-east1-docker.pkg.dev/publicrecord-studio/record/api:NEXT
done
# record-press also needs its --args bumped to the new --version (below)
```

**When to deploy: outside 03:00–06:00 ET.** The night's jobs run then
(the poll at 03:00, the pipeline at 03:30, the nightly edition at 04:30,
the embed drain at 05:45 — the schedule table further down this section); a job updated while one of
its executions is running finishes that execution on the old image and
starts the next on the new one, and a press moved mid-night can carry an
edition pressed by one version under a service worker key minted by
another. Sessions working in parallel settled on this window on
2026-09-24; say which image tag and press version you are taking before
you build (`ListAgents` / specs/PARALLEL.md).

Six jobs, not four: `record-migrate` and `record-seed` are run by hand, not
by a schedule, and were left on an old image by two deploys running (found
on 2026-09-24 at r45 while everything nightly was on r47) — a hand-run
migration from an image that predates the migration file is a migration
that never happens. The loop above is the whole list; when a job is added,
it is added here.

**Rolling back** is instant and does not require a build:

```bash
gcloud run revisions list --service=record-api --region=us-east1
gcloud run services update-traffic record-api --region=us-east1 \
  --to-revisions=record-api-00001-f7d=100
```

Schema changes go through a numbered file in `record/migrations/` and:

```bash
gcloud run jobs execute record-migrate --region=us-east1 --wait
```

Migrations are applied once, recorded in `schema_migrations`, and each runs
inside a transaction. Running it twice is a no-op — that is asserted by a test,
because a command nobody dares re-run after a partial failure is a command
nobody runs at all.

### Releasing — push and tag at every deployed commit

This repository is the record's home (specs/23 D1), and what is live must be
findable by name. Every deploy bumps the press `--version` (the service
worker's cache key — a code-only change served under the old version reaches
returning readers as cached JS), and once the edition is verified live, the
exact commit the container was built from is tagged and pushed:

```bash
git tag -a v2.1.N <deployed commit> -m "v2.1.N / rNN — <what shipped>"
git push origin main --tags
```

The tag names the image (`rNN`) so a rollback (`gcloud run services
update-traffic`, above) and the source it ran can be matched without a
search. CI (`.github/workflows/ci.yml`) runs the no-Postgres suite on every
push and pull request; the PG-backed half is proven at the desk before a
deploy, not in Actions (no database there, on purpose).

### Nightly intake — the poll, the standing rule, and the caption key

Three things happen at night, and each stands on the one before:

| when (ET) | job | what it does |
|---|---|---|
| 03:00 | `record-poll` | polls every live town's channels; files rule-matched candidates as submissions |
| 03:30 | `record-pipeline` | ingests every `approved` submission — captions via the watch page, then `yt-dlp`, then the community caption service (the highlighter's public transcript engine, which fetches through a residential proxy: from Cloud Run the watch page is walled and only the relay answers — verified 2026-09-23, 7,842 cues in 5.7 s) |
| 04:30 | the nightly-edition workflow | presses from the cloud and carries the edition to the Pages repo — once its three secrets exist (below). Two schedule slots (04:30 and 05:30 ET, one run at a time — GitHub's 04:30 cron did not fire on its first morning, 2026-09-24); a morning with no scheduled run in the log means dispatch it by hand: `gh workflow run "nightly edition"` |
| 05:45 | `record-embed` | drains the meaning-vector backlog — every segment still without a vector, under the spend cap — including what the pipeline's per-meeting budget left behind (below) |

Until 2026-09-23 the middle step never ran: `approved` was only ever written
by a click in the console, and the queue was unattended. Two things change
that, and both are a steward's to switch on:

1. **A standing rule.** In the console's intake screen each source has
   *approve matches automatically — a standing rule*. With it on, the poll
   files a rule-matched candidate at `approved` — **only when YouTube's own
   caption list names a track for it** (auto-generated counts). A candidate
   YouTube lists no track for yet files at `submitted` for a person, and the
   poll asks YouTube again about it on later nights for a week (a live
   stream's auto track arrives hours after it ends). The audit log records
   the approval as `rule:<the source's label>`, and `/app/ai` says a rule may
   gate the record beside the promise it qualifies. A rule never touches what
   a person submits from `/app/add`.
2. **The caption key.** The "YouTube's own list" question is Data API v3
   `captions.list` (50 quota units; 10,000 per day per project), which an
   API key answers — a datacenter address cannot read the watch page's list.
   Without a key a standing rule approves nothing from Cloud Run, and every
   probe note says so. The key is a secret, never an argument:

```bash
printf '%s' 'THE-KEY' | gcloud secrets create youtube-data-api-key \
  --data-file=- --project=publicrecord-studio
gcloud run jobs update record-poll --region=us-east1 \
  --update-secrets=RECORD_YOUTUBE_API_KEY=youtube-data-api-key:latest
```

Restrict the key to the YouTube Data API v3 in the Cloud console. The API
can only *list* captions for a video the account does not own; the fetch at
ingest still goes through the caption routes above. A meeting that arrives
with no words parks in `asr_tasks` — and the nightly drain asks again for a
week (`record/pipeline.py::retry_parked`): a live stream's auto captions
arrive hours after it ends, so a tape that parked on the night it was
posted lands a night or two later on its own.

The pipeline job carries the same secret (`gcloud run jobs update
record-pipeline … --update-secrets=RECORD_YOUTUBE_API_KEY=youtube-data-api-key:latest`):
at ingest it asks `videos.list` for a meeting's exact title, posting day and
length, because the caption relay brings words and nothing else and the
watch page is walled from the cloud. Without the key the feed's title and
the day read from it (`record/pipeline.py::plan_from_submission`) stand in.

**The embedding budget.** A landed meeting spends `RECORD_EMBED_BUDGET_S`
seconds (default 120; `0` = no budget) on its meaning vectors inside the
pipeline and no longer — the clock bounds each request too (sixty seconds)
and the retry ladder stands down past it. The first night with every switch on (2026-09-23)
landed one meeting and sat silent for an hour: the embedding endpoint had
slowed from a batch of a hundred every seven seconds to one every one to
four minutes, a 6,187-segment meeting could not finish inside the job's
hour, and a dozen approved tapes behind it were never reached. The meeting
is on the record before the clock starts; the log says what the budget
left (`⏱ … meaning-search is behind for N segment(s)`), and `record-embed`
drains it nightly at 05:45 ET, after the pipeline's hour and its one retry:

```bash
gcloud scheduler jobs create http record-nightly-embed --location=us-east1 \
  --schedule="45 5 * * *" --time-zone="America/New_York" \
  --uri="https://run.googleapis.com/v2/projects/publicrecord-studio/locations/us-east1/jobs/record-embed:run" \
  --http-method=POST \
  --oauth-service-account-email=907309358085-compute@developer.gserviceaccount.com \
  --attempt-deadline=1800s
```

**The pace is the database's, not the API's** (measured 2026-09-24: the
embedding call for 100 texts takes 1 s; the 100 row updates behind it take
341 s on `db-f1-micro`, because the HNSW index on `emb_neural` cannot sit
in its memory — `specs/next-session-prompt.md` has the numbers and the
options, and a larger instance is a spend decision). Two embedders running
at once (a pipeline and a backfill, or two pipelines) share the same slow
writes and both crawl — the 05:45 slot is after the pipeline's worst case
on purpose. The pace is readable in the `spend` ledger (one row per batch,
`added_at` apart).

A job killed by its timeout mid-ingest leaves its submission at `queued`
and its meeting shell at `transcribing` or `analyzing`. Cloud Run retries
the task once, at once — too soon for that row to look abandoned — so the
retry lands the rest of the queue and the *next night's* drain reclaims the
submission (`reclaim_stale`)
and the dedupe no longer counts a shell untouched for an hour as on the
record (`memory.ingest.stale_in_flight`, a bound only the pipeline passes —
the desk's on-device jobs run for hours), so the tape is asked for again
rather than stranded; the retry stage picks up a stale shell of the last
week the same way. The hour is `memory.ingest.STALE_IN_FLIGHT_S`, and it is
the job's own `--task-timeout=3600` (INFRA §8): raise one, raise both.

**The model lane on the hosted pipeline.** `czcore.llm` reads
`GEMINI_API_KEY`; the pipeline carries `RECORD_GEMINI_KEY` and bridges it
once at start (`bridge_model_key`), so the hosted summary and the reading's
draft are the labeled Gemini paragraphs `/app/ai` names. Until 2026-09-23
they were extractive on the hosted lane. To repair meetings that landed
nameless or unread, run the recipe in `specs/next-session-prompt.md`
("Repairing a meeting") as a one-off pipeline execution with overridden
args — never from a Mac.

### The steward desk — the night, readable without a terminal (specs/27)

`/steward` opens on **Tonight**: what is running, its own log lines, the
record counted, the chain step by step with its last executions, and a
*Run now* on poll, pipeline and embed (audited as `run-job`, signed by the
steward). The desk
reads Cloud Run and Cloud Logging with the service's own identity
(`roles/editor` on the default compute account covers `run.executions.list`,
`logging.entries.list` and `run.jobs.run`), and it needs to be told where
the jobs live — two names on the service, nothing else:

```bash
gcloud run services update record-api --region=us-east1 \
  --update-env-vars=RECORD_CLOUD_PROJECT=publicrecord-studio,RECORD_CLOUD_REGION=us-east1
```

Absent, the Tonight screen says so in a sentence and every other screen
still works. The press is not run from the desk — the nightly-edition
workflow owns it (it presses and carries in one breath). While Tonight is
open it re-reads the jobs every twenty seconds and the counted record only
on open and Reload; the log route reads `entries.list` with the service's
identity. Migration `002_neural_todo.sql` (a partial index on the segments
still without a vector) is what keeps those counts cheap — run
`record-migrate` with this deploy. The municipality bar scopes every screen; **Settings** shows
the windows, the lanes, the schedule and the edition readers have, each
with where it is set — nothing on that screen is written from the browser.

### The nightly edition — automated, once two credentials exist

The freeze diagnosis (specs/23 D2, 2026-09-23) found the missing step: the
poll files submissions nightly and the pipeline ingests what a steward
approved, but nothing pressed the edition or carried it to the Pages repo
without a hand — so `edition_date` could not move on its own.
`.github/workflows/nightly-edition.yml` (in the record's own repository)
presses from the cloud at 04:30 ET, after the ingest, syncs the bucket into
`amateurmenace/publicrecord`'s `app/`, decompresses in place, and pushes
only when the edition changed. It stands down, saying so in its log, until
three repository secrets exist on `amateurmenace/publicrecord-studio`:

| Secret | What it is |
|---|---|
| `GCP_WORKLOAD_IDENTITY_PROVIDER` | the full resource name of a Workload Identity Federation provider trusting this repository (`projects/907309358085/locations/global/workloadIdentityPools/<pool>/providers/<provider>`) — no key file ever leaves GCP |
| `GCP_PRESS_SERVICE_ACCOUNT` | a service account with `roles/run.developer` on `record-press` (to execute it), `roles/iam.serviceAccountUser` on the job's runtime account, and `roles/storage.objectViewer` on `publicrecord-edition` |
| `PAGES_TOKEN` | a fine-grained personal access token scoped to the `amateurmenace/publicrecord` repository with *Contents: read and write* — the one thing that can push an edition |

Provisioning these is a spend-free but identity-bearing act, so it is
Stephen's; until then the manual two-step below still works, and the
workflow's "standing down" line in the Actions log is the honest state.

### Refreshing what publicrecord.studio serves

The reader at publicrecord.studio is a **static edition on GitHub Pages** (repo
`amateurmenace/publicrecord`), separate from the live API. New meetings reach
the API and the console immediately; the reader shows them only after the
edition is re-pressed and re-deployed. Two steps, both safe to re-run:

```bash
# 1. press from the cloud (never from a Mac — a thin corpus would shrink it)
gcloud run jobs execute record-press --region=us-east1 --wait
#    → writes gs://publicrecord-edition/app, with RECORD_API_BASE baked in

# 2. sync that edition into the Pages repo and push
gh repo clone amateurmenace/publicrecord /tmp/pr -- --depth 1 && cd /tmp/pr
gcloud storage rsync -r --delete-unmatched-destination-objects \
  gs://publicrecord-edition/app app
# the bucket stores text objects gzipped (Content-Encoding: gzip, for the CDN
# path); this gcloud version's rsync downloads them RAW, so decompress in place
# before pushing — Pages serves the bytes as-is and gzips on the wire itself,
# so gzip bytes in the repo would reach the browser as garbage:
python3 - <<'PY'
import gzip, pathlib
for p in pathlib.Path("app").rglob("*"):
    if p.is_file():
        b = p.read_bytes()
        if b[:2] == b"\x1f\x8b":            # gzip magic → the real text is inside
            p.write_bytes(gzip.decompress(b))
PY
git add -A && git commit -m "Deploy: <what changed>" && git push
```

`--delete-unmatched-destination-objects` deletes what the press dropped, so a
steward's `forget` propagates (older gcloud spelled this `-d`). The decompress
step is not optional on this toolchain: without it every `.html`/`.css`/`.js`
over 1 KB lands as gzip bytes and the live site serves binary. The repo keeps
`CNAME`, `.nojekyll` and the root `index.html` redirect at its top level — the
rsync only touches `app/`, so those survive.
**Before pushing, if the edition dropped a page that is cited on
`control-z.org/app`** (a steward deleted an issue — see §9 item 1), decide
whether that page needs a tombstone rather than a 404; the two editions are
allowed to differ, but a dead citation is the one thing the covenant does not
allow quietly.

---

### Repairing a model's cut answers (v2.1.23)

Until v2.1.23 the Gemini lane's thinking spent the whole output budget, and
every hosted summary and drafted reading was pressed cut off mid-sentence.
The seam now caps the thought (`thinkingLevel: low` on the 3.x family),
gives it room on top of the answer, and refuses any answer that did not end
the way a whole answer ends — so no new fragment can land. The fragments
already stored stay until they are asked again. `record/repair.py` does
that, in the pipeline job's own image and secrets (never from a Mac), once
the image with the fixed seam is on the job. `--before` is the moment the
last old-image writer stopped: the fixed image's deploy, or — if a
`record-pipeline` execution that started on the old image was still running
then (the nightly runs up to an hour, and retries once) — the moment it
finished, since it keeps writing fragments stamped after the deploy.
Everything a Gemini lane wrote before `--before` is asked again (a fragment
that ends on a bracketed receipt looks whole), and a row repaired since is
newer than the cutoff, so a re-run is safe. Run it outside 03:00–06:30 ET:
the nightly poll, ingest and embed share the model's quota and the database.

```bash
# no execution still on the old image? (list them; for one that started before
# the deploy, its end is status.completionTime — the list shows only creation)
gcloud run jobs executions list --job=record-pipeline --region=us-east1 --limit=3
gcloud run jobs executions describe EXECUTION --region=us-east1 --format='value(status.completionTime)'
B=2026-09-24T03:00Z     # the later of the deploy and that execution's end
# look first — the plan, nothing changed
gcloud run jobs execute record-pipeline --region=us-east1 --wait \
  --args=-m,record.repair,--before,$B,--dry-run
# one meeting asked for real and printed, nothing written — read it
gcloud run jobs execute record-pipeline --region=us-east1 --wait \
  --args=-m,record.repair,--before,$B,--probe
# the repair
gcloud run jobs execute record-pipeline --region=us-east1 --wait \
  --args=-m,record.repair,--before,$B
gcloud logging read 'resource.type="cloud_run_job" AND resource.labels.job_name="record-pipeline"' \
  --limit=160 --freshness=1h --format='value(textPayload)' | grep -E 'REPAIR|PLAN|UPDATED|SUMMARY|DRAFT|BACKUP'
```

Then press and carry the edition (below) — only once the last attempt's
final line reads `REPAIR DONE — … 0 could not be asked`. The repair runs as a
`record-pipeline` execution, so it inherits that job's hour and its one
automatic retry: a run that exits 1 is run again at once (harmless — what was
written is newer than the cutoff, what failed is asked again), and a run
killed at the hour prints no final line at all; either way, read the last
attempt, re-run, or narrow it with `--limit` / `--only`. What is written: a
whole answer, always. A fallback only when the model answered both asks and
the seam refused both as fragments — the summary becomes the extractive one,
labeled so, and a draft is removed rather than pressed as a fragment. **A call
that failed** (a quota, a bad key, a request the API refused, a timeout, a
prompt the model declined) **changes nothing**: a meeting is written whole or
not at all (`HELD`), two such meetings in a row stop the run
(`REPAIR STOPPED`), and the job exits 1. A prompt the model declines every
time keeps its meeting's fragment until a person decides (`--only` the others
past it). Each row's old values are printed as a `BACKUP {json}` line before
it is written, so a run that went wrong can be put back from its own log.
Each call's line prints the tokens it spent (the thought included) and the
seam's reason, in parentheses, when it fell back. One repair runs at a time
(an advisory lock, taken before the rows are read). Read the `--probe` lines
before the real run: each call it made (one or two, by what the first
planned meeting needs) must say `ai:gemini-…` and `— whole`.

### The pictures the press presses (specs/29 §P0.2)

The broadsheet reads a meeting around its tape — the poster large, three
frames from inside the night, every tape of the year as its own still — and
the covenant says the reader page loads nothing from a third party. So the
press fetches each tape's `hqdefault.jpg` and `hq1–3.jpg` from
`i.ytimg.com` ONCE and presses them into the edition at `app/stills/<pid>.jpg`
and `<pid>-1..3.jpg` (`record/stills.py`). The cache lives outside the
edition directory (`RECORD_STILLS_DIR`, default `/tmp/record-stills` — the
press wipes the edition directory on every run), and because a Cloud Run
job's disk is new every night, `record.press` seeds that cache from the
edition bucket's `app/stills/` before it fetches: YouTube is asked only for
the tapes that landed since the last pressing. A frame YouTube does not have
comes back as a ~1 KB grey card with a 200; anything under 2.5 KB, or not a
JPEG, is not a still and is not pressed — the page shows the town's colour
instead. `--no-stills` presses none. A desk bake (`web.bake`) presses none
unless `--stills` is given, so a test bake never touches the network; the
edition stays byte-identical either way.

The stills ride the normal sync (JPEG is never gzipped; `.jpg` is in
`_TYPES`) and the nightly carry (the gunzip loop skips them by magic). The
service worker caches them like any other `/app/` plane. The sync's delete
pass keeps a still whose meeting is still on the edition even when tonight's
press did not re-press it (a walled picture host must not empty the cache);
a taken-down meeting's stills are removed with its pages. A still that
failed to fetch is retried when the record next moves (`--force` presses
now); the fetch pass stops early after twelve straight non-answers or three
minutes and says so in the job's log.

### Hand-files at the Pages-repo root

(The press's own output inside `app/` grew in v2.1.23 — `app/pictures/*.svg`,
one file per picture, and `app/glossary/` — and the rsync carries them like
every other pressed file.)

The rsync manages only `app/`; three files live at the repo root by hand and
survive every edition: `CNAME`, the root `index.html`, and
`constitution/index.html` — the shareable spelling
**publicrecord.studio/constitution**, a meta-refresh to `/app/ai/` (its
pressed twin `/app/constitution` redirects the same way; `/app/ai` is
canonical). If a fourth hand-file ever appears, list it here or the next
cleanup will delete it confidently.

### The shared-paper store (specs/21 §6.2)

One-time provisioning, done alongside the r29 deploy. A private bucket the
API writes once and serves read-only; papers land at `p/<id>.json` where the
id is the SHA-256 of the paper's own canonical bytes (record/papers.py — the
canonical form and the abuse posture live there):

```bash
gcloud storage buckets create gs://publicrecord-papers \
  --location=us-east1 --uniform-bucket-level-access \
  --project=publicrecord-studio
# the API's runtime service account needs object read/create on it
gcloud storage buckets add-iam-policy-binding gs://publicrecord-papers \
  --member="serviceAccount:$(gcloud run services describe record-api \
    --region=us-east1 --format='value(spec.template.spec.serviceAccountName)')" \
  --role=roles/storage.objectAdmin
gcloud run services update record-api --region=us-east1 \
  --update-env-vars RECORD_PAPERS_BUCKET=publicrecord-papers
```

Unset `RECORD_PAPERS_BUCKET` and the endpoints answer 503 with the covenant
line — readers fall back to full links and `paper.json` files, losing only
the shortness. The bucket is not the edition bucket on purpose: the edition
is the record's own pressing; the papers are readers' documents, and the two
must never sync, sweep, or bill as one thing.

### The front pages the press lists (specs/29 P2)

The press lists readers' shared pages beside the record's own on `/app/`
and `/app/front-pages/`: every object under `p/` in the share bucket
(`RECORD_PAPERS_BUCKET` — the same content-addressed store the reader's
*short link* writes to) becomes a card: its title, what it is made of, its
first still, the day it was shared. Nobody is named; the store holds no
author to name. A store that cannot be listed costs the readers' cards for
that pressing and nothing else (the log says so: `front pages: the share
store could not be listed`); a press job without the variable says
`front pages: no share store configured`. **The job needs the variable the
service has** (and it runs the same service account, which already reads
and writes the bucket):

```bash
gcloud run jobs update record-press --region=us-east1 \
  --update-env-vars=RECORD_PAPERS_BUCKET=publicrecord-papers
```

Three brakes, none a new stored field: only pages minted on or after
2026-09-24 are listed (the day the button began to say it lists the page —
`web/gallery.py::LISTED_SINCE`; Stephen may move it); at most twelve pages
from any one day (a flood buries a day, not the store); and the front page's
strip seats a reader's page only once it is a day old, so the gallery — and
the press log, which prints the newest five titles each night — comes
first. The store moving is a reason to press: its listing is folded into
the pressing's fingerprint, so a night with no new meeting and one new
shared page still presses, and the service worker's key carries a digest of
the listed set, so returning readers get the new list.

**Taking a page down is the steward's act, and it is one move:**

```bash
gsutil mv gs://$RECORD_PAPERS_BUCKET/p/<id>.json gs://$RECORD_PAPERS_BUCKET/taken/<id>.json
```

Then press, so the card leaves the live pages today rather than at the
next scheduled run: `gh workflow run "nightly edition"` (returning readers
get the new pages when the worker's key changes, which the press makes it
do). The page's short link answers with the reader's existing sentence — *no
paper answers at this address … or the paper was taken down* — and the
store refuses the same bytes again (`put_new` looks under `taken/` first, and
the share answers 410 with the read path's own sentence — no link that 404s),
so a re-share cannot undo the move. The record keeps the bytes under
`taken/` for its own account and serves them to no one; the words a reader
sees are the ones already pressed, and changing them — like a reader-facing
takedown request — is Stephen's call, not a steward's.

## 6. When something is broken

### The API returns 503 and says the corpus is unreachable

```bash
gcloud sql instances describe record-pg --format="value(state)"
```

`RUNNABLE` means the database is fine and the problem is the connector or the
secret. Anything else — start it:

```bash
gcloud sql instances patch record-pg --activation-policy=ALWAYS
```

### Cold starts feel slow

`--min-instances=0` means an idle service costs nothing and the first request
after a quiet spell pays for the start. That trade is deliberate. If it becomes
annoying, `--min-instances=1` removes it and adds roughly $5–10/mo.

### Read the actual error

```bash
gcloud run services logs read record-api --region=us-east1 --limit=50
gcloud logging read 'resource.labels.job_name="record-press"' \
  --limit=20 --format="value(textPayload)" --freshness=1h
```

Failures in this codebase are sentences, not codes. If a log line does not read
like an English explanation, it came from a library rather than from us.

### A poll files nothing

Almost always the rules, not the connector. Run a **preview** — it shows
whether titles are landing in `excluded` (a rule is too broad) or `unmatched`
(no rule names that body). A poll that files zero and reports zero unmatched
means the feed itself returned nothing; check the channel id.

### A shared paper needs to come down

There is deliberately no delete API — takedown is a steward's hand, not an
endpoint someone can find. The free text a stored paper can carry is its
title and its notes — both length-capped plain text, rendered inert
(everything else is refs into the record), so this should be rare:

```bash
gcloud storage rm gs://publicrecord-papers/p/<id>.json
```

The short link then answers an honest 404 ("no paper at this address").
Whoever held the paper still holds it — their draft, full link and
paper.json are theirs, and the record itself never changed.

### The edition looks stale

`GET /api/freshness` returns the corpus fingerprint. If it differs from the one
in the served edition's `manifest.json`, a press is owed. Note the **edition
date is the newest meeting, not the press time** — that is deliberate, so the
bake stays byte-identical for identical input. A re-press with no new meetings
correctly shows an unchanged date.

---

## 7. The money

| Line | Est./mo | Notes |
|---|---|---|
| Cloud SQL `record-pg` | $10–30 | **the only line that bills while idle** |
| Cloud Run `record-api` | $0–5 | min-instances 0; idle costs nothing |
| Cloud Run jobs | ~$0 | seconds per run |
| GCS + egress | $1–5 | |
| GCS `publicrecord-papers` | ~$0 | shared papers are ~2 KB each; pennies at thousands |
| Gemini embeddings | <$1 one-time, then pennies | see below |
| Artifact Registry | <$1 | |
| **Project budget alert** | **$100** | 50 / 90 / 100%, this project only |

### The Gemini key, and where it actually lives

**It is not in AI Studio, and it will not appear there.** AI Studio's key page
is a filtered view of keys created through its own flow, for projects it has
synced; this key was created with `gcloud` in a project AI Studio has not
picked up. Same underlying resource, different front door. The authoritative
view is the Cloud console:

<https://console.cloud.google.com/apis/credentials?project=publicrecord-studio>

It is listed as **`publicrecord gemini`**, and it is **restricted to
`generativelanguage.googleapis.com` only** — if it leaked it could call
nothing else. The value lives in Secret Manager as `record-gemini-key` and has
never been printed to a terminal or a chat.

To rotate it:

```bash
gcloud services api-keys create --display-name="publicrecord gemini 2" \
  --api-target=service=generativelanguage.googleapis.com \
  --project=publicrecord-studio
# then write the new string into a new secret version, redeploy, and delete the old key
```

### Two ceilings, and they are different things

**The GCP budget ($100)** alerts. It does not stop anything. It watches every
service in this project and emails at 50%, 90% and 100%.

**The embedding cap (`RECORD_SPEND_CAP_USD`, default $100)** stops. It is
checked at the top of every backfill batch — before a row is read, let alone
bought — and measured against the `spend` ledger rather than a counter held in
memory, so it survives a restart, a second job, and a job somebody ran last
week.

The arithmetic it uses is pinned and checkable:

| | |
|---|---|
| rate | **$0.15 per 1M input tokens**, `gemini-embedding-001` paid tier, verified against ai.google.dev on 2026-07-19 |
| assumption | 60 tokens per civic segment (deliberately generous — an estimate that undercounts is a cap that does not hold) |
| **the whole imported record** | 72,816 segments ≈ **$0.66** |
| the cap is reached at | ~11.1 million segments |

So the cap is a runaway brake, not a budget: the real backfill costs less than
a coffee, and $100 is roughly a hundred and fifty times it. If the estimate and
the invoice ever disagree, the ledger is the arbiter —
`/api/steward/spend` shows units actually bought, and the conversion above is
only an estimate over them. A drifting price shows up as that divergence.

Lower it for a run:

```bash
gcloud run jobs update record-embed --region=us-east1 \
  --update-env-vars=RECORD_SPEND_CAP_USD=5
```

**Turning it all off** — and it is worth knowing this is safe:

```bash
gcloud sql instances patch record-pg --activation-policy=NEVER
```

The reader keeps working. The record is static; stopping the database stops
meaning-search and intake, not reading. To stop everything:
`gcloud projects delete publicrecord-studio`. The record itself is not in
there — it is in `corpus.db` on the desk and in every pressed edition anyone
has downloaded, which is what the anti-lock-in promise was for.

## 8. Testing a release on a machine that is not yours

This section is about the **desktop app**, not the record, and it is here
because it is the gate people skip and the one that decides whether a stranger
can open what you built.

### Why your own Mac cannot answer the question

The machine that signs an app is the worst possible place to test it, and not
by a little. Ask it and it will say `accepted`, `source=Notarized Developer ID`
— and mean almost nothing by it, for three separate reasons:

1. **Your keychain vouches for the certificate.** `spctl` can accept a
   signature because this machine already trusts the signing identity, not
   because Apple's notarization is carrying it. A stranger's Mac has no such
   shortcut.
2. **Homebrew exists here.** Anything in the bundle that reaches for
   `/opt/homebrew/lib/…` resolves fine on a developer's machine and crashes on
   launch for someone who has never installed it. `build_suite.sh` gates the
   venv against this, but a runtime path can still slip past a build-time check.
3. **Nothing is quarantined.** Gatekeeper only runs its strict path on files
   carrying `com.apple.quarantine`, and a file that never arrived from anywhere
   never got the flag. A pass on an unquarantined DMG is a pass on a check that
   barely ran.

specs/09 §7 has always required this gate. What is easy to forget is *why the
verdict does not transfer between releases*: it is a judgement about a signing
identity, and 2.0.0 changed the bundle identifier from `org.control-z.suite` to
`org.civicmedia.studio`. Apple had never seen that identity. Every future
identity change resets this the same way.

### The machine

Any Mac that has never had Xcode, Homebrew, or a developer certificate. A
friend's laptop, a family machine, a library Mac, a clean VM. Apple silicon —
the DMG is arm64-only.

### Getting the file there

**AirDrop it or download it. Do not use a USB drive.** AirDrop and browser
downloads set the quarantine flag; a thumb drive does not, and the result is a
test that passes because Gatekeeper was never asked.

### On the loaner

```bash
cd ~/Downloads
shasum -a 256 civicmedia-studio-*.dmg          # matches what was handed over?

# THE CHECK THAT DECIDES WHETHER THE REST MEANS ANYTHING
xattr -l civicmedia-studio-*.dmg | grep quarantine
```

If that prints nothing the test is void. Add the flag by hand rather than
abandoning the run:

```bash
xattr -w com.apple.quarantine "0081;00000000;Safari;" civicmedia-studio-*.dmg
```

Then:

```bash
spctl -a -vvv -t open --context context:primary-signature civicmedia-studio-*.dmg
hdiutil attach civicmedia-studio-*.dmg
spctl -a -vvv "/Volumes/Civic Media Studio/Civic Media Studio.app"
```

**A pass is exactly three lines:**

```
…/Civic Media Studio.app: accepted
source=Notarized Developer ID
origin=Developer ID Application: Stephen Walter (6M536MV7GT)
```

`rejected` or `source=Unnotarized` is a signing problem, not a user problem.
Send the whole output and stop.

### The part `spctl` cannot tell you

Drag it to Applications and **double-click it like a person would.**

- No dialog, or at most one *"downloaded from the Internet, are you sure?"* —
  that one is normal.
- It must **not** need right-click → Open.
- It must **not** say *unidentified developer*, *cannot be opened*, or
  *damaged and should be moved to the Trash*.

Then open two tools that do real work — Scribe and Memory — and confirm neither
crashes. `spctl` validates a signature; it does not notice a dylib that is not
there. This step is where reason 2 above actually surfaces.

### What to write down

The three `spctl` lines verbatim; whether quarantine was already present or you
added it; what happened on double-click; and which tools you opened. That is a
release record, and it is worth keeping beside the release notes — the next
identity change will want to compare against it.

---

## 9. What is not done yet

Honest list. Most of §9 closed on 2026-07-19 (specs/19 R1). What remains is
named plainly, and one line is a finding, not a task.

1. ~~The corpus is empty~~ — **landed and whole; then a steward curated it.**
   The record holds 12 meetings and ~81k segments: the desk's 10 arrived through
   the Cloud SQL proxy (with all 216 issues — the import *did* arrive whole), and
   two more came through **hosted ingest** — Boston City Council July 8, and a
   Brookline Select Board meeting **you approved yourself through the console**
   mid-session (audited, `swalter4669@gmail.com`). The corpus now shows 215
   active issues, not because the import dropped one but because you `forget`-ed
   `issue_brookline_callahan-town-council` in the console — a steward deletion,
   with your name and the time on it. The console works end to end; this is the
   proof.
   - **One consequence to know.** `control-z.org/app` still serves the frozen
     desk edition (1.9.0), which was pressed *before* that deletion, so it still
     carries `/app/i/…callahan-town-council`. A fresh cloud press correctly does
     not — so deploying the cloud edition over control-z.org would 404 that one
     page. That is the tension between steward curation (a real editorial delete)
     and the citation-survival rail, and **R1.7 needs a tombstone for a deleted
     issue, not a bare 404** — a page that says *this issue was removed by a
     steward on <date>*, so a citation resolves to an explanation rather than a
     dead end. Until then the cloud edition is not deployed over control-z.org.
2. ~~`publicrecord.studio` has no site behind it yet~~ — **live** (2026-07-19).
   Not by the specs/18 site-move (which needs `control-z-tools` made public —
   still Stephen's call), but by a second, independent GitHub Pages site: the
   public repo `amateurmenace/publicrecord` carries the cloud-pressed live-first
   edition with its own CNAME, so `control-z.org` never had to move and never
   went dark. Both domains were verified serving before and after, in a browser.
   The root redirects to `/app/`; the reader calls the API and degrades to its
   own index when the API is down. **The full specs/18 reorganisation
   (control-z.org → the tools repo, `/app` retired from it) is still R1.8 and
   still Stephen's** — this was the fast, reversible path to a working address,
   not that reorganisation. How to refresh it is in §5.
3. ~~No Gemini key~~ — **done, and used.** `neural.available: true`, the whole
   record embedded under the cap; `/api/steward/spend` shows the cost.
4. ~~The steward console is configured-off~~ — **done.** Google sign-in against
   a server-side allowlist of one; 401 without a token, 403 off the list.
5. ~~The nightly scheduler is not created~~ — **done.** `record-nightly-poll`
   at 03:00 and `record-nightly-ingest` at 03:30 America/New_York, verified to
   trigger their jobs. The ingest job reads `approved` and nothing else, so a
   scheduled ingest is not a covenant hole.
6. ~~The intake connector has never ingested a meeting end to end~~ — **done.**
   One meeting walked all the way through and read before any backlog. Three
   bugs it surfaced are fixed and pinned (see the CHANGELOG). The queue holds
   ~20 approved-or-waiting Boston/Brookline submissions a steward can now work.
7. **The repo split has not run** (specs/19 R1.8). Pre-authorized but deferred:
   it rewrites history, renames both repos, re-points both Macs, and its proof
   step diffs a fresh DMG against the notarized 2.0.0 — which needs Stephen's
   signing machine. It is also entangled with R1.7 (item 2). One risky thing at
   a time; this is Stephen's to run from specs/18 §5 with a human at each step.

---

## 10. Importing the full corpus

From the Mac that holds it — not this one, which has a thinner copy:

```bash
gcloud components install cloud-sql-proxy   # once
cloud-sql-proxy publicrecord-studio:us-east1:record-pg --port 55432 &

# the password is in Secret Manager, not in this file
RECORD_DSN="postgresql://record:$(gcloud secrets versions access latest \
  --secret=record-dsn --project=publicrecord-studio | sed 's/.*record://;s/@.*//')\
@localhost:55432/record" \
  .venv/bin/python -m record.import_desk \
  --corpus ~/Movies/control-z/memory/corpus.db --sample 500
```

It verifies itself: every table counted, a sample of vectors re-read
bit-for-bit against the source blobs, and the issue rollups diffed between
SQLite and Postgres. **It must end with "the record arrived whole."** If it
does not, that output is the finding — send it rather than working around it.

It opens the source corpus **read-only** and cannot write to it.

---

## 11. The rules that are not negotiable

These are covenant, not configuration. If a change would break one, the change
is wrong.

- **Readers never log in, are never counted, never tracked.** No cookie, no
  session, no analytics. The public endpoints take no identity and there is a
  test asserting they set no `Set-Cookie`.
- **Accounts exist for stewards only.**
- **The record stays readable with the backend dead.** Every feature that
  cannot degrade to the static edition is a feature that needs rethinking.
- **Nothing ingests without a human.** Submissions queue; stewards approve.
- **Everything degrades out loud.** A missing capability is stated in the
  response and shown to the reader. Silence is the failure mode we design
  against.
- **Officials-only aggregation.** Enforced at press time. Private citizens are
  findable within a meeting, never aggregated into a person page.
- **Corrections annotate; they never rewrite.** The record remembers its own
  edits, and now remembers who made them.
