"""Local-first SQLite persistence.

Stores meetings, transcript segments, notes, suggestions, and segment
embeddings. Audio is never stored here. The store is intentionally synchronous
and small; callers run it off the UI thread.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Iterable, List, Optional

from copilot.core.models import TranscriptSegment

SCHEMA = """
CREATE TABLE IF NOT EXISTS meetings (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    title       TEXT,
    started_at  REAL NOT NULL,
    ended_at    REAL
);

CREATE TABLE IF NOT EXISTS segments (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id  INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    start       REAL NOT NULL,
    end         REAL NOT NULL,
    text        TEXT NOT NULL,
    speaker     TEXT,
    is_final    INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_segments_meeting ON segments(meeting_id);

CREATE TABLE IF NOT EXISTS notes (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id  INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    created_at  REAL NOT NULL,
    payload     TEXT NOT NULL          -- JSON-serialised Notes
);
CREATE INDEX IF NOT EXISTS idx_notes_meeting ON notes(meeting_id);

CREATE TABLE IF NOT EXISTS suggestions (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    meeting_id  INTEGER NOT NULL REFERENCES meetings(id) ON DELETE CASCADE,
    created_at  REAL NOT NULL,
    payload     TEXT NOT NULL          -- JSON-serialised SuggestionResponse
);

CREATE TABLE IF NOT EXISTS embeddings (
    segment_id  INTEGER PRIMARY KEY REFERENCES segments(id) ON DELETE CASCADE,
    dim         INTEGER NOT NULL,
    vector      BLOB NOT NULL          -- float32 little-endian
);
"""


class Store:
    """A thin wrapper over a SQLite database."""

    def __init__(self, db_path: Path | str):
        self.db_path = str(db_path)
        self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    # -- lifecycle ---------------------------------------------------------
    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- meetings ----------------------------------------------------------
    def create_meeting(self, title: Optional[str] = None) -> int:
        cur = self._conn.execute(
            "INSERT INTO meetings (title, started_at) VALUES (?, ?)",
            (title, time.time()),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def end_meeting(self, meeting_id: int) -> None:
        self._conn.execute(
            "UPDATE meetings SET ended_at = ? WHERE id = ?",
            (time.time(), meeting_id),
        )
        self._conn.commit()

    # -- segments ----------------------------------------------------------
    def add_segment(self, seg: TranscriptSegment) -> int:
        cur = self._conn.execute(
            "INSERT INTO segments (meeting_id, start, end, text, speaker, is_final)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (seg.meeting_id, seg.start, seg.end, seg.text, seg.speaker,
             1 if seg.is_final else 0),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def get_segments(self, meeting_id: int) -> List[TranscriptSegment]:
        rows = self._conn.execute(
            "SELECT * FROM segments WHERE meeting_id = ? ORDER BY start",
            (meeting_id,),
        ).fetchall()
        return [self._row_to_segment(r) for r in rows]

    def recent_segments(self, meeting_id: int, limit: int = 20) -> List[TranscriptSegment]:
        rows = self._conn.execute(
            "SELECT * FROM segments WHERE meeting_id = ? ORDER BY start DESC LIMIT ?",
            (meeting_id, limit),
        ).fetchall()
        return [self._row_to_segment(r) for r in reversed(rows)]

    def all_segments(self) -> List[TranscriptSegment]:
        rows = self._conn.execute("SELECT * FROM segments ORDER BY id").fetchall()
        return [self._row_to_segment(r) for r in rows]

    @staticmethod
    def _row_to_segment(r: sqlite3.Row) -> TranscriptSegment:
        return TranscriptSegment(
            id=r["id"],
            meeting_id=r["meeting_id"],
            start=r["start"],
            end=r["end"],
            text=r["text"],
            speaker=r["speaker"],
            is_final=bool(r["is_final"]),
        )

    # -- notes / suggestions ----------------------------------------------
    def save_notes(self, meeting_id: int, payload: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO notes (meeting_id, created_at, payload) VALUES (?, ?, ?)",
            (meeting_id, time.time(), payload),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    def latest_notes(self, meeting_id: int) -> Optional[str]:
        row = self._conn.execute(
            "SELECT payload FROM notes WHERE meeting_id = ? ORDER BY created_at DESC LIMIT 1",
            (meeting_id,),
        ).fetchone()
        return row["payload"] if row else None

    def save_suggestions(self, meeting_id: int, payload: str) -> int:
        cur = self._conn.execute(
            "INSERT INTO suggestions (meeting_id, created_at, payload) VALUES (?, ?, ?)",
            (meeting_id, time.time(), payload),
        )
        self._conn.commit()
        return int(cur.lastrowid)

    # -- embeddings --------------------------------------------------------
    def save_embedding(self, segment_id: int, vector: bytes, dim: int) -> None:
        self._conn.execute(
            "INSERT OR REPLACE INTO embeddings (segment_id, dim, vector) VALUES (?, ?, ?)",
            (segment_id, dim, vector),
        )
        self._conn.commit()

    def iter_embeddings(self) -> Iterable[tuple[int, int, bytes]]:
        for r in self._conn.execute("SELECT segment_id, dim, vector FROM embeddings"):
            yield r["segment_id"], r["dim"], r["vector"]

    # -- purge (privacy control) ------------------------------------------
    def purge_all(self) -> None:
        """Delete all stored data. Backs the tray "purge" control."""
        for table in ("embeddings", "suggestions", "notes", "segments", "meetings"):
            self._conn.execute(f"DELETE FROM {table}")
        self._conn.commit()
        self._conn.execute("VACUUM")
