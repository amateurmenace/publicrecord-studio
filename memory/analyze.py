"""The reading — what the meeting was about, with receipts.

Extractive by default: brief, entities, topics, decisions, participation all
come from Highlighter's local insight engine, which reads the transcript itself
and quotes it verbatim. No key, no network, stands alone — the covenant's
default.

Generative only on top: a one-paragraph summary through czcore.llm *when the
user has brought a key*, always labeled with its model and always beside — not
instead of — the extractive reading. With no key the same call returns the
extractive brief, so every surface has something true to show. Memory
supplements the official record; it never replaces it, and it never speaks
without saying who is speaking.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from czcore import llm
from highlighter import insight

# why the last model call fell back, in the seam's own sentence — the
# pipeline prints it beside the origin, so a night that pressed extractive
# summaries says why (a cut answer, a quota, a bad key) instead of nothing
LAST_FALLBACK = {"summary": "", "draft": ""}

_SUMMARY_SYS = (
    "You summarize public civic meetings for residents. Be plain, neutral, and "
    "concrete. One short paragraph of plain text — no Markdown, no headings, no "
    "lists, no asterisks. Name what was discussed and any decisions, with the "
    "transcript's own [timestamps] beside them, exactly as the passages write "
    "them, so a reader can check you. Never invent a vote or a name that is not "
    "in the passages. This supplements the official record; it does not "
    "replace it."
)


def read(segments: List[dict], info: Optional[dict] = None) -> dict:
    """The full extractive reading, cached beside the meeting. Every value is
    quoted or counted from the transcript — nothing modeled, nothing inferred
    about people's positions (a hard non-goal)."""
    meta = info or {}
    return {
        "brief": insight.brief(segments),
        "entities": insight.entities(segments),
        "topics": insight.topics(segments),
        "decisions": insight.decisions(segments),
        "questions": insight.questions(segments),
        "participation": insight.participation(segments),
        "wordfreq": insight.word_freq(segments),
        "agenda": insight.agenda(meta),
    }


def extractive_summary(segments: List[dict], n: int = 5) -> str:
    """The brief, joined — verbatim sentences from the meeting, in order."""
    return " ".join(r.get("text", "") for r in insight.brief(segments, n=n)).strip()


def summary(segments: List[dict],
            info: Optional[dict] = None) -> Tuple[str, str]:
    """One-paragraph summary → (text, origin). Generative when a key is set
    (origin 'ai:<model>'), extractive fallback otherwise (origin 'extractive').
    Never raises for lack of a key — that is the whole point."""
    if not segments:
        return "", "none"
    LAST_FALLBACK["summary"] = ""
    if llm.enabled():
        try:
            text = llm.complete(_prompt(segments, info), system=_SUMMARY_SYS,
                                max_tokens=400)
            if text.strip():
                model = llm.status().get("model", "a cloud model")
                return text.strip(), f"ai:{model}"
        except Exception as e:
            # the extractive path stands alone — fall through to it, and say why
            LAST_FALLBACK["summary"] = str(e)[:200]
    return extractive_summary(segments), "extractive"


_DRAFT_SYS = (
    "You write a short reading of a public civic meeting for residents: what "
    "it means, who moved it, and what to watch next. Three short paragraphs of "
    "plain text, plain and neutral, beginning 'What it means:', 'Who moved "
    "it:' and 'What to watch:' — no Markdown, no headings, no lists, no "
    "asterisks. Put the transcript's own [timestamp] beside every claim, "
    "exactly as the passages write it, so a reader can check you. Never invent "
    "a vote, a number, or a name that is not in the passages; say when the "
    "passages do not settle a question. This supplements the official record; "
    "it does not replace it."
)


def draft(segments: List[dict],
          info: Optional[dict] = None) -> Tuple[str, str]:
    """The reading's draft (specs/24 §4) → (text, origin). Generative only:
    origin 'ai:<model>' when a key is set, ('', 'none') otherwise — never a
    fallback, never raising. It stands beside the counted reading under its
    own label, never instead of it."""
    LAST_FALLBACK["draft"] = ""
    if not segments or not llm.enabled():
        return "", "none"
    try:
        text = llm.complete(_prompt(segments, info, budget=60000,
                                    ask="Write the reading: what it means, who "
                                        "moved it, what to watch — three short "
                                        "paragraphs with timestamps."),
                            system=_DRAFT_SYS, max_tokens=700)
        if text.strip():
            model = llm.status().get("model", "a cloud model")
            return text.strip(), f"ai:{model}"
    except Exception as e:
        LAST_FALLBACK["draft"] = str(e)[:200]
    return "", "none"


def _stamp(t) -> str:
    """A passage's time the way the page says it: [MM:SS] under the hour,
    [H:MM:SS] past it — a model echoes what it is shown, and a resident
    reading "[264:28]" has to do arithmetic to find 4:24:28 on the tape."""
    t = max(0, int(float(t or 0)))
    h, m, s = t // 3600, (t % 3600) // 60, t % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m:02d}:{s:02d}"


def _prompt(segments: List[dict], info: Optional[dict], budget: int = 40000,
            ask: str = "Write the summary paragraph.") -> str:
    title = (info or {}).get("title", "")
    lines = [f"[{_stamp(s.get('start', 0))}] "
             f"{(s.get('speaker') + ': ') if s.get('speaker') else ''}"
             f"{s.get('text', '')}" for s in segments]
    body = "\n".join(lines)
    if len(body) > budget:  # stride-sample long meetings, keep the whole arc
        stride = max(2, len(body) // budget + 1)
        body = "\n".join(lines[::stride])
    head = f"Meeting: {title}\n\n" if title else ""
    return f"{head}Transcript passages:\n{body}\n\n{ask}"
