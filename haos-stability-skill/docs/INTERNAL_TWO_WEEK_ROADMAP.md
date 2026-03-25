# Internal Two-Week Roadmap

This roadmap is intentionally small.

Its purpose is to make the oracle feel real and usable without creating architectural drift.

## Week 1: Make The Instrument Stable

### Day 1-2

Lock the telemetry path.

- freeze `TelemetryFrame` and `TelemetrySequence`
- ensure fixed-width windows always emerge from the normalizer
- add one brutal validator for `NaN`, `Inf`, and dimension drift
- write a short note describing what counts as valid telemetry

Outcome:

You trust ingestion.

### Day 3

Simplify geometry encoding.

- scaling
- first derivative
- optional smoothing
- remove everything else

Run three tiny synthetic trajectories and confirm the metrics behave monotonically.

Outcome:

You trust the state representation.

### Day 4-5

Metric sanity pass.

- wrap current HAOS metrics as plugins
- log raw metric time-series for inspection
- verify classification boundaries do not jitter

Add one visualization script only for internal use.

Outcome:

You trust verdict stability.

### Weekend

One clean parity confirmation.

- HAOS path vs telemetry path
- same input -> same band: `stable`, `marginal`, or `unstable`
- write a short markdown parity memo

Outcome:

Psychological closure on the decoupling step.

## Week 2: Make One Undeniable Demo

### Day 6-7

Choose one non-physics trajectory domain.
Keep it boring and observable.

Examples that fit:

- LLM reasoning step vectors
- agent reward curves
- financial micro-volatility windows
- sensor drift sequences

Pick only one.

Outcome:

Scope is contained.

### Day 8-9

Build the adapter only.

- deterministic feature extraction
- fixed vector width
- no ML
- no streaming
- batch windows only

Run the oracle and produce a verdict timeline.

Outcome:

The first foreign signal enters the instrument.

### Day 10

Design one simple prediction test.

Example structure:

- detect instability early
- compare to a naive baseline
- show the oracle flag precedes failure

Do not optimize.
Just verify directionality.

Outcome:

The oracle begins to predict, not just label.

### Day 11-12

Write a minimal internal report.

Suggested sections:

- trajectory description
- metric behavior
- verdict interpretation
- what surprised you

No theory.
Just observation.

Outcome:

Knowledge becomes concrete.

### Day 13-14

Refinement window.

- tighten thresholds
- remove dead code
- rename confusing variables
- prepare one small public artifact: plot, GIF, or short note

Outcome:

The instrument becomes presentable without forcing hype.

## Target State

If this is done calmly, the result after two weeks should be:

- a decoupled oracle
- one real non-HAOS demonstration
- internal confidence
- zero architectural chaos

That is the correct scale right now.
