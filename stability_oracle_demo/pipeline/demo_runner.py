from __future__ import annotations

from collections import Counter
import json
import os
from pathlib import Path
from typing import Any

import pandas as pd
import matplotlib

from haos_skill import State, build_default_engine
from stability_oracle_demo.telemetry.adapters.llm_reasoning_adapter import LLMReasoningAdapter, TelemetrySequence


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "reasoning_demo_traces.json"
OUTPUT_DIR = ROOT / "output"
RESULTS_PATH = OUTPUT_DIR / "results.csv"
PLOT_PATH = OUTPUT_DIR / "metrics_plot.png"
EXPLANATIONS_PATH = OUTPUT_DIR / "trace_explanations.json"

matplotlib.use("Agg")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/stability_oracle_demo_mpl")
import matplotlib.pyplot as plt  # noqa: E402


class ReasoningTraceOracle:
    def __init__(self) -> None:
        self.engine = build_default_engine()

    def classify(self, sequence: TelemetrySequence) -> dict[str, Any]:
        before_state = _build_reasoning_state(sequence)
        after_state = _build_observed_state(sequence)
        result = self.engine.evaluate_transition(before_state, after_state)
        return {
            "class": result.classification,
            "confidence": result.confidence,
            "metrics": {
                "retention": result.metrics.structural_retention,
                "temporal_consistency": result.metrics.temporal_consistency,
                "causal_defect": result.metrics.causal_deformation,
                "geometric_coherence": result.metrics.geometric_integrity,
            },
            "policy_version": result.policy_version,
            "trace": result.trace,
            "derived_transition": {
                "before_node_count": len(before_state.nodes),
                "after_node_count": len(after_state.nodes),
                "before_edge_count": len(before_state.edges),
                "after_edge_count": len(after_state.edges),
            },
        }


def load_dataset(path: Path | None = None) -> list[dict[str, Any]]:
    dataset_path = path or DATA_PATH
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    tasks = payload.get("tasks", [])
    if not isinstance(tasks, list) or not tasks:
        raise ValueError("dataset must contain a non-empty 'tasks' list")
    return tasks


