from __future__ import annotations

from .context import OracleRoute, RouteDecision, RouteDispatchResult


def build_stub_response(decision: RouteDecision) -> RouteDispatchResult:
    route = decision.selected_route
    message = _stub_message(route)
    return RouteDispatchResult(
        status="stub",
        route=route,
        message=message,
        implemented=False,
        decision=decision,
    )


def build_unknown_response(decision: RouteDecision) -> RouteDispatchResult:
    return RouteDispatchResult(
        status="stub",
        route=OracleRoute.UNKNOWN,
        message="Oracle route is unknown for the provided routing context.",
        implemented=False,
        decision=decision,
    )


def build_error_response(decision: RouteDecision, message: str) -> RouteDispatchResult:
    return RouteDispatchResult(
        status="error",
        route=decision.selected_route,
        message=message,
        implemented=decision.selected_route == OracleRoute.LOGICAL,
        decision=decision,
    )


def _stub_message(route: OracleRoute) -> str:
    messages = {
        OracleRoute.PHYSICAL: "Physical oracle route is not implemented in this project version.",
        OracleRoute.FOUNDATIONAL: "Foundational oracle route is not implemented in this project version.",
        OracleRoute.LOGICAL: "Logical oracle route is not available in this project configuration.",
        OracleRoute.UNKNOWN: "Oracle route is unknown for the provided routing context.",
    }
    return messages[route]
