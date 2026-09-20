from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_mof_announced_RON_primary_supply_full_2025_definition import (
    REVIEW_PATH,
    audit_full_2025_definition,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class MOFAnnouncedRONPrimarySupplyFull2025DefinitionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(REVIEW_PATH)
        self.measurement_design = load(
            "model/dynamics/government_securities_supply_measurement_design_review_2026_09_20.json"
        )
        self.q1_pilot = load(
            "model/dynamics/mof_announced_RON_primary_supply_reference_mode_pilot_Q1_2025.json"
        )
        self.source_review = load(
            "model/dynamics/government_securities_supply_pressure_source_boundary_review_2026_09_20.json"
        )
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.prereg = load(
            "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
        )
        self.model_contract = load("model/registries/model_contract.json")

    def audit(self, **overrides):
        return audit_full_2025_definition(
            overrides.get("review", self.review),
            overrides.get("measurement_design", self.measurement_design),
            overrides.get("q1_pilot", self.q1_pilot),
            overrides.get("source_review", self.source_review),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("feedback", self.feedback),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
        )

    def test_current_definition_review_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_full_year_candidate_is_competitive_only(self) -> None:
        design = self.review["full_year_measurement_design"]
        self.assertEqual(
            set(design["included_event_types"]),
            {
                "T_BILL_COMPETITIVE_REFERENCE_AUCTION",
                "BENCHMARK_BOND_COMPETITIVE_REFERENCE_AUCTION",
            },
        )
        self.assertIn(
            "BENCHMARK_BOND_SSON",
            design["excluded_from_canonical_candidate"],
        )

    def test_december_sson_is_formula_dependent_not_fixed_nominal(self) -> None:
        dec = next(
            item
            for item in self.review["official_legal_screening"]["months"]
            if item["month"] == "2025-12"
        )
        self.assertEqual(
            dec["SSON_rule"],
            "15_percent_of_nominal_amount_adjudicated_at_reference_auctions",
        )
        self.assertFalse(dec["fixed_nominal_SSON_amount_known_at_announcement"])
        self.assertTrue(
            self.review["SSON_auxiliary"]["missing_or_formula_dependent_is_not_zero"]
        )

    def test_amendment_months_are_versioned(self) -> None:
        months = {
            item["month"]: item
            for item in self.review["official_legal_screening"]["months"]
        }
        self.assertEqual(months["2025-05"]["amendments"][0]["order"], "752/2025")
        self.assertEqual(months["2025-11"]["amendments"][0]["order"], "1831/2025")
        self.assertEqual(months["2025-12"]["amendments"][0]["order"], "1998/2025")
        self.assertTrue(
            self.review["amendment_handling"]["base_order_rows_may_not_be_silently_overwritten"]
        )

    def test_q1_legacy_pilot_is_retained_not_rewritten(self) -> None:
        q1 = self.review["Q1_disposition"]
        self.assertTrue(q1["legacy_Q1_pilot_remains_valid_on_its_frozen_definition"])
        self.assertFalse(q1["legacy_Q1_pilot_may_be_rewritten_in_place"])
        self.assertTrue(
            q1["full_year_comparable_competitive_only_Q1_subset_may_be_derived_from_retained_Q1_events"]
        )

    def test_manual_sson_reintroduction_is_detected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["full_year_measurement_design"]["included_event_types"].append(
            "BENCHMARK_BOND_SSON"
        )
        errors = self.audit(review=mutated)
        self.assertTrue(any("competitive-only event boundary changed" in e for e in errors))

    def test_manual_feedback_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["scientific_effect"]["feedback_activation_authorized"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(
            any("feedback_activation_authorized" in e for e in errors)
        )


if __name__ == "__main__":
    unittest.main()
