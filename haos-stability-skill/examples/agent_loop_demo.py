from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Sequence

from haos_skill import (
    CausalDeformationMetric,
    GeometricIntegrityMetric,
    MetricRegistry,
    StabilityClassifier,
    StabilityMetrics,
    StructuralRetentionMetric,
    TemporalConsistencyMetric,
    State,
)


STRONG_MARGINAL_CONFIDENCE = 0.55
STRONG_MARGINAL_COHERENCE = 0.70
CLASSIFICATION_PRIORITY = {"unstable": 0, "marginal": 1, "stable": 2}


@dataclass(frozen=True)
class CandidateAction:
    name: str
    description: str
    transform: Callable[[State], State]


@dataclass(frozen=True)
class CandidateEvaluation:
    action_name: str
    description: str
    classification: str
    coherence_score: float
    confidence: float
    admissible: bool
    after_state: State


def run_demo() -> dict[str, object]:
    classifier = StabilityClassifier()
    registry = _build_registry()
    current = _initial_state()
    accepted_steps: list[dict[str, object]] = []

    for step_number, actions in enumerate(_candidate_plan(), start=1):
        evaluations = [
            _evaluate_candidate(current, action, classifier=classifier, registry=registry)
            for action in actions
        ]
        admissible = [candidate for candidate in evaluations if candidate.admissible]
        if not admissible:
            break

        selected = max(
            admissible,
            key=lambda candidate: (
                CLASSIFICATION_PRIORITY[candidate.classification],
                candidate.confidence,
                candidate.coherence_score,
            ),
        )
        current = selected.after_state
        accepted_steps.append(
            {
                "step": step_number,
                "selected": _candidate_to_dict(selected),
                "rejected": [
                    _candidate_to_dict(candidate)
                    for candidate in evaluations
                    if candidate.action_name != selected.action_name
                ],
                "state": current.to_dict(),
            }
        )

    return {
        "policy_version": classifier.config.policy_version,
        "initial_state": _initial_state().to_dict(),
        "steps": accepted_steps,
        "final_state": current.to_dict(),
        "interpretation": _build_interpretation(_initial_state(), current, accepted_steps),
    }


def format_demo(summary: dict[str, object]) -> str:
    lines = [
        "Stability Oracle Agent Loop Demo",
        "Policy: %s" % summary["policy_version"],
        "",
    ]

    initial_state = State.from_dict(summary["initial_state"])
    final_state = State.from_dict(summary["final_state"])
    lines.extend(
        [
            "Initial state: nodes=%d edges=%d"
            % (len(initial_state.nodes), len(initial_state.edges)),
            "",
        ]
    )

    for step in summary["steps"]:
        selected = step["selected"]
        rejected = step["rejected"]
        lines.append("Step %d candidates" % step["step"])
        lines.append("action                    verdict   coh     conf    decision")
        rows = [selected] + rejected
        for candidate in rows:
            if candidate["action_name"] == selected["action_name"]:
                decision = "selected"
            elif candidate["admissible"]:
                decision = "admit"
            else:
                decision = "reject"
            lines.append(
                "%-24s %-9s %-7.4f %-7.4f %s"
                % (
                    candidate["action_name"][:24],
                    candidate["classification"],
                    candidate["coherence_score"],
                    candidate["confidence"],
                    decision,
                )
            )
        lines.append("selected: %s" % selected["description"])
        lines.append("")

    lines.append("Accepted trajectory")
    lines.append("step action                    verdict   coh     conf    nodes edges")
    for step in summary["steps"]:
        selected = step["selected"]
        state = State.from_dict(step["state"])
        lines.append(
            "%-4d %-24s %-9s %-7.4f %-7.4f %-5d %-5d"
            % (
                step["step"],
                selected["action_name"][:24],
                selected["classification"],
                selected["coherence_score"],
                selected["confidence"],
                len(state.nodes),
                len(state.edges),
            )
        )

    lines.extend(
        [
            "",
            "Final state: nodes=%d edges=%d"
            % (len(final_state.nodes), len(final_state.edges)),
            "Interpretation: %s" % summary["interpretation"],
        ]
    )
    return "\n".join(lines)


def main() -> None:
    print(format_demo(run_demo()))


def _build_registry() -> MetricRegistry:
    return MetricRegistry(
        (
            StructuralRetentionMetric(),
            TemporalConsistencyMetric(),
            CausalDeformationMetric(),
            GeometricIntegrityMetric(),
        )
    )


def _initial_state() -> State:
    return State(
        nodes=(1, 2, 3),
        edges=((1, 2), (2, 3)),
        timestamps={1: 0.0, 2: 1.0, 3: 2.0},
    )


