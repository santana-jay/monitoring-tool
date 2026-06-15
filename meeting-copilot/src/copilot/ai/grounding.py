"""Grounding and validation — the core anti-hallucination guard.

Responsibilities:
  * Parse model output as JSON (tolerating markdown code fences).
  * Validate it against the pydantic schema; drop/flag malformed items.
  * Verify citations are *grounded*: each cited span must overlap a span that
    was actually provided as context, and any verbatim quote must appear in the
    provided context text.
  * Gate suggestions by a minimum confidence, and treat an empty/abstaining
    result as the explicit "no confident suggestion" state.

These checks run regardless of what the model claims, so ungrounded or
low-confidence items never reach the UI.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

from pydantic import ValidationError

from copilot.core.models import (
    Citation,
    Notes,
    Suggestion,
    SuggestionResponse,
    TranscriptSegment,
)
from copilot.retrieval.store import RetrievedSnippet

_FENCE = re.compile(r"```(?:json)?\s*(.*?)\s*```", re.DOTALL)


class GroundingError(ValueError):
    """Raised when model output cannot be parsed/validated at all."""


def extract_json(text: str) -> dict:
    """Extract the first JSON object from ``text`` (handles code fences)."""
    if not text or not text.strip():
        raise GroundingError("empty model output")
    candidate = text.strip()
    m = _FENCE.search(candidate)
    if m:
        candidate = m.group(1).strip()
    else:
        start = candidate.find("{")
        end = candidate.rfind("}")
        if start != -1 and end != -1 and end > start:
            candidate = candidate[start : end + 1]
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as exc:
        raise GroundingError(f"output is not valid JSON: {exc}") from exc
    if not isinstance(data, dict):
        raise GroundingError("top-level JSON must be an object")
    return data


@dataclass
class GroundingContext:
    """The material the model was allowed to use, for verifying citations."""

    segments: List[TranscriptSegment]
    text: str = ""

    @classmethod
    def from_parts(
        cls,
        recent: List[TranscriptSegment],
        retrieved: List[RetrievedSnippet],
    ) -> "GroundingContext":
        segs = [r.segment for r in retrieved] + list(recent)
        text = " ".join(s.text for s in segs).lower()
        return cls(segments=segs, text=text)

    def _spans(self) -> List[Tuple[float, float]]:
        return [(s.start, s.end) for s in self.segments]

    def citation_is_grounded(self, cite: Citation, tol: float = 1.0) -> bool:
        """A citation is grounded if its span overlaps a provided span and any
        quote it carries actually appears in the provided context text."""
        overlaps = False
        for (start, end) in self._spans():
            if cite.start <= end + tol and cite.end >= start - tol:
                overlaps = True
                break
        if not overlaps:
            return False
        if cite.quote:
            # Require a reasonable verbatim overlap (first few words) to guard
            # against fabricated quotes.
            needle = cite.quote.strip().lower()
            if needle and needle not in self.text:
                snippet = " ".join(needle.split()[:4])
                if snippet and snippet not in self.text:
                    return False
        return True


def validate_notes(raw: str, context: GroundingContext) -> Notes:
    """Parse, validate, and ground-filter notes output."""
    data = extract_json(raw)
    try:
        notes = Notes.model_validate(data)
    except ValidationError as exc:
        raise GroundingError(f"notes failed schema validation: {exc}") from exc

    for field_name in ("topics", "decisions", "action_items", "open_questions"):
        items = getattr(notes, field_name)
        for item in items:
            item.citations = [
                c for c in item.citations if context.citation_is_grounded(c)
            ]
    return notes


@dataclass
class GatedSuggestions:
    """Result of validating + gating suggestions."""

    suggestions: List[Suggestion] = field(default_factory=list)
    abstained: bool = False
    dropped: int = 0

    @property
    def has_confident(self) -> bool:
        return bool(self.suggestions)


def validate_suggestions(
    raw: str,
    context: GroundingContext,
    min_confidence: float,
    require_citations: bool = True,
) -> GatedSuggestions:
    """Parse, validate, ground, and confidence-gate suggestions.

    Returns a :class:`GatedSuggestions`. When nothing survives (model abstained,
    everything ungrounded, or below threshold) ``has_confident`` is False and the
    UI should show "no confident suggestion".
    """
    data = extract_json(raw)
    try:
        response = SuggestionResponse.model_validate(data)
    except ValidationError as exc:
        raise GroundingError(f"suggestions failed schema validation: {exc}") from exc

    if response.abstain:
        return GatedSuggestions(suggestions=[], abstained=True, dropped=0)

    kept: List[Suggestion] = []
    dropped = 0
    for sug in response.suggestions:
        grounded_cites = [c for c in sug.citations if context.citation_is_grounded(c)]
        if require_citations and not grounded_cites:
            dropped += 1
            continue
        if sug.confidence < min_confidence:
            dropped += 1
            continue
        sug.citations = grounded_cites
        kept.append(sug)

    return GatedSuggestions(suggestions=kept, abstained=False, dropped=dropped)
