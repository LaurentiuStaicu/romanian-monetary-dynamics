from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
REVIEW_PATH="model/dynamics/credit_supply_capacity_to_credit_flow_boundary_review_2026_09_21.json"
STATUS="SUPPLY_CONDITION_AND_DEMAND_OBSERVABLES_AVAILABLE_REALIZED_CREDIT_FLOW_JOINTLY_DETERMINED"
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
def audit_credit_supply_capacity_to_credit_flow_boundary(review,private_credit,aggregate_review,boundary,readiness,feedback,model,baseline):
    errors=[]
    if review["decision"]!="DO_NOT_MAP_CREDIT_SUPPLY_CAPACITY_ONE_TO_ONE_TO_REALIZED_CREDIT_FLOW_KEEP_SUPPLY_AND_DEMAND_SEPARATE_IN_ANY_FUTURE_IDENTIFICATION": errors.append("decision changed")
    for k,v in review["boundary_comparison"].items():
        if v is not False: errors.append(f"boundary comparison may not authorize {k}")
    if private_credit["verdict"]!="PROMOTE_BOTH_TO_OBSERVED_SERIES_AVAILABLE": errors.append("credit-flow observed target changed")
    if aggregate_review["scientific_boundary_decisions"]["aggregate_single_equation_not_yet_eligible_for_calibration"] is not True: errors.append("aggregate calibration gate unexpectedly opened")
    bridge=review["bridge_resolution"]
    if bridge["status"]!=STATUS: errors.append("bridge status changed")
    for k in ("capacity_equals_realized_flow_authorized","BLS_standards_equals_realized_flow_authorized","infer_demand_from_credit_flow_authorized","supply_only_interpretation_of_credit_flow_authorized","synthetic_sector_aggregation_authorized","exact_integrated_equation_ready","parameter_estimation_authorized","feedback_activation_authorized"):
        if bridge[k] is not False: errors.append(f"bridge may not authorize {k}")
    cap=next(x for x in boundary["variables"] if x["id"]=="credit_supply_capacity")
    flow=next(x for x in boundary["variables"] if x["id"]=="credit_flow")
    for n in (cap,flow):
        if n.get("credit_supply_capacity_to_credit_flow_boundary_review")!=REVIEW_PATH: errors.append(f"{n['id']}: review pointer missing")
        if n.get("credit_supply_capacity_to_credit_flow_status")!=STATUS: errors.append(f"{n['id']}: status changed")
        if n["current_boundary_class"]!="UNRESOLVED": errors.append(f"{n['id']}: review may not resolve node")
    if flow.get("exact_reference_mode_id")!="credit_flow": errors.append("credit-flow reference mapping changed")
    if flow.get("endogenous_supply_demand_mapping_ready") is not False: errors.append("credit-flow endogenous mapping may not be ready")
    link=next(x for x in readiness["links"] if x["loop_id"]=="bank_credit_balance_sheet_loop" and x["from"]=="credit_supply_capacity" and x["to"]=="credit_flow")
    if link["readiness_status"]!=STATUS: errors.append("feedback-link status changed")
    if link["exact_integrated_equation_ready"] is not False or link["current_activation_authorized"] is not False: errors.append("feedback link may not be ready or active")
    loop=next(x for x in feedback["loops"] if x["id"]=="bank_credit_balance_sheet_loop")
    if loop.get("credit_supply_capacity_to_credit_flow_boundary_review")!=REVIEW_PATH: errors.append("loop pointer missing")
    if loop.get("credit_supply_capacity_to_credit_flow_status")!=STATUS: errors.append("loop status changed")
    if loop["quantitatively_active"] is not False: errors.append("loop may not activate")
    d=model["dynamic_core"]
    if d.get("credit_supply_capacity_to_credit_flow_boundary_review")!=REVIEW_PATH: errors.append("model pointer missing")
    if d.get("bank_credit_balance_sheet_next_structural_task")!="bank_credit_balance_sheet_loop_terminal_assessment": errors.append("next bank-credit task changed")
    if baseline["authority"].get("credit_supply_capacity_to_credit_flow_boundary_review")!=REVIEW_PATH: errors.append("baseline authority missing")
    for k,v in review["hard_rules"].items():
        if v is not True: errors.append(f"hard rule disabled: {k}")
    return errors
def main():
    errors=audit_credit_supply_capacity_to_credit_flow_boundary(
        load(REVIEW_PATH),load("model/dynamics/private_credit_reference_assessment.json"),load("model/calibration_validation/aggregate_bank_credit_source_boundary_review.json"),load("model/dynamics/feedback_variable_boundary_registry.json"),load("model/dynamics/feedback_link_readiness_registry.json"),load("model/dynamics/feedback_registry.json"),load("model/registries/model_contract.json"),load("model/registries/scientific_baseline_manifest.json"))
    if errors: raise RuntimeError("Credit-supply-capacity to credit-flow boundary audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({"status":"PASS","bridge_status":STATUS,"exact_integrated_equation_ready":False,"feedback_activation_authorized":False,"next_gate":"bank_credit_balance_sheet_loop_terminal_assessment"},indent=2))
if __name__=="__main__": main()
