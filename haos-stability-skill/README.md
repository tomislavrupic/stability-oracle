# haos-stability-skill

`haos-stability-skill` is a standalone application-layer package that exposes HAOS-IIP structural-stability evaluation as an agent-callable skill.

This repository does not contain scientific logic. It treats HAOS-IIP as an external dependency and talks to it through a bounded CLI adapter.

![Stability Oracle Evaluation Layer Overview](../Images/Stability%20Oracle%20Evaluation%20Layer%20Overview.png)

Overview assets:
- [Evaluation Layer Diagram](../Images/Stability%20Oracle%20Evaluation%20Layer%20Overview.png)
- [Overview PDF](../Images/Stability_Oracle.pdf)
- [Numbered Documentation Paper](../Images/01%20Stability%20Oracle%20Documentation%20Paper.pdf)
- [Oracle Engine v2 And Routing Paper](../Images/02%20Oracle%20Engine%20v2%20and%20Deterministic%20Routing%20Paper.pdf)
- [Telemetry Layer And HAOS Parity Bridge Paper](../Images/03%20Telemetry%20Layer%20And%20HAOS%20Parity%20Bridge%20Paper.pdf)
- [LLM Reasoning Telemetry Demo Paper](../Images/04%20LLM%20Reasoning%20Telemetry%20Demo%20Paper.pdf)
- [Oracle Paradigm Reference](../Images/The_Oracle_Paradigm.pdf)

For the conceptual framing and next decoupling direction of the project, see:

- [docs/WHAT_IS_STABILITY_ORACLE.md](./docs/WHAT_IS_STABILITY_ORACLE.md)
- [docs/ARCHITECTURE_V2.md](./docs/ARCHITECTURE_V2.md)
- [docs/METRIC_PLUGIN_CONTRACT.md](./docs/METRIC_PLUGIN_CONTRACT.md)
- [stability_oracle_demo/docs/DEMO_DOMAIN_LLM_REASONING.md](../stability_oracle_demo/docs/DEMO_DOMAIN_LLM_REASONING.md)
- [stability_oracle_demo/DEMO_V1_FROZEN.md](../stability_oracle_demo/DEMO_V1_FROZEN.md)

## Architecture

- agent layer: your planner or tool-calling runtime
- tool interface layer: JSON schema and CLI
- skill logic layer: classification, summaries, bounded output
- adapter layer: calls the external HAOS oracle CLI
- external dependency: HAOS research/demo/oracle package

## Design Guarantees

- read-only with respect to external HAOS code
- deterministic at the skill layer
- no filesystem writes by default
- hard timeout enforcement
- fail-closed error handling
- optional in-memory deterministic cache

## Install

```bash
pip install -e .
```

## External Oracle Contract

By default the adapter calls:

```bash
haos_iip.demo stability --json
```

Input delivery rules:

- if the configured command contains `{state_json}`, the canonical JSON payload is substituted into that token
- else if the configured command contains `--state-json`, the canonical JSON payload is appended as the final argument
- otherwise the canonical JSON payload is sent to stdin

Override the command with `HAOS_ORACLE_COMMAND` when needed:

```bash
export HAOS_ORACLE_COMMAND="haos_iip.demo stability --json"
```

## CLI

Evaluate a single state payload:

```bash
haos-skill evaluate state.json
```

Scan a batch:

```bash
haos-skill scan grid.json
```

Both commands emit JSON only.

## Python API

```python
from haos_skill import State, evaluate_structure, scan_structure

state_spec = State(nodes=(1, 2), edges=((1, 2),))
report = evaluate_structure(state_spec.to_dict())
stability_map = scan_structure({"cases": [{"case_id": "baseline", "state_spec": state_spec.to_dict()}]})
```

## Micro Demo

Run the deterministic agent-loop demo from the package root:

```bash
python3 -m examples.agent_loop_demo
```

It walks a tiny proposal loop where candidate graph edits are scored by the oracle policy, weak moves are rejected, and the accepted trajectory converges toward a more redundant corridor.

Run the deterministic router demo:

```bash
python3 -m examples.router_demo
```

It shows one `LOGICAL` execution path plus bounded stub responses for `PHYSICAL`, `FOUNDATIONAL`, and `UNKNOWN`.

## Invariant Core

The invariant oracle contract now lives in [haos_skill/state_spec.py](./haos_skill/state_spec.py):

- `State`: minimal structural state
- `Perturbation`: structural disturbance description
- `StabilityMetrics`: bounded oracle metric bundle
- `OracleResult`: minimal typed oracle return object

This file is intentionally algorithm-free. It defines the language the oracle speaks.

## Metric Interface

The pluggable metric layer now lives under [haos_skill/metrics](./haos_skill/metrics):

- [base.py](./haos_skill/metrics/base.py): `StabilityMetric` and `MetricRegistry`
- `StructuralRetentionMetric`
- `TemporalConsistencyMetric`
- `CausalDeformationMetric`
- `GeometricIntegrityMetric`

