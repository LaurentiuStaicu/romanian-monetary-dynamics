from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
T=ROOT/"model/dynamics/sectoral_financial_positions_oecd_semantic_adjusted_terminal_assessment_2026_09_21.json"
C=ROOT/"model/dynamics/sectoral_financial_positions_oecd_semantic_adjusted_exact_gate_contract_2026_09_21.json"
R=ROOT/"model/dynamics/reference_modes.json"
M=ROOT/"model/registries/model_contract.json"
A=ROOT/"model/accounting/accounting_readiness_gate.json"

def load(p): return json.loads(p.read_text(encoding="utf-8"))

def audit_semantic_terminal():
    e=[]; t=load(T); c=load(C); r=load(R); m=load(M); a=load(A)
    if t["verdict"]!="FAIL_FROZEN_RECONCILIATION_TOLERANCE_NO_PROMOTION_SEMANTIC_PATH_CLOSED":
        e.append("terminal semantic-adjusted verdict changed")
    if t["row_gate"]["pass"] is not True:
        e.append("row gate must remain passed")
    v=t["value_gate"]
    if v["numeric_observation_value_review_performed"] is not True or v["finite_value_gate_pass"] is not True:
        e.append("terminal value-gate state changed")
    g=t["reconciliation_gate"]
    if g["performed"] is not True or g["frozen_tolerance_million_ron"]!=0.1:
        e.append("frozen reconciliation gate changed")
    if g["violation_count"]!=63 or g["flow_violation_count"]!=27 or g["stock_violation_count"]!=36:
        e.append("reconciliation violation counts changed")
    if abs(g["max_abs_flow_residual_million_ron"]-0.5000000000075033)>1e-12:
        e.append("flow residual maximum changed")
    if abs(g["max_abs_stock_residual_million_ron"]-0.5999999999476131)>1e-12:
        e.append("stock residual maximum changed")
    if t["precision_context"]["tolerance_relaxation_authorized"] is not False:
        e.append("post-result tolerance relaxation may not be authorized")
    s=t["scientific_effect"]
    if s["reference_mode_status"]!="PARTIAL_SERIES_AVAILABLE" or s["readiness_count_change"]!=0:
        e.append("reference mode may not be promoted")
    for k in ("accounting_readiness_change","parameter_estimation_authorized","feedback_activation_authorized","behavioural_closure_authorized"):
        if s[k] is not False: e.append(f"terminal assessment may not authorize {k}")
    er=c["execution_result"]
    if er["result"]!="FAIL_FROZEN_RECONCILIATION_TOLERANCE_NO_PROMOTION" or er["tolerance_relaxation_authorized"] is not False:
        e.append("contract execution result changed")
    mode=next(x for x in r["modes"] if x["id"]=="sectoral_financial_positions")
    if mode["status"]!="OBSERVED_SERIES_AVAILABLE":
        e.append("current successor reference mode must be observed")
    dc=m["dynamic_core"]
    if dc["reference_mode_ready_count"]!=10 or dc["reference_mode_required_count"]!=10:
        e.append("current successor reference-mode readiness must be 10/10")
    if dc["sectoral_financial_positions_reference_mode_promotion_authorized"] is not False:
        e.append("model contract may not authorize promotion")
    st=m["scientific_stage"]
    if st.get("post_terminal_semantic_reopen_task") is not None:
        e.append("semantic task must be closed")
    if st.get("post_terminal_semantic_reopen_status")!="EXECUTED_FAIL_RETURNED_TO_BASELINE_HOLD":
        e.append("semantic reopen terminal status changed")
    if st.get("next_operational_state")!="EVIDENCE_TRIGGERED_BASELINE_HOLD":
        e.append("model must return to baseline hold")
    if a["current_expected_state"]["canonical_complete_stock_and_flow_instruments"]!=["F3"]:
        e.append("Accounting Spine readiness changed")
    return e

def main():
    errors=audit_semantic_terminal()
    if errors:
        raise RuntimeError("Semantic-adjusted terminal audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "row_gate":"PASS",
        "finite_value_gate":"PASS",
        "reconciliation_gate":"FAIL",
        "frozen_tolerance_million_ron":0.1,
        "violation_count":63,
        "reference_modes_ready":"10/10",
        "sectoral_financial_positions":"OBSERVED_SERIES_AVAILABLE",
        "scientific_state":"EVIDENCE_TRIGGERED_BASELINE_HOLD"
    },indent=2))

if __name__=="__main__": main()
