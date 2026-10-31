# Setup decisions and open questions

## Recorded during foundation setup

- Use the folder containing `CloudEQ.code-workspace` as the project root.
- The requested Cursor working location is `C:\Users\kaust\projects\CloudEQ`.
- Keep four independently organized plane packages under `src/cloudeq`.
- Place shared configuration, contracts, and ports under `src/cloudeq/shared`.
- Apply Cursor guidance project-wide and mirror the requested legacy rules file.
- Keep all package markers empty; defer application modules and dependencies.
- Preserve arbitrary source payloads and separately normalized canonical events.
- Configure raw and canonical retention independently, without selecting durations.
- Use offline adapters for future unit testing and initial intake development.

## Resolve when implementation begins

- Verify the proposal's exact scope and the FOAP paper's layer definitions.
- Select supported Python/library versions and a dependency-management approach.
- Define handoff contracts, canonical event schema/versioning, and correlation IDs.
- Select Gemini model IDs and confirm their integration through provider adapters.
- Define raw preservation format, redaction, retention durations, and deletion policy.
- Define Kafka delivery/retry semantics, idempotency, and normalization failure storage.
- Choose Docker execution limits, network access rules, and repair-loop bounds.
- Choose Grafana's data source/export path and required dashboard metrics.

Example addresses, topics, and collection names in `.env.example` are proposed
local-development values only. No service or dependency has been configured to use them.
