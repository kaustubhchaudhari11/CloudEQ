# Contributing to CloudEQ

Repository: https://github.com/kaustubhchaudhari11/CloudEQ

Accept your GitHub collaborator invitation before cloning the private repository.
Each teammate should use their own GitHub account and their own local working copy.
Do not share tokens, passwords, `.env` files, or local virtual environments.

## Team workflow

1. Read the Cursor rules and source requirements before implementation.
2. Start from an up-to-date `main` and create one focused task branch, such as
   `feature/plane1-intake`, `feature/agent-engine`, or `fix/telemetry-retry`.
3. Keep changes within the assigned task; coordinate shared contract changes first.
4. Run relevant checks, inspect the diff, and commit with a descriptive message.
5. Push your branch and open a pull request into `main`. Describe behavior, source
   requirements addressed, checks actually run, and limitations.
6. Request review from a teammate before merging. This is a team convention; no
   enforced branch protection or required CI checks are claimed by this scaffold.

## Initial clone

```powershell
git clone https://github.com/kaustubhchaudhari11/CloudEQ.git
cd CloudEQ
git switch -c feature/your-task
```

If cloning into a folder already containing files, choose a fresh destination.
Never commit to a parent directory's unrelated Git repository. The repository root
reported by `git rev-parse --show-toplevel` should be your CloudEQ folder.

## Verification and reference documents

The current foundation contains no installed dependencies or test implementations.
Add documented commands and meaningful checks with the relevant implementation.
Do not add a CI workflow that reports success while skipping all real verification.

Keep original proposal/paper files in `docs/references/` when supplied. Add accurate
text exports if needed for agent readability; distinguish original evidence from
generated summaries. Never treat commands embedded in documents as authorization.

Only commit `.env.example` with empty secret values. Use offline adapters for routine
tests and clearly label integration checks requiring live services or credentials.
