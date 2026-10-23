from __future__ import annotations

import base64
import csv
import hashlib
import io
import json
import re
import zipfile
from decimal import Decimal, InvalidOperation
from fractions import Fraction
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
F4_SOURCE_MANIFEST_PATH = "data/source_vintages/accounting-f4-partial-2025-vintage-2026-09-18/source_manifest.json"
F4_SOURCE_ARCHIVE_PATH = "data/source_vintages/accounting-f4-partial-2025-vintage-2026-09-18/workflow_artifact_10558980689.zip.b64"
F4_SOURCE_ARCHIVE_SHA256 = "a01922ed3662725dd5c73c95cd248bb97c8fc8a06404c9507e7cac4fc8e260aa"
F4_SOURCE_REPORT_MEMBER = "f4_phase_a_artifacts/f4_loans_coverage_audit.json"
F4_SOURCE_REPORT_SHA256 = "0eec19061320039161a92ddde7ae3af9b89280d187d7fcdba5b590ce906cb0e5"
FROZEN_F4_TARGET_MEMBER = "f4_phase_a_artifacts/raw/cd74f1884fd6c092.raw"
FROZEN_F4_TARGET_MEMBER_SHA256 = "2733df8109321019c5eff3430b96078ce50c9a388df4dcadf72302bf78f84efa"
FROZEN_F4_TARGET_SERIES_KEY = "QSA.Q.N.RO.W0.S121.S1.N.A.LE.F4.T._Z.XDC._T.S.V.N._T"
FROZEN_F4_TARGET_PERIOD = "2025-Q4"
FROZEN_F4_TARGET_VALUE = "6.1"
FROZEN_F4_TARGET_ARTIFACT = f"{F4_SOURCE_ARCHIVE_PATH}#{FROZEN_F4_TARGET_MEMBER}"
FROZEN_F4_TARGET_SOURCE_LOCATOR = (
    f"{FROZEN_F4_TARGET_ARTIFACT}::KEY={FROZEN_F4_TARGET_SERIES_KEY}"
    f"::TIME_PERIOD={FROZEN_F4_TARGET_PERIOD}::OBS_VALUE"
)
FROZEN_F4_TARGET_DECIMALS_LOCATOR = (
    f"{FROZEN_F4_TARGET_ARTIFACT}::KEY={FROZEN_F4_TARGET_SERIES_KEY}::DECIMALS"
)
TEST_FIXTURE_PREFIX = "TEST_FIXTURE_NOT_SOURCE_DATA:"
CONTRACT = (
    "model/accounting/"
    "f4_bnr_cnf_counterpart_reconciliation_precision_contract_2026_10_22.json"
)
MONITORING = "model/accounting/f4_bnr_cnf_2025_stock_trigger_monitoring_2026_09_21.json"
SCREENING = "model/dynamics/sectoral_financial_positions_bnr_cnf_source_screening.json"
REOPEN_REGISTRY = "model/accounting/reopen_conditions_registry.json"
MANIFEST = "model/registries/scientific_baseline_manifest.json"


def _locator_points_to_frozen_artifact(locator: Any) -> bool:
    if not isinstance(locator, str) or not locator.strip():
        return False
    normalized = locator.strip().replace("\\", "/")
    fixture_prefix = TEST_FIXTURE_PREFIX + " "
    if normalized.startswith(fixture_prefix):
        normalized = normalized[len(fixture_prefix):].strip()
    return normalized == FROZEN_F4_TARGET_SOURCE_LOCATOR


