from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_government_debt_issuance_to_debt_stock_boundary import (
    REVIEW_PATH,
    STATUS,
    audit_government_debt_issuance_to_debt_stock_boundary,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class GovernmentDebtIssuanceToDebtStockBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(REVIEW_PATH)
        self.debt_assessment = load("model/dynamics/government_debt_stock_reference_assessment.json")
        self.debt_snapshot = load("model/dynamics/government_debt_stock_reference_snapshot.json")
        self.financing = load("model/dynamics/mof_realized_financing_channel_source_vintage_assessment_2026_09_21.json")
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.prereg = load("model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json")
        self.model_contract = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")

    def audit(self, **overrides):
        return audit_government_debt_issuance_to_debt_stock_boundary(
            overrides.get("review", self.review),
            overrides.get("debt_assessment", self.debt_assessment),
            overrides.get("debt_snapshot", self.debt_snapshot),
            overrides.get("financing", self.financing),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("feedback", self.feedback),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
            overrides.get("baseline", self.baseline),
        )

    def test_current_boundary_review_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_2025_edp_table3a_identity_reconciles(self) -> None:
        c = self.review["official_definition_evidence"]["romania_april_2026_edp_table_3a_2025"]["displayed_2025_components"]
        self.assertEqual(
            c["deficit_contribution_positive_table3_sign"]
            + c["net_acquisition_financial_assets"]
            + c["adjustments"]
            + c["statistical_discrepancies"],
            c["change_in_consolidated_gross_debt"],
        )
        self.assertEqual(c["change_in_consolidated_gross_debt"], 172516)

    def test_gross_borrowing_cannot_equal_stock_change(self) -> None:
        self.assertFalse(
            self.review["accounting_boundary"]["gross_borrowing_equals_change_in_Maastricht_debt"]
        )
        self.assertFalse(
            self.review["bridge_resolution"]["one_to_one_gross_borrowing_to_stock_change_authorized"]
        )

    def test_unmatched_residual_cannot_be_called_redemptions(self) -> None:
        self.assertFalse(
            self.review["bridge_resolution"][
                "residual_redemptions_as_gross_borrowing_minus_stock_change_authorized"
            ]
        )

    def test_manual_one_to_one_mapping_is_detected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["bridge_resolution"]["one_to_one_gross_borrowing_to_stock_change_authorized"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(any("one_to_one_gross_borrowing_to_stock_change_authorized" in e for e in errors))

    def test_feedback_link_uses_stock_accumulation_boundary_status(self) -> None:
        row = next(
            x for x in self.readiness["links"]
            if x["loop_id"] == "government_refinancing_interest_loop"
            and x["from"] == "government_debt_issuance"
            and x["to"] == "government_debt_stock"
        )
        self.assertEqual(row["readiness_status"], STATUS)
        self.assertFalse(row["exact_integrated_equation_ready"])
        self.assertFalse(row["current_activation_authorized"])


if __name__ == "__main__":
    unittest.main()
