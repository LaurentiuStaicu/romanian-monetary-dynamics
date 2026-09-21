from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_mof_realized_financing_channel_source_vintage_assessment import (
    ASSESSMENT_PATH,
    MANIFEST_PATH,
    PREREG_PATH,
    audit_mof_realized_financing_channel_source_vintage_assessment,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class MOFRealizedFinancingChannelSourceVintageAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assessment = load(ASSESSMENT_PATH)
        self.manifest = load(MANIFEST_PATH)
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.prereg = load(PREREG_PATH)
        self.model_contract = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")

    def audit(self, **overrides):
        return audit_mof_realized_financing_channel_source_vintage_assessment(
            overrides.get("assessment", self.assessment),
            overrides.get("manifest", self.manifest),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("feedback", self.feedback),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
            overrides.get("baseline", self.baseline),
        )

    def test_current_assessment_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_all_twelve_reports_are_retained(self) -> None:
        self.assertEqual(self.manifest["available_report_count"], 12)
        self.assertEqual(self.manifest["unavailable_report_count"], 0)
        self.assertEqual(
            self.manifest["available_periods"],
            [f"2025-{month:02d}" for month in range(1, 13)],
        )

    def test_conversion_basis_is_not_stable_across_year(self) -> None:
        self.assertFalse(
            self.assessment["definition_stability"][
                "same_RON_equivalent_conversion_basis_all_year"
            ]
        )
        self.assertEqual(len(self.assessment["conversion_regimes"]), 4)

    def test_monthly_differencing_is_blocked(self) -> None:
        mutated = copy.deepcopy(self.assessment)
        mutated["materialisation_disposition"]["monthly_increment_equation_authorized"] = True
        errors = self.audit(assessment=mutated)
        self.assertTrue(
            any("monthly_increment_equation_authorized" in e for e in errors)
        )

    def test_eurobond_non_monotonicity_is_frozen(self) -> None:
        euro = [
            item for item in self.assessment["non_monotone_cumulative_diagnostics"]
            if item["field"] == "eurobonds_cumulative_ytd"
        ]
        self.assertEqual(
            {
                (item["transition"], item["change_million_RON_equivalent"])
                for item in euro
            },
            {
                ("2025-10_to_2025-11", -500.0),
                ("2025-11_to_2025-12", -5040.0),
            },
        )

    def test_no_generic_node_promotion_or_feedback_activation(self) -> None:
        effect = self.assessment["scientific_effect"]
        self.assertFalse(effect["government_debt_issuance_node_resolved"])
        self.assertFalse(effect["government_financing_need_node_resolved"])
        self.assertFalse(effect["monthly_realized_financing_flow_series_created"])
        self.assertFalse(effect["feedback_activation_authorized"])

    def test_next_gate_is_debt_issuance_to_stock_review(self) -> None:
        gate = self.assessment["next_independent_gate"]
        self.assertEqual(
            gate["id"],
            "government_debt_issuance_to_debt_stock_boundary_review",
        )
        self.assertFalse(
            gate["may_map_gross_borrowing_one_to_one_to_debt_stock_change"]
        )
        self.assertFalse(gate["may_treat_exchange_operations_as_net_new_debt"])
        self.assertFalse(gate["may_estimate_parameters"])
        self.assertFalse(gate["may_activate_feedback"])


if __name__ == "__main__":
    unittest.main()
