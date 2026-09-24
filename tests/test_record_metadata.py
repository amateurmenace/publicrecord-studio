"""The hosted ingest's own knowledge of a meeting, and the model lane it can
reach (specs/24 §4; the 2026-09-23 live catches).

Four meetings landed on the record as their video id, undated: the caption
relay brings words but no title, and a datacenter address is served the
watch page without its details. The poll had known the title all along — it
is the first thing in every submission's note — and YouTube's own `videos.list`
answers a key with the exact title, the posting day and the tape's length.
And the hosted pipeline's summaries had been extractive while the
constitution named Gemini: czcore.llm reads GEMINI_API_KEY and the pipeline
only carried RECORD_GEMINI_KEY.
"""

import json
import os
import subprocess
import tempfile
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


class PlanFromSubmissionTest(unittest.TestCase):
    def test_the_feed_title_and_the_meetings_own_day(self):
        from record.pipeline import plan_from_submission
        sub = {"note": "City Services on September 21, 2026 · published 2026-09-21T15:59:42+00:00 "
                       "· captions were not checked — the watch page named neither captions nor video "
                       "details · found by the nightly poll of UCvM_2-HUTqwKkcQvLVRcMJw", "date": ""}
        p = plan_from_submission(sub)
        self.assertEqual(p["title"], "City Services on September 21, 2026")
        self.assertEqual(p["date"], "2026-09-21")
        self.assertEqual(p["published"], "2026-09-21")

    def test_a_title_without_a_day_falls_to_the_posting_day(self):
        from record.pipeline import plan_from_submission
        p = plan_from_submission({"note": "Boston Zoning Board of Appeal Subcommittee Hearing · "
                                          "published 2026-09-18T13:02:00+00:00 · found by the nightly poll of UCx"})
        self.assertEqual(p["title"], "Boston Zoning Board of Appeal Subcommittee Hearing")
        self.assertEqual(p["date"], "2026-09-18")

    def test_a_stewards_date_wins_and_untitled_stays_empty(self):
        from record.pipeline import plan_from_submission
        p = plan_from_submission({"note": "(untitled) · published 2026-09-18T13:02:00+00:00", "date": "2026-09-10"})
        self.assertEqual(p["title"], "")
        self.assertEqual(p["date"], "2026-09-10")
        self.assertEqual(plan_from_submission({}), {"title": "", "date": "", "published": ""})


class ModelKeyBridgeTest(unittest.TestCase):
    def test_the_hosted_key_reaches_the_model_seam_once(self):
        from record.pipeline import bridge_model_key
        env = {}
        self.assertTrue(bridge_model_key(env, "g-key"))
        self.assertEqual(env, {"GEMINI_API_KEY": "g-key"})

    def test_a_configured_lane_is_never_overwritten(self):
        from record.pipeline import bridge_model_key
        for k in ("GEMINI_API_KEY", "GOOGLE_API_KEY", "ANTHROPIC_API_KEY", "OPENAI_API_KEY"):
            env = {k: "mine"}
            self.assertFalse(bridge_model_key(env, "g-key"))
            self.assertEqual(env, {k: "mine"})
        env = {}
        self.assertFalse(bridge_model_key(env, ""))
        self.assertEqual(env, {})


class VideoMetaTest(unittest.TestCase):
    def meta(self, body=None, error=None):
        from record.connectors import youtube

        def fetch(url, **kw):
            self.assertIn("googleapis.com/youtube/v3/videos", url)
            self.assertIn("key=k", url)
            if error:
                raise error
            return body

        with mock.patch.object(youtube, "_fetch", fetch):
            return youtube.video_meta("2YhgO14jXys", "k")

    def test_youtubes_own_details(self):
        out = self.meta(json.dumps({"items": [{"snippet": {"title": "Brookline School Committee Meeting - June 18, 2026",
                                                               "publishedAt": "2026-06-19T02:11:00Z",
                                                               "channelTitle": "Brookline Interactive Group"},
                                                   "contentDetails": {"duration": "PT5H4M35S"}}]}))
        self.assertEqual(out, {"title": "Brookline School Committee Meeting - June 18, 2026",
                               "published": "2026-06-19T02:11:00Z",
                               "uploader": "Brookline Interactive Group", "duration": 18275.0})

    def test_a_refusal_or_nonsense_is_an_empty_answer(self):
        from record.connectors import youtube
        self.assertEqual(self.meta(error=RuntimeError("YouTube's video details answered HTTP 403 (Forbidden)")), {})
        self.assertEqual(self.meta(error=youtube.Throttled("https://x/?key=SECRET", 429, None, 4)), {})
        for body in ("not json", '{"items": []}', "[]", '{"items": [1]}'):
            self.assertEqual(self.meta(body), {}, body)

    def test_iso_durations(self):
        from record.connectors.youtube import iso_seconds
        self.assertEqual(iso_seconds("PT5H4M35S"), 18275.0)
        self.assertEqual(iso_seconds("PT45M"), 2700.0)
        self.assertEqual(iso_seconds("P1DT1S"), 86401.0)
        self.assertEqual(iso_seconds("nonsense"), 0.0)
        self.assertEqual(iso_seconds(None), 0.0)


