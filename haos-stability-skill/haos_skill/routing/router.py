from __future__ import annotations

from typing import Any

from ..oracle import OracleEngine, OracleInputError, build_default_engine
from ..state_spec import OracleResult
from .context import RouteDecision, RouteDispatchResult, RoutingContext, RoutingContextLike, coerce_routing_context
from .policies import RoutingPolicy
from .stubs import build_error_response, build_stub_response, build_unknown_response


class OracleRouter:
    def __init__(self, policy: RoutingPolicy, logical_engine: OracleEngine | None = None) -> None:
        self.policy = policy
        self.logical_engine = logical_engine

    def decide(self, context: RoutingContext) -> RouteDecision:
        resolved = coerce_routing_context(context)
        return self.policy.select(resolved)

    def dispatch(
        self,
        context: RoutingContext,
        *,
        before: Any = None,
        after: Any = None,
        perturbation: Any = None,
    ) -> RouteDispatchResult:
        decision = self.decide(context)

        if decision.selected_route.value == "LOGICAL":
            return self._dispatch_logical(
                decision,
                before=before,
                after=after,
                perturbation=perturbation,
            )

        if decision.selected_route.value in {"PHYSICAL", "FOUNDATIONAL"}:
            return build_stub_response(decision)

        return build_unknown_response(decision)

    def _dispatch_logical(
        self,
        decision: RouteDecision,
        *,
        before: Any,
        after: Any,
        perturbation: Any,
    ) -> RouteDispatchResult:
        if self.logical_engine is None:
            return build_stub_response(decision)

        try:
            if before is not None and after is not None:
                result = self.logical_engine.evaluate_transition(before, after)
            elif before is not None and perturbation is not None:
                result = self.logical_engine.evaluate(before, perturbation)
            else:
                raise OracleInputError(
                    "logical dispatch requires either before+after or before+perturbation"
                )
        except Exception as exc:
            return build_error_response(decision, str(exc))

        return RouteDispatchResult(
            status="ok",
            route=decision.selected_route,
            message="Logical oracle route executed successfully.",
            implemented=True,
            decision=decision,
            result=_coerce_result_payload(result),
        )


def build_default_router(
    policy: RoutingPolicy | None = None,
    logical_engine: OracleEngine | None = None,
) -> OracleRouter:
    return OracleRouter(
        policy=policy or RoutingPolicy(),
        logical_engine=logical_engine or build_default_engine(),
    )


def route_candidate(
    context: RoutingContextLike,
    *,
    before: Any = None,
    after: Any = None,
    perturbation: Any = None,
    router: OracleRouter | None = None,
) -> RouteDispatchResult:
    resolved_router = router or build_default_router()
    return resolved_router.dispatch(
        coerce_routing_context(context),
        before=before,
        after=after,
        perturbation=perturbation,
    )


def _coerce_result_payload(result: OracleResult | Any) -> dict[str, Any]:
    if isinstance(result, OracleResult):
        return result.to_dict()
    if hasattr(result, "to_dict"):
        payload = result.to_dict()
        if isinstance(payload, dict):
            return payload
    raise TypeError("logical engine must return an OracleResult-compatible object")
