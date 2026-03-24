# Stability Oracle

Structural Stability Evaluation Layer for HAOS-IIP

![Stability Oracle Evaluation Layer Overview](./Images/Stability%20Oracle%20Evaluation%20Layer%20Overview.png)

Stability Oracle is a bounded evaluation surface for one operational question:

Given a state and a perturbation, does meaningful structure remain recoverably coherent?

The project is designed to make HAOS-IIP stability signals usable without entangling the research core with the application layer. The standalone skill layer treats HAOS-IIP as an external dependency and exposes a fast, deterministic interface for agents, demos, and downstream tooling.

## What This Repo Contains

- frozen research-facing oracle surfaces already present in the repository
- a standalone application-layer package in [`haos-stability-skill/`](./haos-stability-skill/)
- structural state contracts, metric interfaces, and a deterministic classification policy
- public documentation assets and diagrams in [`Images/`](./Images/)

## Quick Links

- [Standalone Skill Package](./haos-stability-skill/)
- [Concept Document](./haos-stability-skill/docs/WHAT_IS_STABILITY_ORACLE.md)
- [Numbered Documentation Paper (PDF)](./Images/01%20Stability%20Oracle%20Documentation%20Paper.pdf)
- [Overview PDF](./Images/Stability_Oracle.pdf)
- [GitHub Pages Source](./docs/)

## Current Architecture

- agent layer: planning runtime or tool-calling system
- tool interface layer: CLI and JSON schema
- skill logic layer: bounded reports and summaries
- oracle policy layer: deterministic classification
- adapter layer: external HAOS bridge
- external dependency: frozen HAOS-IIP evaluation surface

## Output Contract

`evaluate_structure(...)` returns a compact machine-readable report:

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

## Design Guarantees

- deterministic evaluation
- bounded JSON output
- read-only with respect to research artifacts
- no filesystem writes by default
- hard timeout enforcement
- fail-closed behavior under malformed inputs or adapter failures

## Status

The invariant language layer, metric interface, and first classification policy are now in place. The repository can already expose HAOS-style structural stability as an agent-callable skill while keeping the research core separate from the application layer.

## Next

- complete the oracle engine path from perturbation to policy verdict
- expand the public Pages surface with benchmark and integration notes
- continue growing the standalone package without modifying frozen research code
