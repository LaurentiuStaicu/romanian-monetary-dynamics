from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = "model/dynamics/government_securities_supply_pressure_source_boundary_review_2026_09_20.json"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_supply_pressure_source_boundary(
    review: dict,
    boundary: dict,
    readiness: dict,
    feedback: dict,
    prereg: dict,
    model_contract: dict,
) -> list[str]:
    errors: list[str] = []

    if review.get("decision") != (
        "MULTIDIMENSIONAL_CANDIDATE_BOUNDARY_NO_SCALAR_PROMOTION"
    ):
        errors.append("supply-pressure source-boundary decision changed")

    state = review["current_node_status"]
    if state["boundary_class"] != "UNRESOLVED":
        errors.append("supply-pressure node may not be resolved by source review")
    if state["feedback_activation_authorized"] is not False:
        errors.append("source review may not authorize feedback activation")
    if state["exact_reference_mode_id"] is not None:
        errors.append("source review may not assign an exact reference mode")

    official = review["official_source_family"]
    if official["institution"] != (
        "Romanian Ministry of Finance — General Directorate of Treasury and Public Debt"
    ):
        errors.append("official Ministry source family changed")
    example = official["example_reviewed_source"]
    required_fields = {
        "announced amounts",
        "amount of tenders submitted",
        "accepted amounts",
        "bid-to-cover ratio",
    }
    if set(example["primary_market_fields_shown"]) != required_fields:
        errors.append("reviewed primary-market field set changed")
    if example["published_bid_to_cover_definition"] != (
        "amount of bids submitted / accepted amounts"
    ):
        errors.append("published bid-to-cover definition changed")

    if review["auction_rule_evidence"]["structural_implication"] != (
        "accepted_amount_is_an_auction_outcome_and_may_not_be_treated_as_pure_ex_ante_supply"
    ):
        errors.append("accepted-amount structural guard changed")

    candidates = {
        item["candidate_id"]: item
        for item in review["candidate_observable_vector"]
    }
    expected = {
        "domestic_RON_primary_market_supply_load",
        "domestic_RON_primary_market_auction_absorption",
        "domestic_RON_primary_market_bid_to_cover",
        "domestic_government_securities_secondary_market_liquidity",
    }
    if set(candidates) != expected:
        errors.append(
            "supply-pressure candidate vector changed: "
            f"expected={sorted(expected)}, observed={sorted(candidates)}"
        )

    if candidates["domestic_RON_primary_market_supply_load"]["provisional_formula"] != (
        "monthly_announced_RON_amount / lagged_month_end_outstanding_domestic_RON_government_securities"
    ):
        errors.append("ex-ante supply-load formula changed")
    if candidates["domestic_RON_primary_market_auction_absorption"]["provisional_formula"] != (
        "monthly_submitted_RON_bids / monthly_announced_RON_amount"
    ):
        errors.append("auction-absorption formula changed")
    if candidates["domestic_RON_primary_market_bid_to_cover"]["provisional_formula"] != (
        "monthly_submitted_RON_bids / monthly_accepted_RON_amount"
    ):
        errors.append("published bid-to-cover formula changed")
    if candidates["domestic_government_securities_secondary_market_liquidity"]["provisional_formula"] != (
        "monthly_secondary_market_transaction_volume / total_government_securities_volume"
    ):
        errors.append("secondary-market liquidity formula changed")

    for item in candidates.values():
        if item["activation_ready"] is not False:
            errors.append(f"{item['candidate_id']}: candidate may not be activation-ready")

    maturity = review["maturity_and_currency_boundary"]
    if maturity["primary_candidate_currency"] != "RON":
        errors.append("primary supply-pressure candidate currency changed")
    if maturity["cross_currency_aggregation_authorized"] is not False:
        errors.append("cross-currency aggregation may not be authorized")
    if maturity["cross_maturity_aggregation_authorized"] is not False:
        errors.append("cross-maturity aggregation may not be authorized")

    gate = review["materialisation_gate"]
    if gate["source_values_materialised_now"] is not False:
        errors.append("source-boundary review may not claim source values materialised")
    if gate["raw_ministry_pdf_retained_now"] is not True:
        errors.append("review must retain completed Ministry raw-source probe")
    if gate.get("raw_source_probe_status") != (
        "PASS_THREE_OFFICIAL_PDFS_RETAINED_NATIVE_TEXT_EXTRACTABLE"
    ):
        errors.append("Ministry raw-source probe status changed")
    if gate.get("exact_auction_table_values_extractable") is not True:
        errors.append("exact auction-table extractability must remain recorded")
    if gate.get("submitted_bids_monthly_series_exactly_extractable") is not False:
        errors.append("submitted-bids series may not be claimed exactly extractable")
    if gate.get("supply_load_denominator_boundary_frozen") is not False:
        errors.append("supply-load denominator may not be claimed frozen")
    for key in (
        "visual_chart_digitisation_authorized",
        "ocr_authorized",
        "manual_approximation_authorized",
    ):
        if gate[key] is not False:
            errors.append(f"source-boundary review may not authorize {key}")

    effect = review["scientific_effect"]
    for key in (
        "government_securities_supply_pressure_node_resolved",
        "scalar_pressure_index_selected",
        "exact_reference_mode_promoted",
        "equation_selected",
        "estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
    ):
        if effect[key] is not False:
            errors.append(f"supply-pressure source review may not promote {key}")

    task = review["next_task"]
    if task["id"] != "government_securities_supply_measurement_design_review":
        errors.append("next supply-pressure task changed")
    if task["authorization"] != "STRUCTURAL_MEASUREMENT_DESIGN_ONLY":
        errors.append("next task authorization changed")
    if task["may_compute_pressure_ratio_now"] is not False:
        errors.append("next task may not compute pressure ratio")
    if task["may_create_approximate_chart_values"] is not False:
        errors.append("next task may not create approximate chart values")
    if task["may_activate_feedback"] is not False:
        errors.append("next task may not activate feedback")

    node = next(
        item for item in boundary["variables"]
        if item["id"] == "government_securities_supply_pressure"
    )
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("boundary registry supply-pressure node resolved")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("boundary registry supply-pressure activation changed")
    if node["source_boundary_review"] != REVIEW_PATH:
        errors.append("boundary registry lacks source-boundary review")
    if node["empirical_boundary_status"] != (
        "MULTIDIMENSIONAL_CANDIDATE_BOUNDARY_NO_SCALAR_PROMOTION"
    ):
        errors.append("boundary registry empirical status changed")
    if node["scalar_pressure_index_selected"] is not False:
        errors.append("boundary registry selected a scalar pressure index")
    if set(node["candidate_observable_vector"]) != expected:
        errors.append("boundary registry candidate vector changed")

    link = next(
        item for item in readiness["links"]
        if item["loop_id"] == "government_issuance_yield_loop"
        and item["from"] == "government_debt_issuance"
        and item["to"] == "government_securities_supply_pressure"
    )
    if link["supply_pressure_source_boundary_review"] != REVIEW_PATH:
        errors.append("issuance-to-pressure link lacks source review")
    if link["readiness_status"] != (
        "STRUCTURAL_RELATION_NOT_CONTRACTED_AS_INTEGRATED_EQUATION"
    ):
        errors.append("issuance-to-pressure canonical readiness changed")
    if link.get("source_boundary_status") != (
        "RAW_RETAINED_ANNOUNCED_EXACT_NO_EXACT_ONE_TO_ONE_DENOMINATOR_SELECTED"
    ):
        errors.append("issuance-to-pressure source-boundary status changed")
    if link["exact_integrated_equation_ready"] is not False:
        errors.append("source review may not make issuance-to-pressure equation ready")
    if link["current_activation_authorized"] is not False:
        errors.append("source review may not activate issuance-to-pressure link")

    loop = next(
        item for item in feedback["loops"]
        if item["id"] == "government_issuance_yield_loop"
    )
    if loop["government_securities_supply_pressure_source_boundary_review"] != REVIEW_PATH:
        errors.append("feedback registry lacks supply-pressure source review")
    if loop["supply_pressure_empirical_boundary_status"] != (
        "MULTIDIMENSIONAL_CANDIDATE_BOUNDARY_NO_SCALAR_PROMOTION"
    ):
        errors.append("feedback registry supply-pressure status changed")
    if loop["supply_pressure_scalar_selected"] is not False:
        errors.append("feedback registry selected a supply-pressure scalar")
    if loop["quantitatively_active"] is not False:
        errors.append("supply-pressure source review may not activate loop")

    bridge = next(
        item for item in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if item["id"] == "issuance_to_supply_pressure"
    )
    if bridge["source_boundary_review"] != REVIEW_PATH:
        errors.append("structural preregistration lacks supply-pressure review")
    if bridge["status"] != (
        "ANNOUNCED_EXACT_NO_ONE_TO_ONE_DENOMINATOR_SUBMITTED_BIDS_BLOCKED"
    ):
        errors.append("issuance-to-pressure bridge status changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic["government_securities_supply_pressure_source_boundary_review"] != REVIEW_PATH:
        errors.append("model contract lacks supply-pressure source review")
    if dynamic["government_securities_supply_pressure_boundary_status"] != (
        "MULTIDIMENSIONAL_CANDIDATE_BOUNDARY_NO_SCALAR_PROMOTION"
    ):
        errors.append("model contract supply-pressure status changed")
    if dynamic["government_securities_supply_pressure_scalar_selected"] is not False:
        errors.append("model contract selected a scalar pressure index")
    if dynamic["next_government_issuance_yield_empirical_task"] != (
        "government_securities_supply_measurement_design_review"
    ):
        errors.append("model contract next issuance-yield task changed")

    return errors


def main() -> None:
    review = load(REVIEW_PATH)
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    readiness = load("model/dynamics/feedback_link_readiness_registry.json")
    feedback = load("model/dynamics/feedback_registry.json")
    prereg = load(
        "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
    )
    model_contract = load("model/registries/model_contract.json")

    errors = audit_supply_pressure_source_boundary(
        review, boundary, readiness, feedback, prereg, model_contract
    )
    if errors:
        raise RuntimeError(
            "Government securities supply-pressure source-boundary audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(
        json.dumps(
            {
                "status": "PASS",
                "node_id": "government_securities_supply_pressure",
                "boundary": "MULTIDIMENSIONAL_CANDIDATE_BOUNDARY_NO_SCALAR_PROMOTION",
                "candidate_observables": 4,
                "source_values_materialised": False,
                "scalar_pressure_index_selected": False,
                "feedback_activation_authorized": False,
                "raw_source_probe": "PASS",
                "exact_auction_table_extractability": True,
                "submitted_bids_series_extractable": False,
                "denominator_boundary_frozen": False,
                "denominator_review": "NO_EXACT_ONE_TO_ONE_AUCTION_UNIVERSE_DENOMINATOR_SELECTED",
                "next_task": "government_securities_supply_measurement_design_review",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
