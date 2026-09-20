from __future__ import annotations

import copy
import json
import math
import unittest
from pathlib import Path

from romania_macro_financial_dynamics.behavioural import (
    InvalidBehaviouralInput,
    aggregate_credit_growth,
    household_consumption_growth,
    npl_ratio_change,
    refinancing_effective_rate,
)
from scripts.audit_behavioural_robustness import audit_behavioural_robustness

ROOT = Path(__file__).resolve().parents[1]


class BehaviouralRobustnessContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mechanisms = json.loads(
            (
                ROOT / "model" / "empirical_dynamics" / "mechanism_registry.json"
            ).read_text(encoding="utf-8")
        )
        self.robustness = json.loads(
            (
                ROOT
                / "model"
                / "empirical_dynamics"
                / "behavioural_robustness_contract.json"
            ).read_text(encoding="utf-8")
        )
        self.model = json.loads(
            (ROOT / "model" / "registries" / "model_contract.json").read_text(
                encoding="utf-8"
            )
        )

    def audit(self, robustness=None):
        return audit_behavioural_robustness(
            self.mechanisms,
            robustness or self.robustness,
            self.model,
        )

    def test_current_contract_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_missing_current_implementation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.robustness)
        mutated["forms"] = mutated["forms"][1:]
        errors = self.audit(mutated)
        self.assertTrue(
            any("current implementation coverage mismatch" in e for e in errors)
        )

    def test_empirical_sensitivity_cannot_be_declared_executed(self) -> None:
        mutated = copy.deepcopy(self.robustness)
        mutated["forms"][0]["sensitivity_plan"]["status"] = "EXECUTED"
        errors = self.audit(mutated)
        self.assertTrue(
            any("empirical sensitivity must remain blocked" in e for e in errors)
        )

    def test_robustness_contract_cannot_authorize_activation(self) -> None:
        mutated = copy.deepcopy(self.robustness)
        mutated["forms"][0]["model_activation_authorized"] = True
        errors = self.audit(mutated)
        self.assertTrue(
            any("may not authorize activation" in e for e in errors)
        )


