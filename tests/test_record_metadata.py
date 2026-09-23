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
import unittest
from unittest import mock


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
