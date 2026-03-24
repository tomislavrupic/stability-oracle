---
layout: default
title: Stability Oracle
description: Structural Stability Evaluation Layer for HAOS-IIP
permalink: /
---

# Stability Oracle

Structural Stability Evaluation Layer for HAOS-IIP

![Stability Oracle Evaluation Layer Overview](./assets/stability-oracle-evaluation-layer-overview.png)

Stability Oracle is a minimal structural evaluation engine.

It measures whether a system configuration can retain coherent organization under controlled perturbation.

The oracle does not model physics. It does not simulate spacetime. It does not attempt to infer ontology.

It performs one bounded task:

Given a state and a perturbation, determine whether meaningful structure survives.

## Why This Exists

HAOS-IIP established that certain interaction regimes produce recoverable coherence under interaction. Stability Oracle turns that insight into an operational surface that can be used in fast loops, public demos, and agent runtimes.

Instead of speculative interpretation, the project emphasizes:

- measurable stability signals
- deterministic classification
- bounded machine-readable output
- clean separation between research core and application layer

## What It Evaluates

The oracle evaluates structural survival across four invariant dimensions:

- `structural_retention`
- `temporal_consistency`
- `causal_deformation`
- `geometric_integrity`

These metrics are normalized to `[0,1]` and fed into a deterministic policy layer that returns:

- `stable`
- `marginal`
- `unstable`

with a continuous confidence signal for downstream planning loops.

## Architecture

- agent layer: planning runtimes and tool-calling systems
- tool interface layer: schema and CLI
- skill logic layer: bounded summaries and output formatting
- oracle policy layer: transparent deterministic classification
- adapter layer: external HAOS oracle bridge
- external dependency: frozen HAOS-IIP evaluation surface

## Documentation Set

1. [Evaluation Layer Diagram (PNG)](./assets/stability-oracle-evaluation-layer-overview.png)
2. [Overview Paper (PDF)](./assets/stability-oracle-overview.pdf)
3. [Numbered Documentation Paper (PDF)](./assets/01-stability-oracle-documentation-paper.pdf)
4. [Concept Document](https://github.com/tomislavrupic/stability-oracle/blob/main/haos-stability-skill/docs/WHAT_IS_STABILITY_ORACLE.md)
5. [Standalone Skill Package](https://github.com/tomislavrupic/stability-oracle/tree/main/haos-stability-skill)

## Current Contract

The application-layer skill exposes a compact report shaped for autonomous systems:

```json
{
  "classification": "stable",
  "structural_retention": 0.94,
  "temporal_consistency": 0.98,
  "causal_deformation": 0.12,
  "geometric_integrity": 0.96,
  "confidence": 0.82,
  "coherence_score": 0.94,
  "policy_version": "v1_floor_mean_band",
  "summary": "Structure is stable with high retention and low deformation."
}
```

## Build Direction

The project is advancing through small operational steps:

- invariant language layer
- pluggable metric interface
- deterministic classification policy
- public demo and scan surfaces
- agent skill integration

No grand claims are required. Only reproducible structure.
