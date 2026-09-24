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
        from tests.test_llm_names import _restore_env
        self.addCleanup(_restore_env, saved)
        with llm._LEDGER_LOCK:
            self._saved = llm._LEDGER[:]
            llm._LEDGER.clear()

        def _restore():
            with llm._LEDGER_LOCK:
                llm._LEDGER[:] = self._saved
        self.addCleanup(_restore)

    def serve(self, provider, bodies, key, model="m-test"):
        api = _FakeAPI(bodies)
        self.addCleanup(api.close)
        (Path(self.td.name) / "llm.json").write_text(json.dumps({
            "api_key": key, "provider": provider, "model": model, "base_url": api.base}))
        return api

    def test_gemini_asks_for_the_answer_plus_a_short_thought(self):
        whole = {"candidates": [{"content": {"parts": [{"text": "A whole answer."}]}, "finishReason": "STOP"}]}
        cases = [("gemini-3.6-flash", 400 + self.llm.GEMINI_THINKING_ROOM, {"thinkingLevel": "low"}),
                 ("gemini-2.5-flash", 400 + self.llm.GEMINI_THINKING_ROOM, {"thinkingBudget": 1024}),
                 # a model that does not think is sent neither: an 8,192-cap model refuses the bigger number
                 ("gemini-2.0-flash", 400, None), ("gemma-3-27b", 400, None)]
        for model, want_max, want_think in cases:
            with self.subTest(model):
                api = self.serve("gemini", [whole], "AIza-x", model=model)
                self.assertEqual(self.llm.complete("q", max_tokens=400), "A whole answer.")
                cfg = api.reqs[-1]["body"]["generationConfig"]
                self.assertEqual(cfg["maxOutputTokens"], want_max)
                self.assertEqual(cfg.get("thinkingConfig"), want_think)
        self.assertGreaterEqual(self.llm.GEMINI_THINKING_ROOM, 4096)

    def test_a_name_this_file_does_not_know_still_gets_the_room(self):
        """Google's own aliases (gemini-flash-latest) and any model newer than
        this file are thinkers: without the room the summary is "At the
        September 22, 2026," again, every answer is refused, and a repair
        under that name would remove every draft (a re-review catch). Only a
        family known not to think goes without."""
        whole = {"candidates": [{"content": {"parts": [{"text": "Whole."}]}, "finishReason": "STOP"}]}
        for model, want_max in (("gemini-flash-latest", 400 + self.llm.GEMINI_THINKING_ROOM),
                                ("gemini-pro-latest", 400 + self.llm.GEMINI_THINKING_ROOM),
                                ("gemini-4-flash", 400 + self.llm.GEMINI_THINKING_ROOM),
                                ("gemini-1.5-flash", 400), ("gemini-pro", 400), ("gemma-3-27b-it", 400)):
            with self.subTest(model):
                api = self.serve("gemini", [whole], "AIza-x", model=model)
                self.llm.complete("q", max_tokens=400)
                cfg = api.reqs[-1]["body"]["generationConfig"]
                self.assertEqual(cfg["maxOutputTokens"], want_max)
                # the field a thinker takes is known only for the families named
                self.assertEqual(cfg.get("thinkingConfig"),
                                 {"thinkingLevel": "low"} if model.startswith("gemini-3") else None)

    def test_a_blocked_prompt_says_why_and_is_not_a_fragment(self):
        """Nothing was answered, so nothing may be kept — and the reason
        reaches the night's log instead of "the API answered with no text"."""
        self.serve("gemini", [{"promptFeedback": {"blockReason": "SAFETY"}}], "AIza-x", model="gemini-3.6-flash")
        with self.assertRaises(RuntimeError) as cm:
            self.llm.complete("q")
        self.assertNotIsInstance(cm.exception, self.llm.CutOff)
        self.assertIn("declined the prompt (SAFETY)", str(cm.exception))

    def test_only_a_whole_answer_stop_passes(self):
        """A length cut is not the only fragment: a safety or recitation stop,
        a filter, a refusal part way all end an answer early (a review catch)."""
        cases = [("gemini", "AIza-x", {"candidates": [{"content": {"parts": [{"text": "At the"}]}, "finishReason": r}]}, r)
                 for r in ("SAFETY", "RECITATION", "OTHER", "PROHIBITED_CONTENT", "SPII", "LANGUAGE", "BLOCKLIST")]
        cases += [("openai", "sk-x", {"choices": [{"message": {"content": "During"}, "finish_reason": "content_filter"}]}, "content_filter"),
                  ("anthropic", "sk-ant-x", {"content": [{"type": "text", "text": "The"}], "stop_reason": "refusal"}, "refusal"),
                  ("anthropic", "sk-ant-x", {"content": [{"type": "text", "text": "The"}],
                                             "stop_reason": "model_context_window_exceeded"}, "model_context_window_exceeded")]
        for prov, key, body, reason in cases:
            with self.subTest(f"{prov} {reason}"):
                self.serve(prov, [body], key, model="gemini-3.6-flash" if prov == "gemini" else "m")
                with self.assertRaises(self.llm.CutOff) as cm:
                    self.llm.complete("q")
                self.assertEqual(cm.exception.reason, reason)
                self.assertIn(reason, str(cm.exception))
        # the whole-answer stops pass, said or unsaid
        for prov, key, body in [("gemini", "AIza-x", {"candidates": [{"content": {"parts": [{"text": "Whole."}]}}]}),
                                ("openai", "sk-x", {"choices": [{"message": {"content": "Whole."}, "finish_reason": "stop"}]}),
                                ("anthropic", "sk-ant-x", {"content": [{"type": "text", "text": "Whole."}], "stop_reason": "end_turn"}),
                                ("anthropic", "sk-ant-x", {"content": [{"type": "text", "text": "Whole."}], "stop_reason": "stop_sequence"})]:
            with self.subTest(f"{prov} whole"):
                self.serve(prov, [body], key)
                self.assertEqual(self.llm.complete("q"), "Whole.")

    def test_a_cut_translation_keeps_its_whole_lines(self):
        """A chunk cut at its limit used to lose all forty lines to the
        source language (or keep the half line as a caption); the whole lines
        before the cut are kept, the half line and the rest fall back."""
        from czcore import mt
        cues = [{"start": float(i), "end": float(i) + 1, "text": f"line {i}"} for i in range(5)]

        def cut(prompt, system="", max_tokens=0, **kw):
            raise self.llm.CutOff("the answer was cut off at its length limit — a fragment is not an answer",
                                  "0|línea 0\n1|línea 1\n2|línea 2\n3|lín", "MAX_TOKENS")
        out = mt.translate_cues(cues, "es", complete=cut)
        self.assertEqual([c["text"] for c in out], ["línea 0", "línea 1", "línea 2", "line 3", "line 4"])
        self.assertEqual([bool(c.get("fallback")) for c in out], [False, False, False, True, True])

        def boom(prompt, system="", max_tokens=0, **kw):
            raise RuntimeError("rate limited by the API (429) — wait a moment and retry")
        out = mt.translate_cues(cues, "es", complete=boom)
        self.assertTrue(all(c.get("fallback") for c in out))

        # a cut that ended on a line break ended on a whole line: it is kept
        def at_break(prompt, system="", max_tokens=0, **kw):
            raise self.llm.CutOff("cut", "0|línea 0\n1|línea 1\n2|línea 2\n", "MAX_TOKENS")
        out = mt.translate_cues(cues, "es", complete=at_break)
        self.assertEqual([c["text"] for c in out], ["línea 0", "línea 1", "línea 2", "line 3", "line 4"])

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
                                                     "finishReason": "MAX_TOKENS"}]}], "AIza-x", model="gemini-3.6-flash")
        with self.assertRaises(RuntimeError) as cm:
            self.llm.complete_vision("what is this", "QUJD", max_tokens=300)
        # the desk's Narrator shows this sentence: said right
        self.assertIn("a fragment is not a whole description", str(cm.exception))
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
        # the reason, and the exception itself (the repair tells a cut from a failure by it)
        self.assertIn("cut off", analyze.LAST_FALLBACK["summary"])
        self.assertIsInstance(analyze.LAST_ERROR["draft"], RuntimeError)
        # a call with nothing to ask clears the last one's reason, never reports it stale
        analyze.summary([], {})
        analyze.draft([], {})
        self.assertEqual((analyze.LAST_FALLBACK, analyze.LAST_ERROR),
                         ({"summary": "", "draft": ""}, {"summary": None, "draft": None}))

    def test_the_nights_reading_line_goes_through_the_job(self):
        """The ingest is the desk's engine too: a print there ignored quiet
        (the pipeline's --json broke) and could fail a meeting on a closed
        pipe — the line is the job's message, like every stage's."""
        src = (REPO / "memory" / "ingest.py").read_text()
        self.assertNotIn("print(", src)
        self.assertIn('job.message = (f"the reading — summary {summ_origin}', src)

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
    "**The Select Board sends the $4.2M operating override to the November 4 ballot xx🗳**",
    "x **" + "💰" * 101 + "** y",
    "**" + "😀" * 41 + "**",
    "* * *\n- - -\n_ _ _\n## \n•  •",
    "a" + " " * 3000 + "x" + "\t" * 2000,
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
        fence = next(f for f in FIXTURES if f.startswith("```\nfenced words"))
        self.assertEqual(self.rp(fence), '<p>fenced words</p><ul class="rd-list"><li>x</li></ul>')
        # a fence line between bullets says nothing, so the list is not broken by it
        split = next(f for f in FIXTURES if f.startswith("* one\n* two"))
        self.assertEqual(self.rp(split), '<ul class="rd-list"><li>one</li><li>two</li><li>three</li></ul>')

    def test_a_limited_lede_is_never_only_a_heading_nor_cut_mid_receipt(self):
        from web.charts import receipt_paras
        para = "The board voted on the override " + "and the budget " * 60 + "[1:00:00]."
        out = receipt_paras("**What it means**  \n" + para, "", limit=900)
        self.assertIn('<p class="rd-h">What it means</p><p>The board voted', out)   # the heading does not spend the cut
        self.assertTrue(out.endswith("…</p>"), out)
        self.assertEqual(receipt_paras("```\n" + para + "\n```", "", limit=900)[:12], "<p>The board")
        # a lede never ends on a heading
        self.assertNotIn("rd-h", receipt_paras("First line.\n**Next heading**\n" + para, "", limit=400))
        # a cut inside a receipt group drops the group whole
        text = "The board took up items " + "x " * 180 + "[12:12, 17:13] and more words after the receipt group"
        out = receipt_paras(text, "", limit=390)
        self.assertNotIn("[12:12", out)
        self.assertTrue(out.endswith("…</p>"), out)

    def test_the_lede_cut_keeps_prose_brackets_and_never_ends_on_a_label(self):
        """Re-review catches: an unclosed bracket of words ("[inaudible") took
        the whole lede with it; a bullet that is only a bold label, or a bare
        bullet, counted as words and ended the lede; a summary that was one
        bold headline pressed as nothing."""
        from web.charts import receipt_paras
        long = "The chair [inaudible opened the meeting. " + "and then the board spoke " * 60
        out = receipt_paras(long, "/app/m/x", limit=900)
        self.assertTrue(out.startswith("<p>The chair [inaudible opened the meeting."), out[:80])
        self.assertGreater(len(out), 700)
        # an unclosed RECEIPT at the cut still goes whole
        cut = receipt_paras("The board voted " + "x" * 880 + " [12:12, 17", "", limit=900)
        self.assertNotIn("[12:12", cut)
        sub = "a" * 298 + "."
        labels = f"* **What it means:**\n  * {sub}\n* **Who moved it:**\n  * {sub}\n* **What to watch:**\n  * {sub}"
        out = receipt_paras(labels, "", limit=900)
        self.assertFalse(re.search(r"<b>(What it means|Who moved it|What to watch):</b></li></ul>$", out), out[-80:])
        self.assertTrue(out.endswith(f"<li>{sub}</li></ul>"), out[-80:])
        # a bare bullet renders nothing, so it is no words: the paragraph after it stands
        self.assertIn("<p>" + "b" * 50, receipt_paras("- `\n" + "b" * 1000, "", limit=900))
        tail = receipt_paras("The board met [1:00].\n**Who moved it:**\n- `", "", limit=900)
        self.assertEqual(tail, '<p>The board met <a class="ts" href="#t60">[1:00]</a>.</p>')
        # a lone label paragraph is a heading, too
        self.assertNotIn("What to watch", receipt_paras("The board met.\nWhat to watch:", "", limit=900))
        # one bold headline IS the summary — pressed as its words, receipt linked
        for head in ("**The Select Board sends the override to the November ballot [1:12:24].**",
                     "# The Select Board sends the override to the November ballot [1:12:24]."):
            out = receipt_paras(head, "/app/m/x", limit=900)
            self.assertTrue(out.startswith("<p>The Select Board sends the override"), out)
            self.assertIn('href="/app/m/x#t4344"', out)
        # and nothing but labels says nothing
        self.assertEqual(receipt_paras("**Who moved it:**\n## What to watch", "", limit=900), "")

    def test_the_lede_keeps_bold_decisions_and_a_headline_that_starts_with_a_label(self):
        """A second re-review's catches of the first fold: a bullet that is all
        bold ("* **Approved the override [1:12:24]**") is a decision, not a
        heading — the lede dropped them (10.5k of 120k fuzz cases lost
        items); a headline that starts with a label is words; a heading-only
        summary is pressed as a paragraph, never a head; a too-long line of
        bare syntax before any words no longer ends the lede empty."""
        from web.charts import receipt_paras
        rp = lambda t: receipt_paras(t, "/m", limit=900)
        out = rp("The Select Board met to take up the override [0:10].\n* **Approved the override for the ballot [1:12:24]**\n"
                 "* **Rejected the parking plan [2:03:00]**")
        self.assertIn('<li><b>Approved the override for the ballot <a class="ts" href="/m#t4344">[1:12:24]</a></b></li>', out)
        self.assertTrue(out.endswith('<li><b>Rejected the parking plan <a class="ts" href="/m#t7380">[2:03:00]</a></b></li></ul>'), out)
        self.assertIn("<li><b>Parking: rejected</b></li></ul>", rp("Decisions tonight:\n- **Override: to the ballot [1:12:24]**\n- **Parking: rejected**"))
        self.assertTrue(rp("**What it means: the town will borrow $10M for the school [1:00].**")
                        .startswith("<p><b>What it means:</b> the town will borrow $10M"))
        self.assertEqual(rp("## **The Select Board sent the override to the ballot.**"),
                         "<p>The Select Board sent the override to the ballot.</p>")
        self.assertEqual(rp("**`**\n# The Select Board sent the override to the ballot."),
                         "<p>The Select Board sent the override to the ballot.</p>")
        self.assertEqual(rp("`" * 1000 + "\nThe board voted to adopt the budget."), "<p>The board voted to adopt the budget.</p>")
        self.assertEqual(rp("The board met.\n*What to watch:*"), "<p>The board met.</p>")
        self.assertEqual(rp("The board met.\n**What to watch**:"), "<p>The board met.</p>")

    def test_spaced_rules_and_bare_markers_say_nothing(self):
        from web.charts import receipt_paras
        self.assertEqual(receipt_paras("* * *\n- - -\n_ _ _\n## \n•  •", ""), "")

    def test_a_long_run_of_spaces_is_trimmed_in_linear_time(self):
        import time
        from web.charts import receipt_paras
        t0 = time.time()
        out = receipt_paras("a" + " " * 200000 + "x" + " \t" * 100000, "")
        self.assertLess(time.time() - t0, 1.0)
        self.assertTrue(out.startswith("<p>a") and out.endswith("x</p>"))

    def test_the_tapes_own_sentences_are_never_read_as_markdown(self):
        """An extractive summary is the tape's words verbatim: "- " is a dash,
        "*" a star, "# 1" a number — only its receipts are linked."""
        from web.charts import receipt_paras
        out = receipt_paras("- we start. f*** that # 1 priority *really* [1:05]", "", plain=True)
        self.assertEqual(out, '<p>- we start. f*** that # 1 priority *really* <a class="ts" href="#t65">[1:05]</a></p>')
        self.assertEqual(receipt_paras("## heading line", "", plain=True), "<p>## heading line</p>")

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



