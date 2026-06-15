"""Prompt construction.

Prompts are written to enforce grounding: the model is told to use ONLY the
provided transcript context, to cite the spans it draws from, to abstain when
unsure, and to never invent names/numbers/quotes. These instructions are part
of the anti-hallucination strategy and are paired with downstream schema
validation and grounding checks (see :mod:`copilot.ai.grounding`).
"""

from __future__ import annotations

from typing import List

from copilot.core.models import TranscriptSegment
from copilot.retrieval.store import RetrievedSnippet

NOTES_SYSTEM = (
    "You extract structured meeting notes. You summarise ONLY what was actually "
    "said in the provided transcript. Do not infer, speculate, or add outside "
    "knowledge. If a name, number, date, or quote is not present in the "
    "transcript, do not include it. Every note item should be supported by the "
    "transcript; attach citations (the start/end timestamps of the supporting "
    "lines). Respond with a single JSON object matching the requested schema and "
    "nothing else."
)

SUGGESTIONS_SYSTEM = (
    "You propose short reply/comment suggestions for a meeting participant. "
    "Ground every suggestion ONLY in the provided context (retrieved snippets "
    "and the recent transcript window). Use only information present in that "
    "context. Never invent names, numbers, quotes, or facts; if something is "
    "unknown from the context, treat it as unknown rather than guessing.\n"
    "Each suggestion MUST include: the suggested text, a confidence in [0,1], "
    "and citations referencing the transcript spans (start/end timestamps) it "
    "draws from. If you cannot ground a useful suggestion in the context, set "
    "\"abstain\": true and return an empty suggestions list. Prefer abstaining "
    "over inventing. Respond with a single JSON object matching the requested "
    "schema and nothing else."
)


def _format_segment(seg: TranscriptSegment) -> str:
    who = f"{seg.speaker}: " if seg.speaker else ""
    return f"[{seg.start:.1f}-{seg.end:.1f}] {who}{seg.text}"


def format_context(
    recent: List[TranscriptSegment],
    retrieved: List[RetrievedSnippet],
) -> str:
    """Render the grounded context block passed to the model.

    Only retrieved snippets + the recent window are included — never the full
    history — keeping calls small and grounded.
    """
    parts: List[str] = []
    if retrieved:
        parts.append("# Retrieved snippets from past/earlier transcript")
        for r in retrieved:
            parts.append(_format_segment(r.segment))
    parts.append("\n# Recent transcript window")
    for seg in recent:
        parts.append(_format_segment(seg))
    return "\n".join(parts)


NOTES_SCHEMA_HINT = (
    "JSON schema: {\n"
    '  "topics": [{"category": "topic", "text": str, "citations": [cite]}],\n'
    '  "decisions": [{"category": "decision", "text": str, "citations": [cite]}],\n'
    '  "action_items": [{"category": "action_item", "text": str, "citations": [cite]}],\n'
    '  "open_questions": [{"category": "open_question", "text": str, "citations": [cite]}]\n'
    "}\n"
    'where cite = {"start": float, "end": float, "quote": str (verbatim from context)}'
)

SUGGESTIONS_SCHEMA_HINT = (
    "JSON schema: {\n"
    '  "abstain": bool,\n'
    '  "suggestions": [{\n'
    '     "text": str,\n'
    '     "confidence": float in [0,1],\n'
    '     "rationale": str (optional),\n'
    '     "citations": [{"start": float, "end": float, "quote": str (verbatim from context)}]\n'
    "  }]\n"
    "}"
)


def build_notes_messages(context: str) -> List[dict]:
    return [
        {
            "role": "user",
            "content": (
                f"{NOTES_SCHEMA_HINT}\n\n"
                f"Transcript context:\n{context}\n\n"
                "Extract the structured notes as JSON."
            ),
        }
    ]


def build_suggestions_messages(context: str) -> List[dict]:
    return [
        {
            "role": "user",
            "content": (
                f"{SUGGESTIONS_SCHEMA_HINT}\n\n"
                f"Context:\n{context}\n\n"
                "Propose grounded reply suggestions as JSON, or abstain."
            ),
        }
    ]
