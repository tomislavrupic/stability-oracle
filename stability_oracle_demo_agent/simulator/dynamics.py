from __future__ import annotations

from dataclasses import asdict, dataclass
import math
from typing import Any

import numpy as np


@dataclass(frozen=True)
class AgentDynamicsConfig:
    regime_label: str
    k_p: float
    k_d: float
    sigma: float
    beta: float = 0.0
    omega: float = 0.0
    gamma: float = 0.0
    start_position: tuple[float, float] = (0.0, 0.0)
    goal_position: tuple[float, float] = (1.0, 1.0)
    initial_velocity: tuple[float, float] = (0.0, 0.0)
    dt: float = 0.05
    total_steps: int = 100


GLOBAL_DEFAULTS = {
    "start_position": (0.0, 0.0),
    "goal_position": (1.0, 1.0),
    "initial_velocity": (0.0, 0.0),
    "dt": 0.05,
    "total_steps": 100,
}


REGIME_CONFIGS: dict[str, AgentDynamicsConfig] = {
    "stable": AgentDynamicsConfig(
        regime_label="stable",
        k_p=1.2,
        k_d=1.1,
        sigma=0.01,
        beta=0.0,
        omega=0.0,
        gamma=0.0,
        **GLOBAL_DEFAULTS,
    ),
    "marginal": AgentDynamicsConfig(
        regime_label="marginal",
        k_p=1.2,
        k_d=0.45,
        sigma=0.04,
        beta=0.03,
        omega=0.25,
        gamma=0.0,
        **GLOBAL_DEFAULTS,
    ),
    "unstable": AgentDynamicsConfig(
        regime_label="unstable",
        k_p=1.0,
        k_d=0.10,
        sigma=0.08,
        beta=0.0,
        omega=0.0,
        gamma=0.18,
        **GLOBAL_DEFAULTS,
    ),
}


def simulate_trajectory(regime_label: str, seed: int) -> dict[str, Any]:
    config = REGIME_CONFIGS[regime_label]
    rng = np.random.default_rng(seed)

    position = np.array(config.start_position, dtype=float)
    velocity = np.array(config.initial_velocity, dtype=float)
    goal = np.array(config.goal_position, dtype=float)

    frames: list[dict[str, float | int]] = []
    for step_index in range(config.total_steps):
        acceleration = (
            config.k_p * (goal - position)
            - config.k_d * velocity
            + rng.normal(0.0, config.sigma, size=2)
            + _bias_term(config, step_index, position, goal)
        )

        frames.append(
            {
                "step_index": step_index,
                "x": round(float(position[0]), 6),
                "y": round(float(position[1]), 6),
                "vx": round(float(velocity[0]), 6),
                "vy": round(float(velocity[1]), 6),
                "ax": round(float(acceleration[0]), 6),
                "ay": round(float(acceleration[1]), 6),
                "goal_x": round(float(goal[0]), 6),
                "goal_y": round(float(goal[1]), 6),
            }
        )

        velocity = velocity + config.dt * acceleration
        position = position + config.dt * velocity

    return {
        "trajectory_id": f"{regime_label}-{seed:03d}",
        "regime_label": regime_label,
        "seed": seed,
        "parameters": _parameter_payload(config),
        "frames": frames,
    }


def summarize_trajectory(trajectory: dict[str, Any]) -> dict[str, float | int | bool]:
    frames = trajectory["frames"]
    distances = [_distance_to_goal(frame) for frame in frames]
    final_distance = distances[-1]

    distance_increases = sum(
        1 for previous, current in zip(distances, distances[1:]) if current > previous + 0.003
    )
    overshoot = any(frame_distance < 0.12 for frame_distance in distances[:-1]) and any(
        later > earlier + 0.04
        for earlier, later in zip(distances, distances[1:])
    )
    mean_control = sum(_control_magnitude(frame) for frame in frames) / len(frames)
    mean_radius = sum(_goal_centered_radius(frame) for frame in frames) / len(frames)
    large_excursions = sum(1 for frame_distance in distances if frame_distance > 1.2)
    heading_changes = _heading_changes(frames)
    high_curvature_steps = sum(1 for change in heading_changes if change > 0.28)

    return {
        "final_distance_to_goal": round(final_distance, 6),
        "distance_increase_count": distance_increases,
        "overshoot": bool(overshoot),
        "mean_control_signal": round(mean_control, 6),
        "mean_goal_radius": round(mean_radius, 6),
        "large_excursion_count": large_excursions,
        "high_curvature_steps": high_curvature_steps,
    }


def observed_label(summary: dict[str, float | int | bool]) -> str:
    final_distance = float(summary["final_distance_to_goal"])
    overshoot = bool(summary["overshoot"])
    distance_increase_count = int(summary["distance_increase_count"])
    mean_control = float(summary["mean_control_signal"])
    high_curvature_steps = int(summary["high_curvature_steps"])

    if final_distance < 0.08 and not overshoot and mean_control < 0.45:
        return "stable"

    if final_distance < 0.25 and (overshoot or distance_increase_count >= 20 or high_curvature_steps >= 2) and mean_control < 0.8:
        return "marginal"

    return "unstable"


def _bias_term(
    config: AgentDynamicsConfig,
    step_index: int,
    position: np.ndarray,
    goal: np.ndarray,
) -> np.ndarray:
    if config.gamma > 0.0:
        offset = position - goal
        return config.gamma * np.array([-offset[1], offset[0]], dtype=float)

    if config.beta > 0.0:
        return config.beta * np.array(
            [math.sin(config.omega * step_index), math.cos(config.omega * step_index)],
            dtype=float,
        )

    return np.zeros(2, dtype=float)


def _parameter_payload(config: AgentDynamicsConfig) -> dict[str, Any]:
    payload = asdict(config)
    payload["start_position"] = list(config.start_position)
    payload["goal_position"] = list(config.goal_position)
    payload["initial_velocity"] = list(config.initial_velocity)
    return payload


def _distance_to_goal(frame: dict[str, Any]) -> float:
    return math.hypot(float(frame["goal_x"]) - float(frame["x"]), float(frame["goal_y"]) - float(frame["y"]))


def _control_magnitude(frame: dict[str, Any]) -> float:
    return math.hypot(float(frame["ax"]), float(frame["ay"]))


def _goal_centered_radius(frame: dict[str, Any]) -> float:
    return math.hypot(float(frame["x"]) - float(frame["goal_x"]), float(frame["y"]) - float(frame["goal_y"]))


def _heading_changes(frames: list[dict[str, Any]]) -> list[float]:
    headings = [math.atan2(float(frame["vy"]), float(frame["vx"])) for frame in frames]
    changes: list[float] = []
    for previous, current in zip(headings, headings[1:]):
        delta = math.atan2(math.sin(current - previous), math.cos(current - previous))
        changes.append(abs(delta))
    return changes
