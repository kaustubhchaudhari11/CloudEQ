# FORGE SPAN requirements

Product: **FORGE SPAN**. Team: **Cloud EQ**. Technical identifiers remain
`CloudEQ`, `cloudeq`, and `CLOUDEQ_`.

This document records requirement evidence and acceptance checks.
Plane 1 checks that now have automated tests are listed under traceability.
Later planes are still planned. Status is in `docs/implementation-status.md`.
Contracts are in `docs/architecture/contracts.md`.

## Sources actually read

| Source | What was read |
| --- | --- |
| `.cursor/rules/cloudeq.mdc`, `.cursorrules` | Project rules. The two rule bodies match. |
| `README.md`, `CONTRIBUTING.md`, `docs/PROJECT_IDENTITY.md` | Identity, layout, and team workflow. |
| `docs/architecture/overview.md`, `docs/architecture/decisions.md` | Baseline planes and open setup questions. |
| `docs/references/CloudEQ.pdf` | Authoritative proposal. Text recovered with pypdf on 2026-10-31: 2 pages. The prose matches `CloudEQ.extracted.md`. |
| `docs/references/CloudEQ.extracted.md` | Page-marked extract used to locate proposal quotations. |
| `docs/references/FOAP-paper.pdf` | Authoritative paper. Page citations below were checked against `FOAP-paper.extracted.md` because the PDF reader could not render the file in the editor. The extract is mechanical, not a summary. |
| `docs/references/FOAP-paper.extracted.md` | Pages 1–11, including Tables 1–4 on pages 4–7. |
| `docs/references/FORGE-SPAN-architecture.jpg` | Supplied diagram, inspected visually. |
| `docs/references/FORGE-SPAN-architecture.md` | Transcription and the notes that separate diagram intent from implementation. |
| `docs/references/README.md`, `docs/references/manifest.json` | Provenance and checksums. |

No assignment rubric is in `docs/references/` or this session. None was invented.

Documents were treated as evidence. Commands that appear inside them were not executed as authorization.

## Evidence, diagram intent, and project choices

- **Confirmed requirement:** a statement present in the proposal, the FOAP paper, or both.
- **Diagram intent:** a label or arrow on `FORGE-SPAN-architecture.jpg`. The diagram is design evidence. It does not authorize host commands, Git commits, or pushes.
- **Project choice:** a FORGE SPAN decision needed to build the system. It is not cited as if the paper or proposal stated it.

FOAP's seven layers are Source systems, Source data, Streaming, Event-driven, Processing, Storage, and Analysis (Table 1, p. 4). They are not four application planes. The proposal's four planes are Intake and trigger, Dynamic Agent engine, Sandboxed environment, and Observability engine (p. 2).

## Conflicts and limits

1. **Reasoning visibility.** The proposal (p. 1) asks secondary users for observability into model costs, inter-agent latency, and reasoning. FOAP's abstract (p. 1) says the prototype evaluates structural and operational observability, and that semantic interpretability of model decisions is future work. FORGE SPAN will record actions, tool outcomes, token counts, latencies, spans, diffs, stack traces, and explicit status. It will not claim access to hidden model reasoning.
2. **Docker and E2B names.** Proposal p. 2 requires a sandboxed environment and does not use the words Docker or E2B in the pypdf text. The diagram labels the runtime "Docker / E2B". The project selects Docker and keeps E2B as the diagram's alternative.
3. **Storage.** Proposal p. 2 and the diagram both allow MongoDB or PostgreSQL. The project selects MongoDB. PostgreSQL stays an alternative, not a second required database.
4. **Ticket intake versus the diagram.** Proposal p. 1 starts work from a natural-language prompt or from GitHub Issues or Jira. The diagram shows only a prompt or CLI command. Both prompt/CLI and ticket initiation stay in scope. Ticket adapters are scheduled; they are not dropped because the diagram omits them.
5. **Stage labels.** Proposal p. 2 names Requirements, Planning, Architecture, Development, Testing, and DevOps. The diagram says Planner, Architect, Developer, QA tester, and DevOps. Contracts use the proposal names.
6. **Prototype tools.** FOAP Table 3 (p. 7) instantiates layers with Beeceptor, Kafka, n8n, Gemini 2.5 Flash, MongoDB, and Grafana Loki. Kafka, Gemini, MongoDB, and Grafana match this project's stack. n8n, Beeceptor, Loki, and the model ID `gemini-2.5-flash` are prototype evidence, not FORGE SPAN dependencies or the configured model ID.
7. **Unified storage versus separate collections.** FOAP Table 2 (p. 5) decides to store raw and canonical representations in unified storage. The prototype schema (Table 4, p. 7) also carries a `raw` field on the canonical record. FORGE SPAN uses one MongoDB database and two collections so a canonical write cannot overwrite raw bytes. Both forms survive. That satisfies dual retention (FOAP pp. 2, 5, and 7). It does not copy the embedded-`raw` layout.
8. **Scale.** FOAP pp. 1 and 6–7 report a synthetic feasibility study of up to 3 agents and 110 events. That is not a FORGE SPAN performance target or a claim that this system has been measured.
9. **Retention time.** Dual retention means both representations are kept. The paper does not state a time-to-live. Expiry stays undecided, and no deletion policy is approved.