class TestTheModelsWordsAreLabeledWhereTheyAreRead(unittest.TestCase):
    """The folds' own receipts: a kit whose copy says "no model" never takes a
    model's summary as its brief; a stored "what changed" a model wrote is
    never pressed unlabeled; a receipt that names no line's first second
    still lands on the line it falls in."""

    def test_a_kit_takes_the_tapes_sentences_not_a_models_summary(self):
        from web.kit import kit_from_meeting
        segs = [{"start": float(i * 10), "end": float(i * 10 + 9), "text": t, "speaker": ""} for i, t in enumerate(
            ["We open the meeting on the override.", "The board votes to put the override on the ballot.",
             "Public comment follows on the budget.", "The motion carries unanimously.", "We adjourn."])]
        moments = [{"t": 10.0, "start": 10.0, "end": 20.0, "quote": "The board votes", "score": 0.9, "kind": "vote"}]
        base = {"pid": "k1", "title": "Select Board — 2026-03-10", "date": "2026-03-10", "video_id": "k1", "url": "u",
                "town": "Testville", "body": "Select Board", "segments": segs, "moments": moments, "analysis": {},
                "duration": 60.0}
        ai = kit_from_meeting({**base, "summary": "**What it means** A model wrote this.", "summary_origin": "ai:gemini-3.6-flash"})
        ex = kit_from_meeting({**base, "summary": "The tape's own words.", "summary_origin": "extractive"})
        self.assertIsNotNone(ai)
        blob = json.dumps(ai)
        self.assertNotIn("A model wrote this", blob)
        self.assertNotIn("**", blob)
        self.assertIn("no model", blob)
        self.assertIn("The tape's own words", json.dumps(ex))

    def test_a_stored_model_delta_is_pressed_as_the_counted_line(self):
        from memory.store import Corpus
        from web import bake
        with tempfile.TemporaryDirectory() as d:
            db = Path(d) / "c.db"
            c = Corpus(str(db))
            c.replace_segments("m1", [{"start": 0.0, "end": 5.0, "speaker": "", "text": "the override"}])
            c.upsert_meeting({"id": "m1", "title": "Select Board — 2026-09-22", "date": "2026-09-22", "town": "T",
                              "body": "Select Board", "source_kind": "youtube", "video_id": "m1", "url": "u",
                              "url_canon": "youtube:m1", "duration": 5.0, "n_segments": 1, "status": "live",
                              "summary": "", "analysis_json": "{}"})
            c.upsert_issue({"id": "issue:t:override", "town": "T", "name": "Override", "status": "active",
                            "keywords": ["override"], "aliases": [], "related": []})
            c.add_event("resurfacing", issue_id="issue:t:override", meeting_id="m1",
                        payload={"delta": "The September 22, 202", "title": "Select Board — 2026-09-22",
                                 "date": "2026-09-22", "body": "Select Board"})
            c.add_event("resurfacing", issue_id="issue:t:override", meeting_id="m1",
                        payload={"delta": "“Override” returned. That is 2 appearances on the record.",
                                 "title": "Select Board — 2026-09-22", "date": "2026-09-22", "body": "Select Board"})
            out = Path(d) / "app"
            bake.bake(str(db), str(out), "9.9.9", "https://example.org")
            home = (out / "index.html").read_text()
        self.assertNotIn("The September 22, 202<", home)
        self.assertIn("“Override” returned at Select Board — 2026-09-22 (Select Board · 2026-09-22).", home)
        self.assertIn("“Override” returned. That is 2 appearances on the record.", home)   # the extractive one stands

    def test_a_renamed_thread_keeps_its_history_and_a_forgotten_one_is_gone(self):
        """The press judged a stored "what changed" by the thread's CURRENT
        name: a steward's rename replaced every earlier paragraph — its arc
        and its quotes — with the bare counted line (a re-review catch). The
        shape decides, not the name."""
        from web.bake import _EXTRACTIVE_DELTA
        old_name = ("“Operating override” returned at Select Board — 2026-09-22 (Select Board · 2026-09-22). "
                    "That is 3 appearances on the record since 2026-06-01. This time: [00:05] the override")
        self.assertTrue(_EXTRACTIVE_DELTA.match(old_name))
        self.assertTrue(_EXTRACTIVE_DELTA.match("“A “quoted” name” returned. That is 1 appearance on the record."))
        for model in ("The September 22, 202", "At the meeting the override returned. That is 3 appearances on the record.",
                      "“Override” was discussed again.", ""):
            self.assertFalse(_EXTRACTIVE_DELTA.match(model), model)
        src = (REPO / "web" / "bake.py").read_text()
        self.assertIn('name = e.get("issue_name") or ""\n                if not name:\n                    continue', src)

    def test_a_receipt_lands_on_the_line_it_falls_in(self):
        node = shutil.which("node")
        if not node:
            self.skipTest("node not available")
        js = (REPO / "web" / "static" / "app.js").read_text(encoding="utf-8")
        fn = re.search(r"  function rowAt\(sec\) \{.+?\n  \}\n", js, re.S).group(0)
        prog = ("const rows = [0, 12.4, 30, 55.9].map(t => ({ id: 't' + Math.floor(t), dataset: { t: String(t) } }));"
                "const document = { getElementById: id => rows.find(r => r.id === id) || null };"
                "let END = '62'; const $ = s => s === '.meeting' ? { dataset: { end: END } } : null;"
                "const $$ = () => rows;" + fn +
                "const at = s => { const a = rowAt(s); return a ? [a.row.id, a.exact] : null; };"
                "const known = [12, 13, 29, 30, 31, 60, 64, 999, -5].map(at);"
                "END = ''; const unknown = [999].map(at);"
                "console.log(JSON.stringify([known, unknown]));")
        r = subprocess.run([node, "-e", prog], capture_output=True, text=True)
        self.assertEqual(r.returncode, 0, r.stderr)
        known, unknown = json.loads(r.stdout)
        # a time past the tape's end (a model's [264:28] on a three-hour tape)
        # names no line — and the player is not primed past the end (a re-review catch)
        self.assertEqual(known, [["t12", True], ["t12", False], ["t12", False], ["t30", True],
                                 ["t30", False], ["t55", False], None, None, None])
        self.assertEqual(unknown, [["t55", False]])          # a page that does not say where it ends: as before
        emit = (REPO / "web" / "emit.py").read_text()
        self.assertIn('data-end="{tape_end}"', emit)


