from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
A=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_materiality_assessment_2026_09_21.json"
C=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_materiality_gate_contract_2026_09_21.json"
M=ROOT/"model/registries/model_contract.json"

def audit_ecb_materiality_preregistration():
    e=[]; a=json.loads(A.read_text()); c=json.loads(C.read_text()); m=json.loads(M.read_text())
    if a["decision"]!="PASS_OFFICIAL_ECB_QFA_10M_EUR_MATERIALITY_RULE_FOUND_AUTHORIZE_ONE_NEW_PREREGISTERED_INSTRUMENT_LEVEL_GATE":
        e.append("materiality assessment decision changed")
    j=a["adjudication"]
    if j["domain_specific_official_quantitative_rule_found"] is not True or j["rule_value_million_eur"]!=10:
        e.append("official materiality rule changed")
    for k in ("historical_0_1_million_ron_gate_rewritten","immediate_reference_mode_promotion_authorized","accounting_spine_reopen_authorized","parameter_estimation_authorized","feedback_activation_authorized","behavioural_closure_authorized"):
        if j[k] is not False: e.append(f"preregistration may not authorize {k}")
    if c["official_materiality_rule"]["threshold_million_eur"]!="10":
        e.append("contract threshold changed")
    if not all(c["hard_rules"].values()):
        e.append("a materiality-gate hard rule was disabled")
    dc=m["dynamic_core"]
    if dc["reference_mode_ready_count"]!=9 or dc["reference_mode_required_count"]!=10:
        e.append("readiness must remain 9/10 before execution")
    if dc["sectoral_financial_positions_reference_mode_status"]!="PARTIAL_SERIES_AVAILABLE":
        e.append("reference mode must remain partial before execution")
    return e

def main():
    errors=audit_ecb_materiality_preregistration()
    if errors: raise RuntimeError("ECB QFA materiality preregistration audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({"status":"PASS","official_threshold_million_eur":10,"reference_modes_ready":"9/10","live_gate":"PENDING"},indent=2))
if __name__=="__main__": main()
