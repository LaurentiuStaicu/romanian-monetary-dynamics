from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_mof_supply_pressure_source_vintage_probe_assessment import (
    ASSESSMENT_PATH,
    audit_mof_supply_pressure_probe_assessment,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class MOFSupplyPressureProbeAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assessment = load(ASSESSMENT_PATH)
        self.manifest = load(
            "data/source_vintages/mof-supply-pressure-probe-vintage-2026-09-20/"
            "source_vintage_probe_manifest.json"
        )
        self.source_review = load(
            "model/dynamics/government_securities_supply_pressure_source_boundary_review_2026_09_20.json"
        )
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.model_contract = load("model/registries/model_contract.json")

    def audit(self, **overrides):
        return audit_mof_supply_pressure_probe_assessment(
            overrides.get("assessment", self.assessment),
            overrides.get("manifest", self.manifest),
            overrides.get("source_review", self.source_review),
            overrides.get("boundary", self.boundary),
            overrides.get("model_contract", self.model_contract),
        )

    def test_current_assessment_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_january_exact_values_are_frozen(self) -> None:
        january = self.assessment["extractability_results"][
            "flash_auction_table_native_text"
        ]["january_2025"]
        self.assertEqual(january["total_announced_RON_million"], 5770.0)
        self.assertEqual(january["total_borrowed_RON_million"], 7556.97)
        self.assertTrue(january["safe_as_exact_descriptive_values"])

    def test_february_borrowed_value_is_not_final_month_claim(self) -> None:
        february = self.assessment["extractability_results"][
            "flash_auction_table_native_text"
        ]["february_2025"]
        self.assertEqual(february["total_announced_RON_million"], 8040.0)
        self.assertEqual(february["borrowed_total_shown_RON_million"], 4207.01)
        self.assertFalse(february["safe_as_final_full_month_borrowed_total"])

    def test_denominator_remains_unselected(self) -> None:
        stock = self.assessment["extractability_results"][
            "january_stock_denominator_candidates"
        ]
        self.assertEqual(
            stock[
                "monthly_report_RON_denom_domestic_market_securities_available_at_nominal_value_LEI_million"
            ],
            381933.8,
        )
        self.assertFalse(stock["flash_components_arithmetically_reconcile_to_flash_total"])
        self.assertFalse(stock["denominator_selected"])

    def test_submitted_bids_remain_blocked(self) -> None:
        chart = self.assessment["extractability_results"][
            "monthly_report_bid_to_cover_chart"
        ]
        self.assertFalse(
            chart["month_to_series_numeric_mapping_reproducible_from_native_text_only"]
        )
        self.assertFalse(chart["submitted_bids_series_materialisation_authorized"])
        self.assertFalse(chart["bid_to_cover_series_materialisation_authorized"])

    def test_manual_pressure_ratio_authorization_is_detected(self) -> None:
        mutated = copy.deepcopy(self.assessment)
        mutated["candidate_readiness"]["domestic_RON_primary_market_supply_load"][
            "ratio_materialisation_authorized"
        ] = True
        errors = self.audit(assessment=mutated)
        self.assertTrue(
            any("supply-load ratio may not be materialised" in error for error in errors)
        )

    def test_manual_feedback_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.assessment)
        mutated["scientific_effect"]["feedback_activation_authorized"] = True
        errors = self.audit(assessment=mutated)
        self.assertTrue(
            any("feedback_activation_authorized" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