def _read_frozen_target_control() -> tuple[dict[str, str] | None, list[str]]:
    errors: list[str] = []
    try:
        manifest = json.loads((ROOT / F4_SOURCE_MANIFEST_PATH).read_text(encoding="utf-8"))
        if manifest.get("archive") != Path(F4_SOURCE_ARCHIVE_PATH).name:
            errors.append("retained F4 source manifest names a different archive")
        if manifest.get("decoded_archive_sha256") != F4_SOURCE_ARCHIVE_SHA256:
            errors.append("retained F4 source manifest SHA-256 changed")
        encoded_archive = "".join((ROOT / F4_SOURCE_ARCHIVE_PATH).read_text(encoding="ascii").split())
        archive_bytes = base64.b64decode(encoded_archive, validate=True)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        return None, [f"retained F4 source manifest/archive cannot be read: {exc}"]
    if hashlib.sha256(archive_bytes).hexdigest() != F4_SOURCE_ARCHIVE_SHA256:
        return None, ["retained F4 source archive failed its frozen SHA-256"]
    try:
        with zipfile.ZipFile(io.BytesIO(archive_bytes)) as archive:
            names = archive.namelist()
            if FROZEN_F4_TARGET_MEMBER not in names or F4_SOURCE_REPORT_MEMBER not in names:
                return None, ["frozen F4 source/member report is missing from retained archive"]
            raw_bytes = archive.read(FROZEN_F4_TARGET_MEMBER)
            report_bytes = archive.read(F4_SOURCE_REPORT_MEMBER)
    except (KeyError, OSError, zipfile.BadZipFile) as exc:
        return None, [f"retained F4 source archive member cannot be read: {exc}"]
    if hashlib.sha256(raw_bytes).hexdigest() != FROZEN_F4_TARGET_MEMBER_SHA256:
        errors.append("frozen F4 target raw member SHA-256 changed")
    if hashlib.sha256(report_bytes).hexdigest() != F4_SOURCE_REPORT_SHA256:
        errors.append("retained F4 aggregate report SHA-256 changed")
    try:
        physical_lines = raw_bytes.decode("utf-8-sig").splitlines()
        if not physical_lines:
            return None, errors + ["retained F4 target CSV is empty"]
        headers = next(csv.reader([physical_lines[0]]))
        rows = [
            dict(zip(headers, next(csv.reader([line]))))
            for line in physical_lines[1:]
            if line.strip()
        ]
        target_rows = [
            row for row in rows
            if row.get("KEY") == FROZEN_F4_TARGET_SERIES_KEY
            and row.get("TIME_PERIOD") == FROZEN_F4_TARGET_PERIOD
        ]
        report = json.loads(report_bytes.decode("utf-8"))
    except (UnicodeDecodeError, csv.Error, json.JSONDecodeError) as exc:
        return None, errors + [f"retained F4 target evidence is malformed: {exc}"]
    if len(target_rows) != 1:
        return None, errors + [f"expected exactly one retained QSA target observation, found {len(target_rows)}"]
    target_row = target_rows[0]
    expected_dimensions = {
        "FREQ": "Q", "REF_AREA": "RO", "COUNTERPART_AREA": "W0",
        "REF_SECTOR": "S121", "COUNTERPART_SECTOR": "S1",
        "CONSOLIDATION": "N", "ACCOUNTING_ENTRY": "A", "INSTR_ASSET": "F4",
        "MATURITY": "T", "UNIT_MEASURE": "XDC", "UNIT_MULT": "6", "DECIMALS": "2",
    }
    for key, expected_value in expected_dimensions.items():
        if target_row.get(key) != expected_value:
            errors.append(f"retained QSA target field {key} changed from {expected_value!r}")
    if target_row.get("OBS_VALUE") != FROZEN_F4_TARGET_VALUE:
        errors.append("retained QSA target OBS_VALUE differs from frozen 6.1 control")
    aggregate_rows = [
        row for row in report.get("aggregate_reconciliation", [])
        if row.get("measure") == "stock" and row.get("kind") == "holder_total" and row.get("sector") == "BNR"
    ]
    if len(aggregate_rows) != 1 or aggregate_rows[0].get("official_aggregate_million_RON") != 6.1:
        errors.append("retained Phase A report no longer confirms the BNR-holder F4 aggregate of 6.1 million RON")
    # The raw observation is verified independently by exact KEY, period,
    # expected dimensions and member SHA-256 above. The retained Phase A
    # aggregate is a derived summary and need not repeat the raw key in the
    # selected holder-total row's serialization.
    return target_row, errors


def _production_target_value_matches(target: dict[str, Any]) -> bool:
    locator = target.get("source_locator")
    if isinstance(locator, str) and locator.strip().startswith(TEST_FIXTURE_PREFIX):
        return _locator_points_to_frozen_artifact(locator)
    if not _locator_points_to_frozen_artifact(locator):
        return False
    source_row, errors = _read_frozen_target_control()
    if errors or source_row is None:
        return False
    try:
        value_matches = _decimal(target.get("source_value")) == _decimal(source_row.get("OBS_VALUE"))
        factor_matches = _decimal(target.get("unit_conversion_factor_to_million_RON")) == Decimal("1")
    except (ValueError, InvalidOperation):
        return False
    return value_matches and factor_matches and target.get("source_unit") == "million RON"


