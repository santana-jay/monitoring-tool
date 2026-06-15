import pytest

from copilot.ai.grounding import (
    GroundingContext,
    GroundingError,
    extract_json,
    validate_notes,
    validate_suggestions,
)
from copilot.core.models import TranscriptSegment


def _ctx():
    segs = [
        TranscriptSegment(id=1, meeting_id=1, start=10, end=12,
                          text="We will ship the API on Friday"),
        TranscriptSegment(id=2, meeting_id=1, start=12, end=15,
                          text="Maria will own the migration"),
    ]
    return GroundingContext.from_parts(recent=segs, retrieved=[])


def test_extract_json_plain():
    assert extract_json('{"a": 1}') == {"a": 1}


def test_extract_json_code_fence():
    assert extract_json('```json\n{"a": 1}\n```') == {"a": 1}


def test_extract_json_with_prose():
    assert extract_json('Here you go: {"a": 1} thanks') == {"a": 1}


def test_extract_json_invalid():
    with pytest.raises(GroundingError):
        extract_json("not json at all")


def test_extract_json_empty():
    with pytest.raises(GroundingError):
        extract_json("")


def test_grounded_citation_accepted():
    ctx = _ctx()
    raw = (
        '{"suggestions": [{"text": "Confirm Friday ship date",'
        ' "confidence": 0.8,'
        ' "citations": [{"start": 10, "end": 12, "quote": "ship the API on Friday"}]}]}'
    )
    res = validate_suggestions(raw, ctx, min_confidence=0.5)
    assert res.has_confident
    assert len(res.suggestions) == 1
    assert res.dropped == 0


def test_ungrounded_span_dropped():
    ctx = _ctx()
    raw = (
        '{"suggestions": [{"text": "Invented", "confidence": 0.95,'
        ' "citations": [{"start": 999, "end": 1000, "quote": "nope"}]}]}'
    )
    res = validate_suggestions(raw, ctx, min_confidence=0.5)
    assert not res.has_confident
    assert res.dropped == 1


def test_fabricated_quote_dropped():
    ctx = _ctx()
    # Span overlaps a real segment, but the quote was never said.
    raw = (
        '{"suggestions": [{"text": "x", "confidence": 0.9,'
        ' "citations": [{"start": 10, "end": 12,'
        ' "quote": "the budget is two million dollars"}]}]}'
    )
    res = validate_suggestions(raw, ctx, min_confidence=0.5)
    assert not res.has_confident
    assert res.dropped == 1


def test_low_confidence_gated():
    ctx = _ctx()
    raw = (
        '{"suggestions": [{"text": "maybe", "confidence": 0.3,'
        ' "citations": [{"start": 10, "end": 12, "quote": "ship the API"}]}]}'
    )
    res = validate_suggestions(raw, ctx, min_confidence=0.55)
    assert not res.has_confident
    assert res.dropped == 1


def test_explicit_abstain():
    ctx = _ctx()
    res = validate_suggestions('{"abstain": true, "suggestions": []}', ctx,
                               min_confidence=0.5)
    assert res.abstained
    assert not res.has_confident


def test_require_citations_drops_uncited():
    ctx = _ctx()
    raw = '{"suggestions": [{"text": "no cite", "confidence": 0.9, "citations": []}]}'
    res = validate_suggestions(raw, ctx, min_confidence=0.5, require_citations=True)
    assert not res.has_confident


def test_malformed_schema_raises():
    ctx = _ctx()
    # confidence out of range → schema validation failure
    raw = '{"suggestions": [{"text": "x", "confidence": 5}]}'
    with pytest.raises(GroundingError):
        validate_suggestions(raw, ctx, min_confidence=0.5)


def test_notes_citation_filtering():
    ctx = _ctx()
    raw = (
        '{"decisions": [{"category": "decision",'
        ' "text": "Ship API Friday",'
        ' "citations": ['
        '   {"start": 10, "end": 12, "quote": "ship the API on Friday"},'
        '   {"start": 999, "end": 1000, "quote": "fabricated"}]}],'
        ' "topics": [], "action_items": [], "open_questions": []}'
    )
    notes = validate_notes(raw, ctx)
    assert len(notes.decisions) == 1
    # the ungrounded citation is filtered out, the grounded one remains
    assert len(notes.decisions[0].citations) == 1
    assert notes.decisions[0].citations[0].start == 10