class BehaviouralExtremeConditionTests(unittest.TestCase):
    def test_refinancing_share_extremes_and_convexity(self) -> None:
        previous = 4.0
        marginal = 8.0
        self.assertEqual(
            refinancing_effective_rate(
                previous, marginal, refinancing_share=0.0
            ),
            previous,
        )
        self.assertEqual(
            refinancing_effective_rate(
                previous, marginal, refinancing_share=1.0
            ),
            marginal,
        )
        middle = refinancing_effective_rate(
            previous, marginal, refinancing_share=0.25
        )
        self.assertGreaterEqual(middle, min(previous, marginal))
        self.assertLessEqual(middle, max(previous, marginal))
        self.assertAlmostEqual(middle, 5.0)

    def test_refinancing_share_outside_structural_domain_is_rejected(self) -> None:
        for share in (-1e-12, 1.0 + 1e-12):
            with self.subTest(share=share):
                with self.assertRaises(InvalidBehaviouralInput):
                    refinancing_effective_rate(
                        4.0, 8.0, refinancing_share=share
                    )

    def test_refinancing_structural_sensitivity_is_exact(self) -> None:
        previous = 4.0
        marginal = 8.0
        eps = 1e-6
        low = refinancing_effective_rate(
            previous, marginal, refinancing_share=0.5 - eps
        )
        high = refinancing_effective_rate(
            previous, marginal, refinancing_share=0.5 + eps
        )
        derivative = (high - low) / (2.0 * eps)
        self.assertAlmostEqual(derivative, marginal - previous, places=8)
        self.assertEqual(
            refinancing_effective_rate(
                previous, previous, refinancing_share=0.9
            ),
            previous,
        )

    def test_household_directional_structure(self) -> None:
        kwargs = dict(
            intercept=0.01,
            income_sensitivity=0.5,
            rate_sensitivity=0.2,
            debt_service_sensitivity=0.3,
        )
        base = household_consumption_growth(
            disposable_income_growth=0.0,
            real_borrowing_rate=0.0,
            debt_service_ratio=0.0,
            **kwargs,
        )
        self.assertEqual(base, kwargs["intercept"])
        self.assertGreater(
            household_consumption_growth(
                disposable_income_growth=0.02,
                real_borrowing_rate=0.0,
                debt_service_ratio=0.0,
                **kwargs,
            ),
            base,
        )
        self.assertLess(
            household_consumption_growth(
                disposable_income_growth=0.0,
                real_borrowing_rate=1.0,
                debt_service_ratio=0.0,
                **kwargs,
            ),
            base,
        )
        self.assertLess(
            household_consumption_growth(
                disposable_income_growth=0.0,
                real_borrowing_rate=0.0,
                debt_service_ratio=0.1,
                **kwargs,
            ),
            base,
        )

    def test_credit_directional_structure(self) -> None:
        kwargs = dict(
            intercept=0.01,
            activity_sensitivity=0.5,
            rate_sensitivity=0.2,
            npl_sensitivity=0.3,
            capital_sensitivity=0.4,
        )
        base = aggregate_credit_growth(
            activity_growth=0.0,
            real_lending_rate=0.0,
            npl_ratio=0.0,
            capital_buffer=0.0,
            **kwargs,
        )
        self.assertEqual(base, kwargs["intercept"])
        self.assertGreater(
            aggregate_credit_growth(
                activity_growth=0.02,
                real_lending_rate=0.0,
                npl_ratio=0.0,
                capital_buffer=0.0,
                **kwargs,
            ),
            base,
        )
        self.assertLess(
            aggregate_credit_growth(
                activity_growth=0.0,
                real_lending_rate=1.0,
                npl_ratio=0.0,
                capital_buffer=0.0,
                **kwargs,
            ),
            base,
        )
        self.assertLess(
            aggregate_credit_growth(
                activity_growth=0.0,
                real_lending_rate=0.0,
                npl_ratio=0.1,
                capital_buffer=0.0,
                **kwargs,
            ),
            base,
        )
        self.assertGreater(
            aggregate_credit_growth(
                activity_growth=0.0,
                real_lending_rate=0.0,
                npl_ratio=0.0,
                capital_buffer=0.1,
                **kwargs,
            ),
            base,
        )

    def test_npl_persistence_extremes_and_directional_structure(self) -> None:
        kwargs = dict(
            intercept=0.0,
            output_sensitivity=0.5,
            debt_service_sensitivity=0.4,
        )
        self.assertEqual(
            npl_ratio_change(
                output_growth=0.0,
                debt_service_burden=0.0,
                previous_npl_ratio=0.2,
                persistence=0.0,
                **kwargs,
            ),
            0.0,
        )
        self.assertAlmostEqual(
            npl_ratio_change(
                output_growth=0.0,
                debt_service_burden=0.0,
                previous_npl_ratio=0.2,
                persistence=1.0,
                **kwargs,
            ),
            0.2,
        )
        base = npl_ratio_change(
            output_growth=0.0,
            debt_service_burden=0.0,
            previous_npl_ratio=0.2,
            persistence=0.5,
            **kwargs,
        )
        self.assertLess(
            npl_ratio_change(
                output_growth=0.1,
                debt_service_burden=0.0,
                previous_npl_ratio=0.2,
                persistence=0.5,
                **kwargs,
            ),
            base,
        )
        self.assertGreater(
            npl_ratio_change(
                output_growth=0.0,
                debt_service_burden=0.1,
                previous_npl_ratio=0.2,
                persistence=0.5,
                **kwargs,
            ),
            base,
        )

    def test_npl_persistence_outside_structural_domain_is_rejected(self) -> None:
        for persistence in (-1e-12, 1.0 + 1e-12):
            with self.subTest(persistence=persistence):
                with self.assertRaises(InvalidBehaviouralInput):
                    npl_ratio_change(
                        output_growth=0.0,
                        debt_service_burden=0.0,
                        previous_npl_ratio=0.2,
                        intercept=0.0,
                        output_sensitivity=0.5,
                        debt_service_sensitivity=0.4,
                        persistence=persistence,
                    )

    def test_non_finite_inputs_are_rejected(self) -> None:
        with self.assertRaises(InvalidBehaviouralInput):
            refinancing_effective_rate(
                math.nan, 8.0, refinancing_share=0.5
            )
        with self.assertRaises(InvalidBehaviouralInput):
            household_consumption_growth(
                disposable_income_growth=math.inf,
                real_borrowing_rate=0.0,
                debt_service_ratio=0.0,
                intercept=0.0,
                income_sensitivity=1.0,
                rate_sensitivity=1.0,
                debt_service_sensitivity=1.0,
            )
        with self.assertRaises(InvalidBehaviouralInput):
            aggregate_credit_growth(
                activity_growth=0.0,
                real_lending_rate=0.0,
                npl_ratio=math.nan,
                capital_buffer=0.0,
                intercept=0.0,
                activity_sensitivity=1.0,
                rate_sensitivity=1.0,
                npl_sensitivity=1.0,
                capital_sensitivity=1.0,
            )
        with self.assertRaises(InvalidBehaviouralInput):
            npl_ratio_change(
                output_growth=0.0,
                debt_service_burden=math.inf,
                previous_npl_ratio=0.2,
                intercept=0.0,
                output_sensitivity=1.0,
                debt_service_sensitivity=1.0,
                persistence=0.5,
            )


if __name__ == "__main__":
    unittest.main()
