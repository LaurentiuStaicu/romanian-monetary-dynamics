from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = (
    "model/dynamics/"
    "primary_yield_to_sovereign_yield_boundary_review_2026_09_20.json"
)
BNR_PATH = "model/dynamics/government_issuance_bnr_primary_market_yield_pilot_2025.json"
ECB_PATH = "model/calibration_validation/sovereign_yield_source_boundary_review.json"
PREREG_PATH = "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_primary_yield_to_sovereign_yield_boundary(
    review: dict,
    bnr: dict,
    ecb: dict,
    boundary: dict,
    readiness: dict,
    prereg: dict,
    model_contract: dict,
    baseline: dict,
) -> list[str]:
    errors: list[str] = []

    if review["decision"] != (
        "DO_NOT_BRIDGE_BNR_PRIMARY_MARKET_RATES_ONE_TO_ONE_TO_SOVEREIGN_YIELD_"
        "USE_ECB_10Y_RON_AS_PREFERRED_OBSERVED_LONG_TERM_TARGET_BOUNDARY"
    ):
        errors.append("primary-yield boundary decision changed")

    bnr_ev = review["official_source_evidence"]["bnr_primary_market"]
    if bnr_ev["market_boundary"] != "DOMESTIC_PRIMARY_MARKET_NEW_AND_ROLL_OVER_ISSUES":
        errors.append("BNR market boundary changed")
    if bnr_ev["generic_sovereign_yield_equivalent"] is not False:
        errors.append("BNR primary rates may not become generic sovereign yield")
    if bnr["semantics"]["generic_sovereign_yield_equivalent"] is not False:
        errors.append("retained BNR pilot semantic guard changed")
    if bnr["semantics"]["secondary_market_yield_equivalent"] is not False:
        errors.append("BNR primary rates may not become secondary-market yield")

    ecb_ev = review["official_source_evidence"]["ecb_long_term_target"]
    if ecb_ev["series_key"] != "IRS.M.RO.L.L40.CI.0000.RON.N.Z":
        errors.append("ECB preferred target series changed")
    if ecb["observed_yield_source"]["romania_series_key"] != ecb_ev["series_key"]:
        errors.append("review/ECB source-boundary series mismatch")
    methodology = ecb_ev["methodology"]
    if methodology["issuer"] != "central government":
        errors.append("ECB long-term issuer boundary changed")
    if methodology["maturity"] != "as close as possible to ten years residual maturity":
        errors.append("ECB long-term maturity boundary changed")
    if methodology["yield_formula"] != "redemption yield":
        errors.append("ECB yield formula changed")
    if methodology["multi_bond_aggregation"] != (
        "simple average of yields when more than one bond is in the sample"
    ):
        errors.append("ECB representative-yield aggregation changed")
    if ecb_ev["canonical_reference_mode_promoted_by_this_review"] is not False:
        errors.append("boundary review may not canonically promote ECB target")

    comparison = review["boundary_comparison"]
    for key in (
        "same_market_boundary",
        "same_maturity_boundary",
        "same_provider_aggregation_semantics",
        "same_instrument_universe",
        "same_information_generation_process",
        "direct_one_to_one_mapping_supported",
        "post_hoc_cross_instrument_average_supported",
        "regression_based_bridge_authorized",
    ):
        if comparison[key] is not False:
            errors.append(f"boundary comparison may not authorize {key}")

    resolution = review["bridge_resolution"]
    if resolution["status"] != "REVIEWED_NO_ONE_TO_ONE_BRIDGE_DIAGNOSTIC_ONLY":
        errors.append("primary-yield bridge resolution changed")
    if resolution["bnr_role_after_review"] != "DESCRIPTIVE_PRIMARY_MARKET_PRICING_DIAGNOSTIC":
        errors.append("BNR diagnostic role changed")
    if resolution["ecb_role_after_review"] != "PREFERRED_OBSERVED_LONG_TERM_TARGET_BOUNDARY":
        errors.append("ECB target role changed")
    if resolution["synthetic_scalar_created"] is not False:
        errors.append("review may not create synthetic primary-yield scalar")
    if resolution["one_to_one_bridge_created"] is not False:
        errors.append("review may not create one-to-one primary-yield bridge")

    chain = review["empirical_chain_effect"]
    if chain["reviewed_candidate_chain"] != [
        "government_financing_need",
        "domestic_primary_market_government_securities_gross_issuance",
        "government_securities_supply_pressure",
        "sovereign_yield",
        "government_interest_cost",
    ]:
        errors.append("reviewed empirical chain changed")
    if chain["qualitative_feedback_topology_changed"] is not False:
        errors.append("boundary review may not change qualitative topology")

    node_effect = review["sovereign_yield_node_effect"]
    if node_effect["current_boundary_class_after_review"] != "UNRESOLVED":
        errors.append("review may not resolve sovereign-yield node")
    if node_effect["preferred_observed_target_boundary_available"] is not True:
        errors.append("preferred sovereign-yield target must remain available")
    if node_effect["exact_reference_mode_id_after_review"] is not None:
        errors.append("review may not assign canonical reference-mode id")
    if node_effect["current_feedback_activation_authorized"] is not False:
        errors.append("review may not activate sovereign-yield node")

    link_effect = review["supply_pressure_to_yield_link_effect"]
    if link_effect["exact_target_boundary_available"] is not True:
        errors.append("supply-pressure/yield target boundary changed")
    for key in (
        "supply_pressure_observable_fully_resolved",
        "exact_integrated_equation_ready",
        "estimation_authorized",
        "current_activation_authorized",
    ):
        if link_effect[key] is not False:
            errors.append(f"review may not promote link field {key}")

    for key, value in review["hard_rules"].items():
        if value is not True:
            errors.append(f"hard rule disabled: {key}")

    next_gate = review["next_gate"]
    if next_gate["id"] != "yield_to_interest_cost_boundary_review":
        errors.append("next boundary gate changed")
    if next_gate["authorization"] != "STRUCTURAL_SOURCE_BOUNDARY_REVIEW_ONLY":
        errors.append("next boundary gate authorization changed")
    for key in ("may_estimate_parameters", "may_activate_feedback", "may_change_behavioural_closure"):
        if next_gate[key] is not False:
            errors.append(f"next gate may not authorize {key}")

    node = next(item for item in boundary["variables"] if item["id"] == "sovereign_yield")
    if node.get("source_boundary_review") != REVIEW_PATH:
        errors.append("sovereign-yield node lacks boundary review")
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("sovereign-yield registry node may not be resolved")
    if node["exact_reference_mode_id"] is not None:
        errors.append("sovereign-yield node may not gain reference-mode id")
    if node.get("primary_market_rate_bridge_status") != (
        "REVIEWED_NO_ONE_TO_ONE_BRIDGE_DIAGNOSTIC_ONLY"
    ):
        errors.append("sovereign-yield node primary-rate bridge status changed")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("sovereign-yield node activation changed")

    link = next(
        item for item in readiness["links"]
        if item["loop_id"] == "government_issuance_yield_loop"
        and item["from"] == "government_securities_supply_pressure"
        and item["to"] == "sovereign_yield"
    )
    if link.get("primary_yield_to_sovereign_yield_boundary_review") != REVIEW_PATH:
        errors.append("supply-pressure/yield link lacks review")
    if link["readiness_status"] != "TARGET_BOUNDARY_AVAILABLE_LINK_FORM_UNRESOLVED":
        errors.append("supply-pressure/yield readiness changed")
    if link["exact_integrated_equation_ready"] is not False:
        errors.append("supply-pressure/yield link may not become equation-ready")
    if link["current_activation_authorized"] is not False:
        errors.append("supply-pressure/yield link may not activate")

    bridge = next(
        item for item in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if item["id"] == "primary_yield_to_sovereign_yield"
    )
    if bridge.get("status") != "REVIEWED_NO_ONE_TO_ONE_BRIDGE_DIAGNOSTIC_ONLY":
        errors.append("preregistration primary-yield bridge status changed")
    if bridge.get("boundary_review") != REVIEW_PATH:
        errors.append("preregistration primary-yield bridge lacks review")
    if bridge.get("required_for_empirical_chain_after_review") is not False:
        errors.append("primary-yield bridge may not remain required intermediate")
    if bridge.get("synthetic_aggregation_authorized") is not False:
        errors.append("preregistration may not authorize synthetic yield aggregation")
    if bridge.get("reference_mode_promotion_authorized") is not False:
        errors.append("preregistration may not authorize reference-mode promotion")
    if prereg["empirical_boundary_status"]["candidate_chain"] != chain["reviewed_candidate_chain"]:
        errors.append("preregistration empirical chain differs from reviewed chain")
    if prereg["next_independent_bridge_task"]["id"] != "interest_cost_to_financing_need_boundary_review":
        errors.append("preregistration current next independent bridge changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("primary_yield_to_sovereign_yield_boundary_review") != REVIEW_PATH:
        errors.append("model contract lacks primary-yield boundary review")
    if dynamic.get("primary_yield_to_sovereign_yield_boundary_status") != (
        "REVIEWED_NO_ONE_TO_ONE_BRIDGE_DIAGNOSTIC_ONLY_ECB_10Y_RON_"
        "PREFERRED_TARGET_BOUNDARY"
    ):
        errors.append("model contract primary-yield boundary status changed")
    if dynamic.get("sovereign_yield_canonical_reference_mode_promoted") is not False:
        errors.append("model contract may not promote sovereign-yield reference mode")
    if dynamic.get("government_issuance_yield_next_independent_task") != (
        "interest_cost_to_financing_need_boundary_review"
    ):
        errors.append("model contract current next independent task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("model contract may not activate issuance-yield feedback")

    if baseline["authority"].get("primary_yield_to_sovereign_yield_boundary_review") != REVIEW_PATH:
        errors.append("scientific baseline lacks boundary-review authority")

    return errors


def main() -> None:
    review = load(REVIEW_PATH)
    bnr = load(BNR_PATH)
    ecb = load(ECB_PATH)
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    readiness = load("model/dynamics/feedback_link_readiness_registry.json")
    prereg = load(PREREG_PATH)
    model_contract = load("model/registries/model_contract.json")
    baseline = load("model/registries/scientific_baseline_manifest.json")

    errors = audit_primary_yield_to_sovereign_yield_boundary(
        review, bnr, ecb, boundary, readiness, prereg, model_contract, baseline
    )
    if errors:
        raise RuntimeError(
            "Primary-yield to sovereign-yield boundary audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(json.dumps({
        "status": "PASS",
        "primary_market_rate_bridge": "DIAGNOSTIC_ONLY_NO_ONE_TO_ONE_MAPPING",
        "preferred_sovereign_yield_target": "ECB IRS.M.RO.L.L40.CI.0000.RON.N.Z",
        "sovereign_yield_node_resolved": False,
        "reference_mode_promoted": False,
        "equation_ready": False,
        "estimation_authorized": False,
        "feedback_activation_authorized": False,
        "next_gate": "yield_to_interest_cost_boundary_review",
    }, indent=2))


if __name__ == "__main__":
    main()
