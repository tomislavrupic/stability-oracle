"""HAOS-IIP structural stability skill wrapper."""

from __future__ import annotations

from typing import Any


__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "SkillInputError",
    "SkillTimeoutError",
    "StabilityReport",
    "evaluate_structure",
    "load_schema",
    "scan_structure",
]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from . import skill

        return getattr(skill, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
