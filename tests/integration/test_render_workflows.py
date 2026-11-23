"""Template selection must not accidentally call the configured live providers."""

from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient

from cloudeq.plane1_intake.settings import Settings
from cloudeq.plane2_agents.settings import AgentSettings
from cloudeq.plane3_runtime.render_runner import RenderRuntimeSettings, RenderSandboxRunner
from cloudeq.plane3_runtime.settings import RuntimeSettings
from cloudeq.plane4_observability.factory import build_observability
from cloudeq.plane4_observability.settings import ObservabilitySettings
from cloudeq.platform.server import create_app
from cloudeq.platform.service import Platform
from cloudeq.platform.settings import PlatformSettings


class SandboxDouble:
    def __init__(self) -> None:
        self.sandboxes = self
        self.calls = 0
        self.cleaned = 0

    async def create(self, **kwargs: Any) -> SimpleNamespace:
        self.calls += 1
        return SimpleNamespace(id=f"sbx-{self.calls}")

    async def wait_until_running(self, *args: Any, **kwargs: Any) -> None:
        pass

    async def copy_to(self, *args: Any) -> None:
        pass

    async def exec(self, sid: str, command: str) -> Any:
        yield SimpleNamespace(stream="stdout", data="test feedback")
        yield SimpleNamespace(exit_code=1 if "forge-harness" in command and self.calls == 1 else 0)

    async def terminate(self, sid: str) -> None:
        self.cleaned += 1


def test_template_route_preserves_live_configuration_and_labels_mock(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    def forbidden(*args: Any, **kwargs: Any) -> None:
        raise AssertionError("Template workflow must not contact Gemini agents or router")

    monkeypatch.setattr("httpx.Client.post", forbidden)
    monkeypatch.setattr("cloudeq.platform.service.CrewAIGeminiStageClient", forbidden)
    wheels = tmp_path / "wheels"
    wheels.mkdir()
    (wheels / "pytest-9.2.0-py3-none-any.whl").write_bytes(b"test fixture")
    (wheels / "flask-3.1.3-py3-none-any.whl").write_bytes(b"test fixture")
    fake = SandboxDouble()
    runner = RenderSandboxRunner(
        RenderRuntimeSettings(
            render_api_key="test-only",
            render_workspace_id="tea-test",
            cloudeq_render_wheels_dir=str(wheels),
        ),
        client_factory=lambda: fake,
    )
    platform = Platform(
        settings=PlatformSettings(cloudeq_execution_mode="render"),
        observability=build_observability(
            ObservabilitySettings(cloudeq_observability_store="memory")
        ),
        intake_settings=Settings(
            cloudeq_router_mode="gemini",
            cloudeq_gemini_live_calls=True,
            gemini_api_key="test-only",
            gemini_router_model="test-model",
        ),
        agent_settings=AgentSettings(
            cloudeq_agent_engine="crewai",
            cloudeq_gemini_live_calls=True,
            gemini_api_key="test-only",
            gemini_agent_model="test-model",
        ),
        runtime_settings=RuntimeSettings(cloudeq_runtime_workspace_root=str(tmp_path / "work")),
        docker_runner=runner,
        runs_file=tmp_path / "runs.jsonl",
    )
    client = TestClient(create_app(platform))
    response = client.post(
        "/api/runs",
        json={
            "prompt": "Add a health check",
            "run_variant": "template",
            "simulated_failures": 1,
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["outcome"] == "passed"
    assert [i["passed"] for i in result["agents"]["iterations"]] == [False, True]
    assert result["agents"]["simulation"] is True
    assert result["agents"]["live_gemini"] is False
    assert result["details"]["runtime_backend"] == "render-sandbox-mock"
    assert len(result["details"]["generated_files"]) == 2
    assert fake.calls == fake.cleaned == 2
    assert platform.intake.settings.cloudeq_router_mode == "gemini"
