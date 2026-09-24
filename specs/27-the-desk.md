# 27 — The steward's desk

**Status: BUILT (2026-09-24), in review.** The console at `/steward` grew
from four screens (intake, queue, issues, ledgers) into a desk: the night
as it stands, every screen scoped to one municipality, a log a steward can
read without a terminal, and the settings the night runs on — read from
the running service, set where each note says.

## Why

On 2026-09-23 the first night with every switch on landed one meeting and
then sat silent for an hour, and the only way to learn that was a laptop
reading Cloud Run's log. The console could approve a tape and could not say
whether the pipeline had ever picked it up. A steward's questions — *did
last night run? what is running now? what did it say? what is waiting, and
where?* — had no screen.

## What

1. **Tonight.** What is running right now, with its own log lines
   refreshing every twenty seconds while the screen is open; the record
   counted in tiles (live, waiting, approved-not-ingested, parked,
   mid-flight, segments meaning-search cannot see, the edition readers
   have, spend against the cap); the chain step by step — poll, pipeline,
   edition, embed — each with its schedule and its last five executions, and
   a *Run now* on poll, pipeline and embed that says it spends what a night
   spends (the edition is GitHub's; the press is not run from here); and each municipality
   counted on its own card with doors into its queue, meetings and rules.
2. **The municipality bar.** Every screen reads it. *Every town* is the
   whole record; a town is its intake, its queue, its meetings, its issues,
   its log, and nothing from another town while it is chosen.
3. **Meetings.** The record itself, newest day first, every state, with how
   much of each meeting meaning-search can see; a live meeting links to its
   page in the pressed edition.
4. **Log.** The audit log filterable by verb and by name (a standing rule
   signs `rule:<source>`; a job run from the desk signs with the steward),
   and the last lines any execution printed, by its own name.
5. **Settings.** The windows (`RECORD_EMBED_BUDGET_S`, the retry and
   re-probe weeks, the stale bound, the spend cap), the lanes (embeddings,
   the model, the caption key, the caption routes), where the jobs live,
   the schedule, the edition, the stewards — each with the note that says
   where it is set. Nothing here is written from the browser: a switch a
   steward flips lives on the Intake screen, per source.
6. **A way back.** *Open the record ↗* in the header, to `/app/`.

## How

- `record/ops.py` reads Cloud Run executions and Cloud Logging tails with
  the service's own identity, behind one seam (`_call(fetch=…)`) the tests
  exercise with recorded answers. `RECORD_CLOUD_PROJECT` and
  `RECORD_CLOUD_REGION` say where the jobs live; absent, the desk says so.
- Routes: `GET /api/steward/overview`, `GET /api/steward/meetings?town=`,
  `GET /api/steward/jobs`, `GET /api/steward/jobs/{job}/executions/{name}/log`,
  `POST /api/steward/jobs/{job}/run` (audited as `run-job`); `submissions`
  gains `town` and `status=all`; `audit` gains `town`, `verb`, `steward`.
- The console builds DOM with `h()` and text nodes only; the page's CSP is
  unchanged (`connect-src 'self'` and Google's sign-in); the edition's
  manifest is fetched server-side from the readers' side of the fence.

## Not in this

Writing settings from the browser (a steward flips switches per source; the
windows are the operator's, set on the jobs); the GitHub workflow's log
(it lives in the repo's Actions tab, and the desk says so); alerts.