class DraftTest(unittest.TestCase):
    SEGS = [{"start": 10.0, "end": 14.0, "text": "we discuss the override at length"},
            {"start": 20.0, "end": 24.0, "text": "the motion carries"}]

    def test_no_key_no_draft_and_no_fallback(self):
        from memory import analyze
        with mock.patch.object(analyze.llm, "enabled", lambda: False):
            self.assertEqual(analyze.draft(self.SEGS, {}), ("", "none"))
        self.assertEqual(analyze.draft([], {}), ("", "none"))

    def test_a_key_drafts_under_the_models_name(self):
        from memory import analyze
        seen = {}

        def complete(prompt, system="", max_tokens=0, **kw):
            seen["prompt"], seen["system"], seen["max"] = prompt, system, max_tokens
            return "  The override carried [00:20]. Watch the next budget round.  "

        with mock.patch.object(analyze.llm, "enabled", lambda: True), \
             mock.patch.object(analyze.llm, "complete", complete), \
             mock.patch.object(analyze.llm, "status", lambda: {"model": "gemini-2.0-flash"}):
            text, origin = analyze.draft(self.SEGS, {"title": "T"})
        self.assertEqual(origin, "ai:gemini-2.0-flash")
        self.assertEqual(text, "The override carried [00:20]. Watch the next budget round.")
        self.assertIn("what to watch", seen["prompt"].lower())
        self.assertIn("[00:10]", seen["prompt"])              # the receipts ride the prompt
        self.assertIn("Never invent", seen["system"])
        self.assertLessEqual(seen["max"], 800)

    def test_a_broken_lane_drafts_nothing(self):
        from memory import analyze

        def boom(*a, **k):
            raise RuntimeError("quota")

        with mock.patch.object(analyze.llm, "enabled", lambda: True), \
             mock.patch.object(analyze.llm, "complete", boom):
            self.assertEqual(analyze.draft(self.SEGS, {}), ("", "none"))


class ReceiptsTest(unittest.TestCase):
    def test_a_drafts_stamps_become_links_and_its_text_is_escaped(self):
        from web.charts import receipt_paras
        html = receipt_paras("Voted at [1:52:55] & again [3:04].\n\nWatch <this>.", "/app/m/x")
        self.assertIn('<a class="ts" href="/app/m/x#t6775">[1:52:55]</a>', html)
        self.assertIn('<a class="ts" href="/app/m/x#t184">[3:04]</a>', html)
        self.assertIn("&amp; again", html)
        self.assertIn("Watch &lt;this&gt;.", html)
        self.assertEqual(html.count("<p>"), 2)
        self.assertEqual(receipt_paras("", "/app/m/x"), "")


