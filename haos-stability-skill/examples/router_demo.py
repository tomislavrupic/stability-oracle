from __future__ import annotations

import json

from haos_skill import Perturbation, RoutingContext, build_default_router


def main() -> None:
    router = build_default_router()
    before = {
        "nodes": [1, 2, 3, 4],
        "edges": [[1, 2], [2, 3], [3, 4]],
        "timestamps": {"1": 0.0, "2": 1.0, "3": 2.0, "4": 3.0},
    }
    perturbation = Perturbation(cluster_split=True)

    cases = [
        (
            "logical",
            RoutingContext(
                candidate_id="router-demo-logical",
                requires_structural_stability=True,
            ),
            {"before": before, "perturbation": perturbation},
        ),
        (
            "physical",
            RoutingContext(
                candidate_id="router-demo-physical",
                requires_empirical_search=True,
            ),
            {},
        ),
        (
            "foundational",
            RoutingContext(
                candidate_id="router-demo-foundational",
                requires_foundational_check=True,
            ),
            {},
        ),
        (
            "unknown",
            RoutingContext(
                candidate_id="router-demo-unknown",
                notes={"source": "router-demo"},
            ),
            {},
        ),
    ]

    for label, context, kwargs in cases:
        print("=== %s ===" % label)
        print(json.dumps(router.decide(context).to_dict(), indent=2, sort_keys=False))
        print(json.dumps(router.dispatch(context, **kwargs).to_dict(), indent=2, sort_keys=False))
        print()


if __name__ == "__main__":
    main()
