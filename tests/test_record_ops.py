"""The steward's desk (specs/27): what the night did, what is running, the
record counted — read through record/ops.py, never from a terminal.

The platform is behind one seam (`fetch`), so these exercise the shaping
of executions and log lines against recorded answers, the refusals, and
the routes' guards, with no network and no database."""

import json
import os
import re
import time
import unittest
from pathlib import Path
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]


class ShapeTest(unittest.TestCase):
    RAW = {"name": "projects/p/locations/r/jobs/record-pipeline/executions/record-pipeline-bkj6w",
           "job": "projects/p/locations/r/jobs/record-pipeline",
           "createTime": "2026-09-24T00:08:30.123456789Z",
           "startTime": "2026-09-24T00:08:37Z",
           "completionTime": "2026-09-24T01:26:10Z",
           "succeededCount": 1, "retriedCount": 1,
           "conditions": [{"type": "Completed", "state": "CONDITION_SUCCEEDED",
                           "message": "Execution completed successfully"}],
           "template": {"containers": [{"image": "us-east1-docker.pkg.dev/p/record/api:r43"}]}}

    def test_an_execution_in_the_desks_words(self):
        from record import ops
        e = ops.shape_execution(self.RAW)
        self.assertEqual((e["name"], e["job"], e["state"], e["image"], e["retries"]),
                         ("record-pipeline-bkj6w", "record-pipeline", "succeeded", "r43", 1))
        self.assertEqual(e["message"], "Execution completed successfully")
        self.assertAlmostEqual(e["completed"] - e["started"], 77 * 60 + 33, delta=1)
        self.assertGreater(e["created"], 1.7e9)

    def test_running_failed_and_cancelled(self):
        from record import ops
        running = dict(self.RAW, completionTime="", runningCount=1, succeededCount=0)
        failed = dict(self.RAW, succeededCount=0, failedCount=1)
        cancelled = dict(self.RAW, succeededCount=0, cancelledCount=1)
        self.assertEqual(ops.shape_execution(running)["state"], "running")
        self.assertEqual(ops.shape_execution(failed)["state"], "failed")
        self.assertEqual(ops.shape_execution(cancelled)["state"], "cancelled")

    def test_an_image_is_named_by_its_tag_or_a_short_digest(self):
        from record import ops
        self.assertEqual(ops.image_tag("us-east1-docker.pkg.dev/p/record/api:r45"), "r45")
        self.assertEqual(ops.image_tag("us-east1-docker.pkg.dev/p/record/api:r45@sha256:" + "ab" * 32), "r45")
        self.assertEqual(ops.image_tag("us-east1-docker.pkg.dev/p/record/api@sha256:" + "ab" * 32), "ab" * 6)
        self.assertEqual(ops.image_tag(""), "")
        e = ops.shape_execution(dict(self.RAW, template={"containers": [{"image": "x/api@sha256:" + "12" * 32}]}))
        self.assertEqual(e["image"], "12" * 6)

    def test_a_time_the_platform_writes_with_nanoseconds_parses(self):
        from record import ops
        self.assertAlmostEqual(ops._when("2026-09-24T00:08:30.123456789Z"), 1790208510.123456, places=3)
        self.assertEqual(ops._when(""), 0.0)
        self.assertEqual(ops._when("junk"), 0.0)