class RetryParkedTest(unittest.TestCase):
    """A tape that parked on the night it was posted is not a tape with no
    words: a live stream's auto captions arrive hours after it ends. The
    nightly drain asks again for a week, closes the drain ticket when the
    words land, and never raises past a failure."""

    class Corpus:
        def __init__(self):
            self.sql = []
            self.statuses = []

        def get_meeting(self, mid):
            return None            # the row as the stage read it stands

        def set_status(self, mid, status, error=""):
            self.statuses.append((mid, status, error))

        def _con(self):
            corpus = self

            class Con:
                def __enter__(s):
                    return s

                def __exit__(s, *a):
                    return False

                def execute(s, q, args=()):
                    corpus.sql.append((q, args))
                    return s

                def fetchall(s):
                    return []
            return Con()

    def run_retry(self, rows, outcome):
        from record import pipeline
        corpus = self.Corpus()
        seen = {}

        def fake_run(c, plan, job, workdir=None):
            seen["plan"] = plan
            if isinstance(outcome, Exception):
                raise outcome
            return outcome

        with mock.patch.object(pipeline, "parked_meetings", lambda c, days=7: rows), \
             mock.patch("memory.ingest.run", fake_run), \
             mock.patch.object(pipeline, "_embed", lambda c, town, meeting_id="", quiet=False: {"embedded": 5}):
            out = pipeline.retry_parked(corpus, mock.MagicMock(), quiet=True)
        return out, corpus, seen

    ROW = {"id": "8j49hpWub8M", "url": "https://www.youtube.com/watch?v=8j49hpWub8M",
           "town": "Brookline", "body": "Select Board", "date": "2026-09-22",
           "title": "Brookline Select Board Meeting - September 22, 2026", "status": "no_transcript"}

    def test_a_landing_keeps_the_name_and_day_closes_the_ticket_and_embeds(self):
        out, corpus, seen = self.run_retry([self.ROW], {"meeting_id": "8j49hpWub8M", "status": "live", "segments": 4000})
        self.assertEqual(out, [{"meeting_id": "8j49hpWub8M", "status": "live", "segments": 4000, "embedded": 5}])
        self.assertEqual(seen["plan"]["title"], self.ROW["title"])
        self.assertEqual(seen["plan"]["date"], "2026-09-22")
        self.assertEqual(seen["plan"]["video_id"], "8j49hpWub8M")
        self.assertTrue(any("asr_tasks SET status = 'done'" in q and a[1] == "8j49hpWub8M" for q, a in corpus.sql))

    def test_still_no_captions_stays_parked_without_touching_the_ticket(self):
        out, corpus, _ = self.run_retry([self.ROW], {"meeting_id": "8j49hpWub8M", "status": "no_transcript"})
        self.assertEqual(out, [{"meeting_id": "8j49hpWub8M", "status": "no_transcript"}])
        self.assertFalse(any("asr_tasks" in q for q, _ in corpus.sql))

    def test_a_failure_is_reported_not_raised(self):
        out, corpus, _ = self.run_retry([self.ROW], RuntimeError("the relay didn’t answer"))
        self.assertEqual(out[0]["status"], "failed")
        self.assertIn("relay", out[0]["error"])
        self.assertFalse(any("asr_tasks" in q for q, _ in corpus.sql))

    def test_nothing_parked_is_nothing_asked(self):
        out, corpus, seen = self.run_retry([], {"status": "live"})
        self.assertEqual(out, [])
        self.assertEqual(seen, {})

    def test_the_plan_of_a_parked_meeting_is_its_own_row(self):
        from record.pipeline import plan_from_meeting
        plan = plan_from_meeting(self.ROW)
        self.assertEqual(plan["kind"], "youtube")
        self.assertEqual(plan["id"], "8j49hpWub8M")
        self.assertEqual(plan["title"], self.ROW["title"])
        self.assertEqual((plan["town"], plan["body"], plan["date"]), ("Brookline", "Select Board", "2026-09-22"))


