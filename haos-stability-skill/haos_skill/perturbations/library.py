from __future__ import annotations

from typing import Sequence

from ..state_spec import State


def copy_state(state: State) -> State:
    return State(
        nodes=tuple(state.nodes),
        edges=tuple(state.edges),
        features=None if state.features is None else dict(state.features),
        timestamps=None if state.timestamps is None else dict(state.timestamps),
    )


def drop_nodes(state: State, ratio: float) -> State:
    drop_count = _drop_count(len(state.nodes), ratio)
    if drop_count == 0:
        return copy_state(state)

    removed_nodes = set(sorted(state.nodes, reverse=True)[:drop_count])
    return rebuild_state(state, removed_nodes=removed_nodes)


def drop_edges(state: State, ratio: float) -> State:
    drop_count = _drop_count(len(state.edges), ratio)
    if drop_count == 0:
        return copy_state(state)

    removed_edges = set(sorted(state.edges, reverse=True)[:drop_count])
    return rebuild_state(state, removed_edges=removed_edges)


def split_clusters(state: State) -> State:
    ordered_nodes = tuple(sorted(state.nodes))
    if len(ordered_nodes) < 2:
        return copy_state(state)

    midpoint = len(ordered_nodes) // 2
    if midpoint == 0 or midpoint == len(ordered_nodes):
        return copy_state(state)

    left_cluster = set(ordered_nodes[:midpoint])
    right_cluster = set(ordered_nodes[midpoint:])
    removed_edges = {
        edge
        for edge in state.edges
        if (edge[0] in left_cluster and edge[1] in right_cluster)
        or (edge[0] in right_cluster and edge[1] in left_cluster)
    }
    if not removed_edges:
        return copy_state(state)
    return rebuild_state(state, removed_edges=removed_edges)


def apply_noise_passthrough(state: State, level: float) -> State:
    """
    Noise is currently treated conservatively.

    The v2 engine keeps topology and ordering intact until a deterministic
    feature-noise contract exists. This preserves metric semantics and keeps
    the perturbation layer explicit rather than speculative.
    """

    _ = level
    return copy_state(state)


def rebuild_state(
    state: State,
    *,
    removed_nodes: set[int] | None = None,
    removed_edges: set[tuple[int, int]] | None = None,
) -> State:
    removed_nodes = removed_nodes or set()
    removed_edges = removed_edges or set()

    nodes = tuple(node for node in state.nodes if node not in removed_nodes)
    valid_nodes = set(nodes)
    edges = tuple(
        edge
        for edge in state.edges
        if edge not in removed_edges and edge[0] in valid_nodes and edge[1] in valid_nodes
    )

    features = None
    if state.features is not None:
        features = {node: value for node, value in state.features.items() if node in valid_nodes}

    timestamps = None
    if state.timestamps is not None:
        timestamps = {node: value for node, value in state.timestamps.items() if node in valid_nodes}

    return State(nodes=nodes, edges=edges, features=features, timestamps=timestamps)


def _drop_count(total: int, ratio: float) -> int:
    if total <= 0 or ratio <= 0.0:
        return 0
    if ratio >= 1.0:
        return total
    return min(total, int(total * ratio))
