# FORGE SPAN implementation status

Product: FORGE SPAN. Team: Cloud EQ. Technical identifiers remain `CloudEQ` / `cloudeq`.

Plane 1 intake, the Plane 2 offline agent engine, and the CrewAI boundary are on `main` through pull request #4. This branch adds the Plane 3 Docker runtime. Plane 4 is not implemented. The default agent engine remains the offline simulation. Live Gemini was not called.

## Current session

- Date checked: 2026-11-03.
- Git root: `C:/Users/kaust/projects/CloudEQ`.
- Branch: `feature/plane3-runtime`, from `2e19e98` (merge of pull request #4). The Plane 3 milestone was verified before its pull request.
- Remote remains `https://github.com/kaustubhchaudhari11/CloudEQ.git`.
- No Gemini request was sent. Docker CLI 25.0.3 is installed. `docker info` failed because the engine pipe `docker_engine` was not available, so the live container smoke test was not run. Kafka, MongoDB, and Grafana were not started. Generated code was not run on the host. Unit tests injected a Docker command runner.

## Plane 1 behavior

- `GET /health` reports the intake plane and `execution_available: false`.
- `POST /tasks` validates an API prompt, assigns `task_id` and `trace_id`, and returns `rejected`, `routed`, or `handed_off`.
- `cloudeq-intake submit` prints the same result fields. Exit 2 is validation rejection. Exit 0 is a completed routing decision.
- The default router is deterministic and offline. A named dataset is infeasible because no catalog exists.
- The Gemini router calls `models.generateContent` only when mode, live-call flag, API key, and an explicit model ID are all set. Tests inject the HTTP client. Malformed output and timeouts stay `routed` with feasibility `error` and do not hand off.
- The handoff port records the contract in memory. `execution_started` stays false. A handoff that claims execution or returns mismatched task/trace IDs is not reported as `handed_off`.
- Telemetry events for one task share `trace_id`. The in-memory sink rejects secret attribute keys, oversized payloads, and conflicting duplicate event ids.
- GitHub Issues and Jira sources are rejected while their flags are false.

HTTP examples are in `docs/plane1-http.md`. PowerShell commands are in `README.md`.

## Checks actually run for Plane 1

| Check | Result |
| --- | --- |
| `uv run ruff check src tests` | Exit 0 after import formatting. |
| `uv run ruff format src tests` | Exit 0. |
| `uv run mypy` | Exit 0. 25 source files. |
| `uv run pytest` | Exit 0. 27 passed after the handoff identity regression test. One `StarletteDeprecationWarning`: Starlette's `TestClient` still imports `httpx` and asks for `httpx2`. The tests did not use a network. |

Not run for Plane 1:

- A live Gemini request
- Kafka, MongoDB, Docker, or Grafana

## Plane 2 behavior

- `agents.yaml` defines Requirements, Planning, Architecture, Development, Testing, and DevOps. A missing or malformed file fails before any stage.
- The supervisor records typed stage output and a task result that carries `task_id` and `trace_id`.
- The Developer–Tester loop defaults to `CLOUDEQ_REPAIR_MAX_ITERATIONS=3`. Each iteration stores its number, pass or fail, feedback, and the same `trace_id`.
- DevOps is appended only after state `passed`. Budget exhaustion, cancellation, configuration errors, and runtime failures leave `devops_ran` false.
- `SupervisingHandoff` implements `TaskHandoff`. It stores the run and returns `execution_started` false. Plane 1's default handoff is still the in-memory acknowledgement and does not start the supervisor.
- `OfflineRuntimeSimulation` implements `RuntimeExecutor`. Results set `simulation` true and `host_execution` false. `git_commit` is refused. No container starts.
- `CLOUDEQ_AGENT_ENGINE=crewai` on the default CLI still has no stage client. Missing Gemini configuration is an error. When the Gemini gates are open and no client was injected, the CLI reports `crewai-execution-unavailable` and does not call kickoff. No model id is guessed.
- A real stage client is allowed only when the runtime backend is `container` and the live-call flag, API key, and explicit model id are all set. A missing piece does not call `run_stage`. A fake client on the container backend can reach DevOps after a container-shaped test pass. `live_crewai` and `live_gemini` stay false for that fake.
- Injected fake stage clients and a mock runtime are tests only. Their `execution_kind` is `mocked`. Agent text that says the tests passed does not set `passed`. DevOps still waits for a runtime result with `simulation` false, a matching identity, and `passed` true.
- `ExecutionRequest` can carry safe relative files with either content or a relative artifact reference, and an allowlisted test plan. The only allowlisted command is `python -m pytest`. Plane 2 does not run it.
- Telemetry events `agents.stage_completed`, `agents.decision`, `agents.repair_iteration`, `agents.test_result`, and `agents.run_finished` share the handoff trace.

The supervisor rejects mismatched runtime identities, timeouts, host execution reports, and inconsistent pass/exit results. A failed file write stops before tests. A shared runtime error contract lets Plane 3 report failures without importing Plane 2. Stage summaries, raw test output, and error messages are excluded from Plane 2 telemetry events.

## Plane 3 behavior

- `DockerRuntimeExecutor.execution_backend` is `container` with the real Docker CLI runner. Injected runners are `container-mock` and return `simulation=true`. It is separate from `OfflineRuntimeSimulation`.
- Task workspaces default to `~/.cloudeq/runtime_workspaces`. The root may neither contain nor be inside this repository. The executor claims new task directories exclusively and ties each one to its trace id. Task ids, relative paths, symlinks and junctions, file counts, and file sizes are validated. Artifact references are rejected until a safe resolver exists.
- `write_file` writes validated bytes into that task directory and does not execute them. `run_tests` accepts only `python -m pytest` and runs it in a container. `git_commit` is rejected by default and is still rejected when the allow flag is true, because Git is not run on the host. There is no push operation.
- The container uses an argument list, network `none`, user `65534:65534`, memory `512m`, one CPU, a 64-process limit, a timeout, no host credentials, no Docker socket, and one read-only task-workspace mount. The image is never pulled implicitly, and host-side Docker output retention is bounded. The image tag is `cloudeq-runtime:py3.12-pytest9.2.0`, built from `python:3.12-slim` plus pytest 9.2.0 by `infra/runtime/Dockerfile`.
- Completed results carry the task id, trace id, operation, exit code, pass or fail, timeout, duration, bounded output, and artifact references. `simulation` is false and `host_execution` is false. Failures before a trustworthy result raise `RuntimeExecutionError`.
- Telemetry events `runtime.operation_completed` and `runtime.operation_rejected` share the request trace. Payloads omit file contents, test output, secrets, and daemon error text.
- The Docker runner removes its unique named container after a timeout; successful runs use Docker's `--rm`. Task cleanup removes only a directory created by this executor.
- `src/cloudeq/composition.py` connects the supervisor to a `RuntimeExecutor`. The `cloudeq-agents` CLI still constructs `OfflineRuntimeSimulation`.

## Checks actually run for Plane 3

| Check | Result |
| --- | --- |
| `uv lock --check` | Exit 0 on 2026-11-03. `Resolved 156 packages in 3ms`. |
| `uv run ruff check src tests` | Exit 0. `All checks passed!` |
| `uv run ruff format --check src tests` | Exit 0. `59 files already formatted`. |
| `uv run mypy` | Exit 0. `Success: no issues found in 47 source files`. |
| `uv run pytest -q` | Exit 0. `74 passed, 1 skipped`. The skip is `tests/plane3/test_smoke.py`: the Docker engine was unavailable, so the live smoke test was not run. |
| Mocked Docker tests | Passed. They cover paths, symlinks, operation validation, Docker settings, startup failure, timeout, cleanup, failed writes, failing and passing tests, matching ids, host-execution false, and DevOps only after a container-shaped pass. Injected runners are labeled as simulations. |
| Real container smoke test | Not run. Docker CLI 25.0.3 is installed. `docker info` returned: the daemon is not running (`open //./pipe/docker_engine: The system cannot find the file specified`). |
| Live Gemini | Not called. The handoff test uses a fake stage client and forbids `live_kickoff`. |

## Checks actually run for Plane 2

| Check | Result |
| --- | --- |
| `uv lock --check` | Exit 0 on 2026-11-02. |
| `uv run ruff check src tests` | Exit 0. `All checks passed!` |
| `uv run ruff format --check src tests` | Exit 0. `49 files already formatted`. |
| `uv run mypy` | Exit 0. `Success: no issues found in 41 source files`. |
| `uv run pytest -q` | Exit 0. `55 passed`. No network and no CrewAI kickoff. |
| `uv run cloudeq-agents run --prompt "Add a health check"` | Exit 0. `state` `passed`, `engine` `offline-simulation`, `execution_kind` `simulated`, `simulation` true, `live_crewai` false, `devops_ran` true. |
| `uv run cloudeq-agents run --engine crewai --prompt "Add a health check"` | Exit 1. `state` `error`, `engine` `crewai-configuration-error`, `live_crewai` false. Live calls stayed disabled. |

Not run in that Plane 2 session:

- Live CrewAI `kickoff`
- A live Gemini request
- Docker, Kafka, MongoDB, or Grafana
- Host execution of generated code

The offline `cloudeq-agents` demonstration remains a simulation. `cloudeq-agents run --engine crewai` is a configuration or availability error with the default settings. It is not a live run.

The same Plane 2 demonstration command is in `README.md`.

Plane 1 offline demo on 2026-10-31, with live Gemini calls left false:

- `uv run cloudeq-intake submit --prompt "Add a health check"` exited 0 with `handed_off` and `execution_started` false.
- A blank prompt exited 2 with `rejected`.
- `--dataset corpus-v1` exited 0 with `routed`, `infeasible`, and `dataset_check` failed.
- Uvicorn on `127.0.0.1:8765` returned health `router_mode` offline and a posted task `handed_off` with `execution_started` false. The server was stopped after that check.

## Earlier configuration

Configuration was merged from `chore/forge-span-configuration`. That session locked pytest 9.2.0, Ruff 0.17.3, and mypy 2.4.1, and left the suite empty. Plane 1 then added FastAPI 0.162.0, Uvicorn 0.54.0, httpx 0.28.1, Pydantic 2.14.2, and pydantic-settings 2.16.2. Plane 2 added PyYAML 6.0.3 and types-PyYAML 6.0.12.20261030. This branch adds CrewAI 1.15.34 with the `google-genai` extra, which locked `google-genai` 1.65.0. Both are project-local.

## Roadmap

| Order | Milestone | State |
| --- | --- | --- |
| 0 | Configuration | Merged. |
| 1 | Plane 1 intake | Offline API, CLI, router, handoff, and telemetry are implemented. Ticket adapters are not. |
| 2 | Plane 2 agent orchestration | Offline simulation remains the default. A real stage client can run only with the container backend and explicit Gemini settings. Live kickoff was not called. |
| 3 | Plane 3 sandboxed execution | `DockerRuntimeExecutor` is implemented and unit-tested with an injected runner. The live container smoke test was not run because the Docker engine was unavailable. |
| 4 | Plane 4 observability | Not started. Replace the in-memory sink with Kafka and MongoDB dual retention. |
| 5 | Integration and demonstration | Not started. |

## Unresolved

- Retention durations and deletion
- Full redaction policy beyond the attribute-key denylist
- Explicit Gemini model IDs
- GitHub Issue and Jira payload mapping
- Canonical field catalog beyond the linkage fields
- Grafana panel layout
- No assignment rubric

## Next commands

```powershell
Set-Location C:\Users\kaust\projects\CloudEQ
uv sync
uv run ruff check src tests
uv run mypy
uv run pytest
uv run cloudeq-intake submit --prompt "Add a health check"
uv run cloudeq-agents run --prompt "Add a health check"
```

Plane 4 should ingest telemetry through Kafka, preserve the raw event before normalization, store raw and canonical records separately in MongoDB, and expose an HTTP read API for Grafana Infinity. Retention durations stay unset. The normalizer stays behind an interface with an offline fake. Live Gemini normalization, Kafka, MongoDB, and Grafana are not part of this milestone. Start Docker Desktop before expecting `tests/plane3/test_smoke.py` to build `cloudeq-runtime:py3.12-pytest9.2.0` and run the fixed pytest fixture.
