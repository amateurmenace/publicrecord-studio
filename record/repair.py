"""Ask again for the model's answers the old budget cut off (specs/28 §2.1).

Until v2.1.23 the Gemini lane's thinking spent the whole output budget, so
every hosted summary and every drafted reading was stored cut off
mid-sentence ("At the September 22, 2026,"). The seam now caps the thought,
gives it room, and refuses a cut answer; this repairs what is already
stored. It runs in the pipeline job's own image and secrets, never from a
Mac:

    # look first: what would be asked again, changing nothing
    gcloud run jobs execute record-pipeline --region=us-east1 --wait \\
      --args=-m,record.repair,--before,2026-09-24T03:00Z,--dry-run
    # one meeting, asked for real and printed, nothing written
    …--args=-m,record.repair,--before,2026-09-24T03:00Z,--probe
    # the repair
    …--args=-m,record.repair,--before,2026-09-24T03:00Z

What is asked again: every summary a Gemini lane wrote and every model
draft stored before `--before` (the fixed image's deploy) — the broken
budget wrote all of them, and a fragment that happens to end on a
bracketed receipt looks whole — plus, whenever run, a summary or draft
that ends mid-sentence or shows raw Markdown, and a live meeting with no
draft at all.

What is written: a whole answer, always. A fallback only when the model
answered twice and the seam refused both as fragments — then the summary
is the extractive one, labeled so, and a draft is removed rather than left
a fragment. A call that FAILED (a quota, a bad key, a request the API
refused, a timeout) licenses nothing: that row stays exactly as stored,
the run stops after two such meetings in a row, and it exits 1. A meeting is
written whole or not at all — if either half could not be asked, neither is
written, so a re-run asks for both. Every row's old values are printed
(BACKUP) before it is written, so a run that went wrong can be put back from
its own log. Re-runs are safe: a repaired row is newer than the cutoff. One
repair at a time (an advisory lock).
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import os
import re
import time
from typing import Iterable, List, Optional

_END = re.compile(r"[.!?…)\]”\"']\s*$")
PAUSE = 20            # seconds before the second ask (a 429 or a slow minute)
STREAK = 2            # meetings in a row that could not be asked → stop


def is_cut(text) -> bool:
    """A stored answer that stops mid-sentence: text that does not end on a
    sentence's close (a stop, a question, a bracketed receipt, a quote)."""
    t = str(text or "").strip()
    return bool(t) and not _END.search(t)


def _when(s: str) -> float:
    """--before as an ISO time (…Z allowed) or seconds since the epoch."""
    s = str(s or "").strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return _dt.datetime.fromisoformat(s.replace("Z", "+00:00")).timestamp()


def _analysis(s) -> Optional[dict]:
    """The stored analysis — or None when it cannot be read as one: nothing
    is planned or written into a row this does not understand."""
    if not s:
        return {}
    try:
        v = json.loads(s)
    except (TypeError, ValueError):
        return None
    return v if isinstance(v, dict) else None


def plan(rows: Iterable[dict], before: float = 0.0) -> List[dict]:
    """Which meetings need asking again, and for what — pure over the rows
    (`id`, `summary`, `summary_origin`, `analysis_json`, `updated_at`)."""
    out = []
    for m in rows:
        old = bool(before) and float(m.get("updated_at") or 0) < before
        want = []
        so = str(m.get("summary_origin") or "")
        if so.startswith("ai:gemini") and (old or is_cut(m.get("summary"))):
            want.append("summary")
        an = _analysis(m.get("analysis_json"))
        d = an.get("draft") if an is not None else None
        if isinstance(d, dict) and str(d.get("origin") or "").startswith("ai:"):
            dt = str(d.get("text") or "")
            # the old budget was Gemini's: another model's whole draft (a desk
            # import) is not asked again for its age — only for its own cut
            gem = str(d.get("origin") or "").startswith("ai:gemini")
            if (old and gem) or is_cut(dt) or "**" in dt:
                want.append("draft")
        elif old and an is not None:
            want.append("draft")          # a live meeting with no draft: the recovery path
        if want:
            out.append({"id": m["id"], "want": want})
    return out


def _calls() -> int:
    from czcore import llm
    return int(llm.usage_summary().get("calls") or 0)


def _spent(n0: int) -> str:
    """What the calls since `n0` cost — only calls that answered are in the
    ledger, so a failed call never borrows the last one's numbers."""
    from czcore import llm
    s = llm.usage_summary()
    new = int(s.get("calls") or 0) - n0
    if new <= 0:
        return "no call answered"
    rec = (s.get("recent") or [])[-new:]
    return (f"in {sum(e['tokens_in'] for e in rec)} out {sum(e['tokens_out'] for e in rec)}"
            + (f" over {new} calls" if new > 1 else ""))


