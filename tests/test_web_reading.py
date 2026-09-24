"""A model's words, pressed whole and read right (specs/27 §2.1–2.2).

v2.1.21 pressed every hosted summary and every drafted reading cut off
mid-sentence ("At the September 22, 2026,") — Gemini's thinking spent the
output budget before the answer began, and the seam never asked why the
answer stopped. And the readings that did arrive showed their Markdown raw
("**What it means**", "*   Motion/Vote:"). These pin both halves: the seam
gives the thought its own room and refuses a cut answer on every provider;
the renderer (web/charts.py receipt_paras, its JS twin app.js receiptParas)
reads the subset of Markdown the models write, escapes first, and links
every receipt — and the twins answer byte for byte.
"""

import json
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest import mock

REPO = Path(__file__).resolve().parent.parent


# ---------------------------------------------------------------------------
# the seam — thinking room, and a cut answer is no answer
# ---------------------------------------------------------------------------

class _FakeAPI:
    """A local stand-in for the three providers: answers each POST with the
    next canned body, and keeps what was asked."""

    def __init__(self, bodies):
        import http.server
        import threading
        self.bodies, self.reqs = list(bodies), []
        outer = self

        class H(http.server.BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def do_POST(self):
                n = int(self.headers.get("Content-Length", "0"))
                outer.reqs.append({"path": self.path,
                                   "body": json.loads(self.rfile.read(n) or b"{}")})
                out = json.dumps(outer.bodies.pop(0) if outer.bodies else {}).encode()
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(out)))
                self.end_headers()
                self.wfile.write(out)

        self.srv = http.server.HTTPServer(("127.0.0.1", 0), H)
        threading.Thread(target=self.srv.serve_forever, daemon=True).start()
        self.base = f"http://127.0.0.1:{self.srv.server_address[1]}"

    def close(self):
        self.srv.shutdown()
        self.srv.server_close()


