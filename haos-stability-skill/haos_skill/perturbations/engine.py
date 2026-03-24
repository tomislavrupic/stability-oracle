from __future__ import annotations

from .library import apply_noise_passthrough, copy_state, drop_edges, drop_nodes, split_clusters
from ..oracle.exceptions import OraclePerturbationError, OracleStateValidationError
from ..state_spec import Perturbation, State, coerce_perturbation, coerce_state


class PerturbationEngine:
    """
    Deterministic perturbation pipeline for structural state transitions.

    The transform order is fixed:
    1. node drop
    2. cluster split
    3. edge drop
    4. conservative noise passthrough
    """

    def apply(self, before: State, perturbation: Perturbation) -> State:
        state = _coerce_state_or_raise(before)
        spec = _coerce_perturbation_or_raise(perturbation)

        current = copy_state(state)
        current = drop_nodes(current, spec.node_drop)
        if spec.cluster_split:
            current = split_clusters(current)
        current = drop_edges(current, spec.edge_drop)
        if spec.noise > 0.0:
            current = apply_noise_passthrough(current, spec.noise)
        return current


def _coerce_state_or_raise(value: State) -> State:
    try:
        return coerce_state(value)
    except (TypeError, ValueError) as exc:
        raise OracleStateValidationError("invalid state payload") from exc


def _coerce_perturbation_or_raise(value: Perturbation) -> Perturbation:
    try:
        return coerce_perturbation(value)
    except (TypeError, ValueError) as exc:
        raise OraclePerturbationError("invalid perturbation payload") from exc
