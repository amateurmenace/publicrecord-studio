"""The night, cut (specs/26 §2.1): the reels the press makes from one
meeting's moments — Community Highlighter's one-press highlight reel, as
pressed links.

A meeting page already carries the analyzer's scored moments as cards, each
a tick away from the tray. But an editor's first want is the reel itself:
the night in three minutes. So the press cuts it — the five loudest moments
in tape order — and cuts the night four more ways, one reel per kind: the
roll calls, the decisions, the pushback, the questions. Each is the viewer's
own link (web/topic.py reel_url; the reader's decodeReel reads it), so it
plays clip to clip at /app/r, shares as its address, and opens back into a
tray with *make this reel yours*. Pure over the moments plane: the same
meeting presses the same links every night.
"""

from __future__ import annotations

from typing import List, Optional, Sequence

from . import topic as _topic

KINDS = (("vote", "the roll calls"), ("decision", "the decisions"),
         ("tension", "the pushback"), ("question", "the questions"))
LOUDEST = 5          # the night in a few minutes: its loudest moments
KIND_CAP = 16        # a reel of one kind stops here — the tray takes the rest


def _clip(pid: str, mo: dict) -> Optional[dict]:
    t = float(mo.get("t") or 0)
    start = float(mo.get("start") if mo.get("start") is not None else t)
    end = float(mo.get("end") or 0) or (start + _topic.WINDOW)
    if end <= start:
        return None
    return {"pid": pid, "start": start, "end": end}


def clips_of(pid: str, moments: Sequence[dict]) -> List[dict]:
    """The moments as clips, in tape order — each its own padded window; a
    window that starts inside the one before it extends it, up to the
    supercut's own cap (web/topic.py MERGE_CAP), so a vote and the decision
    seconds after it play once, not twice, and a night of moments minutes
    apart stays a reel of clips. `n` counts the moments a clip holds."""
    out: List[dict] = []
    for mo in sorted(moments, key=lambda mo: (float(mo.get("t") or 0), str(mo.get("kind") or ""))):
        c = _clip(pid, mo)
        if not c:
            continue
        if out and c["start"] <= out[-1]["end"] and (c["end"] - out[-1]["start"]) <= _topic.MERGE_CAP:
            out[-1]["end"] = max(out[-1]["end"], c["end"])
            out[-1]["n"] += 1
            continue
        out.append({**c, "n": 1})
    return out


def _reel(pid: str, moments: Sequence[dict], base: str) -> Optional[dict]:
    clips = clips_of(pid, moments)
    if not clips:
        return None
    return {"n": sum(c["n"] for c in clips), "clips": len(clips),
            "url": _topic.reel_url(clips, base), "runtime": _topic.runtime(clips)}


def meeting_cuts(m: dict, base: str = "/app") -> Optional[dict]:
    """The night, cut: the loudest reel and one per kind, or None when the
    analyzer scored nothing on this tape (the page says so itself)."""
    moments = [mo for mo in (m.get("moments") or []) if mo.get("t") is not None]
    if not moments or not m.get("pid"):
        return None
    pid = str(m["pid"])
    loud = sorted(moments, key=lambda mo: (-float(mo.get("score") or 0), float(mo.get("t") or 0)))[:LOUDEST]
    loudest = _reel(pid, loud, base)
    kinds = []
    for kind, label in KINDS:
        of_kind = [mo for mo in moments if mo.get("kind") == kind]
        if not of_kind:
            continue
        of_kind.sort(key=lambda mo: float(mo.get("t") or 0))
        r = _reel(pid, of_kind[:KIND_CAP], base)
        if r:
            kinds.append({"kind": kind, "label": label, "total": len(of_kind), **r})
    if not loudest:
        return None
    return {"pid": pid, "loudest": loudest, "kinds": kinds, "n_moments": len(moments)}
