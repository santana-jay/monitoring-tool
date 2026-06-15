import numpy as np

from copilot.core.models import TranscriptSegment
from copilot.retrieval.embeddings import HashingEmbedder, default_embedder
from copilot.retrieval.store import RetrievalStore
from copilot.store.db import Store


def _seed(store, texts, meeting_id=None):
    mid = meeting_id or store.create_meeting()
    segs = []
    for i, t in enumerate(texts):
        seg = TranscriptSegment(meeting_id=mid, start=i * 5, end=i * 5 + 4, text=t)
        seg.id = store.add_segment(seg)
        segs.append(seg)
    return mid, segs


def test_hashing_embedder_normalised():
    emb = HashingEmbedder(dim=64)
    v = emb.embed_one("ship the api on friday")
    assert abs(np.linalg.norm(v) - 1.0) < 1e-5


def test_hashing_embedder_deterministic():
    emb = HashingEmbedder(dim=64)
    assert np.allclose(emb.embed_one("hello world"), emb.embed_one("hello world"))


def test_search_returns_relevant(tmp_db):
    store = Store(tmp_db)
    mid, segs = _seed(store, [
        "We decided to ship the API on Friday",
        "The database migration is risky",
        "Lunch options for the offsite",
    ])
    r = RetrievalStore(store, embedder=HashingEmbedder())
    for seg in segs:
        r.index_segment(seg)
    res = r.search("when do we ship the API", k=2)
    assert res
    assert "API" in res[0].segment.text


def test_search_exclude_after(tmp_db):
    store = Store(tmp_db)
    mid, segs = _seed(store, ["alpha beta", "gamma delta"])
    r = RetrievalStore(store, embedder=HashingEmbedder())
    for seg in segs:
        r.index_segment(seg)
    # exclude segments starting at/after t=5 (the second segment)
    res = r.search("gamma delta", k=5, exclude_after=5)
    assert all(s.segment.start < 5 for s in res)


def test_search_empty_index(tmp_db):
    store = Store(tmp_db)
    r = RetrievalStore(store, embedder=HashingEmbedder())
    assert r.search("anything") == []


def test_persistence_across_instances(tmp_db):
    store = Store(tmp_db)
    mid, segs = _seed(store, ["persisted vector content"])
    r1 = RetrievalStore(store, embedder=HashingEmbedder())
    r1.index_segment(segs[0])
    # New retrieval store should load existing embeddings from the db.
    r2 = RetrievalStore(store, embedder=HashingEmbedder())
    assert r2.size == 1
    assert r2.search("persisted vector content", k=1)


def test_snippet_as_citation(tmp_db):
    store = Store(tmp_db)
    mid, segs = _seed(store, ["cite me"])
    r = RetrievalStore(store, embedder=HashingEmbedder())
    r.index_segment(segs[0])
    res = r.search("cite me", k=1)
    cite = res[0].as_citation()
    assert cite.segment_id == segs[0].id
    assert cite.quote == "cite me"
