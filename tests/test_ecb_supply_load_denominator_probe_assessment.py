from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_ecb_supply_load_denominator_probe_assessment import (
    ASSESSMENT_PATH,
    audit_ecb_denominator_probe_assessment,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class ECBSupplyLoadDenominatorProbeAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assessment = load(ASSESSMENT_PATH)
        self.manifest = load(
            "data/source_vintages/ecb-supply-load-denominator-candidates-2026-09-20/"
            "ecb_denominator_probe_manifest.json"
        )
        self.denominator_review = load(
            "model/dynamics/government_securities_supply_load_denominator_boundary_review_2026_09_20.json"
        )
        self.source_review = load(
            "model/dynamics/government_securities_supply_pressure_source_boundary_review_2026_09_20.json"
        )
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.model_contract = load("model/registries/model_contract.json")

    def audit(self, **overrides):
        return audit_ecb_denominator_probe_assessment(
            overrides.get("assessment", self.assessment),
            overrides.get("manifest", self.manifest),
            overrides.get("denominator_review", self.denominator_review),
            overrides.get("source_review", self.source_review),
            overrides.get("boundary", self.boundary),
            overrides.get("model_contract", self.model_contract),
        )

    def test_current_assessment_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_csec_exact_semantics_are_retained(self) -> None:
        item = self.assessment["candidates"][
            "ecb_csec_central_government_domestic_currency_debt_securities_stock"
        ]
        dims = item["provider_metadata_validation"]
        self.assertEqual(dims["REF_SECTOR"], "S1311")
        self.assertEqual(dims["INSTR_ASSET"], "F3")
        self.assertEqual(dims["MATURITY"], "T")
        self.assertEqual(dims["UNIT_MEASURE"], "XDC")
        self.assertEqual(dims["CURRENCY_DENOM"], "XDC")
        self.assertEqual(dims["VALUATION"], "M")
        self.assertFalse(item["denominator_selected"])

    def test_gfs_domestic_exact_key_is_not_silently_substituted(self) -> None:
        item = self.assessment["candidates"][
            "ecb_gfs_general_government_domestic_currency_debt_securities_face_value_stock"
        ]
        self.assertEqual(item["provider_status"], "PREREGISTERED_EXACT_KEY_NOT_FOUND")
        self.assertEqual(item["http_status"], 404)
        self.assertFalse(item["post_hoc_substitution_performed"])
        self.assertFalse(item["denominator_selected"])

    def test_gfs_context_is_face_value_but_all_currency_s13(self) -> None:
        item = self.assessment["candidates"][
            "ecb_gfs_general_government_all_currency_debt_securities_face_value_context"
        ]
        dims = item["provider_metadata_validation"]
        self.assertEqual(dims["REF_SECTOR"], "S13")
        self.assertEqual(dims["UNIT_MEASURE"], "EUR")
        self.assertEqual(dims["CURRENCY_DENOM"], "_T")
        self.assertEqual(dims["VALUATION"], "F")
        self.assertFalse(item["denominator_selected"])

    def test_no_candidate_ratio_or_selection_is_performed(self) -> None:
        cross = self.assessment["cross_candidate_assessment"]
        self.assertFalse(cross["candidate_ratios_computed"])
        self.assertFalse(cross["denominator_selected"])
        self.assertFalse(cross["numerical_closeness_used_for_selection"])
        self.assertFalse(cross["fit_or_correlation_inspected_for_selection"])

    def test_manual_denominator_selection_is_detected(self) -> None:
        mutated = copy.deepcopy(self.assessment)
        mutated["scientific_effect"]["denominator_selected"] = True
        errors = self.audit(assessment=mutated)
        self.assertTrue(
            any("denominator_selected" in error for error in errors)
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
