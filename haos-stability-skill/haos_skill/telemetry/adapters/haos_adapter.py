from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping

from ...state_spec import State, coerce_state
from ..contracts import TelemetryFrame, TelemetrySequence


@dataclass(frozen=True)
class HaosTelemetryAdapterConfig:
    include_delta: bool = True
    include_counts: bool = True
    include_metric_hints: bool = False


class HaosTelemetryAdapter:
    """
    Convert HAOS state transitions into deterministic numeric telemetry.
    """

    def __init__(self, config: HaosTelemetryAdapterConfig | None = None) -> None:
        self.config = config or HaosTelemetryAdapterConfig()

    def from_state_pair(self, before: Any, after: Any) -> TelemetrySequence:
        before_state = coerce_state(before)
        after_state = coerce_state(after)
        entity_id = _resolve_entity_id(before, after)

        before_features = _extract_state_features(before_state, include_counts=self.config.include_counts)
        after_features = _extract_state_features(after_state, include_counts=self.config.include_counts)

        before_vector = list(before_features)
        after_vector = list(after_features)
        feature_names = list(_feature_names(include_counts=self.config.include_counts))

        if self.config.include_delta:
            delta_vector = [round(after_value - before_value, 6) for before_value, after_value in zip(before_features, after_features)]
            before_vector.extend([0.0] * len(delta_vector))
            after_vector.extend(delta_vector)
            feature_names.extend("delta_%s" % name for name in _feature_names(include_counts=self.config.include_counts))

        if self.config.include_metric_hints:
            hints = _extract_transition_hints(before_state, after_state)
            before_vector.extend([0.0] * len(hints))
            after_vector.extend(hints)
            feature_names.extend(
                (
                    "hint_node_retention",
                    "hint_edge_retention",
                    "hint_timestamp_overlap",
                )
            )

        metadata = {
            "adapter": "haos_state_pair_v1",
            "feature_names": feature_names,
            "bridge_state_transition": {
                "before_state": before_state.to_dict(),
                "after_state": after_state.to_dict(),
            },
            "adapter_config": {
                "include_delta": self.config.include_delta,
                "include_counts": self.config.include_counts,
                "include_metric_hints": self.config.include_metric_hints,
            },
        }

        frames = (
            TelemetryFrame(
                timestamp=0.0,
                entity_id=entity_id,
                state_vector=before_vector,
                metadata={"phase": "before"},
            ),
            TelemetryFrame(
                timestamp=1.0,
                entity_id=entity_id,
                state_vector=after_vector,
                metadata={"phase": "after"},
            ),
        )
        return TelemetrySequence(
            frames=frames,
            entity_id=entity_id,
            feature_dim=len(frames[0].state_vector),
            metadata=metadata,
        )


def _resolve_entity_id(before: Any, after: Any) -> str:
    for candidate in (before, after):
        if isinstance(candidate, Mapping):
            for key in ("entity_id", "candidate_id", "plan_id"):
                raw = candidate.get(key)
                if raw is not None:
                    normalized = str(raw).strip()
                    if normalized:
                        return normalized
    return "haos-transition"


def _extract_state_features(state: State, *, include_counts: bool) -> tuple[float, ...]:
    node_count = float(len(state.nodes))
    edge_count = float(len(state.edges))
    feature_count = float(len(state.features or {}))
    timestamp_count = float(len(state.timestamps or {}))
    component_count = float(_connected_component_count(state))
    edge_density = _edge_density(state)
    mean_degree, max_degree = _degree_statistics(state)

    base_features = (
        node_count,
        edge_count,
        feature_count,
        timestamp_count,
        component_count,
        edge_density,
        mean_degree,
        max_degree,
    )
    if include_counts:
        return base_features
    return base_features[4:]


def _feature_names(*, include_counts: bool) -> tuple[str, ...]:
    names = (
        "node_count",
        "edge_count",
        "feature_count",
        "timestamp_count",
        "component_count",
        "edge_density",
        "mean_degree",
        "max_degree",
    )
    if include_counts:
        return names
    return names[4:]


def _extract_transition_hints(before: State, after: State) -> tuple[float, float, float]:
    before_nodes = set(before.nodes)
    after_nodes = set(after.nodes)
    before_edges = set(before.edges)
    after_edges = set(after.edges)
    before_timestamps = set((before.timestamps or {}).keys())
    after_timestamps = set((after.timestamps or {}).keys())

    node_retention = _overlap_ratio(before_nodes, after_nodes)
    edge_retention = _overlap_ratio(before_edges, after_edges)
    timestamp_overlap = _overlap_ratio(before_timestamps, after_timestamps)
    return (
        round(node_retention, 6),
        round(edge_retention, 6),
        round(timestamp_overlap, 6),
    )


def _connected_component_count(state: State) -> int:
    if not state.nodes:
        return 0
    adjacency = {node: set() for node in state.nodes}
    for source, target in state.edges:
        adjacency[source].add(target)
        adjacency[target].add(source)

    remaining = set(state.nodes)
    components = 0
    while remaining:
        components += 1
        start = remaining.pop()
        stack = [start]
        while stack:
            node = stack.pop()
            for neighbor in adjacency[node]:
                if neighbor in remaining:
                    remaining.remove(neighbor)
                    stack.append(neighbor)
    return components


def _edge_density(state: State) -> float:
    node_count = len(state.nodes)
    if node_count <= 1:
        return 0.0
    denominator = float(node_count * (node_count - 1))
    return round(len(state.edges) / denominator, 6)


def _degree_statistics(state: State) -> tuple[float, float]:
    if not state.nodes:
        return (0.0, 0.0)
    degrees = {node: 0 for node in state.nodes}
    for source, target in state.edges:
        degrees[source] += 1
        degrees[target] += 1
    degree_values = tuple(float(value) for value in degrees.values())
    mean_degree = round(sum(degree_values) / len(degree_values), 6)
    max_degree = round(max(degree_values), 6)
    return (mean_degree, max_degree)


def _overlap_ratio(before_values: set[Any], after_values: set[Any]) -> float:
    if not before_values:
        return 1.0 if not after_values else 0.0
    return len(before_values & after_values) / len(before_values)