class EmbedBudgetTest(unittest.TestCase):
    """A landed meeting may spend a budget on its meaning vectors and no
    longer. On 2026-09-23 the embedding endpoint slowed to a batch a minute
    and worse; a 6,187-segment meeting sat silent in this stage for an hour
    until the job's timeout ended it, with a dozen approved tapes waiting
    behind it. The meeting is on the record before the clock starts; what
    the budget leaves is `record-embed`'s backlog, and the log says how much."""

    class Corpus:
        def __init__(self, batches):
            self.batches = [list(b) for b in batches]   # successive SELECT answers
            self.sql = []

        def _con(self):
            corpus = self

            class Con:
                def __enter__(s):
                    return s

                def __exit__(s, *a):
                    return False

                def execute(s, q, args=()):
                    corpus.sql.append((q, tuple(args)))
                    s.q = q
                    return s

                def fetchall(s):
                    if "SELECT id, text FROM segments" in s.q:
                        return corpus.batches.pop(0) if corpus.batches else []
                    return []

                def fetchone(s):
                    if "COUNT(*)" in s.q:
                        return {"n": sum(len(b) for b in corpus.batches)}
                    return {"n": 0}
            return Con()

    def backfill(self, corpus, **kw):
        from record import embed_neural as en
        with mock.patch.object(en, "available", lambda: True), \
             mock.patch.object(en, "spent_usd", lambda c: 0.0), \
             mock.patch.object(en, "embed_batch",
                               lambda texts, **k: [[1.0, 0.0] for _ in texts]):
            return en.backfill(corpus, meeting_id="m", verbose=False, **kw)

    ROWS = ([{"id": 1, "text": "a"}, {"id": 2, "text": "b"}],
            [{"id": 3, "text": "c"}, {"id": 4, "text": "d"}])

    def test_a_spent_deadline_stops_before_a_row_is_bought(self):
        corpus = self.Corpus(self.ROWS)
        out = self.backfill(corpus, deadline=time.monotonic() - 1)
        self.assertTrue(out["stopped_at_deadline"])
        self.assertEqual(out["embedded"], 0)
        self.assertEqual(out["behind"], 4)
        self.assertFalse(any("UPDATE segments" in q for q, _ in corpus.sql))
        behind = [a for q, a in corpus.sql if "COUNT(*)" in q]
        self.assertEqual(behind, [("m",)])   # counted for this meeting alone

    def test_a_deadline_still_ahead_embeds_the_whole_meeting(self):
        corpus = self.Corpus(self.ROWS)
        out = self.backfill(corpus, deadline=time.monotonic() + 60)
        self.assertFalse(out["stopped_at_deadline"])
        self.assertEqual((out["embedded"], out["behind"]), (4, 0))
        self.assertEqual(sum("UPDATE segments" in q for q, _ in corpus.sql), 4)

    def test_no_deadline_is_the_old_behaviour(self):
        out = self.backfill(self.Corpus(self.ROWS))
        self.assertEqual((out["embedded"], out["stopped_at_deadline"]), (4, False))

    def test_a_deadline_that_passes_mid_run_stops_between_batches(self):
        from record import embed_neural as en
        clock = [0.0]

        def slow_batch(texts, **k):
            clock[0] += 100.0          # every batch costs a hundred seconds
            return [[1.0, 0.0] for _ in texts]
        rows = self.ROWS + ([{"id": 5, "text": "e"}, {"id": 6, "text": "f"}],)
        corpus = self.Corpus(rows)
        with mock.patch.object(en, "available", lambda: True), \
             mock.patch.object(en, "spent_usd", lambda c: 0.0), \
             mock.patch.object(en, "embed_batch", slow_batch), \
             mock.patch.object(en.time, "monotonic", lambda: clock[0]):
            out = en.backfill(corpus, meeting_id="m", verbose=False, deadline=150.0)
        # checks at t=0 and t=100 pass, the third at t=200 does not
        self.assertEqual((out["embedded"], out["stopped_at_deadline"], out["behind"]),
                         (4, True, 2))

    def test_a_batch_the_clock_ran_out_inside_is_a_deadline_not_an_outage(self):
        from record import embed_neural as en
        clock = [0.0]

        def dead_batch(texts, **k):
            clock[0] += 500.0          # the ladder stood down inside this one
            return [None for _ in texts]
        corpus = self.Corpus(self.ROWS)
        with mock.patch.object(en, "available", lambda: True), \
             mock.patch.object(en, "spent_usd", lambda c: 0.0), \
             mock.patch.object(en, "embed_batch", dead_batch), \
             mock.patch.object(en.time, "monotonic", lambda: clock[0]):
            out = en.backfill(corpus, meeting_id="m", verbose=False, deadline=150.0)
        self.assertTrue(out["stopped_at_deadline"])
        self.assertEqual((out["embedded"], out["behind"]), (0, 2))

    def test_past_the_deadline_a_dead_batch_is_not_retried_as_singletons(self):
        from record import embed_neural as en
        calls = []

        def never(texts, task, deadline=0.0):
            calls.append(len(texts))
            return None
        with mock.patch.object(en, "available", lambda: True), \
             mock.patch.object(en, "_attempt", never):
            late = en.embed_batch(["a", "b", "c"], deadline=time.monotonic() - 1)
            self.assertEqual((late, calls), ([None, None, None], []))   # nothing sent at all
            calls.clear()
            soon = en.embed_batch(["a", "b", "c"], deadline=time.monotonic() + 60)
        self.assertEqual(soon, [None, None, None])
        self.assertEqual(calls, [3, 1, 1, 1])      # the batch, then each alone

    def test_the_ladder_does_not_sleep_past_the_deadline(self):
        from record import embed_neural as en
        slept, called = [], []

        class Flaky(Exception):
            code = 503

        def boom(texts, task):
            called.append(1)
            raise Flaky("busy")
        import io, contextlib
        with mock.patch.object(en, "_call", boom), \
             mock.patch.object(en.time, "sleep", lambda s: slept.append(s)), \
             contextlib.redirect_stdout(io.StringIO()):
            self.assertIsNone(en._attempt(["a"], "RETRIEVAL_DOCUMENT",
                                          deadline=time.monotonic() - 1))
            self.assertEqual((len(called), slept), (1, []))
            called.clear()
            self.assertIsNone(en._attempt(["a"], "RETRIEVAL_DOCUMENT"))
        self.assertEqual((len(called), slept), (4, [1.0, 4.0, 10.0]))

    def test_the_client_is_built_with_a_request_timeout(self):
        from record import embed_neural as en
        seen = {}

        class FakeTypes:
            class HttpOptions:
                def __init__(self, timeout=None):
                    seen["timeout"] = timeout

        class FakeGenai:
            class Client:
                def __init__(self, api_key="", http_options=None):
                    seen["key"] = api_key
        with mock.patch.object(en, "genai", FakeGenai), \
             mock.patch.object(en, "genai_types", FakeTypes), \
             mock.patch.object(en, "_CLIENT", None), \
             mock.patch.object(en.settings, "gemini_key", "k"):
            self.assertIsNotNone(en._client())
        self.assertEqual(seen, {"timeout": 60_000, "key": "k"})

    def test_a_count_that_cannot_be_read_is_unknown_not_fatal(self):
        from record import embed_neural as en

        class Broken:
            def _con(self):
                raise RuntimeError("no corpus")
        self.assertEqual(en._behind(Broken(), meeting_id="m"), -1)

    def _embed(self, budget, result):
        from record import embed_neural as en, pipeline
        from record.settings import settings
        seen = {}

        def fake_backfill(corpus, **kw):
            seen.update(kw)
            return dict(result)
        import io, contextlib
        buf = io.StringIO()
        with mock.patch.object(en, "available", lambda: True), \
             mock.patch.object(en, "backfill", fake_backfill), \
             mock.patch.object(settings, "embed_budget_s", budget), \
             contextlib.redirect_stdout(buf):
            r = pipeline._embed(object(), "Boston", meeting_id="m", quiet=False)
        return r, seen, buf.getvalue()

    def test_the_pipeline_hands_the_backfill_its_budget_as_a_deadline(self):
        before = time.monotonic()
        r, seen, out = self._embed(300, {"embedded": 3, "stopped_at_deadline": True,
                                         "behind": 42, "spent_usd": 0.0})
        self.assertEqual(seen["meeting_id"], "m")
        self.assertTrue(before + 299 <= seen["deadline"] <= time.monotonic() + 301)
        self.assertIn("300s embedding budget ran out", out)
        self.assertIn("42 segment(s)", out)
        self.assertIn("record-embed", out)
        self.assertEqual(r["embedded"], 3)

    def test_no_budget_means_no_deadline_and_no_such_line(self):
        r, seen, out = self._embed(0, {"embedded": 3, "spent_usd": 0.0})
        self.assertEqual(seen["deadline"], 0.0)
        self.assertNotIn("budget", out)

    def test_an_unknown_count_is_said_plainly(self):
        _, _, out = self._embed(120, {"embedded": 0, "stopped_at_deadline": True,
                                      "behind": -1, "spent_usd": 0.0})
        self.assertIn("behind for the rest of it", out)

    def test_the_setting_defaults_to_two_minutes_and_reads_the_environment(self):
        from record.settings import Settings
        with mock.patch.dict(os.environ, {"RECORD_EMBED_BUDGET_S": ""}):
            self.assertEqual(Settings().embed_budget_s, 120.0)
        with mock.patch.dict(os.environ, {"RECORD_EMBED_BUDGET_S": "45"}):
            self.assertEqual(Settings().embed_budget_s, 45.0)
        with mock.patch.dict(os.environ, {"RECORD_EMBED_BUDGET_S": "0"}):
            self.assertEqual(Settings().embed_budget_s, 0.0)

    def test_the_drains_call_sites_still_fit_the_embed_signature(self):
        # RetryParkedTest and the drain stub `_embed` as (c, town, meeting_id=, quiet=);
        # the budget is read inside, never passed, so those call sites stand.
        import inspect
        from record import pipeline
        self.assertEqual(list(inspect.signature(pipeline._embed).parameters),
                         ["corpus", "town", "meeting_id", "quiet"])


