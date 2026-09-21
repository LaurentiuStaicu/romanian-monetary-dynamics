from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REVIEW_PATH="model/dynamics/debt_service_and_credit_risk_to_credit_supply_capacity_boundary_review_2026_09_21.json"
STATUS="RISK_AND_PRUDENTIAL_STATE_OBSERVED_CREDIT_SUPPLY_CAPACITY_SCALAR_NOT_IDENTIFIED"
def load(path): return json.loads((ROOT/path).read_text(encoding="utf-8"))
def audit_risk_to_credit_supply_capacity_boundary(review,prudential_review,aggregate_review,boundary,readiness,feedback,model,baseline):
    errors=[]
    if review["decision"]!="DO_NOT_MAP_NPL_DSTI_OR_CAPITAL_RATIO_ONE_TO_ONE_TO_CREDIT_SUPPLY_CAPACITY_KEEP_RISK_PRUDENTIAL_AND_LENDING_STANDARD_CONCEPTS_DISTINCT": errors.append("decision changed")
    for k,v in review["concept_boundary"].items():
        if k=="demand_and_supply_are_jointly_determined":
            if v is not True: errors.append("joint-determination guard disabled")
        elif v is not False: errors.append(f"concept boundary may not authorize {k}")
    if prudential_review["verdict"]!="DIRECT_CBD2_TO_BNR_POPULATION_EQUIVALENCE_REJECTED_NEW_MATCHED_SOURCE_REQUIRED": errors.append("prudential population verdict changed")
    if aggregate_review["scientific_boundary_decisions"]["aggregate_single_equation_not_yet_eligible_for_calibration"] is not True: errors.append("aggregate calibration gate unexpectedly opened")
    bridge=review["bridge_resolution"]
    if bridge["status"]!=STATUS: errors.append("bridge status changed")
    for k in ("direct_NPL_to_capacity_mapping_authorized","direct_DSTI_to_capacity_mapping_authorized","direct_capital_ratio_to_capacity_mapping_authorized","BLS_standards_equals_capacity_authorized","BLS_demand_as_supply_capacity_authorized","exogenous_NPL_supply_shock_authorized","synthetic_prudential_capacity_index_authorized","exact_integrated_equation_ready","parameter_estimation_authorized","feedback_activation_authorized"):
        if bridge[k] is not False: errors.append(f"bridge may not authorize {k}")
    risk=next(x for x in boundary["variables"] if x["id"]=="debt_service_and_credit_risk")
    capacity=next(x for x in boundary["variables"] if x["id"]=="credit_supply_capacity")
    for n in (risk,capacity):
        if n.get("debt_service_and_credit_risk_to_credit_supply_capacity_boundary_review")!=REVIEW_PATH: errors.append(f"{n['id']}: review pointer missing")
        if n.get("debt_service_and_credit_risk_to_credit_supply_capacity_status")!=STATUS: errors.append(f"{n['id']}: status changed")
        if n["current_boundary_class"]!="UNRESOLVED": errors.append(f"{n['id']}: review may not resolve node")
    if capacity.get("exact_reference_mode_id") is not None: errors.append("capacity may not gain exact reference mode")
    if capacity.get("scalar_capacity_measure_selected") is not False: errors.append("capacity scalar may not be selected")
    link=next(x for x in readiness["links"] if x["loop_id"]=="bank_credit_balance_sheet_loop" and x["from"]=="debt_service_and_credit_risk" and x["to"]=="credit_supply_capacity")
    if link["readiness_status"]!=STATUS: errors.append("feedback-link status changed")
    if link["exact_integrated_equation_ready"] is not False or link["current_activation_authorized"] is not False: errors.append("feedback link may not be ready or active")
    loop=next(x for x in feedback["loops"] if x["id"]=="bank_credit_balance_sheet_loop")
    if loop.get("debt_service_and_credit_risk_to_credit_supply_capacity_boundary_review")!=REVIEW_PATH: errors.append("loop pointer missing")
    if loop.get("debt_service_and_credit_risk_to_credit_supply_capacity_status")!=STATUS: errors.append("loop status changed")
    if loop["quantitatively_active"] is not False: errors.append("loop may not activate")
    d=model["dynamic_core"]
    if d.get("debt_service_and_credit_risk_to_credit_supply_capacity_boundary_review")!=REVIEW_PATH: errors.append("model pointer missing")
    if d.get("bank_credit_balance_sheet_next_structural_task")!="bank_credit_balance_sheet_loop_evidence_triggered_hold": errors.append("next bank-credit task changed")
    if baseline["authority"].get("debt_service_and_credit_risk_to_credit_supply_capacity_boundary_review")!=REVIEW_PATH: errors.append("baseline authority missing")
    for k,v in review["hard_rules"].items():
        if v is not True: errors.append(f"hard rule disabled: {k}")
    return errors
def main():
    errors=audit_risk_to_credit_supply_capacity_boundary(
        load(REVIEW_PATH),
        load("model/calibration_validation/bank_credit_prudential_population_boundary_review.json"),
        load("model/calibration_validation/aggregate_bank_credit_source_boundary_review.json"),
        load("model/dynamics/feedback_variable_boundary_registry.json"),
        load("model/dynamics/feedback_link_readiness_registry.json"),
        load("model/dynamics/feedback_registry.json"),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"))
    if errors: raise RuntimeError("Risk-to-credit-supply-capacity boundary audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({"status":"PASS","bridge_status":STATUS,"capacity_scalar_selected":False,"exact_integrated_equation_ready":False,"feedback_activation_authorized":False,"next_gate":"bank_credit_balance_sheet_loop_evidence_triggered_hold"},indent=2))
if __name__=="__main__": main()
