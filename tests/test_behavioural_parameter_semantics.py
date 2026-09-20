from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from romania_macro_financial_dynamics.behavioural import (
    InvalidBehaviouralInput,
    aggregate_credit_growth,
    household_consumption_growth,
    npl_ratio_change,
)
from scripts.audit_behavioural_parameter_semantics import (
    audit_behavioural_parameter_semantics,
)

ROOT = Path(__file__).resolve().parents[1]


class BehaviouralParameterSemanticsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.mechanisms = json.loads(
            (
                ROOT / "model" / "empirical_dynamics" / "mechanism_registry.json"
            ).read_text(encoding="utf-8")
        )
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "empirical_dynamics"
                / "behavioural_parameter_contract.json"
            ).read_text(encoding="utf-8")
        )

    def audit(self, contract=None):
        return audit_behavioural_parameter_semantics(
            self.mechanisms, contract or self.contract
        )

    def test_current_contract_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_current_implementation_coverage_is_exact(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["equations"] = mutated["equations"][1:]
        self.assertTrue(
            any(
                "implementation coverage mismatch" in error
                for error in self.audit(mutated)
            )
        )

    def test_negative_household_magnitudes_are_rejected(self) -> None:
        base = dict(
            disposable_income_growth=0.01,
            real_borrowing_rate=4.0,
            debt_service_ratio=0.2,
            intercept=0.0,
            income_sensitivity=0.5,
            rate_sensitivity=0.2,
            debt_service_sensitivity=0.3,
        )
        for name in (
            "income_sensitivity",
            "rate_sensitivity",
            "debt_service_sensitivity",
        ):
            with self.subTest(parameter=name):
                kwargs = dict(base)
                kwargs[name] = -0.01
                with self.assertRaises(InvalidBehaviouralInput):
                    household_consumption_growth(**kwargs)

    def test_negative_credit_magnitudes_are_rejected(self) -> None:
        base = dict(
            activity_growth=0.01,
            real_lending_rate=5.0,
            npl_ratio=0.05,
            capital_buffer=0.1,
            intercept=0.0,
            activity_sensitivity=0.5,
            rate_sensitivity=0.2,
            npl_sensitivity=0.3,
            capital_sensitivity=0.4,
        )
        for name in (
            "activity_sensitivity",
            "rate_sensitivity",
            "npl_sensitivity",
            "capital_sensitivity",
        ):
            with self.subTest(parameter=name):
                kwargs = dict(base)
                kwargs[name] = -0.01
                with self.assertRaises(InvalidBehaviouralInput):
                    aggregate_credit_growth(**kwargs)

    def test_negative_npl_magnitudes_are_rejected(self) -> None:
        base = dict(
            output_growth=0.01,
            debt_service_burden=0.2,
            previous_npl_ratio=0.05,
            intercept=0.0,
            output_sensitivity=0.5,
            debt_service_sensitivity=0.4,
            persistence=0.5,
        )
        for name in ("output_sensitivity", "debt_service_sensitivity"):
            with self.subTest(parameter=name):
                kwargs = dict(base)
                kwargs[name] = -0.01
                with self.assertRaises(InvalidBehaviouralInput):
                    npl_ratio_change(**kwargs)

    def test_signed_intercepts_remain_allowed(self) -> None:
        value = household_consumption_growth(
            disposable_income_growth=0.0,
            real_borrowing_rate=0.0,
            debt_service_ratio=0.0,
            intercept=-0.02,
            income_sensitivity=0.0,
            rate_sensitivity=0.0,
            debt_service_sensitivity=0.0,
        )
        self.assertEqual(value, -0.02)

    def test_absolute_value_repair_is_not_contractually_allowed(self) -> None:
        self.assertTrue(
            self.contract["hard_rules"]["no_absolute_value_repair_of_negative_estimates"]
        )
        self.assertTrue(self.contract["hard_rules"]["no_post_fit_sign_flip"])

    def test_contract_cannot_authorize_estimation_or_activation(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["current_summary"]["estimation_authorized"] = True
        mutated["current_summary"]["model_activation_authorized"] = True
        errors = self.audit(mutated)
        self.assertTrue(any("may not authorize estimation" in e for e in errors))
        self.assertTrue(any("may not authorize model activation" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