def _candidate_plan() -> tuple[tuple[CandidateAction, ...], ...]:
    return (
        (
            CandidateAction(
                name="restore_sink",
                description="Restore the downstream sink and reconnect the corridor.",
                transform=lambda state: _mutate_state(
                    state,
                    add_nodes=(4,),
                    add_edges=((3, 4),),
                    timestamp_updates={4: 3.0},
                ),
            ),
            CandidateAction(
                name="collapse_bridge",
                description="Drop the bridge node and leave the corridor disconnected.",
                transform=lambda state: _mutate_state(
                    state,
                    remove_nodes=(2,),
                ),
            ),
            CandidateAction(
                name="invert_temporal_order",
                description="Keep the topology but invert the ordering signal.",
                transform=_invert_temporal_order,
            ),
        ),
        (
            CandidateAction(
                name="extend_to_archive",
                description="Extend the corridor to an archive node.",
                transform=lambda state: _mutate_state(
                    state,
                    add_nodes=(5,),
                    add_edges=((4, 5),),
                    timestamp_updates={5: 4.0},
                ),
            ),
            CandidateAction(
                name="truncate_corridor",
                description="Strip the middle span and collapse the downstream branch.",
                transform=lambda state: _mutate_state(
                    state,
                    remove_nodes=(3, 4),
                ),
            ),
            CandidateAction(
                name="scramble_temporal_order",
                description="Preserve the graph but scramble event ordering.",
                transform=_scramble_temporal_order,
            ),
        ),
        (
            CandidateAction(
                name="add_redundant_bridge",
                description="Add a bypass edge so the corridor keeps a second route.",
                transform=lambda state: _mutate_state(
                    state,
                    add_edges=((2, 4),),
                ),
            ),
            CandidateAction(
                name="collapse_middle_span",
                description="Remove the middle span and leave only the endpoints intact.",
                transform=lambda state: _mutate_state(
                    state,
                    remove_nodes=(3, 4),
                ),
            ),
            CandidateAction(
                name="reverse_temporal_axis",
                description="Keep the topology but reverse the entire time axis.",
                transform=_reverse_temporal_axis,
            ),
        ),
    )


def _evaluate_candidate(
    before: State,
    action: CandidateAction,
    classifier: StabilityClassifier,
    registry: MetricRegistry,
) -> CandidateEvaluation:
    after = action.transform(before)
    metrics = StabilityMetrics(**registry.compute_all(before, after))
    result = classifier.evaluate(metrics)
    return CandidateEvaluation(
        action_name=action.name,
        description=action.description,
        classification=result.classification,
        coherence_score=result.coherence_score,
        confidence=result.confidence,
        admissible=_is_admissible(result),
        after_state=after,
    )


def _is_admissible(result: object) -> bool:
    classification = getattr(result, "classification")
    if classification == "stable":
        return True
    return (
        classification == "marginal"
        and getattr(result, "confidence") >= STRONG_MARGINAL_CONFIDENCE
        and getattr(result, "coherence_score") >= STRONG_MARGINAL_COHERENCE
    )


def _candidate_to_dict(candidate: CandidateEvaluation) -> dict[str, object]:
    return {
        "action_name": candidate.action_name,
        "description": candidate.description,
        "classification": candidate.classification,
        "coherence_score": candidate.coherence_score,
        "confidence": candidate.confidence,
        "admissible": candidate.admissible,
    }


def _build_interpretation(
    initial: State,
    final: State,
    accepted_steps: Sequence[dict[str, object]],
) -> str:
    selected_names = [
        step["selected"]["action_name"].replace("_", " ")
        for step in accepted_steps
    ]
    actions = ", ".join(selected_names)
    return (
        "Started as a brittle %d-node corridor with %d edges. "
        "Accepted moves were %s. "
        "The loop ended with %d nodes and %d edges, restoring downstream capacity "
        "and adding one redundant route."
        % (
            len(initial.nodes),
            len(initial.edges),
            actions,
            len(final.nodes),
            len(final.edges),
        )
    )


def _mutate_state(
    state: State,
    *,
    add_nodes: Sequence[int] = (),
    remove_nodes: Sequence[int] = (),
    add_edges: Sequence[tuple[int, int]] = (),
    remove_edges: Sequence[tuple[int, int]] = (),
    timestamp_updates: dict[int, float] | None = None,
) -> State:
    removed_nodes = set(remove_nodes)
    nodes = [node for node in state.nodes if node not in removed_nodes]
    for node in add_nodes:
        if node not in nodes:
            nodes.append(node)

    valid_nodes = set(nodes)
    removed_edges = set(remove_edges)
    edges = [
        edge
        for edge in state.edges
        if edge not in removed_edges and edge[0] in valid_nodes and edge[1] in valid_nodes
    ]
    for edge in add_edges:
        if edge[0] not in valid_nodes or edge[1] not in valid_nodes:
            raise ValueError("edge %s references an unknown node" % (edge,))
        if edge not in edges:
            edges.append(edge)

    timestamps: dict[int, float] | None
    if state.timestamps is None and timestamp_updates is None:
        timestamps = None
    else:
        timestamps = {
            node: timestamp
            for node, timestamp in (state.timestamps or {}).items()
            if node in valid_nodes
        }
        for node, timestamp in (timestamp_updates or {}).items():
            if node not in valid_nodes:
                raise ValueError("timestamp update references an unknown node: %s" % node)
            timestamps[node] = float(timestamp)

    return State(
        nodes=tuple(nodes),
        edges=tuple(edges),
        timestamps=timestamps,
    )


def _invert_temporal_order(state: State) -> State:
    if state.timestamps is None:
        return state
    ordered_nodes = tuple(state.nodes)
    size = len(ordered_nodes)
    updates = {
        node: float(size - index - 1)
        for index, node in enumerate(ordered_nodes)
    }
    return _mutate_state(state, timestamp_updates=updates)


def _scramble_temporal_order(state: State) -> State:
    if state.timestamps is None:
        return state
    ordered_nodes = tuple(state.nodes)
    scrambled = {
        node: float((len(ordered_nodes) - index - 1) * 2)
        for index, node in enumerate(ordered_nodes)
    }
    return _mutate_state(state, timestamp_updates=scrambled)


def _reverse_temporal_axis(state: State) -> State:
    if state.timestamps is None:
        return state
    ordered_nodes = tuple(state.nodes)
    updates = {
        node: float(len(ordered_nodes) - index)
        for index, node in enumerate(ordered_nodes)
    }
    return _mutate_state(state, timestamp_updates=updates)


if __name__ == "__main__":
    main()
