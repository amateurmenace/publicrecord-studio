"""What the night is doing — the steward's window onto the jobs.

The console's other screens are skins over the corpus. This one looks
outward: at Cloud Run, where the poll, the pipeline, the embed and the press
run as jobs, and at Cloud Logging, where each of them says what it did in
sentences. Until 2026-09-24 a steward could only learn that a night had gone
wrong by reading a terminal on somebody's laptop; the record's own promise
(OPERATING.md: "the log reads like sentences") was kept in a place no
steward could open.

Three decisions.

**Read-only by default, one verb.** Executions and their log lines are read
through the platform APIs with the service's own identity. The single write
— *run this job now* — is audited like a curation verb, and it exists so a
steward can re-run a night that failed without a terminal.

**Configuration is two names.** `RECORD_CLOUD_PROJECT` and
`RECORD_CLOUD_REGION` say where the jobs live. Absent, this module says so
and the console shows that sentence instead of an empty screen — the same
honesty the sign-in gate practises.

**The platform is behind one seam.** Every call goes through `_call`, which
takes an optional `fetch` so the tests exercise the shaping of executions and
log lines against recorded answers, never the network.
"""

from __future__ import annotations

import json
import os
import re
import time
import urllib.request
from typing import Callable, List, Optional

from .settings import settings

# The jobs a night is made of, in the order they run, and what each does —
# from record/OPERATING.md "Nightly intake". The edition step is a GitHub
# workflow, not a Cloud Run job; it is listed so the schedule reads whole.
JOBS = ("record-poll", "record-pipeline", "record-embed", "record-press",
        "record-migrate", "record-seed")
# The press is not run from the desk: the nightly-edition workflow owns it
# (it presses and carries in one breath; a press from here could carry a
# mixed edition until the next night).
RUNNABLE = ("record-poll", "record-pipeline", "record-embed")
SCHEDULE = (
    {"at": "03:00 ET", "job": "record-poll",
     "does": "polls every live town's channels; files rule-matched candidates, "
             "approves them under a standing rule when YouTube lists a caption track"},
    {"at": "03:30 ET", "job": "record-pipeline",
     "does": "ingests every approved submission; asks again for a week of parked tapes"},
    {"at": "04:30 ET", "job": "nightly-edition (GitHub Actions)",
     "does": "presses the edition from the cloud and carries it to the Pages repo"},
    {"at": "05:45 ET", "job": "record-embed",
     "does": "drains the meaning-vector backlog under the spend cap"},
)

Fetch = Callable[..., dict]


class OpsError(Exception):
    def __init__(self, detail: str, status: int = 502):
        super().__init__(detail)
        self.detail, self.status = detail, status


def cloud() -> dict:
    """Where the jobs live, or the sentence that says nobody told us."""
    project = (os.environ.get("RECORD_CLOUD_PROJECT") or "").strip()
    region = (os.environ.get("RECORD_CLOUD_REGION") or "").strip()
    why = ""
    if not project or not region:
        why = ("RECORD_CLOUD_PROJECT and RECORD_CLOUD_REGION are not both set, so "
               "the console cannot ask Cloud Run what the night did")
    return {"project": project, "region": region, "configured": not why, "why": why}


_SESSION = None


def _session():
    """One authorized session for the process, built on first use with the
    service's own identity (the metadata server on Cloud Run, ADC at a desk)."""
    global _SESSION
    if _SESSION is None:
        import google.auth
        from google.auth.transport.requests import AuthorizedSession
        creds, _ = google.auth.default(
            scopes=["https://www.googleapis.com/auth/cloud-platform"])
        _SESSION = AuthorizedSession(creds)
    return _SESSION


def _call(method: str, url: str, body: Optional[dict] = None,
          params: Optional[dict] = None, fetch: Optional[Fetch] = None) -> dict:
    """The seam. `fetch(method, url, body, params)` answers with a dict."""
    if fetch is not None:
        return fetch(method, url, body, params)
    try:
        r = _session().request(method, url, json=body, params=params, timeout=20)
    except Exception as exc:
        raise OpsError(f"the platform could not be reached: {exc}") from exc
    if r.status_code >= 400:
        detail = ""
        try:
            detail = (r.json().get("error") or {}).get("message") or ""
        except Exception:
            detail = r.text[:200]
        raise OpsError(f"the platform answered {r.status_code}: {detail}", r.status_code)
    try:
        return r.json()
    except Exception:
        return {}


