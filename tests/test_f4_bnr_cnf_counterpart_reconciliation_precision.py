from __future__ import annotations

import unittest

from scripts.audit_f4_bnr_cnf_counterpart_reconciliation_precision import (
    SEMANTIC_REQUIRED_CHECKS,
    assess_documented_precision_reconciliation,
    assess_f4_counterpart_reconciliation,
    audit_f4_bnr_cnf_counterpart_reconciliation_precision,
)


def term(
    value: str,
    resolution: str,
    *,
    basis: str = "OFFICIAL_METADATA",
    coefficient: str = "1",
    factor: str = "1",
    source_unit: str = "million RON",
    rounding_mode: str | None = None,
) -> dict[str, str]:
    if rounding_mode is None:
        rounding_mode = (
            "EXACT"
            if resolution in {"0", "0.0", "0.00"} and basis == "OFFICIAL_SOURCE_EXACTNESS_STATEMENT"
            else "NEAREST"
        )
    return {
        "source_value": value,
        "source_unit": source_unit,
        "unit_conversion_factor_to_million_RON": factor,
        "source_resolution": resolution,
        "rounding_mode": rounding_mode,
        "precision_basis": basis,
        "source_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: value",
        "precision_evidence_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: precision evidence",
        "coefficient": coefficient,
    }


def target(
    value: str,
    resolution: str = "0.1",
    *,
    basis: str = "OFFICIAL_METADATA",
    factor: str = "1",
    source_unit: str = "million RON",
    rounding_mode: str | None = None,
) -> dict[str, str]:
    if rounding_mode is None:
        rounding_mode = (
            "EXACT"
            if resolution in {"0", "0.0", "0.00"} and basis == "OFFICIAL_SOURCE_EXACTNESS_STATEMENT"
            else "NEAREST"
        )
    return {
        "source_value": value,
        "source_unit": source_unit,
        "unit_conversion_factor_to_million_RON": factor,
        "source_resolution": resolution,
        "rounding_mode": rounding_mode,
        "precision_basis": basis,
        "source_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: target value",
        "precision_evidence_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: target precision evidence",
    }


def semantic_assessment(**overrides: object) -> dict[str, object]:
    assessment: dict[str, object] = {key: True for key in SEMANTIC_REQUIRED_CHECKS}
    assessment["evidence_locators"] = {
        key: f"TEST_FIXTURE_NOT_SOURCE_DATA: semantic evidence for {key}"
        for key in SEMANTIC_REQUIRED_CHECKS
    }
    assessment.update(overrides)
    return assessment


