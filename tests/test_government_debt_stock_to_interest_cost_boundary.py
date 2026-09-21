from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_government_debt_stock_to_interest_cost_boundary import (
    REVIEW_PATH,
    STATUS,
    audit_government_debt_stock_to_interest_cost_boundary,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class GovernmentDebtStockToInterestCostBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(REVIEW_PATH)
        self.debt_assessment = load("model/dynamics/government_debt_stock_reference_assessment.json")
        self.debt_snapshot = load("model/dynamics/government_debt_stock_reference_snapshot.json")
        self.burden_assessment = load("model/dynamics/government_interest_burden_reference_assessment.json")
        self.burden_snapshot = load("model/dynamics/government_interest_burden_reference_snapshot.json")
        self.effective_rate = load("model/dynamics/government_effective_interest_rate_reference_assessment.json")
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.prereg = load("model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json")
        self.model_contract = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")

    def audit(self, **overrides):
        return audit_government_debt_stock_to_interest_cost_boundary(
            overrides.get("review", self.review),
            overrides.get("debt_assessment", self.debt_assessment),
            overrides.get("debt_snapshot", self.debt_snapshot),
            overrides.get("burden_assessment", self.burden_assessment),
            overrides.get("burden_snapshot", self.burden_snapshot),
            overrides.get("effective_rate", self.effective_rate),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("feedback", self.feedback),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
            overrides.get("baseline", self.baseline),
        )

    def test_current_boundary_review_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_debt_level_alone_cannot_determine_interest_cost(self) -> None:
        self.assertFalse(
            self.review["bridge_resolution"]["direct_debt_level_to_interest_cost_mapping_authorized"]
        )
        self.assertFalse(
            self.review["boundary_comparison"]["debt_stock_level_alone_determines_interest_expenditure"]
        )

    def test_apparent_cost_remains_diagnostic_not_reference_mode(self) -> None:
        diagnostic = self.review["official_definition_evidence"]["eurostat_apparent_cost_2025_context"]
        self.assertEqual(diagnostic["apparent_cost_pct"], 5.2)
        self.assertFalse(diagnostic["canonical_RMD_reference_mode_created"])

    def test_year_end_debt_may_not_replace_average_debt(self) -> None:
        self.assertFalse(
            self.review["bridge_resolution"]["year_end_debt_times_rate_identity_authorized"]
        )
        self.assertTrue(
            self.review["hard_rules"]["no_year_end_debt_substituted_for_average_debt"]
        )

    def test_manual_direct_mapping_is_detected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["bridge_resolution"]["direct_debt_level_to_interest_cost_mapping_authorized"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(any("direct_debt_level_to_interest_cost_mapping_authorized" in e for e in errors))

    def test_feedback_link_uses_accounting_scale_status(self) -> None:
        row = next(
            x for x in self.readiness["links"]
            if x["loop_id"] == "government_refinancing_interest_loop"
            and x["from"] == "government_debt_stock"
            and x["to"] == "government_interest_cost"
        )
        self.assertEqual(row["readiness_status"], STATUS)
        self.assertFalse(row["exact_integrated_equation_ready"])
        self.assertFalse(row["current_activation_authorized"])


if __name__ == "__main__":
    unittest.main()