def _short(name: str) -> str:
    return str(name or "").rsplit("/", 1)[-1]


def _when(iso: str) -> float:
    """RFC 3339 → epoch seconds, or 0."""
    if not iso:
        return 0.0
    try:
        from datetime import datetime, timezone
        s = str(iso).replace("Z", "+00:00")
        s = re.sub(r"\.(\d{6})\d+", r".\1", s)     # nanoseconds → microseconds
        return datetime.fromisoformat(s).astimezone(timezone.utc).timestamp()
    except Exception:
        return 0.0


def image_tag(image: str) -> str:
    """The short name of an image: its tag (`r45`) when it has one, else the
    first twelve characters of its digest — an execution records the image
    it ran by digest, and sixty-four hex characters are not a name."""
    img = str(image or "")
    head, _, digest = img.partition("@")
    last = head.rsplit("/", 1)[-1]
    if ":" in last:
        return last.rsplit(":", 1)[-1]
    if digest:
        return digest.replace("sha256:", "")[:12]
    return last


def shape_execution(raw: dict) -> dict:
    """One execution, in the words the console uses."""
    running = int(raw.get("runningCount") or 0)
    ok = int(raw.get("succeededCount") or 0)
    bad = int(raw.get("failedCount") or 0)
    cancelled = int(raw.get("cancelledCount") or 0)
    completed = raw.get("completionTime") or ""
    message = ""
    for c in raw.get("conditions") or []:
        if c.get("type") == "Completed" and c.get("message"):
            message = str(c["message"])
    if running or not completed:
        state = "running"
    elif cancelled:
        state = "cancelled"
    elif bad:
        state = "failed"
    else:
        state = "succeeded"
    image = ""
    try:
        image = image_tag(raw["template"]["containers"][0]["image"])
    except Exception:
        pass
    return {"name": _short(raw.get("name", "")),
            "job": _short(raw.get("job", "")),
            "state": state, "message": message, "image": image,
            "created": _when(raw.get("createTime", "")),
            "started": _when(raw.get("startTime", "")),
            "completed": _when(completed),
            "retries": int(raw.get("retriedCount") or 0)}


def executions(job: str, limit: int = 5, fetch: Optional[Fetch] = None) -> List[dict]:
    """The latest executions of one job, newest first."""
    c = cloud()
    if not c["configured"] and fetch is None:
        raise OpsError(c["why"], 503)
    url = (f"https://run.googleapis.com/v2/projects/{c['project'] or 'p'}/locations/"
           f"{c['region'] or 'r'}/jobs/{job}/executions")
    j = _call("GET", url, params={"pageSize": max(1, min(int(limit), 20))}, fetch=fetch)
    rows = [shape_execution(e) for e in (j.get("executions") or [])]
    rows.sort(key=lambda e: -e["created"])
    return rows[:limit]


def log_tail(execution: str, limit: int = 80, fetch: Optional[Fetch] = None) -> List[dict]:
    """The last `limit` lines an execution printed, oldest first. Names are
    the execution's own (`record-pipeline-abc12`); anything else is refused
    before it reaches a filter."""
    if not re.fullmatch(r"[a-z][a-z0-9-]{2,80}", execution or ""):
        raise OpsError("that is not an execution name", 400)
    c = cloud()
    if not c["configured"] and fetch is None:
        raise OpsError(c["why"], 503)
    body = {"resourceNames": [f"projects/{c['project'] or 'p'}"],
            "filter": ('resource.type="cloud_run_job" AND '
                       f'labels."run.googleapis.com/execution_name"="{execution}"'),
            "orderBy": "timestamp desc",
            "pageSize": max(1, min(int(limit), 500))}
    j = _call("POST", "https://logging.googleapis.com/v2/entries:list", body=body, fetch=fetch)
    out = []
    for e in j.get("entries") or []:
        text = e.get("textPayload")
        if text is None:
            jp = e.get("jsonPayload")
            if isinstance(jp, dict):
                text = jp.get("message") or jp.get("msg") or (json.dumps(jp) if jp else "")
            else:
                text = jp if isinstance(jp, str) else (json.dumps(jp) if jp not in (None, "", {}) else "")
        text = str(text or "").rstrip()
        if not text or text == '""':
            continue
        out.append({"t": _when(e.get("timestamp", "")),
                    "severity": str(e.get("severity") or ""),
                    "line": text})
    out.sort(key=lambda l: l["t"])        # the platform answers newest first
    return out


