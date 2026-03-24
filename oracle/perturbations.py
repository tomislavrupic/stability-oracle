from __future__ import annotations

from dataclasses import replace

from .trajectory import TrajectoryEdge, TrajectoryNode, TrajectorySpec


def drop_node(spec: TrajectorySpec, node_id: str, reconnect: bool = False) -> TrajectorySpec:
    node_map = spec.node_map()
    if node_id not in node_map:
        raise ValueError(f"Unknown node '{node_id}'.")

    remaining_nodes = tuple(node for node in spec.nodes if node.id != node_id)
    incoming = [edge.source for edge in spec.edges if edge.target == node_id]
    outgoing = [edge.target for edge in spec.edges if edge.source == node_id]
    remaining_edges = [
        edge for edge in spec.edges if edge.source != node_id and edge.target != node_id
    ]

    if reconnect:
        seen = {(edge.source, edge.target) for edge in remaining_edges}
        for source in incoming:
            for target in outgoing:
                if source == target:
                    continue
                edge_key = (source, target)
                if edge_key in seen:
                    continue
                remaining_edges.append(TrajectoryEdge(source=source, target=target))
                seen.add(edge_key)

    perturbed = TrajectorySpec(
        nodes=remaining_nodes,
        edges=tuple(remaining_edges),
        plan_id=f"{spec.plan_id}::drop:{node_id}",
    )
    perturbed.validate()
    return perturbed


def mark_node_high_risk(spec: TrajectorySpec, node_id: str, delta: float = 0.2) -> TrajectorySpec:
    updated_nodes: list[TrajectoryNode] = []
    for node in spec.nodes:
        if node.id == node_id:
            updated_nodes.append(replace(node, risk_weight=min(1.0, node.risk_weight + delta)))
        else:
            updated_nodes.append(node)
    return TrajectorySpec(nodes=tuple(updated_nodes), edges=spec.edges, plan_id=spec.plan_id)
