from __future__ import annotations

import unittest

from scripts.audit_f4_bnr_cnf_counterpart_reconciliation_precision import (
    FROZEN_F4_TARGET_ARTIFACT,
    FROZEN_F4_TARGET_DECIMALS_LOCATOR,
    FROZEN_F4_TARGET_SERIES_KEY,
    FROZEN_F4_TARGET_SOURCE_LOCATOR,
    FROZEN_F4_TARGET_PERIOD,
    SEMANTIC_REQUIRED_CHECKS,
    assess_documented_precision_reconciliation,
    assess_f4_counterpart_reconciliation,
    audit_f4_bnr_cnf_counterpart_reconciliation_precision,
    _production_target_value_matches,
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
    key: str | None = None,
    counterpart_group: str = "H",
    source_sector_code: str = "S14+S15",
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
        "source_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: value " + str(key or f"{source_unit}:{value}:{factor}:{coefficient}:{counterpart_group}:{source_sector_code}"),
        "precision_evidence_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: precision evidence",
        "coefficient": coefficient,
        "term_key": key or f"term:{source_unit}:{value}:{factor}:{coefficient}",
        "counterpart_group": counterpart_group,
        "source_sector_code": source_sector_code,
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
        "source_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: " + FROZEN_F4_TARGET_SOURCE_LOCATOR,
        "precision_evidence_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: target precision evidence",
        "target_key": "retained_f4_control_2025_Q4",
        "target_artifact": FROZEN_F4_TARGET_ARTIFACT,
    }


COUNTERPART_CELL_SPECS = [
    ("cell-H", "H", "S14+S15", "2.0"),
    ("cell-C", "C", "S11", "1.0"),
    ("cell-F1", "F", "S122+S123", "0.5"),
    ("cell-F2", "F", "S124+S125+S126+S127", "1.0"),
    ("cell-F3", "F", "S128+S129", "0.2"),
    ("cell-G", "G", "S13", "2.0"),
    ("cell-X", "X", "S2", "0.3"),
]


def counterpart_terms() -> list[dict[str, str]]:
    return [
        term(value, "0.1", key=key, counterpart_group=group, source_sector_code=sector_code)
        for key, group, sector_code, value in COUNTERPART_CELL_SPECS
    ]


