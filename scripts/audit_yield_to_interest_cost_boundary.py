from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = "model/dynamics/yield_to_interest_cost_boundary_review_2026_09_21.json"
EFFECTIVE_ASSESSMENT_PATH = "model/dynamics/government_effective_interest_rate_reference_assessment.json"
BURDEN_ASSESSMENT_PATH = "model/dynamics/government_interest_burden_reference_assessment.json"
REPRICING_ASSESSMENT_PATH = "model/calibration_validation/government_repricing_ledger_assessment.json"
PREREG_PATH = "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
STATUS = "REVIEWED_NO_CONTEMPORANEOUS_ONE_TO_ONE_MAPPING_REPRICING_BRIDGE_DEFERRED"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_yield_to_interest_cost_boundary(
    review: dict,
    effective: dict,
    burden: dict,
    repricing: dict,
    mechanisms: dict,
    delays: dict,
    boundary: dict,
    readiness: dict,
    prereg: dict,
    model_contract: dict,
    baseline: dict,
) -> list[str]:
    errors: list[str] = []

    if review["decision"] != (
        "DO_NOT_MAP_CONTEMPORANEOUS_SOVEREIGN_YIELD_ONE_TO_ONE_TO_"
        "GOVERNMENT_INTEREST_COST_KEEP_PORTFOLIO_RATE_AND_INTEREST_"
        "EXPENDITURE_TARGETS_DISTINCT_REPRICING_BRIDGE_DEFERRED"
    ):
        errors.append("yield-to-interest-cost boundary decision changed")

    evidence = review["official_source_evidence"]
    sovereign = evidence["sovereign_yield_target"]
    if sovereign["series_key"] != "IRS.M.RO.L.L40.CI.0000.RON.N.Z":
        errors.append("preferred sovereign-yield target changed")
    if sovereign["direct_effective_portfolio_cost_equivalent"] is not False:
        errors.append("ECB 10-year yield may not equal portfolio effective cost")

    mof = evidence["mof_portfolio_effective_rate"]
    if mof["role"] != "PREFERRED_OBSERVED_PORTFOLIO_RATE_TARGET":
        errors.append("MoF portfolio-rate role changed")
    if effective["verdict"] != "PROMOTE_TO_OBSERVED_SERIES_AVAILABLE":
        errors.append("MoF effective-rate reference is no longer observed")
    if effective["reference_mode"] != "government_effective_interest_rate":
        errors.append("MoF effective-rate reference id changed")

    eurostat = evidence["eurostat_interest_expenditure"]
    if eurostat["role"] != "PREFERRED_OBSERVED_INTEREST_EXPENDITURE_TARGET":
        errors.append("Eurostat interest-expenditure role changed")
    if burden["verdict"] != "PROMOTE_TO_OBSERVED_SERIES_AVAILABLE":
        errors.append("Eurostat interest-burden reference is no longer observed")
    if burden["reference_mode"] != "government_interest_burden":
        errors.append("Eurostat interest-burden reference id changed")

    apparent = evidence["eurostat_apparent_cost_diagnostic"]
    if apparent["observed_2025_romania_pct"] != 5.2:
        errors.append("Eurostat 2025 apparent-cost diagnostic changed")
    if apparent["boundary_match_to_mof_direct_government_debt_portfolio"] is not False:
        errors.append("Eurostat apparent cost may not be treated as MoF-boundary match")
    if apparent["one_to_one_substitute_for_mof_portfolio_rate"] is not False:
        errors.append("Eurostat apparent cost may not substitute for MoF portfolio rate")

    ledger = evidence["repricing_ledger"]
    if ledger["current_status"] != "DEFERRED":
        errors.append("repricing mechanism review status changed")
    if ledger["gate_1_ledger_completeness"] != "FAIL":
        errors.append("repricing ledger completeness gate changed")
    if ledger["gate_4_parameter_identification"] != "FAIL_BEFORE_ESTIMATION":
        errors.append("repricing parameter-identification gate changed")
    if ledger["observed_opening_principal_rows"] != 0:
        errors.append("repricing review may not claim observed opening-principal rows")
    if ledger["observed_realized_repriced_principal_rows"] != 0:
        errors.append("repricing review may not claim observed repriced-principal rows")
    if ledger["matched_old_new_rate_rows"] != 0:
        errors.append("repricing review may not claim matched old/new rates")
    if repricing["gate_results"]["gate_1_ledger_completeness"]["status"] != "FAIL":
        errors.append("retained repricing assessment completeness status changed")
    if repricing["gate_results"]["gate_4_parameter_identification"]["status"] != "FAIL_BEFORE_ESTIMATION":
        errors.append("retained repricing assessment identification status changed")

    comparison = review["boundary_comparison"]
    for section in ("sovereign_yield_vs_mof_portfolio_rate", "sovereign_yield_vs_eurostat_D41"):
        if comparison[section]["one_to_one_mapping_supported"] is not False:
            errors.append(f"{section}: one-to-one mapping may not be supported")
    if comparison["mof_portfolio_rate_vs_eurostat_apparent_cost"]["substitution_supported"] is not False:
        errors.append("MoF rate / Eurostat apparent-cost substitution may not be supported")

    propagation = review["propagation_architecture"]
    if propagation["direct_sovereign_yield_to_government_interest_cost_equation_authorized"] is not False:
        errors.append("direct sovereign-yield/interest-cost equation may not be authorized")
    for key in (
        "ecb_10y_may_substitute_for_matched_new_or_reset_rate",
        "average_maturity_may_substitute_for_repricing_share",
        "average_time_to_refixing_may_substitute_for_repricing_share",
        "maturity_share_may_substitute_for_refixing_share",
        "scalar_first_order_delay_tau_identified",
    ):
        if propagation[key] is not False:
            errors.append(f"propagation architecture may not authorize {key}")

    node_effect = review["government_interest_cost_node_resolution"]
    if node_effect["current_boundary_class_after_review"] != "UNRESOLVED":
        errors.append("review may not resolve government-interest-cost node")
    if node_effect["exact_reference_mode_id_after_review"] is not None:
        errors.append("review may not assign exact interest-cost reference mode")
    if node_effect["scalar_interest_cost_selected"] is not False:
        errors.append("review may not select scalar interest cost")
    if node_effect["current_feedback_activation_authorized"] is not False:
        errors.append("review may not activate interest-cost node")

    link_effect = review["yield_to_interest_cost_link_resolution"]
    if link_effect["status"] != STATUS:
        errors.append("yield-to-interest-cost bridge status changed")
    if link_effect["exact_integrated_equation_ready"] is not False:
        errors.append("yield-to-interest-cost link may not become equation-ready")
    if link_effect["estimation_authorized"] is not False:
        errors.append("yield-to-interest-cost link may not authorize estimation")
    if link_effect["current_activation_authorized"] is not False:
        errors.append("yield-to-interest-cost link may not activate")
    if link_effect["mechanism_status_after_review"] != "UNCHANGED_DEFERRED":
        errors.append("refinancing mechanism disposition changed")

    mechanism = next(
        item for item in mechanisms["mechanisms"]
        if item["id"] == "government_refinancing_effective_rate"
    )
    if mechanism["classification"] != "DEFERRED":
        errors.append("government refinancing mechanism may not leave DEFERRED")
    if mechanism["parameters"][0]["status"] != "UNIDENTIFIED_NO_DEFAULT":
        errors.append("repricing-share parameter status changed")

    delay_effect = review["delay_effect"]
    if delay_effect["current_tau"] != "TBD":
        errors.append("debt-service delay tau may not be selected")
    if delay_effect["active"] is not False:
        errors.append("debt-service delay may not activate")
    delay = next(item for item in delays["delays"] if item["id"] == "debt_service_maturity_delay")
    if delay["current_tau"] != "TBD" or delay["active"] is not False:
        errors.append("registered debt-service delay activation changed")
    if delay["scalar_tau_activation_ready"] is not False:
        errors.append("registered debt-service delay may not become activation-ready")

    for key, value in review["hard_rules"].items():
        if value is not True:
            errors.append(f"hard rule disabled: {key}")

    next_gate = review["next_gate"]
    if next_gate["id"] != "interest_cost_to_financing_need_boundary_review":
        errors.append("next boundary gate changed")
    if next_gate["authorization"] != "STRUCTURAL_ACCOUNTING_SOURCE_BOUNDARY_REVIEW_ONLY":
        errors.append("next boundary gate authorization changed")
    for key in ("may_estimate_parameters", "may_activate_feedback", "may_change_behavioural_closure"):
        if next_gate[key] is not False:
            errors.append(f"next gate may not authorize {key}")

    node = next(item for item in boundary["variables"] if item["id"] == "government_interest_cost")
    if node.get("yield_to_interest_cost_boundary_review") != REVIEW_PATH:
        errors.append("government-interest-cost node lacks boundary review")
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("government-interest-cost registry node may not be resolved")
    if node.get("preferred_portfolio_rate_target") != "government_effective_interest_rate":
        errors.append("preferred portfolio-rate target changed")
    if node.get("preferred_interest_expenditure_target") != "government_interest_burden":
        errors.append("preferred interest-expenditure target changed")
    if node.get("scalar_interest_cost_selected") is not False:
        errors.append("government-interest-cost registry may not select scalar")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("government-interest-cost node activation changed")

    link = next(
        item for item in readiness["links"]
        if item["loop_id"] == "government_issuance_yield_loop"
        and item["from"] == "sovereign_yield"
        and item["to"] == "government_interest_cost"
    )
    if link.get("yield_to_interest_cost_boundary_review") != REVIEW_PATH:
        errors.append("yield-to-interest-cost link lacks review")
    if link["readiness_status"] != "OBSERVED_TARGETS_AVAILABLE_REPRICING_BRIDGE_DEFERRED":
        errors.append("yield-to-interest-cost link readiness changed")
    if link.get("bridge_status") != STATUS:
        errors.append("yield-to-interest-cost registry bridge status changed")
    if link["exact_integrated_equation_ready"] is not False:
        errors.append("yield-to-interest-cost registry link may not become equation-ready")
    if link["current_activation_authorized"] is not False:
        errors.append("yield-to-interest-cost registry link may not activate")

    bridge = next(
        item for item in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if item["id"] == "yield_to_interest_cost"
    )
    if bridge.get("status") != STATUS:
        errors.append("preregistration yield-to-interest-cost bridge status changed")
    if bridge.get("boundary_review") != REVIEW_PATH:
        errors.append("preregistration yield-to-interest-cost bridge lacks review")
    if bridge.get("required_for_empirical_chain_after_review") is not True:
        errors.append("yield-to-interest-cost bridge must remain required")
    if bridge.get("exact_integrated_equation_ready") is not False:
        errors.append("preregistration may not make yield-to-interest-cost equation-ready")
    if bridge.get("parameter_estimation_authorized") is not False:
        errors.append("preregistration may not authorize repricing estimation")
    if bridge.get("feedback_activation_authorized") is not False:
        errors.append("preregistration may not activate yield-to-interest-cost bridge")
    if prereg["next_independent_bridge_task"]["id"] != "interest_cost_to_financing_need_boundary_review":
        errors.append("preregistration next independent bridge changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("yield_to_interest_cost_boundary_review") != REVIEW_PATH:
        errors.append("model contract lacks yield-to-interest-cost boundary review")
    if dynamic.get("yield_to_interest_cost_boundary_status") != STATUS:
        errors.append("model contract yield-to-interest-cost status changed")
    if dynamic.get("government_interest_cost_boundary_status") != (
        "UNRESOLVED_DISTINCT_PORTFOLIO_RATE_AND_INTEREST_EXPENDITURE_TARGETS"
    ):
        errors.append("model contract government-interest-cost boundary status changed")
    if dynamic.get("government_interest_cost_preferred_portfolio_rate_target") != (
        "government_effective_interest_rate"
    ):
        errors.append("model contract preferred portfolio-rate target changed")
    if dynamic.get("government_interest_cost_preferred_expenditure_target") != (
        "government_interest_burden"
    ):
        errors.append("model contract preferred expenditure target changed")
    if dynamic.get("government_interest_cost_scalar_selected") is not False:
        errors.append("model contract may not select scalar interest cost")
    if dynamic.get("government_issuance_yield_next_independent_task") != (
        "interest_cost_to_financing_need_boundary_review"
    ):
        errors.append("model contract next independent task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("model contract may not activate issuance-yield feedback")

    if baseline["authority"].get("yield_to_interest_cost_boundary_review") != REVIEW_PATH:
        errors.append("scientific baseline lacks yield-to-interest-cost authority")

    return errors


def main() -> None:
    errors = audit_yield_to_interest_cost_boundary(
        load(REVIEW_PATH),
        load(EFFECTIVE_ASSESSMENT_PATH),
        load(BURDEN_ASSESSMENT_PATH),
        load(REPRICING_ASSESSMENT_PATH),
        load("model/empirical_dynamics/mechanism_registry.json"),
        load("model/dynamics/delay_evidence_registry.json"),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load(PREREG_PATH),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
    )
    if errors:
        raise RuntimeError(
            "Yield-to-interest-cost boundary audit failed:\n- " + "\n- ".join(errors)
        )

    print(json.dumps({
        "status": "PASS",
        "yield_to_interest_cost_bridge": STATUS,
        "government_interest_cost_node_resolved": False,
        "portfolio_rate_target": "government_effective_interest_rate",
        "interest_expenditure_target": "government_interest_burden",
        "repricing_parameter_identified": False,
        "delay_tau_identified": False,
        "feedback_activation_authorized": False,
        "next_gate": "interest_cost_to_financing_need_boundary_review",
    }, indent=2))


if __name__ == "__main__":
    main()
