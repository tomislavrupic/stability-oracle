from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

import matplotlib
import pandas as pd

from haos_skill import StateGeometryEncoder, TemporalNormalizer, build_default_engine, telemetry_to_state_transition
from stability_oracle_demo_agent.simulator.generator import DATA_PATH, write_dataset
from stability_oracle_demo_agent.telemetry.adapters.agent_trajectory_adapter import AgentTrajectoryAdapter


ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = ROOT / "output"
RESULTS_PATH = OUTPUT_DIR / "results.csv"
PLOT_PATH = OUTPUT_DIR / "trajectory_plot.png"

matplotlib.use("Agg")
os.environ.setdefault("MPLCONFIGDIR", "/tmp/stability_oracle_demo_agent_mpl")
import matplotlib.pyplot as plt  # noqa: E402


class AgentTrajectoryOracle:
    def __init__(self) -> None:
        self.adapter = AgentTrajectoryAdapter()
        self.normalizer = TemporalNormalizer()
        self.encoder = StateGeometryEncoder()
        self.engine = build_default_engine()

    def classify(self, trajectory: dict[str, Any]) -> dict[str, Any]:
        sequence = self.adapter.from_trajectory(trajectory, trajectory["trajectory_id"])
        normalized = self.normalizer.normalize(sequence)
        encoded = self.encoder.encode(normalized)
        before, after = telemetry_to_state_transition(encoded)
        result = self.engine.evaluate_transition(before, after)
        return {
            "trajectory_id": trajectory["trajectory_id"],
            "regime_label": trajectory["regime_label"],
            "class": result.classification,
            "confidence": result.confidence,
            "metrics": result.metrics.to_dict(),
            "trace": result.trace,
        }


def ensure_dataset(path: Path | None = None) -> Path:
    output_path = path or DATA_PATH
    if not output_path.exists():
        write_dataset(output_path)
    return output_path


def load_dataset(path: Path | None = None) -> list[dict[str, Any]]:
    dataset_path = ensure_dataset(path)
    payload = json.loads(dataset_path.read_text(encoding="utf-8"))
    trajectories = payload.get("trajectories", [])
    if not isinstance(trajectories, list) or not trajectories:
        raise ValueError("dataset must contain a non-empty 'trajectories' list")
    return trajectories


def run_demo(dataset_path: Path | None = None) -> pd.DataFrame:
    trajectories = load_dataset(dataset_path)
    oracle = AgentTrajectoryOracle()

    rows: list[dict[str, Any]] = []
    for trajectory in trajectories:
        result = oracle.classify(trajectory)
        rows.append(
            {
                "trajectory_id": trajectory["trajectory_id"],
                "regime_label": trajectory["regime_label"],
                "oracle_class": result["class"],
                "confidence": result["confidence"],
                "structural_retention": result["metrics"]["structural_retention"],
                "temporal_consistency": result["metrics"]["temporal_consistency"],
                "causal_deformation": result["metrics"]["causal_deformation"],
                "geometric_integrity": result["metrics"]["geometric_integrity"],
            }
        )

    frame = pd.DataFrame(rows)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    frame.to_csv(RESULTS_PATH, index=False)
    _plot_examples(trajectories, frame, PLOT_PATH)
    return frame


def main() -> None:
    frame = run_demo()
    counts = frame.groupby(["regime_label", "oracle_class"]).size().reset_index(name="count")
    print(frame.to_string(index=False))
    print()
    print(counts.to_string(index=False))
    print()
    print(f"Wrote {RESULTS_PATH}")
    print(f"Wrote {PLOT_PATH}")


def _plot_examples(trajectories: list[dict[str, Any]], frame: pd.DataFrame, plot_path: Path) -> None:
    figure, axes = plt.subplots(1, 3, figsize=(12, 4))
    for axis, regime_label in zip(axes, ("stable", "marginal", "unstable")):
        trajectory = next(item for item in trajectories if item["regime_label"] == regime_label)
        oracle_class = frame.loc[frame["trajectory_id"] == trajectory["trajectory_id"], "oracle_class"].iloc[0]

        xs = [step["x"] for step in trajectory["frames"]]
        ys = [step["y"] for step in trajectory["frames"]]
        axis.plot(xs, ys, linewidth=1.8, color="#2c4f80")
        axis.scatter([xs[0]], [ys[0]], c="#2a9d8f", s=40, label="start")
        axis.scatter([trajectory["frames"][0]["goal_x"]], [trajectory["frames"][0]["goal_y"]], c="#e76f51", s=40, label="goal")
        axis.scatter([xs[-1]], [ys[-1]], c="#264653", s=28, label="final")
        axis.set_title(f"{regime_label.capitalize()} -> {oracle_class}")
        axis.set_xlabel("x")
        axis.set_ylabel("y")
        axis.grid(alpha=0.2)
        axis.set_aspect("equal", adjustable="box")

    handles, labels = axes[0].get_legend_handles_labels()
    figure.legend(handles, labels, loc="lower center", ncols=3, frameon=False)
    figure.tight_layout(rect=(0, 0.08, 1, 1))
    figure.savefig(plot_path, dpi=160)
    plt.close(figure)


if __name__ == "__main__":
    main()
