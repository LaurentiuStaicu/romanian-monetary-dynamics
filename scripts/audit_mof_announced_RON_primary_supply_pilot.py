from __future__ import annotations

import csv
import hashlib
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = (
    "model/dynamics/"
    "mof_announced_RON_primary_supply_pilot_assessment_2026_09_20.json"
)
EVENTS_PATH = (
    "data/processed/"
    "government_securities_announced_RON_primary_supply_2025Q1_events.csv"
)
MONTHLY_PATH = (
    "data/processed/"
    "government_securities_announced_RON_primary_supply_2025Q1_monthly.csv"
)
VINTAGE_ROOT = (
    ROOT
    / "data/source_vintages/"
    "mof-announced-ron-primary-supply-pilot-2026-09-20"
)


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def read_csv(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open("r", encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def audit_announced_supply_q1_pilot(
    assessment: dict,
    manifest: dict,
    events: list[dict[str, str]],
    monthly: list[dict[str, str]],
    measurement_design: dict,
    source_review: dict,
    boundary: dict,
    readiness: dict,
    feedback: dict,
    prereg: dict,
    model_contract: dict,
    reference_modes: dict,
) -> list[str]:
    errors: list[str] = []

    if assessment["reference_mode_id"] != "announced_RON_primary_supply_level":
        errors.append("Q1 pilot reference-mode id changed")

    diagnostic = assessment.get("raw_probe_diagnostic", {})
    if diagnostic.get("manifest_all_sources_retained") is not True:
        errors.append("raw source retention must remain complete")
    if diagnostic.get("manifest_all_anchor_checks_pass") is not False:
        errors.append("legacy raw-anchor diagnostic state changed")
    if diagnostic.get("interpretation") != (
        "LEGACY_NAIVE_ANCHOR_FALSE_NEGATIVE_SUPERSEDED_BY_EXACT_"
        "ARTICLE1_AND_EVENT_ROW_RECONCILIATION"
    ):
        errors.append("legacy raw-anchor diagnostic interpretation changed")
    if diagnostic.get("source_retention_is_blocked_by_legacy_anchor_diagnostic") is not False:
        errors.append("legacy anchor diagnostic may not block exact source retention")

    if manifest["all_sources_retained"] is not True:
        errors.append("source-vintage manifest no longer retains all sources")
    if manifest["event_rows_extracted"] is not False:
        errors.append("raw acquisition manifest may not claim event extraction")
    if manifest["reference_mode_materialised"] is not False:
        errors.append("raw acquisition manifest may not claim reference-mode materialisation")
    if manifest["ocr_used"] is not False:
        errors.append("raw acquisition may not use OCR")
    if manifest["visual_digitisation_used"] is not False:
        errors.append("raw acquisition may not use visual digitisation")

    expected_sources = {
        "mof_order_6826_january_2025",
        "mof_order_159_february_2025",
        "mof_order_352_march_2025",
    }
    if set(assessment["source_identity"]) != expected_sources:
        errors.append("Q1 source identity set changed")

    manifest_by_id = {item["source_id"]: item for item in manifest["sources"]}
    for source_id, expected in assessment["source_identity"].items():
        source = manifest_by_id.get(source_id)
        if source is None:
            errors.append(f"{source_id}: source missing from retained manifest")
            continue
        raw_path = VINTAGE_ROOT / source["raw_path"]
        text_path = VINTAGE_ROOT / source["native_text_path"]
        if not raw_path.is_file():
            errors.append(f"{source_id}: retained raw PDF missing")
            continue
        if not text_path.is_file():
            errors.append(f"{source_id}: retained native text missing")
            continue
        if raw_path.stat().st_size != expected["raw_bytes"]:
            errors.append(f"{source_id}: raw byte size changed")
        if sha256_file(raw_path) != expected["raw_sha256"]:
            errors.append(f"{source_id}: raw SHA-256 changed")
        if sha256_file(text_path) != expected["native_text_sha256"]:
            errors.append(f"{source_id}: native-text SHA-256 changed")
        if source["raw_sha256"] != expected["raw_sha256"]:
            errors.append(f"{source_id}: manifest raw SHA-256 changed")

    reconciliations = {
        item["source_id"]: item for item in assessment["document_reconciliations"]
    }
    expected_reconciliation = {
        "mof_order_6826_january_2025": (2, 9, 1400.0, 3800.0, 570.0, 5200.0, 5770.0),
        "mof_order_159_february_2025": (2, 10, 1600.0, 5600.0, 840.0, 7200.0, 8040.0),
        "mof_order_352_march_2025": (2, 10, 1800.0, 5600.0, 840.0, 7400.0, 8240.0),
    }
    if set(reconciliations) != set(expected_reconciliation):
        errors.append("document-reconciliation source set changed")
    for source_id, expected in expected_reconciliation.items():
        item = reconciliations.get(source_id)
        if item is None:
            continue
        observed = (
            item["t_bill_row_count"],
            item["benchmark_row_count"],
            item["t_bill_competitive_RON_million"],
            item["benchmark_competitive_RON_million"],
            item["benchmark_SSON_RON_million"],
            item["parsed_base_RON_million"],
            item["parsed_combined_RON_million"],
        )
        if observed != expected:
            errors.append(
                f"{source_id}: reconciliation tuple changed: {observed!r}"
            )
        if not all(item["checks"].values()):
            errors.append(f"{source_id}: at least one exact reconciliation check failed")

    pilot = assessment["event_level_pilot"]
    if pilot["event_count_all_scheduled"] != 64:
        errors.append("scheduled event count changed")
    if pilot["event_count_completed_by_cutoff"] != 63:
        errors.append("completed event count changed")
    if pilot["cutoff_date"] != "2025-03-31":
        errors.append("Q1 pilot cutoff changed")
    if pilot["post_cutoff_forward_event_count"] != 1:
        errors.append("post-cutoff event count changed")
    expected_forward = {
        "event_date": "2025-04-01",
        "event_type": "BENCHMARK_BOND_SSON",
        "isin": "RO45DLJ4EE76",
        "announced_nominal_RON_million": 75.0,
        "source_id": "mof_order_352_march_2025",
    }
    if pilot["post_cutoff_forward_events"] != [expected_forward]:
        errors.append("post-cutoff forward event changed")

    if len(events) != 64:
        errors.append(f"event CSV row count changed: {len(events)}")
    allowed_event_types = {
        "T_BILL_COMPETITIVE_REFERENCE_AUCTION",
        "BENCHMARK_BOND_COMPETITIVE_REFERENCE_AUCTION",
        "BENCHMARK_BOND_SSON",
    }
    if {row["event_type"] for row in events} != allowed_event_types:
        errors.append("event CSV type set changed")
    completed = [row for row in events if row["completed_by_cutoff"] == "True"]
    forward = [row for row in events if row["completed_by_cutoff"] == "False"]
    if len(completed) != 63 or len(forward) != 1:
        errors.append("event CSV completed/forward partition changed")
    if forward:
        row = forward[0]
        if not (
            row["event_date"] == "2025-04-01"
            and row["event_type"] == "BENCHMARK_BOND_SSON"
            and row["isin"] == "RO45DLJ4EE76"
            and Decimal(row["announced_nominal_RON_million"]) == Decimal("75.000")
        ):
            errors.append("event CSV post-cutoff row changed")

    if len(monthly) != 3:
        errors.append(f"monthly pilot row count changed: {len(monthly)}")
    monthly_by_id = {row["month"]: row for row in monthly}
    expected_monthly = {
        "2025-01": ("5770.000", "20", "1400.000", "3800.000", "570.000"),
        "2025-02": ("8040.000", "22", "1600.000", "5600.000", "840.000"),
        "2025-03": ("8165.000", "21", "1800.000", "5600.000", "765.000"),
    }
    if set(monthly_by_id) != set(expected_monthly):
        errors.append("monthly pilot period set changed")
    for month, expected in expected_monthly.items():
        row = monthly_by_id.get(month)
        if row is None:
            continue
        observed = (
            row["announced_RON_primary_supply_million"],
            row["event_count"],
            row["t_bill_competitive_RON_million"],
            row["benchmark_competitive_RON_million"],
            row["benchmark_SSON_RON_million"],
        )
        if observed != expected:
            errors.append(f"{month}: monthly Q1 tuple changed: {observed!r}")
        if row["status"] != "COMPLETED_PERIOD_EXACT_EVENT_AGGREGATION":
            errors.append(f"{month}: monthly pilot status changed")

    monthly_assessment = assessment["monthly_pilot"]
    if monthly_assessment["values_RON_million"] != {
        "2025-01": 5770.0,
        "2025-02": 8040.0,
        "2025-03": 8165.0,
    }:
        errors.append("assessment monthly Q1 values changed")
    if monthly_assessment["january_flash_crosscheck"] != "PASS_5770":
        errors.append("January Flash cross-check changed")
    if monthly_assessment["february_flash_announced_schedule_crosscheck"] != "PASS_8040":
        errors.append("February Flash cross-check changed")
    if monthly_assessment["march_order_total_not_equal_march_event_month_by_design"] is not True:
        errors.append("March event-date boundary rule changed")
    if monthly_assessment["march_difference_RON_million"] != 75.0:
        errors.append("March event-date difference changed")

    result = assessment["pilot_result"]
    if result["status"] != "PASS_EXACT_EVENT_LEVEL_AND_MONTHLY_Q1_PILOT":
        errors.append("Q1 pilot result changed")
    for key in (
        "raw_source_retention_complete",
        "native_text_extraction_complete",
        "all_document_reconciliations_pass",
        "monthly_event_date_aggregation_pass",
        "reference_mode_pilot_materialised",
    ):
        if result[key] is not True:
            errors.append(f"Q1 pilot must retain PASS state: {key}")
    if result["full_reference_mode_promoted"] is not False:
        errors.append("Q1 pilot may not promote full reference mode")

    for key, value in assessment["scientific_effect"].items():
        if value is not False:
            errors.append(f"Q1 pilot may not authorize/promote {key}")

    next_gate = assessment["next_gate"]
    if next_gate["id"] != "mof_announced_RON_primary_supply_full_2025_extension_contract":
        errors.append("Q1 pilot next gate changed")
    if next_gate["authorization"] != (
        "SOURCE_EXTENSION_AND_REFERENCE_MODE_MATERIALISATION_ONLY"
    ):
        errors.append("Q1 pilot next-gate authorization changed")
    if next_gate["may_estimate_supply_to_yield_effect"] is not False:
        errors.append("Q1 pilot may not estimate supply-to-yield effect")
    if next_gate["may_activate_feedback"] is not False:
        errors.append("Q1 pilot may not activate feedback")

    if measurement_design.get("announced_RON_primary_supply_pilot_assessment") != ASSESSMENT_PATH:
        errors.append("measurement design lacks Q1 pilot assessment")
    measure = next(
        item for item in measurement_design["measurement_vector"]
        if item["measure_id"] == "announced_RON_primary_supply_level"
    )
    if measure["current_source_status"] != (
        "Q1_EXACT_EVENT_MONTH_PILOT_MATERIALISED_FULL_REFERENCE_MODE_NOT_PROMOTED"
    ):
        errors.append("measurement-design Q1 pilot status changed")
    if measure["activation_ready"] is not False:
        errors.append("Q1 pilot may not make announced supply activation-ready")
    if measurement_design["scientific_effect"]["exact_reference_mode_promoted"] is not False:
        errors.append("measurement design may not promote full reference mode")

    if source_review.get("announced_RON_primary_supply_pilot_assessment") != ASSESSMENT_PATH:
        errors.append("source-boundary review lacks Q1 pilot assessment")
    if source_review["announced_RON_primary_supply_pilot_status"] != (
        "PASS_EXACT_Q1_EVENT_MONTH_PILOT_FULL_REFERENCE_MODE_NOT_PROMOTED"
    ):
        errors.append("source-boundary Q1 pilot status changed")

    node = next(
        item for item in boundary["variables"]
        if item["id"] == "government_securities_supply_pressure"
    )
    if node.get("announced_RON_primary_supply_pilot_assessment") != ASSESSMENT_PATH:
        errors.append("boundary registry lacks Q1 pilot assessment")
    if node["announced_RON_primary_supply_reference_mode_status"] != (
        "Q1_PILOT_MATERIALISED_FULL_REFERENCE_MODE_NOT_PROMOTED"
    ):
        errors.append("boundary registry Q1 pilot status changed")
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("Q1 pilot may not resolve supply-pressure umbrella")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("Q1 pilot may not activate supply-pressure umbrella")

    link = next(
        item for item in readiness["links"]
        if item["loop_id"] == "government_issuance_yield_loop"
        and item["from"] == "government_debt_issuance"
        and item["to"] == "government_securities_supply_pressure"
    )
    if link.get("announced_RON_primary_supply_pilot_assessment") != ASSESSMENT_PATH:
        errors.append("issuance-pressure link lacks Q1 pilot assessment")
    if link["source_boundary_status"] != (
        "STRUCTURED_VECTOR_ANNOUNCED_SUPPLY_Q1_PILOT_MATERIALISED_FULL_REFERENCE_MODE_NOT_PROMOTED"
    ):
        errors.append("issuance-pressure link Q1 pilot status changed")
    if link["exact_integrated_equation_ready"] is not False:
        errors.append("Q1 pilot may not make integrated equation ready")
    if link["current_activation_authorized"] is not False:
        errors.append("Q1 pilot may not activate issuance-pressure link")

    loop = next(
        item for item in feedback["loops"]
        if item["id"] == "government_issuance_yield_loop"
    )
    if loop.get("announced_RON_primary_supply_pilot_assessment") != ASSESSMENT_PATH:
        errors.append("feedback registry lacks Q1 pilot assessment")
    if loop["quantitatively_active"] is not False:
        errors.append("Q1 pilot may not activate issuance-yield loop")

    bridge = next(
        item for item in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if item["id"] == "issuance_to_supply_pressure"
    )
    if bridge.get("announced_RON_primary_supply_pilot_assessment") != ASSESSMENT_PATH:
        errors.append("issuance-pressure bridge lacks Q1 pilot assessment")
    if bridge["status"] != (
        "ANNOUNCED_SUPPLY_Q1_PILOT_MATERIALISED_FULL_REFERENCE_MODE_NOT_PROMOTED"
    ):
        errors.append("issuance-pressure bridge Q1 pilot status changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("mof_announced_RON_primary_supply_pilot_assessment") != ASSESSMENT_PATH:
        errors.append("model contract lacks Q1 pilot assessment")
    if dynamic["mof_announced_RON_primary_supply_pilot_events"] != EVENTS_PATH:
        errors.append("model contract Q1 event artifact changed")
    if dynamic["mof_announced_RON_primary_supply_pilot_monthly"] != MONTHLY_PATH:
        errors.append("model contract Q1 monthly artifact changed")
    if dynamic["mof_announced_RON_primary_supply_reference_mode_status"] != (
        "Q1_EXACT_PILOT_MATERIALISED_FULL_REFERENCE_MODE_NOT_PROMOTED"
    ):
        errors.append("model contract Q1 pilot status changed")
    if dynamic["next_government_issuance_yield_empirical_task"] != (
        "mof_announced_RON_primary_supply_full_2025_extension_contract"
    ):
        errors.append("model contract next task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("Q1 pilot may not authorize issuance-yield feedback")

    if any(
        mode["id"] == "announced_RON_primary_supply_level"
        for mode in reference_modes["modes"]
    ):
        errors.append(
            "Q1 pilot may not be silently promoted into canonical reference_modes registry"
        )

    return errors


def main() -> None:
    assessment = load(ASSESSMENT_PATH)
    manifest = load(
        "data/source_vintages/mof-announced-ron-primary-supply-pilot-2026-09-20/"
        "source_vintage_manifest.json"
    )
    events = read_csv(EVENTS_PATH)
    monthly = read_csv(MONTHLY_PATH)
    measurement_design = load(
        "model/dynamics/government_securities_supply_measurement_design_review_2026_09_20.json"
    )
    source_review = load(
        "model/dynamics/government_securities_supply_pressure_source_boundary_review_2026_09_20.json"
    )
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    readiness = load("model/dynamics/feedback_link_readiness_registry.json")
    feedback = load("model/dynamics/feedback_registry.json")
    prereg = load(
        "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
    )
    model_contract = load("model/registries/model_contract.json")
    reference_modes = load("model/dynamics/reference_modes.json")

    errors = audit_announced_supply_q1_pilot(
        assessment,
        manifest,
        events,
        monthly,
        measurement_design,
        source_review,
        boundary,
        readiness,
        feedback,
        prereg,
        model_contract,
        reference_modes,
    )
    if errors:
        raise RuntimeError(
            "Announced RON primary-supply Q1 pilot audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(
        json.dumps(
            {
                "status": "PASS",
                "reference_mode_id": "announced_RON_primary_supply_level",
                "scheduled_events": 64,
                "completed_events_through_2025_03_31": 63,
                "monthly_RON_million": {
                    "2025-01": 5770.0,
                    "2025-02": 8040.0,
                    "2025-03": 8165.0,
                },
                "forward_event": {
                    "date": "2025-04-01",
                    "isin": "RO45DLJ4EE76",
                    "type": "BENCHMARK_BOND_SSON",
                    "RON_million": 75.0,
                },
                "full_reference_mode_promoted": False,
                "feedback_activation_authorized": False,
                "next_task": "mof_announced_RON_primary_supply_full_2025_extension_contract",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
