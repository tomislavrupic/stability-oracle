# Demo V1 Frozen

This marker freezes the current continuous agent trajectory demo contract.

- dataset size = `15`
- telemetry dimension = `8`
- simulation is seeded and deterministic
- expected regime bands:
  - `stable -> stable`
  - `marginal -> marginal`
  - `unstable -> unstable`
- oracle kernel unchanged

This demo exists to show that the same oracle can classify instability in a continuous motion domain without changing the core engine.