def run_job(job: str, fetch: Optional[Fetch] = None) -> dict:
    """Start one execution of a job, now. The steward's one verb here."""
    if job not in RUNNABLE:
        raise OpsError(f"{job} is not a job a steward runs from here", 400)
    c = cloud()
    if not c["configured"] and fetch is None:
        raise OpsError(c["why"], 503)
    url = (f"https://run.googleapis.com/v2/projects/{c['project'] or 'p'}/locations/"
           f"{c['region'] or 'r'}/jobs/{job}:run")
    j = _call("POST", url, body={}, fetch=fetch)
    name = ""
    try:
        # the execution's own name rides in the operation's metadata; the
        # operation's name (…/operations/<uuid>) is not an execution
        name = _short((j.get("metadata") or {}).get("name") or "")
    except Exception:
        pass
    return {"job": job, "execution": name, "started": True}


# -- the edition, as readers have it ------------------------------------------

_EDITION = {"at": 0.0, "value": None}
EDITION_TTL_S = 60


def edition_live(fetch_text: Optional[Callable[[str], str]] = None) -> dict:
    """What publicrecord.studio serves right now: the pressing's own
    manifest, fetched from the reader's side of the fence and cached a
    minute. Unreachable is a sentence, not an exception."""
    now = time.time()
    if fetch_text is None and _EDITION["value"] is not None and now - _EDITION["at"] < EDITION_TTL_S:
        return _EDITION["value"]
    base = (settings.site_base or "https://publicrecord.studio").rstrip("/")
    url = f"{base}/app/pressing.json"
    try:
        if fetch_text is not None:
            text = fetch_text(url)
        else:
            with urllib.request.urlopen(url, timeout=4) as r:   # noqa: S310 — our own site
                text = r.read().decode("utf-8", "replace")
        m = json.loads(text)
        value = {"reachable": True, "url": url,
                 "version": m.get("version", ""), "edition_date": m.get("edition_date", ""),
                 "corpus_hash": m.get("corpus_hash", ""), "pressed_at": m.get("pressed_at", ""),
                 "counts": m.get("counts") or {}}
    except Exception as exc:
        value = {"reachable": False, "url": url, "why": str(exc)}
    if fetch_text is None:
        _EDITION.update(at=now, value=value)
    return value


# -- the record, counted for the desk ----------------------------------------

