"""Shared data models / schemas.

These pydantic models are the contract between layers and the schema that AI
outputs are validated against. Strict validation is part of the
anti-hallucination strategy: malformed or ungrounded items are dropped or
flagged rather than surfaced to the user.
"""

from __future__ import annotations

from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


class TranscriptSegment(BaseModel):
    """A timestamped span of transcribed speech."""

    id: Optional[int] = None
    meeting_id: int
    start: float = Field(..., description="Start time in seconds from meeting start.")
    end: float = Field(..., description="End time in seconds from meeting start.")
    text: str
    speaker: Optional[str] = Field(
        default=None, description="Best-effort speaker turn label, if available."
    )
    is_final: bool = True

    @field_validator("end")
    @classmethod
    def _end_after_start(cls, v: float, info):
        start = info.data.get("start")
        if start is not None and v < start:
            raise ValueError("end must be >= start")
        return v


class Citation(BaseModel):
    """A reference back to the transcript span(s) a suggestion draws from."""

    segment_id: Optional[int] = None
    start: float
    end: float
    quote: Optional[str] = Field(
        default=None,
        description="Short verbatim quote from the cited span (must appear in context).",
    )


class NoteCategory(str, Enum):
    TOPIC = "topic"
    DECISION = "decision"
    ACTION_ITEM = "action_item"
    OPEN_QUESTION = "open_question"


class NoteItem(BaseModel):
    """One extracted structured note."""

    category: NoteCategory
    text: str
    citations: List[Citation] = Field(default_factory=list)


class Notes(BaseModel):
    """The structured notes object produced by the notes pipeline."""

    topics: List[NoteItem] = Field(default_factory=list)
    decisions: List[NoteItem] = Field(default_factory=list)
    action_items: List[NoteItem] = Field(default_factory=list)
    open_questions: List[NoteItem] = Field(default_factory=list)


class Suggestion(BaseModel):
    """A grounded, cited, confidence-scored AI reply/comment proposal.

    ``confidence`` in [0, 1] gates the UI: low-confidence suggestions are
    suppressed in favour of an explicit "no confident suggestion" state.
    """

    text: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    citations: List[Citation] = Field(default_factory=list)
    rationale: Optional[str] = None

    @field_validator("text")
    @classmethod
    def _non_empty(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("suggestion text must be non-empty")
        return v


class SuggestionResponse(BaseModel):
    """Top-level structured output for the suggestions pipeline.

    ``abstain`` lets the model decline explicitly when it has nothing well
    grounded to say; the UI shows "no confident suggestion" in that case.
    """

    abstain: bool = False
    suggestions: List[Suggestion] = Field(default_factory=list)
