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

EXPECTED_STATUS = (
    "PARTIAL_EXACT_MONTHLY_10_OF_12_EVENT_COMPLETE_9_OF_12_"
    "CANONICAL_PROMOTION_BLOCKED_3_REQUIRED_SOURCES_MISSING"
)
EXPECTED_LINK_STATUS = (
    "STRUCTURED_VECTOR_COMPETITIVE_ONLY_PARTIAL_EXACT_MONTHLY_10_OF_12_"
    "EVENT_COMPLETE_9_OF_12_CANONICAL_PROMOTION_BLOCKED_3_REQUIRED_SOURCES_MISSING"
)
EXPECTED_MONTHS = [
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05",
    "2025-06", "2025-07", "2025-09", "2025-10", "2025-11",
]
EXPECTED_EVENT_COMPLETE = [
    "2025-01", "2025-02", "2025-03", "2025-04", "2025-05",
    "2025-06", "2025-07", "2025-09", "2025-10",
]
EXPECTED_VALUES = {
    "2025-01": 5200.0,
    "2025-02": 7200.0,
    "2025-03": 7400.0,
    "2025-04": 6900.0,
    "2025-05": 4000.0,
    "2025-06": 5100.0,
    "2025-07": 5800.0,
    "2025-09": 6200.0,
    "2025-10": 7000.0,
    "2025-11": 5800.0,
}
EXPECTED_RETAINED = {
    "mof_order_541_april_2025",
    "mof_order_728_may_2025",
    "mof_order_752_may_2025_amendment",
    "mof_order_871_june_2025",
    "mof_order_1088_july_2025",
    "mof_order_1452_september_2025",
    "mof_order_1626_october_2025",
    "mof_order_1831_november_2025_amendment",
    "mof_order_1928_december_2025",
}
EXPECTED_MISSING = {
    "mof_order_1221_august_2025",
    "mof_order_1795_november_2025",
    "mof_order_1998_december_2025_amendment",
}


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

    if assessment["candidate_id"] != "announced_RON_primary_reference_auction_supply_level":
        errors.append("partial announced-supply candidate id changed")
    if assessment["status"] != EXPECTED_STATUS:
        errors.append("partial announced-supply assessment status changed")
    if assessment["exact_final_months"] != EXPECTED_MONTHS:
        errors.append("exact final month set changed")
    if assessment["event_level_complete_final_months"] != EXPECTED_EVENT_COMPLETE:
        errors.append("event-complete final month set changed")
    if assessment["monthly_only_exact_final_months"] != ["2025-11"]:
        errors.append("monthly-only exact month set changed")
    if assessment["exact_final_monthly_values_RON_million"] != EXPECTED_VALUES:
        errors.append("exact final monthly values changed")

    coverage = assessment["coverage_by_month"]
    if coverage["2025-08"] != "UNAVAILABLE_BASE_ORDER_1221_RAW_SOURCE_NOT_RETAINED":
        errors.append("August blocker changed")
    if coverage["2025-11"] != (
        "EXACT_FINAL_MONTHLY_TOTAL_FROM_RETAINED_AMENDMENT_1831_"
        "EVENT_LEVEL_INCOMPLETE_BASE_1795_UNAVAILABLE"
    ):
        errors.append("November monthly-only boundary changed")
    if coverage["2025-12"] != (
        "UNAVAILABLE_FINAL_AMENDMENT_1998_RAW_SOURCE_NOT_RETAINED_BASE_1928_RETAINED"
    ):
        errors.append("December blocker changed")

    may = assessment["may_version_history"]
    if may["base_competitive_RON_million"] != 5400.0:
        errors.append("May base historical amount changed")
    if may["base_is_final"] is not False:
        errors.append("May base order may not be final")
    if may["final_competitive_RON_million"] != 4000.0:
        errors.append("May amended final amount changed")
    if may["final_monthly_value_authorized"] is not True:
        errors.append("May amended final value must remain authorized")
    if may["base_rows_retained_as_information_time_history"] is not True:
        errors.append("May base history must remain retained")

    november = assessment["november_direct_monthly_total"]
    if november["final_monthly_total_RON_million"] != 5800.0:
        errors.append("November final monthly total changed")
    if november["materialised_annex2_competitive_RON_million"] != 5300.0:
        errors.append("November retained Annex-2 amount changed")
    if november["event_level_complete"] is not False:
        errors.append("November event level may not be claimed complete")
    if november["missing_annex1_event_inferred"] is not False:
        errors.append("November missing event rows may not be inferred")
    if november["monthly_total_is_direct_source_value_not_event_sum"] is not True:
        errors.append("November monthly total provenance changed")

    december = assessment["december_base_order_history"]
    if december["base_competitive_RON_million"] != 4500.0:
        errors.append("December base historical amount changed")
    if december["final_monthly_value_authorized"] is not False:
        errors.append("December base value may not be promoted to final")

    guards = assessment["scientific_guards"]
    for key in (
        "SSON_included_in_candidate",
        "accepted_or_borrowed_amount_included",
        "missing_months_treated_as_zero",
        "unretained_amendment_inferred",
        "missing_event_rows_inferred",
        "monthly_total_promoted_to_synthetic_event_rows",
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
    if next_gate["id"] != "mof_announced_RON_primary_reference_auction_full_2025_missing_source_recovery":
        errors.append("partial assessment next gate changed")
    if next_gate["authorization"] != "OFFICIAL_SOURCE_RECOVERY_ONLY":
        errors.append("partial assessment next-gate authorization changed")
    if set(next_gate["required_source_ids"]) != EXPECTED_MISSING:
        errors.append("partial assessment missing-source set changed")
    if next_gate["event_materialisation_for_missing_sources_authorized"] is not False:
        errors.append("missing-source event materialisation may not be authorized")
    if next_gate["canonical_promotion_before_complete_required_source_coverage"] is not False:
        errors.append("canonical promotion may not precede complete source coverage")
    if next_gate.get("active_polling") is not False:
        errors.append("remaining source recovery may not actively poll")

    if manifest["raw_sources_retained_count"] != 9:
        errors.append("retained raw-source count changed")
    if manifest["raw_sources_unavailable_count"] != 3:
        errors.append("unavailable raw-source count changed")
    if set(manifest["retained_source_ids"]) != EXPECTED_RETAINED:
        errors.append("retained raw-source set changed")
    if set(manifest["unavailable_source_ids"]) != EXPECTED_MISSING:
        errors.append("manifest missing-source set changed")
    if manifest["canonical_reference_mode_promoted"] is not False:
        errors.append("source-vintage manifest may not promote canonical reference mode")
    if manifest["feedback_activation_authorized"] is not False:
        errors.append("source-vintage manifest may not activate feedback")

    identities = assessment["native_text_identities"]
    if set(identities) != EXPECTED_RETAINED:
        errors.append("native-text identity set changed")
    by_id = {item["source_id"]: item for item in manifest["documents"]}
    for source_id in EXPECTED_RETAINED:
        source = by_id[source_id]
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
    for period, expected in EXPECTED_VALUES.items():
        row = monthly_by_period[period]
        value = row["announced_RON_primary_reference_auction_supply_million"]
        if value == "" or float(value) != expected:
            errors.append(f"{period}: exact monthly value changed")
    if monthly_by_period["2025-11"]["event_count"] != "":
        errors.append("November incomplete event count must remain blank")
    if monthly_by_period["2025-11"]["event_level_complete"] != "False":
        errors.append("November event-complete flag changed")
    for period in ("2025-08", "2025-12"):
        row = monthly_by_period[period]
        if row["announced_RON_primary_reference_auction_supply_million"] != "":
            errors.append(f"{period}: unavailable final month must remain blank")
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
    november_partial = [
        row for row in events
        if row["event_date"].startswith("2025-11")
        and row["materialisation_role"] == "PARTIAL_FINAL_EVENT_SET_BASE_ANNEX1_UNAVAILABLE"
    ]
    if len(november_partial) != 11:
        errors.append("November retained partial event set changed")

    if any(
        mode.get("id") == "announced_RON_primary_reference_auction_supply_level"
        for mode in reference_modes["modes"]
    ):
        errors.append("partial candidate may not appear in canonical reference_modes")

    node = next(item for item in boundary["variables"] if item["id"] == "government_securities_supply_pressure")
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("partial materialisation may not resolve supply-pressure node")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("partial materialisation may not activate supply-pressure node")
    if node["full_year_announced_RON_primary_reference_auction_supply_status"] != EXPECTED_STATUS:
        errors.append("boundary-registry partial supply status changed")
    if node["full_year_announced_RON_primary_reference_auction_supply_missing_required_source_count"] != 3:
        errors.append("boundary-registry missing-source count changed")

    link = next(
        item for item in readiness["links"]
        if item["loop_id"] == "government_issuance_yield_loop"
        and item["from"] == "government_debt_issuance"
        and item["to"] == "government_securities_supply_pressure"
    )
    if link["source_boundary_status"] != EXPECTED_LINK_STATUS:
        errors.append("issuance-pressure link partial status changed")
    if link["exact_integrated_equation_ready"] is not False:
        errors.append("partial materialisation may not make link equation ready")
    if link["current_activation_authorized"] is not False:
        errors.append("partial materialisation may not activate issuance-pressure link")

    loop = next(item for item in feedback["loops"] if item["id"] == "government_issuance_yield_loop")
    if loop["quantitatively_active"] is not False:
        errors.append("partial materialisation may not activate issuance-yield loop")
    if loop["full_year_announced_RON_primary_reference_auction_supply_status"] != EXPECTED_STATUS:
        errors.append("feedback-registry partial supply status changed")

    bridge = next(
        item for item in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if item["id"] == "issuance_to_supply_pressure"
    )
    if bridge["missing_required_source_count"] != 3:
        errors.append("issuance-pressure bridge missing-source count changed")
    if bridge["status"] != EXPECTED_LINK_STATUS:
        errors.append("issuance-pressure bridge partial status changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic["mof_announced_RON_primary_reference_auction_supply_status"] != EXPECTED_STATUS:
        errors.append("model contract partial supply status changed")
    if dynamic["mof_announced_RON_primary_reference_auction_supply_missing_required_source_count"] != 3:
        errors.append("model contract missing-source count changed")
    if dynamic["mof_announced_RON_primary_reference_auction_supply_exact_final_months"] != EXPECTED_MONTHS:
        errors.append("model contract exact month set changed")
    if dynamic["next_government_issuance_yield_empirical_task"] != (
        "government_issuance_yield_loop_evidence_triggered_hold"
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
    prereg = load("model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json")
    model_contract = load("model/registries/model_contract.json")

    errors = audit_partial_announced_supply(
        assessment, manifest, reference_modes, boundary, readiness,
        feedback, prereg, model_contract
    )
    if errors:
        raise RuntimeError(
            "Partial full-2025 announced RON reference-auction audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(json.dumps({
        "status": "PASS",
        "candidate_id": assessment["candidate_id"],
        "exact_final_month_count": 10,
        "event_level_complete_final_month_count": 9,
        "monthly_only_exact_final_months": ["2025-11"],
        "raw_sources_retained": 9,
        "raw_sources_missing": 3,
        "canonical_reference_mode_promoted": False,
        "feedback_activation_authorized": False,
        "next_gate": assessment["next_gate"]["id"],
    }, indent=2))


if __name__ == "__main__":
    main()
