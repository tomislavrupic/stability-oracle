from __future__ import annotations

import math
from typing import Any

from haos_skill import State
from haos_skill.telemetry import TelemetryFrame, TelemetrySequence

from stability_oracle_demo_agent.simulator.dynamics import summarize_trajectory


FEATURE_NAMES = (
    "x_position",
    "y_position",
    "x_velocity",
    "y_velocity",
    "heading_angle",
    "curvature_estimate",
    "distance_to_goal",
    "control_signal_magnitude",
)


class AgentTrajectoryAdapter:
    def from_trajectory(self, trajectory: dict, entity_id: str) -> TelemetrySequence:
        if not isinstance(entity_id, str) or not entity_id.strip():
            raise ValueError("entity_id must be a non-empty string")
        if not isinstance(trajectory, dict):
            raise ValueError("trajectory must be a mapping")

        raw_frames = trajectory.get("frames")
        if not isinstance(raw_frames, list) or not raw_frames:
            raise ValueError("trajectory frames must be a non-empty list")

        telemetry_frames: list[TelemetryFrame] = []
        previous_heading = 0.0
        for index, frame in enumerate(raw_frames):
            heading = math.atan2(float(frame["vy"]), float(frame["vx"]))
            curvature = 0.0 if index == 0 else _angle_change(previous_heading, heading) / math.pi
            previous_heading = heading

            distance_to_goal = math.hypot(
                float(frame["goal_x"]) - float(frame["x"]),
                float(frame["goal_y"]) - float(frame["y"]),
            )
            control_magnitude = math.hypot(float(frame["ax"]), float(frame["ay"]))

            telemetry_frames.append(
                TelemetryFrame(
                    timestamp=float(frame["step_index"]),
                    entity_id=entity_id,
                    state_vector=(
                        _normalize_position(float(frame["x"])),
                        _normalize_position(float(frame["y"])),
                        _normalize_velocity(float(frame["vx"])),
                        _normalize_velocity(float(frame["vy"])),
                        round((heading + math.pi) / (2.0 * math.pi), 6),
                        round(_clip(curvature), 6),
                        round(_clip(distance_to_goal / 1.8), 6),
                        round(_clip(control_magnitude / 2.5), 6),
                    ),
                    metadata={
                        "step_index": int(frame["step_index"]),
                        "seed": int(trajectory["seed"]),
                        "regime_label": str(trajectory["regime_label"]),
                        "trajectory_id": str(trajectory["trajectory_id"]),
                        "feature_names": list(FEATURE_NAMES),
                    },
                )
            )

        summary = summarize_trajectory(trajectory)
        before_state = _build_before_state(telemetry_frames)
        after_state = _build_after_state(telemetry_frames, summary)

        return TelemetrySequence(
            frames=tuple(telemetry_frames),
            entity_id=entity_id,
            feature_dim=len(telemetry_frames[0].state_vector),
            metadata={
                "adapter": "agent_trajectory_v1",
                "trajectory_id": str(trajectory["trajectory_id"]),
                "regime_label": str(trajectory["regime_label"]),
                "seed": int(trajectory["seed"]),
                "feature_names": list(FEATURE_NAMES),
                "trajectory_summary": summary,
                "bridge_state_transition": {
                    "before_state": before_state.to_dict(),
                    "after_state": after_state.to_dict(),
                },
            },
        )


def _build_before_state(frames: list[TelemetryFrame]) -> State:
    nodes = tuple(range(len(frames)))
    edges = tuple(
        [(index, index + 1) for index in range(len(nodes) - 1)]
        + [(index, index + 2) for index in range(len(nodes) - 2)]
    )
    timestamps = {index: frame.timestamp for index, frame in enumerate(frames)}
    features = {
        index: {
            "vector": list(frame.state_vector),
            "distance_to_goal": frame.state_vector[6],
            "control_signal_magnitude": frame.state_vector[7],
        }
        for index, frame in enumerate(frames)
    }
    return State(nodes=nodes, edges=edges, timestamps=timestamps, features=features)


def _build_after_state(
    frames: list[TelemetryFrame],
    summary: dict[str, Any],
) -> State:
    before_state = _build_before_state(frames)
    instability_profile = _trajectory_instability(summary)
    local_instabilities = [_local_instability(index, frame, frames) for index, frame in enumerate(frames)]

    if instability_profile < 0.38:
        retained_nodes = list(before_state.nodes)
        retained_edges = list(before_state.edges)
        timestamps = {index: frame.timestamp for index, frame in enumerate(frames)}
    elif instability_profile < 0.75:
        retained_nodes = list(before_state.nodes)
        retained_edges = [
            edge
            for edge in before_state.edges
            if edge[1] - edge[0] == 1 and _edge_continuity(edge, frames) >= 0.40
        ]
        timestamps = _timestamps_with_soft_ties(frames, local_instabilities)
    else:
        retained_nodes = _select_unstable_nodes(frames, local_instabilities)
        retained_node_set = set(retained_nodes)
        retained_edges = [
            edge
            for edge in before_state.edges
            if edge[0] in retained_node_set
            and edge[1] in retained_node_set
            and edge[1] - edge[0] == 1
            and _edge_continuity(edge, frames) >= 0.70
        ]
        timestamps = _timestamps_with_collapse(frames, retained_nodes, local_instabilities)

    retained_node_set = set(retained_nodes)
    features = {
        index: {
            "vector": list(frames[index].state_vector),
            "local_instability": round(local_instabilities[index], 6),
        }
        for index in retained_nodes
    }

    return State(
        nodes=tuple(retained_nodes),
        edges=tuple(retained_edges),
        timestamps={index: timestamps[index] for index in retained_nodes},
        features=features,
    )