class NightlyCarryGuardTest(unittest.TestCase):
    """The nightly edition's carry step, run for real in a scratch repo. The
    press stamps `pressed_at` into app/pressing.json on every run (the
    2026-09-23 dispatch carried exactly that one line), and a night whose only
    change is that stamp must not become a commit — while a night the record
    changed still carries."""

    def guard(self):
        text = (ROOT / ".github" / "workflows" / "nightly-edition.yml").read_text()
        lines = text.splitlines()
        start = next(i for i, l in enumerate(lines) if l.strip() == "git add -A")
        end = next(i for i in range(start, len(lines)) if lines[i].strip() == "fi")
        return "\n".join(l.strip() for l in lines[start:end + 1])

    def carry(self, record_changed):
        with tempfile.TemporaryDirectory() as d:
            app = Path(d) / "app"
            app.mkdir()
            (app / "pressing.json").write_text('{"pressed_at":"2026-09-23T22:59:48Z"}')
            (app / "index.html").write_text("<p>one</p>")
            env = {**os.environ, "HOME": d, "GIT_CONFIG_GLOBAL": "/dev/null",
                   "GIT_CONFIG_NOSYSTEM": "1",
                   "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@t.test",
                   "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@t.test"}

            def git(*a):
                subprocess.run(["git", *a], cwd=d, env=env, check=True,
                               capture_output=True, text=True)
            git("init", "-q")
            git("add", "-A")
            git("commit", "-q", "-m", "seed")
            (app / "pressing.json").write_text('{"pressed_at":"2026-09-23T23:16:10Z"}')
            if record_changed:
                (app / "index.html").write_text("<p>two</p>")
            r = subprocess.run(["bash", "-e", "-c", self.guard() + "\necho CARRIED"],
                               cwd=d, env=env, capture_output=True, text=True)
            return r.returncode, r.stdout

    def test_a_stamp_alone_is_not_carried(self):
        rc, out = self.carry(record_changed=False)
        self.assertEqual(rc, 0)
        self.assertIn("nothing to carry", out)
        self.assertNotIn("CARRIED", out)

    def test_a_changed_record_is_carried(self):
        rc, out = self.carry(record_changed=True)
        self.assertEqual(rc, 0)
        self.assertIn("CARRIED", out)
        self.assertNotIn("nothing to carry", out)




