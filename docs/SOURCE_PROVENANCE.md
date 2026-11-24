# Source provenance for the SSDI submission

The submitted implementation is the completed **Drive project plus subsequent
deployment fixes**, not a replacement with the older three-plane milestone.

## Source compared

Downloaded folder: `CloudEQ-main-20261117T210342Z-1-001/CloudEQ-main`.
It was supplied by the team through Drive and extracted locally on November 17,
2026. The comparison on November 23 used that local download, not a newly fetched
Drive revision. No claim is made about later edits in the online Drive folder.

Compared 127 project files, excluding local secrets, virtual environments,
caches, logs, and generated runtime data. UTF-8 text was also compared after
normalizing line endings; binary assets were compared as bytes.

## GitHub branches checked

- `main` at `59be07a011406f9aceb29321fdc0274281d9b53e` is the older Plane 3
  milestone. It is missing 28 files from the completed Drive project, including
  the integrated dashboard and most Plane 4 modules.
- `deploy/render-full-stack` at `d24530c6b058fd0607410130387143da5fbb77a4`
  contains every one of the 127 compared Drive files. Of those, 104 are byte
  identical, nine differ only in encoding/line endings, and 14 contain intentional
  code/configuration changes. It additionally contains 27 supporting files.
- The initial integration commit `9f8eace` already contained all 127 Drive files:
  117 matched after line-ending normalization and ten had deployment changes.

These counts describe the checked revision before the submission documentation
cleanup. Later documentation commits update the README, environment comments,
contribution notes, and status history; they do not replace the Drive implementation.

## Why some files differ from Drive

The 14 changed paths at `d24530c` were:

```text
.gitattributes
infra/runtime/Dockerfile
pyproject.toml
src/cloudeq/plane1_intake/router/gemini.py
src/cloudeq/plane2_agents/agents/crewai_live.py
src/cloudeq/plane2_agents/crew_run.py
src/cloudeq/plane2_agents/supervisor.py
src/cloudeq/plane3_runtime/executor.py
src/cloudeq/plane4_observability/normalizer/__init__.py
src/cloudeq/platform/server.py
src/cloudeq/platform/service.py
src/cloudeq/platform/settings.py
src/cloudeq/platform/web/index.html
uv.lock
```

Changes add the Render runtime and authentication, identify remote execution
accurately, allow selecting the Part 1 template workflow, retry temporary Gemini
failures, clarify agent output constraints and UI errors, and bundle Flask for
generated web tests. Added files include Render configuration, the remote runner,
login/access handling, regression tests, and deployment evidence documentation.
The dependency files include those additions. The `.gitattributes` change
normalizes shell-script line endings for Linux images.

Both versions remain inspectable in Git history. The downloaded Drive folder and
the earlier local development checkout were not overwritten. Working on a
separate branch does not change `main` until an integration merge is made.

## Submission rule

PR #6 was merged as `30cfb625b965a2023a896bed359336dc7b6ca0e1` on November 23,
2026. Its tree matched the completed deployment branch. The repository was
confirmed public on November 24. Use the normal repository URL and clone command
in README.md: the default `main` now contains the completed project. The older
`main` comparison above is historical evidence of the work brought in by that merge.
Actual keys and local `.env` files are intentionally excluded from submission.
