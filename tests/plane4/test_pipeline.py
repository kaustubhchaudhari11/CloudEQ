"""Plane 4: raw-first retention, idempotency, normalization failure, redaction, storage."""

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from cloudeq.plane4_observability.bus import BusDeliveryError, InProcessBus
from cloudeq.plane4_observability.factory import ObservabilityStack, build_observability
from cloudeq.plane4_observability.normalizer import (
    GeminiNormalizer,
    NormalizationError,
    OfflineNormalizer,
)
from cloudeq.plane4_observability.records import NormalizationStatus, RawRecord
from cloudeq.plane4_observability.redaction import REDACTED, redact
from cloudeq.plane4_observability.settings import ObservabilitySettings
from cloudeq.plane4_observability.sink import FederatedTelemetrySink
from cloudeq.plane4_observability.storage import MemoryStore, SQLiteStore
from cloudeq.shared.contracts.models import EnvelopeRejected, PlaneName, TelemetryEnvelope


def _stack(**overrides: Any) -> ObservabilityStack:
    settings = ObservabilitySettings(cloudeq_observability_store="memory", **overrides)
    return build_observability(settings)


def _envelope(event_id: str = "e-1", **payload: Any) -> TelemetryEnvelope:
    return TelemetryEnvelope(
        event_id=event_id,
        trace_id="trace-1",
        source=PlaneName.PLANE3_RUNTIME,
        event_name="runtime.operation_completed",
        occurred_at=datetime.now(UTC),
        payload=payload or {"operation": "run_tests", "passed": True, "duration_ms": 7},
        task_id="task-1",
    )


def test_event_is_stored_raw_then_canonical_with_linkage() -> None:
    stack = _stack()
    stack.sink.emit(_envelope())
    raw = stack.store.get_raw("e-1")
    canonical = stack.store.get_canonical("e-1")
    assert raw is not None and canonical is not None
    assert raw.normalization_status is NormalizationStatus.NORMALIZED
    assert canonical.trace_id == raw.trace_id == "trace-1"
    assert canonical.task_id == "task-1"
    assert canonical.schema_version == "1"
    assert canonical.normalizer == "offline-rules"
    assert canonical.status == "SUCCESS" and canonical.success is True
    assert canonical.job == "runtime:operation_completed"
    assert canonical.latency_ms == 7
    assert json.loads(canonical.raw)["event_id"] == "e-1"
    dumped = canonical.model_dump(by_alias=True)
    assert {"Timestamp", "ingestTimestamp", "parseError"} <= dumped.keys()


def test_failing_test_maps_to_failed_status() -> None:
    stack = _stack()
    stack.sink.emit(_envelope(operation="run_tests", passed=False, exit_code=1))
    canonical = stack.store.get_canonical("e-1")
    assert canonical is not None
    assert canonical.status == "FAILED" and canonical.success is False
    assert canonical.error_code


def test_duplicate_event_id_is_idempotent_and_conflict_is_counted() -> None:
    stack = _stack()
    envelope = _envelope()
    stack.sink.emit(envelope)
    stack.sink.emit(envelope)
    stack.sink.emit(_envelope(operation="run_tests", passed=False))  # same id, other content
    assert len(stack.store.list_raw()) == 1
    assert stack.pipeline.counters["duplicate"] == 1
    assert stack.pipeline.counters["conflict"] == 1


def test_malformed_external_event_keeps_raw_and_records_failure() -> None:
    stack = _stack()
    envelope = stack.sink.emit_external("<<not json>>")
    raw = stack.store.get_raw(envelope.event_id)
    assert raw is not None
    assert raw.normalization_status is NormalizationStatus.FAILED
    assert raw.last_error
    assert stack.store.get_canonical(envelope.event_id) is None
    attempts = stack.store.list_attempts(event_id=envelope.event_id)
    assert len(attempts) == 1 and attempts[0].status is NormalizationStatus.FAILED
    result = stack.pipeline.retry_failed()
    assert result == {"retried": 1, "normalized": 0, "still_failed": 1}
    assert stack.store.get_raw(envelope.event_id) is not None
    assert len(stack.store.list_attempts(event_id=envelope.event_id)) == 2


def test_schema_drift_is_normalized() -> None:
    stack = _stack()
    first = stack.sink.emit_external({"agent_id": "qa", "status": "ok", "latency_ms": 3})
    drifted = stack.sink.emit_external({"actor_id": "qa", "outcome": "failed", "elapsed_ms": 9})
    a = stack.store.get_canonical(first.event_id)
    b = stack.store.get_canonical(drifted.event_id)
    assert a is not None and b is not None
    assert a.actor_entity is not None and a.actor_entity.entity_id == "qa"
    assert b.actor_entity is not None and b.actor_entity.entity_id == "qa"
    assert (a.status, b.status) == ("SUCCESS", "FAILED")
    assert b.latency_ms == 9


def test_external_event_without_known_fields_fails_but_is_retained() -> None:
    stack = _stack()
    envelope = stack.sink.emit_external({"zzz": 1})
    raw = stack.store.get_raw(envelope.event_id)
    assert raw is not None and raw.normalization_status is NormalizationStatus.FAILED