def _ask(fn, kind: str, segs, info, tries: int = 2):
    """One call, and once more after a pause if it fell back → (text,
    origin, why, cut). `cut` is True only when EVERY ask came back and the
    seam refused each as a fragment — the one failure that licenses a
    fallback (a timeout and then one cut is not two cuts). Any other
    failure licenses nothing."""
    from czcore import llm
    from memory import analyze
    text, origin, why, cut = "", "none", "", tries > 0
    for k in range(tries):
        text, origin = fn(segs, info)
        if text and str(origin).startswith("ai:"):
            return text, origin, "", False
        why = analyze.LAST_FALLBACK.get(kind, "") or "the model gave no answer"
        cut = cut and isinstance(analyze.LAST_ERROR.get(kind), llm.CutOff)
        if k + 1 < tries:
            time.sleep(PAUSE)
    return text, origin, why, cut


def repair(c, rows: List[dict], todo: List[dict], probe: bool = False) -> dict:
    """Ask again for each planned meeting and write what the rules allow
    (the module's docstring) — `c` needs `transcript(id)`, `get_meeting(id)`
    and `upsert_meeting(row)`. A meeting is written whole or not at all: if
    either half could not be asked, neither is written, so the next run asks
    for both (a row written once is newer than the cutoff, and would never
    be planned again). Returns the counts; prints one line per call."""
    from memory import analyze
    by = {m["id"]: m for m in rows}
    fixed = kept = failed = streak = 0
    stopped, probed = "", False
    # a probe asks the first planned meeting that has a transcript (one with
    # none is skipped below, and a probe that asked nothing is no pass)
    for t in todo:
        m = by[t["id"]]
        an0 = _analysis(m.get("analysis_json"))
        an = dict(an0 or {})
        upd = {"id": m["id"]}
        bad = []
        segs = c.transcript(m["id"])
        if not segs:
            # nothing to ask a model about: not a failure, and nothing to write
            print(f"  SKIP {m['id']} — no transcript on the record; nothing asked", flush=True)
            kept += 1
            continue
        info = {"title": m.get("title") or ""}
        if "summary" in t["want"]:
            n0, t0 = _calls(), time.time()
            s, o, why, cut = _ask(analyze.summary, "summary", segs, info)
            if str(o).startswith("ai:"):
                verdict, write = "whole", True
            elif cut:
                # the model spoke twice and was refused both times: the tape's
                # own sentences stand in, labeled — or, when the tape gave
                # none, no summary at all rather than the stored fragment
                verdict, write = ("refused twice as a fragment — the extractive summary, labeled" if s
                                  else "refused twice as a fragment — the tape gave no sentences; none"), True
                s, o = s or "", "extractive"
            else:
                # nothing was said: the line shows nothing, not the fallback
                # that was never written
                verdict, write = "could not be asked — kept as stored", False
                s, o = "", "none"
                bad.append(why)
            if write and (s, o) != (m.get("summary"), m.get("summary_origin")):
                upd["summary"], upd["summary_origin"] = s, o
            print(f"  SUMMARY {m['id']} {o} {len(s or '')} chars {time.time() - t0:.1f}s {_spent(n0)}"
                  f" — {verdict}" + (f" ({why})" if why else ""), flush=True)
            if probe:
                print(f"    {s[:600]!r}", flush=True)
        if "draft" in t["want"] and an0 is not None:
            n0, t0 = _calls(), time.time()
            text, o, why, cut = _ask(analyze.draft, "draft", segs, info)
            if str(o).startswith("ai:"):
                an["draft"] = {"text": text, "origin": o}
                verdict = "whole"
            elif cut:
                an.pop("draft", None)
                verdict = ("refused twice as a fragment — removed" if "draft" in an0
                           else "refused twice as a fragment — none stored")
            else:
                verdict = "could not be asked — kept as stored"
                bad.append(why)
            if an != an0:
                upd["analysis_json"] = json.dumps(an)
            print(f"  DRAFT {m['id']} {o} {len(text or '')} chars {time.time() - t0:.1f}s {_spent(n0)}"
                  f" — {verdict}" + (f" ({why})" if why else ""), flush=True)
            if probe:
                print(f"    {text[:900]!r}", flush=True)
        if bad:
            failed += 1
            streak += 1
        else:
            streak = 0
        if probe:
            probed = True
            print("REPAIR PROBE — nothing was written", flush=True)
            break
        cur = c.get_meeting(m["id"]) if len(upd) > 1 and not bad else None
        if bad:
            kept += 1
            print(f"  HELD {m['id']} — a part could not be asked; nothing written, the next run asks again",
                  flush=True)
        elif len(upd) > 1 and not (cur and cur.get("status") == "live"):
            # forgotten (or re-queued) while the run asked: never re-insert it
            kept += 1
            print(f"  GONE {m['id']} — no longer live; nothing written", flush=True)
        elif len(upd) > 1 and float(cur.get("updated_at") or 0) != float(m.get("updated_at") or 0):
            # rewritten while the run asked (a night's re-ingest): the new
            # reading stands — writing would put the old one back under the
            # new draft. The next run plans it afresh.
            kept += 1
            print(f"  CHANGED {m['id']} — rewritten while it was asked; nothing written", flush=True)
        elif len(upd) > 1:
            # the row as it stood, in the log, before it changes: a run that
            # went wrong is put back from here
            print("  BACKUP " + json.dumps({"id": m["id"], "summary": m.get("summary"),
                                           "summary_origin": m.get("summary_origin"),
                                           "draft": (an0 or {}).get("draft")}, ensure_ascii=False), flush=True)
            c.upsert_meeting(upd)
            fixed += 1
            print(f"UPDATED {m['id']} {sorted(k for k in upd if k != 'id')}", flush=True)
        else:
            kept += 1
        if streak >= STREAK:
            stopped = bad[-1]
            print(f"REPAIR STOPPED — {streak} meetings in a row could not be asked ({stopped}); "
                  "every row after them is unchanged", flush=True)
            break
    return {"fixed": fixed, "kept": kept, "failed": failed, "stopped": stopped, "probed": probed}


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(prog="record.repair")
    ap.add_argument("--before", default="", help="re-ask everything stored before this time (the fixed image's deploy)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; change nothing")
    ap.add_argument("--probe", action="store_true", help="ask for the first planned meeting and print it; write nothing")
    ap.add_argument("--limit", type=int, default=0, help="at most this many meetings")
    ap.add_argument("--only", default="", help="just this meeting id")
    a = ap.parse_args(argv)

    from memory import analyze
    from record.pipeline import bridge_model_key
    from record.settings import Settings
    from record.store import PgCorpus

    bridge_model_key(os.environ, Settings().gemini_key)
    c = PgCorpus()
    # one repair at a time, and the lock taken BEFORE the rows are read: two
    # overlapping runs could let one act on rows the other just rewrote. A
    # dry run reads only. The lock is the session's; it goes with it.
    lock = None if a.dry_run else c._psycopg.connect(c.dsn, autocommit=True)
    try:
        if lock is not None and not lock.execute(
                "SELECT pg_try_advisory_lock(hashtext('record.repair'))").fetchone()[0]:
            print("REPAIR STOPPED — another repair is running; nothing was changed", flush=True)
            return 1
        with c._con() as con:
            rows = [dict(r) for r in con.execute(
                "SELECT id, title, summary, summary_origin, analysis_json, updated_at FROM meetings "
                "WHERE status = 'live' ORDER BY added_at").fetchall()]
        todo = plan(rows, _when(a.before))
        if a.only:
            todo = [t for t in todo if t["id"] == a.only]
        if a.limit:
            todo = todo[:a.limit]
        print(f"REPAIR {len(rows)} live meetings, {len(todo)} to ask again; lane: "
              f"{analyze.llm.status().get('model')} enabled={analyze.llm.enabled()}", flush=True)
        by = {m["id"]: m for m in rows}
        for t in todo:
            m = by[t["id"]]
            d = (_analysis(m.get("analysis_json")) or {}).get("draft")
            was = f"summary {m.get('summary_origin') or 'none'}, draft " + (
                str(d.get("origin") or "none") if isinstance(d, dict) else "none")
            print(f"  PLAN {t['id']} {'+'.join(t['want'])} ({was})", flush=True)
        if a.dry_run or not todo:
            return 0
        if not analyze.llm.enabled():
            print("REPAIR STOPPED — no model key on this job; nothing was changed", flush=True)
            return 1
        r = repair(c, rows, todo, probe=a.probe)
    finally:
        if lock is not None:
            lock.close()
        c.close()
    if a.probe and not r["probed"]:
        print("REPAIR PROBE — no planned meeting had a transcript; nothing was asked", flush=True)
        return 1
    if not a.probe:
        print(f"REPAIR {'ENDED' if r['stopped'] else 'DONE'} — {r['fixed']} updated, {r['kept']} unchanged, "
              f"{r['failed']} could not be asked", flush=True)
    return 1 if r["failed"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
