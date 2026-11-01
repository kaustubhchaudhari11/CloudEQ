"""Deterministic feasibility router used when Gemini calls are disabled."""

from collections.abc import Mapping
from typing import Any

from cloudeq.shared.contracts.models import (
    DatasetCheck,
    FeasibilityResult,
    FeasibilityStatus,
    RouterKind,
    RoutingRequest,
)

DATASET_KEYS = frozenset({"dataset", "dataset_id", "dataset_ref"})
NO_CATALOG = "No dataset catalog is configured."


def names_dataset(external_ref: Mapping[str, Any] | None) -> bool:
    if not external_ref:
        return False
    for key, value in external_ref.items():
        if key.casefold() in DATASET_KEYS and value not in (None, "", [], {}):
            return True
    return False


class OfflineRouter:
    """Accepts a non-empty prompt and refuses named datasets until a catalog exists."""

    def evaluate(self, request: RoutingRequest) -> FeasibilityResult:
        if names_dataset(request.external_ref):
            return FeasibilityResult(
                status=FeasibilityStatus.INFEASIBLE,
                dataset_check=DatasetCheck.FAILED,
                reasons=[NO_CATALOG],
                router=RouterKind.OFFLINE,
                model_id="",
            )
        return FeasibilityResult(
            status=FeasibilityStatus.FEASIBLE,
            dataset_check=DatasetCheck.NOT_APPLICABLE,
            reasons=["Offline router accepted the prompt."],
            router=RouterKind.OFFLINE,
            model_id="",
        )
