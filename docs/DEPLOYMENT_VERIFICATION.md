# Hosted verification — November 23, 2026

Source: completed Drive project, maintained on `deploy/render-full-stack`.
The original downloaded folder and the older local CloudEQ checkout were not
replaced. Secrets were supplied privately to Render, not committed to GitHub.

## Verified infrastructure

- App: https://forge-span.onrender.com
- Grafana: https://forge-span-grafana.onrender.com/d/forge-span-overview
- Private Kafka and MongoDB are running in the same Render workspace.
- Public health returns only minimal service status. Private APIs reject an
  unauthenticated request. Browser sign-in uses a signed secure session cookie.
- Grafana's Infinity connector health check passed after its installation path
  was moved outside the persistent data mount. Dashboard queries displayed data.
- Remote tests run as UID 65534 with no-new-privileges, a read-only uploaded task
  tree, no application API keys, bounded resources, and denied outbound network.
  Three real isolation checks passed; completed test environments were removed.

## Part 1 — passed

Task `8343f60d-5cbd-4aa1-adb0-b7128e711dc9`, trace
`0c22110d-1a4b-4a35-9702-dc4e9390c43f`: the template demonstration failed its first
test and passed its second. DevOps followed the actual pass. Template generation
does not use Gemini, but tests ran in a real Render environment.

## Part 2 — one complete live run verified; availability remains intermittent

Task `8cea325c-b8a5-4217-b207-e3a064999c2c`, trace
`424a72c8-4dd4-4eb8-b6b0-f7965a33d439`: live CrewAI/Gemini generated `health.py`
and `test_health.py`; the remote pytest result was **1 passed**, followed by
DevOps. `simulation=false`, `live_crewai=true`, `live_gemini=true`, and
`host_execution=false`. Runtime Python was 3.11.2. Total HTTP request time was
approximately 143 seconds. Twelve available Gemini canonical records were
checked against their raw event IDs, trace IDs, and original payload strings.

The exact **Create a small portfolio** request has also failed. One attempt
generated Flask code before Flask was bundled, and the subsequent repair hit a
Google 503. A later attempt completed Requirements, Planning, and Architecture,
then Google returned 503 before Development. These are retained as failed runs;
they are not relabeled as successes.

Final deployed application revision: `2ac429b`. Part 1 was rerun successfully
on that release as task `b126b40e-d609-4dde-ad62-f3029792f864`, confirming the
hosted runner can install the expanded offline package bundle and execute tests.
The final exact portfolio request was task
`dde50dc7-8b4a-41db-b1a5-0085d9d52eb7`, trace
`a919494a-3b51-4b4d-b141-4dfe345870b0`. It completed Requirements, Planning, and
Architecture, then stopped with Gemini HTTP 503 before Development after bounded
retries. The request took approximately 39 seconds. The portfolio workflow is
therefore **not verified successful end to end** on the final release, despite
the separately verified runtime repair and earlier complete live health task.

## Corrections and their evidence

- Bounded retries for temporary provider responses; authentication errors are
  not retried. Provider errors now show a safe HTTP status without credentials.
- Explicit agent output rules keep the test-command allowlist intact.
- A pinned Flask 3.1.3 bundle addresses the observed missing-package error.
  A separate fixed portfolio fixture passed **3 real remote tests**: page route,
  health route, and absence of application credentials with an unprivileged UID.
  This fixture is runtime evidence, not a claim that Gemini produced that fixture.
- The UI exposes intake rejection reasons, prevents overlapping submissions,
  hides the previous result during a new request, disables forced failures for
  Part 2, labels the shortcuts as Part 1, and shows pending for zero trace events.
- Latest full local suite before the Flask bundle: **134 passed, 1 skipped**.
  The skip requires a local Docker engine. After the Flask bundle change,
  **20 focused runtime/provider/workflow tests passed**, with lint and types clean.
- Known private API keys and deployment passwords were absent from tracked
  files; `.env` is not tracked.

## Practical limits

Google model availability cannot be guaranteed by changing the hosting provider.
Additional probes also saw a 503 on Gemini 3.5 Flash and a timeout on Gemini 3.8
Flash. The deployed model remains explicitly `gemini-3.5-flash-lite`.

Historical normalization failures remain in raw storage and can be retried.
Not all historical events are normalized; do not report 100% observability
success. Retention deletion remains disabled. Generated projects are reviewable
artifacts and test results; this system does not automatically publish each
generated website to its own URL. Arbitrary dependency installation and host
execution remain disabled.

No AWS account or local Docker Desktop is needed to use the hosted app. Render
still builds the service from a Dockerfile and provides remote isolated test
environments; this is not a claim that the hosting platform uses no containers.

## Submission reproducibility check — November 23, 2026

Cloned `deploy/render-full-stack` directly from GitHub into a new directory at
commit `d24530c`, without copying the developer environment or any credentials.
`uv sync --locked --python 3.12` installed the application successfully using
Python 3.12.2. The fresh clone passed **134 tests, 1 skipped**; the skip was the
real Docker smoke test because the local engine was stopped. Ruff checks and
format checks passed. Type-checking initially identified a missing optional
Render client, so the README now explicitly installs `--all-extras` for checks.
After that install, mypy passed for all 68 source files.

An actual local HTTP server started from that clone with safe `.env.example`
defaults. Five HTTP scenarios returned the expected outcomes: first-attempt pass,
two failures then a third-attempt pass, exhausted three-attempt budget without
DevOps, infeasible dataset routing, and blank-prompt rejection (HTTP 422). The
first successful task had 20 correlated events with canonical records. These
were **simulation runs**, not a new live Gemini or local Docker verification.

The HTTP-check assertions passed. Its temporary-directory cleanup briefly
encountered a Windows file lock after server shutdown; no application code or
user data was changed by that cleanup failure. The server process subsequently
exited. No additional live model request was made during the submission check.

The source comparison in `SOURCE_PROVENANCE.md` verifies that all 127 downloaded
Drive project files are represented in the GitHub integration branch. The root
README now replaces contradictory milestone notes with current clone, dependency,
environment, local Part 1/Part 2, and optional service-stack instructions.
