from __future__ import annotations

import json
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    "model/accounting/"
    "f4_bnr_cnf_counterpart_reconciliation_precision_contract_2026_10_22.json"
)
MONITORING = "model/accounting/f4_bnr_cnf_2025_stock_trigger_monitoring_2026_09_21.json"
SCREENING = "model/dynamics/sectoral_financial_positions_bnr_cnf_source_screening.json"
REOPEN_REGISTRY = "model/accounting/reopen_conditions_registry.json"
MANIFEST = "model/registries/scientific_baseline_manifest.json"

ALLOWED_PRECISION_BASES = {
    "OFFICIAL_METADATA",
    "EXPLICIT_OFFICIAL_ROUNDING_STATEMENT",
    "OFFICIAL_SOURCE_EXACTNESS_STATEMENT",
}


def load(path: str) -> dict[str, Any]:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def _decimal(value: Any) -> Decimal:
    if not isinstance(value, (str, int)) or isinstance(value, bool):
        raise ValueError("numeric inputs must be exact decimal strings or integers")
    try:
        result = Decimal(str(value))
    except InvalidOperation as exc:
        raise ValueError("invalid exact decimal input") from exc
    if not result.is_finite():
        raise ValueError("numeric inputs must be finite")
    return result


def _fraction_text(value: Fraction) -> str:
    """Format a finite-decimal rational exactly, without Decimal context rounding."""
    numerator = value.numerator
    denominator = value.denominator
    rest = denominator
    twos = 0
    fives = 0
    while rest % 2 == 0:
        rest //= 2
        twos += 1
    while rest % 5 == 0:
        rest //= 5
        fives += 1
    if rest != 1:
        return f"{numerator}/{denominator}"
    scale = max(twos, fives)
    scaled_abs = abs(numerator) * (10 ** scale) // denominator
    digits = str(scaled_abs).zfill(scale + 1)
    if scale:
        integer_part = digits[:-scale]
        fractional_part = digits[-scale:].rstrip("0")
        result = integer_part + ("." + fractional_part if fractional_part else "")
    else:
        result = digits
    return "-" + result if numerator < 0 else result


def _validated_record(
    record: dict[str, Any],
    *,
    index: int,
    needs_coefficient: bool,
) -> tuple[Fraction, Fraction, Fraction] | None:
    """Return (normalized_value, normalized_resolution, coefficient) or fail closed."""
    if record.get("precision_basis") not in ALLOWED_PRECISION_BASES:
        return None
    for key in ("source_locator", "precision_evidence_locator", "source_unit"):
        if not isinstance(record.get(key), str) or not record[key].strip():
            return None
    if "source_value" not in record or "source_resolution" not in record:
        return None
    if "unit_conversion_factor_to_million_RON" not in record:
        return None
    try:
        source_value = _decimal(record["source_value"])
        source_resolution = _decimal(record["source_resolution"])
        conversion_factor = _decimal(record["unit_conversion_factor_to_million_RON"])
        coefficient = _decimal(record["coefficient"]) if needs_coefficient else Decimal("1")
    except (ValueError, InvalidOperation):
        return None
    if source_resolution < 0 or conversion_factor <= 0:
        return None
    rounding_mode = record.get("rounding_mode")
    if source_resolution > 0 and rounding_mode != "NEAREST":
        return None
    if source_resolution == 0 and (
        record.get("precision_basis") != "OFFICIAL_SOURCE_EXACTNESS_STATEMENT"
        or rounding_mode != "EXACT"
    ):
        return None
    normalized_value = Fraction(source_value) * Fraction(conversion_factor)
    normalized_resolution = Fraction(source_resolution) * Fraction(conversion_factor)
    return normalized_value, normalized_resolution, Fraction(coefficient)


