# CloudEQ

CloudEQ is a planned four-plane, multi-agent SDLC semester project using Python,
FastAPI, CrewAI, Kafka, MongoDB, Docker, Grafana, and the Gemini API.

## Setup status

Foundation only: Cursor project rules, configuration examples, documentation,
directories, and empty Python package markers. No application logic, dependencies,
infrastructure services, tests, or generation prompts have been executed or installed.
This directory is the CloudEQ project root; no nested CloudEQ folder is required.

Open this folder in Cursor, or open `CloudEQ.code-workspace`. The always-applied
rule is `.cursor/rules/cloudeq.mdc`; `.cursorrules` contains the same guidance for
compatibility. Keep their rule bodies synchronized.

## Workspace structure

```text
.
|-- CloudEQ.code-workspace
|-- .cursor/rules/cloudeq.mdc
|-- .cursorrules
|-- .gitignore
|-- .env.example
|-- README.md
|-- docs/
|   |-- architecture/
|   |   |-- overview.md
|   |   `-- decisions.md
|   `-- references/README.md
|-- src/cloudeq/
|   |-- shared/
|   |   |-- contracts/
|   |   `-- ports/
|   |-- plane1_intake/
|   |   |-- api/
|   |   `-- router/
|   |-- plane2_agents/
|   |   |-- agents/
|   |   `-- config/
|   |-- plane3_runtime/
|   `-- plane4_observability/
|       |-- normalizer/
|       `-- storage/
|-- infra/
|   |-- docker/
|   |-- kafka/
|   |-- mongodb/
|   `-- grafana/provisioning/
|-- tests/
|   |-- plane1/
|   |-- plane2/
|   |-- plane3/
|   |-- plane4/
|   `-- integration/
`-- scripts/
```

Python package directories contain empty `__init__.py` markers. Empty non-package
directories contain `.gitkeep` markers so their structure can later be tracked.

## References and next step

The proposal and FOAP paper were mentioned in the prior conversation, but their
attachments were not accessible during setup. See `docs/references/README.md`.
Architecture notes distinguish recovered guidance from decisions still awaiting
the original documents.

When ready, supply the missing documents and use `docs/CURSOR_START_PROMPT.md` in
Cursor Agent mode for the first implementation session (foundation and Plane 1).
The full-project prompt in `docs/CURSOR_BUILD_PROMPT.md` covers all five milestones.
Both start with intake contracts and an offline router adapter.
Application files such as `main.py`, `service.py`, `pyproject.toml`,
Dockerfiles, Compose configuration, and test implementations are deliberately left
for that implementation step. `.env.example` is a planning template, not a running
configuration; `.env` and API credentials have not been created.

## Add project reference files

Copy the original proposal to `docs/references/CloudEQ.pdf` and the FOAP paper to
`docs/references/FOAP-paper.pdf`. Add any assignment rubric or other supplied project
documents in the same folder with descriptive filenames. Add these files as context
to your Cursor chat along with `docs/CURSOR_BUILD_PROMPT.md`. If Cursor cannot read a
PDF, provide an accurate text export alongside the original and identify its source.
Files attached in a separate ChatGPT conversation are not automatically local files
in this project. Never attach `.env` or API credentials as chat context.

## GitHub and team contribution

The private repository is [kaustubhchaudhari11/CloudEQ](https://github.com/kaustubhchaudhari11/CloudEQ).
The CloudEQ folder has its own Git repository on `main`; it is independent of any
repository in its parent directory. See `CONTRIBUTING.md` for task branches and
pull-request review. A PR template is included under `.github/`.

The selected model in Cursor writes project code; Gemini is the configured runtime
provider for the project's future adapters. These are separate choices.
