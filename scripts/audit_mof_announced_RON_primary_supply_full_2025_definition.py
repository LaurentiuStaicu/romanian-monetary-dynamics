from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = "model/dynamics/mof_announced_RON_primary_supply_full_2025_definition_review_2026_09_20.json"
NEW_ID = "announced_RON_primary_reference_auction_supply_level"
NEXT_TASK = (
    "mof_announced_RON_primary_reference_auction_supply_full_2025_source_vintage"
)
CURRENT_TASK = (
    "mof_announced_RON_primary_reference_auction_full_2025_missing_source_recovery"
)
CURRENT_STATUS = (
    "STRUCTURED_VECTOR_COMPETITIVE_ONLY_PARTIAL_EXACT_6_FINAL_MONTHS_"
    "8_REQUIRED_SOURCES_MISSING_CANONICAL_PROMOTION_BLOCKED"
)
CURRENT_MEASURE_STATUS = (
    "PARTIAL_EXACT_EVENT_MATERIALISATION_6_FINAL_MONTHS_"
    "8_REQUIRED_SOURCES_MISSING_CANONICAL_PROMOTION_BLOCKED"
)


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_full_2025_definition(
    review: dict,
    measurement_design: dict,
    q1_pilot: dict,
    source_review: dict,
    boundary: dict,
    readiness: dict,
    feedback: dict,
    prereg: dict,
    model_contract: dict,
) -> list[str]:
    errors: list[str] = []

    if review["decision"] != (
        "DO_NOT_EXTEND_Q1_COMBINED_REFERENCE_AUCTION_PLUS_SSON_SCALAR_UNCHANGED_TO_FULL_2025"
    ):
        errors.append("full-year definition decision changed")

    design = review["full_year_measurement_design"]
    if design["canonical_candidate_id"] != NEW_ID:
        errors.append("full-year candidate id changed")
    if design["unit"] != "million_RON_nominal":
        errors.append("full-year candidate unit changed")
    if set(design["included_event_types"]) != {
        "T_BILL_COMPETITIVE_REFERENCE_AUCTION",
        "BENCHMARK_BOND_COMPETITIVE_REFERENCE_AUCTION",
    }:
        errors.append("competitive-only event boundary changed")
    if "BENCHMARK_BOND_SSON" not in design["excluded_from_canonical_candidate"]:
        errors.append("SSON must remain excluded from canonical full-year candidate")
    if design["stock_normalisation_required"] is not False:
        errors.append("full-year candidate may not require stock normalisation")
    if design["canonical_promotion_authorized_now"] is not False:
        errors.append("definition review may not authorize canonical promotion")

    sson = review["SSON_auxiliary"]
    if sson["candidate_id"] != "announced_RON_fixed_SSON_capacity":
        errors.append("SSON auxiliary id changed")
    if "15%" not in sson["December"]:
        errors.append("December adjudication-dependent 15% SSON rule missing")
    if sson["missing_or_formula_dependent_is_not_zero"] is not True:
        errors.append("formula-dependent SSON may not be converted to zero")

    months = {item["month"]: item for item in review["official_legal_screening"]["months"]}
    if set(months) != {f"2025-{m:02d}" for m in range(4, 13)}:
        errors.append("April-December legal-screening month set changed")

    expected_amendments = {
        "2025-05": ("752/2025", "2025-05-07"),
        "2025-11": ("1831/2025", "2025-11-10"),
        "2025-12": ("1998/2025", "2025-12-19"),
    }
    for period, (order, date) in expected_amendments.items():
        item = months[period]
        if item["amendment_identified_in_screening"] is not True:
            errors.append(f"{period}: required amendment flag missing")
            continue
        amendments = item.get("amendments", [])
        if not any(
            amendment.get("order") == order and amendment.get("order_date") == date
            for amendment in amendments
        ):
            errors.append(f"{period}: expected amendment {order} on {date} missing")

    for period in ("2025-04", "2025-06", "2025-07", "2025-08", "2025-09", "2025-10"):
        if months[period]["amendment_identified_in_screening"] is not False:
            errors.append(f"{period}: unverified amendment introduced")

    december = months["2025-12"]
    if december["SSON_rule"] != (
        "15_percent_of_nominal_amount_adjudicated_at_reference_auctions"
    ):
        errors.append("December SSON rule changed")
    if december["fixed_nominal_SSON_amount_known_at_announcement"] is not False:
        errors.append("December SSON may not be treated as fixed nominal ex ante")

    amendment = review["amendment_handling"]
    for key in (
        "versioned_announcement_history_required",
        "base_order_rows_may_not_be_silently_overwritten",
        "amendment_order_date_is_new_information_date",
        "monthly_final_schedule_may_use_latest_legally_effective_schedule",
        "prospective_or_as_of_analysis_must_use_schedule_known_at_each_information_date",
    ):
        if amendment[key] is not True:
            errors.append(f"amendment handling guard changed: {key}")

    q1 = review["Q1_disposition"]
    if q1["legacy_Q1_pilot_remains_valid_on_its_frozen_definition"] is not True:
        errors.append("legacy Q1 pilot validity changed")
    if q1["legacy_Q1_pilot_may_be_rewritten_in_place"] is not False:
        errors.append("legacy Q1 pilot may not be rewritten in place")
    if q1["full_year_comparable_competitive_only_Q1_subset_may_be_derived_from_retained_Q1_events"] is not True:
        errors.append("competitive-only Q1 subset derivation must remain allowed")

    effect = review["scientific_effect"]
    for key in (
        "legacy_Q1_reference_mode_promoted",
        "full_year_canonical_candidate_promoted",
        "government_securities_supply_pressure_node_resolved",
        "yield_effect_estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
    ):
        if effect[key] is not False:
            errors.append(f"definition review may not promote {key}")

    next_task = review["next_task"]
    if next_task["id"] != NEXT_TASK:
        errors.append("definition review next task changed")
    if next_task["authorization"] != (
        "OFFICIAL_SOURCE_RETENTION_AMENDMENT_AWARE_EVENT_MATERIALISATION_ONLY"
    ):
        errors.append("definition review next-task authorization changed")
    if next_task["may_estimate_supply_to_yield_effect"] is not False:
        errors.append("definition review may not authorize yield-effect estimation")
    if next_task["may_activate_feedback"] is not False:
        errors.append("definition review may not activate feedback")

    measures = {item["measure_id"]: item for item in measurement_design["measurement_vector"]}
    if NEW_ID not in measures:
        errors.append("measurement design lacks full-year competitive candidate")
    else:
        new = measures[NEW_ID]
        if new["preferred_observable"] != "sum_of_competitive_announced_RON_reference_targets":
            errors.append("full-year competitive observable changed")
        if new["current_source_status"] != CURRENT_MEASURE_STATUS:
            errors.append("full-year source status changed")
        if new["activation_ready"] is not False:
            errors.append("full-year candidate may not be activation-ready")
        if new.get("full_2025_definition_review") != REVIEW_PATH:
            errors.append("full-year candidate lacks definition review")

    legacy = measures.get("announced_RON_primary_supply_level")
    if legacy is None:
        errors.append("legacy Q1 measure must remain in audit history")
    else:
        if legacy.get("primary_recovery_path") is not False:
            errors.append("legacy Q1 combined measure may not remain primary recovery path")
        if legacy.get("full_2025_definition_review") != REVIEW_PATH:
            errors.append("legacy Q1 measure lacks full-year definition review")

    if measurement_design["reference_mode_strategy"]["first_materialisation_priority"] != NEW_ID:
        errors.append("measurement-design first reference-mode priority changed")
    if measurement_design["next_task"]["id"] != CURRENT_TASK:
        errors.append("measurement-design next task changed")

    if q1_pilot.get("full_2025_definition_review") != REVIEW_PATH:
        errors.append("Q1 pilot lacks full-year definition review")
    if q1_pilot["scientific_disposition"]["legacy_Q1_definition_retained"] is not True:
        errors.append("Q1 pilot legacy definition not retained")
    if q1_pilot["scientific_disposition"]["legacy_Q1_definition_is_full_year_stable"] is not False:
        errors.append("Q1 legacy definition may not be called full-year stable")
    if q1_pilot["next_gate"]["id"] != NEXT_TASK:
        errors.append("Q1 pilot next gate changed")

    if source_review.get("mof_announced_RON_primary_supply_full_2025_definition_review") != REVIEW_PATH:
        errors.append("supply-pressure source review lacks full-year definition review")
    if source_review.get("full_year_primary_supply_candidate_id") != NEW_ID:
        errors.append("supply-pressure source review full-year candidate changed")
    if source_review["next_task"]["id"] != CURRENT_TASK:
        errors.append("supply-pressure source review next task changed")

    node = next(
        item for item in boundary["variables"]
        if item["id"] == "government_securities_supply_pressure"
    )
    if node.get("mof_announced_RON_primary_supply_full_2025_definition_review") != REVIEW_PATH:
        errors.append("boundary registry lacks full-year definition review")
    if node.get("full_year_announced_RON_primary_reference_auction_supply_candidate_id") != NEW_ID:
        errors.append("boundary registry full-year candidate changed")
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("definition review may not resolve supply-pressure node")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("definition review may not activate supply-pressure node")

    link = next(
        item for item in readiness["links"]
        if item["loop_id"] == "government_issuance_yield_loop"
        and item["from"] == "government_debt_issuance"
        and item["to"] == "government_securities_supply_pressure"
    )
    if link.get("mof_announced_RON_primary_supply_full_2025_definition_review") != REVIEW_PATH:
        errors.append("issuance-pressure link lacks full-year definition review")
    if link["source_boundary_status"] != CURRENT_STATUS:
        errors.append("issuance-pressure link full-year status changed")
    if link["exact_integrated_equation_ready"] is not False:
        errors.append("definition review may not make integrated equation ready")
    if link["current_activation_authorized"] is not False:
        errors.append("definition review may not activate issuance-pressure link")

    loop = next(
        item for item in feedback["loops"]
        if item["id"] == "government_issuance_yield_loop"
    )
    if loop.get("mof_announced_RON_primary_supply_full_2025_definition_review") != REVIEW_PATH:
        errors.append("feedback registry lacks full-year definition review")
    if loop["quantitatively_active"] is not False:
        errors.append("definition review may not activate issuance-yield loop")

    bridge = next(
        item for item in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if item["id"] == "issuance_to_supply_pressure"
    )
    if bridge.get("mof_announced_RON_primary_supply_full_2025_definition_review") != REVIEW_PATH:
        errors.append("issuance-pressure bridge lacks full-year definition review")
    if bridge.get("full_year_primary_supply_candidate_id") != NEW_ID:
        errors.append("issuance-pressure bridge full-year candidate changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("mof_announced_RON_primary_supply_full_2025_definition_review") != REVIEW_PATH:
        errors.append("model contract lacks full-year definition review")
    if dynamic.get("mof_announced_RON_primary_reference_auction_supply_candidate_id") != NEW_ID:
        errors.append("model contract full-year candidate changed")
    if dynamic["mof_announced_RON_primary_supply_reference_mode_status"] != (
        "PASS_EXACT_Q1_LEGACY_COMBINED_PILOT_FULL_YEAR_DEFINITION_NOT_STABLE"
    ):
        errors.append("model contract legacy Q1 status changed")
    if dynamic["government_securities_supply_first_reference_mode_priority"] != NEW_ID:
        errors.append("model contract full-year reference-mode priority changed")
    if dynamic["next_government_issuance_yield_empirical_task"] != CURRENT_TASK:
        errors.append("model contract next task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("definition review may not authorize issuance-yield feedback")

    return errors


def main() -> None:
    review = load(REVIEW_PATH)
    measurement_design = load(
        "model/dynamics/government_securities_supply_measurement_design_review_2026_09_20.json"
    )
    q1_pilot = load(
        "model/dynamics/mof_announced_RON_primary_supply_reference_mode_pilot_Q1_2025.json"
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

    errors = audit_full_2025_definition(
        review,
        measurement_design,
        q1_pilot,
        source_review,
        boundary,
        readiness,
        feedback,
        prereg,
        model_contract,
    )
    if errors:
        raise RuntimeError(
            "Full-2025 announced RON supply definition audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(
        json.dumps(
            {
                "status": "PASS",
                "legacy_Q1_definition_retained": True,
                "legacy_Q1_full_year_stable": False,
                "full_year_candidate_id": NEW_ID,
                "canonical_candidate_includes_SSON": False,
                "amendment_months": ["2025-05", "2025-11", "2025-12"],
                "december_fixed_nominal_SSON_ex_ante": False,
                "canonical_reference_mode_promoted": False,
                "feedback_activation_authorized": False,
                "next_task": NEXT_TASK,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
