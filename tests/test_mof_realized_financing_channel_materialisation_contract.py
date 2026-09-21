from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_mof_realized_financing_channel_materialisation_contract import (
    CONTRACT_PATH,
    FINANCING_REVIEW_PATH,
    PREREG_PATH,
    audit_mof_realized_financing_channel_materialisation_contract,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class MOFRealizedFinancingChannelMaterialisationContractTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = load(CONTRACT_PATH)
        self.generic_contract = load(
            "model/dynamics/government_debt_issuance_materialisation_contract.json"
        )
        self.financing_review = load(FINANCING_REVIEW_PATH)
        self.boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
        self.readiness = load("model/dynamics/feedback_link_readiness_registry.json")
        self.prereg = load(PREREG_PATH)
        self.model_contract = load("model/registries/model_contract.json")
        self.baseline = load("model/registries/scientific_baseline_manifest.json")

    def audit(self, **overrides):
        return audit_mof_realized_financing_channel_materialisation_contract(
            overrides.get("contract", self.contract),
            overrides.get("generic_contract", self.generic_contract),
            overrides.get("financing_review", self.financing_review),
            overrides.get("boundary", self.boundary),
            overrides.get("readiness", self.readiness),
            overrides.get("prereg", self.prereg),
            overrides.get("model_contract", self.model_contract),
            overrides.get("baseline", self.baseline),
        )

    def test_current_contract_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_monthly_differencing_is_blocked(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["monthly_increment_gate"]["monthly_differencing_authorized_now"] = True
        errors = self.audit(contract=mutated)
        self.assertTrue(any("monthly differencing may not be authorized" in e for e in errors))

    def test_rff_and_loans_cannot_be_relabelled_securities(self) -> None:
        mutated = copy.deepcopy(self.contract)
        item = next(
            x for x in mutated["required_observables"]
            if x["field_id"] == "rrf_pnrr_loan_drawings_cumulative_ytd"
        )
        item["securities_instrument"] = True
        errors = self.audit(contract=mutated)
        self.assertTrue(any("RRF drawings may not be relabelled securities" in e for e in errors))

    def test_bnr_series_cannot_be_inferred_by_subtraction(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["channel_boundary_rules"]["BNR_series_may_not_be_inferred_by_subtraction"] = False
        errors = self.audit(contract=mutated)
        self.assertTrue(any("BNR series may not be inferred by subtraction" in e for e in errors))

    def test_conversion_convention_may_not_be_assumed_stable(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["currency_and_conversion_contract"][
            "same_conversion_convention_may_not_be_assumed_across_vintages"
        ] = False
        errors = self.audit(contract=mutated)
        self.assertTrue(
            any("same_conversion_convention_may_not_be_assumed_across_vintages" in e for e in errors)
        )

    def test_negative_ytd_difference_needs_revision_or_operation_review(self) -> None:
        mutated = copy.deepcopy(self.contract)
        mutated["revision_and_vintage_contract"][
            "negative_difference_may_not_be_interpreted_as_negative_borrowing_without_revision_or_operation_review"
        ] = False
        errors = self.audit(contract=mutated)
        self.assertTrue(
            any("negative_difference_may_not_be_interpreted" in e for e in errors)
        )

    def test_next_gate_allows_only_raw_and_cumulative_materialisation(self) -> None:
        gate = self.contract["next_gate"]
        self.assertEqual(gate["id"], "mof_realized_financing_channel_source_vintage_probe")
        self.assertTrue(gate["may_retain_raw_sources"])
        self.assertTrue(gate["may_extract_published_cumulative_ytd_values"])
        self.assertFalse(gate["may_difference_cumulative_values"])
        self.assertFalse(gate["may_infer_channel_residuals"])
        self.assertFalse(gate["may_estimate_allocation_shares"])
        self.assertFalse(gate["may_activate_feedback"])


if __name__ == "__main__":
    unittest.main()
