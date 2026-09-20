from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = (
    "model/dynamics/"
    "mof_announced_RON_primary_reference_auction_partial_2025_assessment.json"
)
MANIFEST_PATH = (
    "data/source_vintages/"
    "mof-announced-ron-primary-reference-auction-full-2025-vintage-2026-09-20/"
    "source_vintage_manifest.json"
)
MONTHLY_PATH = (
    "data/processed/"
    "mof_announced_RON_primary_reference_auction_partial_2025_monthly.csv"
)
EVENTS_PATH = (
    "data/processed/"
    "mof_announced_RON_primary_reference_auction_partial_2025_events.csv"
)


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: str) -> list[dict[str, str]]:
    with (ROOT / path).open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def audit_partial_announced_supply(
    assessment: dict,
    manifest: dict,
    reference_modes: dict,
    boundary: dict,
    readiness: dict,
    feedback: dict,
    prereg: dict,
    model_contract: dict,
) -> list[str]:
    errors: list[str] = []

    if assessment["candidate_id"] != (
        "announced_RON_primary_reference_auction_supply_level"
    ):
        errors.append("partial announced-supply candidate id changed")
    if assessment["status"] != (
        "PARTIAL_EXACT_EVENT_MATERIALISATION_CANONICAL_PROMOTION_BLOCKED_"
        "INCOMPLETE_REQUIRED_SOURCE_COVERAGE"
    ):
        errors.append("partial announced-supply assessment status changed")

    expected_months = [
        "2025-01",
        "2025-02",
        "2025-03",
        "2025-04",
        "2025-06",
        "2025-10",
    ]
    if assessment["exact_final_months"] != expected_months:
        errors.append(
            "exact final month set changed: "
            f"{assessment['exact_final_months']}"
        )

    expected_values = {
        "2025-01": 5200.0,
        "2025-02": 7200.0,
        "2025-03": 7400.0,
        "2025-04": 6900.0,
        "2025-06": 5100.0,
        "2025-10": 7000.0,
    }
    if assessment["exact_final_monthly_values_RON_million"] != expected_values:
        errors.append("exact final monthly values changed")

    coverage = assessment["coverage_by_month"]
    if coverage["2025-05"] != (
        "UNAVAILABLE_FINAL_AMENDMENT_752_RAW_SOURCE_NOT_RETAINED"
    ):
        errors.append("May final-value blocker changed")
    for month in ("2025-07", "2025-08", "2025-09"):
        if coverage[month] != "UNAVAILABLE_BASE_ORDER_RAW_SOURCE_NOT_RETAINED":
            errors.append(f"{month}: unavailable base-order status changed")
    for month in ("2025-11", "2025-12"):
        if coverage[month] != (
            "UNAVAILABLE_BASE_AND_AMENDMENT_RAW_SOURCES_NOT_RETAINED"
        ):
            errors.append(f"{month}: unavailable base/amendment status changed")

    may = assessment["may_base_order_history"]
    if may["competitive_base_RON_million"] != 5400.0:
        errors.append("May base-order historical amount changed")
    if may["final_monthly_value_authorized"] is not False:
        errors.append("May base-order amount may not be promoted to final monthly value")

    guards = assessment["scientific_guards"]
    for key in (
        "SSON_included_in_candidate",
        "accepted_or_borrowed_amount_included",
        "missing_months_treated_as_zero",
        "unretained_amendment_inferred",
        "canonical_reference_mode_promoted",
        "government_securities_supply_pressure_node_resolved",
        "yield_effect_estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
    ):
        if guards[key] is not False:
            errors.append(f"partial announced-supply assessment may not promote {key}")

    next_gate = assessment["next_gate"]
    if next_gate["id"] != (
        "mof_announced_RON_primary_reference_auction_full_2025_missing_source_recovery"
    ):
        errors.append("partial assessment next gate changed")
    if next_gate["authorization"] != "OFFICIAL_SOURCE_RECOVERY_ONLY":
        errors.append("partial assessment next-gate authorization changed")
    if next_gate["event_materialisation_for_missing_sources_authorized"] is not False:
        errors.append("missing-source event materialisation may not be authorized")
    if next_gate[
        "canonical_promotion_before_complete_required_source_coverage"
    ] is not False:
        errors.append("canonical promotion may not precede required source coverage")

    if manifest["raw_sources_retained_count"] != 4:
        errors.append("retained raw-source count changed")
    if manifest["raw_sources_unavailable_count"] != 8:
        errors.append("unavailable raw-source count changed")
    expected_retained = {
        "mof_order_541_april_2025",
        "mof_order_728_may_2025",
        "mof_order_871_june_2025",
        "mof_order_1626_october_2025",
    }
    if set(manifest["retained_source_ids"]) != expected_retained:
        errors.append("retained raw-source set changed")
    if set(manifest["unavailable_source_ids"]) != set(next_gate["required_source_ids"]):
        errors.append("assessment missing-source list differs from retained manifest")
    if manifest["canonical_reference_mode_promoted"] is not False:
        errors.append("source-vintage manifest may not promote canonical reference mode")
    if manifest["feedback_activation_authorized"] is not False:
        errors.append("source-vintage manifest may not activate feedback")

    identities = assessment["native_text_identities"]
    for source_id in expected_retained:
        source = next(
            item for item in manifest["documents"]
            if item["source_id"] == source_id
        )
        pdf_path = ROOT / (
            "data/source_vintages/"
            "mof-announced-ron-primary-reference-auction-full-2025-vintage-2026-09-20/"
            + source["official_pdf_path"]
        )
        text_path = ROOT / (
            "data/source_vintages/"
            "mof-announced-ron-primary-reference-auction-full-2025-vintage-2026-09-20/"
            "native_text/"
            + source_id
            + ".txt"
        )
        if sha256_file(pdf_path) != identities[source_id]["pdf_sha256"]:
            errors.append(f"{source_id}: retained PDF SHA-256 changed")
        if text_path.stat().st_size != identities[source_id]["native_text_bytes"]:
            errors.append(f"{source_id}: native-text byte size changed")
        if sha256_file(text_path) != identities[source_id]["native_text_sha256"]:
            errors.append(f"{source_id}: native-text SHA-256 changed")

    monthly = read_csv(MONTHLY_PATH)
    if [row["period"] for row in monthly] != [f"2025-{m:02d}" for m in range(1, 13)]:
        errors.append("monthly partial series coverage changed")
    monthly_by_period = {row["period"]: row for row in monthly}
    for period, expected in expected_values.items():
        value = monthly_by_period[period][
            "announced_RON_primary_reference_auction_supply_million"
        ]
        if value == "" or float(value) != expected:
            errors.append(f"{period}: exact monthly value changed")
    for period in ("2025-05", "2025-07", "2025-08", "2025-09", "2025-11", "2025-12"):
        row = monthly_by_period[period]
        if row["announced_RON_primary_reference_auction_supply_million"] != "":
            errors.append(f"{period}: unavailable month must remain blank")
        if row["event_count"] != "":
            errors.append(f"{period}: unavailable event count must remain blank")

    events = read_csv(EVENTS_PATH)
    if not events:
        errors.append("event-level partial series is empty")
    for row in events:
        if row["event_type"] == "BENCHMARK_BOND_SSON":
            errors.append("SSON appeared in competitive-only event series")
        if row["currency"] != "RON":
            errors.append("non-RON event appeared in competitive-only series")

    if any(
        mode.get("id") == "announced_RON_primary_reference_auction_supply_level"
        for mode in reference_modes["modes"]
    ):
        errors.append("partial candidate may not appear in canonical reference_modes")

    node = next(
        item for item in boundary["variables"]
        if item["id"] == "government_securities_supply_pressure"
    )
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("partial materialisation may not resolve supply-pressure node")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("partial materialisation may not activate supply-pressure node")
    if node[
        "full_year_announced_RON_primary_reference_auction_supply_status"
    ] != (
        "PARTIAL_EXACT_EVENT_MATERIALISATION_6_FINAL_MONTHS_"
        "8_REQUIRED_SOURCES_MISSING_CANONICAL_PROMOTION_BLOCKED"
    ):
        errors.append("boundary-registry partial supply status changed")

    link = next(
        item for item in readiness["links"]
        if item["loop_id"] == "government_issuance_yield_loop"
        and item["from"] == "government_debt_issuance"
        and item["to"] == "government_securities_supply_pressure"
    )
    if link["source_boundary_status"] != (
        "STRUCTURED_VECTOR_COMPETITIVE_ONLY_PARTIAL_EXACT_6_FINAL_MONTHS_"
        "8_REQUIRED_SOURCES_MISSING_CANONICAL_PROMOTION_BLOCKED"
    ):
        errors.append("issuance-pressure link partial status changed")
    if link["exact_integrated_equation_ready"] is not False:
        errors.append("partial materialisation may not make link equation ready")
    if link["current_activation_authorized"] is not False:
        errors.append("partial materialisation may not activate issuance-pressure link")

    loop = next(
        item for item in feedback["loops"]
        if item["id"] == "government_issuance_yield_loop"
    )
    if loop["quantitatively_active"] is not False:
        errors.append("partial materialisation may not activate issuance-yield loop")
    if loop[
        "full_year_announced_RON_primary_reference_auction_supply_status"
    ] != (
        "PARTIAL_EXACT_EVENT_MATERIALISATION_6_FINAL_MONTHS_"
        "8_REQUIRED_SOURCES_MISSING_CANONICAL_PROMOTION_BLOCKED"
    ):
        errors.append("feedback-registry partial supply status changed")

    bridge = next(
        item for item in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if item["id"] == "issuance_to_supply_pressure"
    )
    if bridge["missing_required_source_count"] != 8:
        errors.append("issuance-pressure bridge missing-source count changed")
    if bridge["status"] != (
        "STRUCTURED_VECTOR_COMPETITIVE_ONLY_PARTIAL_EXACT_6_FINAL_MONTHS_"
        "8_REQUIRED_SOURCES_MISSING_CANONICAL_PROMOTION_BLOCKED"
    ):
        errors.append("issuance-pressure bridge partial status changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic["mof_announced_RON_primary_reference_auction_supply_status"] != (
        "PARTIAL_EXACT_EVENT_MATERIALISATION_6_FINAL_MONTHS_"
        "8_REQUIRED_SOURCES_MISSING_CANONICAL_PROMOTION_BLOCKED"
    ):
        errors.append("model contract partial supply status changed")
    if dynamic[
        "mof_announced_RON_primary_reference_auction_supply_missing_required_source_count"
    ] != 8:
        errors.append("model contract missing-source count changed")
    if dynamic["next_government_issuance_yield_empirical_task"] != (
        "mof_announced_RON_primary_reference_auction_full_2025_missing_source_recovery"
    ):
        errors.append("model contract next task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("partial materialisation may not authorize issuance-yield feedback")

    return errors


def main() -> None:
    assessment = load(ASSESSMENT_PATH)
    manifest = load(MANIFEST_PATH)
    reference_modes = load("model/dynamics/reference_modes.json")
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    readiness = load("model/dynamics/feedback_link_readiness_registry.json")
    feedback = load("model/dynamics/feedback_registry.json")
    prereg = load(
        "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
    )
    model_contract = load("model/registries/model_contract.json")

    errors = audit_partial_announced_supply(
        assessment,
        manifest,
        reference_modes,
        boundary,
        readiness,
        feedback,
        prereg,
        model_contract,
    )
    if errors:
        raise RuntimeError(
            "Partial full-2025 announced RON reference-auction audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(
        json.dumps(
            {
                "status": "PASS",
                "candidate_id": assessment["candidate_id"],
                "exact_final_months": assessment["exact_final_months"],
                "exact_final_month_count": len(assessment["exact_final_months"]),
                "raw_sources_retained": manifest["raw_sources_retained_count"],
                "raw_sources_missing": manifest["raw_sources_unavailable_count"],
                "canonical_reference_mode_promoted": False,
                "supply_pressure_node_resolved": False,
                "feedback_activation_authorized": False,
                "next_gate": assessment["next_gate"]["id"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