class F4BNRCNFDocumentedPrecisionTests(unittest.TestCase):
    def test_canonical_preregistration_audit_passes(self) -> None:
        self.assertEqual(audit_f4_bnr_cnf_counterpart_reconciliation_precision(), [])

    def test_passes_within_documented_source_rounding_envelope(self) -> None:
        result = assess_documented_precision_reconciliation(
            [term("6.0", "0.1"), term("0.0", "0.1", basis="EXPLICIT_OFFICIAL_ROUNDING_STATEMENT")],
            target("6.1"),
        )
        self.assertEqual(
            result["status"],
            "PRECISION_AND_RECONCILIATION_PASS_ELIGIBLE_FOR_BASE_F4_TRIGGER_ADJUDICATION",
        )
        self.assertEqual(result["rounding_envelope_million_RON"], "0.15")
        self.assertEqual(result["residual_million_RON"], "-0.1")

    def test_fails_outside_documented_rounding_envelope(self) -> None:
        result = assess_documented_precision_reconciliation(
            [term("6.0", "0.1"), term("0.0", "0.1")],
            target("6.3"),
        )
        self.assertEqual(result["status"], "RECONCILIATION_FAIL_KEEP_F4_CLOSED")
        self.assertEqual(result["rounding_envelope_million_RON"], "0.15")

    def test_missing_precision_basis_never_passes(self) -> None:
        result = assess_documented_precision_reconciliation(
            [term("6", "1", basis="DISPLAYED_INTEGER_FORMAT_ONLY")],
            target("6"),
        )
        self.assertEqual(result["status"], "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED")

    def test_missing_resolution_never_passes(self) -> None:
        item = term("6", "1")
        item.pop("source_resolution")
        result = assess_documented_precision_reconciliation([item], target("6"))
        self.assertEqual(result["status"], "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED")

    def test_zero_with_nonzero_resolution_is_not_exact_zero(self) -> None:
        result = assess_documented_precision_reconciliation(
            [term("0", "1")],
            target("0", "1"),
        )
        self.assertEqual(
            result["status"],
            "PRECISION_AND_RECONCILIATION_PASS_ELIGIBLE_FOR_BASE_F4_TRIGGER_ADJUDICATION",
        )
        self.assertEqual(result["rounding_envelope_million_RON"], "1")

    def test_large_decimal_inputs_remain_exact_beyond_decimal_context_precision(self) -> None:
        value = "123456789012345678901234567890.1234567890123456789"
        result = assess_documented_precision_reconciliation(
            [term(value, "0.0000000000000000002")],
            target(value, "0", basis="OFFICIAL_SOURCE_EXACTNESS_STATEMENT"),
        )
        self.assertEqual(
            result["status"],
            "PRECISION_AND_RECONCILIATION_PASS_ELIGIBLE_FOR_BASE_F4_TRIGGER_ADJUDICATION",
        )
        self.assertEqual(result["residual_million_RON"], "0")
        self.assertEqual(result["counterpart_sum_million_RON"], value)
        self.assertEqual(result["target_million_RON"], value)
        self.assertEqual(
            result["rounding_envelope_million_RON"],
            "0.0000000000000000001",
        )

    def test_exact_unit_conversion_is_applied_to_values_and_resolutions(self) -> None:
        result = assess_documented_precision_reconciliation(
            [
                term("6000", "100", factor="0.001", source_unit="thousand RON"),
                term("0", "100", factor="0.001", source_unit="thousand RON"),
            ],
            target("6.1", "0.1"),
        )
        self.assertEqual(
            result["status"],
            "PRECISION_AND_RECONCILIATION_PASS_ELIGIBLE_FOR_BASE_F4_TRIGGER_ADJUDICATION",
        )
        self.assertEqual(result["counterpart_sum_million_RON"], "6")
        self.assertEqual(result["rounding_envelope_million_RON"], "0.15")
        self.assertEqual(result["residual_million_RON"], "-0.1")

    def test_zero_resolution_requires_explicit_exactness_basis(self) -> None:
        result = assess_documented_precision_reconciliation(
            [term("6", "0", basis="OFFICIAL_METADATA")],
            target("6", "0", basis="OFFICIAL_SOURCE_EXACTNESS_STATEMENT"),
        )
        self.assertEqual(result["status"], "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED")

    def test_missing_precision_evidence_locator_never_passes(self) -> None:
        item = term("6", "0.1")
        item.pop("precision_evidence_locator")
        result = assess_documented_precision_reconciliation([item], target("6"))
        self.assertEqual(result["status"], "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED")

    def test_missing_rounding_mode_never_passes(self) -> None:
        item = term("6", "0.1")
        item.pop("rounding_mode")
        result = assess_documented_precision_reconciliation([item], target("6"))
        self.assertEqual(result["status"], "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED")

    def test_truncation_cannot_be_treated_as_nearest_rounding(self) -> None:
        result = assess_documented_precision_reconciliation(
            [term("6", "0.1", rounding_mode="TRUNCATE")],
            target("6"),
        )
        self.assertEqual(result["status"], "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED")

    def test_exact_additive_subsector_terms_have_separate_precision_contributions(self) -> None:
        result = assess_documented_precision_reconciliation(
            [
                term("2", "1", coefficient="1"),
                term("3", "1", coefficient="1"),
                term("1", "1", coefficient="1"),
            ],
            target("6", "1"),
        )
        self.assertEqual(result["rounding_envelope_million_RON"], "2")
        self.assertEqual(result["status"], "PRECISION_AND_RECONCILIATION_PASS_ELIGIBLE_FOR_BASE_F4_TRIGGER_ADJUDICATION")


    def test_combined_reconciliation_requires_semantic_gate(self) -> None:
        result = assess_f4_counterpart_reconciliation(
            [term("6.0", "0.1"), term("0.0", "0.1")],
            target("6.1"),
            semantic_assessment(self_counterpart_boundary_resolved=False),
        )
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_missing_semantic_evidence_locator_blocks_numeric_eligibility(self) -> None:
        evidence = {
            key: f"TEST_FIXTURE_NOT_SOURCE_DATA: semantic evidence for {key}"
            for key in SEMANTIC_REQUIRED_CHECKS
        }
        evidence.pop("sector_mapping_h_c_f_g_x_verified")
        result = assess_f4_counterpart_reconciliation(
            [term("6.0", "0.1"), term("0.0", "0.1")],
            target("6.1"),
            semantic_assessment(evidence_locators=evidence),
        )
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_complete_semantic_and_precision_checks_only_yield_trigger_adjudication_eligibility(self) -> None:
        result = assess_f4_counterpart_reconciliation(
            [term("6.0", "0.1"), term("0.0", "0.1")],
            target("6.1"),
            semantic_assessment(),
        )
        self.assertEqual(
            result["status"],
            "PRECISION_AND_RECONCILIATION_PASS_ELIGIBLE_FOR_BASE_F4_TRIGGER_ADJUDICATION",
        )
        self.assertFalse(result["status"] == "F4_STOCK_GATE_OPEN")


if __name__ == "__main__":
    unittest.main()