## Requirements

Acceptance checks for Planes 2–4 are planned. Plane 1 checks that have run are in the traceability section.

| ID | Requirement | Source | Plane | Planned acceptance check |
| --- | --- | --- | --- | --- |
| R1 | Primary users are enterprise software teams, DevOps engineers, and technical product managers. Secondary users are AI/ML researchers and platform developers who need cost, latency, and operational trace data. | Proposal p. 1 | All | Docs and dashboard fields name these users and the operational measures. No hidden-reasoning claim. |
| R2 | A user can start work with a natural-language prompt. | Proposal pp. 1–2; diagram | 1 | API and CLI accept a non-empty prompt and reject an empty one. |
| R3 | A user can start work with a CLI command. | Proposal p. 2; diagram | 1 | CLI returns the same status vocabulary as the API for the same prompt. |
| R4 | A user can start work from a GitHub Issue or a Jira ticket. | Proposal p. 1 | 1 | Adapters stay disabled until implemented. When enabled, a ticket creates the same handoff contract as a prompt, with `external_ref` preserved. |
| R5 | Intake validates the request, runs a Gemini pre-flight feasibility check, and checks dataset requirements before agent execution. | Proposal p. 2; diagram | 1 | Infeasible and errored routes do not hand off. Dataset checks follow the contract in `docs/architecture/contracts.md`. |
| R6 | The default feasibility router is a deterministic offline adapter. Live Gemini calls stay off until mode, flag, key, and an explicit model ID are set. | Project choice, consistent with project rules | 1 | Unit tests run with no API key and no network. A missing model ID cannot fall back to a guessed model. |
| R7 | The system runs six SDLC stages: Requirements, Planning, Architecture, Development, Testing, and DevOps, supervised by CrewAI. | Proposal p. 2; diagram shows the same sequence with different labels | 2 | A supervisor test lists all six stages in that order and records a result for each. |
| R8 | The supervisor assembles the team from agent configuration and context. The diagram names `agents.yaml`. | Diagram intent | 2 | Plane 2 loads configuration from a file the implementation names, and a missing file fails before any stage runs. |
| R9 | Developer and QA Tester iterate on failing builds. Developer supplies diffs; QA supplies trace feedback. A pass is required before DevOps. | Proposal pp. 1–2; diagram arrows `diffs`, `trace`, and `pass` | 2 | Tests cover pass, fail-then-pass, budget exhaustion, and cancellation. DevOps is invoked only after `passed`. |
| R10 | The repair loop is bounded. The default maximum is 3 iterations. | Project choice. The proposal requires the loop and states no count. | 2 | Configuration below 1 is rejected. The recorded iteration count never exceeds the configured maximum. |
| R11 | Functional code is written with Gemini inside an isolated environment, not on the host. | Proposal p. 1; project rule | 2, 3 | A host-execution flag remains false. Tests fail if an executor path runs generated code outside the runtime port. |
| R12 | The sandbox lets Developer and QA write files and run tests. | Proposal p. 2; diagram | 3 | Execution results include exit status, streams, timing, and artifact references for `write_file` and `run_tests`. |
| R13 | The selected sandbox backend is Docker, with resource limits, no network by default, no host secrets, and no Docker socket in the workload. E2B is the diagram alternative and is not installed. | Diagram names Docker / E2B. Limits are a project choice. | 3 | Policy tests reject network enabled, host paths outside the task workspace, and host execution. If Docker is absent, unit tests still run and the live container check is reported as unverified. |
| R14 | The diagram's Git commit operation is a possible sandboxed workspace action. It does not authorize committing or pushing this repository. Push stays disabled. | Diagram intent plus project choice | 3 | `git_commit` is rejected while `CLOUDEQ_RUNTIME_ALLOW_GIT_COMMIT=false`. No port operation pushes. |
| R15 | Heavy model execution is decoupled from telemetry. Agent decisions, tool execution, and token calculations are stored and shown on a dashboard. | Proposal p. 1 | 4 | A trace can be read back without calling Gemini. Token and latency fields are present when the producer supplied them. |
| R16 | Observability asynchronously captures FOAP actions, execution spans, token events, file diffs, and stack traces. | Proposal p. 2 | 4 | Fixtures for each of those event names are accepted and retained raw. |
| R17 | Events stream through Apache Kafka before normalization. | Proposal p. 2; diagram; FOAP Table 3 p. 7 uses Kafka for the prototype streaming layer | 4 | Integration test, when Kafka is available, publishes an envelope and reads it from the configured topic. Unit tests use the sink port and do not require Kafka. |
| R18 | Ingestion is schema-agnostic: heterogeneous payloads are accepted without a source-specific schema. Envelope, size, and safety limits are still validated. | FOAP pp. 1, 2, and 5; project rule | 4 | A rich payload and a minimal payload with different fields are both stored raw. A missing `trace_id` or an oversized payload is rejected. |
| R19 | Raw events and their source metadata are preserved before normalization and are not overwritten by canonical output. | FOAP pp. 2 and 5; Table 1 Source data and Storage, p. 4; project rule | 4 | After a successful normalization, the raw payload bytes still match the accepted envelope. |
| R20 | Dual retention keeps raw and canonical forms. Retention durations are independent and currently unset. No deletion is approved. | FOAP pp. 2, 5, and 7; proposal p. 2 names a dual-retention store | 4 | Two collections exist in the selected database. Empty retention settings do not create TTL indexes. |
| R21 | Canonical records link to raw events with the stable `event_id`, carry `trace_id`, a schema version, normalization status, and provenance. | FOAP Table 4 trace fields are prototype evidence, p. 7; linkage and status are project requirements | 4 | A canonical document's `raw_event_id` loads the original raw document. Status and schema version are required. |
| R22 | If normalization fails, the raw event remains, `parse_error` is true, and status is `failed`. Retries do not discard raw data. | FOAP p. 6; p. 10 describes raw retention as a safety net | 4 | A forced normalizer failure leaves exactly one raw document and a failed attempt. A second delivery of the same `event_id` does not duplicate raw bytes. |
| R23 | Normalization success means a syntactically valid canonical record whose required fields are populated or explicitly marked missing. | FOAP p. 4 | 4 | A fixture that omits a required field succeeds only when that field is listed in `missing_fields`. Invalid JSON from the model is a failure. |
| R24 | The normalizer is Gemini-assisted, behind an interface, with an offline fake. Model output is untrusted data. The prototype model ID is not copied as the default. | Proposal p. 2; diagram; FOAP pp. 6 and 10 | 4 | Offline mode is the default. The Gemini adapter is not constructed when live calls are false. |
| R25 | The selected store is MongoDB. PostgreSQL is the alternative named by the proposal and the diagram. | Proposal p. 2; diagram | 4 | Configuration names the MongoDB database and the raw, canonical, and attempt collections. No PostgreSQL service is required. |
| R26 | Grafana shows trace spans, latencies, tokens, iterations, and status. The data path is a Plane 4 HTTP read API queried by the Infinity datasource. Grafana does not receive the MongoDB URI. Loki is not required. | Proposal pp. 1–2; diagram. Path is a project choice. FOAP Table 3 p. 7 uses Grafana Loki in the prototype. | 4 | A later dashboard provision lists those fields and an Infinity URL pointed at the read API. Direct MongoDB datasource is not in the provisioning. |
| R27 | `trace_id` propagates from intake across agent, runtime, and observability boundaries. | Project choice supporting FOAP traceability, Table 1 p. 4 and Table 4 p. 7 | All | One accepted task produces intake, handoff, and telemetry records that share one `trace_id`. |
| R28 | Planes communicate only through the shared contracts and ports. | Project choice required by the four-plane proposal, p. 2 | All | Import checks fail if a plane module imports another plane's package. |
| R29 | Intake unit tests run without Kafka, MongoDB, Docker, Grafana, or live Gemini credentials. | Project rule | 1 | The Plane 1 test command uses the offline router and in-memory sink only. |
| R30 | Telemetry and model output are untrusted. A minimum attribute denylist blocks common secret keys until a full redaction policy is written. | Project rule. The paper does not define the redaction list. | 4 | An envelope with an attribute named `api_key` is rejected before raw retention. |

