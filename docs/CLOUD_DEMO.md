# FORGE SPAN cloud demonstration

Website: https://forge-span.onrender.com

Observability: https://forge-span-grafana.onrender.com/d/forge-span-overview

Both use username `forge` with separate private passwords. The project owner has
the login instructions outside this repository. Passwords and API keys must not
appear in the submitted manual. If an old browser authentication popup remains,
cancel it and reload the website to use the new sign-in form.

## Part 1: controlled repair demonstration

1. Sign in and choose **Part 1: template workflow and repair demonstration**.
2. Enter **Add a health check** and set failing iterations to **1**.
3. Select **Run through all planes** and wait for the result.
4. Open the run detail. The first test fails; the second passes. Inspect the
   generated files and runtime test output. DevOps is allowed only after a pass.
5. Inspect trace events and the Grafana dashboard. The template code is
   deterministic; its tests genuinely run in a remote isolated environment.

## Part 2: live Gemini agents

1. Choose **Part 2: configured agents** and set failing iterations to **0**.
2. Enter a small Python task, for example **Add a health check endpoint**.
3. Select **Run through all planes** once. Live work can take several minutes.
4. Inspect Requirements, Planning, Architecture, Development, Testing, and
   DevOps. Verify live Gemini/CrewAI flags and actual pytest output. Model text
   alone is never accepted as a successful test result.
5. Review the generated source and tests. The hosted test environment currently
   supports Python 3.11 standard-library code and pytest; it cannot install
   arbitrary dependencies or make outbound network requests.

For a narrowly specified example, use: **Create health.py with a health_check()
function returning {"status":"ok"}, and test_health.py with pytest tests.**

The hosted runtime uses Render's isolated environments. Local Docker Desktop is
not required to use this website. The original local Docker setup remains an
independent deployment option.

## Additional scenarios

- **Validation:** select Blank (rejected) or submit an empty prompt. Expect a
  rejected result and no generated-code execution.
- **Repair budget:** choose Part 1 and set failing iterations to 3. Expect
  `failed_budget_exhausted` and no DevOps success.
- **Schema changes:** use Rich event and Drifted fields under Plane 4. Inspect
  raw records, canonical records, and trace links. Malformed events retain their
  raw evidence even when normalization fails.

## Recovery and limits

Temporary Google 429/5xx responses receive up to three provider attempts with
backoff. Persistent provider failures remain errors; credits do not guarantee
model availability. Retry a small task after the provider recovers. Do not
submit repeated copies while a run is still processing.

An unsupported test command is rejected before execution. Agent instructions
now explicitly request `python -m pytest`; the allowlist is still enforced.
Use the run's reason to distinguish provider, validation, and test failures.

Historical failed runs remain visible. The **Retry failed** button retries
normalization with the configured Gemini normalizer; it does not rerun agents.
Raw and canonical data are separate MongoDB collections. Retention deletion
remains disabled. Grafana reads a private authenticated HTTP API, not MongoDB.

## Hosting period and cost

The approved configuration is a Hobby workspace with four paid services:
app $25/month, Kafka $25/month, MongoDB $7/month, Grafana $7/month, plus twelve GB
of disks at $3/month total. The standing equivalent is $67/month, approximately
$2.23/day for November, plus isolated-test usage, Gemini usage, and applicable
taxes. No Pro workspace upgrade is required.

Hosting is intended through November 26 or 27, 2026. There is no automatic
shutdown scheduled. After the demonstration, export required evidence, then
suspend/remove the services as appropriate and inspect remaining disk charges
in Render. Deleting disks destroys stored run history and requires a deliberate
decision by the project owner.
