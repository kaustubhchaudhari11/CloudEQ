# Architecture baseline

The supplied team proposal (`docs/references/CloudEQ.pdf`, pp. 1-2) confirms
this four-plane SDLC architecture. The FOAP research paper supports the observability
design; see `docs/references/README.md` for source distinctions. Cloud EQ is the team
name; FORGE SPAN is the accepted project name, while CloudEQ remains the technical identifier.
The supplied diagram is `docs/references/FORGE-SPAN-architecture.jpg`; read its companion
Markdown for labels and design interpretation.

## Plane responsibilities

1. **Intake & Trigger** (`plane1_intake`): FastAPI and CLI intake, request
   validation, feasibility routing through a Gemini adapter or offline fake,
   and validated task handoff.
2. **Dynamic Agent Engine** (`plane2_agents`): CrewAI orchestration for requirements,
   planning, architecture, development, testing, and DevOps, including a bounded
   Developer-Tester repair loop.
3. **Sandboxed Runtime** (`plane3_runtime`): Docker-isolated execution, runtime
   workspace ownership, resource policies, and structured execution/test results.
4. **FOAP Observability** (`plane4_observability`): telemetry ingestion through
   Kafka, raw preservation, Gemini-assisted canonical normalization, separate
   MongoDB stores, and observability for Grafana.

## Boundaries and data

Shared contracts and ports define handoffs; plane internals remain independent.
Every plane emits correlated telemetry through an interface. Domain code should
be testable with in-memory adapters, without external services.

Schema-agnostic ingestion accepts heterogeneous event payloads; it does not remove
envelope validation, payload-size limits, or normalized-output validation. Preserve
the accepted raw representation and metadata before normalization, link canonical
records to their raw event, and retain failures for diagnosis/retry.

Raw and canonical retention are independently configured. Durations and TTL
behavior remain unset. The canonical field catalog and a full redaction policy
are still open. Failure handling is specified: a failed normalizer keeps the raw
event. Never let normalization overwrite raw events.

FOAP Table 1 (PDF p. 4) names seven layers: Source systems, Source data, Streaming,
Event-driven, Processing, Storage, and Analysis. For this project, Planes 1-3 supply
systems/data; Plane 4 handles streaming, routing, normalization, storage, and analysis.
This mapping is our implementation interpretation, not a claim that the paper defines
the proposal's four planes. The paper's prototype uses n8n and Grafana Loki (Table 3,
p. 7); these are not project dependencies. Grafana reads a future Plane 4 HTTP API
through the Infinity datasource, documented in `docs/architecture/decisions.md`.

Dual retention means keeping both raw and canonical forms (FOAP pp. 2, 5, 7).
Independently configurable expiry policies are a project design choice, not a
paper-specified duration. Proposal p. 2 names a dual-retention store of
MongoDB/PostgreSQL. The pypdf text of that page does not name Docker or E2B;
the supplied diagram labels the sandbox "Docker / E2B". The project selects
MongoDB and Docker. PostgreSQL and E2B stay alternatives.

The proposal also describes GitHub Issues/Jira initiation (p. 1). The diagram
shows prompt and CLI intake only. Ticket initiation stays on the roadmap.
Raw preservation, the repair bound, and the Grafana read path are specified in
`docs/architecture/contracts.md` and `docs/architecture/decisions.md`.
Requirement IDs and planned checks are in `docs/requirements.md`.
