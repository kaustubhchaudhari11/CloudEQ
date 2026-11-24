# FORGE SPAN

**An autonomous multi-agent SDLC framework with federated observability**
Team: **Cloud EQ**. Repository/package identifiers remain `CloudEQ` / `cloudeq`.

## Submission source and status

**Submission repository: [github.com/kaustubhchaudhari11/CloudEQ](https://github.com/kaustubhchaudhari11/CloudEQ)**

The public **`main`** branch contains the complete Drive project plus the deployment fixes, merged in pull request #6. A normal clone or a download of `main` contains the complete application, tests, dependency lockfile, configuration template, and documentation. See [source provenance](docs/SOURCE_PROVENANCE.md) for the recorded comparison.

**[Read or download the user manual (PDF)](docs/FORGE-SPAN-User-Manual.pdf)** — installation, features, main workflow, additional scenarios, and screenshots. This is the team's supplied November 17–21 local-demonstration edition, preserved unchanged. Use this README for current clone/install commands, model configuration, runtime packages, and fixes made after that edition; its historical model IDs, test totals, and UI limitations are not promises about the current release.

### For the evaluator

1. Follow **sections 1–3** to install and run the offline demonstration. No API key, Docker, or paid hosting account is required for this first check. Initial dependency installation needs internet access.
2. Follow **section 4** for deterministic agents with actual local container tests.
3. Follow **section 5** for live CrewAI/Gemini generation using your own key and Docker. This workflow can also be demonstrated locally during the presentation.
4. Use **sections 6–7** to inspect observability and run automated checks.

The offline demonstration verifies the workflow and repair/control paths with simulated stage/test outputs. It does **not** verify live model generation or actual generated-code execution. Real API keys are intentionally absent; all required local variable names and examples are documented below and in [`.env.example`](.env.example).

All four planes and the integrated dashboard are implemented:

1. **Intake:** validate a prompt, check feasibility, and hand it to the agents.
2. **Agents:** Requirements, Planning, Architecture, Development, Testing, and DevOps. Development and Testing repeat within a repair budget; DevOps follows an actual pass.
3. **Runtime:** test generated Python code in a restricted Docker container locally or an isolated Render environment when hosted.
4. **Observability:** retain accepted raw events before normalization, store canonical records separately, and correlate events by task/event/trace IDs. SQLite is the local default; Kafka, MongoDB, and Grafana are optional integrations.

Hosted demo: <https://forge-span.onrender.com>. Local evaluation requires no Render or AWS account. Simulation, deterministic template runs, and live Gemini runs are labeled separately. One complete hosted live Gemini health-check workflow passed real tests; other live requests encountered Gemini 503 errors. See [verification](docs/DEPLOYMENT_VERIFICATION.md).

## 1. Technical requirements

- Git, or download and extract the ZIP of the source branch above.
- Python **3.12** recommended. The package supports `>=3.12,<3.14`.
- [uv](https://docs.astral.sh/uv/getting-started/installation/) for locked dependencies and the project-local environment. Submission checks used Windows and uv 0.13.2.
- A modern browser; the local application uses port **8000**.
- For actual generated-code execution: Docker Desktop with Linux containers on Windows/macOS, or Docker Engine on Linux. The engine must be running.
- For live Part 2: a Gemini API key, an explicit model ID available to that key, internet access, and sufficient provider quota. No key is needed for the offline demonstration.
- Suggested capacity: 8 GB RAM and 10 GB free disk for the full demonstration, not a measured minimum. Test containers default to one CPU, 512 MB RAM, and a 120-second timeout.

`pyproject.toml` lists application/development dependencies, and `uv.lock` pins resolved versions. Core packages include FastAPI, CrewAI with Google GenAI, Uvicorn, httpx, Pydantic Settings, and PyYAML. Optional extras are `kafka`, `mongo`, and `render`. The local runtime image contains pytest 9.2.0 and Flask 3.1.3.

## 2. Download and install

The repository is public and can be cloned without a collaborator invitation. No team credentials are included.

```text
git clone https://github.com/kaustubhchaudhari11/CloudEQ.git FORGE-SPAN
cd FORGE-SPAN
uv python install 3.12
uv sync --locked --python 3.12
```

For a ZIP, select **`main`** on GitHub before **Code → Download ZIP**, or [download main directly](https://github.com/kaustubhchaudhari11/CloudEQ/archive/refs/heads/main.zip). Extract it, open a terminal in the directory containing `pyproject.toml`, then run the two `uv` commands. No developer-specific absolute path is needed.

Create `.env` once from the supplied template. Do not replace an existing file.

Windows PowerShell:

```powershell
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
```

macOS/Linux:

```sh
test -e .env || cp .env.example .env
```

The template contains offline defaults and empty secrets. The app loads `.env` from the current working directory; existing process environment variables take precedence. Restart the server after changes. Never commit `.env`, passwords, or keys.

On Windows, the checkout-aware launcher below always starts from its own project
folder, installs locked dependencies, and reports an existing FORGE SPAN server
instead of trying to start a second one on the same port:

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\start.ps1
```

Use the launcher from the updated GitHub checkout, not an earlier extracted Drive
copy. The mode comes from `.env`; this launcher does not silently enable paid API
calls. If it finds a running server, it prints that server's current agent mode.

## 3. First check: no key or Docker required

Keep the copied `.env` defaults and run:

```text
uv run --locked cloudeq-server
```

Open **<http://localhost:8000>** (equivalently <http://127.0.0.1:8000>). Select **Part 1: template workflow and repair demonstration** and submit `Add a health check`. In `simulation` execution mode, the workflow and telemetry are real application behavior but test outcomes are simulated. Expect `simulation=true`, `live_gemini=false`, and `host_execution=false`.

The repair budget defaults to three attempts. **Repair ×2** fails twice and passes on the third attempt. **Budget exhausted** fails all three and skips DevOps. **Blank (rejected)** demonstrates validation. **Infeasible** uses an unknown dataset; there is no dataset catalog.

Terminal-only demonstration of these five scenarios:

```text
uv run --locked cloudeq-demo
```

This command runs the five scenarios and two external telemetry examples in a temporary local store. Expected results are two successful workflows, one exhausted repair budget with no DevOps, one infeasible request, and one rejected blank request. The malformed telemetry example intentionally fails normalization while keeping its raw event. The offline run rechecked on **November 24, 2026** exited successfully with **79 raw events, 78 canonical records, one expected normalization failure, and no pending events**. Generated IDs vary between runs. CLI demo records are temporary; use the dashboard buttons to create results visible in its Recent runs list.

Stop the web server with **Ctrl+C** before changing modes.

## 4. Part 1 with actual local tests

Start the Docker engine in Linux container mode. From the repository root:

```text
docker info
docker build -t cloudeq-runtime:py3.12-pytest9.2.0 infra/runtime
```

Edit these existing `.env` lines:

```dotenv
CLOUDEQ_EXECUTION_MODE=docker
CLOUDEQ_AGENT_ENGINE=offline
CLOUDEQ_GEMINI_LIVE_CALLS=false
CLOUDEQ_ROUTER_MODE=offline
CLOUDEQ_NORMALIZER_MODE=offline
```

Restart `uv run --locked cloudeq-server`, select **Part 1**, and choose **Repair ×2**. The stage content is deterministic, but pytest executes in real containers. Expect runtime `container`, `simulation=false`, two failing iterations followed by a pass, and DevOps after the pass. `live_gemini=false` is expected.

Containers have no network, no application keys, a non-root user, a read-only task mount, and resource/time limits. `host_execution=false` is correct: generated code did not run directly on the application host.

## 5. Part 2: live CrewAI and Gemini locally

**Localhost is not the same as offline.** A browser at `http://localhost:8000`
can use real CrewAI and Gemini: the application runs on your computer while model
requests go over the internet to Gemini. Truly offline simulation makes no LLM
calls. Setting an API key while leaving `CLOUDEQ_EXECUTION_MODE=simulation` does
not turn the simulation into live generation.

Complete section 4 first. Obtain your own key through [Google AI Studio](https://aistudio.google.com/apikey), following [Google's key setup instructions](https://aistudio.google.com/docs/api-key). Usage may require quota or billing. Keep the key only in your local configuration.

Edit these `.env` values:

```dotenv
CLOUDEQ_EXECUTION_MODE=docker
CLOUDEQ_AGENT_ENGINE=crewai
CLOUDEQ_GEMINI_LIVE_CALLS=true
GEMINI_API_KEY=REPLACE_LOCALLY_WITH_YOUR_OWN_KEY
GEMINI_AGENT_MODEL=gemini-3.5-flash-lite
CLOUDEQ_GEMINI_TIMEOUT_SECONDS=60
CLOUDEQ_ROUTER_MODE=offline
CLOUDEQ_NORMALIZER_MODE=offline
```

The key value above is a placeholder. `gemini-3.5-flash-lite` was used in the verified hosted run on November 23, 2026; model availability depends on the provider and your account. Choose an available compatible Gemini model explicitly if needed. No model ID is silently guessed.

Keeping routing and normalization offline initially isolates the six live agent stages and reduces unrelated API calls. To use Gemini in those two planes as well, set `CLOUDEQ_ROUTER_MODE=gemini`, `CLOUDEQ_NORMALIZER_MODE=gemini`, and fill `GEMINI_ROUTER_MODEL` and `GEMINI_NORMALIZER_MODEL` with available model IDs.

Restart `uv run --locked cloudeq-server`. Confirm the dashboard says **CrewAI + Gemini (live)**, select **Part 2: configured agents**, and submit:

```text
Write health.py with a health_check() function returning exactly {"status":"ok"}, and test_health.py with pytest tests for that function. Use only Python standard library and pytest; compatible with Python 3.11 or later. Include both files in the Development output. Testing must request exactly python -m pytest. No networking, installs, subprocesses, or external packages.
```

Allow time for sequential model stages and container tests. A successful live run must show:

- Agent outcome `passed`, with all six stages and DevOps.
- `live_crewai=true`, `live_gemini=true`, and `simulation=false`.
- A real runtime test result with exit code zero; model text alone is insufficient.
- Generated files and telemetry linked to the same task and trace.
- `host_execution=false`, because tests ran inside the isolated environment.

**Part 1 presets switch the workflow to Part 1.** They do not test Gemini or force it to generate a bug. A missing live configuration can select the template client; check the labels and flags. Use `cloudeq-server` for the integrated live workflow. The earlier `cloudeq-agents` CLI is an offline/boundary demonstration.

### Step-by-step live pipeline for local evaluation

1. **Prepare the application.** Clone `main` and run the installation commands in
   section 2. Create `.env` from `.env.example` once. Never copy someone else's key.
2. **Prepare test execution.** Start Docker, verify `docker info`, and build the
   image with the exact section 4 command. Keep the application running on the
   host; the Compose application itself intentionally uses simulation.
3. **Enable live agents.** Apply the section 5 `.env` block, supply your own key,
   and verify the explicit model ID is available to it. The required combination
   is execution mode `docker`, agent engine `crewai`, live calls `true`, a key,
   and a model. Start a fresh terminal so older environment overrides do not win.
4. **Start the integrated server.** From the repository root run
   `uv run --locked cloudeq-server --host 127.0.0.1 --port 8000` and open
   `http://localhost:8000`. `/health` should report `execution_mode: docker`,
   `stage_client: CrewAI + Gemini (live)`, `live_gemini: true`, and
   `docker_engine_available: true`. These establish readiness, not a completed run.
5. **Select the live workflow.** Choose **Part 2: configured agents**, leave the
   dataset empty, and paste the health-check prompt above. Click **Run through all
   planes** once. Do not click Part 1 presets: those deliberately select templates.
6. **Plane 1 — intake.** The request is validated and receives task/trace IDs.
   Feasible input is handed to the supervisor. Empty input is rejected; an unknown
   dataset is routed as infeasible. The recommended initial profile uses an offline
   feasibility router while the subsequent agent stages still call live Gemini.
7. **Plane 2 — planning and development.** The supervisor runs Requirements,
   Planning, Architecture, and Development sequentially. Each live stage builds a
   CrewAI crew backed by the configured Gemini model and validates its structured
   output. Development must supply implementation files and pytest tests. Stage
   summaries are recorded separately; this implementation does not pass a complete
   accumulated design document between every role. It supplies the original prompt
   and, during repairs, prior runtime feedback to each stage.
8. **Plane 3 — execute tests.** Validated relative files are written to the task
   directory outside the repository. The Testing stage requests exactly
   `python -m pytest`. Docker executes it with network disabled, no application
   credentials, a non-root user, a read-only task mount, and resource/time limits.
   The real exit code and output determine pass/fail, not an LLM's claim.
9. **Repair or finish.** A failing test sends runtime feedback back to Development,
   then Testing runs again, up to the configured three-attempt budget. A pass
   permits DevOps; exhaustion or a provider/runtime error prevents successful
   completion. DevOps produces a stage summary, not a deployment or Git push.
10. **Plane 4 — inspect evidence.** Events from the workflow share the trace ID.
    The local in-process/SQLite profile retains raw records before offline
    normalization and keeps canonical records separately. The optional Kafka,
    MongoDB, and Gemini-normalizer configurations are described in section 6 and
    above. Scroll to the generated files, iterations, and correlated trace, or open
    `/api/runs/TASK_ID` and `/observability/traces/TRACE_ID` with the returned IDs.
11. **Confirm a live success.** Check `passed`, all six stages, `live_crewai=true`,
    `live_gemini=true`, `simulation=false`, actual pytest output, and
    `host_execution=false`. Old simulation runs remain in Recent runs; inspect the
    new task's own flags. A 503 or timeout is a failed provider attempt, not a live
    success. Retry later rather than presenting a simulated pass as a live run.

If the header still says **mode simulation / offline simulation (no LLM)**, stop
that server, verify you edited `.env` in the directory used to start it, remove
stale process overrides by opening a fresh terminal, and restart. Refresh the
browser and select Part 2 again. Merely changing the dropdown cannot change the
server's execution mode. You can keep routing/normalization offline while live
CrewAI agents run; those are independently configured components.

**Alternative when Docker is unavailable:** the existing Render runtime adapter
can execute tests remotely while the dashboard and CrewAI still run at localhost.
This is a hybrid deployment, not offline or fully local execution: its header says
`mode render`, agents remain live, and runtime results say `render-sandbox`.
It requires a Render account and private runtime credentials, the `render` extra,
and the trusted pytest/Flask wheel bundle described in
[Render deployment](docs/RENDER_DEPLOYMENT.md). Remote test usage may incur charges.
The default TA instructions above use Docker and need no Render account.

## 6. Observability and optional service stack

Local defaults use an in-process event bus and SQLite, with no extra service. The **Rich event**, **Drifted fields**, and **Malformed** ingest examples demonstrate successful normalization and preserved raw data on normalization failure. **Retry failed** processes retained failures again. Trace IDs connect activity across the planes.

To inspect an event from the manual's telemetry scenario, copy its `trace_id` and open `http://localhost:8000/observability/traces/TRACE_ID`, replacing `TRACE_ID` with that value. Successful normalization and a source event whose status is `FAILED` can coexist: one describes processing, the other the original event.

To run Kafka, MongoDB, and Grafana locally, stop any host server on port 8000, then run:

```text
docker compose up -d --build
docker compose ps
```

The Compose dashboard uses port 8000; Grafana uses 3000 (`admin` / `admin` for the first local login); Kafka uses 9092 and MongoDB 27017. These are local demonstration settings. Grafana reads the application HTTP API and never receives `MONGODB_URI`.

**The Compose app uses simulation and offline models.** It has no Docker socket and cannot launch nested test containers. For actual local execution, run the host application as in sections 4–5. To combine that host application with Kafka/MongoDB:

```text
docker compose up -d kafka mongo
uv sync --locked --extra kafka --extra mongo
```

Set `CLOUDEQ_TELEMETRY_BUS=kafka`, `CLOUDEQ_OBSERVABILITY_STORE=mongodb`, `KAFKA_BOOTSTRAP_SERVERS=localhost:9092`, and `MONGODB_URI=mongodb://localhost:27017` in `.env`, then restart the host application. The supplied Grafana datasource targets the Compose app, not this host process.

`docker compose down` stops the optional stack and retains its data volumes. Blank `FOAP_RAW_RETENTION_DAYS` and `FOAP_CANONICAL_RETENTION_DAYS` mean deletion is not enabled.

## 7. Verification

From the repository root, with safe default settings:

```text
uv sync --locked --all-extras
uv lock --check
uv run --locked --all-extras ruff check src tests
uv run --locked --all-extras ruff format --check src tests
uv run --locked --all-extras mypy
uv run --locked --all-extras pytest -q
```

`--all-extras` installs the optional integration client libraries so type-checking
can inspect their imports. It does not start Kafka, MongoDB, or Render services.

Unit/integration tests use offline adapters and test doubles; no Gemini key is required. The real Docker smoke test skips if the engine is unavailable. With Docker running, check it explicitly:

```text
uv run --locked pytest tests/plane3/test_smoke.py -q
```

See [dated verification results](docs/DEPLOYMENT_VERIFICATION.md). A skipped check is not a container pass. Local Docker and Compose were not rerun during the November 23 submission check because the local engine was stopped; hosted remote execution was checked separately.

## Troubleshooting and practical limits

- **Gemini 503:** temporary provider unavailability. Bounded retries are built in; wait before retrying. More hosting capacity does not resolve this.
- **429 / 401 / 403 / 404:** check quota, local key configuration, account permissions, and model availability. Do not disclose the key.
- **No handoff:** inspect the intake rejection/feasibility reason first.
- **No actual execution:** check `docker info`, the built image, the mode, and the runtime error. Keep the task workspace outside the repository.
- **Docker reports a read-only data filesystem:** this is a Docker/WSL storage
  problem, not a Gemini setting. Follow [Docker's troubleshooting guidance](https://docs.docker.com/desktop/troubleshoot-and-support/troubleshoot/).
  Do not delete Docker volumes or reset its data merely to run this demonstration.
- **Missing Flask:** rebuild `infra/runtime/Dockerfile`; it includes Flask. Arbitrary generated package-install commands are not supported.
- **Port occupied:** stop the other server or use `cloudeq-server --port 8001`.
- **Old settings:** process environment values override `.env`; use a fresh terminal and restart the server after edits.
- **MongoDB connection refused / `ServerSelectionTimeoutError`:** installing
  `pymongo` only installs a client. MongoDB must also be running at `MONGODB_URI`.
  For the standalone local profile, set `CLOUDEQ_OBSERVABILITY_STORE=sqlite` and
  `CLOUDEQ_TELEMETRY_BUS=inprocess`, then restart. These settings do not disable
  live CrewAI/Gemini agents. If using MongoDB deliberately, start the service and
  match its published port (the supplied Compose file uses 27017).
- Generated projects are reviewable files and test results, not automatically published websites. Generated Git commit/push operations are disabled.
- Ticket adapters and a dataset catalog are not implemented. Retention deletion is not configured. Historical normalization failures remain visible and are not counted as successes.

Default data locations are `~/.cloudeq/runs.jsonl`, `~/.cloudeq/observability.sqlite3`, and `~/.cloudeq/runtime_workspaces`. These can be changed through the variables in `.env.example`.

## Source map and documentation

- `src/cloudeq/plane1_intake/` — validation, intake API/CLI, routing.
- `src/cloudeq/plane2_agents/` — roles, supervisor, repair loop, model clients.
- `src/cloudeq/plane3_runtime/` — local Docker and hosted runtime.
- `src/cloudeq/plane4_observability/` — bus, storage, normalization, read API.
- `src/cloudeq/platform/` — integrated dashboard; `shared/` — contracts/interfaces.
- `tests/` — automated checks; `infra/` — images and service configuration.
- [References](docs/references/README.md), [architecture contracts](docs/architecture/contracts.md), [requirements](docs/requirements.md), and [project identity](docs/PROJECT_IDENTITY.md).
- [Cloud demonstration](docs/CLOUD_DEMO.md) and [Render deployment](docs/RENDER_DEPLOYMENT.md).

For submission, use **https://github.com/kaustubhchaudhari11/CloudEQ**. The default `main` branch is the evaluation entry point. The hosted demo is optional; the source and instructions support local evaluation. Do not include your real `.env` file or API key in the submission.
