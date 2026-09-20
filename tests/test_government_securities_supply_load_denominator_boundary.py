from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_government_securities_supply_load_denominator_boundary import (
    REVIEW_PATH,
    audit_supply_load_denominator_boundary,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class GovernmentSecuritiesSupplyLoadDenominatorBoundaryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.review = load(REVIEW_PATH)
        self.source_review = load(
            "model/dynamics/government_securities_supply_pressure_source_boundary_review_2026_09_20.json"
        )
        self.probe = load(
            "model/dynamics/government_securities_supply_pressure_source_vintage_probe_assessment_2026_09_20.json"
        )
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.prereg = load(
            "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
        )
        self.model_contract = load("model/registries/model_contract.json")

    def audit(self, **overrides):
        return audit_supply_load_denominator_boundary(
            overrides.get("review", self.review),
            overrides.get("source_review", self.source_review),
            overrides.get("probe", self.probe),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
        )

    def test_current_denominator_review_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_no_denominator_is_selected(self) -> None:
        self.assertFalse(
            self.review["decision_effect"]["mof_holdings_denominator_selected"]
        )
        self.assertFalse(
            self.review["decision_effect"]["ecb_csec_denominator_selected"]
        )
        self.assertFalse(
            self.review["decision_effect"]["ecb_gfs_denominator_selected"]
        )
        self.assertFalse(
            self.review["decision_effect"]["supply_load_ratio_materialisation_authorized"]
        )

    def test_ministry_nominal_candidate_is_exact_but_not_equivalent(self) -> None:
        item = next(
            x for x in self.review["denominator_candidates"]
            if x["candidate_id"] == "mof_RON_domestic_market_holdings_nominal"
        )
        self.assertEqual(item["january_2025_exact_value_RON_million"], 381933.8)
        self.assertEqual(item["valuation"], "available at nominal value")
        self.assertFalse(item["exact_auction_universe_equivalence_established"])
        self.assertFalse(item["selected"])

    def test_ecb_candidates_preserve_known_tradeoffs(self) -> None:
        items = {x["candidate_id"]: x for x in self.review["denominator_candidates"]}
        self.assertEqual(
            items["ecb_csec_central_government_domestic_currency_debt_securities_stock"]["valuation"],
            "market value",
        )
        self.assertEqual(
            items["ecb_gfs_general_government_debt_securities_face_value_stock"]["valuation"],
            "face value",
        )
        self.assertEqual(
            items["ecb_gfs_general_government_debt_securities_face_value_stock"]["sector_boundary"],
            "general government (S13)",
        )

    def test_flash_headline_is_not_eligible_denominator(self) -> None:
        check = self.review["flash_report_consistency_check"]
        self.assertFalse(check["components_reconcile_to_headline"])
        self.assertFalse(check["eligible_as_denominator"])

    def test_manual_denominator_selection_is_detected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["decision_effect"]["mof_holdings_denominator_selected"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(
            any("mof_holdings_denominator_selected" in error for error in errors)
        )

    def test_manual_feedback_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.review)
        mutated["decision_effect"]["feedback_activation_authorized"] = True
        errors = self.audit(review=mutated)
        self.assertTrue(
            any("feedback_activation_authorized" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