def run_demo(dataset_path: Path | None = None) -> pd.DataFrame:
    adapter = LLMReasoningAdapter()
    oracle = ReasoningTraceOracle()
    tasks = load_dataset(dataset_path)

    rows: list[dict[str, Any]] = []
    explanations: list[dict[str, Any]] = []
    for task in tasks:
        sequence = adapter.from_trace(task["trace"], task["task_id"])
        result = oracle.classify(sequence)
        rows.append(
            {
                "task_id": task["task_id"],
                "trace_type": task["trace_type"],
                "oracle_class": result["class"],
                "confidence": result["confidence"],
                "retention": result["metrics"]["retention"],
                "temporal_consistency": result["metrics"]["temporal_consistency"],
                "causal_defect": result["metrics"]["causal_defect"],
                "geometric_coherence": result["metrics"]["geometric_coherence"],
                "outcome": task["outcome"],
            }
        )
        explanations.append(_build_trace_explanation(task, sequence, result))

    frame = pd.DataFrame(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(RESULTS_PATH, index=False)
    EXPLANATIONS_PATH.write_text(json.dumps(explanations, indent=2), encoding="utf-8")
    _plot_metrics(frame, PLOT_PATH)
    return frame


def main() -> None:
    frame = run_demo()
    counts = (
        frame.groupby(["trace_type", "oracle_class"]).size().reset_index(name="count").sort_values(["trace_type", "oracle_class"])
    )
    print(frame.to_string(index=False))
    print()
    print(counts.to_string(index=False))
    print()
    print(f"Wrote {RESULTS_PATH}")
    print(f"Wrote {EXPLANATIONS_PATH}")
    print(f"Wrote {PLOT_PATH}")


def _build_reasoning_state(sequence: TelemetrySequence) -> State:
    nodes = tuple(range(len(sequence.frames)))
    edges = tuple(
        [(index, index + 1) for index in range(len(nodes) - 1)]
        + [(index, index + 2) for index in range(len(nodes) - 2)]
    )
    timestamps = {index: frame.timestamp for index, frame in enumerate(sequence.frames)}
    features = {
        index: {
            "vector": list(frame.state_vector),
            "text": frame.metadata.get("text", ""),
            "is_final": bool(frame.metadata.get("is_final", False)),
        }
        for index, frame in enumerate(sequence.frames)
    }
    return State(nodes=nodes, edges=edges, timestamps=timestamps, features=features)


def _build_observed_state(sequence: TelemetrySequence) -> State:
    before_state = _build_reasoning_state(sequence)
    instability_scores = [_node_instability(index, frame.state_vector, len(sequence.frames)) for index, frame in enumerate(sequence.frames)]

    retained_nodes = [index for index, score in enumerate(instability_scores) if score < 0.70 or index == 0]
    if (len(sequence.frames) - 1) not in retained_nodes and instability_scores[-1] < 0.92:
        retained_nodes.append(len(sequence.frames) - 1)
    retained_nodes = sorted(set(retained_nodes))
    retained_set = set(retained_nodes)

    edges: list[tuple[int, int]] = []
    for source, target in before_state.edges:
        if source not in retained_set or target not in retained_set:
            continue
        continuity = _edge_continuity(sequence, source, target)
        if continuity >= 0.46:
            edges.append((source, target))

    timestamps: dict[int, float] = {}
    previous_timestamp = -1.0
    for index in retained_nodes:
        vector = sequence.frames[index].state_vector
        if vector[4] >= 0.75 and index > 0:
            timestamp = previous_timestamp - 0.25
        elif instability_scores[index] >= 0.55 and index > 0:
            timestamp = previous_timestamp
        else:
            timestamp = sequence.frames[index].timestamp
        timestamps[index] = float(timestamp)
        previous_timestamp = float(timestamp)

    features = {
        index: {
            "vector": list(sequence.frames[index].state_vector),
            "text": sequence.frames[index].metadata.get("text", ""),
            "is_final": bool(sequence.frames[index].metadata.get("is_final", False)),
            "instability_score": round(instability_scores[index], 4),
        }
        for index in retained_nodes
    }
    return State(nodes=tuple(retained_nodes), edges=tuple(edges), timestamps=timestamps, features=features)


def _plot_metrics(frame: pd.DataFrame, plot_path: Path) -> None:
    summary = (
        frame.assign(causal_stability=1.0 - frame["causal_defect"])
        .groupby("trace_type")[["confidence", "retention", "temporal_consistency", "causal_stability", "geometric_coherence"]]
        .mean()
        .reindex(["coherent", "drifted", "broken"])
    )

    figure, axis = plt.subplots(figsize=(10, 5))
    summary.plot(kind="bar", ax=axis)
    axis.set_ylim(0.0, 1.05)
    axis.set_ylabel("Mean score")
    axis.set_title("Reasoning Trace Stability Metrics")
    axis.legend(loc="lower left", ncols=2)
    axis.grid(axis="y", alpha=0.2)
    figure.tight_layout()
    figure.savefig(plot_path, dpi=160)
    plt.close(figure)


def _mean(values: Any) -> float:
    values = list(values)
    if not values:
        return 0.0
    return sum(float(value) for value in values) / len(values)


def _clip(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _build_trace_explanation(
    task: dict[str, Any],
    sequence: TelemetrySequence,
    result: dict[str, Any],
) -> dict[str, Any]:
    retention = float(result["metrics"]["retention"])
    temporal_consistency = float(result["metrics"]["temporal_consistency"])
    causal_defect = float(result["metrics"]["causal_defect"])
    geometric_coherence = float(result["metrics"]["geometric_coherence"])

    instability_contributions = {
        "retention": _clip(1.0 - retention),
        "temporal_consistency": _clip(1.0 - temporal_consistency),
        "causal_defect": _clip(causal_defect),
        "geometric_coherence": _clip(1.0 - geometric_coherence),
    }
    dominant_metric = max(instability_contributions, key=instability_contributions.get)

    recovery_scores = [_frame_recovery_score(frame.state_vector) for frame in sequence.frames]
    transition_magnitude = _transition_magnitude(sequence)

    return {
        "task_id": task["task_id"],
        "trace_type": task["trace_type"],
        "oracle_class": result["class"],
        "dominant_metric_contribution": {
            "metric": dominant_metric,
            "instability_contribution": round(instability_contributions[dominant_metric], 4),
        },
        "transition_magnitude": round(transition_magnitude, 4),
        "recovery_score_trend": {
            "values": [round(score, 4) for score in recovery_scores],
            "direction": _trend_direction(recovery_scores),
        },
        "final_class_reason": _class_reason(
            classification=result["class"],
            dominant_metric=dominant_metric,
            transition_magnitude=transition_magnitude,
        ),
    }


def _node_instability(index: int, vector: list[float], total_steps: int) -> float:
    instability = (
        0.38 * vector[4]
        + 0.22 * (1.0 - vector[5])
        + 0.18 * vector[2]
        + 0.12 * vector[6]
        + 0.10 * (1.0 - vector[1])
    )
    if index == total_steps - 1:
        instability += 0.25 * (1.0 - vector[7])
    return _clip(instability)


def _edge_continuity(sequence: TelemetrySequence, source: int, target: int) -> float:
    target_vector = sequence.frames[target].state_vector
    continuity = (
        0.38 * target_vector[3]
        + 0.32 * target_vector[5]
        + 0.15 * (1.0 - target_vector[4])
        + 0.15 * target_vector[1]
    )
    if target - source == 2:
        bridge_vector = sequence.frames[source + 1].state_vector
        bridge_continuity = (
            0.38 * bridge_vector[3]
            + 0.32 * bridge_vector[5]
            + 0.15 * (1.0 - bridge_vector[4])
            + 0.15 * bridge_vector[1]
        )
        continuity = (continuity + bridge_continuity) / 2.0
    return _clip(continuity)


def _frame_recovery_score(vector: list[float]) -> float:
    return _clip(
        0.30 * vector[3]
        + 0.25 * (1.0 - vector[4])
        + 0.20 * vector[5]
        + 0.15 * vector[1]
        + 0.10 * vector[7]
    )


def _transition_magnitude(sequence: TelemetrySequence) -> float:
    if len(sequence.frames) < 2:
        return 0.0
    deltas: list[float] = []
    for left, right in zip(sequence.frames, sequence.frames[1:]):
        step_delta = sum(abs(a - b) for a, b in zip(left.state_vector, right.state_vector)) / len(left.state_vector)
        deltas.append(step_delta)
    return _clip(_mean(deltas))


def _trend_direction(values: list[float]) -> str:
    if len(values) < 2:
        return "flat"
    total_change = values[-1] - values[0]
    if total_change >= 0.12:
        return "rising"
    if total_change <= -0.12:
        return "falling"
    return "mixed"


def _class_reason(classification: str, dominant_metric: str, transition_magnitude: float) -> str:
    if classification == "stable":
        return "Stable because the transition stayed bounded and no core metric collapsed."
    if classification == "marginal":
        return (
            f"Marginal because {dominant_metric.replace('_', ' ')} absorbed the main distortion "
            f"while the trajectory stayed recoverable."
        )
    return (
        f"Unstable because {dominant_metric.replace('_', ' ')} dominated the transition "
        f"and the trajectory did not recover cleanly."
    )


if __name__ == "__main__":
    main()
