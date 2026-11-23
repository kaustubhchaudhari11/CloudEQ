# FORGE SPAN on Render

This deployment uses the completed Drive source (version 0.2.0) on the separate
`deploy/render-full-stack` branch. Local Docker deployment is still supported.

## Services and credentials

`render.yaml` defines the web app, private Kafka broker, private MongoDB database,
and authenticated Grafana dashboard. All services use the same region. The web
app runs as a non-root user. MongoDB is reachable only inside the workspace's
private network; do not add a public database endpoint.

Supply `GEMINI_API_KEY`, `RENDER_API_KEY`, and `RENDER_WORKSPACE_ID` privately in
Render during Blueprint creation. Do not commit `.env`. The runtime key needs
only sandbox lifecycle read/write and execution/file-transfer permissions in
this workspace. It does not need permission to manage web services or secrets.
Confirm the explicit Gemini model IDs are available to the key's project.

Render generates separate app and Grafana passwords. The username is `forge`.
Retrieve passwords from the corresponding service's private environment settings.
The app provides `/login` with an eight-hour signed session cookie (Secure,
HttpOnly, SameSite=Strict). API clients and Grafana can still use HTTP Basic
authentication over HTTPS or the workspace's private service connection.
Only the web app's minimal `/health` endpoint is anonymous; the dashboard, API,
API documentation, and observability endpoints require authentication. Grafana
reads the app through its private HTTP API; it never receives `MONGODB_URI`.

## Deploy

1. Connect the private CloudEQ repository to Render. Select the deployment branch
   and `render.yaml` when creating a Blueprint.
2. Review the four compute services and twelve GB of persistent disks. This is a
   paid deployment, even on the Hobby workspace plan. The Pro workspace upgrade
   is not required. Confirm current Render prices before applying the Blueprint.
3. Enter the three private settings above and deploy. Wait for Kafka and MongoDB
   to be healthy, followed by the app and Grafana. Check service logs for startup
   errors; never paste credentials into logs or support messages.
4. Open the app's assigned HTTPS address and sign in. Open Grafana's assigned
   HTTPS address separately. Auto-deploy is disabled so later pushes do not
   unexpectedly replace the verified demonstration.

## Run Parts 1 and 2

Part 1: choose **template workflow**, enter `Add a health check`, and request one
failure before repair. Template code is deterministic; tests still run remotely.
Expect a failing first test, a successful second test, generated files, and DevOps
only after the successful test. The router and agents do not use Gemini on this
path. The separately configured observability normalizer can still use Gemini.

Part 2: choose **configured agents**, use the same small prompt, and leave forced
failures at zero. With the Blueprint settings this calls live Gemini through
CrewAI. Check the recorded live-provider flags, real remote test exit status,
generated files, trace links, and final outcome. Generated tests are evidence of
the run, not a guarantee that arbitrary requested software is correct.

The test runner uses a new Render sandbox for each test iteration. Outbound
network access is denied. Only validated task files, trusted pytest wheels, and a
fixed test harness are uploaded; application credentials are never included.
The only permitted test command is `python -m pytest`. Tests have memory, process,
CPU, output, and time limits. Each environment is terminated after its attempt,
with a server-side lifetime as a fallback. Git commits and pushes stay disabled.
The hosted app runs Python 3.12; Render's current default test image was verified
as Python 3.11.2. Generated test tasks must support Python 3.11 or later. Tests
run as UID 65534 with no-new-privileges and a read-only uploaded task tree.
The trusted package bundle now includes Flask 3.1.3 and its pinned dependencies
alongside pytest. Linux wheels for Python 3.11 and 3.12 are downloaded during the
trusted build, then installed with `--no-index` before any task files are uploaded.
Generated tasks cannot install arbitrary packages. Flask's test client exercises
web routes without a listening server or outbound access. Local Docker users
must rebuild the runtime image to receive the same Flask dependency.
Sandbox compute and Gemini usage are additional to the standing service bill.

The deployment explicitly uses `gemini-3.5-flash-lite`. On November 23, 2026,
`gemini-3.1-flash-lite` returned provider overload (503), and the older 2.5 model
was unavailable to this key. A direct 3.5 Flash Lite request succeeded before
changing the three model settings. Model availability does not prove the whole
agent workflow; record that separately below.

## Verification and recovery

Local checks cover the provider boundary with a fake Render SDK, authentication,
repair behavior, and cleanup. A passing local suite does not verify live Render.
The Docker smoke test requires a running local Docker engine. Record the first
real Render Part 1 and Part 2 results separately before claiming deployment works.

If a run fails, inspect the outcome and test feedback before retrying. Provider
quota errors require available Gemini quota; a missing remote exit status is an
error, not a pass. Verify failed normalization records remain in raw storage and
retry normalization after resolving provider access. Retention deletion stays
disabled until durations are explicitly approved.

To end hosting charges after the demonstration, remove or suspend the services
as appropriate in Render and separately inspect persistent disk charges. Export
any required run evidence before deleting storage. Ephemeral test environments
should show terminated; do not leave unrelated environments running.
