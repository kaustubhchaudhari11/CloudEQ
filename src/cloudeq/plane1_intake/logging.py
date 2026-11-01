"""Structured logging with correlation ids. Messages do not include secrets."""

import logging


class _CorrelationFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        if not hasattr(record, "trace_id"):
            record.trace_id = "-"
        if not hasattr(record, "task_id"):
            record.task_id = "-"
        if not hasattr(record, "status"):
            record.status = "-"
        return True


def configure_logging(level: str) -> None:
    named = getattr(logging, level.upper(), None)
    if not isinstance(named, int):
        named = logging.INFO
    handler = logging.StreamHandler()
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s trace_id=%(trace_id)s "
            "task_id=%(task_id)s status=%(status)s %(message)s"
        )
    )
    handler.addFilter(_CorrelationFilter())
    logger = logging.getLogger("cloudeq")
    logger.handlers.clear()
    logger.addHandler(handler)
    logger.setLevel(named)
    logger.propagate = False
