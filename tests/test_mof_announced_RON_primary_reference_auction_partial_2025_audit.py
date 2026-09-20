from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_mof_announced_RON_primary_reference_auction_partial_2025 import (
    ASSESSMENT_PATH,
    MANIFEST_PATH,
    audit_partial_announced_supply,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class MOFAnnouncedRONPrimaryReferenceAuctionPartial2025AuditTests(unittest.TestCase):
    def setUp(self) -> None:
        self.assessment = load(ASSESSMENT_PATH)
        self.manifest = load(MANIFEST_PATH)
        self.reference_modes = load("model/dynamics/reference_modes.json")
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.feedback = load("model/dynamics/feedback_registry.json")
        self.prereg = load(
            "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
        )
        self.model_contract = load("model/registries/model_contract.json")

    def audit(self, **overrides):
        return audit_partial_announced_supply(
            overrides.get("assessment", self.assessment),
            overrides.get("manifest", self.manifest),
            overrides.get("reference_modes", self.reference_modes),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("feedback", self.feedback),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
        )

    def test_current_partial_assessment_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_may_base_order_may_not_be_final_value(self) -> None:
        mutated = copy.deepcopy(self.assessment)
        mutated["may_base_order_history"]["final_monthly_value_authorized"] = True
        errors = self.audit(assessment=mutated)
        self.assertTrue(
            any("May base-order amount may not be promoted" in e for e in errors)
        )

    def test_missing_months_may_not_be_zero_imputed(self) -> None:
        mutated = copy.deepcopy(self.assessment)
        mutated["scientific_guards"]["missing_months_treated_as_zero"] = True
        errors = self.audit(assessment=mutated)
        self.assertTrue(
            any("missing_months_treated_as_zero" in e for e in errors)
        )

    def test_partial_candidate_may_not_become_canonical_reference_mode(self) -> None:
        mutated = copy.deepcopy(self.reference_modes)
        mutated["modes"].append(
            {
                "id": "announced_RON_primary_reference_auction_supply_level",
                "role": "FORBIDDEN_TEST_INSERTION",
            }
        )
        errors = self.audit(reference_modes=mutated)
        self.assertTrue(
            any("may not appear in canonical reference_modes" in e for e in errors)
        )

    def test_feedback_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.feedback)
        loop = next(
            item for item in mutated["loops"]
            if item["id"] == "government_issuance_yield_loop"
        )
        loop["quantitatively_active"] = True
        errors = self.audit(feedback=mutated)
        self.assertTrue(
            any("may not activate issuance-yield loop" in e for e in errors)
        )


if __name__ == "__main__":
    unittest.main()