def _trajectory_instability(summary: dict[str, Any]) -> float:
    final_distance_norm = _clip(float(summary["final_distance_to_goal"]) / 0.6)
    mean_control_norm = _clip(float(summary["mean_control_signal"]) / 0.9)
    radius_norm = _clip(float(summary["mean_goal_radius"]) / 0.9)
    return _clip(0.45 * final_distance_norm + 0.30 * mean_control_norm + 0.25 * radius_norm)


def _local_instability(index: int, frame: TelemetryFrame, frames: list[TelemetryFrame]) -> float:
    distance = float(frame.state_vector[6])
    curvature = float(frame.state_vector[5])
    control = float(frame.state_vector[7])
    progress_penalty = 0.0
    if index > 0:
        previous_distance = float(frames[index - 1].state_vector[6])
        progress_penalty = _clip((distance - previous_distance) / 0.10)
    return _clip(0.38 * distance + 0.27 * control + 0.20 * curvature + 0.15 * progress_penalty)


def _edge_continuity(edge: tuple[int, int], frames: list[TelemetryFrame]) -> float:
    source, target = edge
    target_frame = frames[target]
    continuity = (
        0.40 * (1.0 - float(target_frame.state_vector[5]))
        + 0.30 * (1.0 - float(target_frame.state_vector[6]))
        + 0.20 * (1.0 - float(target_frame.state_vector[7]))
        + 0.10 * (1.0 - abs(0.5 - float(target_frame.state_vector[4])) * 2.0)
    )
    if target - source == 2:
        bridge_frame = frames[source + 1]
        continuity = (continuity + (
            0.40 * (1.0 - float(bridge_frame.state_vector[5]))
            + 0.30 * (1.0 - float(bridge_frame.state_vector[6]))
            + 0.20 * (1.0 - float(bridge_frame.state_vector[7]))
            + 0.10 * (1.0 - abs(0.5 - float(bridge_frame.state_vector[4])) * 2.0)
        )) / 2.0
    return _clip(continuity)


def _timestamps_with_soft_ties(
    frames: list[TelemetryFrame],
    local_instabilities: list[float],
) -> dict[int, float]:
    timestamps: dict[int, float] = {}
    previous_timestamp = -1.0
    for index, frame in enumerate(frames):
        if index > 0 and local_instabilities[index] >= 0.44:
            timestamp = previous_timestamp
        else:
            timestamp = frame.timestamp
        timestamps[index] = float(timestamp)
        previous_timestamp = float(timestamp)
    return timestamps


def _select_unstable_nodes(
    frames: list[TelemetryFrame],
    local_instabilities: list[float],
) -> list[int]:
    horizon = max(10, min(len(frames) - 1, len(frames) // 3))
    retained = [0]
    for index in range(1, horizon):
        if index < 6 or local_instabilities[index] < 0.75:
            retained.append(index)
    retained.append(len(frames) - 1)
    return sorted(set(retained))


def _timestamps_with_collapse(
    frames: list[TelemetryFrame],
    retained_nodes: list[int],
    local_instabilities: list[float],
) -> dict[int, float]:
    timestamps: dict[int, float] = {}
    previous_timestamp = -1.0
    collapse_point = len(retained_nodes) // 2
    for order_index, index in enumerate(retained_nodes):
        if order_index > 0 and (order_index > collapse_point or local_instabilities[index] >= 0.45):
            timestamp = previous_timestamp - 0.10
        elif order_index > 0 and index % 5 == 0:
            timestamp = previous_timestamp
        else:
            timestamp = frames[index].timestamp
        timestamps[index] = float(timestamp)
        previous_timestamp = float(timestamp)
    return timestamps


def _normalize_position(value: float) -> float:
    return round(_clip((value + 0.75) / 2.5), 6)


def _normalize_velocity(value: float) -> float:
    return round(_clip((value + 1.25) / 2.5), 6)


def _clip(value: float) -> float:
    return max(0.0, min(1.0, float(value)))


def _angle_change(previous_heading: float, current_heading: float) -> float:
    return abs(math.atan2(math.sin(current_heading - previous_heading), math.cos(current_heading - previous_heading)))
