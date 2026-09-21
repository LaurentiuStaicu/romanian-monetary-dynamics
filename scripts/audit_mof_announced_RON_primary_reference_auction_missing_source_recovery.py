from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = (
    "model/dynamics/"
    "mof_announced_RON_primary_reference_auction_missing_source_recovery_assessment_2026_09_20.json"
)
PARTIAL_PATH = (
    "model/dynamics/"
    "mof_announced_RON_primary_reference_auction_partial_2025_assessment.json"
)
RECOVERY_STATUS = "EVIDENCE_TRIGGERED_HOLD_3_REQUIRED_SOURCES_REMAINING"
EXPECTED_MISSING = {
    "mof_order_1221_august_2025",
    "mof_order_1795_november_2025",
    "mof_order_1998_december_2025_amendment",
}


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_missing_source_recovery(
    assessment: dict,
    partial: dict,
    measurement: dict,
    source_review: dict,
    boundary: dict,
    readiness: dict,
    prereg: dict,
    model_contract: dict,
) -> list[str]:
    errors: list[str] = []

    if assessment["status"] != (
        "PARTIAL_RECOVERY_5_OFFICIAL_SOURCES_RECOVERED_"
        "3_REQUIRED_SOURCES_REMAIN_EVIDENCE_TRIGGERED_HOLD"
    ):
        errors.append("missing-source recovery status changed")

    current = assessment["current_materialisation"]
    if current["retained_required_source_count"] != 9:
        errors.append("retained-source count changed")
    if current["required_missing_source_count"] != 3:
        errors.append("missing-source count changed")
    if current["exact_final_month_count"] != 10:
        errors.append("exact-final-month count changed")
    if current["event_level_complete_final_month_count"] != 9:
        errors.append("event-complete-final-month count changed")
    if current["monthly_only_exact_final_months"] != ["2025-11"]:
        errors.append("monthly-only exact month changed")
    if current["canonical_reference_mode_promoted"] is not False:
        errors.append("recovery assessment may not promote canonical reference mode")

    if len(assessment["recovered_sources"]) != 5:
        errors.append("recovered-source count changed")
    recovered_ids = {item["source_id"] for item in assessment["recovered_sources"]}
    if recovered_ids != {
        "mof_order_752_may_2025_amendment",
        "mof_order_1088_july_2025",
        "mof_order_1452_september_2025",
        "mof_order_1831_november_2025_amendment",
        "mof_order_1928_december_2025",
    }:
        errors.append("recovered-source identity set changed")

    missing = assessment["missing_sources"]
    if {item["source_id"] for item in missing} != EXPECTED_MISSING:
        errors.append("remaining missing-source identity set changed")
    for item in missing:
        if item["raw_repository_source_status"] != "UNAVAILABLE":
            errors.append(f"{item['source_id']}: remaining source may not be treated as retained")
        if item["stable_official_pdf_discovered"] is not False:
            errors.append(f"{item['source_id']}: stable official PDF may not be claimed discovered")

    transport = assessment["transport_evidence"]
    if "Five previously missing exact official PDFs" not in transport["successful_recovery"]:
        errors.append("successful recovery evidence changed")
    if "Three required acts" not in transport["remaining_recovery"]:
        errors.append("remaining recovery evidence changed")
    if transport["web_index_text_is_not_treated_as_repository_raw_source"] is not True:
        errors.append("web-index source boundary changed")

    interpretation = assessment["interpretation"]
    if interpretation["documents_do_not_exist"] is not False:
        errors.append("identified acts may not be described as nonexistent")
    if interpretation["public_legal_identity_is_unavailable"] is not False:
        errors.append("public legal identity may not be described as unavailable")
    if interpretation["remaining_repository_raw_retention_is_currently_unavailable"] is not True:
        errors.append("remaining raw-retention blocker must stay explicit")
    for key in (
        "missing_values_may_be_imputed",
        "web_search_snippets_may_be_repository_raw_sources",
        "third_party_reproductions_may_be_repository_raw_sources",
        "later_auction_outcomes_may_reconstruct_ex_ante_announcements",
        "exact_monthly_total_may_substitute_for_missing_event_rows",
    ):
        if interpretation[key] is not False:
            errors.append(f"recovery assessment may not authorize {key}")

    reopen_ids = {item["id"] for item in assessment["reopen_conditions"]}
    if reopen_ids != {
        "stable_official_pdf_or_file_transport",
        "portal_transport_becomes_reproducible",
        "verifiable_official_raw_file_supplied",
    }:
        errors.append("reopen-condition set changed")

    effect = assessment["scientific_effect"]
    for key in (
        "full_year_source_recovery_complete",
        "canonical_reference_mode_promoted",
        "government_securities_supply_pressure_node_resolved",
        "supply_pressure_scalar_selected",
        "yield_effect_estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
    ):
        if effect[key] is not False:
            errors.append(f"recovery assessment may not promote {key}")

    disposition = assessment["path_disposition"]
    if disposition["active_polling"] is not False:
        errors.append("remaining recovery may not actively poll")
    if disposition["state"] != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("recovery path disposition changed")
    if disposition["remaining_required_source_count"] != 3:
        errors.append("recovery disposition remaining count changed")

    independent = assessment["next_independent_issuance_yield_task"]
    if independent["id"] != "yield_to_interest_cost_boundary_review":
        errors.append("next independent issuance-yield task changed")
    if independent["authorization"] != "STRUCTURAL_SOURCE_BOUNDARY_REVIEW_ONLY":
        errors.append("next independent task authorization changed")
    for key in (
        "may_estimate_parameters",
        "may_activate_feedback",
        "may_change_behavioural_closure",
    ):
        if independent[key] is not False:
            errors.append(f"next independent task may not authorize {key}")

    if partial.get("missing_source_recovery_assessment") != ASSESSMENT_PATH:
        errors.append("partial assessment lacks recovery assessment")
    if partial.get("missing_source_recovery_status") != RECOVERY_STATUS:
        errors.append("partial assessment recovery status changed")
    if set(partial["next_gate"]["required_source_ids"]) != EXPECTED_MISSING:
        errors.append("partial assessment remaining-source set changed")
    if partial["next_gate"].get("active_polling") is not False:
        errors.append("partial assessment recovery may not actively poll")

    if measurement.get("announced_supply_missing_source_recovery_assessment") != ASSESSMENT_PATH:
        errors.append("measurement design lacks recovery assessment")
    if measurement["next_task"].get("required_source_count") != 3:
        errors.append("measurement-design remaining source count changed")
    if measurement["next_task"].get("recovery_state") != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("measurement-design recovery state changed")
    if measurement["next_task"].get("active_polling") is not False:
        errors.append("measurement-design recovery may not actively poll")
    if measurement.get("next_independent_issuance_yield_task", {}).get("id") != (
        "financing_channel_allocation_boundary_review"
    ):
        errors.append("measurement-design next independent task changed")

    if source_review.get("announced_supply_missing_source_recovery_assessment") != ASSESSMENT_PATH:
        errors.append("supply-pressure source review lacks recovery assessment")
    if source_review.get("announced_supply_missing_source_recovery_status") != RECOVERY_STATUS:
        errors.append("supply-pressure source recovery status changed")
    if source_review["next_task"].get("required_source_count") != 3:
        errors.append("supply-pressure source remaining count changed")

    node = next(item for item in boundary["variables"] if item["id"] == "government_securities_supply_pressure")
    if node.get("announced_supply_missing_source_recovery_assessment") != ASSESSMENT_PATH:
        errors.append("boundary registry lacks recovery assessment")
    if node.get("announced_supply_missing_source_recovery_status") != RECOVERY_STATUS:
        errors.append("boundary registry recovery status changed")
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("recovery hold may not resolve supply-pressure node")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("recovery hold may not activate supply-pressure node")

    link = next(
        item for item in readiness["links"]
        if item["loop_id"] == "government_issuance_yield_loop"
        and item["from"] == "government_debt_issuance"
        and item["to"] == "government_securities_supply_pressure"
    )
    if link.get("announced_supply_missing_source_recovery_assessment") != ASSESSMENT_PATH:
        errors.append("issuance-pressure link lacks recovery assessment")
    if link.get("announced_supply_missing_source_recovery_status") != RECOVERY_STATUS:
        errors.append("issuance-pressure link recovery status changed")
    if link["exact_integrated_equation_ready"] is not False:
        errors.append("recovery hold may not make link equation ready")
    if link["current_activation_authorized"] is not False:
        errors.append("recovery hold may not activate issuance-pressure link")

    bridge = next(
        item for item in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if item["id"] == "issuance_to_supply_pressure"
    )
    if bridge.get("announced_supply_missing_source_recovery_assessment") != ASSESSMENT_PATH:
        errors.append("issuance-pressure bridge lacks recovery assessment")
    if bridge.get("missing_source_recovery_status") != RECOVERY_STATUS:
        errors.append("issuance-pressure bridge recovery status changed")
    if bridge.get("missing_required_source_count") != 3:
        errors.append("issuance-pressure bridge remaining source count changed")
    if prereg.get("next_independent_bridge_task", {}).get("id") != (
        "mof_realized_financing_channel_source_vintage_probe"
    ):
        errors.append("preregistration next independent bridge changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get(
        "mof_announced_RON_primary_reference_auction_supply_missing_source_recovery_assessment"
    ) != ASSESSMENT_PATH:
        errors.append("model contract lacks recovery assessment")
    if dynamic.get(
        "mof_announced_RON_primary_reference_auction_supply_missing_source_recovery_status"
    ) != RECOVERY_STATUS:
        errors.append("model contract recovery status changed")
    if dynamic.get(
        "mof_announced_RON_primary_reference_auction_supply_missing_required_source_count"
    ) != 3:
        errors.append("model contract remaining source count changed")
    if dynamic.get("government_issuance_yield_next_independent_task") != (
        "mof_realized_financing_channel_source_vintage_probe"
    ):
        errors.append("model contract next independent task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("recovery hold may not authorize issuance-yield feedback")

    return errors


def main() -> None:
    assessment = load(ASSESSMENT_PATH)
    partial = load(PARTIAL_PATH)
    measurement = load("model/dynamics/government_securities_supply_measurement_design_review_2026_09_20.json")
    source_review = load("model/dynamics/government_securities_supply_pressure_source_boundary_review_2026_09_20.json")
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    readiness = load("model/dynamics/feedback_link_readiness_registry.json")
    prereg = load("model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json")
    model_contract = load("model/registries/model_contract.json")

    errors = audit_missing_source_recovery(
        assessment, partial, measurement, source_review,
        boundary, readiness, prereg, model_contract
    )
    if errors:
        raise RuntimeError(
            "Announced-supply missing-source recovery assessment failed:\n- "
            + "\n- ".join(errors)
        )

    print(json.dumps({
        "status": "PASS",
        "recovery_state": "EVIDENCE_TRIGGERED_HOLD",
        "retained_required_sources": 9,
        "missing_source_count": 3,
        "exact_final_month_count": 10,
        "event_level_complete_final_month_count": 9,
        "active_polling": False,
        "canonical_reference_mode_promoted": False,
        "feedback_activation_authorized": False,
        "next_independent_task": "financing_channel_allocation_boundary_review",
    }, indent=2))


if __name__ == "__main__":
    main()
