"""FOAP processing and storage flow.

producer -> TelemetrySink -> EventBus -> ingest():
    1. validate envelope        (rejects are counted, never stored half-way)
    2. store RAW first          (duplicate event_id is idempotent)
    3. normalize -> CANONICAL   (failure keeps raw, records an attempt, retry later)
"""

import json
import logging
import threading
from collections import Counter, defaultdict
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from pydantic import ValidationError

from cloudeq.plane4_observability.normalizer import NormalizationError, Normalizer
from cloudeq.plane4_observability.records import (
    CanonicalEvent,
    NormalizationAttempt,
    NormalizationStatus,
    RawRecord,
)
from cloudeq.plane4_observability.storage import ObservabilityStore
from cloudeq.shared.contracts.models import EnvelopeRejected, TelemetryEnvelope
from cloudeq.shared.telemetry_validation import emit_checked

logger = logging.getLogger(__name__)


def _now() -> str:
    return datetime.now(UTC).isoformat()


class ObservabilityPipeline:
    def __init__(
        self,
        store: ObservabilityStore,
        normalizer: Normalizer,
        *,
        schema_version: str = "1",
        max_payload_bytes: int = 1_048_576,
        retention_days: tuple[int | None, int | None] = (None, None),
        fallback_normalizer: Normalizer | None = None,
    ) -> None:
        self.store = store
        self.normalizer = normalizer
        self.fallback_normalizer = fallback_normalizer
        self.schema_version = schema_version
        self.max_payload_bytes = max_payload_bytes
        self.retention_days = retention_days
        self.counters: Counter[str] = Counter()
        self._lock = threading.RLock()

    # ---------------------------------------------------------------- ingest
    def ingest(self, message: dict[str, Any]) -> str:
        """Consume one bus message. Returns accepted | duplicate | conflict | rejected."""

        try:
            envelope = TelemetryEnvelope.model_validate(message)
            emit_checked(envelope, max_payload_bytes=self.max_payload_bytes)
        except (ValidationError, EnvelopeRejected) as exc:
            with self._lock:
                self.counters["rejected"] += 1
            logger.warning("telemetry envelope rejected: %s", type(exc).__name__)
            return "rejected"
        envelope_doc = envelope.model_dump(mode="json")
        record = RawRecord(
            event_id=envelope.event_id,
            trace_id=envelope.trace_id,
            task_id=envelope.task_id,
            source=envelope.source.value,
            event_name=envelope.event_name,
            occurred_at=envelope.occurred_at.isoformat(),
            ingested_at=_now(),
            envelope=envelope_doc,
            raw=json.dumps(envelope_doc, separators=(",", ":"), ensure_ascii=False),
            redactions=int(envelope.attributes.get("redactions", 0) or 0),
        )
        outcome = self.store.insert_raw(record)
        with self._lock:
            self.counters[outcome if outcome != "inserted" else "accepted"] += 1
        if outcome != "inserted":
            return outcome
        self.process(record.event_id)
        return "accepted"

    # ----------------------------------------------------------- normalize
    def process(
        self, event_id: str, *, normalizer: Normalizer | None = None
    ) -> NormalizationStatus:
        record = self.store.get_raw(event_id)
        if record is None:
            raise KeyError(event_id)
        chosen = normalizer or self.normalizer
        attempt_no = record.normalization_attempts + 1
        error: str | None = None
        canonical: CanonicalEvent | None = None
        try:
            canonical = chosen.normalize(record, schema_version=self.schema_version)
        except NormalizationError as exc:
            error = exc.reason
        except Exception as exc:  # a normalizer bug must never drop the raw event
            error = f"Normalizer crashed: {type(exc).__name__}."
        if canonical is not None and (
            canonical.event_id != record.event_id or canonical.trace_id != record.trace_id
        ):
            canonical, error = None, "Normalizer changed the event identity; output discarded."
        status = NormalizationStatus.NORMALIZED if canonical else NormalizationStatus.FAILED
        self.store.add_attempt(
            NormalizationAttempt(
                attempt_id=str(uuid4()),
                event_id=record.event_id,
                trace_id=record.trace_id,
                attempt=attempt_no,
                normalizer=chosen.name + (f":{chosen.model_id}" if chosen.model_id else ""),
                status=status,
                error=error,
                at=_now(),
            )
        )
        if canonical is not None:
            self.store.upsert_canonical(canonical)
        record.normalization_status = status
        record.normalization_attempts = attempt_no
        record.last_error = error
        self.store.update_raw(record)
        with self._lock:
            self.counters["normalized" if canonical else "normalization_failed"] += 1
        if canonical is None and self.fallback_normalizer is not None and normalizer is None:
            return self.process(event_id, normalizer=self.fallback_normalizer)
        return status

    def retry_failed(
        self, *, limit: int = 100, normalizer: Normalizer | None = None
    ) -> dict[str, int]:
        results = {"retried": 0, "normalized": 0, "still_failed": 0}
        for record in self.store.list_raw(status=NormalizationStatus.FAILED, limit=limit):
            results["retried"] += 1
            status = self.process(record.event_id, normalizer=normalizer)
            key = "normalized" if status is NormalizationStatus.NORMALIZED else "still_failed"
            results[key] += 1
        with self._lock:
            self.counters["retries"] += results["retried"]
        return results

    def apply_retention(self) -> dict[str, int]:
        raw_days, canonical_days = self.retention_days
        if raw_days is None and canonical_days is None:
            return {"raw": 0, "canonical": 0, "skipped": 1}
        return self.store.purge(raw_days=raw_days, canonical_days=canonical_days)

    # --------------------------------------------------------------- read
    def trace(self, trace_id: str) -> dict[str, Any]:
        raw = sorted(
            self.store.list_raw(trace_id=trace_id, limit=2000), key=lambda r: r.occurred_at
        )
        canonical = {
            c.event_id: c for c in self.store.list_canonical(trace_id=trace_id, limit=2000)
        }
        events = []
        for record in raw:
            item = canonical.get(record.event_id)
            events.append(
                {
                    "raw": record.model_dump(mode="json"),
                    "canonical": item.model_dump(mode="json", by_alias=True) if item else None,
                }
            )
        return {"trace_id": trace_id, "event_count": len(events), "events": events}

    def metrics(self, *, sample: int = 5000) -> dict[str, Any]:
        raw = self.store.list_raw(limit=sample)
        canonical = self.store.list_canonical(limit=sample)
        by_plane = Counter(r.source for r in raw)
        by_norm = Counter(r.normalization_status.value for r in raw)
        by_status = Counter(c.status for c in canonical)
        runs: dict[str, dict[str, Any]] = {}
        iterations: dict[str, int] = defaultdict(int)
        latencies: list[float] = []
        per_minute: Counter[str] = Counter()
        for r in raw:
            payload = r.envelope.get("payload")
            per_minute[r.occurred_at[:16]] += 1
            if not isinstance(payload, dict):
                continue
            if r.event_name == "agents.run_finished":
                runs[r.trace_id] = {"state": payload.get("state"), "at": r.occurred_at}
            elif r.event_name == "agents.repair_iteration":
                iterations[r.trace_id] += 1
            elif r.event_name == "runtime.operation_completed":
                value = payload.get("duration_ms")
                if isinstance(value, int | float):
                    latencies.append(float(value))
        states = Counter(str(v["state"]) for v in runs.values())
        total_norm = by_norm.get("normalized", 0) + by_norm.get("failed", 0)
        with self._lock:
            counters = dict(self.counters)
        return {
            "generated_at": _now(),
            "totals": {
                "raw_events": len(raw),
                "canonical_events": len(canonical),
                "traces": len({r.trace_id for r in raw}),
                "agent_runs": len(runs),
                "repair_iterations": sum(iterations.values()),
            },
            "events_by_plane": dict(by_plane),
            "normalization": {
                **{k: by_norm.get(k, 0) for k in ("normalized", "failed", "pending")},
                "success_rate": round(by_norm.get("normalized", 0) / total_norm, 4)
                if total_norm
                else None,
            },
            "canonical_status": {k: by_status.get(k, 0) for k in ("SUCCESS", "FAILED", "ERROR")},
            "run_states": dict(states),
            "repair_iterations_by_trace": dict(iterations),
            "runtime_latency_ms": {
                "count": len(latencies),
                "avg": round(sum(latencies) / len(latencies), 2) if latencies else None,
                "max": max(latencies) if latencies else None,
            },
            "events_per_minute": [
                {"minute": k, "events": v} for k, v in sorted(per_minute.items())[-60:]
            ],
            "pipeline_counters": counters,
        }
