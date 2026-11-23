# FORGE SPAN

**An Autonomous Multi-Agent SDLC Framework with Federated Observability**
By **Cloud EQ**.

Cloud EQ is the team. FORGE SPAN is the product. The technical identifier remains
`CloudEQ`: the GitHub repository, the `cloudeq` package, and the `CLOUDEQ_`
environment prefix. See `docs/PROJECT_IDENTITY.md`.

Grok is the coding assistant in Cursor. Gemini is the application's runtime model
provider. This project does not replace Gemini with Grok.

## Quick start: run it and see it

All four planes are implemented and wired together. From the repository root
in Windows PowerShell:

```powershell
uv sync                      # installs everything (first run re-locks for the new extras)
uv run cloudeq-server        # then open http://127.0.0.1:8000
```

Or double-click-style: `powershell -ExecutionPolicy Bypass -File scripts\start.ps1`.

The dashboard lets you submit a prompt and watch it go through every plane:

1. **Intake** validates and routes it (blank prompts are rejected, named datasets are infeasible).
2. **Agents** run Requirements → Planning → Architecture → Developer ⇄ Tester (bounded repair loop) → DevOps.
3. **Runtime** writes files and runs tests (simulated by default, real Docker in docker mode).
4. **Observability** stores every event raw first, normalizes it to the FOAP canonical schema,
   and shows the correlated trace, pipeline health, and failures.

Use the preset buttons (*Pass first try*, *Repair ×2*, *Budget exhausted*, *Infeasible*,
*Blank*) and the Plane 4 ingest buttons (*Rich event*, *Drifted fields*, *Malformed*, *Retry failed*).

Terminal-only demonstration of the same five scenarios:

```powershell
uv run cloudeq-demo
```

### Execution modes

| Mode | How | What is real |
| --- | --- | --- |
| `simulation` (default) | `uv run cloudeq-server` | Intake, supervisor, repair loop, telemetry pipeline. Runtime results are simulated and labeled so. |
| `docker` | Start Docker Desktop, then `scripts\start-docker-mode.ps1` | Generated Python code and its pytest suite are written to a task workspace and tested in the locked-down sandbox container (no network, non-root, read-only mount). The "failing iterations" setting injects a defect so the container's real test failure drives the repair. Stage text comes from a deterministic template client, not an LLM. |
| docker + live Gemini | docker mode plus `CLOUDEQ_AGENT_ENGINE=crewai`, `CLOUDEQ_GEMINI_LIVE_CALLS=true`, `GEMINI_API_KEY`, `GEMINI_AGENT_MODEL` | CrewAI + Gemini write the code. Paid API usage; never enabled by default. |

### Full integration stack (Kafka, MongoDB, Grafana)

```powershell
docker compose up -d --build     # app :8000, Grafana :3000 (admin/admin), Kafka :9092, MongoDB :27017
docker compose down              # keeps data volumes
```

In this stack telemetry goes app → Kafka → consumer → MongoDB (`raw_events`,
`canonical_events`, `normalization_attempts`), and Grafana's provisioned
"FORGE SPAN — cross-plane operations" dashboard reads `/observability/grafana/*`
through the Infinity data source. To run the app on the host against those
services instead: `uv sync --extra kafka --extra mongo` and set
`CLOUDEQ_TELEMETRY_BUS=kafka`, `CLOUDEQ_OBSERVABILITY_STORE=mongodb` in `.env`.

### Useful endpoints

| Endpoint | Purpose |
| --- | --- |
| `GET /` | Dashboard |
| `POST /api/runs` `{prompt, dataset?, simulated_failures?}` | Run a prompt through all planes |
| `GET /api/runs`, `GET /api/runs/{task_id}` | Run history (persisted to `~/.cloudeq/runs.jsonl`) |
| `POST /tasks` | Plane 1 contract, now backed by the agents |
| `GET /observability/traces/{trace_id}` | Raw + canonical events for one trace |
| `GET /observability/metrics`, `/observability/health` | Pipeline metrics |
| `POST /observability/ingest` | Schema-agnostic external event ingestion |
| `POST /observability/retry?normalizer=offline` | Re-normalize failed events |
| `GET /observability/grafana/*` | Flat tables for Grafana Infinity |

`uv run cloudeq-observability stats|retry|consume|retention` covers the worker and maintenance side.

## Setup status

All four planes and the integration layer are in place (see Quick start above).
The notes below describe the individual plane CLIs, which still work on their own.
Configuration, Plane 1 intake, the Plane 2 agent engine, and the Plane 3
container runtime are in place. The API and CLI validate a prompt, route it
with the offline feasibility adapter, and hand a feasible task to the default
in-memory port. That default handoff does not run the supervisor.
`cloudeq-agents run` runs a labeled offline simulation of the six SDLC stages
and the Developer–Tester loop. It does not call CrewAI, Gemini, Docker, Kafka,
or MongoDB. Plane 4 is not implemented. Live Gemini calls stay disabled.

