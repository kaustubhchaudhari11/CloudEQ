"""Shared fixtures for Plane 1. No live services."""

import httpx
from fastapi.testclient import TestClient

from cloudeq.plane1_intake.adapters import InMemoryTaskHandoff, InMemoryTelemetrySink
from cloudeq.plane1_intake.api.app import create_app
from cloudeq.plane1_intake.service import IntakeService
from cloudeq.plane1_intake.settings import Settings
from cloudeq.shared.ports.protocols import GeminiTransport


def settings(**overrides: object) -> Settings:
    values: dict[str, object] = {
        "cloudeq_router_mode": "offline",
        "cloudeq_gemini_live_calls": False,
        "gemini_api_key": "",
        "gemini_router_model": "",
        "cloudeq_github_issues_enabled": False,
        "cloudeq_jira_enabled": False,
        "cloudeq_log_level": "WARNING",
    }
    values.update(overrides)
    return Settings(**values)  # type: ignore[arg-type]


class SpyTransport:
    def __init__(self, text: str = "", *, error: Exception | None = None) -> None:
        self.text = text
        self.error = error
        self.calls: list[tuple[str, str, str]] = []

    def generate(self, *, model: str, api_key: str, user_text: str) -> str:
        self.calls.append((model, api_key, user_text))
        if self.error is not None:
            raise self.error
        return self.text


def service_for(
    *,
    configured: Settings | None = None,
    transport: GeminiTransport | None = None,
    handoff: InMemoryTaskHandoff | None = None,
    sink: InMemoryTelemetrySink | None = None,
) -> tuple[IntakeService, InMemoryTelemetrySink, InMemoryTaskHandoff]:
    chosen = configured or settings()
    memory = sink or InMemoryTelemetrySink(chosen.cloudeq_telemetry_max_payload_bytes)
    port = handoff or InMemoryTaskHandoff()
    intake = IntakeService.from_settings(chosen, transport=transport, handoff=port, sink=memory)
    return intake, memory, port


def client_for(intake: IntakeService) -> TestClient:
    return TestClient(create_app(intake))


def gemini_http(handler: httpx.MockTransport) -> httpx.Client:
    return httpx.Client(transport=handler)
