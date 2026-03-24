from __future__ import annotations

import unittest

from haos_skill.foundational import (
    FoundationalCheck,
    FoundationalDimension,
    FoundationalResult,
    FoundationalSignals,
)


class FoundationalContractTests(unittest.TestCase):
    def test_foundational_check_round_trip_is_json_friendly(self) -> None:
        check = FoundationalCheck.from_dict(
            {
                "candidate_id": "demo",
                "dimensions": [
                    "contradiction_risk",
                    "invalid_abstraction_crossing",
                ],
                "notes": {"scope": "contract-only"},
            }
        )

        self.assertEqual(
            check.to_dict(),
            {
                "candidate_id": "demo",
                "dimensions": [
                    "contradiction_risk",
                    "invalid_abstraction_crossing",
                ],
                "notes": {"scope": "contract-only"},
            },
        )

    def test_foundational_signals_are_bounded(self) -> None:
        signals = FoundationalSignals(
            contradiction_risk=0.1,
            composability_violation=0.2,
            non_recoverable_identity_collapse=0.3,
            invalid_abstraction_crossing=0.4,
        )

        self.assertEqual(
            signals.to_dict(),
            {
                "contradiction_risk": 0.1,
                "composability_violation": 0.2,
                "non_recoverable_identity_collapse": 0.3,
                "invalid_abstraction_crossing": 0.4,
            },
        )

    def test_foundational_result_round_trip_is_typed(self) -> None:
        result = FoundationalResult(
            classification="unavailable",
            signals=FoundationalSignals(
                contradiction_risk=0.0,
                composability_violation=0.0,
                non_recoverable_identity_collapse=0.0,
                invalid_abstraction_crossing=0.0,
            ),
            policy_version="foundational_contract_v1",
            summary="Foundational route is contract-defined but not implemented.",
        )

        self.assertEqual(
            FoundationalResult.from_dict(result.to_dict()).to_dict(),
            {
                "classification": "unavailable",
                "signals": {
                    "contradiction_risk": 0.0,
                    "composability_violation": 0.0,
                    "non_recoverable_identity_collapse": 0.0,
                    "invalid_abstraction_crossing": 0.0,
                },
                "policy_version": "foundational_contract_v1",
                "summary": "Foundational route is contract-defined but not implemented.",
            },
        )

    def test_dimension_enum_is_explicit(self) -> None:
        self.assertEqual(
            tuple(dimension.value for dimension in FoundationalDimension),
            (
                "contradiction_risk",
                "composability_violation",
                "non_recoverable_identity_collapse",
                "invalid_abstraction_crossing",
            ),
        )


if __name__ == "__main__":
    unittest.main()