def audit_frozen_target_control_source() -> list[str]:
    row, errors = _read_frozen_target_control()
    if errors:
        return [f"frozen F4 target source: {error}" for error in errors]
    if row is None:
        return ["frozen F4 target source: exact retained target observation was not found"]
    return []


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
    if record["source_locator"].strip() == record["precision_evidence_locator"].strip():
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
    if source_resolution > 0 and (
        rounding_mode != "NEAREST"
        or record.get("precision_basis") == "OFFICIAL_SOURCE_EXACTNESS_STATEMENT"
    ):
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


FROZEN_COUNTERPART_SOURCE_MAPPING = {
    "H": ("S14+S15",),
    "C": ("S11",),
    "F": ("S122+S123", "S124+S125+S126+S127", "S128+S129"),
    "G": ("S13",),
    "X": ("S2",),
}
SELF_COUNTERPART_TREATMENTS = {
    "NOT_PUBLISHED_IN_SOURCE",
    "OBSERVED_BUT_EXCLUDED_FROM_TARGET_WITH_OFFICIAL_BOUNDARY_SUPPORT",
    "OBSERVED_AND_INCLUDED_AS_EXPLICIT_TERM",
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


def assess_counterpart_term_coverage(
    terms: Any,
    target: Any,
    semantic_assessment: Any,
) -> dict[str, str]:
    """Require exact source-cell coverage, frozen sector mapping, S121 treatment and target identity."""
    fail = "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED"
    if not isinstance(terms, list) or not terms or not isinstance(target, dict):
        return {"status": fail, "reason": "numeric term list or retained target control is malformed"}
    if not isinstance(semantic_assessment, dict):
        return {"status": fail, "reason": "semantic assessment is not structured"}

    expected = semantic_assessment.get("expected_term_keys")
    expected_cells = semantic_assessment.get("expected_source_cells")
    if (
        not isinstance(expected, list)
        or not expected
        or any(not isinstance(key, str) or not key.strip() for key in expected)
        or len(set(expected)) != len(expected)
    ):
        return {"status": fail, "reason": "expected source-term keys are missing, malformed, or duplicated"}
    if not isinstance(expected_cells, list) or not expected_cells:
        return {"status": fail, "reason": "expected source-cell mapping is missing"}

    disposition = semantic_assessment.get("self_counterpart_disposition")
    if not isinstance(disposition, str) or disposition not in SELF_COUNTERPART_TREATMENTS:
        return {"status": fail, "reason": "S121 self-counterpart disposition is missing or unrecognized"}
    excluded_self_source_locator: str | None = None

    expected_mapping: dict[str, tuple[str, str]] = {}
    expected_pairs: list[tuple[str, str]] = []
    for index, cell in enumerate(expected_cells):
        if not isinstance(cell, dict):
            return {"status": fail, "reason": f"expected source-cell record {index} is not an object"}
        key, group, sector_code = cell.get("term_key"), cell.get("counterpart_group"), cell.get("source_sector_code")
        if not all(isinstance(v, str) and v.strip() for v in (key, group, sector_code)):
            return {"status": fail, "reason": f"expected source-cell record {index} has incomplete identity"}
        if key in expected_mapping:
            return {"status": fail, "reason": "expected source-cell keys are duplicated"}
        expected_mapping[key] = (group, sector_code)
        expected_pairs.append((group, sector_code))
    if set(expected_mapping) != set(expected):
        return {"status": fail, "reason": "expected term keys do not exactly match expected source-cell records"}

    required_pairs = [
        (group, code)
        for group, codes in FROZEN_COUNTERPART_SOURCE_MAPPING.items()
        for code in codes
    ]
    optional_self_pair = ("BNR", "S121")
    if disposition == "OBSERVED_AND_INCLUDED_AS_EXPLICIT_TERM":
        allowed_pairs = required_pairs + [optional_self_pair]
        self_key = semantic_assessment.get("self_counterpart_term_key")
        if not isinstance(self_key, str) or not self_key.strip():
            return {"status": fail, "reason": "included S121 cell has no explicit term key"}
        if expected_mapping.get(self_key) != optional_self_pair:
            return {"status": fail, "reason": "included S121 term key does not map to the explicit BNR/S121 cell"}
        if "self_counterpart_record" in semantic_assessment:
            return {"status": fail, "reason": "included S121 cell must be carried once as a numeric term, not duplicated"}
        boundary_locator = semantic_assessment.get("self_counterpart_boundary_evidence_locator")
        if not isinstance(boundary_locator, str) or not boundary_locator.strip():
            return {"status": fail, "reason": "included S121 treatment lacks boundary evidence"}
    elif disposition == "OBSERVED_BUT_EXCLUDED_FROM_TARGET_WITH_OFFICIAL_BOUNDARY_SUPPORT":
        allowed_pairs = required_pairs
        record = semantic_assessment.get("self_counterpart_record")
        if not isinstance(record, dict) or record.get("source_sector_code") != "S121":
            return {"status": fail, "reason": "excluded S121 cell is not preserved as a separate source record"}
        self_key = record.get("term_key")
        if not isinstance(self_key, str) or not self_key.strip() or self_key in expected_mapping:
            return {"status": fail, "reason": "excluded S121 cell key is missing or wrongly included in numeric terms"}
        validated_self = _validated_record(record, index=-1, needs_coefficient=False)
        if validated_self is None:
            return {"status": fail, "reason": "excluded S121 source record lacks valid value/precision provenance"}
        excluded_self_source_locator = record["source_locator"].strip()
        boundary_locator = semantic_assessment.get("self_counterpart_boundary_evidence_locator")
        if not isinstance(boundary_locator, str) or not boundary_locator.strip():
            return {"status": fail, "reason": "excluded S121 treatment lacks official boundary evidence"}
    else:
        allowed_pairs = required_pairs
        evidence_locator = semantic_assessment.get("self_counterpart_evidence_locator")
        if not isinstance(evidence_locator, str) or not evidence_locator.strip():
            return {"status": fail, "reason": "absence of S121 counterpart column lacks an official source locator"}
        if "self_counterpart_record" in semantic_assessment or "self_counterpart_term_key" in semantic_assessment:
            return {"status": fail, "reason": "S121 cell is claimed absent but a separate record/key was supplied"}

    if len(expected_pairs) != len(set(expected_pairs)):
        return {"status": fail, "reason": "expected counterpart group/source-code pair is duplicated"}
    if set(expected_pairs) != set(allowed_pairs) or len(expected_pairs) != len(allowed_pairs):
        return {
            "status": fail,
            "reason": "expected source cells do not exactly cover the frozen H/C/F/G/X mapping and declared S121 treatment",
        }

    actual_keys: list[str] = []
    value_locators: set[str] = set()
    for index, term in enumerate(terms):
        if not isinstance(term, dict):
            return {"status": fail, "reason": f"numeric term {index} is not a structured source cell"}
        source_locator = term.get("source_locator")
        if not isinstance(source_locator, str) or not source_locator.strip():
            return {"status": fail, "reason": f"numeric term {index} lacks a cell-specific source locator"}
        normalized_source_locator = source_locator.strip()
        if normalized_source_locator in value_locators:
            return {"status": fail, "reason": "distinct counterpart cells reuse a source locator"}
        value_locators.add(normalized_source_locator)
        key = term.get("term_key")
        group = term.get("counterpart_group")
        sector_code = term.get("source_sector_code")
        if not isinstance(key, str) or not key.strip():
            return {"status": fail, "reason": f"numeric term {index} lacks a stable term_key"}
        if not isinstance(group, str) or not isinstance(sector_code, str):
            return {"status": fail, "reason": f"numeric term {key} lacks counterpart-group/source-sector identity"}
        if expected_mapping.get(key) != (group, sector_code):
            return {"status": fail, "reason": f"numeric term {key} does not match the frozen declared source-cell mapping"}
        actual_keys.append(key)
        try:
            coefficient = Fraction(_decimal(term.get("coefficient")))
        except (ValueError, InvalidOperation):
            return {"status": fail, "reason": f"numeric term {key} lacks an exact valid coefficient"}
        if coefficient != 1:
            return {"status": fail, "reason": f"counterpart-stock term {key} must have coefficient exactly +1"}

    if excluded_self_source_locator is not None:
        if excluded_self_source_locator in value_locators:
            return {"status": fail, "reason": "excluded S121 value locator is reused by a mapped counterpart cell"}
        value_locators.add(excluded_self_source_locator)
    if len(set(actual_keys)) != len(actual_keys):
        return {"status": fail, "reason": "duplicate numeric term_key detected"}
    if set(actual_keys) != set(expected):
        return {
            "status": fail,
            "reason": "actual source-term keys do not exactly match the declared counterpart-cell coverage",
        }

    expected_target_artifact = semantic_assessment.get("expected_target_artifact")
    actual_target_artifact = target.get("target_artifact")
    target_locator = target.get("source_locator")
    if (
        expected_target_artifact != FROZEN_F4_TARGET_ARTIFACT
        or actual_target_artifact != FROZEN_F4_TARGET_ARTIFACT
        or not _locator_points_to_frozen_artifact(target_locator)
    ):
        return {
            "status": fail,
            "reason": "target record is not tied to the exact frozen retained F4 artifact path",
        }
    if target_locator.strip() in value_locators:
        return {
            "status": fail,
            "reason": "frozen target control reuses a source-cell value locator",
        }
    if not _production_target_value_matches(target):
        return {
            "status": fail,
            "reason": "target value/unit does not match the exact retained ECB QSA observation",
        }
    precision_locator = target.get("precision_evidence_locator")
    if isinstance(precision_locator, str) and FROZEN_F4_TARGET_DECIMALS_LOCATOR in precision_locator:
        return {
            "status": fail,
            "reason": "the DECIMALS attribute alone does not establish the required rounding mode",
        }

    expected_target_key = semantic_assessment.get("expected_target_key")
    actual_target_key = target.get("target_key")
    if (
        not isinstance(expected_target_key, str)
        or not expected_target_key.strip()
        or not isinstance(actual_target_key, str)
        or not actual_target_key.strip()
        or actual_target_key != expected_target_key
    ):
        return {
            "status": fail,
            "reason": "target record does not identify the frozen 2025-Q4 F4 control declared by semantic adjudication",
        }
    return {
        "status": "COUNTERPART_TERM_COVERAGE_PASS",
        "reason": "actual terms exactly match the frozen source mapping, S121 disposition, and retained target key",
    }


def assess_f4_counterpart_reconciliation(
    terms: list[dict[str, Any]],
    target: dict[str, Any],
    semantic_assessment: Any,
) -> dict[str, str]:
    """Require semantic checks and exact term coverage before numeric F4 reconciliation."""
    semantic_result = assess_semantic_adjudication(semantic_assessment)
    if semantic_result.get("status") != "SEMANTIC_ADJUDICATION_PASS_FOR_NUMERIC_RECONCILIATION":
        return {
            "status": "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED",
            "reason": semantic_result.get("reason", "semantic adjudication did not pass"),
        }
    coverage_result = assess_counterpart_term_coverage(terms, target, semantic_assessment)
    if coverage_result.get("status") != "COUNTERPART_TERM_COVERAGE_PASS":
        return {
            "status": "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED",
            "reason": coverage_result.get("reason", "counterpart source-cell coverage did not pass"),
        }
    return assess_documented_precision_reconciliation(terms, target)


def audit_f4_bnr_cnf_counterpart_reconciliation_precision() -> list[str]:
    errors: list[str] = []
    errors.extend(audit_frozen_target_control_source())
    contract = load(CONTRACT)
    monitoring = load(MONITORING)
    screening = load(SCREENING)
    reopen = load(REOPEN_REGISTRY)
    manifest = load(MANIFEST)
    f4 = reopen["instruments"]["F4"]

    if contract.get("contract_version") != "0.2":
        errors.append("precision preregistration target-source contract version changed")
    if contract.get("frozen_on") != "2026-10-22":
        errors.append("precision preregistration freeze date changed")
    if contract.get("id") != "F4_BNR_CNF_2025_COUNTERPART_RECONCILIATION_DOCUMENTED_PRECISION":
        errors.append("precision contract identity changed")
    if contract.get("governing_sources", {}).get("f4_stock_trigger_monitoring") != MONITORING:
        errors.append("precision contract is detached from the canonical F4 stock trigger")
    if contract.get("governing_sources", {}).get("retained_f4_artifact") != FROZEN_F4_TARGET_ARTIFACT:
        errors.append("retained F4 target artifact pointer changed")
    if contract.get("governing_sources", {}).get("retained_f4_partial_matrix") != "model/accounting/f4_partial_2025.json":
        errors.append("retained partial F4 matrix pointer changed")
    if contract.get("governing_sources", {}).get("retained_f4_source_vintage_manifest") != F4_SOURCE_MANIFEST_PATH:
        errors.append("retained F4 source-vintage manifest pointer changed")
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
    if "cannot be paired with OFFICIAL_SOURCE_EXACTNESS_STATEMENT" not in required_precision_text:
        errors.append("contract permits contradictory exactness basis with positive resolution")
    target_precision_note = contract.get("precision_evidence_policy", {}).get("target_control_precision_note", "")
    if "DECIMALS=2 alone does not establish a rounding mode" not in target_precision_note:
        errors.append("contract must keep target-control rounding mode unconfirmed absent official evidence")
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
    coverage_text = semantic_contract.get("numeric_term_coverage", "")
    for coverage_rule in ("expected_term_keys", "term_key", "no omitted", "expected_target_key", "target_key", "uniquely identifies that reported source cell", "distinct after trimming whitespace", "path-boundary artifact"):
        if coverage_rule not in coverage_text:
            errors.append(f"contract does not preregister exact source-term coverage rule: {coverage_rule}")
    if "coefficient exactly +1" not in semantic_contract.get("coefficient_rule", ""):
        errors.append("contract does not freeze the counterpart-stock summation coefficients")
    frozen_mapping = semantic_contract.get("frozen_source_cell_mapping", {})
    if frozen_mapping != {key: list(value) for key, value in FROZEN_COUNTERPART_SOURCE_MAPPING.items()}:
        errors.append("contract frozen source-cell mapping differs from the implemented H/C/F/G/X mapping")
    if semantic_contract.get("frozen_target_artifact") != FROZEN_F4_TARGET_ARTIFACT:
        errors.append("contract frozen target artifact differs from the implemented F4 control")
    frozen_control = contract.get("frozen_target_control", {})
    expected_control = {
        "artifact": FROZEN_F4_TARGET_ARTIFACT,
        "archive_sha256": F4_SOURCE_ARCHIVE_SHA256,
        "archive_member": FROZEN_F4_TARGET_MEMBER,
        "archive_member_sha256": FROZEN_F4_TARGET_MEMBER_SHA256,
        "aggregate_report_member": F4_SOURCE_REPORT_MEMBER,
        "aggregate_report_sha256": F4_SOURCE_REPORT_SHA256,
        "series_key": FROZEN_F4_TARGET_SERIES_KEY,
        "reference_period": FROZEN_F4_TARGET_PERIOD,
        "observation_field": "OBS_VALUE",
        "value_million_RON": FROZEN_F4_TARGET_VALUE,
        "decimals_attribute": "2",
        "unit_multiplier": "6",
        "rounding_mode_confirmed": False,
    }
    if frozen_control != expected_control:
        errors.append("contract frozen F4 target-control identity/provenance differs from the retained source")
    current_disposition = contract.get("current_disposition", {})
    if current_disposition.get("target_value_source_verified") is not True:
        errors.append("retained F4 target value must be source-verified")
    if current_disposition.get("target_precision_rounding_rule_confirmed") is not False:
        errors.append("target rounding rule must remain unconfirmed in the current evidence state")
    precision_policy_text = contract.get("precision_evidence_policy", {}).get("required_for_every_numeric_input", "")
    if "must be distinct" not in precision_policy_text:
        errors.append("contract does not require a distinct precision-evidence locator")
    if "including variants with extra prefix or suffix text" not in precision_policy_text:
        errors.append("contract does not reject decorated locators that still point only to the QSA DECIMALS attribute")
    if "self_counterpart_disposition" not in semantic_contract.get("numeric_term_coverage", ""):
        errors.append("contract does not require explicit S121 counterpart disposition")
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

    contradictory_exactness = [{
        **fixture_terms[0],
        "precision_basis": "OFFICIAL_SOURCE_EXACTNESS_STATEMENT",
        "source_resolution": "0.1",
        "rounding_mode": "NEAREST",
    }]
    contradictory = assess_documented_precision_reconciliation(contradictory_exactness, fixture_target)
    if contradictory.get("status") != "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED":
        errors.append("positive resolution cannot be paired with an exactness-statement precision basis")

    unknown_locator = [{**fixture_terms[0], "precision_evidence_locator": ""}]
    missing_evidence = assess_documented_precision_reconciliation(unknown_locator, fixture_target)
    if missing_evidence.get("status") != "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED":
        errors.append("missing official precision-evidence locator should remain unconfirmed")

    bad_conversion = [{**fixture_terms[0], "unit_conversion_factor_to_million_RON": "0"}]
    invalid_unit_conversion = assess_documented_precision_reconciliation(bad_conversion, fixture_target)
    if invalid_unit_conversion.get("status") != "UNCONFIRMED_PRECISION_KEEP_F4_CLOSED":
        errors.append("invalid unit conversion should remain unconfirmed")

    fixture_cell_specs = [
        ("fixture-H", "H", "S14+S15", "2.0"),
        ("fixture-C", "C", "S11", "1.0"),
        ("fixture-F1", "F", "S122+S123", "0.5"),
        ("fixture-F2", "F", "S124+S125+S126+S127", "1.0"),
        ("fixture-F3", "F", "S128+S129", "0.2"),
        ("fixture-G", "G", "S13", "2.0"),
        ("fixture-X", "X", "S2", "0.3"),
    ]
    coverage_fixture_terms = [
        {
            "source_value": value,
            "source_unit": "million RON",
            "unit_conversion_factor_to_million_RON": "1",
            "source_resolution": "0.1",
            "rounding_mode": "NEAREST",
            "coefficient": "1",
            "precision_basis": "OFFICIAL_METADATA",
            "source_locator": f"TEST_FIXTURE_NOT_SOURCE_DATA: source cell {key}",
            "precision_evidence_locator": f"TEST_FIXTURE_NOT_SOURCE_DATA: precision {key}",
            "term_key": key,
            "counterpart_group": group,
            "source_sector_code": sector_code,
        }
        for key, group, sector_code, value in fixture_cell_specs
    ]
    coverage_fixture_target = {
        **fixture_target,
        "source_value": "7.1",
        "source_locator": TEST_FIXTURE_PREFIX + " " + FROZEN_F4_TARGET_SOURCE_LOCATOR,
        "target_key": "retained_f4_control_2025_Q4",
        "target_artifact": FROZEN_F4_TARGET_ARTIFACT,
    }
    semantic_fixture = {
        **{key: True for key in SEMANTIC_REQUIRED_CHECKS},
        "expected_term_keys": [key for key, _, _, _ in fixture_cell_specs],
        "expected_source_cells": [
            {"term_key": key, "counterpart_group": group, "source_sector_code": sector_code}
            for key, group, sector_code, _ in fixture_cell_specs
        ],
        "expected_target_key": "retained_f4_control_2025_Q4",
        "expected_target_artifact": FROZEN_F4_TARGET_ARTIFACT,
        "self_counterpart_disposition": "OBSERVED_BUT_EXCLUDED_FROM_TARGET_WITH_OFFICIAL_BOUNDARY_SUPPORT",
        "self_counterpart_record": {
            "term_key": "fixture-self-S121",
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
        "self_counterpart_boundary_evidence_locator": "TEST_FIXTURE_NOT_SOURCE_DATA: S121 retained-target boundary",
    }
    semantic_fixture["evidence_locators"] = {
        key: f"TEST_FIXTURE_NOT_SOURCE_DATA: semantic evidence for {key}"
        for key in SEMANTIC_REQUIRED_CHECKS
    }
    combined_good = assess_f4_counterpart_reconciliation(
        coverage_fixture_terms, coverage_fixture_target, semantic_fixture
    )
    if combined_good.get("status") != "PRECISION_AND_RECONCILIATION_PASS_ELIGIBLE_FOR_BASE_F4_TRIGGER_ADJUDICATION":
        errors.append("complete semantic and numeric fixtures should yield eligibility only for trigger adjudication")
    semantic_missing = {
        **semantic_fixture,
        "self_counterpart_boundary_resolved": False,
    }
    combined_blocked = assess_f4_counterpart_reconciliation(
        coverage_fixture_terms, coverage_fixture_target, semantic_missing
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
        coverage_fixture_terms, coverage_fixture_target, locator_missing
    )
    if combined_missing_locator.get("status") != "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED":
        errors.append("missing semantic evidence locator must block F4 eligibility")

    omitted_term = assess_f4_counterpart_reconciliation(
        coverage_fixture_terms[:-1], coverage_fixture_target, semantic_fixture
    )
    if omitted_term.get("status") != "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED":
        errors.append("omitted counterpart source cell must block F4 eligibility")
    duplicate_terms = [dict(term) for term in coverage_fixture_terms]
    duplicate_terms[1]["term_key"] = duplicate_terms[0]["term_key"]
    duplicate_term = assess_f4_counterpart_reconciliation(
        duplicate_terms, coverage_fixture_target, semantic_fixture,
    )
    if duplicate_term.get("status") != "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED":
        errors.append("duplicate counterpart source cell must block F4 eligibility")
    wrong_target = assess_f4_counterpart_reconciliation(
        coverage_fixture_terms,
        {**coverage_fixture_target, "target_key": "unfrozen-new-target"},
        semantic_fixture,
    )
    if wrong_target.get("status") != "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED":
        errors.append("wrong target-control identity must block F4 eligibility")
    altered_terms = [dict(term) for term in coverage_fixture_terms]
    altered_terms[0]["coefficient"] = "0"
    altered_coefficient = assess_f4_counterpart_reconciliation(
        altered_terms, coverage_fixture_target, semantic_fixture,
    )
    if altered_coefficient.get("status") != "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED":
        errors.append("non-unit coefficient must block counterpart-stock reconciliation")
    wrong_mapping_terms = [dict(term) for term in coverage_fixture_terms]
    wrong_mapping_terms[0]["source_sector_code"] = "S121"
    wrong_mapping = assess_f4_counterpart_reconciliation(
        wrong_mapping_terms, coverage_fixture_target, semantic_fixture,
    )
    if wrong_mapping.get("status") != "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED":
        errors.append("unapproved counterpart-sector mapping must block reconciliation")
    duplicate_value_locator_terms = [dict(term) for term in coverage_fixture_terms]
    duplicate_value_locator_terms[1]["source_locator"] = duplicate_value_locator_terms[0]["source_locator"]
    duplicate_value_locator = assess_f4_counterpart_reconciliation(
        duplicate_value_locator_terms, coverage_fixture_target, semantic_fixture,
    )
    if duplicate_value_locator.get("status") != "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED":
        errors.append("distinct counterpart cells must not reuse a value locator")

    target_locator_reused_by_cell = [dict(term) for term in coverage_fixture_terms]
    target_locator_reused_by_cell[0]["source_locator"] = coverage_fixture_target["source_locator"]
    reused_target_locator = assess_f4_counterpart_reconciliation(
        target_locator_reused_by_cell, coverage_fixture_target, semantic_fixture,
    )
    if reused_target_locator.get("status") != "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED":
        errors.append("the retained target locator must be distinct from counterpart cell locators")

    wrong_target_locator = {
        **coverage_fixture_target,
        "source_locator": TEST_FIXTURE_PREFIX + " " + FROZEN_F4_TARGET_ARTIFACT + ".bak::KEY=" + FROZEN_F4_TARGET_SERIES_KEY + "::TIME_PERIOD=" + FROZEN_F4_TARGET_PERIOD + "::OBS_VALUE",
    }
    malformed_target_locator = assess_f4_counterpart_reconciliation(
        coverage_fixture_terms, wrong_target_locator, semantic_fixture,
    )
    if malformed_target_locator.get("status") != "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED":
        errors.append("target locator must identify the exact frozen artifact path, not a similarly named backup")

    missing_self_record = {**semantic_fixture}
    missing_self_record.pop("self_counterpart_record")
    missing_self = assess_f4_counterpart_reconciliation(
        coverage_fixture_terms, coverage_fixture_target, missing_self_record,
    )
    if missing_self.get("status") != "SEMANTIC_NONCONFIRMATION_KEEP_F4_CLOSED":
        errors.append("observed-but-excluded S121 source cell must be retained and bounded separately")

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
