from copilot.core.models import TranscriptSegment
from copilot.store.db import Store


def test_store_meeting_and_segments(tmp_db):
    s = Store(tmp_db)
    mid = s.create_meeting("standup")
    sid = s.add_segment(TranscriptSegment(meeting_id=mid, start=0, end=1, text="hello"))
    assert sid > 0
    segs = s.get_segments(mid)
    assert len(segs) == 1 and segs[0].text == "hello"
    s.end_meeting(mid)
    s.close()


def test_recent_segments_order(tmp_db):
    s = Store(tmp_db)
    mid = s.create_meeting()
    for i in range(5):
        s.add_segment(TranscriptSegment(meeting_id=mid, start=i, end=i + 1, text=f"t{i}"))
    recent = s.recent_segments(mid, limit=2)
    assert [r.text for r in recent] == ["t3", "t4"]


def test_notes_and_suggestions_roundtrip(tmp_db):
    s = Store(tmp_db)
    mid = s.create_meeting()
    s.save_notes(mid, '{"topics": []}')
    assert s.latest_notes(mid) == '{"topics": []}'
    s.save_suggestions(mid, '{"suggestions": []}')


def test_embedding_persist(tmp_db):
    import numpy as np

    s = Store(tmp_db)
    mid = s.create_meeting()
    sid = s.add_segment(TranscriptSegment(meeting_id=mid, start=0, end=1, text="x"))
    vec = np.ones(8, dtype=np.float32)
    s.save_embedding(sid, vec.tobytes(), 8)
    rows = list(s.iter_embeddings())
    assert len(rows) == 1 and rows[0][0] == sid and rows[0][1] == 8


def test_purge_all(tmp_db):
    s = Store(tmp_db)
    mid = s.create_meeting()
    s.add_segment(TranscriptSegment(meeting_id=mid, start=0, end=1, text="x"))
    s.purge_all()
    assert s.all_segments() == []


def test_foreign_key_cascade(tmp_db):
    s = Store(tmp_db)
    mid = s.create_meeting()
    sid = s.add_segment(TranscriptSegment(meeting_id=mid, start=0, end=1, text="x"))
    import numpy as np

    s.save_embedding(sid, np.ones(2, dtype=np.float32).tobytes(), 2)
    s._conn.execute("DELETE FROM meetings WHERE id = ?", (mid,))
    s._conn.commit()
    assert list(s.iter_embeddings()) == []  # cascaded