def assess_documented_precision_reconciliation(
    terms: list[dict[str, Any]],
    target: dict[str, Any],
) -> dict[str, str]:
    """Reconcile exact source values after validating source precision and units.

    Each record must provide source_value, source_unit, a positive exact conversion
    factor to million RON, source_resolution in source-unit terms, an accepted
    precision basis, a value locator, and a separate precision-evidence locator.
    A zero resolution is accepted only when an official source explicitly declares
    the value exact. No precision is inferred from the value's printed formatting.
    """
    if not terms:
        return {
            "status": "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED",
            "reason": "no counterpart terms supplied",
        }
    if not isinstance(terms, list) or not isinstance(target, dict):
        return {
            "status": "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED",
            "reason": "terms and target must be structured records",
        }

    normalized_terms: list[tuple[Fraction, Fraction, Fraction]] = []
    for index, term in enumerate(terms):
        if not isinstance(term, dict):
            return {
                "status": "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED",
                "reason": f"counterpart record {index} is not an object",
            }
        validated = _validated_record(term, index=index, needs_coefficient=True)
        if validated is None:
            return {
                "status": "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED",
                "reason": f"counterpart record {index} lacks valid source, unit-conversion, or precision evidence",
            }
        normalized_terms.append(validated)

    normalized_target = _validated_record(target, index=len(terms), needs_coefficient=False)
    if normalized_target is None:
        return {
            "status": "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED",
            "reason": "target lacks valid source, unit-conversion, or precision evidence",
        }

    observed_sum = sum(
        (coefficient * value for value, _, coefficient in normalized_terms),
        Fraction(0),
    )
    target_value, target_resolution, _ = normalized_target
    envelope = sum(
        (abs(coefficient) * resolution / 2 for _, resolution, coefficient in normalized_terms),
        Fraction(0),
    ) + target_resolution / 2

    residual = observed_sum - target_value
    status = (
        "PRECISION_AND_RECONCILIATION_PASS_ELIGIBLE_FOR_BASE_F4_TRIGGER_ADJUDICATION"
        if abs(residual) <= envelope
        else "RECONCILIATION_FAIL_KEEP_F4_CLOSED"
    )
    return {
        "status": status,
        "residual_million_RON": _fraction_text(residual),
        "rounding_envelope_million_RON": _fraction_text(envelope),
        "counterpart_sum_million_RON": _fraction_text(observed_sum),
        "target_million_RON": _fraction_text(target_value),
    }


SEMANTIC_REQUIRED_CHECKS = (
    "evidence_window_satisfied",
    "official_source_identity_verified",
    "reference_period_2025_year_end_verified",
    "reporting_sector_s121_verified",
    "instrument_af4_f4_verified",
    "asset_entry_verified",
    "nonconsolidated_scope_verified",
    "consolidation_valuation_maturity_dimensions_match",
    "sector_mapping_h_c_f_g_x_verified",
    "f_subsector_sum_exact_and_complete",
    "self_counterpart_boundary_resolved",
    "counterpart_matrix_coverage_complete",
    "retained_target_control_vintage_frozen",
    "target_control_concepts_match",
)


def assess_semantic_adjudication(assessment: Any) -> dict[str, str]:
    """Fail closed unless scope, topology and provenance were independently adjudicated."""
    if not isinstance(assessment, dict):
        return {
            "status": "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED",
            "reason": "semantic assessment is not a structured object",
        }
    for key in SEMANTIC_REQUIRED_CHECKS:
        if assessment.get(key) is not True:
            return {
                "status": "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED",
                "reason": f"semantic prerequisite {key} is missing or not confirmed",
            }
    locators = assessment.get("evidence_locators")
    if not isinstance(locators, dict):
        return {
            "status": "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED",
            "reason": "semantic evidence locators are missing",
        }
    for key in SEMANTIC_REQUIRED_CHECKS:
        locator = locators.get(key)
        if not isinstance(locator, str) or not locator.strip():
            return {
                "status": "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED",
                "reason": f"semantic evidence locator for {key} is missing",
            }
    return {
        "status": "SEMANTIC_ADJUDICATION_PASS_FOR_NUMERIC_RECONCILIATION",
        "reason": "all semantic checks and their evidence locators are present",
    }


def assess_f4_counterpart_reconciliation(
    terms: list[dict[str, Any]],
    target: dict[str, Any],
    semantic_assessment: Any,
) -> dict[str, str]:
    """Require semantic adjudication before using a numeric result for the F4 trigger."""
    semantic_result = assess_semantic_adjudication(semantic_assessment)
    if semantic_result.get("status") != "SEMANTIC_ADJUDICATION_PASS_FOR_NUMERIC_RECONCILIATION":
        return {
            "status": "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED",
            "reason": semantic_result.get("reason", "semantic adjudication did not pass"),
        }
    return assess_documented_precision_reconciliation(terms, target)


