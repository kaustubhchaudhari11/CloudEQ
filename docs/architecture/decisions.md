# Setup decisions and open questions

Product name: FORGE SPAN. Team: Cloud EQ. Technical identifiers stay
`CloudEQ`, `cloudeq`, and `CLOUDEQ_`.

## Recorded during foundation setup

- Use the folder containing `CloudEQ.code-workspace` as the project root.
- The requested Cursor working location is `C:\Users\kaust\projects\CloudEQ`.
- Keep four independently organized plane packages under `src/cloudeq`.
- Place shared configuration, contracts, and ports under `src/cloudeq/shared`.
- Apply Cursor guidance project-wide and mirror the requested legacy rules file.
- Keep package markers free of application behavior until a plane is implemented.
- Preserve arbitrary source payloads and separately normalized canonical events.
- Configure raw and canonical retention independently, without selecting durations.
- Use offline adapters for future unit testing and initial intake development.

## Recorded during configuration (2026-10-31)

Checked on this workstation: Python 3.12.2 (`py -3.12`), uv 0.13.2
(2026-10-19). Versions below were read from official project or PyPI pages.
Runtime libraries were not installed.

### Python and packaging

The library window that satisfies the stack is CPython `>=3.11,<3.14`:

| Library | Version observed | Python constraint | Source |
| --- | --- | --- | --- |
| CrewAI | 1.15.33 | `>=3.10,<3.14` | [CrewAI installation](https://docs.crewai.com/installation) and [PyPI](https://pypi.org/project/crewai/) |
| FastAPI | 0.162.0 | `>=3.10`; depends on Pydantic `>=2.9.0` | [PyPI](https://pypi.org/project/fastapi/) |
| PyMongo | 4.19.0 | `>=3.11` | [PyPI](https://pypi.org/project/pymongo/) |
| confluent-kafka | 2.16.1 | `>=3.8` | [PyPI](https://pypi.org/project/confluent-kafka/) |
| pytest | 9.2.0 | `>=3.10` | [PyPI](https://pypi.org/project/pytest/) |
| Ruff | 0.17.3 | tool supports this interpreter | [PyPI](https://pypi.org/project/ruff/) |
| mypy | 2.4.1 locked; 2.4 announced 1 Oct 2026 | supports this interpreter | [mypy news](https://www.mypy-lang.org/news.html) and the project lockfile |

The project requires `>=3.12,<3.14` because Python 3.12.2 is the interpreter
installed here and it sits inside that window. Python 3.14 is excluded because
CrewAI 1.15.33 does not support it. Python 3.11 is inside the library window
and is not the configured target.

Packaging uses `pyproject.toml`, the existing `src/cloudeq` layout, and uv.
The lockfile is `uv.lock`. The environment is the project-local `.venv`, which
Git ignores. Development dependencies are pytest, Ruff, mypy, and types-PyYAML.

Plane 1 installed, from PyPI on 2026-10-31, and locked in `uv.lock`:

- FastAPI 0.162.0
- Uvicorn 0.54.0
- httpx 0.28.1
- Pydantic 2.14.2
- pydantic-settings 2.16.2

The Gemini router uses the official `models.generateContent` REST method on
`generativelanguage.googleapis.com` with an injected HTTP client. No Gemini SDK
is installed. PyMongo and confluent-kafka remain candidates for Plane 4 and are
not installed.

Plane 2 installed PyYAML 6.0.3 and the dev stub package types-PyYAML
6.0.12.20261030 so `agents.yaml` can be parsed and type-checked. The default
engine is `offline`: a labeled simulation.

On 2026-11-02, CrewAI 1.15.34 was installed with the `google-genai` extra.
That lock resolved `google-genai` 1.65.0. CrewAI's own constraint is
`>=3.10,<3.14`, which matches this project. The native Gemini call is
`LLM(model="gemini/<GEMINI_AGENT_MODEL>", api_key=..., timeout=...)`.
The model id stays empty until someone sets it. Official docs:
[CrewAI 1.15.34](https://pypi.org/project/crewai/1.15.34/) and
[CrewAI LLMs](https://docs.crewai.com/v1.15.34/en/concepts/llms).
Installing the package does not prove a live kickoff. Live mode returns
execution unavailable until Plane 3 provides a container executor.

### Runtime and storage

- Docker is the sandbox backend. The diagram also names E2B. E2B is not configured.
- Proposal prose requires a sandbox and does not name Docker or E2B. Those product
  names come from the diagram.
- MongoDB is the dual-retention database. PostgreSQL remains the alternative
  named by proposal p. 2 and the diagram.
- One database, separate raw, canonical, and normalization-attempt collections.
- Raw payload bytes are write-once. Canonical status may change on retry.
- Kafka delivery is at-least-once. Consumers deduplicate on `event_id`.
  Exactly-once delivery is not claimed.
- Repair maximum defaults to 3. That number is not in the proposal.
- Workspace Git commit stays disabled. Git push is not an operation.
- Generated code is not executed on the host.

### Grafana

Grafana's Infinity datasource reads a future Plane 4 HTTP JSON API.
Plugin documentation: [Infinity](https://grafana.com/docs/plugins/yesoreyeram-infinity-datasource/latest/).
That page requires Grafana 11.6 or later. Grafana is not installed or started here.
Grafana does not receive `MONGODB_URI`. The prototype's Grafana Loki path
(FOAP Table 3, p. 7) is not adopted. n8n is not adopted.

### Models

`GEMINI_ROUTER_MODEL` and `GEMINI_NORMALIZER_MODEL` stay empty. Empty means
"not configured", not a hidden default. FOAP pp. 6 and 10 identify Gemini 2.5
Flash as the prototype normalizer. That is evidence, not this project's model ID.
`CLOUDEQ_GEMINI_LIVE_CALLS` defaults to false.

### Contracts

Shared types and ports are specified in `docs/architecture/contracts.md`.
Requirements and checks are in `docs/requirements.md`.
Plane 1 and Plane 2 contain application code. Plane 3 and Plane 4 remain
package markers. `RuntimeExecutor` is the only path from the supervisor to a
sandbox. The current implementation is `OfflineRuntimeSimulation`.

## Still unresolved

- Retention durations and any deletion or TTL behavior. Empty settings stay empty.
- A complete redaction policy beyond the minimum attribute-key denylist.
- Explicit Gemini model IDs and who supplies the API key locally.
- GitHub Issue and Jira field mapping, authentication, and webhook or poll behavior.
- The canonical field catalog beyond linkage, status, provenance, and missing-field
  markers. FOAP Table 4 is a candidate, not a frozen schema.
- Whether a later plane replaces confluent-kafka with another supported client
  after checking that client's Python constraint.
- Grafana dashboard layout and which Infinity queries map to spans, latencies,
  tokens, iterations, and status.
- No assignment rubric has been supplied.

Example addresses, topics, and collection names in `.env.example` are local
planning values. No broker, database, container, or dashboard was started.
