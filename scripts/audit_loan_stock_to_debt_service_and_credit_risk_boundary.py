from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REVIEW_PATH="model/dynamics/loan_stock_to_debt_service_and_credit_risk_boundary_review_2026_09_21.json"
STATUS="EXPOSURE_SCALE_OBSERVED_DEBT_SERVICE_AND_CREDIT_RISK_STATE_BOUNDARY_UNRECONCILED"
def load(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))
def audit_loan_stock_to_debt_service_and_credit_risk_boundary(review,risk_review,boundary,readiness,feedback,model,baseline):
    errors=[]
    if review["decision"]!="DO_NOT_MAP_LOAN_STOCK_ONE_TO_ONE_TO_DEBT_SERVICE_OR_CREDIT_RISK_KEEP_BURDEN_AND_ASSET_QUALITY_CONCEPTS_DISTINCT": errors.append("decision changed")
    for k,v in review["boundary_comparison"].items():
        if v is not False: errors.append(f"boundary comparison may not authorize {k}")
    bridge=review["bridge_resolution"]
    if bridge["status"]!=STATUS: errors.append("bridge status changed")
    for k in ("direct_loan_stock_to_debt_service_mapping_authorized","direct_loan_stock_to_credit_risk_mapping_authorized","stock_times_lending_rate_as_debt_service_authorized","assumed_maturity_amortisation_authorized","household_DSTI_substitution_for_aggregate_risk_authorized","NPL_target_switch_authorized","exact_integrated_equation_ready","parameter_estimation_authorized","feedback_activation_authorized"):
        if bridge[k] is not False: errors.append(f"bridge may not authorize {k}")
    if risk_review["disposition"]["mechanism_classification"]!="DEFERRED": errors.append("credit-risk mechanism classification changed")
    if risk_review["source_admissibility"]["registered_full_form_admissible"] is not False: errors.append("registered risk form unexpectedly admissible")
    loan=next(x for x in boundary["variables"] if x["id"]=="loan_stock")
    risk=next(x for x in boundary["variables"] if x["id"]=="debt_service_and_credit_risk")
    for n in (loan,risk):
        if n.get("loan_stock_to_debt_service_and_credit_risk_boundary_review")!=REVIEW_PATH: errors.append(f"{n['id']}: review pointer missing")
        if n.get("loan_stock_to_debt_service_and_credit_risk_status")!=STATUS: errors.append(f"{n['id']}: status changed")
        if n["current_boundary_class"]!="UNRESOLVED": errors.append(f"{n['id']}: review may not resolve node")
    if risk.get("exact_reference_mode_id") is not None: errors.append("combined risk node may not gain exact reference mode")
    link=next(x for x in readiness["links"] if x["loop_id"]=="bank_credit_balance_sheet_loop" and x["from"]=="loan_stock" and x["to"]=="debt_service_and_credit_risk")
    if link["readiness_status"]!=STATUS: errors.append("feedback-link status changed")
    if link["exact_integrated_equation_ready"] is not False or link["current_activation_authorized"] is not False: errors.append("feedback link may not be ready or active")
    loop=next(x for x in feedback["loops"] if x["id"]=="bank_credit_balance_sheet_loop")
    if loop.get("loan_stock_to_debt_service_and_credit_risk_boundary_review")!=REVIEW_PATH: errors.append("loop pointer missing")
    if loop.get("loan_stock_to_debt_service_and_credit_risk_status")!=STATUS: errors.append("loop status changed")
    if loop["quantitatively_active"] is not False: errors.append("loop may not activate")
    d=model["dynamic_core"]
    if d.get("loan_stock_to_debt_service_and_credit_risk_boundary_review")!=REVIEW_PATH: errors.append("model pointer missing")
    if d.get("bank_credit_balance_sheet_next_structural_task")!="bank_credit_balance_sheet_loop_terminal_assessment": errors.append("next bank-credit task changed")
    if baseline["authority"].get("loan_stock_to_debt_service_and_credit_risk_boundary_review")!=REVIEW_PATH: errors.append("baseline authority missing")
    for k,v in review["hard_rules"].items():
        if v is not True: errors.append(f"hard rule disabled: {k}")
    return errors
def main():
    errors=audit_loan_stock_to_debt_service_and_credit_risk_boundary(
        load(REVIEW_PATH),
        load("model/calibration_validation/credit_risk_npl_source_boundary_review.json"),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/feedback_registry.json"),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"))
    if errors: raise RuntimeError("Loan-stock to debt-service/credit-risk boundary audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({"status":"PASS","bridge_status":STATUS,"exact_integrated_equation_ready":False,"feedback_activation_authorized":False,"next_gate":"bank_credit_balance_sheet_loop_terminal_assessment"},indent=2))
if __name__=="__main__": main()
