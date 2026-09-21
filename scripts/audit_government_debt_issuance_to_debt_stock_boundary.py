from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = "model/dynamics/government_debt_issuance_to_debt_stock_boundary_review_2026_09_21.json"
PREREG_PATH = "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
STATUS = "STOCK_ACCUMULATION_FORM_KNOWN_NET_DEBT_TRANSACTION_BOUNDARY_NOT_IDENTIFIED"
NEXT_GATE = "government_debt_stock_to_interest_cost_boundary_review"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_government_debt_issuance_to_debt_stock_boundary(
    review: dict,
    debt_assessment: dict,
    debt_snapshot: dict,
    financing_assessment: dict,
    boundary: dict,
    readiness: dict,
    feedback: dict,
    prereg: dict,
    model_contract: dict,
    baseline: dict,
) -> list[str]:
    errors: list[str] = []

    if review["decision"] != (
        "DO_NOT_MAP_GROSS_BORROWING_ONE_TO_ONE_TO_DEBT_STOCK_CHANGE_"
        "USE_MATCHED_NET_DEBT_TRANSACTIONS_PLUS_STOCK_FLOW_ADJUSTMENTS"
    ):
        errors.append("debt-issuance to debt-stock decision changed")

    edp = review["official_definition_evidence"]["romania_april_2026_edp_table_3a_2025"]
    c = edp["displayed_2025_components"]
    if c["deficit_contribution_positive_table3_sign"] + c["net_acquisition_financial_assets"] + c["adjustments"] + c["statistical_discrepancies"] != c["change_in_consolidated_gross_debt"]:
        errors.append("EDP Table 3A displayed 2025 identity no longer reconciles")
    if c["change_in_consolidated_gross_debt"] != 172516:
        errors.append("EDP Table 3A 2025 debt change changed")

    series = debt_snapshot["series"]["MIO_NAC"]["observations"]
    delta = round(series["2025-Q4"] - series["2024-Q4"], 1)
    retained = review["official_definition_evidence"]["retained_government_debt_stock_reference"]
    if delta != retained["observed_2025_change_million_RON"]:
        errors.append("retained quarterly debt-stock delta changed")
    if round(delta) != c["change_in_consolidated_gross_debt"]:
        errors.append("quarterly debt-stock snapshot no longer matches EDP annual debt change at published precision")
    if debt_assessment["verdict"] != "PROMOTE_TO_OBSERVED_SERIES_AVAILABLE":
        errors.append("government-debt stock observed target status changed")

    mof = review["official_definition_evidence"]["retained_mof_realized_financing_boundary"]
    if mof["direct_equality_or_residual_reconciliation_authorized"] is not False:
        errors.append("MoF borrowing may not be directly reconciled as an identity to S13 debt change")
    if financing_assessment["materialisation_disposition"]["monthly_increment_equation_authorized"] is not False:
        errors.append("monthly financing differencing unexpectedly became authorized")

    accounting = review["accounting_boundary"]
    for key in (
        "gross_borrowing_equals_change_in_Maastricht_debt",
        "gross_issuance_equals_net_incurrence_of_debt_liabilities",
    ):
        if accounting[key] is not False:
            errors.append(f"accounting boundary may not authorize {key}")
    for key in (
        "redemptions_and_principal_repayments_required_for_netting",
        "exchange_buyback_and_liability_management_operations_must_be_separate",
        "consolidation_across_general_government_subsectors_must_be_preserved",
        "nominal_face_value_boundary_must_be_preserved",
        "statistical_discrepancy_must_not_be_forced_to_zero",
        "sector_instrument_currency_frequency_and_valuation_must_match_before_identity",
    ):
        if accounting[key] is not True:
            errors.append(f"accounting boundary guard disabled: {key}")

    bridge = review["bridge_resolution"]
    if bridge["status"] != STATUS:
        errors.append("debt-stock bridge status changed")
    if bridge["causal_role"] != "STOCK_ACCUMULATION_ACCOUNTING_RELATION_CONDITIONAL_ON_MATCHED_BOUNDARY":
        errors.append("debt-stock bridge causal role changed")
    for key in (
        "one_to_one_gross_borrowing_to_stock_change_authorized",
        "residual_redemptions_as_gross_borrowing_minus_stock_change_authorized",
        "exchange_operations_as_net_new_debt_authorized",
        "synthetic_redemption_schedule_authorized",
        "synthetic_stock_flow_adjustment_authorized",
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
    if effect["debt_issuance_to_stock_boundary_strengthened"] is not True:
        errors.append("boundary-strengthening effect changed")
    for key, value in effect.items():
        if key != "debt_issuance_to_stock_boundary_strengthened" and value is not False:
            errors.append(f"review may not promote {key}")

    issuance = next(x for x in boundary["variables"] if x["id"] == "government_debt_issuance")
    stock = next(x for x in boundary["variables"] if x["id"] == "government_debt_stock")
    for node in (issuance, stock):
        if node.get("government_debt_issuance_to_debt_stock_boundary_review") != REVIEW_PATH:
            errors.append(f"{node['id']}: debt-stock boundary review missing")
        if node.get("debt_issuance_to_stock_status") != STATUS:
            errors.append(f"{node['id']}: debt-stock boundary status changed")
        if node["current_boundary_class"] != "UNRESOLVED":
            errors.append(f"{node['id']}: review may not resolve node")
        if node["current_feedback_activation_authorized"] is not False:
            errors.append(f"{node['id']}: review may not activate node")
    if issuance.get("matched_net_debt_transaction_stream_identified") is not False:
        errors.append("issuance node may not claim a matched net-debt transaction stream")
    if stock.get("exact_stock_transition_ready") is not False:
        errors.append("debt-stock node may not claim an exact stock transition")

    link = next(
        x for x in readiness["links"]
        if x["loop_id"] == "government_refinancing_interest_loop"
        and x["from"] == "government_debt_issuance"
        and x["to"] == "government_debt_stock"
    )
    if link["readiness_status"] != STATUS:
        errors.append("feedback-link debt-stock status changed")
    if link["causal_role"] != "STOCK_ACCUMULATION_ACCOUNTING_RELATION_CONDITIONAL_ON_MATCHED_BOUNDARY":
        errors.append("feedback-link causal role changed")
    if link.get("government_debt_issuance_to_debt_stock_boundary_review") != REVIEW_PATH:
        errors.append("feedback-link review pointer missing")
    if link["exact_integrated_equation_ready"] is not False or link["current_activation_authorized"] is not False:
        errors.append("debt-stock feedback link may not be exact-ready or active")

    loop = next(x for x in feedback["loops"] if x["id"] == "government_refinancing_interest_loop")
    if loop.get("government_debt_issuance_to_debt_stock_boundary_review") != REVIEW_PATH:
        errors.append("refinancing loop review pointer missing")
    if loop.get("debt_issuance_to_stock_status") != STATUS:
        errors.append("refinancing loop debt-stock status changed")
    if loop.get("debt_issuance_to_stock_equation_ready") is not False:
        errors.append("refinancing loop debt-stock equation may not be ready")
    if loop["quantitatively_active"] is not False:
        errors.append("review may not activate refinancing loop")

    if prereg.get("government_debt_issuance_to_debt_stock_boundary_review") != REVIEW_PATH:
        errors.append("preregistration review pointer missing")
    if prereg.get("government_debt_issuance_to_debt_stock_boundary_status") != STATUS:
        errors.append("preregistration debt-stock status changed")
    next_task = prereg["next_independent_bridge_task"]
    if next_task["id"] != NEXT_GATE:
        errors.append("preregistration next independent bridge changed")
    if next_task["authorization"] != "STRUCTURAL_ACCOUNTING_SOURCE_BOUNDARY_REVIEW_ONLY":
        errors.append("next independent bridge authorization changed")
    for key in (
        "may_map_debt_stock_level_one_to_one_to_interest_cost",
        "may_estimate_parameters",
        "may_activate_feedback",
        "may_change_behavioural_closure",
    ):
        if next_task[key] is not False:
            errors.append(f"next independent bridge may not authorize {key}")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("government_debt_issuance_to_debt_stock_boundary_review") != REVIEW_PATH:
        errors.append("model contract review pointer missing")
    if dynamic.get("government_debt_issuance_to_debt_stock_boundary_status") != STATUS:
        errors.append("model contract debt-stock status changed")
    if dynamic.get("government_debt_issuance_to_debt_stock_equation_ready") is not False:
        errors.append("model contract may not mark debt-stock bridge equation-ready")
    if dynamic.get("government_issuance_yield_next_independent_task") != NEXT_GATE:
        errors.append("model contract next independent task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("model contract may not activate government feedback")

    if baseline["authority"].get("government_debt_issuance_to_debt_stock_boundary_review") != REVIEW_PATH:
        errors.append("scientific baseline lacks debt-stock boundary authority")

    return errors


def main() -> None:
    errors = audit_government_debt_issuance_to_debt_stock_boundary(
        load(REVIEW_PATH),
        load("model/dynamics/government_debt_stock_reference_assessment.json"),
        load("model/dynamics/government_debt_stock_reference_snapshot.json"),
        load("model/dynamics/mof_realized_financing_channel_source_vintage_assessment_2026_09_21.json"),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/feedback_registry.json"),
        load(PREREG_PATH),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
    )
    if errors:
        raise RuntimeError(
            "Government debt issuance-to-stock boundary audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(json.dumps({
        "status": "PASS",
        "bridge_status": STATUS,
        "gross_borrowing_to_stock_one_to_one": False,
        "matched_net_debt_transaction_stream_identified": False,
        "exact_integrated_equation_ready": False,
        "feedback_activation_authorized": False,
        "next_gate": NEXT_GATE,
    }, indent=2))


if __name__ == "__main__":
    main()
