from __future__ import annotations

from collections import deque
from dataclasses import asdict, dataclass
from typing import Any

from .trajectory import TrajectorySpec


@dataclass(frozen=True)
class PropagationMetrics:
    score: float
    reachable_fraction: float
    terminal_fraction: float
    connectivity_fraction: float
    branching_penalty: float
    irreversible_exposure: float
    pre_checkpoint_exposure: float
    disconnected_nodes: tuple[str, ...]
    overloaded_branches: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_propagation_metrics(spec: TrajectorySpec) -> PropagationMetrics:
    node_map = spec.node_map()
    outgoing = spec.outgoing_map()
    incoming = spec.incoming_map()
    node_count = len(spec.nodes)

    reachable = _walk_forward(spec.roots(), outgoing)
    can_reach_terminal = _walk_backward(spec.sinks(), incoming)
    disconnected_nodes = tuple(
        node_id
        for node_id in node_map
        if node_id not in reachable or node_id not in can_reach_terminal
    )

    overloaded_branches = tuple(
        node_id for node_id, children in outgoing.items() if len(children) > 2
    )

    total_risk = sum(node.risk_weight for node in spec.nodes) or 1.0
    weighted_exposure = 0.0
    for node in spec.nodes:
        descendant_factor = len(spec.descendants_of(node.id)) / max(1, node_count - 1)
        reversibility_factor = 1.0 if not node.reversible else 0.35
        weighted_exposure += node.risk_weight * descendant_factor * reversibility_factor
    irreversible_exposure = min(1.0, weighted_exposure / total_risk)

    topo_order = spec.topological_order() or tuple(node.id for node in spec.nodes)
    order_index = {node_id: index for index, node_id in enumerate(topo_order)}
    checkpoint_positions = [
        order_index[node.id] for node in spec.nodes if node.checkpoint and node.id in order_index
    ]
    if checkpoint_positions:
        first_checkpoint_index = min(checkpoint_positions)
        pre_checkpoint_exposure = sum(
            node.risk_weight
            for node in spec.nodes
            if not node.reversible and order_index.get(node.id, 0) < first_checkpoint_index
        ) / total_risk
    else:
        pre_checkpoint_exposure = sum(
            node.risk_weight for node in spec.nodes if not node.reversible
        ) / total_risk

    reachable_fraction = len(reachable) / node_count
    terminal_fraction = len(can_reach_terminal) / node_count
    connectivity_fraction = 1.0 - (len(disconnected_nodes) / node_count)
    branching_penalty = len(overloaded_branches) / node_count

    score = 100.0 * max(
        0.0,
        0.30 * reachable_fraction
        + 0.20 * terminal_fraction
        + 0.15 * connectivity_fraction
        + 0.10 * (1.0 - branching_penalty)
        + 0.10 * (1.0 - irreversible_exposure)
        + 0.15 * (1.0 - min(1.0, pre_checkpoint_exposure)),
    )

    return PropagationMetrics(
        score=round(score, 2),
        reachable_fraction=round(reachable_fraction, 4),
        terminal_fraction=round(terminal_fraction, 4),
        connectivity_fraction=round(connectivity_fraction, 4),
        branching_penalty=round(branching_penalty, 4),
        irreversible_exposure=round(irreversible_exposure, 4),
        pre_checkpoint_exposure=round(pre_checkpoint_exposure, 4),
        disconnected_nodes=disconnected_nodes,
        overloaded_branches=overloaded_branches,
    )


def _walk_forward(start_nodes: tuple[str, ...], outgoing: dict[str, tuple[str, ...]]) -> set[str]:
    visited: set[str] = set()
    queue = deque(start_nodes)
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        queue.extend(outgoing[current])
    return visited


def _walk_backward(start_nodes: tuple[str, ...], incoming: dict[str, tuple[str, ...]]) -> set[str]:
    visited: set[str] = set()
    queue = deque(start_nodes)
    while queue:
        current = queue.popleft()
        if current in visited:
            continue
        visited.add(current)
        queue.extend(incoming[current])
    return visited
