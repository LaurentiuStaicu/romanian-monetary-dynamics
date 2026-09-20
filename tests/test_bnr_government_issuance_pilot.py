from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_bnr_government_issuance_pilot import audit_bnr_issuance_pilot

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class BNRGovernmentIssuancePilotTests(unittest.TestCase):
    def setUp(self) -> None:
        self.snapshot = load(
            "model/dynamics/government_debt_issuance_bnr_pilot_2025.json"
        )
        self.revision = load(
            "model/dynamics/government_debt_issuance_bnr_revision_assessment_2025.json"
        )
        self.review = load(
            "model/dynamics/government_debt_issuance_source_boundary_review.json"
        )
        self.contract = load(
            "model/dynamics/government_debt_issuance_materialisation_contract.json"
        )
        self.boundary = load(
            "model/dynamics/feedback_variable_boundary_registry.json"
        )
        self.reference_modes = load("model/dynamics/reference_modes.json")

    def audit(self, snapshot=None, revision=None):
        return audit_bnr_issuance_pilot(
            snapshot or self.snapshot,
            revision or self.revision,
            self.review,
            self.contract,
            self.boundary,
            self.reference_modes,
        )

    def test_current_full_year_pilot_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_all_four_2025_quarters_are_complete(self) -> None:
        checks = self.snapshot["derived_checks"]
        for quarter in ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"):
            self.assertTrue(checks[quarter]["complete_three_months"])
        self.assertTrue(checks["all_four_quarters_complete"])
        self.assertEqual(checks["full_year_RON_total_million"], 98905.8)
        self.assertEqual(checks["full_year_EUR_total_million"], 1856.1)

    def test_revision_check_exactly_preserves_original_jan_jul_cells(self) -> None:
        result = self.revision["result"]
        self.assertTrue(result["revision_check_completed"])
        self.assertEqual(result["exact_matches"], 28)
        self.assertEqual(result["changed_cells"], 0)
        self.assertEqual(result["revised_periods"], [])
        self.assertEqual(
            result["jan_jul_revision_status"],
            "PASS_NO_CHANGES_AT_PUBLISHED_PRECISION",
        )

    def test_native_currency_separation_is_preserved(self) -> None:
        may = next(
            row for row in self.snapshot["monthly_observations"]
            if row["period"] == "2025-05"
        )
        august = next(
            row for row in self.snapshot["monthly_observations"]
            if row["period"] == "2025-08"
        )
        self.assertEqual(
            may["total_EUR_domestic_primary_market_securities_million_EUR"],
            1625.1,
        )
        self.assertEqual(
            august["total_EUR_domestic_primary_market_securities_million_EUR"],
            231.0,
        )
        self.assertFalse(
            self.snapshot["extraction"]["EUR_to_RON_conversion_performed"]
        )

    def test_exact_source_boundary_is_not_broader_government_borrowing(self) -> None:
        semantics = self.snapshot["semantics"]
        self.assertTrue(
            semantics["gross_issuance_equivalent_on_exact_source_boundary"]
        )
        self.assertFalse(semantics["total_government_borrowing_equivalent"])
        self.assertFalse(semantics["refinancing_need_equivalent"])
        self.assertFalse(semantics["supply_pressure_equivalent"])

    def test_revision_and_raw_retention_gates_are_closed_without_promotion(self) -> None:
        extraction = self.snapshot["extraction"]
        self.assertTrue(extraction["source_revision_check_performed"])
        self.assertFalse(
            extraction["promotion_blocked_by_raw_retention_and_revision_gate"]
        )
        self.assertFalse(extraction["promotion_blocked_by_raw_retention_gate"])
        self.assertTrue(extraction["raw_pdf_retained_in_repository"])
        self.assertEqual(
            extraction["raw_source_sha256"],
            "171569f159b47ceedc9d8ba6d5628a39de49a8fb18d11e13a20ac55edb39c628",
        )
        # The revision assessment itself did not close retention; the later
        # dedicated retention step did. Preserve that historical distinction.
        self.assertFalse(
            self.revision["scientific_effect"]["raw_source_retention_blocker_closed"]
        )
        self.assertTrue(
            self.snapshot["scientific_disposition"]["raw_source_retention_completed"]
        )
        self.assertFalse(
            self.snapshot["scientific_disposition"][
                "canonical_reference_mode_promoted"
            ]
        )

    def test_manual_revision_claim_change_is_detected(self) -> None:
        mutated = copy.deepcopy(self.revision)
        mutated["result"]["changed_cells"] = 1
        errors = self.audit(revision=mutated)
        self.assertTrue(
            any("Jan-Jul revision comparison changed" in error for error in errors)
        )

    def test_manual_generic_node_promotion_is_detected(self) -> None:
        mutated = copy.deepcopy(self.snapshot)
        mutated["scientific_disposition"][
            "generic_government_debt_issuance_node_resolved"
        ] = True
        errors = self.audit(snapshot=mutated)
        self.assertTrue(
            any(
                "may not promote generic_government_debt_issuance_node_resolved"
                in error
                for error in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
