# Architecture V2

## Purpose

Stability Oracle v2 is a domain-agnostic trajectory stability engine. It evaluates whether structured behavior remains coherent under change, using only numeric telemetry and deterministic metrics.

## Core Principle

The engine does not know what a system means. It only sees the geometry of change.

## Layered Architecture

- adapters
  convert domain-specific records into the universal telemetry format
- telemetry core
  validates frames, normalizes time, and builds trajectory windows
- geometry layer
  transforms raw numeric trajectories into comparable geometric representations
- metric layer
  computes deterministic stability metrics over windows
- policy layer
  maps metric vectors to bounded classifications
- output layer
  returns machine-readable assessments and optional human summaries

## Canonical Flow

Domain data

`-> Adapter`

`-> TelemetryFrame[]`

`-> TemporalNormalizer`

`-> TrajectoryWindow[]`

`-> StateGeometryEncoder`

`-> Metric plugins`

`-> Policy classifier`

`-> OracleAssessment`

## Hard Invariants

- core never imports domain code
- metrics never depend on semantic labels
- all outputs are deterministic
- validation fails closed
- policies are versioned
- streaming and batch paths use the same window and metric contracts

## Canonical Data Objects

```python
from dataclasses import dataclass, field


@dataclass
class TelemetryFrame:
    timestamp: float
    entity_id: str | int
    state_vector: list[float]
    metadata: dict = field(default_factory=dict)


@dataclass
class TrajectoryWindow:
    frames: list[TelemetryFrame]
    duration: float
    cadence: float


@dataclass
class OracleAssessment:
    entity_id: str | int
    time_window: tuple[float, float]
    classification: str
    stability_score: float
    confidence: float
    metric_vector: dict[str, float]
    policy_version: str
    summary: str
```

## Public API Direction

```python
oracle = StabilityOracle(profile="default")
result = oracle.assess(telemetry_stream)
```

Optional:

```python
results = oracle.assess_stream(telemetry_stream)
results = oracle.scan(telemetry_stream, perturbation_grid)
```

## Practical Migration Sequence

1. Freeze current Oracle core.
2. Extract HAOS parsing logic into an adapter.
3. Introduce `TelemetryFrame`.
4. Insert the geometry encoder.
5. Convert metrics to plugins.
6. Build one non-HAOS demo.
7. Validate identical behavior on HAOS-shaped input.

## Result

After decoupling, the Oracle becomes a universal trajectory stability instrument.

It is not a physics engine, philosophy layer, or domain model. It is a detector of structural persistence under change.
