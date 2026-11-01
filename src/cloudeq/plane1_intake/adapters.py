"""In-memory telemetry and handoff adapters for Plane 1 tests and local intake."""

from cloudeq.shared.contracts.models import (
    EnvelopeRejected,
    HandoffAcknowledgement,
    HandoffRequest,
    TelemetryEnvelope,
)
from cloudeq.shared.telemetry_validation import emit_checked


class InMemoryTelemetrySink:
    """Stores accepted envelopes. Duplicate ``event_id`` values are idempotent."""

    def __init__(self, max_payload_bytes: int = 1_048_576) -> None:
        self.max_payload_bytes = max_payload_bytes
        self.events: list[TelemetryEnvelope] = []
        self._by_id: dict[str, TelemetryEnvelope] = {}

    def emit(self, envelope: TelemetryEnvelope) -> str:
        emit_checked(envelope, max_payload_bytes=self.max_payload_bytes)
        existing = self._by_id.get(envelope.event_id)
        if existing is not None:
            if existing.model_dump(mode="json") != envelope.model_dump(mode="json"):
                raise EnvelopeRejected("event_id was already accepted with a different envelope")
            return envelope.event_id
        self._by_id[envelope.event_id] = envelope
        self.events.append(envelope)
        return envelope.event_id


class InMemoryTaskHandoff:
    """Records the Plane 2 contract. This adapter does not run agents."""

    def __init__(self, *, accept: bool = True) -> None:
        self.requests: list[HandoffRequest] = []
        self._accept = accept

    def submit(self, handoff: HandoffRequest) -> HandoffAcknowledgement:
        self.requests.append(handoff)
        return HandoffAcknowledgement(
            task_id=handoff.task_id,
            trace_id=handoff.trace_id,
            accepted=self._accept,
            execution_started=False,
        )
