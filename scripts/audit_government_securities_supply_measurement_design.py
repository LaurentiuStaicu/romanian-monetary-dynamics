from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = (
    "model/dynamics/"
    "government_securities_supply_measurement_design_review_2026_09_20.json"
)


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_supply_measurement_design(
    review: dict,
    source_review: dict,
    denominator_review: dict,
    ecb_assessment: dict,
    boundary: dict,
    readiness: dict,
    feedback: dict,
    prereg: dict,
    model_contract: dict,
) -> list[str]:
    errors: list[str] = []

    if review["decision"] != (
        "STRUCTURED_MEASUREMENT_VECTOR_KEEP_UMBRELLA_NODE_UNRESOLVED"
    ):
        errors.append("supply measurement-design decision changed")

    measures = {item["measure_id"]: item for item in review["measurement_vector"]}
    expected = {
        "announced_RON_primary_supply_level",
        "announced_RON_supply_surprise",
        "announced_RON_duration_supply",
        "primary_auction_absorption",
        "primary_auction_bid_to_cover",
        "secondary_market_liquidity_context",
        "market_capacity_stock_proxy",
    }
    if set(measures) != expected:
        errors.append(
            "measurement vector changed: "
            f"expected={sorted(expected)}, observed={sorted(measures)}"
        )

    announced = measures["announced_RON_primary_supply_level"]
    if announced["timing"] != "EX_ANTE_AT_AUCTION_ANNOUNCEMENT":
        errors.append("announced supply timing changed")
    if announced["preferred_observable"] != "sum_of_announced_RON_target_amounts":
        errors.append("announced supply observable changed")
    if announced["normalisation_required"] is not False:
        errors.append("announced supply may not require normalisation")
    if announced["stock_denominator_required"] is not False:
        errors.append("announced supply may not require stock denominator")
    if announced["activation_ready"] is not False:
        errors.append("announced supply may not be activation-ready")

    surprise = measures["announced_RON_supply_surprise"]
    if surprise["current_source_status"] != (
        "BLOCKED_PREANNOUNCEMENT_EXPECTATION_SOURCE_NOT_FROZEN"
    ):
        errors.append("supply-surprise source status changed")
    if surprise["official_plan_revision_substitute_allowed"] is not False:
        errors.append("official plan revision may not substitute for market expectation")
    if surprise["activation_ready"] is not False:
        errors.append("supply surprise may not be activation-ready")

    duration = measures["announced_RON_duration_supply"]
    if duration["preferred_observable"] != (
        "sum_i(announced_notional_i * preannouncement_DV01_per_RON_i)"
    ):
        errors.append("duration-supply preferred observable changed")
    if duration["fallback_descriptive_observable"] != (
        "announced_notional_by_residual_maturity_bucket"
    ):
        errors.append("duration-supply fallback changed")
    if duration["activation_ready"] is not False:
        errors.append("duration supply may not be activation-ready")

    absorption = measures["primary_auction_absorption"]
    if absorption["timing"] != "POST_AUCTION_OUTCOME":
        errors.append("auction absorption timing changed")
    if absorption["preferred_observable"] != (
        "submitted_RON_bids / announced_RON_amount"
    ):
        errors.append("auction absorption observable changed")
    if absorption["causal_role"] != "AUCTION_ABSORPTION_OUTCOME_DIAGNOSTIC":
        errors.append("auction absorption causal role changed")

    btc = measures["primary_auction_bid_to_cover"]
    if btc["preferred_observable"] != (
        "submitted_RON_bids / accepted_RON_amount"
    ):
        errors.append("bid-to-cover observable changed")
    if btc["causal_role"] != "AUCTION_SUCCESS_AND_DEMAND_DIAGNOSTIC":
        errors.append("bid-to-cover causal role changed")

    liquidity = measures["secondary_market_liquidity_context"]
    if liquidity["causal_role"] != "MODERATOR_OR_CONTROL_NOT_SUPPLY_INPUT":
        errors.append("liquidity context may not be relabelled supply input")

    capacity = measures["market_capacity_stock_proxy"]
    if capacity["causal_role"] != "CONTEXT_OR_SENSITIVITY_SCALER_ONLY":
        errors.append("market-capacity proxy causal role changed")
    if capacity["activation_ready"] is not False:
        errors.append("market-capacity proxy may not be activation-ready")

    topology = review["structural_topology"]
    if topology["umbrella_node_status"] != (
        "QUALITATIVE_UNRESOLVED_MEASUREMENT_LAYER"
    ):
        errors.append("umbrella supply-pressure node status changed")
    if topology["replace_single_scalar_search"] is not True:
        errors.append("single-scalar search must remain replaced")
    if topology["scalar_composite_authorized"] is not False:
        errors.append("scalar composite may not be authorized")
    if topology["arbitrary_weighted_index_authorized"] is not False:
        errors.append("arbitrary weighted index may not be authorized")

    if set(topology["ex_ante_supply_inputs"]) != {
        "announced_RON_primary_supply_level",
        "announced_RON_supply_surprise",
        "announced_RON_duration_supply",
    }:
        errors.append("ex-ante supply-input set changed")
    if set(topology["post_auction_outcome_diagnostics"]) != {
        "primary_auction_absorption",
        "primary_auction_bid_to_cover",
    }:
        errors.append("post-auction diagnostic set changed")

    strategy = review["reference_mode_strategy"]
    if strategy["first_materialisation_priority"] != (
        "announced_RON_primary_supply_level"
    ):
        errors.append("first supply reference-mode priority changed")
    if strategy["completed_period_only_for_reference_mode"] is not True:
        errors.append("reference mode must remain completed-period only")
    if strategy[
        "forward_schedule_rows_may_be_retained_as_expectation_information_but_not_as_realised_completed_month_supply"
    ] is not True:
        errors.append("forward schedule handling changed")

    effect = review["scientific_effect"]
    if effect["measurement_vector_adopted_for_recovery"] is not True:
        errors.append("measurement vector must remain adopted for recovery")
    if effect["stock_normalised_supply_load_required"] is not False:
        errors.append("stock-normalised supply load may not be required")
    for key in (
        "government_securities_supply_pressure_node_resolved",
        "single_supply_pressure_scalar_selected",
        "exact_reference_mode_promoted",
        "equation_selected",
        "estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
    ):
        if effect[key] is not False:
            errors.append(f"measurement design may not promote {key}")

    next_task = review["next_task"]
    if next_task["id"] != "mof_announced_RON_primary_supply_source_vintage_pilot":
        errors.append("measurement-design next task changed")
    if next_task["authorization"] != (
        "RAW_SOURCE_RETENTION_EXACT_EVENT_EXTRACTION_AND_REFERENCE_MODE_PILOT_ONLY"
    ):
        errors.append("measurement-design next-task authorization changed")
    if next_task["may_materialise_announced_supply_reference_mode"] is not True:
        errors.append("announced supply reference-mode materialisation must be authorized")
    for key in (
        "may_materialise_supply_surprise",
        "may_materialise_duration_supply",
        "may_estimate_supply_to_yield_effect",
        "may_activate_feedback",
    ):
        if next_task[key] is not False:
            errors.append(f"measurement-design next task may not authorize {key}")

    if source_review.get("supply_measurement_design_review") != REVIEW_PATH:
        errors.append("source-boundary review lacks measurement design")
    if source_review.get("measurement_architecture_status") != (
        "STRUCTURED_MEASUREMENT_VECTOR_KEEP_UMBRELLA_NODE_UNRESOLVED"
    ):
        errors.append("source-boundary measurement architecture changed")
    if source_review.get("single_scalar_search_superseded_for_primary_recovery_path") is not True:
        errors.append("source-boundary scalar search not marked superseded")
    if source_review["next_task"]["id"] != (
        "mof_announced_RON_primary_supply_source_vintage_pilot"
    ):
        errors.append("source-boundary next task not advanced")

    if denominator_review.get("supply_measurement_design_review") != REVIEW_PATH:
        errors.append("denominator review lacks measurement design")
    if denominator_review.get("denominator_search_status") != (
        "FROZEN_NOT_REQUIRED_FOR_FIRST_EX_ANTE_REFERENCE_MODE"
    ):
        errors.append("denominator search status changed")
    if denominator_review["decision_effect"].get(
        "stock_normalised_supply_load_required"
    ) is not False:
        errors.append("denominator review may not require stock-normalised load")

    if ecb_assessment.get("supply_measurement_design_review") != REVIEW_PATH:
        errors.append("ECB assessment lacks measurement design")
    if ecb_assessment["next_gate"]["id"] != (
        "mof_announced_RON_primary_supply_reference_mode_contract"
    ):
        errors.append("ECB assessment next gate not advanced")

    node = next(
        item for item in boundary["variables"]
        if item["id"] == "government_securities_supply_pressure"
    )
    if node.get("supply_measurement_design_review") != REVIEW_PATH:
        errors.append("boundary registry lacks measurement design")
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("measurement design may not resolve umbrella node")
    if node.get("single_scalar_selected") is not False:
        errors.append("boundary registry may not select scalar")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("measurement design may not activate umbrella node")

    link = next(
        item for item in readiness["links"]
        if item["loop_id"] == "government_issuance_yield_loop"
        and item["from"] == "government_debt_issuance"
        and item["to"] == "government_securities_supply_pressure"
    )
    if link.get("supply_measurement_design_review") != REVIEW_PATH:
        errors.append("issuance-pressure link lacks measurement design")
    if link["source_boundary_status"] != (
        "STRUCTURED_VECTOR_ANNOUNCED_SUPPLY_SOURCE_CONTRACT_FROZEN_PILOT_NOT_MATERIALISED"
    ):
        errors.append("issuance-pressure measurement status changed")
    if link["exact_integrated_equation_ready"] is not False:
        errors.append("measurement design may not make integrated equation ready")
    if link["current_activation_authorized"] is not False:
        errors.append("measurement design may not activate link")

    loop = next(
        item for item in feedback["loops"]
        if item["id"] == "government_issuance_yield_loop"
    )
    if loop.get("government_securities_supply_measurement_design_review") != REVIEW_PATH:
        errors.append("feedback registry lacks measurement design")
    if loop.get("supply_pressure_measurement_architecture") != (
        "STRUCTURED_VECTOR_UMBRELLA_UNRESOLVED"
    ):
        errors.append("feedback registry measurement architecture changed")
    if loop.get("supply_pressure_scalar_selected") is not False:
        errors.append("feedback registry may not select supply-pressure scalar")
    if loop["quantitatively_active"] is not False:
        errors.append("measurement design may not activate feedback loop")

    bridge = next(
        item for item in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if item["id"] == "issuance_to_supply_pressure"
    )
    if bridge.get("supply_measurement_design_review") != REVIEW_PATH:
        errors.append("issuance-pressure bridge lacks measurement design")
    if bridge["status"] != (
        "STRUCTURED_VECTOR_ANNOUNCED_SUPPLY_SOURCE_CONTRACT_FROZEN_PILOT_NOT_MATERIALISED"
    ):
        errors.append("issuance-pressure bridge measurement status changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("government_securities_supply_measurement_design_review") != REVIEW_PATH:
        errors.append("model contract lacks measurement design")
    if dynamic.get("government_securities_supply_measurement_architecture") != (
        "STRUCTURED_MEASUREMENT_VECTOR_KEEP_UMBRELLA_NODE_UNRESOLVED"
    ):
        errors.append("model contract measurement architecture changed")
    if dynamic.get("government_securities_supply_first_reference_mode_priority") != (
        "announced_RON_primary_supply_level"
    ):
        errors.append("model contract supply reference-mode priority changed")
    if dynamic.get("government_securities_supply_stock_normalisation_required") is not False:
        errors.append("model contract may not require stock normalisation")
    if dynamic["next_government_issuance_yield_empirical_task"] != (
        "mof_announced_RON_primary_supply_source_vintage_pilot"
    ):
        errors.append("model contract next task changed")

    return errors


def main() -> None:
    review = load(REVIEW_PATH)
    source_review = load(
        "model/dynamics/government_securities_supply_pressure_source_boundary_review_2026_09_20.json"
    )
    denominator_review = load(
        "model/dynamics/government_securities_supply_load_denominator_boundary_review_2026_09_20.json"
    )
    ecb_assessment = load(
        "model/dynamics/government_securities_supply_load_ecb_denominator_probe_assessment_2026_09_20.json"
    )
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    readiness = load("model/dynamics/feedback_link_readiness_registry.json")
    feedback = load("model/dynamics/feedback_registry.json")
    prereg = load(
        "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
    )
    model_contract = load("model/registries/model_contract.json")

    errors = audit_supply_measurement_design(
        review,
        source_review,
        denominator_review,
        ecb_assessment,
        boundary,
        readiness,
        feedback,
        prereg,
        model_contract,
    )
    if errors:
        raise RuntimeError(
            "Government securities supply measurement-design audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(
        json.dumps(
            {
                "status": "PASS",
                "architecture": "STRUCTURED_MEASUREMENT_VECTOR",
                "measurement_components": 7,
                "ex_ante_supply_inputs": 3,
                "post_auction_diagnostics": 2,
                "market_context_measures": 2,
                "single_scalar_selected": False,
                "umbrella_node_resolved": False,
                "first_reference_mode_priority": "announced_RON_primary_supply_level",
                "feedback_activation_authorized": False,
                "next_task": "mof_announced_RON_primary_supply_source_vintage_pilot",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
