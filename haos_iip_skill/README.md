# HAOS-IIP Structural Stability Skill

This module is a thin application-layer wrapper over the existing frozen stability oracle in [`oracle/`](../oracle).

It does not:

- modify research bundles
- launch simulations
- expand telemetry
- write to disk by default

It does:

- validate a `TrajectorySpec`-compatible payload
- call the existing deterministic evaluator
- return a compact, bounded report for agent planning loops

## Public API

```python
from haos_iip_skill import evaluate_structure, scan_structure

report = evaluate_structure(state_spec)
stability_map = scan_structure(
    {
        "cases": [
            {"case_id": "baseline", "state_spec": state_spec},
            {"case_id": "variant", "state_spec": variant_state_spec},
        ]
    }
)
```

`evaluate_structure(state_spec)` returns:

```json
{
  "classification": "stable",
  "structural_retention": 1.0,
  "temporal_consistency": 1.0,
  "causal_deformation": 0.0383,
  "geometric_integrity": 1.0,
  "summary": "Structure is stable with clean propagation and retained invariants."
}
```

## Metric Mapping

The skill reuses the current oracle metrics and only translates them:

- `structural_retention`: persistence retention plus checkpoint coverage
- `temporal_consistency`: normalized ordering score
- `causal_deformation`: bounded exposure/deformation composite
- `geometric_integrity`: normalized reachability/connectivity composite

Classification is mapped directly from the frozen oracle:

- `green -> stable`
- `yellow -> marginal`
- `red -> unstable`

## CLI Wrapper

Pretty JSON:

```bash
haos-iip-skill evaluate --state-file examples/media_pipeline_plan.json
```

Single-line JSON for tool callers:

```bash
haos-iip-skill evaluate \
  --state-file examples/media_pipeline_plan.json \
  --timeout-seconds 2.0 \
  --json-only
```

Batch scan:

```bash
haos-iip-skill scan --grid-json '{
  "cases": [
    {"case_id": "stable", "state_spec": {"plan_id": "stable", "nodes": [], "edges": []}}
  ]
}' --json-only
```

Schema export:

```bash
haos-iip-skill schema --json-only
```

## Example Agent Integration Snippet

```python
from haos_iip_skill import evaluate_structure, load_schema

TOOL_REGISTRY = {
    "haos_iip.evaluate_structure": {
        "schema": load_schema()["tools"][0]["input_schema"],
        "callable": evaluate_structure,
    }
}


def answer_stability_question(state_spec: dict) -> dict:
    return TOOL_REGISTRY["haos_iip.evaluate_structure"]["callable"](state_spec)
```

## Short Demo

```python
from pathlib import Path
import json

from haos_iip_skill import evaluate_structure

state_spec = json.loads(Path("examples/media_pipeline_plan.json").read_text())
print(evaluate_structure(state_spec))
```

Expected result shape:

```json
{
  "classification": "stable",
  "structural_retention": 1.0,
  "temporal_consistency": 1.0,
  "causal_deformation": 0.0383,
  "geometric_integrity": 1.0,
  "summary": "Structure is stable with clean propagation and retained invariants."
}
```
