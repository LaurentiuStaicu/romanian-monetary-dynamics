from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_mof_announced_RON_primary_reference_auction_missing_source_recovery import (
    ASSESSMENT_PATH,
    PARTIAL_PATH,
    audit_missing_source_recovery,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class MOFAnnouncedSupplyMissingSourceRecoveryTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assessment = load(ASSESSMENT_PATH)
        self.partial = load(PARTIAL_PATH)
        self.measurement = load(
            "model/dynamics/government_securities_supply_measurement_design_review_2026_09_20.json"
        )
        self.source_review = load(
            "model/dynamics/government_securities_supply_pressure_source_boundary_review_2026_09_20.json"
        )
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.prereg = load(
            "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
        )
        self.model_contract = load("model/registries/model_contract.json")

    def audit(self, **overrides):
        return audit_missing_source_recovery(
            overrides.get("assessment", self.assessment),
            overrides.get("partial", self.partial),
            overrides.get("measurement", self.measurement),
            overrides.get("source_review", self.source_review),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
        )

    def test_current_recovery_hold_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_five_sources_are_recovered_and_three_remain_blocked(self) -> None:
        current = self.assessment["current_materialisation"]
        self.assertEqual(current["retained_required_source_count"], 9)
        self.assertEqual(current["required_missing_source_count"], 3)
        self.assertEqual(current["exact_final_month_count"], 10)
        self.assertEqual(current["event_level_complete_final_month_count"], 9)
        self.assertEqual(len(self.assessment["recovered_sources"]), 5)
        self.assertEqual(len(self.assessment["missing_sources"]), 3)
        interpretation = self.assessment["interpretation"]
        self.assertFalse(interpretation["documents_do_not_exist"])
        self.assertFalse(interpretation["public_legal_identity_is_unavailable"])
        self.assertTrue(
            interpretation["remaining_repository_raw_retention_is_currently_unavailable"]
        )

    def test_web_snippets_and_third_party_sources_cannot_be_raw_sources(self) -> None:
        interpretation = self.assessment["interpretation"]
        self.assertFalse(interpretation["web_search_snippets_may_be_repository_raw_sources"])
        self.assertFalse(interpretation["third_party_reproductions_may_be_repository_raw_sources"])

    def test_recovery_is_evidence_triggered_not_polled(self) -> None:
        disposition = self.assessment["path_disposition"]
        self.assertEqual(disposition["state"], "EVIDENCE_TRIGGERED_HOLD")
        self.assertFalse(disposition["active_polling"])

    def test_manual_imputation_authorization_is_detected(self) -> None:
        mutated = copy.deepcopy(self.assessment)
        mutated["interpretation"]["missing_values_may_be_imputed"] = True
        errors = self.audit(assessment=mutated)
        self.assertTrue(any("missing_values_may_be_imputed" in e for e in errors))

    def test_manual_feedback_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.assessment)
        mutated["scientific_effect"]["feedback_activation_authorized"] = True
        errors = self.audit(assessment=mutated)
        self.assertTrue(any("feedback_activation_authorized" in e for e in errors))


if __name__ == "__main__":
    unittest.main()
