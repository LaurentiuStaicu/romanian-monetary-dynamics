from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_mof_announced_RON_primary_supply_reference_mode_contract import (
    CONTRACT_PATH,
    audit_announced_supply_reference_mode_contract,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class AnnouncedRONPrimarySupplyReferenceModeContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load(CONTRACT_PATH)
        self.measurement_design = load(
            "model/dynamics/government_securities_supply_measurement_design_review_2026_09_20.json"
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
        return audit_announced_supply_reference_mode_contract(
            overrides.get("contract", self.contract),
            overrides.get("measurement_design", self.measurement_design),
            overrides.get("source_review", self.source_review),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("feedback", self.feedback),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
        )

    def test_current_contract_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_article_1_totals_reconcile(self) -> None:
        for item in self.contract["pilot_source_documents"]:
            self.assertEqual(
                item["article_1_base_nominal_RON_million"]
                + item["article_1_SSON_max_RON_million"],
                item["article_1_document_total_RON_million"],
            )

    def test_t_bills_benchmark_and_sson_are_separate_components(self) -> None:
        self.assertEqual(
            set(self.contract["event_schema"]["allowed_event_types"]),
            {
                "T_BILL_COMPETITIVE_REFERENCE_AUCTION",
                "BENCHMARK_BOND_COMPETITIVE_REFERENCE_AUCTION",
                "BENCHMARK_BOND_SSON",
            },
        )

    def test_monthly_bucket_uses_event_date(self) -> None:
        rule = self.contract["aggregation_rules"]["monthly_bucket_rule"]
        self.assertIn("event_date", rule)
        self.assertIn("Data licitatiei", rule)
        self.assertIn("Data SSON", rule)

    def test_no_stock_denominator_or_realised_borrowing(self) -> None:
        concept = self.contract["concept"]
        self.assertFalse(concept["stock_normalisation_required"])
        self.assertTrue(
            concept["accepted_or_borrowed_amount_is_not_part_of_measure"]
        )

    def test_contract_alone_cannot_promote_reference_mode(self) -> None:
        self.assertFalse(
            self.contract["materialisation_gate"][
                "reference_mode_promotion_authorized_by_contract_alone"
            ]
        )

    def test_manual_feedback_activation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["scientific_guards"]["feedback_activation_authorized"] = True
        errors = self.audit(contract=mutated)
        self.assertTrue(
            any("feedback_activation_authorized" in error for error in errors)
        )


if __name__ == "__main__":
    unittest.main()
