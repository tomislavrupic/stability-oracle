from __future__ import annotations

from .classifier import PolicyConfig
from ..state_spec import OracleResult


def explain_result(result: OracleResult, config: PolicyConfig | None = None) -> str:
    """
    Convert a bounded oracle result into a short deterministic explanation.
    """

    resolved_config = config or PolicyConfig.balanced()
    values = tuple(result.normalized_vector.values())
    minimum = min(values)
    spread = round(max(values) - minimum, 4)
    floor_triggered = minimum < resolved_config.floor_threshold

    if result.classification == "stable":
        return "stable because all normalized dimensions stayed above threshold and spread remained bounded"
    if result.classification == "marginal":
        return "marginal because the survivability floor held but coherence was uneven"
    if floor_triggered:
        return "unstable because at least one core dimension fell below the survivability floor"
    if spread > resolved_config.stable_spread_threshold:
        return "unstable because metric imbalance exceeded the bounded spread band"
    return "unstable because global coherence fell below the policy band"
