# Continuous Agent Trajectory Demo

This demo tests whether the Stability Oracle can classify instability in a continuous 2-D motion domain using the same core engine used by the symbolic reasoning demo.

It does not test robotics control, physics realism, navigation optimality, or planning competence. It is a bounded trajectory-stability demonstration.

## Dynamics

The demo uses a deterministic damped goal-seeking point-agent system:

- position: `p_t = (x_t, y_t)`
- velocity: `v_t = (vx_t, vy_t)`
- goal: `g = (gx, gy)`

Update rule:

- `a_t = k_p * (g - p_t) - k_d * v_t + eta_t + b_t`
- `v_(t+1) = v_t + dt * a_t`
- `p_(t+1) = p_t + dt * v_(t+1)`

Noise is always seeded and deterministic.

The demo uses three fixed parameter families:

- stable
- marginal
- unstable

Each family differs only by the seed used for the Gaussian noise process.

## Telemetry Vector

Each simulation frame is converted into an 8-dimensional telemetry vector:

1. `x_position`
2. `y_position`
3. `x_velocity`
4. `y_velocity`
5. `heading_angle`
6. `curvature_estimate`
7. `distance_to_goal`
8. `control_signal_magnitude`

All values are numeric and fixed-width.

## Oracle Role

The oracle kernel is unchanged.

The demo path is:

1. raw trajectory frames
2. `AgentTrajectoryAdapter`
3. `TelemetrySequence`
4. existing normalizer
5. existing geometry encoder
6. existing telemetry bridge
7. existing oracle engine

This is the point of the demo: reuse, not reimplementation.

## Why This Domain Matters

This domain is maximally different from the LLM reasoning demo in one practical sense:

- the reasoning demo is symbolic and discrete
- this demo is continuous and geometric

If the same oracle can separate stable, marginal, and unstable behavior in both settings, the decoupling claim becomes much more concrete.

## Dataset

The dataset contains 15 trajectories total:

- 5 stable
- 5 marginal
- 5 unstable

The records store raw simulation values so the adapter can reconstruct telemetry deterministically.

## Reproducibility

Run the demo from the repository root:

```bash
MPLCONFIGDIR=/tmp/stability_oracle_demo_agent_mpl \
PYTHONPATH=/Volumes/Samsung\ T5/2026/HAOS/stability-oracle/haos-stability-skill:/Volumes/Samsung\ T5/2026/HAOS/stability-oracle \
python3 -m stability_oracle_demo_agent.pipeline.demo_runner
```

Outputs:

- `stability_oracle_demo_agent/output/results.csv`
- `stability_oracle_demo_agent/output/trajectory_plot.png`

The current parameter family marked `marginal` settles near the goal with visible overshoot but does not always meet a stricter `< 0.15` terminal-distance cutoff by step 100. The demo therefore keeps the parameter family fixed, records the observed summary in the dataset, and uses the oracle band separation itself as the public proof surface.
