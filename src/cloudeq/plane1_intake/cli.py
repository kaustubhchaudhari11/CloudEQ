"""Command-line intake. Prints the same task result as the API."""

import argparse
import json
from typing import Any

from cloudeq.plane1_intake.logging import configure_logging
from cloudeq.plane1_intake.service import IntakeService
from cloudeq.plane1_intake.settings import load_settings
from cloudeq.shared.contracts.models import SubmissionSource, TaskStatus, TaskSubmission


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="cloudeq-intake",
        description="Submit a FORGE SPAN prompt. A handed-off task has not been executed.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)
    submit = subparsers.add_parser("submit", help="Validate, route, and hand off one prompt")
    submit.add_argument("--prompt", required=True)
    submit.add_argument(
        "--dataset",
        default=None,
        help="Named dataset reference. Intake refuses it until a catalog exists.",
    )
    args = parser.parse_args(argv)
    if args.command != "submit":
        return 1
    settings = load_settings()
    configure_logging(settings.cloudeq_log_level)
    service = IntakeService.from_settings(settings)
    external: dict[str, Any] | None = None
    dataset = args.dataset
    if isinstance(dataset, str):
        external = {"dataset": dataset}
    result = service.submit(
        TaskSubmission(source=SubmissionSource.CLI, prompt=str(args.prompt), external_ref=external),
        expected_source=SubmissionSource.CLI,
    )
    print(json.dumps(result.model_dump(mode="json"), indent=2))
    if result.status is TaskStatus.REJECTED:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
