from __future__ import annotations

import json
from collections import deque
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class TrajectoryValidationError(ValueError):
    """Raised when a trajectory payload fails normalization or validation."""


@dataclass(frozen=True)
class TrajectoryNode:
    id: str
    step_type: str
    reversible: bool
    checkpoint: bool
    invariant_tags: tuple[str, ...]
    risk_weight: float

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TrajectoryNode":
        node_id = str(payload.get("id", "")).strip()
        if not node_id:
            raise TrajectoryValidationError("Each node requires a non-empty 'id'.")

        step_type = str(payload.get("step_type", "")).strip()
        if not step_type:
            raise TrajectoryValidationError(f"Node '{node_id}' requires a non-empty 'step_type'.")

        tags = payload.get("invariant_tags", ())
        if not isinstance(tags, (list, tuple)):
            raise TrajectoryValidationError(f"Node '{node_id}' has invalid 'invariant_tags'.")

        normalized_tags: list[str] = []
        seen: set[str] = set()
        for raw in tags:
            tag = str(raw).strip()
            if not tag or tag in seen:
                continue
            normalized_tags.append(tag)
            seen.add(tag)

        risk_weight = float(payload.get("risk_weight", 0.0))
        if not 0.0 <= risk_weight <= 1.0:
            raise TrajectoryValidationError(
                f"Node '{node_id}' has risk_weight={risk_weight}, expected a value between 0.0 and 1.0."
            )

        return cls(
            id=node_id,
            step_type=step_type,
            reversible=bool(payload.get("reversible", False)),
            checkpoint=bool(payload.get("checkpoint", False)),
            invariant_tags=tuple(normalized_tags),
            risk_weight=risk_weight,
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TrajectoryEdge:
    source: str
    target: str

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TrajectoryEdge":
        source = str(payload.get("source", "")).strip()
        target = str(payload.get("target", "")).strip()
        if not source or not target:
            raise TrajectoryValidationError("Each edge requires non-empty 'source' and 'target'.")
        return cls(source=source, target=target)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TrajectorySpec:
    nodes: tuple[TrajectoryNode, ...]
    edges: tuple[TrajectoryEdge, ...]
    plan_id: str = "unnamed-plan"

    @classmethod
    def from_dict(cls, payload: dict[str, Any]) -> "TrajectorySpec":
        raw_nodes = payload.get("nodes")
        raw_edges = payload.get("edges")
        if not isinstance(raw_nodes, list) or not raw_nodes:
            raise TrajectoryValidationError("Trajectory payload requires a non-empty 'nodes' list.")
        if not isinstance(raw_edges, list):
            raise TrajectoryValidationError("Trajectory payload requires an 'edges' list.")

        nodes = tuple(TrajectoryNode.from_dict(node) for node in raw_nodes)
        edges = tuple(TrajectoryEdge.from_dict(edge) for edge in raw_edges)
        plan_id = str(payload.get("plan_id", "unnamed-plan")).strip() or "unnamed-plan"
        spec = cls(nodes=nodes, edges=edges, plan_id=plan_id)
        spec.validate()
        return spec

    def validate(self) -> None:
        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            raise TrajectoryValidationError("Node ids must be unique.")

        known_nodes = set(node_ids)
        seen_edges: set[tuple[str, str]] = set()
        for edge in self.edges:
            if edge.source not in known_nodes or edge.target not in known_nodes:
                raise TrajectoryValidationError(
                    f"Edge '{edge.source} -> {edge.target}' references a missing node."
                )
            if edge.source == edge.target:
                raise TrajectoryValidationError(
                    f"Edge '{edge.source} -> {edge.target}' must not self-loop."
                )
            edge_key = (edge.source, edge.target)
            if edge_key in seen_edges:
                raise TrajectoryValidationError(f"Duplicate edge '{edge.source} -> {edge.target}'.")
            seen_edges.add(edge_key)

        roots = self.roots()
        if not roots:
            raise TrajectoryValidationError("Trajectory must contain at least one root node.")

        sinks = self.sinks()
        if not sinks:
            raise TrajectoryValidationError("Trajectory must contain at least one sink node.")

    def to_dict(self) -> dict[str, Any]:
        return {
            "plan_id": self.plan_id,
            "nodes": [node.to_dict() for node in self.nodes],
            "edges": [edge.to_dict() for edge in self.edges],
        }

    def node_map(self) -> dict[str, TrajectoryNode]:
        return {node.id: node for node in self.nodes}

    def outgoing_map(self) -> dict[str, tuple[str, ...]]:
        mapping = {node.id: [] for node in self.nodes}
        for edge in self.edges:
            mapping[edge.source].append(edge.target)
        return {key: tuple(value) for key, value in mapping.items()}

    def incoming_map(self) -> dict[str, tuple[str, ...]]:
        mapping = {node.id: [] for node in self.nodes}
        for edge in self.edges:
            mapping[edge.target].append(edge.source)
        return {key: tuple(value) for key, value in mapping.items()}

    def roots(self) -> tuple[str, ...]:
        incoming = self.incoming_map()
        return tuple(node_id for node_id, parents in incoming.items() if not parents)

    def sinks(self) -> tuple[str, ...]:
        outgoing = self.outgoing_map()
        return tuple(node_id for node_id, children in outgoing.items() if not children)

    def topological_order(self) -> tuple[str, ...] | None:
        incoming = {node_id: len(parents) for node_id, parents in self.incoming_map().items()}
        outgoing = self.outgoing_map()
        queue = deque(sorted(node_id for node_id, degree in incoming.items() if degree == 0))
        ordered: list[str] = []

        while queue:
            node_id = queue.popleft()
            ordered.append(node_id)
            for child in outgoing[node_id]:
                incoming[child] -= 1
                if incoming[child] == 0:
                    queue.append(child)

        if len(ordered) != len(self.nodes):
            return None
        return tuple(ordered)

    def descendants_of(self, node_id: str) -> tuple[str, ...]:
        outgoing = self.outgoing_map()
        visited: set[str] = set()
        queue = deque(outgoing[node_id])
        while queue:
            current = queue.popleft()
            if current in visited:
                continue
            visited.add(current)
            queue.extend(outgoing[current])
        return tuple(sorted(visited))

    def checkpoint_count(self) -> int:
        return sum(1 for node in self.nodes if node.checkpoint)


def load_trajectory_file(path: str | Path) -> TrajectorySpec:
    payload_path = Path(path).resolve()
    with payload_path.open("r", encoding="utf-8") as handle:
        payload = json.load(handle)
    if not isinstance(payload, dict):
        raise TrajectoryValidationError(f"Expected a JSON object in {payload_path}")
    return TrajectorySpec.from_dict(payload)