def overview(corpus) -> dict:
    """Every number the desk shows at a glance, per town and for the whole
    record. One round of queries, no model, no platform call."""
    from memory import ingest
    from . import embed_neural, pipeline
    from .connectors import youtube as yt
    from czcore import llm

    with corpus._con() as con:
        towns = [dict(r) for r in con.execute(
            "SELECT slug, name, state, status FROM towns ORDER BY name").fetchall()]
        subs = con.execute(
            "SELECT town, status, COUNT(*) AS n FROM submissions "
            "GROUP BY town, status").fetchall()
        mts = con.execute(
            "SELECT town, status, COUNT(*) AS n, MAX(date) AS latest, "
            "COALESCE(SUM(n_segments),0) AS segments FROM meetings "
            "GROUP BY town, status").fetchall()
        behind = con.execute(
            "SELECT town, COUNT(*) AS n FROM segments "
            "WHERE emb_neural IS NULL AND btrim(coalesce(text,'')) <> '' "
            "GROUP BY town").fetchall()
        parked = con.execute(
            "SELECT town, COUNT(*) AS n FROM meetings WHERE status = 'no_transcript' "
            "GROUP BY town").fetchall()
        stale_cut = time.time() - ingest.STALE_IN_FLIGHT_S
        flight = con.execute(
            "SELECT town, id, title, status, COALESCE(updated_at, added_at, 0) AS touched "
            "FROM meetings WHERE status IN ('queued','transcribing','analyzing') "
            "ORDER BY touched DESC").fetchall()
        spend = con.execute(
            "SELECT COALESCE(SUM(units),0) AS units, COUNT(*) AS calls, "
            "MAX(added_at) AS last FROM spend").fetchone()
        last_audit = con.execute(
            "SELECT steward, verb, town, added_at FROM audit "
            "ORDER BY added_at DESC LIMIT 1").fetchone()

    by_town = {t["slug"]: t for t in towns}
    # meetings and submissions name towns by slug or by name in different
    # eras of the record; fold both onto the town row.
    def town_of(name: str) -> str:
        for t in towns:
            if name in (t["slug"], t["name"]):
                return t["slug"]
        return name or ""
    for t in towns:
        t.update(submissions={}, meetings={}, latest="", segments=0, behind=0,
                 parked=0, in_flight=[])
    other = {"slug": "", "name": "(no town)", "state": "", "status": "",
             "submissions": {}, "meetings": {}, "latest": "", "segments": 0,
             "behind": 0, "parked": 0, "in_flight": []}
    def row(name):
        return by_town.get(town_of(name), other)
    for r in subs:
        row(r["town"])["submissions"][r["status"]] = int(r["n"])
    for r in mts:
        t = row(r["town"])
        t["meetings"][r["status"]] = int(r["n"])
        t["segments"] += int(r["segments"] or 0)
        if r["latest"] and str(r["latest"]) > str(t["latest"]):
            t["latest"] = str(r["latest"])
    for r in behind:
        row(r["town"])["behind"] += int(r["n"])
    for r in parked:
        row(r["town"])["parked"] += int(r["n"])
    for r in flight:
        row(r["town"])["in_flight"].append({
            "id": r["id"], "title": r["title"], "status": r["status"],
            "touched": float(r["touched"] or 0),
            "stale": float(r["touched"] or 0) < stale_cut})
    if any(other[k] for k in ("submissions", "meetings", "behind", "parked", "in_flight")):
        towns.append(other)

    units = int(spend["units"] or 0)
    lane = llm.status()
    return {
        "towns": towns,
        "totals": {
            "submissions": {k: sum(t["submissions"].get(k, 0) for t in towns)
                            for k in {s for t in towns for s in t["submissions"]}},
            "meetings": {k: sum(t["meetings"].get(k, 0) for t in towns)
                         for k in {s for t in towns for s in t["meetings"]}},
            "behind": sum(t["behind"] for t in towns),
            "parked": sum(t["parked"] for t in towns),
            "in_flight": sum(len(t["in_flight"]) for t in towns),
        },
        "spend": {"units": units, "calls": int(spend["calls"] or 0),
                  "usd_estimate": round(embed_neural.estimate_usd(units), 4),
                  "cap_usd": settings.spend_cap_usd,
                  "last": float(spend["last"] or 0)},
        "lanes": {
            "neural": embed_neural.status(),
            "model": {"enabled": bool(lane.get("enabled")), "model": lane.get("model"),
                      "provider": lane.get("provider"), "source": lane.get("source")},
            "youtube_key": bool(yt.data_api_key()),
            "caption_relay": True,
        },
        "windows": {"embed_budget_s": settings.embed_budget_s,
                    "retry_days": pipeline.RETRY_DAYS,
                    "reprobe_days": yt.REPROBE_DAYS,
                    "stale_in_flight_s": ingest.STALE_IN_FLIGHT_S,
                    "spend_cap_usd": settings.spend_cap_usd},
        "stewards": list(settings.steward_allowlist),
        "last_audit": dict(last_audit) if last_audit else None,
        "schedule": list(SCHEDULE),
        "cloud": cloud(),
        "edition": edition_live(),
    }


def meetings_of(corpus, town: str = "", limit: int = 100) -> List[dict]:
    """The record's meetings for the desk's own list — every status, newest
    day first, with what search knows of each (segments, vectors)."""
    sql = ("SELECT id, town, body, title, date, status, error, summary_origin, "
           "n_segments, added_at, updated_at FROM meetings")
    args: list = []
    if town:
        sql += " WHERE town = %s OR town = (SELECT name FROM towns WHERE slug = %s)"
        args += [town, town]
    sql += " ORDER BY date DESC NULLS LAST, added_at DESC LIMIT %s"
    args.append(max(1, min(int(limit), 500)))
    with corpus._con() as con:
        rows = [dict(r) for r in con.execute(sql, args).fetchall()]
        # what search cannot see yet, one grouped read over the partial
        # index (002_neural_todo) rather than a subquery per meeting
        missing = {}
        if rows:
            for r in con.execute(
                    "SELECT meeting_id, COUNT(*) AS n FROM segments "
                    "WHERE emb_neural IS NULL AND btrim(coalesce(text, '')) <> '' "
                    "AND meeting_id = ANY(%s) "
                    "GROUP BY meeting_id", ([m["id"] for m in rows],)).fetchall():
                missing[r["meeting_id"]] = int(r["n"])
    for m in rows:
        m["embedded"] = max(0, int(m.get("n_segments") or 0) - missing.get(m["id"], 0))
    return rows
