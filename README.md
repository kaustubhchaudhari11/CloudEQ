# FORGE SPAN

**An autonomous multi-agent SDLC framework with federated observability**
Team: **Cloud EQ**. Repository/package identifiers remain `CloudEQ` / `cloudeq`.

## Submission source and status

The complete Drive project plus our deployment fixes is on **`deploy/render-full-stack`**. Use the branch-specific clone command below. At the November 23 check, `main` still contained the older Plane 3 milestone. See [source provenance](docs/SOURCE_PROVENANCE.md) for the comparison.

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

The repository is private until the team changes its visibility; private access requires an invitation and your own GitHub account. No team credentials are included.

```text
git clone --branch deploy/render-full-stack --single-branch https://github.com/kaustubhchaudhari11/CloudEQ.git FORGE-SPAN
cd FORGE-SPAN
uv python install 3.12
uv sync --locked --python 3.12
```

For a ZIP, select `deploy/render-full-stack` on GitHub before **Code → Download ZIP**. Extract it, open a terminal in the directory containing `pyproject.toml`, then run the two `uv` commands. No developer-specific absolute path is needed.

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

## 3. First check: no key or Docker required

Keep the copied `.env` defaults and run:

```text
uv run --locked cloudeq-server
```

Open <http://127.0.0.1:8000>. Select **Part 1: template workflow and repair demonstration** and submit `Add a health check`. In `simulation` execution mode, the workflow and telemetry are real application behavior but test outcomes are simulated. Expect `simulation=true`, `live_gemini=false`, and `host_execution=false`.

The repair budget defaults to three attempts. **Repair ×2** fails twice and passes on the third attempt. **Budget exhausted** fails all three and skips DevOps. **Blank (rejected)** demonstrates validation. **Infeasible** uses an unknown dataset; there is no dataset catalog.

Terminal-only demonstration of these five scenarios:

```text
uv run --locked cloudeq-demo
```

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

## 6. Observability and optional service stack

Local defaults use an in-process event bus and SQLite, with no extra service. The **Rich event**, **Drifted fields**, and **Malformed** ingest examples demonstrate successful normalization and preserved raw data on normalization failure. **Retry failed** processes retained failures again. Trace IDs connect activity across the planes.

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
- **Missing Flask:** rebuild `infra/runtime/Dockerfile`; it includes Flask. Arbitrary generated package-install commands are not supported.
- **Port occupied:** stop the other server or use `cloudeq-server --port 8001`.
- **Old settings:** process environment values override `.env`; use a fresh terminal and restart the server after edits.
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

Submit the complete source branch and ensure the evaluator can access it. Do not submit only the hosted URL or include your real `.env` file.