class TestTheRepairAsksAgainOnlyForFragments(unittest.TestCase):
    """record/repair.py — the one-off that asks again for what the old budget
    cut: it must touch fragments and nothing else, and be safe to re-run."""

    def test_a_fragment_is_cut_and_a_whole_answer_is_not(self):
        from record.repair import is_cut
        for t in ("At the September 22, 2026,", "During the", "vote on", "[13:"):
            self.assertTrue(is_cut(t), t)
        for t in ("The board voted.", "Was it passed?", "… [264:28][279:55].", "facing the town [279:55]",
                  "(G.)", "“Adjourned.”", "", "   "):
            self.assertFalse(is_cut(t), t)

    def test_the_plan_names_only_what_the_old_budget_cut(self):
        from record.repair import plan
        rows = [
            {"id": "a", "summary": "At the September 22, 2026,", "summary_origin": "ai:gemini-3.6-flash",
             "analysis_json": json.dumps({"draft": {"text": "**What it means**\nThe board focused on", "origin": "ai:gemini-3.6-flash"}})},
            # an older model's whole summary, and a draft that is whole: kept
            {"id": "b", "summary": "The board met [1:00:00].", "summary_origin": "ai:gpt-4o-mini",
             "analysis_json": json.dumps({"draft": {"text": "What it means: a plan [1:00].", "origin": "ai:gemini-3.6-flash"}})},
            # a cut extractive summary is the tape's own words, never asked of a model here
            {"id": "c", "summary": "and then the", "summary_origin": "extractive", "analysis_json": "{}"},
            # whole prose that still shows Markdown is asked again; a cut desk-model summary is not Gemini's to redo
            {"id": "d", "summary": "Fine.", "summary_origin": "ai:gemini-3.6-flash",
             "analysis_json": json.dumps({"draft": {"text": "**Who moved it:** the chair.", "origin": "ai:gemini-3.6-flash"}})},
            {"id": "e", "summary": "The board", "summary_origin": "ai:gpt-4o-mini", "analysis_json": "not json"},
        ]
        self.assertEqual(plan(rows), [{"id": "a", "want": ["summary", "draft"]}, {"id": "d", "want": ["draft"]}])
        # after a repair the same rows plan nothing: safe to re-run
        fixed = [{**rows[0], "summary": "The board met.", "analysis_json": json.dumps(
            {"draft": {"text": "What it means: whole.", "origin": "ai:gemini-3.6-flash"}})}]
        self.assertEqual(plan(fixed), [])

    def test_before_the_fix_everything_the_budget_wrote_is_asked_again(self):
        """A fragment that happens to end on a bracketed receipt looks whole
        ("…the override [1:12:24]") — so everything a Gemini lane wrote before
        the fixed image is asked again, and a live meeting with no draft is
        filled; a row repaired since is newer than the cutoff and left alone."""
        from record.repair import plan, _when
        cutoff = _when("2026-09-24T03:00Z")
        self.assertEqual(cutoff, _when(str(cutoff)))
        looks_whole = json.dumps({"draft": {"text": "What it means: the board took up the override [1:12:24]",
                                            "origin": "ai:gemini-3.6-flash"}})
        rows = [
            {"id": "a", "summary": "The board met [279:55].", "summary_origin": "ai:gemini-3.6-flash",
             "analysis_json": looks_whole, "updated_at": cutoff - 3600},
            {"id": "b", "summary": "Whole.", "summary_origin": "ai:gpt-4o-mini", "analysis_json": "{}",
             "updated_at": cutoff - 3600},
            {"id": "c", "summary": "Whole.", "summary_origin": "ai:gemini-3.6-flash", "analysis_json": looks_whole,
             "updated_at": cutoff + 60},
        ]
        self.assertEqual(plan(rows, cutoff), [{"id": "a", "want": ["summary", "draft"]}, {"id": "b", "want": ["draft"]}])
        self.assertEqual(plan(rows), [])          # without the cutoff, only true fragments

    # -- the run: only a cut licenses a fallback; a failed call changes nothing

    SEGS = [{"start": 10.0 * i, "end": 10.0 * i + 8, "text": t} for i, t in enumerate([
        "Good evening, this meeting of the Select Board will come to order.",
        "The first item tonight is the proposed operating override for the November ballot.",
        "The town administrator presented the budget gap of four point two million dollars.",
        "Several residents spoke in favor of placing the override question before the voters.",
        "The board discussed whether the override should fund the schools or the operating budget.",
        "A motion was made to place the override on the November ballot and it was seconded.",
        "The motion carries unanimously and the override question goes to the voters in November.",
        "The next item is the reserve fund transfer requested by the department of public works.",
    ])]

    live = {"m0", "m1", "m2", "n0", "x", "e0", "rw"}
    bare = {"e0"}
    moved = {"rw": 5.0}              # rewritten (updated_at moved) while the run asked

    def run_repair(self, rows, todo, complete, probe=False):
        import contextlib
        import io
        from record import repair
        from memory import analyze
        writes, segs = [], self.SEGS

        live, moved = self.live, self.moved

        class Store:
            def transcript(self, mid):
                return [] if mid in self.bare else segs

            def get_meeting(self, mid):
                return {"id": mid, "status": "live" if mid in live else "forgotten",
                        "updated_at": moved.get(mid, 0)}

            def upsert_meeting(self, row):
                writes.append(row)
        Store.bare = self.bare
        buf = io.StringIO()
        with mock.patch.object(repair, "PAUSE", 0), \
             mock.patch.object(analyze.llm, "enabled", lambda: True), \
             mock.patch.object(analyze.llm, "complete", complete), \
             mock.patch.object(analyze.llm, "status", lambda: {"model": "gemini-3.6-flash"}), \
             contextlib.redirect_stdout(buf):
            r = repair.repair(Store(), rows, todo, probe=probe)
        return r, writes, buf.getvalue()

    def rows(self, n=3):
        an = json.dumps({"brief": [{"t": 10, "text": "kept"}],
                         "draft": {"text": "What it means: the board", "origin": "ai:gemini-3.6-flash"}})
        return [{"id": f"m{i}", "title": "T", "summary": "At the September 22, 2026,",
                 "summary_origin": "ai:gemini-3.6-flash", "analysis_json": an} for i in range(n)]

    def test_a_failed_call_changes_nothing_and_the_run_stops(self):
        """A quota, a bad key, a request the API refused, a timeout: the old
        repair wrote the extractive summary over every Gemini summary and
        removed every draft, said REPAIR DONE and exited 0 — and no re-run
        could put it back (a re-review catch, the gravest). Now the row stays
        as stored, two such meetings in a row stop the run, and it fails."""
        rows = self.rows(3)
        todo = [{"id": m["id"], "want": ["summary", "draft"]} for m in rows]

        def quota(*a, **k):
            raise RuntimeError("rate limited by the API (429) — wait a moment and retry")
        r, writes, out = self.run_repair(rows, todo, quota)
        self.assertEqual(writes, [])
        self.assertEqual((r["fixed"], r["kept"], r["failed"]), (0, 2, 2))
        self.assertIn("429", r["stopped"])
        self.assertIn("REPAIR STOPPED — 2 meetings in a row could not be asked", out)
        self.assertNotIn("m2", out)                        # the third was never asked
        self.assertIn("could not be asked — kept as stored", out)
        self.assertIn("no call answered", out)             # never the last call's numbers

    def test_a_cut_answer_twice_is_the_extractive_summary_and_no_draft(self):
        from czcore import llm
        rows = self.rows(1)

        def cut(*a, **k):
            raise llm.CutOff("the answer was cut off at its length limit — a fragment is not a whole answer",
                             "At the", "MAX_TOKENS")
        r, writes, out = self.run_repair(rows, [{"id": "m0", "want": ["summary", "draft"]}], cut)
        self.assertEqual((r["fixed"], r["failed"]), (1, 0))
        w = writes[0]
        self.assertEqual(w["summary_origin"], "extractive")
        self.assertTrue(w["summary"].strip())                               # the tape's own sentences
        an = json.loads(w["analysis_json"])
        self.assertNotIn("draft", an)
        self.assertEqual(an["brief"], [{"t": 10, "text": "kept"}])       # the rest of the reading untouched
        # the row as it stood is in the log, before it changed
        lines = out.splitlines()
        b = next(i for i, ln in enumerate(lines) if ln.strip().startswith("BACKUP "))
        u = next(i for i, ln in enumerate(lines) if ln.startswith("UPDATED "))
        self.assertLess(b, u)
        backup = json.loads(lines[b].strip()[len("BACKUP "):])
        self.assertEqual(backup["summary"], "At the September 22, 2026,")
        self.assertEqual(backup["draft"]["text"], "What it means: the board")

    def test_a_whole_answer_is_written_and_nothing_else_is(self):
        rows = self.rows(1)
        r, writes, out = self.run_repair(rows, [{"id": "m0", "want": ["summary", "draft"]}],
                                         lambda *a, **k: "The board met [00:10].")
        self.assertEqual(writes[0]["summary"], "The board met [00:10].")
        self.assertEqual(writes[0]["summary_origin"], "ai:gemini-3.6-flash")
        self.assertEqual(json.loads(writes[0]["analysis_json"])["draft"],
                         {"text": "The board met [00:10].", "origin": "ai:gemini-3.6-flash"})
        # a meeting with no draft whose ask comes back cut has nothing to change: no write
        from czcore import llm
        bare = [{"id": "n0", "title": "T", "summary": "", "summary_origin": "extractive", "analysis_json": "{}"}]

        def cut(*a, **k):
            raise llm.CutOff("cut", "At", "MAX_TOKENS")
        r, writes, out = self.run_repair(bare, [{"id": "n0", "want": ["draft"]}], cut)
        self.assertEqual((writes, r["kept"], r["fixed"]), ([], 1, 0))
        self.assertNotIn("UPDATED", out)

    def test_a_meeting_is_written_whole_or_not_at_all(self):
        """A summary written and a draft that failed would leave the draft's
        fragment on the record for good: the row is newer than the cutoff
        and no run would plan it again (a second re-review's catch). Now
        neither half is written, and the next run asks for both."""
        rows = self.rows(1)
        calls = []

        def summary_whole_draft_quota(prompt, system="", **k):
            calls.append(system[:20])
            if "reading" in system:
                raise RuntimeError("rate limited by the API (429) — wait a moment and retry")
            return "The board met [00:10]."
        r, writes, out = self.run_repair(rows, [{"id": "m0", "want": ["summary", "draft"]}], summary_whole_draft_quota)
        self.assertEqual(writes, [])
        self.assertEqual((r["fixed"], r["kept"], r["failed"]), (0, 1, 1))
        self.assertIn("HELD m0", out)
        self.assertNotIn("UPDATED", out)

    def test_a_fallback_needs_every_ask_refused_as_a_fragment(self):
        """A timeout and then one cut is not "refused twice": the stored
        draft stays (a second re-review's catch)."""
        from czcore import llm
        seq = iter([RuntimeError("couldn't reach the API (timed out)"), llm.CutOff("cut", "At", "MAX_TOKENS")] * 2)

        def complete(*a, **k):
            raise next(seq)
        r, writes, out = self.run_repair(self.rows(1), [{"id": "m0", "want": ["draft"]}], complete)
        self.assertEqual((writes, r["failed"]), ([], 1))
        self.assertNotIn("refused twice", out)

    def test_another_models_whole_draft_is_not_asked_again_for_its_age(self):
        from record.repair import plan
        gpt = json.dumps({"draft": {"text": "What it means: whole.", "origin": "ai:gpt-4o-mini"}})
        cut = json.dumps({"draft": {"text": "What it means: the", "origin": "ai:gpt-4o-mini"}})
        rows = [{"id": "g", "summary": "", "summary_origin": "extractive", "analysis_json": gpt, "updated_at": 0},
                {"id": "c", "summary": "", "summary_origin": "extractive", "analysis_json": cut, "updated_at": 0}]
        self.assertEqual(plan(rows, 100.0), [{"id": "c", "want": ["draft"]}])

    def test_no_transcript_is_skipped_a_probe_counts_its_failures_and_a_forgotten_meeting_is_not_rewritten(self):
        from czcore import llm
        rows = [{"id": "e0", "title": "T", "summary": "At", "summary_origin": "ai:gemini-3.6-flash", "analysis_json": "{}"}]
        r, writes, out = self.run_repair(rows, [{"id": "e0", "want": ["summary"]}], lambda *a, **k: "Whole.")
        self.assertEqual((writes, r["failed"], r["kept"]), ([], 0, 1))
        self.assertIn("SKIP e0 — no transcript", out)

        def quota(*a, **k):
            raise RuntimeError("rate limited by the API (429) — wait a moment and retry")
        r, writes, out = self.run_repair(self.rows(1), [{"id": "m0", "want": ["summary"]}], quota, probe=True)
        self.assertEqual((writes, r["failed"]), ([], 1))              # the probe's exit says it failed
        self.assertIn("SUMMARY m0 none 0 chars", out)                # never the fallback it did not write
        gone = [{**self.rows(1)[0], "id": "zz"}]
        r, writes, out = self.run_repair(gone, [{"id": "zz", "want": ["summary"]}], lambda *a, **k: "Whole.")
        self.assertEqual(writes, [])
        self.assertIn("GONE zz", out)
        # a meeting rewritten while it was asked keeps its new reading (a final review's catch)
        moved = [{**self.rows(1)[0], "id": "rw", "updated_at": 0}]
        r, writes, out = self.run_repair(moved, [{"id": "rw", "want": ["summary", "draft"]}], lambda *a, **k: "Whole.")
        self.assertEqual(writes, [])
        self.assertIn("CHANGED rw", out)
        # a probe asks the first planned meeting that HAS a transcript
        two = [{"id": "e0", "title": "T", "summary": "At", "summary_origin": "ai:gemini-3.6-flash", "analysis_json": "{}"},
               self.rows(1)[0]]
        r, writes, out = self.run_repair(two, [{"id": "e0", "want": ["summary"]}, {"id": "m0", "want": ["summary"]}],
                                         lambda *a, **k: "Whole.", probe=True)
        self.assertTrue(r["probed"])
        self.assertIn("SUMMARY m0 ai:gemini-3.6-flash", out)
        self.assertEqual(writes, [])

    def test_an_analysis_it_cannot_read_is_never_planned_nor_written(self):
        """The planner tolerated bad JSON and planned a draft for it; the run
        then crashed on the row, and the job's retry crashed on it again — no
        row after it was ever repaired (a re-review catch)."""
        from record.repair import plan
        for bad in ("not json", json.dumps("a string"), json.dumps([1, 2])):
            rows = [{"id": "x", "summary": "Whole.", "summary_origin": "ai:gpt-4o-mini", "analysis_json": bad,
                     "updated_at": 0}]
            self.assertEqual(plan(rows, 100.0), [], bad)
            r, writes, out = self.run_repair(rows, [{"id": "x", "want": ["draft"]}], lambda *a, **k: "Whole.")
            self.assertEqual((writes, r["failed"]), ([], 0))


if __name__ == "__main__":
    unittest.main()
