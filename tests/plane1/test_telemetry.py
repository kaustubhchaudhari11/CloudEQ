"""Telemetry envelope limits used by the intake sink."""

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from cloudeq.plane1_intake.adapters import InMemoryTelemetrySink
from cloudeq.shared.contracts.models import EnvelopeRejected, PlaneName, TelemetryEnvelope


def _envelope(**overrides: object) -> TelemetryEnvelope:
    values: dict[str, object] = {
        "event_id": str(uuid4()),
        "trace_id": str(uuid4()),
        "source": PlaneName.PLANE1_INTAKE,
        "event_name": "intake.submission_accepted",
        "occurred_at": datetime.now(UTC),
        "payload": {"note": "heterogeneous", "extra": {"nested": True}},
        "task_id": str(uuid4()),
        "attributes": {},
    }
    values.update(overrides)
    return TelemetryEnvelope(**values)  # type: ignore[arg-type]


def test_sink_accepts_different_payload_shapes_and_deduplicates() -> None:
    sink = InMemoryTelemetrySink()
    first = _envelope(payload={"rich": {"tokens": 3}})
    minimal = _envelope(payload={"status": "ok"})
    assert sink.emit(first) == first.event_id
    assert sink.emit(minimal) == minimal.event_id
    assert sink.emit(first) == first.event_id
    assert len(sink.events) == 2


def test_sink_rejects_secret_attribute_keys_and_oversized_payloads() -> None:
    sink = InMemoryTelemetrySink(max_payload_bytes=32)
    secret = _envelope(attributes={"Authorization": "nope"})
    with pytest.raises(EnvelopeRejected, match="not allowed"):
        sink.emit(secret)
    huge = _envelope(payload={"blob": "x" * 80})
    with pytest.raises(EnvelopeRejected, match="limit"):
        sink.emit(huge)
    assert sink.events == []


def test_conflicting_duplicate_event_id_is_rejected() -> None:
    sink = InMemoryTelemetrySink()
    event_id = str(uuid4())
    sink.emit(_envelope(event_id=event_id, payload={"n": 1}))
    with pytest.raises(EnvelopeRejected, match="different envelope"):
        sink.emit(_envelope(event_id=event_id, payload={"n": 2}))
    assert len(sink.events) == 1
