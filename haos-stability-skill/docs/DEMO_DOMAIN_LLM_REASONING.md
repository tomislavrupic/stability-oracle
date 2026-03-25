# Demo Domain: LLM Reasoning

## Why This Domain

The first non-HAOS demo domain should be LLM reasoning trace stability.

This is the right first extension because it is:

- close to the current direction of the project
- easy to explain publicly
- useful for agents and tool-calling systems
- sequential by nature
- free of physics claims

## Domain Framing

Each reasoning step becomes a telemetry frame.

Entity:

- one model solving one task

The Oracle still does not need to know what the steps mean. It only analyzes how the trajectory evolves.

## Candidate Frame Features

`TelemetryFrame.state_vector` can include deterministic numeric features such as:

- step length
- embedding projection
- contradiction score
- self-reference count
- tool-call count
- answer-delta magnitude

These semantics live in the adapter, not in the Oracle core.

## Minimal Demo Question

Can the Oracle distinguish between:

- coherent successful reasoning
- weakly perturbed or drifting reasoning
- fragmented or collapsing reasoning

## Demo Scenarios

1. Baseline

Smooth step-to-step progression toward an answer.

2. Perturbed

Mild contradiction insertion or dependency disruption.

3. Fragmented

Strong inconsistency, abrupt jumps, or step deletion.

## Observable Output

For each trace, the demo should emit:

- `structural_retention`
- `temporal_consistency`
- `causal_deformation`
- `geometric_integrity`
- final classification

## Minimal Success Criterion

The Oracle should separate the three trace classes with visibly ordered scores:

`baseline > perturbed > fragmented`

and produce:

- `stable`
- `marginal`
- `unstable`

without domain-specific tuning beyond the adapter.

## Why This Matters

This makes the Oracle immediately legible as a reasoning stability checker.

That is directly useful for:

- agent loops
- prompt-chain diagnosis
- tool-use monitoring
- self-repair triggers