class ReclaimStaleTest(unittest.TestCase):
    """A job killed by its timeout mid-ingest (2026-09-23) left its submission
    at `queued` — a state nothing ever selected again — and its meeting shell
    at `transcribing`, which the dedupe counted as already on the record. The
    next drain reclaims the one and the dedupe ignores the other."""

    class Corpus:
        def __init__(self, rowcount=0):
            self.sql, self.rowcount = [], rowcount

        def _con(self):
            corpus = self

            class Con:
                rowcount = corpus.rowcount

                def __enter__(s):
                    return s

                def __exit__(s, *a):
                    return False

                def execute(s, q, args=()):
                    corpus.sql.append((q, tuple(args)))
                    return s

                def fetchall(s):
                    return []

                def fetchone(s):
                    return {"n": corpus.rowcount}
            return Con()

    def test_a_queued_row_older_than_a_job_can_live_goes_back_to_approved(self):
        from record import pipeline
        corpus = self.Corpus(rowcount=2)
        before = time.time()
        n = pipeline.reclaim_stale(corpus)
        self.assertEqual(n, 2)
        (q, args), = corpus.sql
        self.assertIn("UPDATE submissions SET status=%s", q)
        self.assertIn("WHERE status=%s AND updated_at < %s", q)
        self.assertEqual((args[0], args[2]), ("approved", "queued"))
        self.assertAlmostEqual(args[3], before - 3600, delta=5)

    def test_the_drain_reclaims_first_and_says_so(self):
        from record import pipeline
        corpus = self.Corpus(rowcount=1)
        import io, contextlib
        buf = io.StringIO()
        with mock.patch.object(pipeline, "parked_meetings", lambda c, days=7: []), \
             contextlib.redirect_stdout(buf):
            out = pipeline.drain(corpus, retry_days=0)
        self.assertEqual(out["reclaimed"], 1)
        self.assertIn("1 reclaimed from a job that died", buf.getvalue())
        self.assertTrue(corpus.sql[0][0].startswith("UPDATE submissions"))   # before the SELECT
        self.assertTrue(corpus.sql[1][0].startswith("SELECT * FROM submissions"))

    def test_a_dry_run_reclaims_nothing_but_says_how_many_it_would(self):
        from record import pipeline
        corpus = self.Corpus(rowcount=1)
        with mock.patch.object(pipeline, "parked_meetings", lambda c, days=7: []):
            out = pipeline.drain(corpus, dry_run=True, quiet=True, retry_days=0)
        self.assertEqual(out.get("reclaimed", 0), 1)
        self.assertFalse(any(q.startswith("UPDATE") for q, _ in corpus.sql))

    def test_a_stale_in_flight_shell_is_not_on_the_record(self):
        from memory import ingest
        now = time.time()

        class Corpus:
            def __init__(self, hit):
                self.hit = hit

            def get_meeting(self, mid):
                return self.hit

            def find_by_url_canon(self, u):
                return None

            def find_by_hash(self, h):
                return None
        plan = {"id": "m", "url_canon": "yt:m", "source_hash": ""}
        fresh = {"id": "m", "status": "transcribing", "updated_at": now - 60}
        stale = {"id": "m", "status": "transcribing", "updated_at": now - 4000}
        live = {"id": "m", "status": "live", "updated_at": now - 4000}
        untimed = {"id": "m", "status": "analyzing"}
        H = ingest.STALE_IN_FLIGHT_S
        self.assertIs(ingest.submit_dedupe(Corpus(fresh), plan, stale_after=H), fresh)
        self.assertIsNone(ingest.submit_dedupe(Corpus(stale), plan, stale_after=H))
        self.assertIs(ingest.submit_dedupe(Corpus(live), plan, stale_after=H), live)   # live is live, however old
        self.assertIsNone(ingest.submit_dedupe(Corpus(untimed), plan, stale_after=H))
        self.assertTrue(ingest.stale_in_flight({"updated_at": "junk"}, H))

    def test_the_desk_passes_no_bound_and_nothing_is_ever_stale(self):
        # A three-hour on-device transcription never touches the row; the
        # desk's default must keep refusing a second job on the same tape.
        from memory import ingest
        old = {"id": "m", "status": "transcribing", "updated_at": time.time() - 3 * 3600}

        class Corpus:
            def get_meeting(self, mid):
                return old
        plan = {"id": "m", "url_canon": "", "source_hash": ""}
        self.assertIs(ingest.submit_dedupe(Corpus(), plan), old)
        self.assertFalse(ingest.stale_in_flight(old))
        self.assertFalse(ingest.stale_in_flight({}, 0))

    def test_the_pipeline_passes_its_hour(self):
        import inspect
        from record import pipeline
        src = inspect.getsource(pipeline.ingest_one)
        self.assertIn("submit_dedupe(corpus, plan, stale_after=ingest.STALE_IN_FLIGHT_S)", src)

    def test_a_dry_run_counts_what_a_real_run_would_reclaim(self):
        from record import pipeline
        corpus = self.Corpus(rowcount=3)
        self.assertEqual(pipeline.reclaim_stale(corpus, dry_run=True), 3)
        (q, args), = corpus.sql
        self.assertTrue(q.startswith("SELECT COUNT(*)"))
        self.assertEqual(args[0], "queued")

    def test_parked_meetings_also_selects_a_stale_shell_of_the_week(self):
        from record import pipeline
        corpus = self.Corpus()
        before = time.time()
        pipeline.parked_meetings(corpus, days=7)
        (q, args), = corpus.sql
        self.assertIn("status = 'no_transcript'", q)
        self.assertIn("url <> ''", q)          # a desk import's file: row has nothing to ask
        self.assertIn("status IN ('queued', 'transcribing', 'analyzing')", q)
        self.assertIn("COALESCE(updated_at, added_at, 0) < %s", q)
        self.assertAlmostEqual(args[0], before - 7 * 86400, delta=5)
        self.assertAlmostEqual(args[1], before - 3600, delta=5)

    def _retry(self, current_status, outcome):
        from record import pipeline
        seen = {"runs": 0, "status": []}
        row = {"id": "m1", "url": "https://www.youtube.com/watch?v=m1", "town": "Brookline",
               "body": "Select Board", "date": "2026-09-22", "title": "t", "status": "transcribing"}

        class Corpus:
            def get_meeting(self, mid):
                return {"id": mid, "status": current_status}

            def set_status(self, mid, status, error=""):
                seen["status"].append((mid, status, error))

            def _con(self):
                raise AssertionError("no ticket is closed on a skip or a failure")

        def fake_run(c, plan, job, workdir=None):
            seen["runs"] += 1
            if isinstance(outcome, Exception):
                raise outcome
            return outcome
        with mock.patch.object(pipeline, "parked_meetings", lambda c, days=7: [row]), \
             mock.patch("memory.ingest.run", fake_run), \
             mock.patch.object(pipeline, "_embed", lambda c, town, meeting_id="", quiet=False: {"embedded": 0}):
            out = pipeline.retry_parked(Corpus(), mock.MagicMock(), quiet=True)
        return out, seen

    def test_the_retry_stage_does_not_ask_twice_for_a_meeting_the_queue_just_landed(self):
        out, seen = self._retry("live", {"status": "live"})
        self.assertEqual((out[0]["status"], seen["runs"]), ("exists", 0))

    def test_a_failed_ask_goes_back_to_parked_with_its_sentence(self):
        out, seen = self._retry("transcribing", RuntimeError("relay down"))
        self.assertEqual(out[0]["status"], "failed")
        self.assertEqual(seen["status"], [("m1", "no_transcript", "relay down")])

    def test_a_tape_the_queue_stage_just_parked_is_not_asked_again_in_the_same_drain(self):
        from record import pipeline
        started = time.time()
        fresh = {"id": "a", "url": "u", "status": "no_transcript", "updated_at": started + 30}
        old = {"id": "b", "url": "u", "status": "no_transcript", "updated_at": started - 30}
        asked = []

        class Corpus:
            def get_meeting(self, mid):
                return None

            def set_status(self, *a):
                pass

        def fake_run(c, plan, job, workdir=None):
            asked.append(plan.get("id") or plan.get("url"))
            return {"status": "no_transcript"}
        with mock.patch.object(pipeline, "parked_meetings", lambda c, days=7: [fresh, old]), \
             mock.patch("memory.ingest.run", fake_run):
            out = pipeline.retry_parked(Corpus(), mock.MagicMock(), quiet=True, since=started)
        self.assertEqual(len(asked), 1)
        self.assertEqual([r["meeting_id"] for r in out], ["b"])
        self.assertEqual(pipeline._touched({"updated_at": "junk"}), 0.0)

    def test_the_drain_hands_the_retry_stage_its_own_start(self):
        import inspect
        from record import pipeline
        src = inspect.getsource(pipeline.drain)
        self.assertIn("since=started", src)

    def test_a_failed_retry_fails_the_job_like_a_failed_ingest(self):
        from record import pipeline
        self.assertEqual(pipeline.exit_code({"failed": 0, "retried": []}), 0)
        self.assertEqual(pipeline.exit_code({"failed": 1, "retried": []}), 1)
        self.assertEqual(pipeline.exit_code({"failed": 0, "retried": [{"status": "no_transcript"}]}), 0)
        self.assertEqual(pipeline.exit_code({"failed": 0, "retried": [{"status": "failed"}]}), 1)
        self.assertEqual(pipeline.exit_code({}), 0)
