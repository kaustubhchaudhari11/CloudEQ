"""Envelope checks that do not impose a payload schema."""

import json
from collections.abc import Mapping
from typing import Any

from cloudeq.shared.contracts.models import EnvelopeRejected, TelemetryEnvelope

SECRET_ATTRIBUTE_KEYS = frozenset({"api_key", "token", "password", "secret", "authorization"})


def emit_checked(envelope: TelemetryEnvelope, *, max_payload_bytes: int) -> None:
    if envelope.envelope_version != "1":
        raise EnvelopeRejected("envelope_version must be 1")
    if not envelope.event_id or not envelope.trace_id or not envelope.event_name:
        raise EnvelopeRejected("event_id, trace_id, and event_name are required")
    if envelope.occurred_at.tzinfo is None or envelope.occurred_at.utcoffset() is None:
        raise EnvelopeRejected("occurred_at must be timezone-aware UTC")
    _reject_secret_keys(envelope.attributes)
    size = _payload_size(envelope.payload)
    if size > max_payload_bytes:
        raise EnvelopeRejected(f"payload is {size} bytes; the limit is {max_payload_bytes} bytes")


def _payload_size(payload: Any) -> int:
    try:
        encoded = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    except (TypeError, ValueError) as exc:
        raise EnvelopeRejected("payload must be JSON") from exc
    return len(encoded)


def _reject_secret_keys(attributes: Mapping[str, Any]) -> None:
    for key in _keys(attributes):
        if key.casefold() in SECRET_ATTRIBUTE_KEYS:
            raise EnvelopeRejected(f"attribute key '{key}' is not allowed in telemetry")


def _keys(value: object) -> list[str]:
    found: list[str] = []
    if isinstance(value, Mapping):
        for key, item in value.items():
            found.append(str(key))
            found.extend(_keys(item))
    elif isinstance(value, list):
        for item in value:
            found.extend(_keys(item))
    return found