def test_secret_values_are_redacted_before_storage() -> None:
    stack = _stack()
    stack.sink.emit(_envelope(note="key AIza" + "A" * 35, nested={"api_key": "abc"}))
    raw = stack.store.get_raw("e-1")
    assert raw is not None
    assert "AIza" not in raw.raw and "abc" not in raw.raw
    assert raw.envelope["payload"]["nested"]["api_key"] == REDACTED
    assert raw.envelope["attributes"]["redactions"] == 2


def test_secret_attribute_keys_are_rejected_at_the_sink() -> None:
    stack = _stack()
    bad = _envelope().model_copy(update={"attributes": {"token": "x"}})
    with pytest.raises(EnvelopeRejected):
        stack.sink.emit(bad)
    assert stack.store.list_raw() == []


def test_redact_counts_and_preserves_other_fields() -> None:
    cleaned, count = redact({"a": 1, "password": "p", "list": ["Bearer abcdefghijklmnopqrstu"]})
    assert count == 2
    assert cleaned["a"] == 1 and cleaned["password"] == REDACTED


def test_invalid_bus_message_is_rejected_not_stored() -> None:
    stack = _stack()
    assert stack.pipeline.ingest({"not": "an envelope"}) == "rejected"
    assert stack.store.list_raw() == []


def test_undelivered_events_are_visible_not_silently_lost() -> None:
    sink = FederatedTelemetrySink(InProcessBus())  # nobody subscribed
    sink.emit(_envelope())
    assert len(sink.undelivered) == 1
    with pytest.raises(BusDeliveryError):
        InProcessBus().publish("k", {})


def test_identity_cannot_be_changed_by_gemini_output() -> None:
    model_text = json.dumps(
        {
            "event_id": "evil",
            "trace_id": "evil",
            "event_type": "Runtime",
            "action": "tests",
            "status": "success",
            "message": "ok",
        }
    )
    normalizer = GeminiNormalizer(model_id="m", generate=lambda _m, _t: model_text)
    stack = build_observability(
        ObservabilitySettings(cloudeq_observability_store="memory"), normalizer=normalizer
    )
    stack.sink.emit(_envelope())
    canonical = stack.store.get_canonical("e-1")
    assert canonical is not None
    assert (canonical.event_id, canonical.trace_id) == ("e-1", "trace-1")
    assert canonical.normalizer == "gemini" and canonical.normalizer_model == "m"


def test_gemini_failures_keep_raw_and_can_be_retried_offline() -> None:
    def broken(_model: str, _text: str) -> str:
        return "this is not json"

    stack = build_observability(
        ObservabilitySettings(cloudeq_observability_store="memory"),
        normalizer=GeminiNormalizer(model_id="m", generate=broken),
    )
    stack.sink.emit(_envelope())
    raw = stack.store.get_raw("e-1")
    assert raw is not None and raw.normalization_status is NormalizationStatus.FAILED
    assert stack.pipeline.retry_failed(normalizer=OfflineNormalizer())["normalized"] == 1
    assert stack.store.get_canonical("e-1") is not None


def test_gemini_normalizer_is_not_built_without_explicit_settings() -> None:
    stack = _stack(cloudeq_normalizer_mode="gemini", cloudeq_gemini_live_calls=True)
    assert stack.pipeline.normalizer.name == "offline-rules"  # no key or model id: no call


def test_offline_normalizer_rejects_non_object_payload() -> None:
    record = RawRecord(
        event_id="x",
        trace_id="t",
        source="plane1_intake",
        event_name="intake.thing",
        occurred_at="2026-01-01T00:00:00+00:00",
        ingested_at="2026-01-01T00:00:00+00:00",
        envelope={"payload": [1, 2]},
        raw="{}",
    )
    with pytest.raises(NormalizationError):
        OfflineNormalizer().normalize(record, schema_version="1")


def test_retention_is_a_no_op_until_configured() -> None:
    stack = _stack()
    stack.sink.emit(_envelope())
    assert stack.pipeline.apply_retention()["skipped"] == 1
    assert len(stack.store.list_raw()) == 1


def test_sqlite_store_persists_across_instances(tmp_path: Path) -> None:
    path = tmp_path / "obs.sqlite3"
    settings = ObservabilitySettings(
        cloudeq_observability_store="sqlite", cloudeq_observability_sqlite_path=str(path)
    )
    first = build_observability(settings)
    first.sink.emit(_envelope())
    first.sink.emit_external("bad")
    first.close()
    store = SQLiteStore(path)
    assert store.get_raw("e-1") is not None and store.get_canonical("e-1") is not None
    assert len(store.list_raw(status=NormalizationStatus.FAILED)) == 1
    assert len(store.list_raw(trace_id="trace-1")) == 1
    assert len(store.list_attempts()) == 2
    store.close()


def test_memory_store_purge_respects_configured_days() -> None:
    store = MemoryStore()
    stack = build_observability(
        ObservabilitySettings(cloudeq_observability_store="memory"), store=store
    )
    stack.sink.emit(_envelope())
    assert store.purge(raw_days=1, canonical_days=1) == {"raw": 0, "canonical": 0}


def test_metrics_and_trace_views() -> None:
    stack = _stack()
    stack.sink.emit(_envelope())
    metrics = stack.pipeline.metrics()
    assert metrics["totals"]["raw_events"] == 1
    assert metrics["events_by_plane"] == {"plane3_runtime": 1}
    assert metrics["normalization"]["success_rate"] == 1.0
    trace = stack.pipeline.trace("trace-1")
    assert trace["event_count"] == 1 and trace["events"][0]["canonical"]["Timestamp"]