class TestTheSeamGivesTheThoughtRoom(unittest.TestCase):
    def setUp(self):
        from czcore import llm
        self.llm = llm
        self.td = tempfile.TemporaryDirectory(prefix="cz-seam-")
        self.addCleanup(self.td.cleanup)
        pd = mock.patch.object(llm, "support_dir", lambda sub="": Path(self.td.name))
        pd.start(); self.addCleanup(pd.stop)
        saved = {k: os.environ.pop(k, None) for k in (
            "ANTHROPIC_API_KEY", "OPENAI_API_KEY", "GEMINI_API_KEY",
            "GOOGLE_API_KEY", "CONTROL_Z_LLM_MODEL")}
        self.addCleanup(lambda: [os.environ.update({k: v}) for k, v in saved.items() if v is not None])
        with llm._LEDGER_LOCK:
            self._saved = llm._LEDGER[:]
            llm._LEDGER.clear()

        def _restore():
            with llm._LEDGER_LOCK:
                llm._LEDGER[:] = self._saved
        self.addCleanup(_restore)

    def serve(self, provider, bodies, key):
        api = _FakeAPI(bodies)
        self.addCleanup(api.close)
        (Path(self.td.name) / "llm.json").write_text(json.dumps({
            "api_key": key, "provider": provider, "model": "m-test", "base_url": api.base}))
        return api

    def test_gemini_asks_for_the_answer_plus_the_thought(self):
        api = self.serve("gemini", [{"candidates": [{"content": {"parts": [{"text": "A whole answer."}]},
                                                     "finishReason": "STOP"}]}], "AIza-x")
        self.assertEqual(self.llm.complete("q", max_tokens=400), "A whole answer.")
        got = api.reqs[-1]["body"]["generationConfig"]["maxOutputTokens"]
        self.assertEqual(got, 400 + self.llm.GEMINI_THINKING_ROOM)
        self.assertGreaterEqual(self.llm.GEMINI_THINKING_ROOM, 4096)

    def test_a_cut_answer_is_refused_on_every_provider_and_still_counted(self):
        cases = [
            ("gemini", "AIza-x", {"candidates": [{"content": {"parts": [{"text": "At the September 22, 2026,"}]},
                                                  "finishReason": "MAX_TOKENS"}],
                                  "usageMetadata": {"promptTokenCount": 9, "candidatesTokenCount": 8,
                                                    "thoughtsTokenCount": 392}}),
            ("openai", "sk-x", {"choices": [{"message": {"content": "During the"}, "finish_reason": "length"}],
                                "usage": {"prompt_tokens": 9, "completion_tokens": 400}}),
            ("anthropic", "sk-ant-x", {"content": [{"type": "text", "text": "The board"}],
                                       "stop_reason": "max_tokens",
                                       "usage": {"input_tokens": 9, "output_tokens": 400}}),
        ]
        for prov, key, body in cases:
            with self.subTest(prov):
                self.serve(prov, [body], key)
                with self.assertRaises(RuntimeError) as cm:
                    self.llm.complete("q", max_tokens=400)
                self.assertIn("cut off", str(cm.exception))
                # the call was paid for — the audit counts it, thought and all
                self.assertEqual(self.llm.last_usage()["tokens_out"], 400)

    def test_a_whole_answer_passes_and_the_thought_is_billed(self):
        self.serve("gemini", [{"candidates": [{"content": {"parts": [{"text": "Whole."}]}, "finishReason": "STOP"}],
                               "usageMetadata": {"promptTokenCount": 5, "candidatesTokenCount": 2,
                                                 "thoughtsTokenCount": 30}}], "AIza-x")
        self.assertEqual(self.llm.complete("q"), "Whole.")
        self.assertEqual(self.llm.last_usage()["tokens_out"], 32)

    def test_thought_parts_are_never_the_answer(self):
        self.serve("gemini", [{"candidates": [{"content": {"parts": [
            {"text": "let me think about the budget", "thought": True}, {"text": "The answer."}]},
            "finishReason": "STOP"}]}], "AIza-x")
        self.assertEqual(self.llm.complete("q"), "The answer.")

    def test_the_vision_door_keeps_the_same_rules(self):
        api = self.serve("gemini", [{"candidates": [{"content": {"parts": [{"text": "A hall"}]},
                                                     "finishReason": "MAX_TOKENS"}]}], "AIza-x")
        with self.assertRaises(RuntimeError):
            self.llm.complete_vision("what is this", "QUJD", max_tokens=300)
        self.assertEqual(api.reqs[-1]["body"]["generationConfig"]["maxOutputTokens"],
                         300 + self.llm.GEMINI_THINKING_ROOM)

    def test_a_cut_summary_falls_to_the_extractive_one_and_a_cut_draft_to_none(self):
        from memory import analyze
        segs = [{"start": 10.0, "end": 14.0, "text": "We will discuss the override tonight."},
                {"start": 4000.0, "end": 4004.0, "text": "The motion carries unanimously."}]

        def cut(*a, **k):
            raise RuntimeError("the answer was cut off at its length limit — a fragment is not an answer")
        with mock.patch.object(analyze.llm, "enabled", lambda: True), \
             mock.patch.object(analyze.llm, "complete", cut):
            text, origin = analyze.summary(segs, {"title": "T"})
            self.assertEqual(origin, "extractive")
            self.assertEqual(analyze.draft(segs, {"title": "T"}), ("", "none"))

    def test_the_prompts_ask_for_plain_text_and_hour_stamps(self):
        from memory import analyze
        seen = {}

        def complete(prompt, system="", max_tokens=0, **kw):
            seen.setdefault("calls", []).append((prompt, system))
            return "What it means: fine [1:06:40]."
        segs = [{"start": 10.0, "end": 14.0, "text": "opening"},
                {"start": 4000.0, "end": 4004.0, "text": "the vote"}]
        with mock.patch.object(analyze.llm, "enabled", lambda: True), \
             mock.patch.object(analyze.llm, "complete", complete), \
             mock.patch.object(analyze.llm, "status", lambda: {"model": "m"}):
            analyze.summary(segs, {})
            analyze.draft(segs, {})
        for prompt, system in seen["calls"]:
            self.assertIn("no Markdown", system)
            self.assertIn("[00:10] opening", prompt)          # under the hour: MM:SS, as before
            self.assertIn("[1:06:40] the vote", prompt)       # past it: H:MM:SS, never [66:40]
        self.assertIn("What it means:", seen["calls"][1][1])