class PlatformSeamTest(unittest.TestCase):
    def test_executions_are_newest_first_and_capped(self):
        from record import ops
        seen = {}

        def fetch(method, url, body, params):
            seen.update(method=method, url=url, params=params)
            return {"executions": [
                dict(ShapeTest.RAW, name="x/record-pipeline-old", createTime="2026-09-23T00:00:00Z"),
                dict(ShapeTest.RAW, name="x/record-pipeline-new", createTime="2026-09-24T00:00:00Z"),
                dict(ShapeTest.RAW, name="x/record-pipeline-mid", createTime="2026-09-23T12:00:00Z")]}
        rows = ops.executions("record-pipeline", limit=2, fetch=fetch)
        self.assertEqual([r["name"] for r in rows], ["record-pipeline-new", "record-pipeline-mid"])
        self.assertEqual(seen["method"], "GET")
        self.assertIn("/jobs/record-pipeline/executions", seen["url"])
        self.assertEqual(seen["params"], {"pageSize": 2})

    def test_the_log_tail_is_oldest_first_and_names_only_that_execution(self):
        from record import ops
        seen = {}

        def fetch(method, url, body, params):
            seen.update(method=method, url=url, body=body)
            return {"entries": [
                {"timestamp": "2026-09-24T00:11:56Z", "textPayload": "    in the record — 4372 segments"},
                {"timestamp": "2026-09-24T00:08:37Z", "textPayload": "12 approved submission(s) waiting"},
                {"timestamp": "2026-09-24T00:08:38Z", "jsonPayload": {"message": "  finding a transcript…"}},
                {"timestamp": "2026-09-24T00:08:39Z", "textPayload": ""},
                {"timestamp": "2026-09-24T00:08:40Z", "jsonPayload": ""},
                {"timestamp": "2026-09-24T00:08:41Z", "jsonPayload": {}}]}
        lines = ops.log_tail("record-pipeline-bkj6w", limit=50, fetch=fetch)
        self.assertEqual([l["line"] for l in lines],
                         ["12 approved submission(s) waiting", "  finding a transcript…",
                          "    in the record — 4372 segments"])
        self.assertEqual(seen["method"], "POST")
        self.assertIn('execution_name"="record-pipeline-bkj6w"', seen["body"]["filter"])
        self.assertEqual(seen["body"]["pageSize"], 50)

    def test_a_name_that_is_not_an_execution_is_refused_before_any_call(self):
        from record import ops
        for bad in ('x" OR 1=1', "", "A", "record pipeline"):
            with self.assertRaises(ops.OpsError) as cm:
                ops.log_tail(bad, fetch=lambda *a: self.fail("called the platform"))
            self.assertEqual(cm.exception.status, 400)

    def test_only_the_nights_jobs_can_be_run_and_the_execution_is_named(self):
        from record import ops
        for job in ("record-migrate", "record-press"):
            with self.assertRaises(ops.OpsError) as cm:
                ops.run_job(job, fetch=lambda *a: self.fail("called the platform"))
            self.assertEqual(cm.exception.status, 400, job)
        # an operation's own name is not an execution
        r = ops.run_job("record-poll", fetch=lambda m, u, b, p: {"name": "x/operations/uuid"})
        self.assertEqual(r["execution"], "")
        r = ops.run_job("record-poll", fetch=lambda m, u, b, p: {
            "metadata": {"name": "projects/p/locations/r/jobs/record-poll/executions/record-poll-zz9"}})
        self.assertEqual(r, {"job": "record-poll", "execution": "record-poll-zz9", "started": True})

    def test_unconfigured_is_a_sentence_with_both_names(self):
        from record import ops
        with mock.patch.dict(os.environ, {"RECORD_CLOUD_PROJECT": "", "RECORD_CLOUD_REGION": ""}):
            c = ops.cloud()
            self.assertFalse(c["configured"])
            self.assertIn("RECORD_CLOUD_PROJECT", c["why"])
            self.assertIn("RECORD_CLOUD_REGION", c["why"])
            with self.assertRaises(ops.OpsError) as cm:
                ops.executions("record-poll")
            self.assertEqual(cm.exception.status, 503)
        with mock.patch.dict(os.environ, {"RECORD_CLOUD_PROJECT": "p", "RECORD_CLOUD_REGION": "r"}):
            self.assertTrue(ops.cloud()["configured"])


