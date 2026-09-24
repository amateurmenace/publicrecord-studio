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
draft at all. A summary the model still cannot finish falls back to the
extractive one, labeled so (the seam's rule); a draft that cannot be
finished is removed, never left a fragment. Re-runs are safe: a repaired
row is newer than the cutoff. Prints one line per meeting and per call.
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
        try:
            an = json.loads(m.get("analysis_json") or "{}") or {}
        except (TypeError, ValueError):
            an = {}
        d = an.get("draft") if isinstance(an, dict) else None
        if isinstance(d, dict) and str(d.get("origin") or "").startswith("ai:"):
            dt = str(d.get("text") or "")
            if old or is_cut(dt) or "**" in dt:
                want.append("draft")
        elif old:
            want.append("draft")          # a live meeting with no draft: the recovery path
        if want:
            out.append({"id": m["id"], "want": want})
    return out


def _usage() -> str:
    from czcore import llm
    u = llm.last_usage() or {}
    return f"in {u.get('tokens_in', 0)} out {u.get('tokens_out', 0)}" if u else "no call"


def _ask(fn, segs, info, tries: int = 2):
    """One call, and once more after a pause if it fell back — a 429 or a
    timeout on one night is not a reason to lose a draft."""
    from memory import analyze
    for k in range(tries):
        text, origin = fn(segs, info)
        if text and str(origin).startswith("ai:"):
            return text, origin, ""
        why = analyze.LAST_FALLBACK.get("summary" if fn is analyze.summary else "draft", "")
        if k + 1 < tries:
            time.sleep(20)
    return text, origin, why


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
    for t in todo:
        print(f"  PLAN {t['id']} {'+'.join(t['want'])}", flush=True)
    if a.dry_run or not todo:
        c.close()
        return 0
    if not analyze.llm.enabled():
        print("REPAIR STOPPED — no model key on this job; nothing was changed", flush=True)
        c.close()
        return 1
    by = {m["id"]: m for m in rows}
    fixed = 0
    for t in (todo[:1] if a.probe else todo):
        m = by[t["id"]]
        upd = {"id": m["id"]}
        segs = c.transcript(m["id"])
        info = {"title": m.get("title") or ""}
        if "summary" in t["want"]:
            t0 = time.time()
            s, o, why = _ask(analyze.summary, segs, info)
            if s:
                upd["summary"], upd["summary_origin"] = s, o
            print(f"  SUMMARY {m['id']} {o} {len(s or '')} chars {time.time() - t0:.1f}s {_usage()}"
                  + (f" ({why})" if why else ""), flush=True)
            if a.probe:
                print(f"    {s[:600]!r}", flush=True)
        if "draft" in t["want"]:
            an = json.loads(m.get("analysis_json") or "{}") or {}
            t0 = time.time()
            text, o, why = _ask(analyze.draft, segs, info)
            if text:
                an["draft"] = {"text": text, "origin": o}
            else:
                an.pop("draft", None)
            upd["analysis_json"] = json.dumps(an)
            print(f"  DRAFT {m['id']} {o} {len(text or '')} chars {time.time() - t0:.1f}s {_usage()}"
                  + (f" ({why})" if why else ""), flush=True)
            if a.probe:
                print(f"    {text[:900]!r}", flush=True)
        if a.probe:
            print("REPAIR PROBE — nothing was written", flush=True)
            break
        if len(upd) > 1:
            c.upsert_meeting(upd)
            fixed += 1
            print(f"UPDATED {m['id']} {sorted(k for k in upd if k != 'id')}", flush=True)
    c.close()
    if not a.probe:
        print(f"REPAIR DONE — {fixed} updated, {len(rows) - fixed} kept", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
