"""CLI status vocabulary matches the API."""

import json
import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest
from tests.plane1.support import client_for, service_for

from cloudeq.plane1_intake.cli import main


@pytest.fixture
def isolated_cli(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> Iterator[Path]:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("CLOUDEQ_ROUTER_MODE", "offline")
    monkeypatch.setenv("CLOUDEQ_GEMINI_LIVE_CALLS", "false")
    monkeypatch.setenv("GEMINI_API_KEY", "")
    monkeypatch.setenv("GEMINI_ROUTER_MODEL", "")
    yield tmp_path


def test_cli_hands_off_the_same_status_as_the_api(
    isolated_cli: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["submit", "--prompt", "Build a CLI"])
    assert code == 0
    body = json.loads(capsys.readouterr().out)
    assert body["status"] == "handed_off"
    assert body["source"] == "cli"
    assert body["execution_started"] is False
    assert body["feasibility"]["status"] == "feasible"
    intake, _sink, _handoff = service_for()
    api = client_for(intake).post("/tasks", json={"source": "api", "prompt": "Build a CLI"})
    assert api.json()["status"] == body["status"]
    assert api.json()["execution_started"] is body["execution_started"]


def test_cli_rejects_a_blank_prompt(isolated_cli: Path, capsys: pytest.CaptureFixture[str]) -> None:
    code = main(["submit", "--prompt", "  "])
    assert code == 2
    body = json.loads(capsys.readouterr().out)
    assert body["status"] == "rejected"
    assert body["task_id"] is None
    assert "prompt must not be empty" in body["reasons"]


def test_cli_dataset_flag_is_infeasible(
    isolated_cli: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    code = main(["submit", "--prompt", "Use the corpus", "--dataset", "corpus-v1"])
    assert code == 0
    body = json.loads(capsys.readouterr().out)
    assert body["status"] == "routed"
    assert body["feasibility"]["dataset_check"] == "failed"
    assert body["execution_started"] is False


def test_module_entrypoint_submits_offline(isolated_cli: Path) -> None:
    env = os.environ.copy()
    root = Path(__file__).resolve().parents[2]
    env["PYTHONPATH"] = str(root / "src")
    completed = subprocess.run(
        [sys.executable, "-m", "cloudeq.plane1_intake", "submit", "--prompt", "Build a CLI"],
        cwd=isolated_cli,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    body = json.loads(completed.stdout)
    assert body["status"] == "handed_off"
    assert body["execution_started"] is False
    assert body["trace_id"]
