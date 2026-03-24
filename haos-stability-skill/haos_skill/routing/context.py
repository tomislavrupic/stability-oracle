from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from typing import Any, Dict, Mapping, Optional, Union


class OracleRoute(str, Enum):
    PHYSICAL = "PHYSICAL"
    LOGICAL = "LOGICAL"
    FOUNDATIONAL = "FOUNDATIONAL"
    UNKNOWN = "UNKNOWN"


@dataclass(frozen=True)
class RoutingContext:
    candidate_id: Optional[str] = None
    domain_hint: Optional[str] = None
    uncertainty_level: Optional[float] = None
    requires_empirical_search: bool = False
    requires_structural_stability: bool = False
    requires_foundational_check: bool = False
    prior_route: Optional[OracleRoute] = None
    notes: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        candidate_id = _normalize_optional_string(self.candidate_id)
        domain_hint = _normalize_domain_hint(self.domain_hint)
        uncertainty_level = _normalize_optional_unit_interval(
            self.uncertainty_level,
            "uncertainty_level",
        )
        prior_route = _normalize_optional_route(self.prior_route)
        notes = _normalize_notes(self.notes)

        object.__setattr__(self, "candidate_id", candidate_id)
        object.__setattr__(self, "domain_hint", domain_hint)
        object.__setattr__(self, "uncertainty_level", uncertainty_level)
        object.__setattr__(self, "requires_empirical_search", bool(self.requires_empirical_search))
        object.__setattr__(self, "requires_structural_stability", bool(self.requires_structural_stability))
        object.__setattr__(self, "requires_foundational_check", bool(self.requires_foundational_check))
        object.__setattr__(self, "prior_route", prior_route)
        object.__setattr__(self, "notes", notes)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "RoutingContext":
        if not isinstance(payload, Mapping):
            raise TypeError("routing context payload must be a mapping")
        return cls(
            candidate_id=payload.get("candidate_id"),
            domain_hint=payload.get("domain_hint"),
            uncertainty_level=payload.get("uncertainty_level"),
            requires_empirical_search=payload.get("requires_empirical_search", False),
            requires_structural_stability=payload.get("requires_structural_stability", False),
            requires_foundational_check=payload.get("requires_foundational_check", False),
            prior_route=payload.get("prior_route"),
            notes=payload.get("notes"),
        )

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "candidate_id": self.candidate_id,
            "domain_hint": self.domain_hint,
            "uncertainty_level": self.uncertainty_level,
            "requires_empirical_search": self.requires_empirical_search,
            "requires_structural_stability": self.requires_structural_stability,
            "requires_foundational_check": self.requires_foundational_check,
            "prior_route": self.prior_route.value if self.prior_route is not None else None,
            "notes": None if self.notes is None else dict(self.notes),
        }
        return payload


@dataclass(frozen=True)
class RouteDecision:
    selected_route: OracleRoute
    confidence: float
    rationale: str
    policy_version: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "selected_route", _normalize_route(self.selected_route))
        object.__setattr__(self, "confidence", _normalize_unit_interval(self.confidence, "confidence"))
        rationale = str(self.rationale).strip()
        if not rationale:
            raise ValueError("rationale must be a non-empty string")
        policy_version = str(self.policy_version).strip()
        if not policy_version:
            raise ValueError("policy_version must be a non-empty string")
        object.__setattr__(self, "rationale", rationale)
        object.__setattr__(self, "policy_version", policy_version)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "selected_route": self.selected_route.value,
            "confidence": self.confidence,
            "rationale": self.rationale,
            "policy_version": self.policy_version,
        }


@dataclass(frozen=True)
class RouteDispatchResult:
    status: str
    route: OracleRoute
    message: str
    implemented: bool
    decision: RouteDecision
    result: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        status = str(self.status).strip().lower()
        if status not in {"ok", "stub", "error"}:
            raise ValueError("status must be one of: ok, stub, error")
        message = str(self.message).strip()
        if not message:
            raise ValueError("message must be a non-empty string")
        if self.result is not None and not isinstance(self.result, Mapping):
            raise TypeError("result must be a mapping when provided")
        object.__setattr__(self, "status", status)
        object.__setattr__(self, "route", _normalize_route(self.route))
        object.__setattr__(self, "message", message)
        object.__setattr__(self, "implemented", bool(self.implemented))
        object.__setattr__(self, "result", None if self.result is None else dict(self.result))

    def to_dict(self) -> Dict[str, Any]:
        payload: Dict[str, Any] = {
            "status": self.status,
            "route": self.route.value,
            "message": self.message,
            "implemented": self.implemented,
            "decision": self.decision.to_dict(),
        }
        if self.result is not None:
            payload["result"] = dict(self.result)
        return payload


RoutingContextLike = Union[RoutingContext, Mapping[str, Any]]


def coerce_routing_context(value: RoutingContextLike) -> RoutingContext:
    if isinstance(value, RoutingContext):
        return value
    return RoutingContext.from_dict(value)


def _normalize_optional_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_domain_hint(value: Any) -> Optional[str]:
    normalized = _normalize_optional_string(value)
    if normalized is None:
        return None
    return normalized.lower()


def _normalize_optional_unit_interval(value: Any, field_name: str) -> Optional[float]:
    if value is None:
        return None
    return _normalize_unit_interval(value, field_name)


def _normalize_unit_interval(value: Any, field_name: str) -> float:
    numeric = round(float(value), 4)
    if not 0.0 <= numeric <= 1.0:
        raise ValueError("%s must be within [0.0, 1.0]" % field_name)
    return numeric


def _normalize_optional_route(value: Any) -> Optional[OracleRoute]:
    if value is None:
        return None
    return _normalize_route(value)


def _normalize_route(value: Any) -> OracleRoute:
    if isinstance(value, OracleRoute):
        return value
    normalized = str(value).strip().upper()
    try:
        return OracleRoute(normalized)
    except ValueError as exc:
        raise ValueError("unsupported route label: %s" % value) from exc


def _normalize_notes(value: Any) -> Optional[Dict[str, Any]]:
    if value is None:
        return None
    if not isinstance(value, Mapping):
        raise TypeError("notes must be a mapping when provided")
    try:
        normalized = json.loads(json.dumps(value, sort_keys=True, ensure_ascii=True))
    except (TypeError, ValueError) as exc:
        raise TypeError("notes must be JSON-serializable") from exc
    if not isinstance(normalized, dict):
        raise TypeError("notes must serialize to a JSON object")
    return normalized
