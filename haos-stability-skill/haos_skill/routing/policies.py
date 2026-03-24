from __future__ import annotations

from .context import OracleRoute, RouteDecision, RoutingContext


ROUTING_POLICY_VERSION_V1 = "routing_v1_explicit_priority"


class RoutingPolicy:
    """
    Deterministic rule-based router for selecting the next oracle layer.
    """

    def __init__(self, policy_version: str = ROUTING_POLICY_VERSION_V1) -> None:
        normalized = str(policy_version).strip()
        if not normalized:
            raise ValueError("policy_version must be a non-empty string")
        self.policy_version = normalized

    def select(self, context: RoutingContext) -> RouteDecision:
        if context.requires_foundational_check:
            return RouteDecision(
                selected_route=OracleRoute.FOUNDATIONAL,
                confidence=1.0,
                rationale="requires_foundational_check",
                policy_version=self.policy_version,
            )

        if context.requires_structural_stability:
            return RouteDecision(
                selected_route=OracleRoute.LOGICAL,
                confidence=1.0,
                rationale="requires_structural_stability",
                policy_version=self.policy_version,
            )

        if context.requires_empirical_search:
            return RouteDecision(
                selected_route=OracleRoute.PHYSICAL,
                confidence=1.0,
                rationale="requires_empirical_search",
                policy_version=self.policy_version,
            )

        if context.domain_hint is not None:
            route = _map_domain_hint(context.domain_hint)
            if route is not None:
                return RouteDecision(
                    selected_route=route,
                    confidence=0.8,
                    rationale="domain_hint:%s" % context.domain_hint,
                    policy_version=self.policy_version,
                )
            return RouteDecision(
                selected_route=OracleRoute.UNKNOWN,
                confidence=0.4,
                rationale="unknown_domain_hint:%s" % context.domain_hint,
                policy_version=self.policy_version,
            )

        return RouteDecision(
            selected_route=OracleRoute.UNKNOWN,
            confidence=0.4,
            rationale="no_routing_signal",
            policy_version=self.policy_version,
        )


def _map_domain_hint(domain_hint: str) -> OracleRoute | None:
    mapping = {
        "physical": OracleRoute.PHYSICAL,
        "logical": OracleRoute.LOGICAL,
        "foundational": OracleRoute.FOUNDATIONAL,
    }
    return mapping.get(domain_hint)
