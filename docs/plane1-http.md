# Plane 1 HTTP contract

FORGE SPAN intake by Cloud EQ. These routes validate and route a prompt.
`handed_off` means the in-memory Plane 2 port accepted the contract.
It does not mean an agent ran, a container started, or a commit was made.
`execution_started` is false for every Plane 1 response.

The API reads process environment variables. When `.env` exists, the API and CLI
load it without overriding variables that are already set. Live Gemini calls stay
off unless `CLOUDEQ_ROUTER_MODE=gemini`, `CLOUDEQ_GEMINI_LIVE_CALLS=true`,
`GEMINI_API_KEY`, and `GEMINI_ROUTER_MODEL` are all set. The model ID is never guessed.

## `GET /health`

```json
{
  "status": "ok",
  "service": "FORGE SPAN",
  "team": "Cloud EQ",
  "plane": "plane1_intake",
  "router_mode": "offline",
  "live_gemini_calls": false,
  "execution_available": false
}
```

## `POST /tasks`

Request:

```json
{
  "source": "api",
  "prompt": "Add a health check",
  "external_ref": {"dataset": "optional-name"}
}
```

`source` must be `api` on this route. `task_id` is rejected if the caller sends it.
`prompt` must contain non-whitespace text. `github_issues` and `jira` are rejected
while those adapters are disabled.

Feasible offline response, HTTP 200:

```json
{
  "status": "handed_off",
  "trace_id": "generated-uuid",
  "task_id": "generated-uuid",
  "source": "api",
  "prompt": "Add a health check",
  "reasons": ["Offline router accepted the prompt."],
  "feasibility": {
    "status": "feasible",
    "dataset_check": "not_applicable",
    "reasons": ["Offline router accepted the prompt."],
    "router": "offline",
    "model_id": ""
  },
  "handoff_accepted": true,
  "execution_started": false
}
```

A named dataset is HTTP 200 with `status` `routed`, feasibility `infeasible`,
and `dataset_check` `failed`. Router errors and timeouts are HTTP 200 with
`status` `routed` and feasibility `error`. Neither case hands off.

Empty prompts, a caller-supplied `task_id`, a non-`api` source, and disabled
ticket sources are HTTP 422 with `status` `rejected`, a `trace_id`, and
`task_id` null.

## `GET /tasks/{task_id}`

Returns the stored result for an accepted task. Unknown ids return HTTP 404.
Rejected requests are not stored.

## CLI

`cloudeq-intake submit --prompt "..."` prints the same JSON fields.
Exit 0 means the command produced `routed` or `handed_off`.
Exit 2 means validation rejected the prompt. Neither exit code means code ran.
