# Metric Plugin Contract

## Purpose

A metric plugin maps one `TrajectoryWindow` to one normalized scalar in `[0, 1]`.

Higher should mean more stable, unless the metric is explicitly declared as inverse polarity and normalized by the engine before classification.

## Canonical Contract

```python
from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class MetricSpec:
    name: str
    version: str
    polarity: str
    min_window_size: int
    deterministic: bool = True


class MetricPlugin(ABC):
    spec: MetricSpec

    @abstractmethod
    def compute(self, window: TrajectoryWindow) -> float:
        """
        Returns a finite scalar in [0,1].
        Must be deterministic and side-effect free.
        """
        raise NotImplementedError
```

## Required Rules

Every metric plugin must:

- accept only `TrajectoryWindow`
- return a finite scalar in `[0,1]`
- be deterministic
- be side-effect free
- never mutate input frames
- never import domain-specific adapters
- never assume semantic meaning of vector axes
- never depend on absolute dimensional labels
- document failure conditions explicitly

## Allowed Dependencies

A metric may depend on:

- window geometry
- temporal spacing
- relative vector change
- local curvature
- divergence or convergence
- return-to-baseline structure

## Forbidden Dependencies

A metric may not depend on:

- “this dimension means price”
- “this node means memory”
- “this signal means reward”
- any domain-specific interpretation

## Engine Normalization Rule

If `polarity == "inverse"`, the engine converts:

```python
stable_score = 1.0 - raw_score
```

before classification.

## Validation Rule

Before `compute(...)` runs:

- all vectors must be finite
- shape must remain consistent within the window
- `window_size >= min_window_size`

Otherwise:

- raise `InvalidTelemetry` or `MetricInputError`

## Recommended Initial Metric Set

- `structural_retention`
- `temporal_consistency`
- `causal_deformation` with inverse polarity
- `geometric_integrity`

## Design Intent

The plugin system should let the Oracle evaluate recoverability geometry across domains without importing upstream semantics into the core.
