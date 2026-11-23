"""Storage layer: raw and canonical records are kept separately (dual retention).

Raw rows are written before normalization starts, so a failed normalization
never loses the event. Rows are linked by ``event_id`` and ``trace_id``.
"""

import json
import sqlite3
import threading
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal, Protocol

from cloudeq.plane4_observability.records import (
    CanonicalEvent,
    NormalizationAttempt,
    NormalizationStatus,
    RawRecord,
)

InsertOutcome = Literal["inserted", "duplicate", "conflict"]


class ObservabilityStore(Protocol):
    backend: str

    def insert_raw(self, record: RawRecord) -> InsertOutcome: ...

    def get_raw(self, event_id: str) -> RawRecord | None: ...

    def update_raw(self, record: RawRecord) -> None: ...

    def upsert_canonical(self, event: CanonicalEvent) -> None: ...

    def get_canonical(self, event_id: str) -> CanonicalEvent | None: ...

    def add_attempt(self, attempt: NormalizationAttempt) -> None: ...

    def list_raw(
        self,
        *,
        trace_id: str | None = None,
        status: NormalizationStatus | None = None,
        limit: int = 200,
    ) -> list[RawRecord]: ...

    def list_canonical(
        self, *, trace_id: str | None = None, limit: int = 200
    ) -> list[CanonicalEvent]: ...

    def list_attempts(
        self, *, event_id: str | None = None, limit: int = 200
    ) -> list[NormalizationAttempt]: ...

    def purge(self, *, raw_days: int | None, canonical_days: int | None) -> dict[str, int]: ...

    def close(self) -> None: ...


def same_raw(left: RawRecord, right: RawRecord) -> bool:
    """Two submissions of one event_id are duplicates when their accepted content matches.

    ``occurred_at`` is excluded so a producer re-posting the same external event
    later is recognised as a duplicate rather than a conflicting rewrite.
    """

    keys = ("event_name", "trace_id", "source", "task_id", "payload")
    return all(left.envelope.get(k) == right.envelope.get(k) for k in keys)


def _cutoff(days: int) -> str:
    return (datetime.now(UTC) - timedelta(days=days)).isoformat()


class MemoryStore:
    backend = "memory"

    def __init__(self) -> None:
        self._lock = threading.RLock()
        self._raw: dict[str, RawRecord] = {}
        self._canonical: dict[str, CanonicalEvent] = {}
        self._attempts: list[NormalizationAttempt] = []

    def insert_raw(self, record: RawRecord) -> InsertOutcome:
        with self._lock:
            existing = self._raw.get(record.event_id)
            if existing is not None:
                return "duplicate" if same_raw(existing, record) else "conflict"
            self._raw[record.event_id] = record.model_copy(deep=True)
            return "inserted"

    def get_raw(self, event_id: str) -> RawRecord | None:
        with self._lock:
            found = self._raw.get(event_id)
            return found.model_copy(deep=True) if found else None

    def update_raw(self, record: RawRecord) -> None:
        with self._lock:
            self._raw[record.event_id] = record.model_copy(deep=True)

    def upsert_canonical(self, event: CanonicalEvent) -> None:
        with self._lock:
            self._canonical[event.event_id] = event.model_copy(deep=True)

    def get_canonical(self, event_id: str) -> CanonicalEvent | None:
        with self._lock:
            return self._canonical.get(event_id)

    def add_attempt(self, attempt: NormalizationAttempt) -> None:
        with self._lock:
            self._attempts.append(attempt)

    def list_raw(
        self,
        *,
        trace_id: str | None = None,
        status: NormalizationStatus | None = None,
        limit: int = 200,
    ) -> list[RawRecord]:
        with self._lock:
            rows = [
                r
                for r in self._raw.values()
                if (trace_id is None or r.trace_id == trace_id)
                and (status is None or r.normalization_status is status)
            ]
        rows.sort(key=lambda r: (r.occurred_at, r.ingested_at), reverse=True)
        return rows[:limit]

    def list_canonical(
        self, *, trace_id: str | None = None, limit: int = 200
    ) -> list[CanonicalEvent]:
        with self._lock:
            rows = [c for c in self._canonical.values() if trace_id in (None, c.trace_id)]
        rows.sort(key=lambda c: c.timestamp, reverse=True)
        return rows[:limit]

    def list_attempts(
        self, *, event_id: str | None = None, limit: int = 200
    ) -> list[NormalizationAttempt]:
        with self._lock:
            rows = [a for a in self._attempts if event_id in (None, a.event_id)]
        return list(reversed(rows))[:limit]

    def purge(self, *, raw_days: int | None, canonical_days: int | None) -> dict[str, int]:
        removed = {"raw": 0, "canonical": 0}
        with self._lock:
            if raw_days is not None:
                cut = _cutoff(raw_days)
                for key in [k for k, r in self._raw.items() if r.ingested_at < cut]:
                    del self._raw[key]
                    removed["raw"] += 1
            if canonical_days is not None:
                cut = _cutoff(canonical_days)
                for key in [k for k, c in self._canonical.items() if c.ingest_timestamp < cut]:
                    del self._canonical[key]
                    removed["canonical"] += 1
        return removed

    def close(self) -> None:
        return None