# ---------------------------------------------------------------------------
# the renderer — Markdown read, never shown; receipts linked; twins equal
# ---------------------------------------------------------------------------

FIXTURES = [
    "",
    "Voted at [1:52:55] & again [3:04].\n\nWatch <this>.",
    "**What it means**  \nThe Brookline Select Board focused on the override vote [1:12:24].",
    "**What it means:**\nThe board met.\n\n**Who moved it:** Chair Warren [13:15-13:44].\n**What to watch**: the ballot.",
    "What it means: the plan.\nWho moved it: nobody [12:12, 17:13].\nwhat to watch: the budget [264:28][279:55].",
    "## Decisions\n*   Motion/Vote: Approved, seconded [13:15-13:44].\n    *   Paving 10 miles [87:31-87:46]\n- a dash item\n• a bullet item\nAfter the list.",
    "Garbage [1:75] and [99:99:99] and [13:] and [see 3:04] and [1:2:3] stay as written.",
    "A *quiet* aside, a stray * star, `code` ticks, and 3 * 4 = 12.",
    "---\n***\nRules vanish.\n___",
    "<script>alert(1)</script> [0:05] \"quoted\" 'single'",
    "Line one\r\nLine two\rLine three Line four",
    "﻿  Padded line  \t",
    "[00:20] opens; [0:00] too; [12:30–12:45] and [1:00:00—1:00:30] ranges; [1:00, 2:00; 3:00] lists.",
    "[1:00 2:00] a space-joined pair and [1:00 - x] a stray",
    "**bold with [2:00] inside** and **unclosed bold",
    "* \n-\n*   ",
    "WHAT IT MEANS: shouted label.",
    "What it means — no colon, no label.",
    "ſtray long s: whaſ it meanſ: stays plain.",
    "```\nfenced words\n```\n**\n* **\n- `x`",
    "* one\n* two\n```\n* three",
]


