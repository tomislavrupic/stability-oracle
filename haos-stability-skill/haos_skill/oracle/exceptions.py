from __future__ import annotations

from ..safety import SkillError


class OracleInputError(SkillError):
    """Raised when Oracle Engine input does not satisfy the public contract."""


class OracleStateValidationError(OracleInputError):
    """Raised when a State payload cannot be validated or coerced safely."""


class OraclePerturbationError(OracleInputError):
    """Raised when a Perturbation payload cannot be validated or applied safely."""
