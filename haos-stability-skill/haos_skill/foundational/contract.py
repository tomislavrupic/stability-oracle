from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from typing import Any, Dict, Mapping, Optional, Sequence


class FoundationalDimension(str, Enum):
    CONTRADICTION_RISK = "contradiction_risk"
    COMPOSABILITY_VIOLATION = "composability_violation"
    NON_RECOVERABLE_IDENTITY_COLLAPSE = "non_recoverable_identity_collapse"
    INVALID_ABSTRACTION_CROSSING = "invalid_abstraction_crossing"


VALID_FOUNDATIONAL_CLASSIFICATIONS = (
    "admissible",
    "borderline",
    "inadmissible",
    "unavailable",
)
DEFAULT_DIMENSIONS = (
    FoundationalDimension.CONTRADICTION_RISK,
    FoundationalDimension.COMPOSABILITY_VIOLATION,
    FoundationalDimension.NON_RECOVERABLE_IDENTITY_COLLAPSE,
    FoundationalDimension.INVALID_ABSTRACTION_CROSSING,
)


@dataclass(frozen=True)
class FoundationalCheck:
    """
    Contract for what a future foundational route is allowed to inspect.
    """

    candidate_id: Optional[str] = None
    dimensions: tuple[FoundationalDimension, ...] = DEFAULT_DIMENSIONS
    notes: Optional[Dict[str, Any]] = None

    def __post_init__(self) -> None:
        candidate_id = _normalize_optional_string(self.candidate_id)
        dimensions = _normalize_dimensions(self.dimensions)
        notes = _normalize_notes(self.notes)

        object.__setattr__(self, "candidate_id", candidate_id)
        object.__setattr__(self, "dimensions", dimensions)
        object.__setattr__(self, "notes", notes)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FoundationalCheck":
        if not isinstance(payload, Mapping):
            raise TypeError("foundational check payload must be a mapping")
        return cls(
            candidate_id=payload.get("candidate_id"),
            dimensions=tuple(payload.get("dimensions", DEFAULT_DIMENSIONS)),
            notes=payload.get("notes"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "candidate_id": self.candidate_id,
            "dimensions": [dimension.value for dimension in self.dimensions],
            "notes": None if self.notes is None else dict(self.notes),
        }


@dataclass(frozen=True)
class FoundationalSignals:
    contradiction_risk: float
    composability_violation: float
    non_recoverable_identity_collapse: float
    invalid_abstraction_crossing: float

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "contradiction_risk",
            _normalize_unit_interval(self.contradiction_risk, "contradiction_risk"),
        )
        object.__setattr__(
            self,
            "composability_violation",
            _normalize_unit_interval(self.composability_violation, "composability_violation"),
        )
        object.__setattr__(
            self,
            "non_recoverable_identity_collapse",
            _normalize_unit_interval(
                self.non_recoverable_identity_collapse,
                "non_recoverable_identity_collapse",
            ),
        )
        object.__setattr__(
            self,
            "invalid_abstraction_crossing",
            _normalize_unit_interval(
                self.invalid_abstraction_crossing,
                "invalid_abstraction_crossing",
            ),
        )

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FoundationalSignals":
        if not isinstance(payload, Mapping):
            raise TypeError("foundational signals payload must be a mapping")
        return cls(
            contradiction_risk=payload["contradiction_risk"],
            composability_violation=payload["composability_violation"],
            non_recoverable_identity_collapse=payload["non_recoverable_identity_collapse"],
            invalid_abstraction_crossing=payload["invalid_abstraction_crossing"],
        )

    def to_dict(self) -> Dict[str, float]:
        return {
            "contradiction_risk": self.contradiction_risk,
            "composability_violation": self.composability_violation,
            "non_recoverable_identity_collapse": self.non_recoverable_identity_collapse,
            "invalid_abstraction_crossing": self.invalid_abstraction_crossing,
        }


@dataclass(frozen=True)
class FoundationalResult:
    classification: str
    signals: FoundationalSignals
    policy_version: str
    summary: str

    def __post_init__(self) -> None:
        classification = str(self.classification).strip().lower()
        if classification not in VALID_FOUNDATIONAL_CLASSIFICATIONS:
            raise ValueError(
                "classification must be one of %s"
                % ", ".join(VALID_FOUNDATIONAL_CLASSIFICATIONS)
            )
        policy_version = str(self.policy_version).strip()
        summary = str(self.summary).strip()
        if not policy_version:
            raise ValueError("policy_version must be a non-empty string")
        if not summary:
            raise ValueError("summary must be a non-empty string")
        object.__setattr__(self, "classification", classification)
        object.__setattr__(self, "policy_version", policy_version)
        object.__setattr__(self, "summary", summary)

    @classmethod
    def from_dict(cls, payload: Mapping[str, Any]) -> "FoundationalResult":
        if not isinstance(payload, Mapping):
            raise TypeError("foundational result payload must be a mapping")
        return cls(
            classification=payload["classification"],
            signals=FoundationalSignals.from_dict(payload["signals"]),
            policy_version=payload["policy_version"],
            summary=payload["summary"],
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "classification": self.classification,
            "signals": self.signals.to_dict(),
            "policy_version": self.policy_version,
            "summary": self.summary,
        }


def _normalize_optional_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    normalized = str(value).strip()
    return normalized or None


def _normalize_dimensions(value: Sequence[FoundationalDimension | str]) -> tuple[FoundationalDimension, ...]:
    if not isinstance(value, Sequence) or isinstance(value, (str, bytes, bytearray)):
        raise TypeError("dimensions must be a sequence")
    normalized = []
    for item in value:
        if isinstance(item, FoundationalDimension):
            dimension = item
        else:
            candidate = str(item).strip().lower()
            try:
                dimension = FoundationalDimension(candidate)
            except ValueError as exc:
                raise ValueError("unsupported foundational dimension: %s" % item) from exc
        if dimension not in normalized:
            normalized.append(dimension)
    if not normalized:
        raise ValueError("dimensions must contain at least one foundational dimension")
    return tuple(normalized)


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


def _normalize_unit_interval(value: Any, field_name: str) -> float:
    numeric = round(float(value), 4)
    if not 0.0 <= numeric <= 1.0:
        raise ValueError("%s must be within [0.0, 1.0]" % field_name)
    return numeric
