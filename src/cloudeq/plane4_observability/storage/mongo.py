"""MongoDB adapter for dual retention. Requires the optional ``mongo`` extra (pymongo).

Raw, canonical, and normalization-attempt documents live in three separate
collections. ``_id`` is the ``event_id`` so a replayed event cannot create a
second raw document. No TTL index is created: retention stays unset until
``FOAP_*_RETENTION_DAYS`` are chosen deliberately.
"""

from typing import Any

from cloudeq.plane4_observability.records import (
    CanonicalEvent,
    NormalizationAttempt,
    NormalizationStatus,
    RawRecord,
)
from cloudeq.plane4_observability.settings import ObservabilitySettings
from cloudeq.plane4_observability.storage import InsertOutcome, _cutoff, same_raw


class MongoStore:
    backend = "mongodb"

    def __init__(self, settings: ObservabilitySettings, *, client: Any | None = None) -> None:
        if client is None:
            try:
                from pymongo import MongoClient
            except ImportError as exc:  # pragma: no cover - depends on optional extra
                raise RuntimeError(
                    "MongoDB storage needs pymongo. Run: uv sync --extra mongo"
                ) from exc
            client = MongoClient(settings.mongodb_uri, serverSelectionTimeoutMS=5000)
        self._client = client
        database = client[settings.mongodb_database]
        self._raw = database[settings.mongodb_raw_collection]
        self._canonical = database[settings.mongodb_canonical_collection]
        self._attempts = database[settings.mongodb_normalization_collection]
        self._raw.create_index("trace_id")
        self._raw.create_index("normalization_status")
        self._canonical.create_index("trace_id")
        self._attempts.create_index("event_id")

    def insert_raw(self, record: RawRecord) -> InsertOutcome:
        existing = self.get_raw(record.event_id)
        if existing is not None:
            return "duplicate" if same_raw(existing, record) else "conflict"
        self._raw.insert_one({"_id": record.event_id, **record.model_dump(mode="json")})
        return "inserted"

    def get_raw(self, event_id: str) -> RawRecord | None:
        doc = self._raw.find_one({"_id": event_id})
        return RawRecord.model_validate(_strip(doc)) if doc else None

    def update_raw(self, record: RawRecord) -> None:
        self._raw.replace_one(
            {"_id": record.event_id}, {"_id": record.event_id, **record.model_dump(mode="json")}
        )

    def upsert_canonical(self, event: CanonicalEvent) -> None:
        self._canonical.replace_one(
            {"_id": event.event_id},
            {"_id": event.event_id, **event.model_dump(mode="json")},
            upsert=True,
        )

    def get_canonical(self, event_id: str) -> CanonicalEvent | None:
        doc = self._canonical.find_one({"_id": event_id})
        return CanonicalEvent.model_validate(_strip(doc)) if doc else None

    def add_attempt(self, attempt: NormalizationAttempt) -> None:
        self._attempts.insert_one({"_id": attempt.attempt_id, **attempt.model_dump(mode="json")})

    def list_raw(
        self,
        *,
        trace_id: str | None = None,
        status: NormalizationStatus | None = None,
        limit: int = 200,
    ) -> list[RawRecord]:
        query: dict[str, Any] = {}
        if trace_id is not None:
            query["trace_id"] = trace_id
        if status is not None:
            query["normalization_status"] = status.value
        cursor = self._raw.find(query).sort("occurred_at", -1).limit(limit)
        return [RawRecord.model_validate(_strip(doc)) for doc in cursor]

    def list_canonical(
        self, *, trace_id: str | None = None, limit: int = 200
    ) -> list[CanonicalEvent]:
        query = {} if trace_id is None else {"trace_id": trace_id}
        cursor = self._canonical.find(query).sort("timestamp", -1).limit(limit)
        return [CanonicalEvent.model_validate(_strip(doc)) for doc in cursor]

    def list_attempts(
        self, *, event_id: str | None = None, limit: int = 200
    ) -> list[NormalizationAttempt]:
        query = {} if event_id is None else {"event_id": event_id}
        cursor = self._attempts.find(query).sort("at", -1).limit(limit)
        return [NormalizationAttempt.model_validate(_strip(doc)) for doc in cursor]

    def purge(self, *, raw_days: int | None, canonical_days: int | None) -> dict[str, int]:
        removed = {"raw": 0, "canonical": 0}
        if canonical_days is not None:
            result = self._canonical.delete_many(
                {"ingest_timestamp": {"$lt": _cutoff(canonical_days)}}
            )
            removed["canonical"] = int(result.deleted_count)
        if raw_days is not None:
            kept = self._canonical.distinct("_id")
            result = self._raw.delete_many(
                {"ingested_at": {"$lt": _cutoff(raw_days)}, "_id": {"$nin": kept}}
            )
            removed["raw"] = int(result.deleted_count)
        return removed

    def close(self) -> None:
        self._client.close()


def _strip(doc: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in doc.items() if key != "_id"}