class EditionTest(unittest.TestCase):
    def test_the_edition_is_read_from_the_readers_side(self):
        from record import ops
        seen = {}

        def fetch_text(url):
            seen["url"] = url
            return json.dumps({"version": "2.1.20", "edition_date": "2026-09-22",
                               "corpus_hash": "6865a1f2ec625c8a", "pressed_at": "2026-09-24T00:34:22Z",
                               "counts": {"meetings": 20}})
        e = ops.edition_live(fetch_text=fetch_text)
        self.assertTrue(e["reachable"])
        self.assertTrue(seen["url"].endswith("/app/pressing.json"))
        self.assertEqual((e["version"], e["counts"]["meetings"]), ("2.1.20", 20))

    def test_unreachable_is_a_sentence(self):
        from record import ops

        def fetch_text(url):
            raise OSError("no route")
        e = ops.edition_live(fetch_text=fetch_text)
        self.assertEqual((e["reachable"], "no route" in e["why"]), (False, True))


class RoutesGuardTest(unittest.TestCase):
    """The desk's routes with no database anywhere near them: the guards
    answer before the corpus is touched."""

    def setUp(self):
        from fastapi.testclient import TestClient
        from record import auth
        from record.app import create_app
        p = mock.patch.object(auth, "verify_token", lambda tok: {"email": "s@example.org", "name": "S"})
        p.start(); self.addCleanup(p.stop)
        self.client = TestClient(create_app(corpus=object()))
        self.hdr = {"Authorization": "Bearer t"}

    def test_the_jobs_screen_says_when_it_cannot_see_the_platform(self):
        with mock.patch.dict(os.environ, {"RECORD_CLOUD_PROJECT": "", "RECORD_CLOUD_REGION": ""}):
            r = self.client.get("/api/steward/jobs", headers=self.hdr)
        self.assertEqual(r.status_code, 200)
        j = r.json()
        self.assertFalse(j["cloud"]["configured"])
        self.assertEqual(j["jobs"], {})
        self.assertEqual([s["job"] for s in j["schedule"]][:2], ["record-poll", "record-pipeline"])

    def test_a_log_is_only_read_for_an_execution_of_that_job(self):
        r = self.client.get("/api/steward/jobs/record-poll/executions/record-pipeline-abc12/log", headers=self.hdr)
        self.assertEqual(r.status_code, 400)
        r = self.client.get("/api/steward/jobs/nope/executions/nope-1/log", headers=self.hdr)
        self.assertEqual(r.status_code, 400)

    def test_a_job_that_is_not_the_nights_cannot_be_run(self):
        r = self.client.post("/api/steward/jobs/record-migrate/run", headers=self.hdr)
        self.assertEqual(r.status_code, 400)

    def test_a_platform_failure_is_a_502_never_a_lost_session(self):
        from record import ops
        with mock.patch.object(ops, "run_job", side_effect=ops.OpsError("the platform answered 403", 403)):
            r = self.client.post("/api/steward/jobs/record-poll/run", headers=self.hdr)
        self.assertEqual(r.status_code, 502)
        with mock.patch.object(ops, "log_tail", side_effect=ops.OpsError("unset", 503)):
            r = self.client.get("/api/steward/jobs/record-poll/executions/record-poll-a1/log", headers=self.hdr)
        self.assertEqual(r.status_code, 502)

    def test_everything_on_the_desk_fails_closed_without_a_steward(self):
        from record import auth
        with mock.patch.object(auth, "verify_token", side_effect=auth.AuthError(401, "no")):
            for path in ("/api/steward/overview", "/api/steward/jobs", "/api/steward/meetings",
                         "/api/steward/jobs/record-poll/executions/record-poll-a1/log"):
                self.assertEqual(self.client.get(path).status_code, 401, path)
            self.assertEqual(self.client.post("/api/steward/jobs/record-poll/run").status_code, 401)

    def test_config_hands_the_console_the_site(self):
        j = self.client.get("/steward/config.json").json()
        self.assertTrue(j["site_base"].startswith("http"))
        self.assertFalse(j["site_base"].endswith("/"))


