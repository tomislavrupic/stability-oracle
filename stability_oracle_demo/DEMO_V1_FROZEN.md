# Demo V1 Frozen

This marker freezes the current LLM reasoning demo contract.

- telemetry dimension = `8`
- dataset size = `12` traces
- expected classification bands:
  - `coherent -> stable`
  - `drifted -> marginal`
  - `broken -> unstable`
- no stochastic components
- oracle kernel untouched

Anchor sentence:

This demo shows that the oracle can detect structural reasoning drift using only trajectory geometry.

If the demo changes meaningfully after this point, version it explicitly instead of silently editing the contract.