_SCHEMA = """
CREATE TABLE IF NOT EXISTS raw_events (
    event_id TEXT PRIMARY KEY,
    trace_id TEXT NOT NULL,
    task_id TEXT,
    source TEXT NOT NULL,
    event_name TEXT NOT NULL,
    occurred_at TEXT NOT NULL,
    ingested_at TEXT NOT NULL,
    normalization_status TEXT NOT NULL,
    doc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS raw_trace ON raw_events(trace_id);
CREATE INDEX IF NOT EXISTS raw_status ON raw_events(normalization_status);
CREATE TABLE IF NOT EXISTS canonical_events (
    event_id TEXT PRIMARY KEY REFERENCES raw_events(event_id),
    trace_id TEXT NOT NULL,
    task_id TEXT,
    status TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    ingest_timestamp TEXT NOT NULL,
    doc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS canonical_trace ON canonical_events(trace_id);
CREATE TABLE IF NOT EXISTS normalization_attempts (
    attempt_id TEXT PRIMARY KEY,
    event_id TEXT NOT NULL,
    trace_id TEXT NOT NULL,
    at TEXT NOT NULL,
    doc TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS attempts_event ON normalization_attempts(event_id);
"""


class SQLiteStore:
    """Persistent local store. One file, three tables, no server to install."""

    backend = "sqlite"

    def __init__(self, path: str | Path) -> None:
        target = Path(path).expanduser() if str(path) != ":memory:" else path
        if isinstance(target, Path):
            target.parent.mkdir(parents=True, exist_ok=True)
        self.path = str(target)
        self._lock = threading.RLock()
        self._db = sqlite3.connect(self.path, check_same_thread=False)
        self._db.execute("PRAGMA journal_mode=WAL")
        self._db.executescript(_SCHEMA)
        self._db.commit()

    def insert_raw(self, record: RawRecord) -> InsertOutcome:
        with self._lock:
            existing = self.get_raw(record.event_id)
            if existing is not None:
                return "duplicate" if same_raw(existing, record) else "conflict"
            self._db.execute(
                "INSERT INTO raw_events VALUES (?,?,?,?,?,?,?,?,?)",
                (
                    record.event_id,
                    record.trace_id,
                    record.task_id,
                    record.source,
                    record.event_name,
                    record.occurred_at,
                    record.ingested_at,
                    record.normalization_status.value,
                    record.model_dump_json(),
                ),
            )
            self._db.commit()
            return "inserted"

    def get_raw(self, event_id: str) -> RawRecord | None:
        with self._lock:
            row = self._db.execute(
                "SELECT doc FROM raw_events WHERE event_id = ?", (event_id,)
            ).fetchone()
        return RawRecord.model_validate_json(row[0]) if row else None

    def update_raw(self, record: RawRecord) -> None:
        with self._lock:
            self._db.execute(
                "UPDATE raw_events SET normalization_status = ?, doc = ? WHERE event_id = ?",
                (record.normalization_status.value, record.model_dump_json(), record.event_id),
            )
            self._db.commit()

    def upsert_canonical(self, event: CanonicalEvent) -> None:
        with self._lock:
            self._db.execute(
                "INSERT OR REPLACE INTO canonical_events VALUES (?,?,?,?,?,?,?)",
                (
                    event.event_id,
                    event.trace_id,
                    event.task_id,
                    event.status,
                    event.timestamp,
                    event.ingest_timestamp,
                    event.model_dump_json(),
                ),
            )
            self._db.commit()

    def get_canonical(self, event_id: str) -> CanonicalEvent | None:
        with self._lock:
            row = self._db.execute(
                "SELECT doc FROM canonical_events WHERE event_id = ?", (event_id,)
            ).fetchone()
        return CanonicalEvent.model_validate_json(row[0]) if row else None

    def add_attempt(self, attempt: NormalizationAttempt) -> None:
        with self._lock:
            self._db.execute(
                "INSERT INTO normalization_attempts VALUES (?,?,?,?,?)",
                (
                    attempt.attempt_id,
                    attempt.event_id,
                    attempt.trace_id,
                    attempt.at,
                    attempt.model_dump_json(),
                ),
            )
            self._db.commit()

    def list_raw(
        self,
        *,
        trace_id: str | None = None,
        status: NormalizationStatus | None = None,
        limit: int = 200,
    ) -> list[RawRecord]:
        clauses, params = _where(trace_id=trace_id, normalization_status=status)
        with self._lock:
            rows = self._db.execute(
                f"SELECT doc FROM raw_events{clauses} "
                "ORDER BY occurred_at DESC, ingested_at DESC LIMIT ?",
                (*params, limit),
            ).fetchall()
        return [RawRecord.model_validate_json(row[0]) for row in rows]

    def list_canonical(
        self, *, trace_id: str | None = None, limit: int = 200
    ) -> list[CanonicalEvent]:
        clauses, params = _where(trace_id=trace_id)
        with self._lock:
            rows = self._db.execute(
                f"SELECT doc FROM canonical_events{clauses} ORDER BY timestamp DESC LIMIT ?",
                (*params, limit),
            ).fetchall()
        return [CanonicalEvent.model_validate_json(row[0]) for row in rows]

    def list_attempts(
        self, *, event_id: str | None = None, limit: int = 200
    ) -> list[NormalizationAttempt]:
        clauses, params = _where(event_id=event_id)
        with self._lock:
            rows = self._db.execute(
                f"SELECT doc FROM normalization_attempts{clauses} ORDER BY at DESC LIMIT ?",
                (*params, limit),
            ).fetchall()
        return [NormalizationAttempt.model_validate_json(row[0]) for row in rows]

    def purge(self, *, raw_days: int | None, canonical_days: int | None) -> dict[str, int]:
        removed = {"raw": 0, "canonical": 0}
        with self._lock:
            if canonical_days is not None:
                cur = self._db.execute(
                    "DELETE FROM canonical_events WHERE ingest_timestamp < ?",
                    (_cutoff(canonical_days),),
                )
                removed["canonical"] = cur.rowcount
            if raw_days is not None:
                cur = self._db.execute(
                    "DELETE FROM raw_events WHERE ingested_at < ? AND event_id NOT IN "
                    "(SELECT event_id FROM canonical_events)",
                    (_cutoff(raw_days),),
                )
                removed["raw"] = cur.rowcount
            self._db.commit()
        return removed

    def close(self) -> None:
        with self._lock:
            self._db.close()


def _where(**filters: object) -> tuple[str, tuple[object, ...]]:
    parts: list[str] = []
    params: list[object] = []
    for column, value in filters.items():
        if value is None:
            continue
        parts.append(f"{column} = ?")
        params.append(value.value if isinstance(value, NormalizationStatus) else value)
    return ((" WHERE " + " AND ".join(parts)) if parts else ""), tuple(params)


def dumps(value: object) -> str:
    return json.dumps(value, separators=(",", ":"), ensure_ascii=False, default=str)
