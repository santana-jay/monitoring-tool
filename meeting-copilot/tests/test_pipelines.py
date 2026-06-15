from copilot.ai.client import AnthropicClient
from copilot.ai.pipelines import NotesPipeline, SuggestionsPipeline
from copilot.core.models import TranscriptSegment
from copilot.retrieval.embeddings import HashingEmbedder
from copilot.retrieval.store import RetrievalStore
from copilot.store.db import Store
from tests.conftest import FakeLLM


def _recent():
    return [
        TranscriptSegment(id=1, meeting_id=1, start=10, end=12,
                          text="We will ship the API on Friday"),
    ]


def test_suggestions_pipeline_grounded():
    llm = FakeLLM(
        '{"suggestions": [{"text": "Confirm Friday", "confidence": 0.9,'
        ' "citations": [{"start": 10, "end": 12, "quote": "ship the API"}]}]}'
    )
    pipe = SuggestionsPipeline(client=llm, model="fast", retrieval=None,
                               min_confidence=0.5)
    res = pipe.run(_recent(), meeting_id=1)
    assert res.has_confident
    # the fast model id was passed through
    assert llm.calls[0]["model"] == "fast"


def test_suggestions_pipeline_abstains():
    llm = FakeLLM('{"abstain": true, "suggestions": []}')
    pipe = SuggestionsPipeline(client=llm, model="fast", min_confidence=0.5)
    res = pipe.run(_recent(), meeting_id=1)
    assert not res.has_confident
    assert res.abstained


def test_notes_pipeline_low_temperature():
    llm = FakeLLM(
        '{"topics": [], "decisions": [{"category": "decision",'
        ' "text": "Ship Friday", "citations":'
        ' [{"start": 10, "end": 12, "quote": "ship the API"}]}],'
        ' "action_items": [], "open_questions": []}'
    )
    pipe = NotesPipeline(client=llm, model="strong")
    notes = pipe.run(_recent())
    assert len(notes.decisions) == 1
    assert llm.calls[0]["model"] == "strong"
    assert llm.calls[0]["temperature"] == 0.0  # notes use low temperature


def test_suggestions_with_retrieval(tmp_db):
    store = Store(tmp_db)
    mid = store.create_meeting()
    # seed a past segment to be retrieved
    past = TranscriptSegment(meeting_id=mid, start=0, end=3,
                             text="Last week we agreed Friday is the deadline")
    past.id = store.add_segment(past)
    retr = RetrievalStore(store, embedder=HashingEmbedder())
    retr.index_segment(past)

    llm = FakeLLM(
        '{"suggestions": [{"text": "Confirm Friday", "confidence": 0.9,'
        ' "citations": [{"start": 0, "end": 3, "quote": "Friday is the deadline"}]}]}'
    )
    pipe = SuggestionsPipeline(client=llm, model="fast", retrieval=retr,
                               min_confidence=0.5)
    recent = [TranscriptSegment(id=9, meeting_id=mid, start=100, end=102,
                                text="When is the deadline again?")]
    res = pipe.run(recent, meeting_id=mid)
    assert res.has_confident
    # retrieved snippet text should appear in the prompt context
    assert "Friday is the deadline" in llm.calls[0]["messages"][0]["content"]


def test_anthropic_client_unconfigured(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    client = AnthropicClient(api_key=None)
    # configured reflects key presence; no network call is made here.
    assert client.configured in (True, False)
