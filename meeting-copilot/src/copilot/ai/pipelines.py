"""Notes and suggestions pipelines.

Both pipelines assemble grounded context (retrieved snippets + recent window),
call the LLM, then validate/ground/gate the output before returning it. They
take an :class:`LLMClient` so they can be unit-tested with a fake client.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, List, Optional

from copilot.ai import prompts
from copilot.ai.client import LLMClient
from copilot.ai.grounding import (
    GatedSuggestions,
    GroundingContext,
    validate_notes,
    validate_suggestions,
)
from copilot.core.models import Notes, TranscriptSegment
from copilot.retrieval.store import RetrievalStore, RetrievedSnippet


@dataclass
class NotesPipeline:
    """Periodic, low-temperature extraction of structured notes.

    Notes are extraction/summarization of what was actually said — a separate
    duty from suggestions. Uses the stronger model.
    """

    client: LLMClient
    model: str
    temperature: float = 0.0
    max_tokens: int = 1500

    def run(self, recent: List[TranscriptSegment],
            retrieved: Optional[List[RetrievedSnippet]] = None) -> Notes:
        retrieved = retrieved or []
        context = prompts.format_context(recent, retrieved)
        messages = prompts.build_notes_messages(context)
        raw = self.client.complete(
            system=prompts.NOTES_SYSTEM,
            messages=messages,
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
        )
        gc = GroundingContext.from_parts(recent, retrieved)
        return validate_notes(raw, gc)


@dataclass
class SuggestionsPipeline:
    """Real-time, grounded, cited, confidence-gated suggestions.

    Uses the fast model and streams. Retrieves grounding snippets from past +
    current transcript for the query window, then validates and gates output.
    """

    client: LLMClient
    model: str
    retrieval: Optional[RetrievalStore] = None
    min_confidence: float = 0.55
    temperature: float = 0.2
    max_tokens: int = 700
    k: int = 5

    def _retrieve(self, query: str, meeting_id: Optional[int],
                  exclude_after: Optional[float]) -> List[RetrievedSnippet]:
        if self.retrieval is None or not query.strip():
            return []
        return self.retrieval.search(query, k=self.k, exclude_after=exclude_after)

    def run(self, recent: List[TranscriptSegment],
            meeting_id: Optional[int] = None,
            on_delta: Optional[Callable[[str], None]] = None) -> GatedSuggestions:
        query = " ".join(s.text for s in recent[-5:])
        exclude_after = recent[0].start if recent else None
        retrieved = self._retrieve(query, meeting_id, exclude_after)
        context = prompts.format_context(recent, retrieved)
        messages = prompts.build_suggestions_messages(context)
        raw = self.client.complete(
            system=prompts.SUGGESTIONS_SYSTEM,
            messages=messages,
            model=self.model,
            max_tokens=self.max_tokens,
            temperature=self.temperature,
            on_delta=on_delta,
        )
        gc = GroundingContext.from_parts(recent, retrieved)
        return validate_suggestions(raw, gc, min_confidence=self.min_confidence)
