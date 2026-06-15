"""AI orchestration layer (Anthropic Claude)."""

from copilot.ai.client import AnthropicClient, LLMClient
from copilot.ai.grounding import (
    GatedSuggestions,
    GroundingContext,
    GroundingError,
    validate_notes,
    validate_suggestions,
)
from copilot.ai.pipelines import NotesPipeline, SuggestionsPipeline

__all__ = [
    "AnthropicClient",
    "LLMClient",
    "GatedSuggestions",
    "GroundingContext",
    "GroundingError",
    "validate_notes",
    "validate_suggestions",
    "NotesPipeline",
    "SuggestionsPipeline",
]
