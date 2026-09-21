from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REVIEW_PATH = "model/dynamics/credit_flow_to_loan_stock_boundary_review_2026_09_21.json"
STATUS = "STOCK_TRANSACTION_RECONCILIATION_FORM_KNOWN_NON_TRANSACTION_ADJUSTMENTS_REQUIRED"

def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def audit_credit_flow_to_loan_stock_boundary(
    review: dict, private_credit: dict, snapshot: dict, boundary: dict,
    readiness: dict, feedback: dict, model_contract: dict, baseline: dict
) -> list[str]:
    errors: list[str] = []
    if review["decision"] != "DO_NOT_SET_LOAN_STOCK_CHANGE_EQUAL_TO_CREDIT_FLOW_USE_MATCHED_BSI_STOCK_TRANSACTION_RECONCILIATION_WITH_NON_TRANSACTION_ADJUSTMENTS":
        errors.append("credit-flow/loan-stock decision changed")
    form = review["admissible_accounting_form"]
    if form["credit_transaction_is_observed"] is not True:
        errors.append("credit transaction observation status changed")
    if form["exact_future_endogenous_stock_equation_ready"] is not False:
        errors.append("endogenous stock equation may not be ready")
    bridge = review["bridge_resolution"]
    if bridge["status"] != STATUS:
        errors.append("bridge status changed")
    for key in (
        "stock_change_equals_credit_flow_authorized",
        "omit_non_transaction_adjustment_authorized",
        "use_stock_first_difference_as_credit_flow_authorized",
        "infer_causal_adjustment_decomposition_from_residual_authorized",
        "exact_integrated_equation_ready",
        "parameter_estimation_authorized",
        "feedback_activation_authorized",
    ):
        if bridge[key] is not False:
            errors.append(f"bridge may not authorize {key}")
    if private_credit["verdict"] != "PROMOTE_BOTH_TO_OBSERVED_SERIES_AVAILABLE":
        errors.append("private-credit observed reference status changed")
    if snapshot["hard_boundary"]["stock_difference_used_as_flow"] is not False:
        errors.append("stock difference may not become flow")
    credit = next(x for x in boundary["variables"] if x["id"] == "credit_flow")
    stock = next(x for x in boundary["variables"] if x["id"] == "loan_stock")
    for node in (credit, stock):
        if node.get("credit_flow_to_loan_stock_boundary_review") != REVIEW_PATH:
            errors.append(f"{node['id']}: boundary review pointer missing")
        if node.get("credit_flow_to_loan_stock_status") != STATUS:
            errors.append(f"{node['id']}: boundary status changed")
        if node["current_boundary_class"] != "UNRESOLVED":
            errors.append(f"{node['id']}: review may not resolve endogenous boundary")
    if stock.get("exact_reference_mode_id") != "credit_stock":
        errors.append("loan_stock exact reference mapping changed")
    if stock.get("endogenous_stock_transition_ready") is not False:
        errors.append("loan_stock endogenous transition may not be ready")
    link = next(x for x in readiness["links"] if x["loop_id"]=="bank_credit_balance_sheet_loop" and x["from"]=="credit_flow" and x["to"]=="loan_stock")
    if link["readiness_status"] != STATUS:
        errors.append("feedback-link status changed")
    if link["exact_integrated_equation_ready"] is not False or link["current_activation_authorized"] is not False:
        errors.append("feedback link may not become exact-ready or active")
    loop = next(x for x in feedback["loops"] if x["id"]=="bank_credit_balance_sheet_loop")
    if loop.get("credit_flow_to_loan_stock_boundary_review") != REVIEW_PATH:
        errors.append("bank-credit loop review pointer missing")
    if loop.get("credit_flow_to_loan_stock_status") != STATUS:
        errors.append("bank-credit loop boundary status changed")
    if loop["quantitatively_active"] is not False:
        errors.append("bank-credit loop may not activate")
    d=model_contract["dynamic_core"]
    if d.get("credit_flow_to_loan_stock_boundary_review") != REVIEW_PATH:
        errors.append("model contract review pointer missing")
    if d.get("credit_flow_to_loan_stock_boundary_status") != STATUS:
        errors.append("model contract boundary status changed")
    if d.get("bank_credit_balance_sheet_next_structural_task") != "bank_credit_balance_sheet_loop_evidence_triggered_hold":
        errors.append("model contract next bank-credit task changed")
    if baseline["authority"].get("credit_flow_to_loan_stock_boundary_review") != REVIEW_PATH:
        errors.append("scientific baseline authority missing")
    for key,value in review["hard_rules"].items():
        if value is not True:
            errors.append(f"hard rule disabled: {key}")
    return errors

def main() -> None:
    errors = audit_credit_flow_to_loan_stock_boundary(
        load(REVIEW_PATH),
        load("model/dynamics/private_credit_reference_assessment.json"),
        load("model/dynamics/private_credit_reference_snapshot.json"),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/feedback_registry.json"),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
    )
    if errors:
        raise RuntimeError("Credit-flow to loan-stock boundary audit failed:\n- " + "\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "bridge_status":STATUS,
        "loan_stock_reference_mode":"credit_stock",
        "stock_change_equals_flow":False,
        "exact_integrated_equation_ready":False,
        "feedback_activation_authorized":False,
        "next_gate":"loan_stock_to_debt_service_and_credit_risk_boundary_review"
    },indent=2))

if __name__ == "__main__":
    main()
