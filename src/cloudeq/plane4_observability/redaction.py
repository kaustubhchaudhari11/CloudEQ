"""Secret filtering applied before telemetry is retained.

Raw fidelity: the raw store keeps the event exactly as accepted *after* this
redaction step. Values that look like credentials are replaced by a fixed
marker; nothing else in the payload is changed, reordered, or dropped.
"""

import re
from collections.abc import Mapping
from typing import Any

REDACTED = "[REDACTED]"

SECRET_KEY_PARTS = (
    "api_key",
    "apikey",
    "token",
    "password",
    "passwd",
    "secret",
    "authorization",
    "cookie",
    "private_key",
    "credential",
)

_SECRET_VALUE_PATTERNS = (
    re.compile(r"AIza[0-9A-Za-z_\-]{30,}"),  # Google API keys
    re.compile(r"gh[pousr]_[0-9A-Za-z]{30,}"),  # GitHub tokens
    re.compile(r"sk-[0-9A-Za-z_\-]{20,}"),  # generic provider keys
    re.compile(r"(?i)bearer\s+[0-9A-Za-z._\-]{16,}"),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"),
)


def is_secret_key(key: str) -> bool:
    folded = key.casefold().replace("-", "_")
    return any(part in folded for part in SECRET_KEY_PARTS)


def redact(value: Any) -> tuple[Any, int]:
    """Return a redacted copy and the number of values replaced."""

    if isinstance(value, Mapping):
        out: dict[str, Any] = {}
        count = 0
        for key, item in value.items():
            if is_secret_key(str(key)) and item not in (None, "", False):
                out[str(key)] = REDACTED
                count += 1
            else:
                cleaned, found = redact(item)
                out[str(key)] = cleaned
                count += found
        return out, count
    if isinstance(value, list):
        items: list[Any] = []
        count = 0
        for item in value:
            cleaned, found = redact(item)
            items.append(cleaned)
            count += found
        return items, count
    if isinstance(value, str):
        text = value
        count = 0
        for pattern in _SECRET_VALUE_PATTERNS:
            text, found = pattern.subn(REDACTED, text)
            count += found
        return text, count
    return value, 0
