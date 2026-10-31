# FORGE SPAN: supplied architecture diagram

Source: `FORGE-SPAN-architecture.jpg`, supplied by the user. This is a human-readable
transcription plus explicitly separated implementation notes. Inspect the image for
layout and arrows; the original image is unchanged.

## Diagram content

1. Intake and trigger: natural-language prompt or CLI command flows into the intake
   and situation router, with Gemini pre-flight evaluation.
2. Agent orchestration (CrewAI): a supervisor/team assembler parses `agents.yaml`
   and context. Stages are Requirements, Planner, Architect, Developer, QA tester,
   and DevOps. Developer sends diffs to QA; QA sends trace feedback to Developer.
   A passing QA result proceeds to DevOps.
3. Sandboxed runtime (Docker / E2B): file write, run tests, and Git commit operations.
   The Developer-to-runtime arrow is labeled "FOAP tool calls".
4. Telemetry and observability: events, tokens, and traces flow into Apache Kafka,
   then a Gemini normalization agent. Outputs lead to dual-retention storage
   (MongoDB / PostgreSQL; audit trail, diffs, commits) and Grafana dashboards
   (trace spans, latencies, tokens, iterations, status).

## Implementation interpretation and open decisions

- Preserve the four-plane boundaries. The current selected stack uses Docker and
  MongoDB; E2B/PostgreSQL are alternatives, not extra mandatory installations.
- Emit telemetry from all planes, even though this simplified drawing emphasizes
  runtime events. Shared contracts/ports keep these integrations decoupled.
- The raw event must survive normalization failure. Add a durable raw-preservation
  path before normalization; the diagram does not specify its detailed mechanism.
- Dual retention means raw and canonical forms, not fixed retention durations.
- A normalization-to-dashboard arrow does not define a Grafana data-source protocol;
  choose a supported adapter/export path during implementation.
- Bound the repair loop; require an explicit passing result before DevOps handoff.
- The Git commit box is a proposed runtime capability, not permission to commit or
  push arbitrary host files. Any generated-workspace commit must be isolated and
  governed by a defined execution policy.
- "FOAP tool calls" is a supplied label, not evidence of a published FOAP SDK/API.
  Define runtime tool contracts rather than inventing such a dependency.
