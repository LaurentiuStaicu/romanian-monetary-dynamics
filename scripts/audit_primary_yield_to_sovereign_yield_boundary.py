from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = (
    "model/dynamics/"
    "primary_yield_to_sovereign_yield_boundary_review_2026_09_20.json"
)


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_primary_yield_to_sovereign_yield_boundary(
    review: dict,
    boundary: dict,
    readiness: dict,
    feedback: dict,
    prereg: dict,
    model_contract: dict,
    selection_result: dict,
) -> list[str]:
    errors: list[str] = []

    if review["decision"] != (
        "DO_NOT_AGGREGATE_PRIMARY_ISSUE_RATES_INTO_GENERIC_SOVEREIGN_YIELD_"
        "KEEP_UMBRELLA_NODE_UNRESOLVED"
    ):
        errors.append("primary-to-sovereign-yield boundary decision changed")

    primary = review["primary_market_boundary"]
    if primary["generic_scalar_aggregation_authorized"] is not False:
        errors.append("primary-market rate vector may not be aggregated generically")
    if primary["status"] != (
        "EXACT_RETAINED_2025_INSTRUMENT_AND_CURRENCY_SPECIFIC_PRIMARY_MARKET_RATES"
    ):
        errors.append("primary-market observed boundary status changed")

    long_term = review["long_term_RON_boundary"]
    if long_term["candidate_id"] != "RON_10Y_long_term_sovereign_yield":
        errors.append("long-term candidate id changed")
    if long_term["series_key"] != "IRS.M.RO.L.L40.CI.0000.RON.N.Z":
        errors.append("ECB long-term series key changed")
    if long_term["maturity"] != "10 years":
        errors.append("ECB long-term maturity changed")
    if long_term["currency"] != "RON":
        errors.append("ECB long-term currency changed")
    if long_term["generic_sovereign_yield_node_resolution_authorized"] is not False:
        errors.append("10Y candidate may not resolve generic sovereign-yield node")

    mapping = review["mapping_assessment"]
    if mapping["primary_market_issue_rate_to_generic_sovereign_yield"] != (
        "NOT_ONE_TO_ONE_AND_NO_EX_ANTE_AGGREGATION_RULE_JUSTIFIED"
    ):
        errors.append("primary-to-generic mapping disposition changed")
    if mapping["RON_10Y_long_term_yield_to_generic_sovereign_yield"] != (
        "VALID_SPECIFIC_LONG_TERM_BOUNDARY_NOT_GENERIC_NODE_RESOLUTION"
    ):
        errors.append("10Y-to-generic mapping disposition changed")
    if mapping["generic_sovereign_yield_to_interest_cost"] != (
        "REQUIRES_SEPARATE_DEBT_STOCK_PROPAGATION_BRIDGE"
    ):
        errors.append("yield-to-interest-cost bridge requirement changed")

    umbrella = review["umbrella_node_disposition"]
    if umbrella["current_boundary_class"] != "UNRESOLVED":
        errors.append("generic sovereign-yield node may not be resolved")
    if umbrella["keep_generic_umbrella_node"] is not True:
        errors.append("generic sovereign-yield umbrella must remain explicit")
    if umbrella["narrow_generic_node_to_10Y_now"] is not False:
        errors.append("generic node may not be silently narrowed to 10Y")
    if umbrella["current_feedback_activation_authorized"] is not False:
        errors.append("generic sovereign-yield node may not activate feedback")

    failed = review["existing_structural_selection_evidence"]
    if failed["selection_verdict"] != "FAIL_BEFORE_HOLDOUT":
        errors.append("existing sovereign-yield selection verdict changed")
    if failed["final_evaluation_opened"] is not False:
        errors.append("failed sovereign-yield holdout may not be opened retroactively")
    if failed["causal_claim_allowed"] is not False:
        errors.append("failed sovereign-yield selection may not support causal claim")
    if failed["system_dynamics_activation"] is not False:
        errors.append("failed sovereign-yield selection may not activate SD feedback")
    if selection_result["selection_verdict"] != "FAIL_BEFORE_HOLDOUT":
        errors.append("retained structural-selection result changed")
    if selection_result["final_evaluation_opened"] is not False:
        errors.append("retained structural-selection holdout state changed")

    effect = review["scientific_effect"]
    if effect["primary_market_rate_vector_retained_as_descriptive_evidence"] is not True:
        errors.append("primary-market rate evidence must remain descriptive")
    if effect["RON_10Y_long_term_boundary_recognized_as_exact_observed_candidate"] is not True:
        errors.append("exact 10Y observed boundary recognition changed")
    for key in (
        "generic_sovereign_yield_node_resolved",
        "generic_sovereign_yield_scalar_constructed",
        "primary_to_sovereign_aggregation_selected",
        "reference_mode_promoted",
        "equation_selected",
        "estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
    ):
        if effect[key] is not False:
            errors.append(f"boundary review may not promote {key}")

    disposition = review["bridge_disposition"]
    if disposition["id"] != "primary_yield_to_sovereign_yield":
        errors.append("bridge disposition id changed")
    if disposition["status"] != (
        "BOUNDARY_REVIEWED_NO_ONE_TO_ONE_MAPPING_NO_GENERIC_AGGREGATION"
    ):
        errors.append("bridge disposition status changed")
    if disposition["closed_empirical_bridge_claim_allowed"] is not False:
        errors.append("review may not claim a closed empirical primary-to-yield bridge")

    next_task = review["next_independent_bridge_task"]
    if next_task["id"] != "yield_to_interest_cost_boundary_review":
        errors.append("next independent bridge task changed")
    if next_task["authorization"] != "STRUCTURAL_SOURCE_BOUNDARY_REVIEW_ONLY":
        errors.append("next independent bridge authorization changed")
    for key in (
        "may_select_interest_cost_equation",
        "may_estimate_yield_to_cost_effect",
        "may_activate_feedback",
    ):
        if next_task[key] is not False:
            errors.append(f"next bridge review may not authorize {key}")

    node = next(x for x in boundary["variables"] if x["id"] == "sovereign_yield")
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("boundary registry sovereign_yield unexpectedly resolved")
    if node.get("primary_yield_to_sovereign_yield_boundary_review") != REVIEW_PATH:
        errors.append("boundary registry lacks primary-to-sovereign review")
    if node.get("exact_long_term_candidate_id") != "RON_10Y_long_term_sovereign_yield":
        errors.append("boundary registry exact long-term candidate changed")
    if node.get("exact_long_term_candidate_series_key") != "IRS.M.RO.L.L40.CI.0000.RON.N.Z":
        errors.append("boundary registry ECB series key changed")
    if node.get("primary_market_rate_vector_generic_aggregation_authorized") is not False:
        errors.append("boundary registry may not authorize primary-rate aggregation")
    if node.get("generic_node_narrowing_to_10Y_authorized") is not False:
        errors.append("boundary registry may not narrow generic node to 10Y")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("boundary registry may not activate sovereign_yield")

    link = next(
        x for x in readiness["links"]
        if x["loop_id"] == "government_issuance_yield_loop"
        and x["from"] == "government_securities_supply_pressure"
        and x["to"] == "sovereign_yield"
    )
    if link.get("primary_yield_to_sovereign_yield_boundary_review") != REVIEW_PATH:
        errors.append("supply-to-yield link lacks yield-boundary review")
    if link["readiness_status"] != (
        "RELATED_MECHANISM_AND_EXACT_10Y_BOUNDARY_NOT_EXACT_INTEGRATED_LINK_FORM"
    ):
        errors.append("supply-to-yield link readiness changed")
    if link["exact_integrated_equation_ready"] is not False:
        errors.append("yield-boundary review may not make integrated link ready")
    if link["current_activation_authorized"] is not False:
        errors.append("yield-boundary review may not activate supply-to-yield link")

    loop = next(x for x in feedback["loops"] if x["id"] == "government_issuance_yield_loop")
    if loop.get("primary_yield_to_sovereign_yield_boundary_review") != REVIEW_PATH:
        errors.append("feedback registry lacks yield-boundary review")
    if loop.get("primary_market_rate_to_generic_sovereign_yield_aggregation_authorized") is not False:
        errors.append("feedback registry may not authorize generic primary-rate aggregation")
    if loop["quantitatively_active"] is not False:
        errors.append("yield-boundary review may not activate issuance-yield loop")

    bridge = next(
        x for x in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if x["id"] == "primary_yield_to_sovereign_yield"
    )
    if bridge.get("boundary_review") != REVIEW_PATH:
        errors.append("preregistration primary-yield bridge lacks boundary review")
    if bridge.get("status") != (
        "BOUNDARY_REVIEWED_NO_ONE_TO_ONE_MAPPING_NO_GENERIC_AGGREGATION"
    ):
        errors.append("preregistration primary-yield bridge status changed")
    if bridge.get("closed_empirical_bridge_claim_allowed") is not False:
        errors.append("preregistration may not close primary-yield bridge")
    if prereg["next_independent_bridge_task"]["id"] != "yield_to_interest_cost_boundary_review":
        errors.append("preregistration next independent bridge changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("primary_yield_to_sovereign_yield_boundary_review") != REVIEW_PATH:
        errors.append("model contract lacks yield-boundary review")
    if dynamic.get("primary_yield_to_sovereign_yield_boundary_status") != (
        "BOUNDARY_REVIEWED_NO_ONE_TO_ONE_MAPPING_NO_GENERIC_AGGREGATION"
    ):
        errors.append("model contract primary-yield boundary status changed")
    if dynamic.get("sovereign_yield_exact_long_term_candidate_series_key") != (
        "IRS.M.RO.L.L40.CI.0000.RON.N.Z"
    ):
        errors.append("model contract exact long-term yield key changed")
    if dynamic.get("sovereign_yield_generic_node_resolved") is not False:
        errors.append("model contract may not resolve generic sovereign_yield")
    if dynamic.get("government_issuance_yield_next_independent_task") != (
        "yield_to_interest_cost_boundary_review"
    ):
        errors.append("model contract next independent task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("yield-boundary review may not authorize issuance-yield feedback")

    return errors


def main() -> None:
    review = load(REVIEW_PATH)
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    readiness = load("model/dynamics/feedback_link_readiness_registry.json")
    feedback = load("model/dynamics/feedback_registry.json")
    prereg = load("model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json")
    model_contract = load("model/registries/model_contract.json")
    selection_result = load("model/calibration_validation/sovereign_yield_structural_selection_result.json")

    errors = audit_primary_yield_to_sovereign_yield_boundary(
        review, boundary, readiness, feedback, prereg, model_contract, selection_result
    )
    if errors:
        raise RuntimeError(
            "Primary-yield to sovereign-yield boundary audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(json.dumps({
        "status": "PASS",
        "generic_sovereign_yield_node_resolved": False,
        "primary_rate_generic_aggregation_authorized": False,
        "exact_long_term_candidate": "RON_10Y_long_term_sovereign_yield",
        "exact_long_term_series_key": "IRS.M.RO.L.L40.CI.0000.RON.N.Z",
        "existing_structural_selection_verdict": "FAIL_BEFORE_HOLDOUT",
        "feedback_activation_authorized": False,
        "next_independent_bridge_task": "yield_to_interest_cost_boundary_review",
    }, indent=2))


if __name__ == "__main__":
    main()
