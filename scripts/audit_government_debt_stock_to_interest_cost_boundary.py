from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = "model/dynamics/government_debt_stock_to_interest_cost_boundary_review_2026_09_21.json"
PREREG_PATH = "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
STATUS = "ACCOUNTING_SCALE_FORM_KNOWN_RATE_BOUNDARY_NOT_CANONICAL"
NEXT_GATE = "government_refinancing_interest_loop_terminal_assessment"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_government_debt_stock_to_interest_cost_boundary(
    review: dict,
    debt_assessment: dict,
    debt_snapshot: dict,
    burden_assessment: dict,
    burden_snapshot: dict,
    effective_rate: dict,
    boundary: dict,
    readiness: dict,
    feedback: dict,
    prereg: dict,
    model_contract: dict,
    baseline: dict,
) -> list[str]:
    errors: list[str] = []

    if review["decision"] != (
        "DO_NOT_MAP_DEBT_STOCK_LEVEL_ONE_TO_ONE_TO_GOVERNMENT_INTEREST_COST_"
        "RETAIN_CONDITIONAL_ACCOUNTING_SCALE_FORM_ONLY_ON_MATCHED_RATE_AND_DEBT_BOUNDARY"
    ):
        errors.append("debt-stock to interest-cost decision changed")

    if debt_assessment["verdict"] != "PROMOTE_TO_OBSERVED_SERIES_AVAILABLE":
        errors.append("government debt-stock observed target status changed")
    if burden_assessment["verdict"] != "PROMOTE_TO_OBSERVED_SERIES_AVAILABLE":
        errors.append("government interest-burden observed target status changed")
    if effective_rate["verdict"] != "PROMOTE_TO_OBSERVED_SERIES_AVAILABLE":
        errors.append("government effective-rate observed target status changed")

    debt_2025_q4 = debt_snapshot["series"]["MIO_NAC"]["observations"]["2025-Q4"]
    if debt_2025_q4 != review["official_definition_evidence"]["retained_government_debt_stock"]["2025_Q4_million_RON"]:
        errors.append("retained 2025-Q4 debt-stock value changed")

    q = review["official_definition_evidence"]["retained_government_interest_burden"]["2025_quarters_million_RON"]
    expected = {
        "Q1": burden_snapshot["series"]["MIO_NAC"]["observations"]["2025-Q1"],
        "Q2": burden_snapshot["series"]["MIO_NAC"]["observations"]["2025-Q2"],
        "Q3": burden_snapshot["series"]["MIO_NAC"]["observations"]["2025-Q3"],
        "Q4": burden_snapshot["series"]["MIO_NAC"]["observations"]["2025-Q4"],
    }
    if q != expected:
        errors.append("retained 2025 quarterly D41 values changed")
    if round(sum(q.values()), 1) != review["official_definition_evidence"]["retained_government_interest_burden"]["2025_annual_sum_million_RON"]:
        errors.append("2025 annual D41 sum changed")

    diagnostic = review["official_definition_evidence"]["eurostat_apparent_cost_2025_context"]
    if diagnostic["apparent_cost_pct"] != 5.2 or diagnostic["prior_year_2024_pct"] != 4.9:
        errors.append("Eurostat apparent-cost context changed")
    if diagnostic["canonical_RMD_reference_mode_created"] is not False:
        errors.append("apparent-cost diagnostic may not become a canonical reference mode")

    comparison = review["boundary_comparison"]
    for key in (
        "debt_stock_level_and_interest_expenditure_same_concept",
        "debt_stock_level_and_effective_interest_rate_same_concept",
        "ministry_effective_rate_and_eurostat_apparent_cost_same_measure",
        "eurostat_D41_and_ministry_portfolio_rate_same_measure",
        "year_end_debt_stock_is_the_published_apparent_cost_denominator",
        "current_market_yield_is_the_apparent_cost_rate",
        "debt_stock_level_alone_determines_interest_expenditure",
        "debt_stock_level_alone_determines_portfolio_rate",
    ):
        if comparison[key] is not False:
            errors.append(f"boundary comparison may not authorize {key}")
    if comparison["same_S13_accrual_boundary_exists_for_debt_and_D41"] is not True:
        errors.append("same-boundary S13 debt/D41 relation changed")

    scale = review["accounting_scale_form"]
    if scale["status"] != "DEFINITIONAL_RATIO_AVAILABLE_AS_BOUNDARY_DIAGNOSTIC":
        errors.append("accounting scale-form status changed")
    for key in (
        "current_RMD_exact_integrated_equation_ready",
        "exact_average_debt_denominator_materialised_in_RMD",
        "eurostat_apparent_cost_series_materialised_as_RMD_reference_mode",
        "generic_interest_cost_node_narrowed_to_D41",
        "portfolio_rate_endogenized",
    ):
        if scale[key] is not False:
            errors.append(f"accounting scale form may not promote {key}")

    bridge = review["bridge_resolution"]
    if bridge["status"] != STATUS:
        errors.append("debt-stock to interest-cost bridge status changed")
    if bridge["causal_role"] != "ACCOUNTING_SCALE_CONDITIONAL_ON_RATE_AND_DEBT_BOUNDARY":
        errors.append("debt-stock to interest-cost causal role changed")
    for key in (
        "direct_debt_level_to_interest_cost_mapping_authorized",
        "year_end_debt_times_rate_identity_authorized",
        "ministry_effective_rate_times_S13_debt_identity_authorized",
        "current_market_yield_times_debt_identity_authorized",
        "synthetic_average_debt_authorized",
        "synthetic_interest_rate_authorized",
        "parameter_estimation_authorized",
        "exact_integrated_equation_ready",
        "feedback_activation_authorized",
    ):
        if bridge[key] is not False:
            errors.append(f"debt-stock bridge may not authorize {key}")

    for key, value in review["hard_rules"].items():
        if value is not True:
            errors.append(f"hard rule disabled: {key}")

    effect = review["scientific_effect"]
    if effect["debt_stock_to_interest_cost_boundary_strengthened"] is not True:
        errors.append("boundary-strengthening effect changed")
    for key, value in effect.items():
        if key != "debt_stock_to_interest_cost_boundary_strengthened" and value is not False:
            errors.append(f"review may not promote {key}")

    debt = next(x for x in boundary["variables"] if x["id"] == "government_debt_stock")
    cost = next(x for x in boundary["variables"] if x["id"] == "government_interest_cost")
    for node in (debt, cost):
        if node.get("government_debt_stock_to_interest_cost_boundary_review") != REVIEW_PATH:
            errors.append(f"{node['id']}: debt-stock/interest-cost review missing")
        if node.get("debt_stock_to_interest_cost_status") != STATUS:
            errors.append(f"{node['id']}: debt-stock/interest-cost status changed")
        if node["current_boundary_class"] != "UNRESOLVED":
            errors.append(f"{node['id']}: review may not resolve node")
        if node["current_feedback_activation_authorized"] is not False:
            errors.append(f"{node['id']}: review may not activate node")

    link = next(
        x for x in readiness["links"]
        if x["loop_id"] == "government_refinancing_interest_loop"
        and x["from"] == "government_debt_stock"
        and x["to"] == "government_interest_cost"
    )
    if link["readiness_status"] != STATUS:
        errors.append("feedback-link debt-stock/interest-cost status changed")
    if link["causal_role"] != "ACCOUNTING_SCALE_CONDITIONAL_ON_RATE_AND_DEBT_BOUNDARY":
        errors.append("feedback-link debt-stock/interest-cost causal role changed")
    if link.get("government_debt_stock_to_interest_cost_boundary_review") != REVIEW_PATH:
        errors.append("feedback-link review pointer missing")
    if link["exact_integrated_equation_ready"] is not False or link["current_activation_authorized"] is not False:
        errors.append("debt-stock/interest-cost feedback link may not be exact-ready or active")

    loop = next(x for x in feedback["loops"] if x["id"] == "government_refinancing_interest_loop")
    if loop.get("government_debt_stock_to_interest_cost_boundary_review") != REVIEW_PATH:
        errors.append("refinancing loop review pointer missing")
    if loop.get("debt_stock_to_interest_cost_status") != STATUS:
        errors.append("refinancing loop debt-stock/interest-cost status changed")
    if loop.get("debt_stock_to_interest_cost_equation_ready") is not False:
        errors.append("refinancing loop debt-stock/interest-cost equation may not be ready")
    if loop["quantitatively_active"] is not False:
        errors.append("review may not activate refinancing loop")

    if prereg.get("government_debt_stock_to_interest_cost_boundary_review") != REVIEW_PATH:
        errors.append("preregistration review pointer missing")
    if prereg.get("government_debt_stock_to_interest_cost_boundary_status") != STATUS:
        errors.append("preregistration debt-stock/interest-cost status changed")
    next_task = prereg["next_independent_bridge_task"]
    if next_task["id"] != NEXT_GATE:
        errors.append("preregistration next independent task changed")
    if next_task["authorization"] != "STRUCTURAL_TERMINAL_ASSESSMENT_ONLY":
        errors.append("next independent task authorization changed")
    for key in ("may_estimate_parameters","may_activate_feedback","may_change_behavioural_closure","may_relax_existing_gates"):
        if next_task[key] is not False:
            errors.append(f"next independent task may not authorize {key}")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("government_debt_stock_to_interest_cost_boundary_review") != REVIEW_PATH:
        errors.append("model contract review pointer missing")
    if dynamic.get("government_debt_stock_to_interest_cost_boundary_status") != STATUS:
        errors.append("model contract debt-stock/interest-cost status changed")
    if dynamic.get("government_debt_stock_to_interest_cost_equation_ready") is not False:
        errors.append("model contract may not mark debt-stock/interest-cost equation-ready")
    if dynamic.get("government_issuance_yield_next_independent_task") != NEXT_GATE:
        errors.append("model contract next independent task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("model contract may not activate government feedback")

    if baseline["authority"].get("government_debt_stock_to_interest_cost_boundary_review") != REVIEW_PATH:
        errors.append("scientific baseline lacks debt-stock/interest-cost authority")

    return errors


def main() -> None:
    errors = audit_government_debt_stock_to_interest_cost_boundary(
        load(REVIEW_PATH),
        load("model/dynamics/government_debt_stock_reference_assessment.json"),
        load("model/dynamics/government_debt_stock_reference_snapshot.json"),
        load("model/dynamics/government_interest_burden_reference_assessment.json"),
        load("model/dynamics/government_interest_burden_reference_snapshot.json"),
        load("model/dynamics/government_effective_interest_rate_reference_assessment.json"),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/feedback_registry.json"),
        load(PREREG_PATH),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
    )
    if errors:
        raise RuntimeError(
            "Government debt-stock to interest-cost boundary audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(json.dumps({
        "status":"PASS",
        "bridge_status":STATUS,
        "direct_debt_level_to_interest_cost":False,
        "apparent_cost_reference_mode_added":False,
        "exact_integrated_equation_ready":False,
        "feedback_activation_authorized":False,
        "next_gate":NEXT_GATE,
    }, indent=2))


if __name__ == "__main__":
    main()