Each metric is deterministic, side-effect free, and operates only on `(before: State, after: State)`.

## Classification Policy

The deterministic policy layer now lives under [haos_skill/oracle](./haos_skill/oracle):

- [classifier.py](./haos_skill/oracle/classifier.py): `PolicyConfig` and `StabilityClassifier`

The default policy is `v1_floor_mean_band`:

- normalize causal deformation into a direct stability signal
- apply a survivability floor
- compute coherence as an unweighted mean
- compute spread as max-minus-min
- classify into `stable`, `marginal`, or `unstable`
- emit `confidence`, `coherence_score`, and `policy_version`

`evaluate_structure(...)` returns:

```json
{
  "classification": "stable",
  "structural_retention": 0.94,
  "temporal_consistency": 0.98,
  "causal_deformation": 0.12,
  "geometric_integrity": 0.96,
  "confidence": 0.82,
  "coherence_score": 0.94,
  "metric_vector": {
    "structural_retention": 0.94,
    "temporal_consistency": 0.98,
    "causal_deformation": 0.12,
    "geometric_integrity": 0.96
  },
  "normalized_vector": {
    "structural_retention": 0.94,
    "temporal_consistency": 0.98,
    "causal_stability": 0.88,
    "geometric_integrity": 0.96
  },
  "policy_version": "v1_floor_mean_band",
  "summary": "Structure is stable with high retention and low deformation."
}
```

## Oracle Engine v2

Oracle Engine v2 adds a reusable local decision layer on top of the existing contracts:

- transition evaluation: `engine.evaluate_transition(before, after)`
- perturbation evaluation: `engine.evaluate(before, perturbation)`
- batch scanning: `engine.scan(before, perturbations)`
- deterministic trace payload: node and edge counts, normalized vector, coherence, spread, floor trigger, and policy version

Build it directly with:

```python
from haos_skill.oracle.engine import build_default_engine

engine = build_default_engine()
```

For bounded rule-based language, use:

```python
from haos_skill import explain_result
```

## Telemetry Layer v0

The telemetry layer is a new parallel ingestion path, not a rewrite of the current logical core.

It adds:

- `TelemetryFrame`
- `TelemetrySequence`
- `HaosTelemetryAdapter`
- `TemporalNormalizer`
- `StateGeometryEncoder`
- `telemetry_to_state_transition(...)`

The current `State` plus `OracleEngine` path remains the stable execution kernel.

The intended migration rule is:

- prove HAOS parity first
- then widen to other domains

The first intended non-HAOS demo after parity is LLM reasoning trace stability.

## Oracle Routing Layer

The routing layer adds a deterministic selector for which oracle domain should evaluate a candidate next:

- current implemented route: `LOGICAL`
- future route label: `PHYSICAL`
- future route label: `FOUNDATIONAL`
- bounded stubs are returned for unimplemented routes instead of crashing

Build it directly with:

```python
from haos_skill.routing.router import build_default_router

router = build_default_router()
```

Example route decision:

```python
from haos_skill import RoutingContext, build_default_router

router = build_default_router()
decision = router.decide(
    RoutingContext(requires_structural_stability=True)
)
print(decision.to_dict())
```

```json
{
  "selected_route": "LOGICAL",
  "confidence": 1.0,
  "rationale": "requires_structural_stability",
  "policy_version": "routing_v1_explicit_priority"
}
```

Example dispatch result:

```python
from haos_skill import Perturbation, RoutingContext, build_default_router

router = build_default_router()
result = router.dispatch(
    RoutingContext(requires_structural_stability=True),
    before={
        "nodes": [1, 2, 3, 4],
        "edges": [[1, 2], [2, 3], [3, 4]],
        "timestamps": {"1": 0.0, "2": 1.0, "3": 2.0, "4": 3.0}
    },
    perturbation=Perturbation(cluster_split=True),
)
print(result.to_dict())
```

The dispatch payload includes the route decision and, for `LOGICAL`, the traced engine result.

## Foundational Contract

The repository now also defines the future FOUNDATIONAL language layer without implementing the engine itself.

The contract lives in [haos_skill/foundational/contract.py](./haos_skill/foundational/contract.py) and defines:

- `FoundationalCheck`: what a foundational route is allowed to inspect
- `FoundationalSignals`: bounded signal bundle
- `FoundationalResult`: typed future result contract

The current foundational dimensions are:

- `contradiction_risk`
- `composability_violation`
- `non_recoverable_identity_collapse`
- `invalid_abstraction_crossing`

## Agent Integration

OpenClaw-style:

```python
from haos_skill import evaluate_structure

agent.register_skill(evaluate_structure)
```

Hermes-style:

```python
from haos_skill import evaluate_structure, load_schema

tool_registry.add(load_schema()["tools"][0], evaluate_structure)
```

## Notes

- caching is in-memory only and must be enabled explicitly
- this package never edits the external HAOS dependency
- if the external oracle returns an unrecognized payload, the skill raises a controlled error instead of guessing