Open this folder in Cursor, or open `FORGE-SPAN.code-workspace`. The always-applied
rule is `.cursor/rules/cloudeq.mdc`. `.cursorrules` carries the same guidance.
Keep their rule bodies synchronized.

The next session is Plane 4, observability, in `docs/CURSOR_BUILD_PROMPT.md`.
Plane 1's prompt remains `docs/CURSOR_START_PROMPT.md`.

## Workspace structure

```text
.
|-- FORGE-SPAN.code-workspace
|-- CloudEQ.code-workspace
|-- pyproject.toml
|-- uv.lock
|-- .python-version
|-- .cursor/rules/cloudeq.mdc
|-- .cursorrules
|-- .gitignore
|-- .env.example
|-- README.md
|-- CONTRIBUTING.md
|-- docs/
|   |-- requirements.md
|   |-- implementation-status.md
|   |-- PROJECT_IDENTITY.md
|   |-- CURSOR_CONFIGURE_PROMPT.md
|   |-- CURSOR_START_PROMPT.md
|   |-- CURSOR_BUILD_PROMPT.md
|   |-- architecture/
|   |   |-- overview.md
|   |   |-- decisions.md
|   |   `-- contracts.md
|   `-- references/
|-- src/cloudeq/
|   |-- shared/
|   |   |-- contracts/
|   |   `-- ports/
|   |-- plane1_intake/
|   |-- plane2_agents/
|   |-- plane3_runtime/
|   `-- plane4_observability/
|-- infra/
|-- tests/
`-- scripts/
```

Plane 1, Plane 2, and Plane 3 contain application code. Plane 4 is still a
package marker. `.env.example` has empty secrets and offline defaults. Do not
commit `.env`.

## References in Cursor

Add these files to chat context before an implementation session:

- `docs/references/CloudEQ.extracted.md`
- `docs/references/FOAP-paper.extracted.md`
- `docs/references/FORGE-SPAN-architecture.md`
- `docs/references/FORGE-SPAN-architecture.jpg`
- the prompt for that session (`docs/CURSOR_START_PROMPT.md` for Plane 1)

Keep the original PDFs beside the extracts. The PDFs are authoritative. Extracts
are page-marked text, and figures may be missing from them. No assignment rubric
has been supplied. Never attach `.env` or API credentials.

![FORGE SPAN architecture supplied by the team](docs/references/FORGE-SPAN-architecture.jpg)

Read `docs/references/README.md` before treating a sentence as a requirement.
`docs/requirements.md` records page references and planned checks.
`docs/architecture/contracts.md` records plane boundaries. The diagram's Git
commit box does not authorize a host commit or a push.

## Windows PowerShell setup

Run these commands from the repository root. The root must be this folder, not
`C:\Users\kaust\projects`.

```powershell
Set-Location C:\Users\kaust\projects\CloudEQ
git rev-parse --show-toplevel
py -3.12 --version
uv --version
uv sync
uv lock --check
uv run python -c "import cloudeq.plane1_intake, cloudeq.plane2_agents, cloudeq.plane3_runtime, cloudeq.plane4_observability, cloudeq.shared.contracts, cloudeq.shared.ports; print('imports-ok')"
uv run ruff check src tests
uv run ruff format --check src tests
uv run mypy
uv run pytest
```

`uv sync` creates `.venv` in this folder and installs the package, FastAPI,
Uvicorn, httpx, PyYAML, CrewAI 1.15.34 with the Gemini extra, pytest, Ruff,
and mypy. It does not install a Kafka client, MongoDB, the Docker engine, or
Grafana, and it does not call Gemini. Plane 3 unit tests inject a command
runner, so they pass while Docker Desktop is stopped.

Expected results on this machine:

- `git rev-parse --show-toplevel` prints `C:/Users/kaust/projects/CloudEQ`.
- Python is 3.12.x and below 3.14. This machine used 3.12.2.
- `imports-ok` prints after the import command.
- Ruff and mypy exit 0.
- `uv run pytest` exits 0. On 2026-11-03 the result was `74 passed, 1 skipped`.
  The skip is the live container smoke test when `docker info` cannot reach
  the engine. A passing test is not evidence that CrewAI, Gemini, Kafka,
  MongoDB, or Grafana ran.

If `uv` is missing, install it from [Astral's uv documentation](https://docs.astral.sh/uv/getting-started/installation/) and open a new shell. If `py -3.12` fails, install CPython 3.12. The project rejects 3.14 because current CrewAI does not support it. Library versions and that constraint are in `docs/architecture/decisions.md`.

Copy `.env.example` to `.env` only for local settings. Leave secrets empty and
leave `CLOUDEQ_GEMINI_LIVE_CALLS=false` until a model ID is chosen deliberately.
The HTTP shapes are in `docs/plane1-http.md`.

## Offline Plane 1 demo

Run this from the repository root. It does not call Gemini.

```powershell
Set-Location C:\Users\kaust\projects\CloudEQ
$env:CLOUDEQ_ROUTER_MODE = "offline"
$env:CLOUDEQ_GEMINI_LIVE_CALLS = "false"
$env:GEMINI_API_KEY = ""
$env:GEMINI_ROUTER_MODEL = ""
uv run cloudeq-intake submit --prompt "Add a health check"
uv run uvicorn cloudeq.plane1_intake.api.app:app --host 127.0.0.1 --port 8000
```

In a second shell, with the server still running:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/health
$body = @{ source = "api"; prompt = "Add a health check" } | ConvertTo-Json
Invoke-RestMethod http://127.0.0.1:8000/tasks -Method Post -ContentType "application/json" -Body $body
```

