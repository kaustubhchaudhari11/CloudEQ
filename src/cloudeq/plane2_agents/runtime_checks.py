"""Validate runtime results without trusting agent text."""

from cloudeq.shared.contracts.models import ExecutionResult, HandoffRequest, RuntimeOperation


def runtime_problem(
    result: ExecutionResult,
    *,
    handoff: HandoffRequest,
    operation: RuntimeOperation,
    expect_simulation: bool,
) -> str | None:
    if result.host_execution:
        return "Runtime reported host execution. Generated code must stay off the host."
    if result.task_id != handoff.task_id or result.trace_id != handoff.trace_id:
        return "Runtime returned a mismatched task or trace id."
    if result.operation is not operation:
        return "Runtime returned a different operation."
    if result.timed_out:
        return "Runtime timed out."
    if result.simulation is not expect_simulation:
        if expect_simulation:
            return "Offline mode cannot accept a non-simulated runtime result."
        return "A simulated runtime result cannot count as container execution."
    if operation is RuntimeOperation.WRITE_FILE:
        if result.exit_code != 0:
            return "Runtime failed to write the developer artifacts."
        if result.passed is not None:
            return "A file write cannot report a test pass."
        return None
    if operation is RuntimeOperation.RUN_TESTS:
        if result.passed is None:
            return "Runtime did not return a test pass or fail."
        if result.passed and result.exit_code != 0:
            return "A passing test result cannot have a nonzero exit code."
        if not result.passed and result.exit_code == 0:
            return "A failing test result cannot have a zero exit code."
        return None
    return "Unsupported runtime operation."
