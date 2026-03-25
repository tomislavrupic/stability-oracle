# LLM Reasoning Telemetry Demo

This demo shows that the oracle can detect structural reasoning drift using only trajectory geometry.

This demo tests whether the Stability Oracle can separate stepwise reasoning traces into `stable`, `marginal`, and `unstable` classes using deterministic telemetry only.

It does not test truth, intelligence, cognition, or model internals. It is a structural telemetry classification demo.

## What The Demo Measures

Each reasoning step is converted into one fixed-width telemetry frame. The vector has exactly eight dimensions, in this order:

1. `step_length_norm`
2. `confidence_proxy`
3. `novelty_vs_prev`
4. `self_overlap`
5. `contradiction_score`
6. `numeric_consistency_score`
7. `tool_dependency_score`
8. `terminality_score`

All values are bounded to `[0,1]` and filled deterministically.

## Oracle Role

The demo does not modify Oracle internals.

Instead it:

1. converts reasoning text into telemetry vectors
2. builds a canonical reasoning state from the trace
3. derives an observed structural transition from telemetry continuity rules
4. sends that transition into the existing Stability Oracle engine

The Oracle then returns the standard structural metrics and a bounded class verdict.

## What The Dataset Contains

The dataset contains twelve tasks:

- four coherent traces with correct outcomes
- four drifted traces with incorrect outcomes
- four broken traces with broken outcomes

The task mix is deliberately small and includes both arithmetic and logical reasoning.

## Reproducibility

Run the demo from the repository root:

```bash
MPLCONFIGDIR=/tmp/stability_oracle_demo_mpl \
PYTHONPATH=/Volumes/Samsung\ T5/2026/HAOS/stability-oracle/haos-stability-skill:/Volumes/Samsung\ T5/2026/HAOS/stability-oracle \
python3 -m stability_oracle_demo.pipeline.demo_runner
```

Outputs:

- `stability_oracle_demo/output/results.csv`
- `stability_oracle_demo/output/trace_explanations.json`
- `stability_oracle_demo/output/metrics_plot.png`

The demo is deterministic. It uses no external APIs, no adaptive learning, and no hidden state.