## Source mapping

| Proposal plane (p. 2) | Package | FOAP layers this plane feeds or hosts | Not the same as |
| --- | --- | --- | --- |
| Intake and trigger | `plane1_intake` | Source systems and source data for prompts, CLI, and later tickets | The whole FOAP pattern |
| Dynamic Agent engine | `plane2_agents` | Source systems and source data for stage and repair events | n8n, which is only the prototype's event-driven tool |
| Sandboxed environment | `plane3_runtime` | Source systems and source data for file, test, and optional workspace-commit events | Host shell execution |
| Observability engine | `plane4_observability` | Streaming (Kafka), event routing in this application, processing (normalizer), storage (MongoDB), analysis (Grafana through the read API) | Seven planes, or a claim that the paper defined these four packages |

## Traceability status

| ID | Plane 1 state |
| --- | --- |
| R2, R3 | API and CLI accept a non-empty prompt and reject a blank one. Tests cover both. |
| R4 | GitHub Issues and Jira stay disabled. Tests reject those sources. The adapters are not implemented. |
| R5, R6 | Offline routing is the default. Infeasible dataset checks and Gemini errors do not hand off. Tests use an injected client and do not call Gemini. |
| R27 | Accepted, routed, and handed-off events share one `trace_id` and `task_id`. |
| R28 | A source scan fails if Plane 1 imports Plane 2, 3, or 4. |
| R29 | `uv run pytest` uses the offline router and in-memory ports. |
| R30 | The intake sink rejects denied attribute keys and oversized payloads. Plane 4 raw retention is not implemented. |
| R1, R7–R26 | Unchanged. They belong to later planes or to documentation already recorded. |