class ConsoleDeskTest(unittest.TestCase):
    """The page reaches every route the desk added, links to the record,
    and scopes itself by municipality."""

    def setUp(self):
        self.html = (ROOT / "record/static/console.html").read_text()
        self.js = (ROOT / "record/static/console.js").read_text()
        self.css = (ROOT / "record/static/console.css").read_text()

    def test_there_is_a_way_back_to_the_record(self):
        self.assertIn('id="open-record"', self.html)
        self.assertIn("$('open-record').href = SITE + '/app/'", self.js)

    def test_every_pane_has_its_tab_and_its_loader(self):
        panes = re.findall(r'<section id="(pane-[a-z]+)"', self.html)
        tabs = re.findall(r'data-pane="(pane-[a-z]+)"', self.html)
        self.assertEqual(sorted(panes), sorted(tabs))
        for pane in panes:
            self.assertIn("'" + pane + "':", self.js, pane)
        self.assertEqual(panes[0], "pane-tonight")

    def test_the_desk_reaches_its_routes(self):
        for route in ("/api/steward/overview", "/api/steward/jobs", "/api/steward/meetings",
                      "/executions/", "/run", "/api/steward/audit"):
            self.assertIn(route, self.js, route)

    def test_the_municipality_scopes_every_screen(self):
        self.assertIn('id="town-picks"', self.html)
        for call in ("submissions?town=", "meetings?town=", "audit?limit=300&town="):
            self.assertIn(call, self.js, call)
        self.assertIn("TOWNS.filter(function (t) { return !TOWN || t.slug === TOWN; })", self.js)
        self.assertIn('role="radiogroup"', self.html)
        self.assertIn("'aria-checked': TOWN === t.slug", self.js)

    def test_the_tonight_screen_refreshes_only_while_open_and_only_once(self):
        self.assertIn("if (TOKEN && $('tonight-live').checked && !$('pane-tonight').hidden)", self.js)
        self.assertIn("if (tab.dataset.pane !== 'pane-tonight') stopTick();", self.js)
        self.assertIn("const my = ++SEQ;", self.js)
        self.assertIn("if (my !== SEQ) return;", self.js)
        self.assertIn("TICK = setTimeout(function () { tonight(false); }, 20000);", self.js)
        # a lost session (401/403) or an unconfigured console stops the timer
        self.assertIn("if (TOKEN && $('tonight-live').checked", self.js)
        m = re.search(r"function handle\(err, where\) \{[\s\S]*?\n\}", self.js)
        self.assertEqual(m.group(0).count("stopTick();"), 2)

    def test_the_meetings_screen_counts_blank_cues_like_the_rest_of_the_desk(self):
        src = (ROOT / "record/ops.py").read_text()
        body = src[src.index("def meetings_of"):]
        self.assertIn("btrim(coalesce(text, '')) <> ''", body)

    def test_run_now_is_not_drawn_without_the_platform_and_never_for_the_press(self):
        self.assertIn("if (jobs.cloud && jobs.cloud.configured) {", self.js)
        self.assertIn("/^record-(poll|pipeline|embed)$/", self.js)

    def test_the_partial_index_migration_exists(self):
        sql = (ROOT / "record/migrations/002_neural_todo.sql").read_text()
        self.assertIn("WHERE emb_neural IS NULL", sql)
        self.assertIn("CREATE INDEX IF NOT EXISTS", sql)

    def test_running_a_job_asks_first_and_says_it_spends(self):
        m = re.search(r"async function runJob[\s\S]*?\n}", self.js)
        self.assertIsNotNone(m)
        self.assertIn("confirm(", m.group(0))
        self.assertIn("spends what a night spends", m.group(0))

    def test_the_log_reads_an_execution_by_its_own_name_only(self):
        self.assertIn(r"/^(record-[a-z]+)-[a-z0-9]+$/", self.js)

    def test_nothing_is_drawn_with_innerhtml(self):
        self.assertIsNone(re.search(r"\.innerHTML\s*=", self.js))

    def test_the_desks_styles_take_no_studio_hue(self):
        desk = self.css[self.css.index("/* -- the desk (2026-09-24)"):]
        for hue in ("a855f7", "7c3aed", "22c55e"):
            self.assertNotIn(hue, desk.lower())


if __name__ == "__main__":
    unittest.main()
