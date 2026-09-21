from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = "model/dynamics/interest_cost_to_financing_need_boundary_review_2026_09_21.json"
BURDEN_PATH = "model/dynamics/government_interest_burden_reference_assessment.json"
REFINANCING_PATH = "model/dynamics/government_refinancing_need_reference_assessment.json"
FISCAL_BOUNDARY_PATH = "model/calibration_validation/fiscal_primary_balance_source_boundary_review.json"
PREREG_PATH = "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
STATUS = (
    "REVIEWED_POSITIVE_STRUCTURAL_DIRECTION_GFN_DECOMPOSITION_VALID_"
    "EXACT_INTEGRATED_CASH_ACCOUNTING_BOUNDARY_UNRESOLVED"
)


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_interest_cost_to_financing_need_boundary(
    review: dict,
    burden: dict,
    refinancing: dict,
    fiscal_boundary: dict,
    boundary: dict,
    readiness: dict,
    feedback: dict,
    prereg: dict,
    model_contract: dict,
    baseline: dict,
) -> list[str]:
    errors: list[str] = []

    if review["decision"] != (
        "DO_NOT_EQUATE_GOVERNMENT_INTEREST_COST_WITH_FINANCING_NEED_"
        "KEEP_GFN_COMPONENT_DECOMPOSITION_EXPLICIT_EXACT_INTEGRATED_"
        "BOUNDARY_UNRESOLVED"
    ):
        errors.append("interest-cost/financing-need decision changed")

    evidence = review["official_source_evidence"]

    d41 = evidence["eurostat_accrual_interest"]
    if d41["reference_mode"] != "government_interest_burden":
        errors.append("D41 reference-mode identity changed")
    if d41["timing"] != "ACCRUAL_NOT_CASH":
        errors.append("D41 accrual/cash timing boundary changed")
    if d41["direct_cash_financing_requirement_equivalent"] is not False:
        errors.append("D41 may not be treated as direct cash financing requirement")
    if burden["verdict"] != "PROMOTE_TO_OBSERVED_SERIES_AVAILABLE":
        errors.append("government-interest-burden reference is no longer observed")

    fiscal = evidence["eurostat_overall_and_primary_balance"]
    if fiscal["exact_matched_identity"] != (
        "primary_balance_pct_gdp = B9_pct_gdp + D41PAY_pct_gdp"
    ):
        errors.append("ESA matched primary-balance identity changed")
    if fiscal["exact_GFN_identity_established"] is not False:
        errors.append("ESA fiscal identity may not be relabelled exact GFN identity")
    if fiscal_boundary["primary_balance_measurement_boundary"]["accounting_identity"] != (
        "primary_balance = net_lending_borrowing + interest_expenditure, "
        "when both components share a compatible accounting/unit/seasonal boundary "
        "and interest expenditure is expressed as a positive use."
    ):
        errors.append("retained fiscal accounting identity changed")

    mof_refi = evidence["mof_refinancing_component"]
    if mof_refi["reference_mode"] != "government_refinancing_need":
        errors.append("MoF refinancing reference-mode identity changed")
    if mof_refi["gross_financing_need_equivalent"] is not False:
        errors.append("MoF refinancing need may not equal GFN")
    if mof_refi["interest_expenditure_equivalent"] is not False:
        errors.append("MoF refinancing need may not equal interest expenditure")
    if refinancing["verdict"] != "OBSERVED_SERIES_AVAILABLE_AFTER_HISTORICAL_CONTINUITY_GATE":
        errors.append("government-refinancing-need reference is no longer observed")

    plan = evidence["mof_2025_financing_plan"]
    if plan["status"] != "PLAN_NOT_REALIZED_CANONICAL_GFN_SERIES":
        errors.append("MoF 2025 financing-plan status changed")
    if plan["gross_financing_requirements_RON_billion"] != 232:
        errors.append("MoF 2025 GFN plan changed")
    if plan["budget_deficit_RON_billion"] != 135:
        errors.append("MoF 2025 budget-deficit plan changed")
    if plan["public_debt_refinancing_RON_billion"] != 97:
        errors.append("MoF 2025 refinancing plan changed")
    if plan["arithmetic_reconciles"] is not True:
        errors.append("MoF 2025 plan arithmetic must remain reconciled")

    imf = evidence["imf_gfn_framework"]
    if imf["debt_issuance_equivalent"] is not False:
        errors.append("IMF GFN may not be relabelled debt issuance")

    decomposition = review["semantic_decomposition"]
    interest = decomposition["government_interest_cost_umbrella"]
    if interest["portfolio_rate_target_may_enter_GFN_directly"] is not False:
        errors.append("portfolio rate may not enter GFN directly")
    if interest["eurostat_D41_may_be_used_as_cash_interest_without_bridge"] is not False:
        errors.append("D41 may not be used as cash interest without bridge")

    gfn = decomposition["government_financing_need_umbrella"]
    if gfn["current_boundary"] != "UNRESOLVED":
        errors.append("government-financing-need umbrella may not be resolved")
    if gfn["scalar_GFN_selected"] is not False:
        errors.append("review may not select scalar GFN")
    if gfn["exact_reference_mode_id"] is not None:
        errors.append("review may not assign exact GFN reference mode")

    accounting = review["accounting_boundary"]
    if accounting["exact_esa_identity_available"] is not True:
        errors.append("exact ESA balance identity must remain available")
    if accounting["exact_GFN_identity_available_on_current_RMD_sources"] is not False:
        errors.append("current RMD sources may not claim exact GFN identity")
    for key in (
        "cross_boundary_sum_authorized",
        "frequency_interpolation_authorized",
        "planned_GFN_may_fill_realized_GFN",
    ):
        if accounting[key] is not False:
            errors.append(f"accounting boundary may not authorize {key}")

    resolution = review["link_resolution"]
    if resolution["status"] != STATUS:
        errors.append("interest-cost/financing-need bridge status changed")
    if resolution["qualitative_sign"] != "+":
        errors.append("interest-cost/financing-need qualitative sign changed")
    if resolution["qualitative_sign_retained"] is not True:
        errors.append("qualitative positive direction must remain retained")
    if resolution["exact_integrated_equation_ready"] is not False:
        errors.append("interest-cost/financing-need link may not become equation-ready")
    if resolution["accounting_identity_ready"] is not False:
        errors.append("interest-cost/financing-need exact accounting identity may not be ready")
    if resolution["estimation_authorized"] is not False:
        errors.append("interest-cost/financing-need review may not authorize estimation")
    if resolution["current_activation_authorized"] is not False:
        errors.append("interest-cost/financing-need link may not activate")

    node_effect = review["government_financing_need_node_effect"]
    if node_effect["current_boundary_class_after_review"] != "UNRESOLVED":
        errors.append("review may not resolve government-financing-need node")
    if set(node_effect["related_reference_modes"]) != {
        "government_refinancing_need",
        "government_interest_burden",
    }:
        errors.append("government-financing-need related target set changed")
    if node_effect["exact_reference_mode_id_after_review"] is not None:
        errors.append("review may not assign financing-need reference mode")
    if node_effect["scalar_financing_need_selected"] is not False:
        errors.append("review may not select scalar financing need")
    if node_effect["canonical_GFN_reference_mode_promoted"] is not False:
        errors.append("review may not promote GFN reference mode")
    if node_effect["current_feedback_activation_authorized"] is not False:
        errors.append("review may not activate financing-need node")

    loops = review["multi_loop_effect"]
    if set(loops["affected_loops"]) != {
        "government_refinancing_interest_loop",
        "government_issuance_yield_loop",
    }:
        errors.append("affected-loop set changed")
    if loops["qualitative_topology_changed"] is not False:
        errors.append("review may not change qualitative topology")
    if loops["exact_link_equation_ready_in_either_loop"] is not False:
        errors.append("review may not make exact link ready in either loop")
    if loops["feedback_activation_authorized_in_either_loop"] is not False:
        errors.append("review may not activate either loop")

    for key, value in review["hard_rules"].items():
        if value is not True:
            errors.append(f"hard rule disabled: {key}")

    next_gate = review["next_gate"]
    if next_gate["id"] != "financing_channel_allocation_boundary_review":
        errors.append("next boundary gate changed")
    if next_gate["authorization"] != "STRUCTURAL_SOURCE_BOUNDARY_REVIEW_ONLY":
        errors.append("next boundary gate authorization changed")
    for key in (
        "may_construct_one_to_one_financing_need_to_bnr_issuance_mapping",
        "may_estimate_parameters",
        "may_activate_feedback",
        "may_change_behavioural_closure",
    ):
        if next_gate[key] is not False:
            errors.append(f"next gate may not authorize {key}")

    node = next(
        item for item in boundary["variables"]
        if item["id"] == "government_financing_need"
    )
    if node.get("interest_cost_to_financing_need_boundary_review") != REVIEW_PATH:
        errors.append("government-financing-need node lacks boundary review")
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("government-financing-need registry node may not be resolved")
    if set(node.get("related_reference_modes", [])) != {
        "government_refinancing_need",
        "government_interest_burden",
    }:
        errors.append("government-financing-need registry target set changed")
    if node.get("scalar_financing_need_selected") is not False:
        errors.append("government-financing-need registry may not select scalar")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("government-financing-need node activation changed")

    matching_links = [
        item for item in readiness["links"]
        if item["from"] == "government_interest_cost"
        and item["to"] == "government_financing_need"
    ]
    if {item["loop_id"] for item in matching_links} != {
        "government_refinancing_interest_loop",
        "government_issuance_yield_loop",
    }:
        errors.append("interest-cost/financing-need link coverage changed")
    for link in matching_links:
        if link.get("interest_cost_to_financing_need_boundary_review") != REVIEW_PATH:
            errors.append(f"{link['loop_id']}: link lacks boundary review")
        if link["readiness_status"] != (
            "STRUCTURAL_RELATION_NOT_CONTRACTED_AS_INTEGRATED_EQUATION"
        ):
            errors.append(f"{link['loop_id']}: readiness vocabulary/status changed")
        if link.get("bridge_status") != STATUS:
            errors.append(f"{link['loop_id']}: bridge status changed")
        if link["exact_integrated_equation_ready"] is not False:
            errors.append(f"{link['loop_id']}: link may not become equation-ready")
        if link["current_activation_authorized"] is not False:
            errors.append(f"{link['loop_id']}: link may not activate")

    for loop_id in (
        "government_refinancing_interest_loop",
        "government_issuance_yield_loop",
    ):
        loop = next(item for item in feedback["loops"] if item["id"] == loop_id)
        if loop.get("interest_cost_to_financing_need_boundary_review") != REVIEW_PATH:
            errors.append(f"{loop_id}: feedback loop lacks boundary review")
        if loop.get("interest_cost_to_financing_need_bridge_status") != STATUS:
            errors.append(f"{loop_id}: feedback-loop bridge status changed")
        if loop["quantitatively_active"] is not False:
            errors.append(f"{loop_id}: review may not activate loop")

    bridges = {
        item["id"]: item
        for item in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
    }
    if "interest_cost_to_financing_need" not in bridges:
        errors.append("preregistration lacks interest-cost/financing-need bridge")
    else:
        bridge = bridges["interest_cost_to_financing_need"]
        if bridge.get("status") != STATUS:
            errors.append("preregistration interest-cost/financing-need status changed")
        if bridge.get("boundary_review") != REVIEW_PATH:
            errors.append("preregistration bridge lacks boundary review")
        if bridge.get("exact_integrated_equation_ready") is not False:
            errors.append("preregistration may not make bridge equation-ready")
        if bridge.get("accounting_identity_ready") is not False:
            errors.append("preregistration may not claim exact accounting identity")
        if bridge.get("parameter_estimation_authorized") is not False:
            errors.append("preregistration may not authorize estimation")
        if bridge.get("feedback_activation_authorized") is not False:
            errors.append("preregistration may not activate bridge")

    if prereg["next_independent_bridge_task"]["id"] != (
        "financing_channel_allocation_boundary_review"
    ):
        errors.append("preregistration next independent bridge changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("interest_cost_to_financing_need_boundary_review") != REVIEW_PATH:
        errors.append("model contract lacks interest-cost/financing-need review")
    if dynamic.get("interest_cost_to_financing_need_boundary_status") != STATUS:
        errors.append("model contract interest-cost/financing-need status changed")
    if dynamic.get("government_financing_need_boundary_status") != (
        "UNRESOLVED_OBSERVED_COMPONENTS_AVAILABLE_NO_CANONICAL_GFN"
    ):
        errors.append("model contract financing-need boundary status changed")
    if set(dynamic.get("government_financing_need_related_reference_modes", [])) != {
        "government_refinancing_need",
        "government_interest_burden",
    }:
        errors.append("model contract financing-need target set changed")
    if dynamic.get("government_financing_need_scalar_selected") is not False:
        errors.append("model contract may not select scalar financing need")
    if dynamic.get("government_issuance_yield_next_independent_task") != (
        "financing_channel_allocation_boundary_review"
    ):
        errors.append("model contract next independent task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("model contract may not activate issuance-yield feedback")

    if baseline["authority"].get("interest_cost_to_financing_need_boundary_review") != REVIEW_PATH:
        errors.append("scientific baseline lacks financing-need boundary authority")

    return errors


def main() -> None:
    errors = audit_interest_cost_to_financing_need_boundary(
        load(REVIEW_PATH),
        load(BURDEN_PATH),
        load(REFINANCING_PATH),
        load(FISCAL_BOUNDARY_PATH),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/feedback_registry.json"),
        load(PREREG_PATH),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
    )
    if errors:
        raise RuntimeError(
            "Interest-cost to financing-need boundary audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(json.dumps({
        "status": "PASS",
        "bridge_status": STATUS,
        "government_financing_need_node_resolved": False,
        "related_observed_targets": [
            "government_refinancing_need",
            "government_interest_burden",
        ],
        "exact_GFN_identity_ready": False,
        "required_empirical_bridges": 5,
        "feedback_activation_authorized": False,
        "next_gate": "financing_channel_allocation_boundary_review",
    }, indent=2))


if __name__ == "__main__":
    main()