def audit_f4_bnr_cnf_counterpart_reconciliation_precision() -> list[str]:
    errors: list[str] = []
    contract = load(CONTRACT)
    monitoring = load(MONITORING)
    screening = load(SCREENING)
    reopen = load(REOPEN_REGISTRY)
    manifest = load(MANIFEST)
    f4 = reopen["instruments"]["F4"]

    if contract.get("contract_version") != "0.1":
        errors.append("precision preregistration contract version changed")
    if contract.get("frozen_on") != "2026-10-22":
        errors.append("precision preregistration freeze date changed")
    if contract.get("id") != "F4_BNR_CNF_2025_COUNTERPART_RECONCILIATION_DOCUMENTED_PRECISION":
        errors.append("precision contract identity changed")
    if contract.get("governing_sources", {}).get("f4_stock_trigger_monitoring") != MONITORING:
        errors.append("precision contract is detached from the canonical F4 stock trigger")
    if contract.get("governing_sources", {}).get("retained_f4_artifact") != "model/accounting/f4_partial_2025.json":
        errors.append("retained F4 artifact pointer changed")
    if contract.get("scope", {}).get("reference_period") != "2025-year-end":
        errors.append("precision contract target period changed")
    if contract.get("scope", {}).get("reporting_sector") != "S121":
        errors.append("precision contract reporting sector changed")
    if contract.get("scope", {}).get("instrument") != "AF4/F4":
        errors.append("precision contract instrument changed")
    if contract.get("scope", {}).get("accounting_entry") != "assets":
        errors.append("precision contract accounting entry changed")

    required_bases = set(contract.get("precision_evidence_policy", {}).get("accepted_basis", []))
    if required_bases != ALLOWED_PRECISION_BASES:
        errors.append("precision contract accepted source bases differ from implemented fail-closed rule")
    if "solely from the number of decimal places" not in contract.get("precision_evidence_policy", {}).get("forbidden_inference", ""):
        errors.append("contract no longer forbids inferring precision from number formatting")
    required_precision_text = contract.get("precision_evidence_policy", {}).get("required_for_every_numeric_input", "")
    for required_field in (
        "source_value",
        "source_unit",
        "conversion_factor_to_million_RON",
        "source_resolution",
        "rounding_mode",
        "precision_basis",
        "source_locator",
        "precision_evidence_locator",
    ):
        if required_field not in required_precision_text:
            errors.append(f"contract does not require {required_field} for every numeric input")
    if "normalized values and resolutions from the recorded exact conversion factor" not in required_precision_text:
        errors.append("contract does not require exact application of unit conversion factors")
    if "rounding_mode = NEAREST" not in required_precision_text or "rounding_mode = EXACT" not in required_precision_text:
        errors.append("contract does not distinguish documented nearest-rounding from exact values")
    if "no usable documented precision/rounding rule" not in contract.get("precision_evidence_policy", {}).get("no_official_precision_disposition", ""):
        errors.append("contract does not fail closed when source precision is unknown")
    if contract.get("reconciliation_method", {}).get("arithmetic") != "Exact decimal/rational arithmetic only; no binary floating-point comparison and no discretionary epsilon.":
        errors.append("exact arithmetic/no-epsilon rule changed")
    if not contract.get("reconciliation_method", {}).get("rounding_envelope", "").startswith(
        "E = sum_i(abs(a_i) * q_i / 2) + q_y / 2"
    ):
        errors.append("documented rounding-envelope formula changed")
    if "abs(R) <= E" not in contract.get("reconciliation_method", {}).get("pass_condition", ""):
        errors.append("pass condition is no longer the frozen envelope comparison")
    if "must be adjudicated and preregistered in a new immutable contract" not in contract.get("reconciliation_method", {}).get("explicit_official_accounting_tolerance", ""):
        errors.append("a separate fixed tolerance may not be introduced without a new preregistration")

    semantic_contract = contract.get("semantic_adjudication", {})
    if semantic_contract.get("required_checks") != list(SEMANTIC_REQUIRED_CHECKS):
        errors.append("contract semantic prerequisites differ from the implemented fail-closed set")
    if semantic_contract.get("failure_disposition") != "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED":
        errors.append("semantic nonconfirmation must keep F4 closed")
    if "numeric primitive only" not in semantic_contract.get("numeric_helper_boundary", ""):
        errors.append("contract does not distinguish numeric reconciliation from semantic adjudication")
    if contract.get("decision_logic", {}).get("semantic_adjudication_missing_or_failed") != "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED":
        errors.append("semantic nonconfirmation disposition is not declared in decision logic")

    decision_logic = contract.get("decision_logic", {})
    if decision_logic.get("any_precision_unknown_or_missing") != "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED":
        errors.append("unknown precision no longer returns to F4 hold")
    if decision_logic.get("reconciliation_outside_frozen_envelope") != "RECONCILIATION_FAIL_KEEP_F4_CLOSED":
        errors.append("failed reconciliation no longer returns to F4 hold")

    prohibited = contract.get("prohibited_effects", {})
    for key in (
        "flow_reopen",
        "aggregate_reference_mode_reopen",
        "automatic_F4_completion",
        "calibration_or_refit",
        "holdout_access",
        "feedback_activation",
        "behavioural_closure",
        "benchmark_change",
        "public_version_change",
    ):
        if prohibited.get(key) is not False:
            errors.append(f"precision contract may not authorize {key}")

    if contract.get("current_disposition", {}).get("precision_gate_executed") is not False:
        errors.append("precision gate must remain unexecuted during preregistration")
    if contract.get("current_disposition", {}).get("reconciliation_executed") is not False:
        errors.append("reconciliation must remain unexecuted during preregistration")
    if contract.get("current_disposition", {}).get("F4_stock_gate_open") is not False:
        errors.append("precision preregistration must not open F4")

    if screening.get("observed_counterpart_matrix", {}).get("period") != "2024":
        errors.append("historical source screening period changed")
    precision_note = contract.get("governing_sources", {}).get("historical_source_precision_note", "")
    if "does not identify an explicit rounding rule or source precision metadata" not in precision_note:
        errors.append("historical source precision limitation is no longer explicit")
    if contract.get("current_disposition", {}).get("next_evidence_window") != "after 2026-10-31":
        errors.append("existing F4 evidence window changed")

    expected_contract_path = CONTRACT
    if f4.get("priority_stock_reconciliation_precision_contract") != expected_contract_path:
        errors.append("canonical F4 registry lacks the precision-contract pointer")
    if manifest.get("authority", {}).get("f4_bnr_cnf_counterpart_reconciliation_precision_contract") != expected_contract_path:
        errors.append("scientific baseline manifest lacks the precision-contract authority pointer")
    if f4.get("priority_stock_reconciliation_precision_contract_state") != "PREREGISTERED_SOURCE_PRECISION_REQUIRED_FAIL_CLOSED":
        errors.append("canonical F4 registry precision-contract state is stale")
    if f4.get("current_reopen_gate_open") is not False:
        errors.append("F4 reopen gate unexpectedly opened")
    if monitoring.get("monitoring_policy", {}).get("earliest_evidence_window_for_recheck") != "after 2026-10-31":
        errors.append("base F4 source window changed")
    if monitoring.get("current_public_review", {}).get("current_reopen_trigger_satisfied") is not False:
        errors.append("base F4 monitoring trigger unexpectedly satisfied")
    base_trigger = monitoring.get("frozen_future_trigger", {})
    if base_trigger.get("id") != "BNR_CNF_2025_F4_CENTRAL_BANK_ASSET_COUNTERPART_STOCK_MATRIX":
        errors.append("base F4 monitoring trigger identity changed")
    if base_trigger.get("flow_reopen_authorized") is not False:
        errors.append("base F4 trigger unexpectedly authorizes flows")

    # Regression fixture: explicitly documented source resolutions and exact
    # unit conversions may pass only inside the derived envelope. These are not
    # actual RMD source observations.
    fixture_terms = [
        {
            "source_value": "6.0",
            "source_unit": "million RON",
            "unit_conversion_factor_to_million_RON": "1",
            "source_resolution": "0.1",
            "rounding_mode": "NEAREST",
            "coefficient": "1",
            "precision_basis": "OFFICIAL_METADATA",
            "source_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: counterpart cell 1",
            "precision_evidence_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: cell 1 precision",
        },
        {
            "source_value": "0.0",
            "source_unit": "million RON",
            "unit_conversion_factor_to_million_RON": "1",
            "source_resolution": "0.1",
            "rounding_mode": "NEAREST",
            "coefficient": "1",
            "precision_basis": "EXPLICIT_OFFICIAL_ROUNDING_STATEMENT",
            "source_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: counterpart cell 2",
            "precision_evidence_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: cell 2 rounding rule",
        },
    ]
    fixture_target = {
        "source_value": "6.1",
        "source_unit": "million RON",
        "unit_conversion_factor_to_million_RON": "1",
        "source_resolution": "0.1",
        "rounding_mode": "NEAREST",
        "precision_basis": "OFFICIAL_METADATA",
        "source_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: target control",
        "precision_evidence_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: target precision",
    }
    good = assess_documented_precision_reconciliation(fixture_terms, fixture_target)
    if good.get("status") != "PRECISION_AND_RECONCILIATION_PASS_ELIGIBLE_FOR_BASE_F4_TRIGGER_ADJUDICATION":
        errors.append("documented-precision test fixture should pass its exact rounding envelope")
    if good.get("rounding_envelope_million_RON") != "0.15":
        errors.append("test fixture did not calculate the exact expected rounding envelope")

    failing_target = {**fixture_target, "source_value": "6.3"}
    failed = assess_documented_precision_reconciliation(fixture_terms, failing_target)
    if failed.get("status") != "RECONCILIATION_FAIL_KEEP_F4_CLOSED":
        errors.append("out-of-envelope fixture should fail closed")

    unknown_terms = [{**fixture_terms[0], "precision_basis": None}]
    unknown = assess_documented_precision_reconciliation(unknown_terms, fixture_target)
    if unknown.get("status") != "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED":
        errors.append("unknown source precision fixture should remain unconfirmed")

    unknown_locator = [{**fixture_terms[0], "precision_evidence_locator": ""}]
    missing_evidence = assess_documented_precision_reconciliation(unknown_locator, fixture_target)
    if missing_evidence.get("status") != "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED":
        errors.append("missing official precision-evidence locator should remain unconfirmed")

    bad_conversion = [{**fixture_terms[0], "unit_conversion_factor_to_million_RON": "0"}]
    invalid_unit_conversion = assess_documented_precision_reconciliation(bad_conversion, fixture_target)
    if invalid_unit_conversion.get("status") != "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED":
        errors.append("invalid unit conversion should remain unconfirmed")

    semantic_fixture = {
        key: True for key in SEMANTIC_REQUIRED_CHECKS
    }
    semantic_fixture["evidence_locators"] = {
        key: f"TEST_FIXTURE_NOT_SOURCE_DATA: semantic evidence for {key}"
        for key in SEMANTIC_REQUIRED_CHECKS
    }
    combined_good = assess_f4_counterpart_reconciliation(
        fixture_terms, fixture_target, semantic_fixture
    )
    if combined_good.get("status") != "PRECISION_AND_RECONCILIATION_PASS_ELIGIBLE_FOR_BASE_F4_TRIGGER_ADJUDICATION":
        errors.append("complete semantic and numeric fixtures should yield eligibility only for trigger adjudication")
    semantic_missing = {
        **semantic_fixture,
        "self_counterpart_boundary_resolved": False,
    }
    combined_blocked = assess_f4_counterpart_reconciliation(
        fixture_terms, fixture_target, semantic_missing
    )
    if combined_blocked.get("status") != "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED":
        errors.append("unresolved S121 self-counterpart semantics must block a numeric pass")
    locator_missing = {
        **semantic_fixture,
        "evidence_locators": {
            **semantic_fixture["evidence_locators"],
            "sector_mapping_h_c_f_g_x_verified": "",
        },
    }
    combined_missing_locator = assess_f4_counterpart_reconciliation(
        fixture_terms, fixture_target, locator_missing
    )
    if combined_missing_locator.get("status") != "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED":
        errors.append("missing semantic evidence locator must block F4 eligibility")

    return errors


def main() -> None:
    errors = audit_f4_bnr_cnf_counterpart_reconciliation_precision()
    if errors:
        raise RuntimeError(
            "F4 documented-precision reconciliation audit failed:\n- "
            + "\n- ".join(errors)
        )
    contract = load(CONTRACT)
    print(
        json.dumps(
            {
                "status": "PASS",
                "contract": CONTRACT,
                "contract_status": contract["current_disposition"]["contract_status"],
                "precision_gate_executed": contract["current_disposition"]["precision_gate_executed"],
                "reconciliation_executed": contract["current_disposition"]["reconciliation_executed"],
                "F4_stock_gate_open": contract["current_disposition"]["F4_stock_gate_open"],
                "next_evidence_window": contract["current_disposition"]["next_evidence_window"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
