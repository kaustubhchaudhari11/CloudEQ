# Architecture baseline

This scaffold follows the four-plane layout recovered from the earlier Project
Setup Guide. The original CloudEQ proposal and FOAP paper are not available here,
so the layout is a working baseline pending source verification.

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

Raw and canonical retention are independently configured. Durations, TTL behavior,
canonical fields, redaction policy, and failure handling need explicit decisions
before implementation. Never let normalization overwrite raw events.

The previous guide mentions seven conceptual FOAP layers. Their names and mapping
are intentionally not reconstructed without the paper. Likewise, the Grafana data
source/export path remains undecided; direct MongoDB dashboard support is not assumed.
