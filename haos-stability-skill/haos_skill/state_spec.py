from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple, Union


NodeId = int
Edge = Tuple[NodeId, NodeId]
VALID_CLASSIFICATIONS = ("stable", "marginal", "unstable")
RAW_METRIC_KEYS = (
    "structural_retention",
    "temporal_consistency",
    "causal_deformation",
    "geometric_integrity",
)
NORMALIZED_METRIC_KEYS = (
    "structural_retention",
    "temporal_consistency",
    "causal_stability",
    "geometric_integrity",
)
TRACE_KEYS = (
    "input_node_count",
    "input_edge_count",
    "output_node_count",
    "output_edge_count",
    "normalized_vector",
    "coherence_score",
    "spread",
    "floor_triggered",
    "policy_version",
)


@dataclass(frozen=True)
class State:
    """
    Minimal structural state representation.

    This is the invariant contract for what the oracle consumes.
    It carries only recoverable structure and optional side channels.
    """

    nodes: Tuple[NodeId, ...]
    edges: Tuple[Edge, ...]
    features: Optional[Dict[NodeId, Any]] = None
    timestamps: Optional[Dict[NodeId, float]] = None

    def __post_init__(self) -> None:
        node_ids = tuple(_coerce_node_id(node_id, "nodes") for node_id in self.nodes)
        edge_pairs = tuple(_coerce_edge(edge) for edge in self.edges)
        feature_map = _coerce_feature_map(self.features)
        timestamp_map = _coerce_timestamp_map(self.timestamps)

        if len(node_ids) != len(set(node_ids)):
            raise ValueError("state nodes must be unique")

        known_nodes = set(node_ids)
        for source, target in edge_pairs:
            if source not in known_nodes or target not in known_nodes:
                raise ValueError("state edges must only reference known nodes")

        if feature_map is not None and not set(feature_map).issubset(known_nodes):
            raise ValueError("state features must only reference known nodes")
        if timestamp_map is not None and not set(timestamp_map).issubset(known_nodes):
            raise ValueError("state timestamps must only reference known nodes")

        object.__setattr__(self, "nodes", node_ids)
        object.__setattr__(self, "edges", edge_pairs)
        object.__setattr__(self, "features", feature_map)
        object.__setattr__(self, "timestamps", timestamp_map)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "State":
        if not isinstance(payload, Mapping):
            raise TypeError("state payload must be a mapping")

        nodes = payload.get("nodes", ())
        edges = payload.get("edges", ())
        if not isinstance(nodes, Sequence) or isinstance(nodes, (str, bytes, bytearray)):
            raise TypeError("state 'nodes' must be a sequence")
        if not isinstance(edges, Sequence) or isinstance(edges, (str, bytes, bytearray)):
            raise TypeError("state 'edges' must be a sequence")

        return cls(
            nodes=tuple(nodes),
            edges=tuple(edges),
            features=_as_optional_mapping(payload.get("features"), "features"),
            timestamps=_as_optional_mapping(payload.get("timestamps"), "timestamps"),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "nodes": list(self.nodes),
            "edges": [[source, target] for source, target in self.edges],
        }
        if self.features is not None:
            payload["features"] = {str(node_id): value for node_id, value in sorted(self.features.items())}
        if self.timestamps is not None:
            payload["timestamps"] = {
                str(node_id): timestamp for node_id, timestamp in sorted(self.timestamps.items())
            }
        return payload


@dataclass(frozen=True)
class Perturbation:
    """
    Describes a structural disturbance without implying a substrate.
    """

    node_drop: float = 0.0
    edge_drop: float = 0.0
    noise: float = 0.0
    cluster_split: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(self, "node_drop", _coerce_unit_interval(self.node_drop, "node_drop"))
        object.__setattr__(self, "edge_drop", _coerce_unit_interval(self.edge_drop, "edge_drop"))
        object.__setattr__(self, "noise", _coerce_unit_interval(self.noise, "noise"))
        object.__setattr__(self, "cluster_split", bool(self.cluster_split))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "Perturbation":
        if not isinstance(payload, Mapping):
            raise TypeError("perturbation payload must be a mapping")
        return cls(
            node_drop=payload.get("node_drop", 0.0),
            edge_drop=payload.get("edge_drop", 0.0),
            noise=payload.get("noise", 0.0),
            cluster_split=payload.get("cluster_split", False),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "node_drop": self.node_drop,
            "edge_drop": self.edge_drop,
            "noise": self.noise,
            "cluster_split": self.cluster_split,
        }


