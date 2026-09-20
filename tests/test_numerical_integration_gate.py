from __future__ import annotations

import copy
import json
import math
import unittest
from pathlib import Path

from romania_macro_financial_dynamics.dynamics import (
    DEFAULT_DT_YEARS,
    first_order_delay_timestep_is_adequate,
    simulate_first_order_delay_euler,
)
from scripts.audit_numerical_integration import (
    audit_numerical_integration,
    simulate_constant_rate_partition,
)

ROOT = Path(__file__).resolve().parents[1]


def read(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class NumericalIntegrationGateTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = read(
            "model/dynamics/numerical_integration_contract.json"
        )
        self.core = read("model/dynamics/core_contract.json")
        self.delay = read("model/dynamics/delay_evidence_registry.json")
        self.model = read("model/registries/model_contract.json")

    def audit(self, contract=None, delay=None):
        return audit_numerical_integration(
            contract or self.contract,
            self.core,
            delay or self.delay,
            self.model,
        )

    def test_current_contract_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_constant_rate_stock_update_is_partition_invariant(self) -> None:
        results = [
            simulate_constant_rate_partition(
                opening=1000.0,
                transaction_rate=100.0,
                revaluation_rate=-20.0,
                other_change_rate=5.0,
                horizon_years=1.0,
                dt_years=dt,
            )
            for dt in (1.0, 0.5, 0.25, 0.125)
        ]
        for result in results:
            self.assertAlmostEqual(result, 1085.0, places=10)

    def test_first_order_delay_converges_under_step_halving(self) -> None:
        exact = 1.0 - math.exp(-1.0)
        results = [
            simulate_first_order_delay_euler(
                initial=0.0,
                input_value=1.0,
                tau_years=1.0,
                horizon_years=1.0,
                dt_years=dt,
            )
            for dt in (0.25, 0.125, 0.0625, 0.03125)
        ]
        errors = [abs(value - exact) for value in results]
        self.assertTrue(
            all(
                later < earlier
                for earlier, later in zip(errors, errors[1:])
            )
        )

    def test_default_quarterly_dt_has_strict_tau_threshold(self) -> None:
        self.assertEqual(DEFAULT_DT_YEARS, 0.25)
        self.assertFalse(
            first_order_delay_timestep_is_adequate(
                DEFAULT_DT_YEARS, 0.75
            )
        )
        self.assertTrue(
            first_order_delay_timestep_is_adequate(
                DEFAULT_DT_YEARS, 0.750001
            )
        )
        self.assertFalse(
            first_order_delay_timestep_is_adequate(
                DEFAULT_DT_YEARS, 0.5
            )
        )

    def test_default_dt_is_not_declared_universally_valid(self) -> None:
        self.assertTrue(
            self.contract["hard_rules"][
                "default_dt_is_not_universally_valid_for_delays"
            ]
        )
        self.assertEqual(
            self.contract["current_summary"]["default_dt_delay_adequacy"],
            "CONDITIONAL_ON_TAU_GREATER_THAN_0_75_YEARS",
        )

    def test_all_current_delay_candidates_remain_inactive_and_unparameterized(self) -> None:
        self.assertEqual(
            self.delay["current_summary"]["registered_delay_candidates"], 7
        )
        self.assertEqual(
            self.delay["current_summary"][
                "scalar_tau_identified_and_validated"
            ],
            0,
        )
        self.assertEqual(
            self.delay["current_summary"]["active_delay_candidates"], 0
        )
        self.assertTrue(
            all(item["current_tau"] == "TBD" for item in self.delay["delays"])
        )
        self.assertTrue(
            all(item["active"] is False for item in self.delay["delays"])
        )

    def test_structural_convergence_does_not_claim_integrated_model_robustness(self) -> None:
        summary = self.contract["current_summary"]
        self.assertEqual(
            summary["first_order_delay_reference_convergence"], "PASS"
        )
        self.assertEqual(
            summary["integrated_model_numerical_robustness"],
            "NOT_RUN_BEHAVIOURAL_CLOSURE_INACTIVE",
        )
        self.assertFalse(summary["behavioural_closure_active"])
        self.assertFalse(summary["model_activation_authorized"])

    def test_stale_default_dt_tau_implication_is_detected(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["structural_primitives"]["first_order_delay"][
            "explicit_euler_time_step_rule"
        ]["implied_tau_requirement_at_default_dt"] = "tau_years >= 0.75"
        errors = self.audit(contract=mutated)
        self.assertTrue(
            any("tau implication is stale" in error for error in errors)
        )

    def test_active_delay_without_validated_parameterization_is_detected(self) -> None:
        mutated_delay = copy.deepcopy(self.delay)
        mutated_delay["current_summary"]["active_delay_candidates"] = 1
        errors = self.audit(delay=mutated_delay)
        self.assertTrue(
            any("active-delay count is stale" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
