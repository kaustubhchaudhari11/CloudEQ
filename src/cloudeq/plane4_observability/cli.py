"""``cloudeq-observability``: worker and maintenance commands for Plane 4."""

import argparse
import json

from cloudeq.plane4_observability.factory import build_observability
from cloudeq.plane4_observability.normalizer import OfflineNormalizer
from cloudeq.shared.dotenv import load_dotenv


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="cloudeq-observability")
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser("stats", help="Print pipeline metrics from the configured store")
    retry = sub.add_parser("retry", help="Re-normalize events whose normalization failed")
    retry.add_argument("--offline", action="store_true", help="Use the offline normalizer")
    sub.add_parser("consume", help="Run the Kafka consumer (CLOUDEQ_TELEMETRY_BUS=kafka)")
    sub.add_parser("retention", help="Apply retention. Does nothing while retention is unset.")
    args = parser.parse_args(argv)
    load_dotenv()

    if args.command == "consume":
        stack = build_observability(consume=False)
        if stack.bus.name != "kafka":
            print("CLOUDEQ_TELEMETRY_BUS is not kafka; the in-process bus needs no worker.")
            return 1
        stack.bus.subscribe(stack.pipeline.ingest)
        print("Consuming telemetry from Kafka. Ctrl+C to stop.")
        consume = getattr(stack.bus, "consume_forever", None)
        if consume is not None:
            try:
                consume()
            except KeyboardInterrupt:
                pass
        stack.close()
        return 0

    stack = build_observability(consume=False)
    if args.command == "stats":
        print(json.dumps(stack.pipeline.metrics(), indent=2))
    elif args.command == "retry":
        chosen = OfflineNormalizer() if args.offline else None
        print(json.dumps(stack.pipeline.retry_failed(normalizer=chosen), indent=2))
    elif args.command == "retention":
        print(json.dumps(stack.pipeline.apply_retention(), indent=2))
    stack.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
