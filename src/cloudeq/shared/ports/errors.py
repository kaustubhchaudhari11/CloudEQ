"""Errors raised by adapters implementing shared ports."""


class RuntimeExecutionError(Exception):
    """A runtime operation failed before a trustworthy result was available."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason
