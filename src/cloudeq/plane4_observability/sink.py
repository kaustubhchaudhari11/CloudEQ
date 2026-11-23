"""Source-data layer: the shared ``TelemetrySink`` port that every plane emits through."""

import logging
import threading
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from cloudeq.plane4_observability.bus import BusDeliveryError, EventBus
from cloudeq.plane4_observability.redaction import redact
from cloudeq.shared.contracts.models import PlaneName, TelemetryEnvelope
from cloudeq.shared.telemetry_validation import emit_checked

logger = logging.getLogger(__name__)


class FederatedTelemetrySink:
    """Validate, redact, then publish. Implements ``cloudeq.shared.ports.TelemetrySink``.

    A delivery failure does not abort the producing plane: the envelope is kept
    in ``undelivered`` (bounded) and counted so the loss is visible, not silent.
    """

    def __init__(self, bus: EventBus, *, max_payload_bytes: int = 1_048_576) -> None:
        self.bus = bus
        self.max_payload_bytes = max_payload_bytes
        self.undelivered: list[dict[str, Any]] = []
        self.delivered = 0
        self._lock = threading.Lock()

    def emit(self, envelope: TelemetryEnvelope) -> str:
        emit_checked(envelope, max_payload_bytes=self.max_payload_bytes)
        payload, hits_payload = redact(envelope.payload)
        attributes, hits_attrs = redact(envelope.attributes)
        hits = hits_payload + hits_attrs
        if hits:
            attributes = {**attributes, "redactions": hits}
        message = envelope.model_copy(update={"payload": payload, "attributes": attributes})
        document = message.model_dump(mode="json")
        try:
            self.bus.publish(envelope.trace_id, document)
        except BusDeliveryError as exc:
            with self._lock:
                if len(self.undelivered) < 1000:
                    self.undelivered.append(document)
            logger.error("telemetry delivery failed: %s", exc.reason)
            return envelope.event_id
        with self._lock:
            self.delivered += 1
        return envelope.event_id

    def emit_external(self, body: Any) -> TelemetryEnvelope:
        """Wrap a heterogeneous external event (schema-agnostic ingestion)."""

        found: dict[str, Any] = body if isinstance(body, dict) else {}
        trace = found.get("trace_id") or found.get("traceId") or found.get("correlation_id")
        event_id = found.get("event_id") or found.get("eventId") or str(uuid4())
        task = found.get("task_id") or found.get("taskId")
        envelope = TelemetryEnvelope(
            event_id=str(event_id),
            trace_id=str(trace or uuid4()),
            source=PlaneName.PLANE4_OBSERVABILITY,
            event_name="external.event",
            occurred_at=datetime.now(UTC),
            payload=body,
            task_id=str(task) if task else None,
            attributes={"ingest": "external"},
        )
        self.emit(envelope)
        return envelope
