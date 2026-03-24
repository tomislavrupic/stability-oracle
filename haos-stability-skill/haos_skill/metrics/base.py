from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Dict, Iterable

from ..state_spec import State


class StabilityMetric(ABC):
    """
    Deterministic structural metric.

    Implementations must be:
    - read-only with respect to inputs
    - reproducible
    - bounded to [0, 1]
    """

    name: str

    @abstractmethod
    def compute(self, before: State, after: State) -> float:
        raise NotImplementedError


class MetricRegistry:
    """
    Pluggable metric container for `(before, after)` state pairs.
    """

    def __init__(self, metrics: Iterable[StabilityMetric] = ()) -> None:
        self._metrics: Dict[str, StabilityMetric] = {}
        for metric in metrics:
            self.register(metric)

    def register(self, metric: StabilityMetric) -> None:
        if not getattr(metric, "name", "").strip():
            raise ValueError("metric.name must be a non-empty string")
        self._metrics[metric.name] = metric

    def compute_all(self, before: State, after: State) -> Dict[str, float]:
        return {
            name: _coerce_metric_value(name, metric.compute(before, after))
            for name, metric in self._metrics.items()
        }

    def names(self) -> tuple[str, ...]:
        return tuple(self._metrics)


def _coerce_metric_value(name: str, value: float) -> float:
    numeric = round(float(value), 4)
    if not 0.0 <= numeric <= 1.0:
        raise ValueError("metric %s returned %s, expected a value in [0, 1]" % (name, value))
    return numeric
