"""Bounded retries for temporary provider responses; never log credentials."""

import time
from typing import Any

import httpx

TRANSIENT_STATUS_CODES = (429, 500, 502, 503, 504)


def post_json_with_retry(
    client: httpx.Client,
    url: str,
    *,
    headers: dict[str, str],
    body: dict[str, Any],
    timeout_seconds: float,
) -> httpx.Response:
    deadline = time.monotonic() + timeout_seconds
    for attempt in range(3):
        remaining = max(0.001, deadline - time.monotonic())
        response = client.post(url, headers=headers, json=body, timeout=remaining)
        if response.status_code not in TRANSIENT_STATUS_CODES or attempt == 2:
            return response
        delay = float(2**attempt)
        try:
            delay = max(delay, min(10.0, float(response.headers.get("Retry-After", "0"))))
        except ValueError:
            pass
        if time.monotonic() + delay >= deadline:
            return response
        response.close()
        time.sleep(delay)
    raise AssertionError("unreachable")