class TestTheRendererReadsTheModelsProse(unittest.TestCase):
    def rp(self, text, base="/app/m/x"):
        from web.charts import receipt_paras
        return receipt_paras(text, base)

    def test_headings_lists_and_bold_are_read_never_shown(self):
        out = self.rp(FIXTURES[5])
        self.assertIn('<p class="rd-h">Decisions</p>', out)
        self.assertIn('<ul class="rd-list"><li>Motion/Vote: Approved, seconded '
                      '<a class="ts" href="/app/m/x#t795">[13:15]</a>–<a class="ts" href="/app/m/x#t824">[13:44]</a>.</li>', out)
        self.assertEqual(out.count("<li>"), 4)
        self.assertIn("<p>After the list.</p>", out)
        out = self.rp(FIXTURES[2])
        self.assertTrue(out.startswith('<p class="rd-h">What it means</p><p>The Brookline'), out)
        self.assertNotIn("*", out)

    def test_the_three_labels_lead_their_paragraphs_in_bold(self):
        out = self.rp(FIXTURES[4])
        self.assertIn("<p><b>What it means:</b> the plan.</p>", out)
        self.assertIn('<p><b>Who moved it:</b> nobody <a class="ts" href="/app/m/x#t732">[12:12]</a>, '
                      '<a class="ts" href="/app/m/x#t1033">[17:13]</a>.</p>', out)
        self.assertIn("<b>what to watch:</b>", out)
        # the minutes-past-the-hour stamps the old prompt taught read as the page's times
        self.assertIn('<a class="ts" href="/app/m/x#t15868">[4:24:28]</a>', out)
        self.assertIn('<a class="ts" href="/app/m/x#t16795">[4:39:55]</a>', out)
        out = self.rp(FIXTURES[3])
        self.assertIn('<p class="rd-h">What it means</p>', out)
        self.assertIn("<p><b>Who moved it:</b> Chair Warren", out)
        self.assertNotIn("<b><b>", out)

    def test_garbage_stamps_stay_as_written_and_everything_is_escaped(self):
        out = self.rp(FIXTURES[6])
        for g in ("[1:75]", "[99:99:99]", "[13:]", "[see 3:04]", "[1:2:3]"):
            self.assertIn(g, out)
        self.assertNotIn('class="ts"', out)
        out = self.rp(FIXTURES[9])
        self.assertIn("&lt;script&gt;alert(1)&lt;/script&gt;", out)
        self.assertIn("&quot;quoted&quot;", out)
        self.assertNotIn("<script>", out)

    def test_leftover_syntax_goes_and_literal_asterisks_stay(self):
        out = self.rp(FIXTURES[7])
        self.assertEqual(out, "<p>A <i>quiet</i> aside, a stray * star, code ticks, and 3 * 4 = 12.</p>")
        self.assertEqual(self.rp(FIXTURES[15]), "")
        self.assertEqual(self.rp(FIXTURES[-2]), '<p>fenced words</p><ul class="rd-list"><li>x</li></ul>')
        # a fence line between bullets says nothing, so the list is not broken by it
        self.assertEqual(self.rp(FIXTURES[-1]), '<ul class="rd-list"><li>one</li><li>two</li><li>three</li></ul>')

    def test_the_old_contract_holds(self):
        out = self.rp(FIXTURES[1])
        self.assertIn('<a class="ts" href="/app/m/x#t6775">[1:52:55]</a>', out)
        self.assertIn('<a class="ts" href="/app/m/x#t184">[3:04]</a>', out)
        self.assertIn("&amp; again", out)
        self.assertEqual(out.count("<p>"), 2)
        self.assertEqual(self.rp(""), "")

    def test_a_limit_keeps_whole_lines_and_never_ends_mid_receipt(self):
        from web.charts import receipt_paras
        text = "First line with [1:00:00] a receipt.\n" + ("word " * 400) + "\nThird."
        out = receipt_paras(text, "", limit=120)
        self.assertEqual(out, '<p>First line with <a class="ts" href="#t3600">[1:00:00]</a> a receipt.</p>')
        long_first = "[2:00] " + ("word " * 400)
        out = receipt_paras(long_first, "", limit=100)
        self.assertTrue(out.startswith('<p><a class="ts" href="#t120">[2:00]</a> word'), out)
        self.assertTrue(out.endswith("…</p>"), out)

    def test_the_js_twin_answers_byte_for_byte(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        from web.charts import receipt_paras
        js = (REPO / "web" / "static" / "app.js").read_text(encoding="utf-8")
        esc = re.search(r"  const esc = s => .+?\n.+?\n", js).group(0)
        hms = re.search(r"  const hms = t => \{.+?\};\n", js, re.S).group(0)
        body = re.search(r"  const RD_BULLET = .+?\n  function receiptParas\(text, hrefBase\) \{.+?\n  \}\n", js, re.S)
        self.assertTrue(body, "receiptParas and its helpers moved — re-point the twin")
        prog = (esc + hms + body.group(0)
                + "const F = JSON.parse(require('fs').readFileSync(0, 'utf8'));"
                  "console.log(JSON.stringify(F.map(([t, b]) => receiptParas(t, b))));")
        cases = [(t, b) for t in FIXTURES for b in ("/app/m/x", "")]
        r = subprocess.run([node, "-e", prog], input=json.dumps(cases), capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        got = json.loads(r.stdout)
        for (t, b), js_out in zip(cases, got):
            self.assertEqual(js_out, receipt_paras(t, b), f"the twins differ on {t!r}")


if __name__ == "__main__":
    unittest.main()