`status` `handed_off` and `execution_started` `$false` mean the default in-memory
port accepted the contract. They do not mean the supervisor ran or that code was
generated. Stop the server with Ctrl+C.
A blank prompt exits the CLI with code 2. A named dataset is routed as infeasible:

```powershell
uv run cloudeq-intake submit --prompt "Use the corpus" --dataset "corpus-v1"
```

## Offline Plane 2 demo

This command runs the labeled simulation. `simulation` is true, `live_crewai`
and `live_gemini` are false, and `host_execution` is false. A pass runs DevOps
only after the simulated test result. It does not prove live CrewAI or Gemini
execution, and it does not execute generated code.

```powershell
Set-Location C:\Users\kaust\projects\CloudEQ
$env:CLOUDEQ_AGENT_ENGINE = "offline"
$env:CLOUDEQ_REPAIR_MAX_ITERATIONS = "3"
uv run cloudeq-agents run --prompt "Add a health check"
```

Exit 0 is `passed` for the offline simulation. Exit 2 is `failed_budget_exhausted`.
Exit 3 is `cancelled`. Exit 1 is `error`. `--engine crewai` with the default
settings is a configuration error. The CLI does not construct a live stage
client, so a key and model id still leave kickoff uncalled.

## Plane 3 container image

The sandbox image is `cloudeq-runtime:py3.12-pytest9.2.0`. Its base is
`python:3.12-slim`, and `infra/runtime/Dockerfile` adds pytest 9.2.0 because
the only allowlisted test command is `python -m pytest`. Build it when Docker
Desktop is running:

```powershell
Set-Location C:\Users\kaust\projects\CloudEQ
docker build -t cloudeq-runtime:py3.12-pytest9.2.0 infra/runtime
uv run pytest tests/plane3/test_smoke.py
```

The smoke test writes a fixed `tests/test_health.py` fixture and runs it in
one container. It does not call Gemini. If `docker info` cannot reach the
engine, pytest skips that test. The default `cloudeq-agents` command stays on
the offline simulation. A fake stage client can be composed with
`DockerRuntimeExecutor` through `src/cloudeq/composition.py`. An injected Docker runner is labeled `container-mock` with `simulation=true`; only the real Docker CLI runner is labeled `container`. The task workspace defaults to `~/.cloudeq/runtime_workspaces`, outside the repository.

## Roadmap

Status is in `docs/implementation-status.md`.

1. Configuration — done.
2. Plane 1, intake — offline API and CLI are implemented. Ticket adapters are not.
3. Plane 2, agent orchestration — offline simulation is the default. A real stage client requires the container backend and explicit Gemini settings. Live kickoff was not called.
4. Plane 3, sandboxed execution — `DockerRuntimeExecutor` is implemented. Unit tests inject the Docker runner. The live container smoke test runs only when the Docker engine is up.
5. Plane 4, observability — implemented: redaction, raw-first dual retention,
   offline + Gemini normalizers, SQLite/MongoDB stores, in-process/Kafka bus, read API.
6. Integration and demonstration — implemented: `cloudeq-server` dashboard,
   `cloudeq-demo`, Docker Compose stack, Grafana provisioning.

## GitHub and team contribution

The private repository is [kaustubhchaudhari11/CloudEQ](https://github.com/kaustubhchaudhari11/CloudEQ).
Plane 3 work is on `feature/plane3-runtime` and is not pushed by this session. It is independent of any repository in the parent directory. See
`CONTRIBUTING.md`. A pull-request template is under `.github/`.

Do not rename the GitHub repository to match the product name.
