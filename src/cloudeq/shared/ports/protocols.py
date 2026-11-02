"""Ports between planes. Implementations stay in the owning plane."""

from typing import Protocol

from cloudeq.shared.contracts.models import (
    ExecutionRequest,
    ExecutionResult,
    FeasibilityResult,
    HandoffAcknowledgement,
    HandoffRequest,
    RoutingRequest,
    TelemetryEnvelope,
)


class FeasibilityRouter(Protocol):
    def evaluate(self, request: RoutingRequest) -> FeasibilityResult:
        """Return a feasibility decision. Do not start agent execution."""


class TaskHandoff(Protocol):
    def submit(self, handoff: HandoffRequest) -> HandoffAcknowledgement:
        """Accept or refuse a feasible task. ``execution_started`` stays false here."""


class TelemetrySink(Protocol):
    def emit(self, envelope: TelemetryEnvelope) -> str:
        """Accept one envelope and return its stable ``event_id``."""


class GeminiTransport(Protocol):
    def generate(self, *, model: str, api_key: str, user_text: str) -> str:
        """Return the model text. Callers treat that text as data."""


class RuntimeExecutor(Protocol):
    def execute(self, request: ExecutionRequest) -> ExecutionResult:
        """Run one sandbox operation. Callers must not execute generated code themselves."""
