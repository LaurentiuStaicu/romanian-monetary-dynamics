from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
E=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_10m_horizontal_gate_execution_assessment_2026_09_21.json"
C=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_10m_horizontal_gate_contract_2026_09_21.json"
M=ROOT/"model/registries/model_contract.json"
R=ROOT/"model/dynamics/reference_modes.json"

def audit_execution_state():
    e=[]
    x=json.loads(E.read_text(encoding="utf-8"))
    c=json.loads(C.read_text(encoding="utf-8"))
    m=json.loads(M.read_text(encoding="utf-8"))
    r=json.loads(R.read_text(encoding="utf-8"))
    if x["scientific_gate_result"]!="PASS":
        e.append("ECB QFA 10m gate result changed")
    if x["gates"]["horizontal_test_count"]!=686:
        e.append("horizontal test count changed")
    if x["gates"]["strict_bound_exceedance_count"]!=0:
        e.append("strict sufficient bound has an exceedance")
    if x["gates"]["global_max_abs_residual_million_ron"]!="0.2":
        e.append("global per-instrument residual maximum changed")
    if any(v!="0.2" for v in x["gates"]["max_abs_residual_by_instrument_million_ron"].values()):
        e.append("per-instrument retained maxima changed")
    if x["official_fx_safety"]["pass"] is not True:
        e.append("ECB FX safety gate changed")
    if min(float(x["official_fx_safety"][k]["minimum_ron_per_eur"]) for k in ("quarterly_average","quarter_end"))<=1:
        e.append("ECB FX safety minimum no longer proves the strict sufficient bound")
    if x["disposition"]!="ECB_QFA_HORIZONTAL_CONSISTENCY_STRICT_SUFFICIENT_PASS_PROMOTION_ASSESSMENT_AUTHORIZED":
        e.append("gate disposition changed")
    if x["scientific_effect"]["reference_mode_promoted_by_this_assessment"] is not False:
        e.append("execution assessment may not itself promote the mode")
    if x["scientific_effect"]["readiness_count_change"]!=0:
        e.append("execution assessment may not change readiness")
    if not all(c["hard_rules"].values()):
        e.append("a preregistered hard rule was disabled")
    d=m["dynamic_core"]
    if d["reference_mode_ready_count"]!=10 or d["reference_mode_required_count"]!=10:
        e.append("current successor readiness must remain 10/10")
    mode=next(z for z in r["modes"] if z["id"]=="sectoral_financial_positions")
    if mode["status"]!="OBSERVED_SERIES_AVAILABLE":
        e.append("current successor sectoral mode must remain observed")
    if d.get("reference_mode_post_terminal_promotion_assessment")!="model/dynamics/reference_mode_post_terminal_promotion_assessment_2026_09_21.json":
        e.append("current promotion must remain attributable to the separate successor assessment")
    return e

def main():
    errors=audit_execution_state()
    if errors: raise RuntimeError("ECB QFA 10m execution-state audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({"status":"PASS","horizontal_tests":686,"strict_bound_exceedances":0,"max_abs_residual_million_ron":0.2,"promotion_assessment_authorized":True,"reference_modes_ready":"10/10"},indent=2))
if __name__=="__main__": main()
