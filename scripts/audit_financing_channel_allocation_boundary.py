from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = "model/dynamics/financing_channel_allocation_boundary_review_2026_09_21.json"
PREREG_PATH = "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
STATUS = "MULTI_CHANNEL_STRUCTURE_CONFIRMED_ALLOCATION_VECTOR_NOT_IDENTIFIED"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_financing_channel_allocation_boundary(
    review: dict,
    bnr: dict,
    source_review: dict,
    boundary: dict,
    readiness: dict,
    feedback: dict,
    prereg: dict,
    model_contract: dict,
    baseline: dict,
) -> list[str]:
    errors: list[str] = []

    if review["decision"] != (
        "DO_NOT_MAP_TOTAL_GOVERNMENT_FINANCING_NEED_ONE_TO_ONE_TO_BNR_"
        "DOMESTIC_PRIMARY_ISSUANCE_USE_MULTI_CHANNEL_FINANCING_VECTOR_"
        "ALLOCATION_NOT_IDENTIFIED"
    ):
        errors.append("financing-channel boundary decision changed")

    programme = review["official_source_evidence"]["ministry_indicative_financing_programme_2025"]
    numeric = programme["numeric_context"]
    if numeric["gross_financing_need_bn_RON"] != 232.0:
        errors.append("2025 gross financing need context changed")
    if numeric["projected_budget_deficit_bn_RON"] != 135.0:
        errors.append("2025 projected deficit context changed")
    if numeric["public_debt_refinancing_bn_RON"] != 97.0:
        errors.append("2025 refinancing context changed")
    if numeric["indicative_domestic_market_borrowing_bn_RON_range"] != [145.0, 150.0]:
        errors.append("domestic financing envelope changed")
    if numeric["deficit_financing_internal_share_pct"] != 45.0:
        errors.append("internal deficit-financing share changed")
    if numeric["deficit_financing_external_share_pct"] != 55.0:
        errors.append("external deficit-financing share changed")
    if "applies to financing the projected budget deficit" not in programme["scope_guard"]:
        errors.append("45/55 scope guard changed")

    april = review["official_source_evidence"]["ministry_investor_presentation_april_2025"]
    if april["findings"]["retail_bonds_issued_through_2025_04_30_bn_RON"] != 19.5:
        errors.append("April retail-bond evidence changed")
    if april["findings"]["financing_needs_covered_as_of_2025_04_30_pct_approx"] != 44.0:
        errors.append("April GFN-coverage evidence changed")

    retained = review["official_source_evidence"]["retained_bnr_domestic_primary_boundary"]
    if retained["full_2025_RON_total_million"] != 98905.8:
        errors.append("retained BNR RON total changed")
    if retained["full_2025_EUR_total_million"] != 1856.1:
        errors.append("retained BNR EUR total changed")
    if retained["total_government_borrowing_equivalent"] is not False:
        errors.append("BNR primary issuance may not become total government borrowing")
    if retained["government_financing_need_equivalent"] is not False:
        errors.append("BNR primary issuance may not become government financing need")

    if bnr["target_candidate_id"] != "domestic_primary_market_government_securities_gross_issuance":
        errors.append("BNR pilot candidate boundary changed")
    if source_review["verdict"] != (
        "SOURCE_FAMILIES_FOUND_GENERIC_NODE_SEMANTICALLY_OVERLOADED_"
        "BOUNDARY_REMAINS_UNRESOLVED"
    ):
        errors.append("government-debt issuance source-boundary verdict changed")
    if source_review["scientific_decision"]["current_boundary_class"] != "UNRESOLVED":
        errors.append("government-debt issuance source boundary may not be resolved")

    channel_ids = {
        item["channel_id"]
        for item in review["channel_architecture"]["market_financing_channels"]
    }
    if channel_ids != {
        "domestic_interbank_government_securities",
        "domestic_retail_government_securities",
        "domestic_other_or_private_placements",
        "external_market_securities_and_private_placements",
    }:
        errors.append("market financing-channel vector changed")

    official_ids = {
        item["channel_id"]
        for item in review["channel_architecture"]["official_sector_and_loan_channels"]
    }
    if official_ids != {"RRF_or_EC_loan_disbursements", "IFI_and_other_loans"}:
        errors.append("official-sector/loan channel vector changed")

    comparison = review["boundary_comparison"]
    for key in (
        "government_financing_need_equals_BNR_domestic_primary_issuance",
        "BNR_domestic_primary_issuance_covers_retail",
        "BNR_domestic_primary_issuance_covers_external_Eurobonds",
        "BNR_domestic_primary_issuance_covers_RRF_or_IFI_loans",
        "all_financing_channels_share_same_currency",
        "all_financing_channels_share_same_instrument_type",
        "all_financing_channels_are_observed_at_same_frequency",
        "all_financing_channels_have_frozen_monthly_realized_source_vintages",
        "residual_channel_can_be_inferred_as_GFN_minus_BNR_issuance",
        "deficit_45_55_split_is_full_GFN_allocation",
        "indicative_domestic_145_150_bn_is_realized_BNR_primary_issuance",
        "april_44_pct_GFN_covered_identifies_channel_mix",
        "retail_19_5_bn_through_april_is_in_BNR_primary_pilot",
    ):
        if comparison[key] is not False:
            errors.append(f"boundary comparison may not authorize {key}")

    resolution = review["allocation_bridge_resolution"]
    if resolution["status"] != STATUS:
        errors.append("allocation bridge status changed")
    for key in (
        "one_to_one_mapping_authorized",
        "residual_allocation_authorized",
        "synthetic_channel_shares_authorized",
        "cross_currency_aggregation_without_frozen_conversion_authorized",
        "parameter_estimation_authorized",
        "feedback_activation_authorized",
    ):
        if resolution[key] is not False:
            errors.append(f"allocation bridge may not authorize {key}")

    for key, value in review["hard_rules"].items():
        if value is not True:
            errors.append(f"hard rule disabled: {key}")

    for key, value in review["scientific_effect"].items():
        if value is not False:
            errors.append(f"review may not promote {key}")

    next_gate = review["next_gate"]
    if next_gate["id"] != "mof_realized_financing_channel_materialisation_contract":
        errors.append("next gate changed")
    if next_gate["authorization"] != "DESCRIPTIVE_SOURCE_CONTRACT_ONLY":
        errors.append("next gate authorization changed")
    for key in (
        "may_difference_cumulative_values_now",
        "may_infer_channel_residuals",
        "may_estimate_allocation_shares",
        "may_promote_generic_debt_issuance_node",
        "may_activate_feedback",
    ):
        if next_gate[key] is not False:
            errors.append(f"next gate may not authorize {key}")

    debt_node = next(x for x in boundary["variables"] if x["id"] == "government_debt_issuance")
    if debt_node.get("financing_channel_allocation_boundary_review") != REVIEW_PATH:
        errors.append("government-debt issuance node lacks financing-channel review")
    if debt_node.get("financing_channel_allocation_status") != STATUS:
        errors.append("government-debt issuance allocation status changed")
    if debt_node["current_boundary_class"] != "UNRESOLVED":
        errors.append("financing-channel review may not resolve debt-issuance node")
    if debt_node["current_feedback_activation_authorized"] is not False:
        errors.append("financing-channel review may not activate debt-issuance node")

    need_node = next(x for x in boundary["variables"] if x["id"] == "government_financing_need")
    if need_node.get("financing_channel_allocation_boundary_review") != REVIEW_PATH:
        errors.append("financing-need node lacks financing-channel review")
    if need_node.get("financing_channel_allocation_status") != STATUS:
        errors.append("financing-need allocation status changed")
    if need_node.get("allocation_vector_identified") is not False:
        errors.append("financing-need allocation vector may not be identified")

    links = [
        x for x in readiness["links"]
        if x["from"] == "government_financing_need"
        and x["to"] == "government_debt_issuance"
    ]
    if len(links) != 2:
        errors.append("expected two financing-need/debt-issuance links")
    for link in links:
        if link.get("financing_channel_allocation_boundary_review") != REVIEW_PATH:
            errors.append(f"{link['loop_id']}: financing-channel review missing")
        if link["causal_role"] != "FINANCING_CHANNEL_ALLOCATION_CONDITIONAL_ON_BOUNDARY":
            errors.append(f"{link['loop_id']}: financing-channel causal role changed")
        if link["readiness_status"] != STATUS:
            errors.append(f"{link['loop_id']}: financing-channel readiness changed")
        if link["exact_integrated_equation_ready"] is not False:
            errors.append(f"{link['loop_id']}: financing-channel link may not be equation-ready")
        if link["current_activation_authorized"] is not False:
            errors.append(f"{link['loop_id']}: financing-channel link may not activate")

    for loop_id in ("government_issuance_yield_loop", "government_refinancing_interest_loop"):
        loop = next(x for x in feedback["loops"] if x["id"] == loop_id)
        if loop.get("financing_channel_allocation_boundary_review") != REVIEW_PATH:
            errors.append(f"{loop_id}: feedback registry lacks financing-channel review")
        if loop.get("financing_channel_allocation_status") != STATUS:
            errors.append(f"{loop_id}: financing-channel status changed")
        if loop.get("financing_need_to_debt_issuance_equation_ready") is not False:
            errors.append(f"{loop_id}: financing-need/debt-issuance equation may not be ready")
        if loop["quantitatively_active"] is not False:
            errors.append(f"{loop_id}: financing-channel review may not activate loop")

    bridge = next(
        x for x in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if x["id"] == "financing_channel_allocation"
    )
    if bridge.get("status") != STATUS or bridge.get("boundary_review") != REVIEW_PATH:
        errors.append("preregistration financing-channel bridge changed")
    for key in (
        "one_to_one_GFN_to_BNR_issuance_authorized",
        "residual_allocation_authorized",
        "synthetic_channel_shares_authorized",
        "cross_currency_aggregation_without_frozen_conversion_authorized",
        "parameter_estimation_authorized",
        "feedback_activation_authorized",
    ):
        if bridge[key] is not False:
            errors.append(f"preregistration may not authorize {key}")
    if prereg["next_independent_bridge_task"]["id"] != "government_debt_issuance_to_debt_stock_boundary_review":
        errors.append("preregistration next independent bridge changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("financing_channel_allocation_boundary_review") != REVIEW_PATH:
        errors.append("model contract lacks financing-channel review")
    if dynamic.get("financing_channel_allocation_status") != STATUS:
        errors.append("model contract financing-channel status changed")
    if dynamic.get("government_financing_need_to_debt_issuance_equation_ready") is not False:
        errors.append("model contract may not mark financing-channel equation ready")
    if dynamic.get("government_financing_need_allocation_vector_identified") is not False:
        errors.append("model contract may not identify allocation vector")
    if dynamic.get("government_issuance_yield_next_independent_task") != (
        "government_debt_issuance_to_debt_stock_boundary_review"
    ):
        errors.append("model contract next independent task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("model contract may not activate issuance-yield feedback")

    if baseline["authority"].get("financing_channel_allocation_boundary_review") != REVIEW_PATH:
        errors.append("scientific baseline lacks financing-channel authority")

    return errors


def main() -> None:
    errors = audit_financing_channel_allocation_boundary(
        load(REVIEW_PATH),
        load("model/dynamics/government_debt_issuance_bnr_pilot_2025.json"),
        load("model/dynamics/government_debt_issuance_source_boundary_review.json"),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/feedback_registry.json"),
        load(PREREG_PATH),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
    )
    if errors:
        raise RuntimeError(
            "Financing-channel allocation boundary audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(json.dumps({
        "status": "PASS",
        "bridge_status": STATUS,
        "one_to_one_GFN_to_BNR_issuance": False,
        "allocation_vector_identified": False,
        "canonical_nodes_resolved": False,
        "feedback_activation_authorized": False,
        "next_gate": "mof_realized_financing_channel_materialisation_contract",
    }, indent=2))


if __name__ == "__main__":
    main()
