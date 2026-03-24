from __future__ import annotations

import hashlib
import json
from typing import Any, Mapping, MutableMapping, Sequence


MAX_INPUT_BYTES = 262144
MAX_NODES = 512
MAX_EDGES = 2048
MAX_SCAN_CASES = 64
DEFAULT_TIMEOUT_SECONDS = 2.0


class SkillError(RuntimeError):
    """Base class for controlled skill failures."""


class InputLimitError(SkillError):
    """Raised when a payload exceeds bounded skill limits."""


class SkillTimeoutError(SkillError):
    """Raised when the external oracle exceeds the hard timeout."""


class OracleExecutionError(SkillError):
    """Raised when the external oracle cannot be executed cleanly."""


class OracleProtocolError(SkillError):
    """Raised when the external oracle returns an unsupported payload."""


def canonical_json(payload: Any) -> str:
    return json.dumps(payload, separators=(",", ":"), sort_keys=True, ensure_ascii=True)


def payload_hash(payload: Any) -> str:
    digest = hashlib.sha256(canonical_json(payload).encode("utf-8"))
    return digest.hexdigest()


def normalize_timeout(timeout: Any) -> float:
    if timeout is None:
        return DEFAULT_TIMEOUT_SECONDS
    normalized = float(timeout)
    if normalized <= 0.0:
        raise InputLimitError("timeout must be greater than zero")
    return normalized


def ensure_state_spec_limits(state_spec: Mapping[str, Any]) -> None:
    if not isinstance(state_spec, Mapping):
        raise InputLimitError("state_spec must be a JSON object")

    payload_size = len(canonical_json(state_spec).encode("utf-8"))
    if payload_size > MAX_INPUT_BYTES:
        raise InputLimitError(
            "state_spec exceeds the maximum serialized size of %d bytes" % MAX_INPUT_BYTES
        )

    nodes = state_spec.get("nodes")
    if isinstance(nodes, Sequence) and not isinstance(nodes, (str, bytes, bytearray)):
        if len(nodes) > MAX_NODES:
            raise InputLimitError("state_spec exceeds the maximum node limit of %d" % MAX_NODES)

    edges = state_spec.get("edges")
    if isinstance(edges, Sequence) and not isinstance(edges, (str, bytes, bytearray)):
        if len(edges) > MAX_EDGES:
            raise InputLimitError("state_spec exceeds the maximum edge limit of %d" % MAX_EDGES)


def coerce_scan_cases(grid_spec: Any) -> list[Mapping[str, Any]]:
    if isinstance(grid_spec, Mapping):
        raw_cases = grid_spec.get("cases")
    else:
        raw_cases = grid_spec

    if not isinstance(raw_cases, Sequence) or isinstance(raw_cases, (str, bytes, bytearray)):
        raise InputLimitError("grid_spec must provide a 'cases' sequence")

    cases = list(raw_cases)
    if not cases:
        raise InputLimitError("grid_spec must contain at least one case")
    if len(cases) > MAX_SCAN_CASES:
        raise InputLimitError("grid_spec exceeds the maximum case limit of %d" % MAX_SCAN_CASES)

    normalized_cases = []
    for case in cases:
        if not isinstance(case, Mapping):
            raise InputLimitError("each scan case must be a JSON object")
        if "state_spec" not in case:
            raise InputLimitError("each scan case must include 'state_spec'")
        state_spec = case["state_spec"]
        if not isinstance(state_spec, Mapping):
            raise InputLimitError("each scan case 'state_spec' must be a JSON object")
        ensure_state_spec_limits(state_spec)
        normalized_cases.append(case)

    return normalized_cases


def coerce_unit_interval(value: Any, field_name: str) -> float:
    try:
        numeric = float(value)
    except (TypeError, ValueError) as exc:
        raise OracleProtocolError("%s must be numeric" % field_name) from exc

    if 0.0 <= numeric <= 1.0:
        return round(numeric, 4)
    if 0.0 <= numeric <= 100.0:
        return round(numeric / 100.0, 4)
    raise OracleProtocolError("%s must be within [0,1] or [0,100]" % field_name)


def bounded_round(value: float) -> float:
    return round(max(0.0, min(1.0, float(value))), 4)


def deep_copy_json_object(payload: Mapping[str, Any]) -> dict[str, Any]:
    copied = json.loads(canonical_json(payload))
    if not isinstance(copied, MutableMapping):
        raise OracleProtocolError("expected a JSON object")
    return dict(copied)
