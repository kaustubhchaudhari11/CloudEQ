# CloudEQ implementation prompt for Cursor

Open `C:\Users\kaust\projects\CloudEQ\CloudEQ.code-workspace` in Cursor. First copy
the original proposal, FOAP paper, and any assignment rubric into `docs/references/`
and add them to the chat context. Paste the prompt below into Cursor Agent mode.
This is a saved prompt only; it has not been executed during foundation setup.

---

Act as the lead architect and implementation engineer for CloudEQ. Build this
semester project from the existing foundation through a working, demonstrable MVP.
I authorize implementation of all four planes in the sequence below, including
project-local dependencies and development configuration. Inspect existing files
first, preserve my work, and follow `.cursor/rules/cloudeq.mdc` and `.cursorrules`.
Do not stop after generating a plan or skeleton; implement and verify each milestone.

## Source requirements and working method

1. Read the CloudEQ proposal, FOAP paper, any rubric in `docs/references/`, README,
   and architecture notes. If the proposal or paper is missing or unreadable, ask
   me for it before claiming source compliance. You may continue independent
   foundation work with explicitly documented assumptions while awaiting sources.
2. Extract verifiable requirements with document/page references into
   `docs/requirements.md`. Separate source requirements from design choices. Do not
   invent FOAP layer names, retention durations, benchmark results, or citations.
   If supplied documents conflict materially with these instructions, ask me to resolve it.
3. Record an implementation checklist and update it after each milestone, including
   checks actually run and unresolved blockers. Consult official documentation when
   selecting compatible Python/library versions and current integration APIs.
4. Use Python, FastAPI, CrewAI, Kafka, MongoDB, Docker, Grafana, and Gemini. Keep
   concrete integrations behind interfaces and keep unit tests offline.
5. Make routine engineering choices independently. Ask only when missing information
   materially blocks progress. Never publish, deploy remotely, incur paid API usage,
   delete user data, or overwrite unrelated work without explicit authorization.

## Milestone 1: foundation and Intake & Trigger

- Add `pyproject.toml`, reproducible dependency configuration, environment validation,
  and Windows PowerShell setup/run instructions. Keep secrets in ignored local files.
- Define shared task, execution, and telemetry contracts with stable IDs and trace
  correlation; define ports without importing other planes' internal implementations.
- Implement FastAPI health and task-submission endpoints, a CLI, validation, service
  logic, and a feasibility-router interface with offline fake and Gemini adapters.
- Make offline mode the default and keep intake independent of live Kafka/MongoDB.
  Document HTTP contracts, failure cases, and commands. Verify API/CLI behavior,
  invalid input, router failures/timeouts, and correlation propagation.

## Milestone 2: Dynamic Agent Engine

- Implement CrewAI orchestration for requirements, planning, architecture, developer,
  tester, and DevOps roles, aligned with the proposal's exact requirements.
- Define typed handoffs and a supervisor with a configurable, bounded Developer-Tester
  repair loop. Record iteration counts, termination reasons, outputs, and failures.
- Use a runtime port for execution requests. Provide deterministic offline adapters
  for tests and clearly label them as simulations; they do not prove live CrewAI or
  Gemini execution. Verify success, failure, exhausted repair budgets, and cancellation.

## Milestone 3: Sandboxed Runtime

- Implement Docker execution and per-task workspaces with path validation, resource
  limits, timeouts, non-root execution, restricted mounts, and network denied by default.
  Do not expose host credentials or the Docker socket inside generated-code containers.
- Return structured exit status, output, timing, artifacts, and test results. Implement
  cleanup scoped to owned task directories. Never execute generated code on the host.
- Verify timeout/error handling and workspace isolation. If Docker is unavailable,
  continue adapter tests and clearly report runtime integration as unverified.

## Milestone 4: FOAP Observability

- Emit telemetry from every plane through a shared port. Implement Kafka production
  and consumption with bounded retries, idempotency, and explicit delivery semantics.
- Accept heterogeneous payloads with a stable envelope and payload-size controls;
  do not require source-specific fields at ingestion.
- Preserve accepted raw events before normalization. Store raw and canonical records
  separately in MongoDB, linked by event IDs and trace IDs, with canonical schema
  version and normalization provenance/status. Normalization failures must retain raw
  events and support diagnosis/retry without silent loss.
- Implement Gemini-assisted normalization behind an interface with offline fixtures;
  validate outputs and treat input events as data, not instructions.
- Configure raw and canonical retention independently. Leave deletion disabled until
  retention policies are explicitly chosen; do not invent TTL durations from the paper.
  Define secret filtering/redaction before telemetry capture and explain raw fidelity.
- Choose and document a supported Grafana data source/export path; add any required
  metrics adapter explicitly. Provide dashboards for cross-plane operations, failures,
  repair iterations, and observability pipeline health without assuming direct MongoDB
  support. Map the paper's actual FOAP layers after reading it.

## Milestone 5: integration and demonstration

- Add Dockerfiles and local Compose services for the implemented components, with
  environment examples, health checks, persistence, and clear startup/shutdown commands.
  Do not remove Docker volumes as part of normal verification or shutdown.
- Provide an offline demonstration and a distinct real-integration procedure. The
  end-to-end path should show request intake, agent orchestration, container execution,
  a bounded repair flow, and correlated raw/canonical telemetry observable in Grafana.
- Add meaningful per-plane tests and boundary/integration tests. Verify retained raw
  data after failed normalization, duplicate handling, validation, and runtime limits.
- Run the applicable tests, lint/type checks, and smoke checks, then repair failures.
  Distinguish passed, skipped, unavailable, and unrun checks. Never report a mocked
  demonstration as verification of live services or model integrations.
- Complete README, architecture decisions, requirement-to-feature/test traceability,
  setup/troubleshooting guide, demo script, and known limitations for semester review.

## Completion criteria

All four planes have implemented behavior and documented boundaries; offline tests
pass; runnable integration configuration and a reproducible demo are supplied; source
requirements are traced to implementation and verification; and outstanding service,
credential, or document blockers are clearly reported. Mark live integration complete
only after actually exercising it. Do not leave core functions as TODOs or stubs and
claim completion. End with exact run commands and a concise verification report.

Start by inspecting this workspace and the references, then implement Milestone 1
and continue through the remaining milestones within this authorization.
