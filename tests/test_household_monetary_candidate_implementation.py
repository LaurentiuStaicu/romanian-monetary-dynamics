from __future__ import annotations

import csv
import json
import math
import unittest
from pathlib import Path

from romania_macro_financial_dynamics.behavioural import (
    InvalidBehaviouralInput,
    household_housing_delta_policy_rate,
)
from romania_macro_financial_dynamics.validation_recovery import (
    Fit,
    predict_delta_policy,
)

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data" / "raw" / "validation_recovery"


def read_series(path: Path) -> dict[str, float]:
    with path.open(encoding="utf-8") as handle:
        return {
            row["period"]: float(row["value_pct"])
            for row in csv.DictReader(handle)
        }


class HouseholdMonetaryCandidateImplementationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = json.loads(
            (
                ROOT
                / "model"
                / "empirical_dynamics"
                / "mechanism_registry.json"
            ).read_text(encoding="utf-8")
        )
        self.holdout = json.loads(
            (
                ROOT
                / "model"
                / "calibration_validation"
                / "validation_recovery_holdout.json"
            ).read_text(encoding="utf-8")
        )
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "calibration_validation"
                / "validation_recovery_contract.json"
            ).read_text(encoding="utf-8")
        )

    def monetary_mechanism(self) -> dict[str, object]:
        return next(
            item
            for item in self.registry["mechanisms"]
            if item["id"] == "monetary_policy_lending_rate_pass_through"
        )

    def test_registry_maps_exact_frozen_target_specific_form(self) -> None:
        mechanism = self.monetary_mechanism()
        self.assertEqual(mechanism["classification"], "CANDIDATE")
        self.assertFalse(mechanism["central_feedback"])
        self.assertEqual(
            mechanism["implementation"],
            "household_housing_delta_policy_rate",
        )
        self.assertEqual(
            mechanism["implementation_scope"],
            "HOUSEHOLD_HOUSING_TARGET_SPECIFIC_ONLY",
        )
        self.assertTrue(mechanism["implementation_not_generic_feedback_link"])
        self.assertEqual(
            mechanism["validation_recovery_selected_form"]["equation"],
            self.holdout["equation"],
        )
        self.assertFalse(
            mechanism["validation_recovery_selected_form"][
                "passes_all_final_holdout_gates"
            ]
        )
        self.assertFalse(
            mechanism["validation_recovery_selected_form"]["causal_claim"]
        )

    def test_frozen_beta_and_validation_domain_match_recovery_artifacts(self) -> None:
        mechanism = self.monetary_mechanism()
        beta = mechanism["parameters"][0]
        candidate = next(
            item
            for item in self.contract["candidate_models"]
            if item["id"] == "delta_policy_contemporaneous"
        )
        self.assertAlmostEqual(beta["value"], self.holdout["frozen_beta"])
        self.assertEqual(
            candidate["parameter_domain_for_validation"]["beta"],
            [0, 2],
        )
        self.assertEqual(
            mechanism["implementation_parameter_domain"][
                "beta_household_housing"
            ],
            [0, 2],
        )

    def test_implementation_matches_validation_recovery_predictor_exactly(self) -> None:
        policy_map = read_series(DATA / "policy_rate_bis_monthly.csv")
        lending_map = read_series(DATA / "household_housing_mir_monthly.csv")
        periods = sorted(set(policy_map) & set(lending_map))
        policy = [policy_map[p] for p in periods]
        lending = [lending_map[p] for p in periods]
        beta = float(self.holdout["frozen_beta"])
        fit = Fit(
            model_id="delta_policy_contemporaneous",
            parameters={"beta": beta},
            training_observations=1,
            driver_sum_squares=1.0,
            design_rank=1,
        )
        for index in range(1, len(periods)):
            expected = predict_delta_policy(
                lending, policy, index, fit, lag=0
            )
            observed = household_housing_delta_policy_rate(
                lending[index - 1],
                policy[index],
                policy[index - 1],
                beta=beta,
            )
            self.assertAlmostEqual(observed, expected, places=15)

    def test_zero_policy_change_equals_persistence(self) -> None:
        self.assertEqual(
            household_housing_delta_policy_rate(
                7.25, 6.5, 6.5, beta=0.5
            ),
            7.25,
        )

    def test_signed_policy_change_direction_is_preserved(self) -> None:
        beta = 0.5
        self.assertEqual(
            household_housing_delta_policy_rate(
                7.0, 7.0, 6.0, beta=beta
            ),
            7.5,
        )
        self.assertEqual(
            household_housing_delta_policy_rate(
                7.0, 5.0, 6.0, beta=beta
            ),
            6.5,
        )

    def test_beta_validation_domain_is_enforced(self) -> None:
        self.assertEqual(
            household_housing_delta_policy_rate(
                7.0, 8.0, 6.0, beta=0.0
            ),
            7.0,
        )
        self.assertEqual(
            household_housing_delta_policy_rate(
                7.0, 8.0, 6.0, beta=2.0
            ),
            11.0,
        )
        for beta in (-1e-12, 2.0 + 1e-12):
            with self.subTest(beta=beta):
                with self.assertRaises(InvalidBehaviouralInput):
                    household_housing_delta_policy_rate(
                        7.0, 8.0, 6.0, beta=beta
                    )

    def test_nonfinite_inputs_are_rejected(self) -> None:
        for values in (
            (math.nan, 6.0, 6.0, 0.5),
            (7.0, math.inf, 6.0, 0.5),
            (7.0, 6.0, math.nan, 0.5),
            (7.0, 6.0, 6.0, math.inf),
        ):
            with self.subTest(values=values):
                with self.assertRaises(InvalidBehaviouralInput):
                    household_housing_delta_policy_rate(
                        values[0],
                        values[1],
                        values[2],
                        beta=values[3],
                    )

    def test_target_specific_implementation_does_not_make_generic_link_ready(self) -> None:
        readiness = json.loads(
            (
                ROOT
                / "model"
                / "dynamics"
                / "feedback_link_readiness_registry.json"
            ).read_text(encoding="utf-8")
        )
        row = next(
            item
            for item in readiness["links"]
            if item["link_key"]
            == (
                "monetary_credit_transmission_loop|"
                "policy_rate|market_and_lending_rates"
            )
        )
        self.assertEqual(
            row["target_specific_implementation_pointer"],
            "household_housing_delta_policy_rate",
        )
        self.assertEqual(
            row["readiness_status"],
            "PARTIAL_TARGET_SPECIFIC_FORM_NOT_INTEGRATED",
        )
        self.assertFalse(row["exact_integrated_equation_ready"])
        self.assertFalse(row["current_activation_authorized"])


if __name__ == "__main__":
    unittest.main()
