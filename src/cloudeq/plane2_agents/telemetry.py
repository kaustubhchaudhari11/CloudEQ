"""In-memory telemetry for Plane 2. It does not talk to Kafka or MongoDB."""

from cloudeq.shared.contracts.models import TelemetryEnvelope
from cloudeq.shared.telemetry_validation import emit_checked


class MemoryTelemetrySink:
    def __init__(self, max_payload_bytes: int = 1_048_576) -> None:
        self.events: list[TelemetryEnvelope] = []
        self._max_payload_bytes = max_payload_bytes

    def emit(self, envelope: TelemetryEnvelope) -> str:
        emit_checked(envelope, max_payload_bytes=self._max_payload_bytes)
        self.events.append(envelope)
        return envelope.event_id