def semantic_assessment(**overrides: object) -> dict[str, object]:
    assessment: dict[str, object] = {
        **{key: True for key in SEMANTIC_REQUIRED_CHECKS},
        "expected_term_keys": [key for key, _, _, _ in COUNTERPART_CELL_SPECS],
        "expected_source_cells": [
            {"term_key": key, "counterpart_group": group, "source_sector_code": sector_code}
            for key, group, sector_code, _ in COUNTERPART_CELL_SPECS
        ],
        "expected_target_key": "retained_f4_control_2025_Q4",
        "expected_target_artifact": FROZEN_F4_TARGET_ARTIFACT,
        "self_counterpart_disposition": "OBSERVED_BUT_EXCLUDED_FROM_TARGET_WITH_OFFICIAL_BOUNDARY_SUPPORT",
        "self_counterpart_record": {
            "term_key": "self-counterpart-S121",
            "source_sector_code": "S121",
            "source_value": "0.2",
            "source_unit": "million RON",
            "unit_conversion_factor_to_million_RON": "1",
            "source_resolution": "0.1",
            "rounding_mode": "NEAREST",
            "precision_basis": "OFFICIAL_METADATA",
            "source_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: separate S121 source cell",
            "precision_evidence_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: S121 precision",
        },
        "self_counterpart_boundary_evidence_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: S121 target boundary",
    }
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

    def test_positive_resolution_cannot_claim_exact_value_basis(self) -> None:
        result = assess_documented_precision_reconciliation(
            [term("6", "0.1", basis="OFFICIAL_SOURCE_EXACTNESS_STATEMENT", rounding_mode="NEAREST")],
            target("6", "0.1"),
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
            counterpart_terms(), target("7.1"),
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
            counterpart_terms(), target("7.1"),
            semantic_assessment(evidence_locators=evidence),
        )
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_complete_semantic_and_precision_checks_only_yield_trigger_adjudication_eligibility(self) -> None:
        result = assess_f4_counterpart_reconciliation(
            counterpart_terms(), target("7.1"), semantic_assessment()
        )
        self.assertEqual(
            result["status"],
            "PRECISION_AND_RECONCILIATION_PASS_ELIGIBLE_FOR_BASE_F4_TRIGGER_ADJUDICATION",
        )
        self.assertFalse(result["status"] == "F4_STOCK_GATE_OPEN")

    def test_omitted_counterpart_term_blocks_numerical_pass(self) -> None:
        result = assess_f4_counterpart_reconciliation(
            counterpart_terms()[:-1], target("7.1"), semantic_assessment()
        )
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_duplicate_counterpart_term_key_blocks_numerical_pass(self) -> None:
        terms = counterpart_terms()
        terms[1]["term_key"] = terms[0]["term_key"]
        result = assess_f4_counterpart_reconciliation(terms, target("7.1"), semantic_assessment())
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_unexpected_counterpart_term_blocks_numerical_pass(self) -> None:
        terms = counterpart_terms()
        terms[-1]["term_key"] = "unexpected-cell"
        result = assess_f4_counterpart_reconciliation(terms, target("7.1"), semantic_assessment())
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_target_key_must_match_frozen_retained_control(self) -> None:
        result = assess_f4_counterpart_reconciliation(
            counterpart_terms(), {**target("7.1"), "target_key": "different-control"},
            semantic_assessment(),
        )
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_non_unit_coefficient_cannot_mask_counterpart_coverage(self) -> None:
        terms = counterpart_terms()
        terms[1]["coefficient"] = "0"
        result = assess_f4_counterpart_reconciliation(terms, target("7.1"), semantic_assessment())
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_frozen_source_sector_mapping_cannot_be_relabelled(self) -> None:
        terms = counterpart_terms()
        terms[0]["source_sector_code"] = "S121"
        result = assess_f4_counterpart_reconciliation(terms, target("7.1"), semantic_assessment())
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_unresolved_s121_treatment_blocks_numeric_pass(self) -> None:
        result = assess_f4_counterpart_reconciliation(
            counterpart_terms(), target("7.1"),
            semantic_assessment(self_counterpart_disposition="UNKNOWN"),
        )
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_excluded_s121_cell_must_be_preserved_and_boundary_documented(self) -> None:
        assessment = semantic_assessment()
        assessment.pop("self_counterpart_record")
        result = assess_f4_counterpart_reconciliation(counterpart_terms(), target("7.1"), assessment)
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_included_s121_cell_requires_one_explicit_numeric_term(self) -> None:
        terms = counterpart_terms()
        terms.append(term(
            "0.2", "0.1", key="cell-S121",
            counterpart_group="BNR", source_sector_code="S121",
        ))
        assessment = semantic_assessment(
            self_counterpart_disposition="OBSERVED_AND_INCLUDED_AS_EXPLICIT_TERM",
            self_counterpart_term_key="cell-S121",
            expected_term_keys=[key for key, _, _, _ in COUNTERPART_CELL_SPECS] + ["cell-S121"],
            expected_source_cells=[
                *[
                    {"term_key": key, "counterpart_group": group, "source_sector_code": sector_code}
                    for key, group, sector_code, _ in COUNTERPART_CELL_SPECS
                ],
                {"term_key": "cell-S121", "counterpart_group": "BNR", "source_sector_code": "S121"},
            ],
        )
        assessment.pop("self_counterpart_record", None)
        result = assess_f4_counterpart_reconciliation(terms, target("7.3"), assessment)
        self.assertEqual(
            result["status"],
            "PRECISION_AND_RECONCILIATION_PASS_ELIGIBLE_FOR_BASE_F4_TRIGGER_ADJUDICATION",
        )

    def test_not_published_s121_requires_official_matrix_locator(self) -> None:
        assessment = semantic_assessment(
            self_counterpart_disposition="NOT_PUBLISHED_IN_SOURCE",
            self_counterpart_evidence_locator="",
        )
        assessment.pop("self_counterpart_record", None)
        assessment.pop("self_counterpart_boundary_evidence_locator", None)
        result = assess_f4_counterpart_reconciliation(counterpart_terms(), target("7.1"), assessment)
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")


    def test_precision_evidence_locator_must_differ_from_value_locator(self) -> None:
        item = term("6.0", "0.1")
        item["precision_evidence_locator"] = item["source_locator"]
        result = assess_documented_precision_reconciliation([item], target("6.0"))
        self.assertEqual(result["status"], "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED")

    def test_target_must_name_frozen_f4_artifact(self) -> None:
        wrong_target = {**target("7.1"), "target_artifact": "model/accounting/other_file.json"}
        result = assess_f4_counterpart_reconciliation(counterpart_terms(), wrong_target, semantic_assessment())
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_not_published_s121_path_can_pass_only_with_official_source_locator(self) -> None:
        assessment = semantic_assessment(
            self_counterpart_disposition="NOT_PUBLISHED_IN_SOURCE",
            self_counterpart_evidence_locator="TEST_FIXTURE_NOT_SOURCE_DATA: official counterpart matrix header",
        )
        assessment.pop("self_counterpart_record", None)
        assessment.pop("self_counterpart_boundary_evidence_locator", None)
        result = assess_f4_counterpart_reconciliation(counterpart_terms(), target("7.1"), assessment)
        self.assertEqual(
            result["status"],
            "PRECISION_AND_RECONCILIATION_PASS_ELIGIBLE_FOR_BASE_F4_TRIGGER_ADJUDICATION",
        )

    def test_malformed_unhashable_s121_disposition_fails_closed(self) -> None:
        result = assess_f4_counterpart_reconciliation(
            counterpart_terms(), target("7.1"),
            semantic_assessment(self_counterpart_disposition=["UNKNOWN"]),
        )
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_distinct_counterpart_cells_cannot_reuse_value_locator(self) -> None:
        terms = counterpart_terms()
        terms[1]["source_locator"] = terms[0]["source_locator"]
        result = assess_f4_counterpart_reconciliation(terms, target("7.1"), semantic_assessment())
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_target_locator_cannot_be_reused_for_counterpart_cell(self) -> None:
        terms = counterpart_terms()
        frozen_target = target("7.1")
        terms[0]["source_locator"] = frozen_target["source_locator"]
        result = assess_f4_counterpart_reconciliation(terms, frozen_target, semantic_assessment())
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_excluded_s121_locator_must_be_distinct_from_counterpart_cells(self) -> None:
        assessment = semantic_assessment()
        terms = counterpart_terms()
        assessment["self_counterpart_record"]["source_locator"] = terms[0]["source_locator"]
        result = assess_f4_counterpart_reconciliation(terms, target("7.1"), assessment)
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_target_locator_requires_exact_path_boundary(self) -> None:
        wrong_target = {
            **target("7.1"),
            "source_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: " + FROZEN_F4_TARGET_ARTIFACT + ".bak::KEY=" + FROZEN_F4_TARGET_SERIES_KEY + "::TIME_PERIOD=" + FROZEN_F4_TARGET_PERIOD + "::OBS_VALUE",
            "target_artifact": FROZEN_F4_TARGET_ARTIFACT,
        }
        result = assess_f4_counterpart_reconciliation(
            counterpart_terms(), wrong_target, semantic_assessment()
        )
        self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")

    def test_production_target_value_must_match_retained_qsa_observation(self) -> None:
        exact_target = target("6.1")
        exact_target["source_locator"] = FROZEN_F4_TARGET_SOURCE_LOCATOR
        self.assertTrue(_production_target_value_matches(exact_target))
        wrong_target = {**exact_target, "source_value": "6.2"}
        self.assertFalse(_production_target_value_matches(wrong_target))

    def test_decimals_attribute_alone_does_not_establish_target_rounding(self) -> None:
        unsupported_locators = (
            FROZEN_F4_TARGET_DECIMALS_LOCATOR,
            "TEST_FIXTURE_NOT_SOURCE_DATA: " + FROZEN_F4_TARGET_DECIMALS_LOCATOR + "::OBS_STATUS=A",
        )
        for locator in unsupported_locators:
            with self.subTest(locator=locator):
                target_record = target("7.1")
                target_record["precision_evidence_locator"] = locator
                result = assess_f4_counterpart_reconciliation(
                    counterpart_terms(), target_record, semantic_assessment()
                )
                self.assertEqual(result["status"], "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED")


if __name__ == "__main__":
    unittest.main()
