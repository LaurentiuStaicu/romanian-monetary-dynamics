from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_interest_cost_to_financing_need_boundary import (
    PREREG_PATH,
    REVIEW_PATH,
    audit_interest_cost_to_financing_need_boundary,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class InterestCostToFinancingNeedBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(REVIEW_PATH)
        self.refinancing = load("model/dynamics/government_refinancing_need_reference_assessment.json")
        self.fiscal_contract = load("model/calibration_validation/fiscal_primary_balance_materialisation_contract.json")
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.prereg = load(PREREG_PATH)
        self.model_contract = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")

    def audit(self, **overrides):
        return audit_interest_cost_to_financing_need_boundary(
            overrides.get("review", self.review),
            overrides.get("refinancing", self.refinancing),
            overrides.get("fiscal_contract", self.fiscal_contract),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("feedback", self.feedback),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
            overrides.get("baseline", self.baseline),
        )

    def test_current_review_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_headline_deficit_form_cannot_add_interest_twice(self) -> None:
        headline = self.review["accounting_forms"]["headline_deficit_form"]
        self.assertFalse(headline["interest_cost_explicit_separate_addend"])
        self.assertTrue(headline["double_counting_if_interest_added_again"])

    def test_primary_deficit_form_contains_interest_exactly_once(self) -> None:
        primary = self.review["accounting_forms"]["primary_deficit_form"]
        self.assertTrue(primary["interest_cost_explicit_separate_addend"])
        self.assertTrue(primary["requires_matched_component_boundaries"])

    def test_ministry_examples_reconcile_but_are_not_canonical(self) -> None:
        evidence = self.review["official_definition_evidence"]["ministry_operational_examples"]
        for row in evidence["examples_bn_RON"].values():
            self.assertAlmostEqual(
                row["budget_deficit"] + row["government_debt_refinancing"],
                row["reported_gross_financing_need"],
            )
        self.assertFalse(
            self.review["accounting_forms"]["ministry_operational_form"][
                "canonical_for_dynamic_core_now"
            ]
        )

    def test_manual_interest_double_counting_is_detected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["accounting_forms"]["headline_deficit_form"][
            "interest_cost_explicit_separate_addend"
        ] = True
        errors = self.audit(review=mutated)
        self.assertTrue(any("headline deficit" in error for error in errors))

    def test_manual_feedback_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["scientific_effect"]["feedback_activation_authorized"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(any("feedback_activation_authorized" in error for error in errors))


if __name__ == "__main__":
    unittest.main()
