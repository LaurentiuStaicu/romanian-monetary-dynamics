from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = "model/dynamics/yield_to_interest_cost_boundary_review_2026_09_21.json"
PREREG_PATH = "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
REPRICING_PATH = "model/calibration_validation/government_repricing_ledger_assessment.json"
EFFECTIVE_RATE_PATH = "model/dynamics/government_effective_interest_rate_reference_assessment.json"
INTEREST_BURDEN_PATH = "model/dynamics/government_interest_burden_reference_assessment.json"

EXPECTED_DECISION = (
    "DO_NOT_MAP_CONTEMPORANEOUS_ECB_10Y_RON_ONE_TO_ONE_TO_"
    "GOVERNMENT_INTEREST_COST_KEEP_PORTFOLIO_COST_AND_INTEREST_"
    "EXPENDITURE_TARGETS_DISTINCT_REPRICING_TRANSITION_UNIDENTIFIED"
)
EXPECTED_STATUS = "REVIEWED_TARGETS_AVAILABLE_REPRICING_TRANSITION_UNIDENTIFIED"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_yield_to_interest_cost_boundary(
    review: dict,
    repricing: dict,
    effective_rate: dict,
    interest_burden: dict,
    reference_modes: dict,
    boundary: dict,
    readiness: dict,
    feedback: dict,
    prereg: dict,
    model_contract: dict,
    baseline: dict,
) -> list[str]:
    errors: list[str] = []

    if review["decision"] != EXPECTED_DECISION:
        errors.append("yield-to-interest-cost boundary decision changed")

    yield_target = review["official_source_evidence"]["sovereign_yield_target"]
    if yield_target["series_key"] != "IRS.M.RO.L.L40.CI.0000.RON.N.Z":
        errors.append("preferred sovereign-yield target series changed")
    if yield_target["market_role"] != "MARGINAL_LONG_TERM_MARKET_PRICE_SIGNAL":
        errors.append("sovereign-yield market role changed")
    if yield_target["not_portfolio_average_cost"] is not True:
        errors.append("sovereign yield may not be treated as portfolio-average cost")
    if yield_target["not_interest_expenditure"] is not True:
        errors.append("sovereign yield may not be treated as interest expenditure")

    effective = review["official_source_evidence"]["government_effective_interest_rate_target"]
    if effective["reference_mode"] != "government_effective_interest_rate":
        errors.append("effective-rate target id changed")
    if effective["role"] != "OBSERVED_PORTFOLIO_COST_TARGET":
        errors.append("effective-rate target role changed")
    if effective["not_marginal_sovereign_yield"] is not True:
        errors.append("effective portfolio rate may not be relabelled marginal sovereign yield")
    if effective_rate["verdict"] != "PROMOTE_TO_OBSERVED_SERIES_AVAILABLE":
        errors.append("government effective interest-rate reference assessment changed")

    burden = review["official_source_evidence"]["government_interest_burden_target"]
    if burden["reference_mode"] != "government_interest_burden":
        errors.append("interest-burden target id changed")
    if burden["role"] != "OBSERVED_INTEREST_EXPENDITURE_TARGET":
        errors.append("interest-burden target role changed")
    if burden["not_effective_interest_rate"] is not True:
        errors.append("interest expenditure may not be relabelled effective interest rate")
    if burden["not_marginal_sovereign_yield"] is not True:
        errors.append("interest expenditure may not be relabelled marginal sovereign yield")
    if interest_burden["verdict"] != "PROMOTE_TO_OBSERVED_SERIES_AVAILABLE":
        errors.append("government interest-burden reference assessment changed")

    modes = {item["id"]: item for item in reference_modes["modes"]}
    for mode_id in ("government_effective_interest_rate", "government_interest_burden"):
        if mode_id not in modes:
            errors.append(f"missing observed reference mode: {mode_id}")
        elif modes[mode_id]["status"] != "OBSERVED_SERIES_AVAILABLE":
            errors.append(f"observed reference mode status changed: {mode_id}")
    if "sovereign_yield" in modes:
        errors.append("yield-to-interest-cost review may not canonically promote sovereign_yield")

    repricing_ev = review["official_source_evidence"]["repricing_structure"]
    if repricing_ev["status"] != "DEFERRED":
        errors.append("review repricing status changed")
    snapshot = repricing_ev["mof_risk_snapshot_2024_12_30"]
    expected_snapshot = {
        "debt_maturing_within_1y_pct": 10,
        "debt_refixing_within_1y_pct": 12,
        "average_time_to_maturity_years": 6.9,
        "average_time_to_refixing_years": 6.7,
        "local_debt_maturing_within_1y_pct": 17,
        "local_debt_refixing_within_1y_pct": 15,
        "local_average_time_to_maturity_years": 4.6,
        "local_average_time_to_refixing_years": 4.6,
    }
    if snapshot != expected_snapshot:
        errors.append("MoF maturity/refixing risk snapshot changed")

    if repricing["final_verdict"] != "DEFERRED":
        errors.append("repricing ledger may not be treated as identified")
    diagnostics = repricing["observed_ledger_diagnostics"]
    for key in (
        "rows_with_opening_outstanding_principal",
        "rows_with_realized_principal_repriced",
        "rows_with_matched_old_and_new_effective_rate",
        "rows_with_contractual_refixing_date",
        "floating_rate_instruments_with_reset_schedule",
        "synthetic_allocations",
    ):
        if diagnostics[key] != 0:
            errors.append(f"repricing diagnostic unexpectedly changed: {key}")
    if repricing["gate_results"]["gate_1_ledger_completeness"]["status"] != "FAIL":
        errors.append("repricing completeness gate changed")
    if repricing["gate_results"]["gate_4_parameter_identification"]["status"] != "FAIL_BEFORE_ESTIMATION":
        errors.append("repricing parameter-identification gate changed")
    if repricing["estimation"]["run"] is not False:
        errors.append("repricing estimator may not have run")

    refinancing = review["official_source_evidence"]["refinancing_reference"]
    if refinancing["role"] != "PORTFOLIO_TURNOVER_CONTEXT_ONLY":
        errors.append("refinancing reference role changed")
    if refinancing["not_realized_matched_repriced_principal"] is not True:
        errors.append("refinancing need may not become realized repriced principal")
    if refinancing["does_not_identify_old_new_rate_pair"] is not True:
        errors.append("refinancing need may not identify old/new rate pair")

    comparison = review["boundary_comparison"]
    for key in (
        "sovereign_yield_and_effective_portfolio_rate_same_concept",
        "sovereign_yield_and_interest_expenditure_same_concept",
        "effective_portfolio_rate_and_interest_expenditure_same_concept",
        "same_time_resolution",
        "same_sector_boundary_across_all_targets",
        "same_instrument_boundary",
        "same_information_generation_process",
        "contemporaneous_one_to_one_mapping_supported",
        "full_debt_stock_times_current_10y_yield_supported",
        "single_fixed_lag_mapping_supported",
        "regression_fit_alone_identifies_repricing_transition",
    ):
        if comparison[key] is not False:
            errors.append(f"boundary comparison may not authorize {key}")

    architecture = review["propagation_architecture"]
    if architecture["current_empirical_state"] != "TARGETS_OBSERVED_TRANSITION_UNIDENTIFIED":
        errors.append("propagation architecture empirical state changed")
    if architecture["portfolio_turnover_delay_required"] is not True:
        errors.append("portfolio-turnover delay must remain required")
    if architecture["currency_and_rate_type_structure_required"] is not True:
        errors.append("currency/rate-type structure must remain required")
    if architecture["maturity_and_refixing_may_not_be_collapsed"] is not True:
        errors.append("maturity and refixing may not be collapsed")
    if architecture["yield_curve_maturity_match_required_for_any_future_market_rate_input"] is not True:
        errors.append("future market-rate maturity matching rule changed")
    if architecture["ten_year_yield_may_not_price_all_repricing_blocks"] is not True:
        errors.append("10-year yield may not price all repricing blocks")
    if architecture["current_equation_ready"] is not False:
        errors.append("yield-to-interest-cost architecture may not be equation-ready")

    resolution = review["bridge_resolution"]
    if resolution["status"] != EXPECTED_STATUS:
        errors.append("yield-to-interest-cost bridge status changed")
    for key in (
        "direct_one_to_one_bridge_created",
        "synthetic_repricing_share_created",
        "synthetic_lag_distribution_created",
        "reference_mode_relabelled",
    ):
        if resolution[key] is not False:
            errors.append(f"boundary review may not create {key}")

    node_effect = review["government_interest_cost_node_effect"]
    if node_effect["current_boundary_class_after_review"] != "UNRESOLVED":
        errors.append("review may not resolve government_interest_cost")
    if node_effect["related_observed_targets"] != [
        "government_effective_interest_rate",
        "government_interest_burden",
    ]:
        errors.append("government-interest-cost related target set changed")
    if node_effect["exact_reference_mode_id_after_review"] is not None:
        errors.append("review may not assign exact government_interest_cost reference mode")
    if node_effect["current_feedback_activation_authorized"] is not False:
        errors.append("review may not activate government_interest_cost node")

    loop_effect = review["issuance_yield_loop_effect"]
    if loop_effect["qualitative_topology_changed"] is not False:
        errors.append("review may not change issuance-yield qualitative topology")
    if loop_effect["sovereign_yield_to_interest_cost_sign_retained"] != "+":
        errors.append("yield-to-interest-cost sign changed")
    if loop_effect["link_boundary_status"] != "TARGETS_AVAILABLE_REPRICING_TRANSITION_UNIDENTIFIED":
        errors.append("review link boundary status changed")
    for key in ("exact_integrated_equation_ready", "estimation_authorized", "current_activation_authorized"):
        if loop_effect[key] is not False:
            errors.append(f"review may not promote issuance-yield field {key}")

    refinancing_effect = review["government_refinancing_interest_loop_effect"]
    if refinancing_effect["mechanism_status_after_review"] != "DEFERRED":
        errors.append("government refinancing mechanism status changed")
    if refinancing_effect["repricing_parameter_identified"] is not False:
        errors.append("repricing parameter may not be identified")
    if refinancing_effect["current_activation_authorized"] is not False:
        errors.append("government refinancing loop may not activate")

    for key, value in review["hard_rules"].items():
        if value is not True:
            errors.append(f"hard rule disabled: {key}")

    next_gate = review["next_gate"]
    if next_gate["id"] != "interest_cost_to_financing_need_boundary_review":
        errors.append("next boundary gate changed")
    if next_gate["authorization"] != "STRUCTURAL_ACCOUNTING_BOUNDARY_REVIEW_ONLY":
        errors.append("next boundary gate authorization changed")
    for key in ("may_estimate_parameters", "may_activate_feedback", "may_change_behavioural_closure"):
        if next_gate[key] is not False:
            errors.append(f"next gate may not authorize {key}")

    node = next(item for item in boundary["variables"] if item["id"] == "government_interest_cost")
    if node.get("source_boundary_review") != REVIEW_PATH:
        errors.append("government-interest-cost node lacks boundary review")
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("government-interest-cost registry node may not be resolved")
    if node["exact_reference_mode_id"] is not None:
        errors.append("government-interest-cost node may not gain exact reference-mode id")
    if node.get("yield_to_interest_cost_bridge_status") != EXPECTED_STATUS:
        errors.append("government-interest-cost node bridge status changed")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("government-interest-cost node activation changed")

    link = next(
        item for item in readiness["links"]
        if item["loop_id"] == "government_issuance_yield_loop"
        and item["from"] == "sovereign_yield"
        and item["to"] == "government_interest_cost"
    )
    if link.get("yield_to_interest_cost_boundary_review") != REVIEW_PATH:
        errors.append("yield-to-interest-cost link lacks boundary review")
    if link["readiness_status"] != "TARGETS_AVAILABLE_REPRICING_TRANSITION_UNIDENTIFIED":
        errors.append("yield-to-interest-cost link readiness changed")
    if link["exact_integrated_equation_ready"] is not False:
        errors.append("yield-to-interest-cost link may not become equation-ready")
    if link["current_activation_authorized"] is not False:
        errors.append("yield-to-interest-cost link may not activate")

    loop = next(item for item in feedback["loops"] if item["id"] == "government_issuance_yield_loop")
    if loop.get("yield_to_interest_cost_boundary_review") != REVIEW_PATH:
        errors.append("issuance-yield loop lacks yield-to-interest-cost review")
    if loop.get("yield_to_interest_cost_status") != EXPECTED_STATUS:
        errors.append("issuance-yield loop yield-to-interest-cost status changed")
    if loop["quantitatively_active"] is not False:
        errors.append("yield-to-interest-cost review may not activate issuance-yield loop")

    bridge = next(
        item for item in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if item["id"] == "yield_to_interest_cost"
    )
    if bridge.get("status") != EXPECTED_STATUS:
        errors.append("preregistration yield-to-interest-cost status changed")
    if bridge.get("boundary_review") != REVIEW_PATH:
        errors.append("preregistration yield-to-interest-cost bridge lacks review")
    for key in (
        "direct_one_to_one_mapping_authorized",
        "synthetic_repricing_share_authorized",
        "synthetic_lag_distribution_authorized",
        "parameter_estimation_authorized",
        "feedback_activation_authorized",
    ):
        if bridge.get(key) is not False:
            errors.append(f"preregistration may not authorize {key}")
    if prereg["next_independent_bridge_task"]["id"] != "mof_realized_financing_channel_materialisation_contract":
        errors.append("preregistration next independent bridge changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("yield_to_interest_cost_boundary_review") != REVIEW_PATH:
        errors.append("model contract lacks yield-to-interest-cost review")
    if dynamic.get("yield_to_interest_cost_boundary_status") != EXPECTED_STATUS:
        errors.append("model contract yield-to-interest-cost status changed")
    if dynamic.get("government_interest_cost_canonical_reference_mode_promoted") is not False:
        errors.append("model contract may not promote generic government_interest_cost")
    if dynamic.get("government_interest_cost_preferred_portfolio_cost_target") != "government_effective_interest_rate":
        errors.append("model contract preferred portfolio-cost target changed")
    if dynamic.get("government_interest_cost_preferred_interest_expenditure_target") != "government_interest_burden":
        errors.append("model contract preferred interest-expenditure target changed")
    if dynamic.get("government_issuance_yield_next_independent_task") != "mof_realized_financing_channel_materialisation_contract":
        errors.append("model contract next independent task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("model contract may not activate issuance-yield feedback")

    if baseline["authority"].get("yield_to_interest_cost_boundary_review") != REVIEW_PATH:
        errors.append("scientific baseline lacks yield-to-interest-cost authority")

    return errors


def main() -> None:
    review = load(REVIEW_PATH)
    repricing = load(REPRICING_PATH)
    effective_rate = load(EFFECTIVE_RATE_PATH)
    interest_burden = load(INTEREST_BURDEN_PATH)
    reference_modes = load("model/dynamics/reference_modes.json")
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    readiness = load("model/dynamics/feedback_link_readiness_registry.json")
    feedback = load("model/dynamics/feedback_registry.json")
    prereg = load(PREREG_PATH)
    model_contract = load("model/registries/model_contract.json")
    baseline = load("model/registries/scientific_baseline_manifest.json")

    errors = audit_yield_to_interest_cost_boundary(
        review, repricing, effective_rate, interest_burden, reference_modes,
        boundary, readiness, feedback, prereg, model_contract, baseline
    )
    if errors:
        raise RuntimeError(
            "Yield-to-interest-cost boundary audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(json.dumps({
        "status": "PASS",
        "bridge_status": EXPECTED_STATUS,
        "sovereign_yield_target": "ECB IRS.M.RO.L.L40.CI.0000.RON.N.Z",
        "portfolio_cost_target": "government_effective_interest_rate",
        "interest_expenditure_target": "government_interest_burden",
        "repricing_transition_identified": False,
        "government_interest_cost_node_resolved": False,
        "equation_ready": False,
        "feedback_activation_authorized": False,
        "next_gate": "interest_cost_to_financing_need_boundary_review",
    }, indent=2))


if __name__ == "__main__":
    main()