@dataclass(frozen=True)
class StabilityMetrics:
    structural_retention: float
    temporal_consistency: float
    causal_deformation: float
    geometric_integrity: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "structural_retention",
            _coerce_unit_interval(self.structural_retention, "structural_retention"),
        )
        object.__setattr__(
            self,
            "temporal_consistency",
            _coerce_unit_interval(self.temporal_consistency, "temporal_consistency"),
        )
        object.__setattr__(
            self,
            "causal_deformation",
            _coerce_unit_interval(self.causal_deformation, "causal_deformation"),
        )
        object.__setattr__(
            self,
            "geometric_integrity",
            _coerce_unit_interval(self.geometric_integrity, "geometric_integrity"),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "StabilityMetrics":
        if not isinstance(payload, Mapping):
            raise TypeError("metrics payload must be a mapping")
        return cls(
            structural_retention=payload["structural_retention"],
            temporal_consistency=payload["temporal_consistency"],
            causal_deformation=payload["causal_deformation"],
            geometric_integrity=payload["geometric_integrity"],
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "structural_retention": self.structural_retention,
            "temporal_consistency": self.temporal_consistency,
            "causal_deformation": self.causal_deformation,
            "geometric_integrity": self.geometric_integrity,
        }


@dataclass(frozen=True)
class OracleResult:
    classification: str
    metrics: StabilityMetrics
    confidence: float
    coherence_score: float
    metric_vector: Dict[str, float]
    normalized_vector: Dict[str, float]
    policy_version: str
    trace: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        normalized = str(self.classification).strip().lower()
        if normalized not in VALID_CLASSIFICATIONS:
            raise ValueError("classification must be one of %s" % ", ".join(VALID_CLASSIFICATIONS))
        object.__setattr__(self, "classification", normalized)
        object.__setattr__(self, "confidence", _coerce_unit_interval(self.confidence, "confidence"))
        object.__setattr__(self, "coherence_score", _coerce_unit_interval(self.coherence_score, "coherence_score"))
        object.__setattr__(self, "metric_vector", _coerce_metric_vector(self.metric_vector, RAW_METRIC_KEYS))
        object.__setattr__(
            self,
            "normalized_vector",
            _coerce_metric_vector(self.normalized_vector, NORMALIZED_METRIC_KEYS),
        )
        policy_version = str(self.policy_version).strip()
        if not policy_version:
            raise ValueError("policy_version must be a non-empty string")
        object.__setattr__(self, "policy_version", policy_version)
        object.__setattr__(self, "trace", _coerce_trace_payload(self.trace))

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "OracleResult":
        if not isinstance(payload, Mapping):
            raise TypeError("oracle result payload must be a mapping")
        return cls(
            classification=payload["classification"],
            metrics=StabilityMetrics.from_dict(payload["metrics"]),
            confidence=payload["confidence"],
            coherence_score=payload["coherence_score"],
            metric_vector=_as_required_mapping(payload.get("metric_vector"), "metric_vector"),
            normalized_vector=_as_required_mapping(payload.get("normalized_vector"), "normalized_vector"),
            policy_version=payload["policy_version"],
            trace=payload.get("trace", {}),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload = {
            "classification": self.classification,
            "metrics": self.metrics.to_dict(),
            "confidence": self.confidence,
            "coherence_score": self.coherence_score,
            "metric_vector": dict(self.metric_vector),
            "normalized_vector": dict(self.normalized_vector),
            "policy_version": self.policy_version,
        }
        if self.trace:
            payload["trace"] = dict(self.trace)
        return payload


StateLike = Union[State, Mapping[str, Any]]
PerturbationLike = Union[Perturbation, Mapping[str, Any]]


def coerce_state(value: StateLike) -> State:
    if isinstance(value, State):
        return value
    return State.from_dict(value)


def coerce_state_payload(value: StateLike) -> Dict[str, Any]:
    return coerce_state(value).to_dict()


def coerce_perturbation(value: PerturbationLike) -> Perturbation:
    if isinstance(value, Perturbation):
        return value
    return Perturbation.from_dict(value)


def coerce_perturbation_payload(value: PerturbationLike) -> Dict[str, Any]:
    return coerce_perturbation(value).to_dict()


def _as_optional_mapping(value: Any, field_name: str) -> Optional[Mapping[Any, Any]]:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TypeError("%s must be a mapping when provided" % field_name)
    return value


def _as_required_mapping(value: Any, field_name: str) -> Mapping[Any, Any]:
    if not isinstance(value, Mapping):
        raise TypeError("%s must be a mapping" % field_name)
    return value


def _coerce_node_id(value: Any, field_name: str) -> NodeId:
    if isinstance(value, bool):
        raise TypeError("%s cannot contain booleans as node ids" % field_name)
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            try:
                return int(stripped)
            except ValueError:
                pass
    raise TypeError("%s must contain integer node ids" % field_name)


def _coerce_edge(value: Any) -> Edge:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise TypeError("edges must be two-item sequences")
    if len(value) != 2:
        raise ValueError("edges must contain exactly two node ids")
    return (_coerce_node_id(value[0], "edges"), _coerce_node_id(value[1], "edges"))


def _coerce_feature_map(value: Optional[Mapping[Any, Any]]) -> Optional[Dict[NodeId, Any]]:
    if value is None:
        return None
    return {_coerce_node_id(node_id, "features"): feature for node_id, feature in value.items()}


def _coerce_timestamp_map(value: Optional[Mapping[Any, Any]]) -> Optional[Dict[NodeId, float]]:
    if value is None:
        return None
    normalized: Dict[NodeId, float] = {}
    for node_id, timestamp in value.items():
        normalized[_coerce_node_id(node_id, "timestamps")] = float(timestamp)
    return normalized


def _coerce_unit_interval(value: Any, field_name: str) -> float:
    numeric = float(value)
    if not 0.0 <= numeric <= 1.0:
        raise ValueError("%s must be within [0.0, 1.0]" % field_name)
    return round(numeric, 4)


def _coerce_metric_vector(value: Mapping[Any, Any], expected_keys: Tuple[str, ...]) -> Dict[str, float]:
    normalized = {str(key): _coerce_unit_interval(metric, str(key)) for key, metric in value.items()}
    if set(normalized) != set(expected_keys):
        raise ValueError("metric vector must contain keys: %s" % ", ".join(expected_keys))
    return {key: normalized[key] for key in expected_keys}


def _coerce_trace_payload(value: Any) -> Dict[str, Any]:
    if value is None:
        return {}
    if not isinstance(value, Mapping):
        raise TypeError("trace must be a mapping")

    normalized = {str(key): raw_value for key, raw_value in value.items()}
    if not normalized:
        return {}
    if set(normalized) != set(TRACE_KEYS):
        raise ValueError("trace must contain keys: %s" % ", ".join(TRACE_KEYS))

    policy_version = str(normalized["policy_version"]).strip()
    if not policy_version:
        raise ValueError("trace.policy_version must be a non-empty string")
    floor_triggered = normalized["floor_triggered"]
    if not isinstance(floor_triggered, bool):
        raise TypeError("trace.floor_triggered must be a boolean")

    trace = {
        "input_node_count": _coerce_non_negative_int(normalized["input_node_count"], "trace.input_node_count"),
        "input_edge_count": _coerce_non_negative_int(normalized["input_edge_count"], "trace.input_edge_count"),
        "output_node_count": _coerce_non_negative_int(normalized["output_node_count"], "trace.output_node_count"),
        "output_edge_count": _coerce_non_negative_int(normalized["output_edge_count"], "trace.output_edge_count"),
        "normalized_vector": _coerce_metric_vector(
            _as_required_mapping(normalized["normalized_vector"], "trace.normalized_vector"),
            NORMALIZED_METRIC_KEYS,
        ),
        "coherence_score": _coerce_unit_interval(normalized["coherence_score"], "trace.coherence_score"),
        "spread": _coerce_unit_interval(normalized["spread"], "trace.spread"),
        "floor_triggered": floor_triggered,
        "policy_version": policy_version,
    }
    return trace


def _coerce_non_negative_int(value: Any, field_name: str) -> int:
    if isinstance(value, bool):
        raise TypeError("%s must be an integer" % field_name)
    numeric = int(value)
    if numeric < 0:
        raise ValueError("%s must be non-negative" % field_name)
    return numeric
