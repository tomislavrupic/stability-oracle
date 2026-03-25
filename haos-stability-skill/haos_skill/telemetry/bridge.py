from __future__ import annotations

from typing import Any, Mapping

from ..state_spec import State
from .contracts import InvalidTelemetry, TelemetrySequence, validate_sequence


class TelemetryBridgeError(InvalidTelemetry):
    """Raised when telemetry cannot be bridged safely into a state transition."""


def telemetry_to_state_transition(seq: TelemetrySequence) -> tuple[dict[str, Any], dict[str, Any]]:
    """
    Convert a HAOS-shaped telemetry sequence back into a minimal state transition.

    This bridge is intentionally narrow. It only works for telemetry that carries
    an explicit state-pair bridge payload from the HAOS adapter.
    """

    validate_sequence(seq)
    adapter_kind = seq.metadata.get("adapter")
    if adapter_kind == "haos_state_pair_v1":
        if len(seq.frames) != 2:
            raise TelemetryBridgeError("telemetry bridge requires exactly two frames for haos_state_pair_v1")
    elif adapter_kind == "agent_trajectory_v1":
        if len(seq.frames) < 2:
            raise TelemetryBridgeError("telemetry bridge requires at least two frames for agent_trajectory_v1")
    else:
        raise TelemetryBridgeError("telemetry bridge only supports haos_state_pair_v1 and agent_trajectory_v1 sequences")

    bridge_payload = seq.metadata.get("bridge_state_transition")
    if not isinstance(bridge_payload, Mapping):
        raise TelemetryBridgeError("telemetry sequence is missing bridge_state_transition metadata")

    before_state = _coerce_state_payload(bridge_payload.get("before_state"), "before_state")
    after_state = _coerce_state_payload(bridge_payload.get("after_state"), "after_state")
    return (before_state, after_state)


def _coerce_state_payload(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, Mapping):
        raise TelemetryBridgeError("%s must be a mapping" % field_name)
    state = State.from_dict(value)
    return state.to_dict()
