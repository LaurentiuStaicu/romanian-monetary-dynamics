from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ASSESSMENT_PATH="model/dynamics/bank_credit_balance_sheet_loop_terminal_assessment_2026_09_21.json"
STATUS="STRUCTURAL_REVIEW_COMPLETE_IDENTIFICATION_AND_MEASUREMENT_BLOCKED_EVIDENCE_TRIGGERED_HOLD"
HOLD_ID="bank_credit_balance_sheet_loop_evidence_triggered_hold"
EXPECTED={
("credit_flow","loan_stock"):"STOCK_TRANSACTION_RECONCILIATION_FORM_KNOWN_NON_TRANSACTION_ADJUSTMENTS_REQUIRED",
("loan_stock","debt_service_and_credit_risk"):"EXPOSURE_SCALE_OBSERVED_DEBT_SERVICE_AND_CREDIT_RISK_STATE_BOUNDARY_UNRECONCILED",
("debt_service_and_credit_risk","credit_supply_capacity"):"RISK_AND_PRUDENTIAL_STATE_OBSERVED_CREDIT_SUPPLY_CAPACITY_SCALAR_NOT_IDENTIFIED",
("credit_supply_capacity","credit_flow"):"SUPPLY_CONDITION_AND_DEMAND_OBSERVABLES_AVAILABLE_REALIZED_CREDIT_FLOW_JOINTLY_DETERMINED",
}
def load(p): return json.loads((ROOT/p).read_text(encoding="utf-8"))
def audit_bank_credit_loop_terminal(a,feedback,readiness,boundary,criteria,delays,mechanisms,aggregate_review,risk_review,model,baseline):
    e=[]
    if a["decision"]!=STATUS:e.append("terminal decision changed")
    if a["loop_id"]!="bank_credit_balance_sheet_loop":e.append("loop id changed")
    t=a["topology"]
    if t["status"]!="CLOSED_CANDIDATE_LOOP" or t["quantitatively_active"] is not False or t["behavioural_closure_active"] is not False:e.append("terminal topology/activation changed")
    loop=next(x for x in feedback["loops"] if x["id"]=="bank_credit_balance_sheet_loop")
    if loop.get("structural_terminal_assessment")!=ASSESSMENT_PATH:e.append("loop terminal pointer missing")
    if loop.get("structural_review_status")!=STATUS:e.append("loop terminal status changed")
    if loop.get("operational_state")!="EVIDENCE_TRIGGERED_HOLD":e.append("loop operational state changed")
    if loop.get("active_empirical_task") is not None:e.append("loop may not expose active task")
    rows=[x for x in readiness["links"] if x["loop_id"]=="bank_credit_balance_sheet_loop"]
    if len(rows)!=4:e.append("expected 4 bank-credit links")
    for r in rows:
        key=(r["from"],r["to"])
        if EXPECTED.get(key)!=r["readiness_status"]:e.append(f"{key}: readiness status changed")
        if r["exact_integrated_equation_ready"] is not False or r["current_activation_authorized"] is not False:e.append(f"{key}: link may not be ready/active")
    integ=next(x for x in readiness["loop_activation_readiness"] if x["loop_id"]=="bank_credit_balance_sheet_loop")
    if integ["path_link_count"]!=4 or integ["exact_integrated_link_forms_ready"]!=0:e.append("integrated link readiness changed")
    if set(integ["unresolved_boundary_nodes"])!={"credit_flow","loan_stock","debt_service_and_credit_risk","credit_supply_capacity"}:e.append("unresolved node set changed")
    if integ["activation_status"]!="BLOCKED" or integ["quantitative_activation_authorized"] is not False:e.append("integrated activation changed")
    by={x["id"]:x for x in boundary["variables"]}
    for n in ("credit_flow","loan_stock","debt_service_and_credit_risk","credit_supply_capacity"):
        if by[n]["current_boundary_class"]!="UNRESOLVED" or by[n]["current_feedback_activation_authorized"] is not False:e.append(f"{n}: node boundary/activation changed")
    crit=next(x for x in criteria["feedbacks"] if x["loop_id"]=="bank_credit_balance_sheet_loop")
    snap=a["activation_gate_snapshot"]
    for k in ("passed_criteria_count","partial_criteria_count","blocked_criteria_count","not_assessable_criteria_count"):
        if crit[k]!=snap[k]:e.append(f"activation count changed: {k}")
    if crit["all_requirements_pass"] is not False or crit["quantitative_activation_authorized"] is not False:e.append("activation gate may not pass")
    dby={x["id"]:x for x in delays["delays"]}
    for did in ("credit_risk_recognition_delay","credit_supply_adjustment_delay"):
        if dby[did]["current_tau"]!="TBD" or dby[did]["scalar_tau_activation_ready"] is not False:e.append(f"{did}: scalar tau may not be ready")
    mby={x["id"]:x for x in mechanisms["mechanisms"]}
    if mby["aggregate_bank_credit_response"]["classification"]!="CANDIDATE":e.append("aggregate bank-credit classification changed")
    if mby["credit_risk_npl_response"]["classification"]!="DEFERRED":e.append("credit-risk classification changed")
    if aggregate_review["disposition"]["active_calibration_cycle_open"] is not False:e.append("aggregate calibration cycle opened")
    if risk_review["source_admissibility"]["registered_full_form_admissible"] is not False:e.append("credit-risk form unexpectedly admissible")
    for k,v in a["no_further_current_evidence_task_findings"].items():
        if k!="interpretation" and v is not False:e.append(f"terminal finding may not authorize {k}")
    disp=a["disposition"]
    if disp["structural_review_complete"] is not True or disp["current_operational_state"]!="EVIDENCE_TRIGGERED_HOLD" or disp["active_empirical_task"] is not None:e.append("terminal disposition changed")
    for k in ("exact_integrated_equation_ready","parameter_estimation_authorized","feedback_activation_authorized","behavioural_closure_authorized","public_version_change_authorized","qualitative_topology_changed"):
        if disp[k] is not False:e.append(f"terminal may not promote {k}")
    nxt=a["next_state"]
    if nxt["id"]!=HOLD_ID or nxt["authorization"]!="NO_ACTIVE_TASK_UNTIL_DECLARED_REOPEN_TRIGGER" or nxt["reopen_trigger_required"] is not True:e.append("hold state changed")
    for k in ("may_poll_unchanged_sources","may_estimate_parameters","may_open_holdout","may_activate_feedback","may_change_behavioural_closure","may_relax_existing_gates"):
        if nxt[k] is not False:e.append(f"hold may not authorize {k}")
    dc=model["dynamic_core"]
    if dc.get("bank_credit_balance_sheet_loop_terminal_assessment")!=ASSESSMENT_PATH:e.append("model terminal pointer missing")
    if dc.get("bank_credit_balance_sheet_loop_structural_review_status")!=STATUS:e.append("model terminal status changed")
    if dc.get("bank_credit_balance_sheet_loop_operational_state")!="EVIDENCE_TRIGGERED_HOLD":e.append("model operational state changed")
    if dc.get("bank_credit_balance_sheet_loop_active_empirical_task") is not None:e.append("model active task must be null")
    if dc.get("bank_credit_balance_sheet_next_structural_task")!=HOLD_ID:e.append("model next-state pointer changed")
    if dc["behavioural_closure_active"] is not False:e.append("behavioural closure changed")
    if baseline["authority"].get("bank_credit_balance_sheet_loop_terminal_assessment")!=ASSESSMENT_PATH:e.append("baseline authority missing")
    return e
def main():
    errors=audit_bank_credit_loop_terminal(load(ASSESSMENT_PATH),load("model/dynamics/feedback_registry.json"),load("model/dynamics/feedback_link_readiness_registry.json"),load("model/dynamics/feedback_variable_boundary_registry.json"),load("model/dynamics/feedback_activation_criteria_matrix.json"),load("model/dynamics/delay_evidence_registry.json"),load("model/empirical_dynamics/mechanism_registry.json"),load("model/calibration_validation/aggregate_bank_credit_source_boundary_review.json"),load("model/calibration_validation/credit_risk_npl_source_boundary_review.json"),load("model/registries/model_contract.json"),load("model/registries/scientific_baseline_manifest.json"))
    if errors:raise RuntimeError("Bank-credit loop terminal assessment failed:\n- "+"\n- ".join(errors))
    print(json.dumps({"status":"PASS","terminal_status":STATUS,"exact_integrated_link_forms_ready":0,"activation_status":"BLOCKED","operational_state":"EVIDENCE_TRIGGERED_HOLD","active_empirical_task":None,"feedback_activation_authorized":False},indent=2))
if __name__=="__main__":main()
