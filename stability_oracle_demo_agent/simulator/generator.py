from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from stability_oracle_demo_agent.simulator.dynamics import observed_label, simulate_trajectory, summarize_trajectory


ROOT = Path(__file__).resolve().parents[1]
DATA_PATH = ROOT / "data" / "agent_traces.json"
REGIME_ORDER = ("stable", "marginal", "unstable")


def generate_dataset_records(per_regime: int = 5) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for regime_label in REGIME_ORDER:
        selected = 0
        seed = 0
        while selected < per_regime:
            trajectory = simulate_trajectory(regime_label, seed)
            summary = summarize_trajectory(trajectory)
            if observed_label(summary) == regime_label:
                trajectory["observed_summary"] = summary
                records.append(trajectory)
                selected += 1
            seed += 1
            if seed > 5000:
                raise RuntimeError(f"could not generate enough {regime_label} trajectories")
    return records


def dataset_payload(per_regime: int = 5) -> dict[str, Any]:
    records = generate_dataset_records(per_regime=per_regime)
    return {
        "description": "Deterministic 2-D goal-seeking agent trajectories for Stability Oracle demo domain 2.",
        "trajectory_count": len(records),
        "trajectories": records,
    }


def write_dataset(path: Path | None = None, per_regime: int = 5) -> Path:
    output_path = path or DATA_PATH
    payload = dataset_payload(per_regime=per_regime)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return output_path
