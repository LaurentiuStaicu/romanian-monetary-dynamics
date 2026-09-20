from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_behavioural_dimensional_consistency import audit_behavioural_units

ROOT = Path(__file__).resolve().parents[1]


class BehaviouralDimensionalConsistencyTests(unittest.TestCase):
    def setUp(self) -> None:
        self.registry = json.loads(
            (
                ROOT
                / "model"
                / "empirical_dynamics"
                / "mechanism_registry.json"
            ).read_text(encoding="utf-8")
        )
        self.contract = json.loads(
            (
                ROOT
                / "model"
                / "empirical_dynamics"
                / "behavioural_unit_contract.json"
            ).read_text(encoding="utf-8")
        )

    def test_current_contract_passes(self) -> None:
        self.assertEqual(
            audit_behavioural_units(self.registry, self.contract),
            [],
        )

    def test_every_current_implementation_requires_unit_contract(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["equations"] = mutated["equations"][1:]
        errors = audit_behavioural_units(self.registry, mutated)
        self.assertTrue(
            any("implementation coverage mismatch" in error for error in errors)
        )

    def test_additive_unit_mismatch_is_detected(self) -> None:
        mutated = copy.deepcopy(self.contract)
        household = next(
            item
            for item in mutated["equations"]
            if item["implementation"] == "household_consumption_growth"
        )
        household["additive_terms"][0]["unit_class"] = "rate_level_pp_per_annum"
        errors = audit_behavioural_units(self.registry, mutated)
        self.assertTrue(
            any(
                error.startswith("household_consumption_growth: additive term")
                for error in errors
            )
        )

    def test_unfrozen_measurement_scale_cannot_pass_unit_gate(self) -> None:
        mutated = copy.deepcopy(self.contract)
        credit = next(
            item
            for item in mutated["equations"]
            if item["implementation"] == "aggregate_credit_growth"
        )
        credit["unit_activation_readiness"] = "PASS_UNIT_GATE_ONLY"
        errors = audit_behavioural_units(self.registry, mutated)
        self.assertTrue(
            any(
                error.startswith(
                    "aggregate_credit_growth: unfrozen measurement scale"
                )
                for error in errors
            )
        )

    def test_refinancing_share_cannot_be_treated_as_rate_dimension(self) -> None:
        mutated_registry = copy.deepcopy(self.registry)
        government = next(
            item
            for item in mutated_registry["mechanisms"]
            if item["id"] == "government_refinancing_effective_rate"
        )
        m = next(item for item in government["parameters"] if item["id"] == "m[t]")
        m["unit"] = "fraction_per_period"
        errors = audit_behavioural_units(mutated_registry, self.contract)
        self.assertTrue(
            any(
                "m[t] must be a dimensionless period share" in error
                for error in errors
            )
        )

    def test_unit_contract_never_authorizes_model_activation(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["equations"][0]["model_activation_authorized"] = True
        errors = audit_behavioural_units(self.registry, mutated)
        self.assertTrue(
            any("must not authorize model activation" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
