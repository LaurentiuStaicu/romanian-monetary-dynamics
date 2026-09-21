from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
S=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_materiality_scope_assessment_2026_09_21.json"
C=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_materiality_gate_contract_2026_09_21.json"
M=ROOT/"model/registries/model_contract.json"

def audit_ecb_materiality_preregistration() -> list[str]:
    e=[]
    s=json.loads(S.read_text(encoding="utf-8"))
    c=json.loads(C.read_text(encoding="utf-8"))
    m=json.loads(M.read_text(encoding="utf-8"))
    if s["decision"]!="PASS_AUTHORIZE_ONE_PREREGISTERED_ECB_MATERIALITY_ACCEPTABILITY_GATE":
        e.append("ECB materiality scope decision changed")
    a=s["scope_adjudication"]
    if a["romania_is_in_scope"] is not True or a["threshold_eur_million"]!=10:
        e.append("Romania/threshold scope changed")
    if a["rule_is_independent_of_rmd_observed_residuals"] is not True:
        e.append("materiality rule must remain independent of observed residuals")
    b=s["scientific_boundary"]
    if b["may_reassess_aggregate_reference_mode_acceptability"] is not True:
        e.append("aggregate acceptability gate not authorized")
    for k in ("may_rewrite_historical_rmd_0_1m_gate","may_change_accounting_spine_readiness","may_relax_canonical_accounting_identity","may_activate_behavioural_closure","may_estimate_parameters"):
        if b[k] is not False: e.append(f"scope improperly authorizes {k}")
    if c["currency_sufficiency_rule"]["conservative_local_threshold_ron"]!=10000000:
        e.append("conservative RON threshold changed")
    if c["currency_sufficiency_rule"]["required_condition"]!="Every official quarterly RON-per-EUR rate must be > 1.":
        e.append("FX sufficiency condition changed")
    if not all(c["hard_rules"].values()):
        e.append("a materiality-gate hard rule was disabled")
    dc=m["dynamic_core"]
    if dc["reference_mode_ready_count"]!=9 or dc["reference_mode_required_count"]!=10:
        e.append("readiness may not change before live gate")
    if dc["sectoral_financial_positions_reference_mode_status"]!="PARTIAL_SERIES_AVAILABLE":
        e.append("reference mode may not be promoted before live gate")
    return e

def main():
    errors=audit_ecb_materiality_preregistration()
    if errors:
        raise RuntimeError("ECB QFA materiality preregistration audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({"status":"PASS","official_threshold_eur_million":10,"conservative_gate_ron_million":10,"romania_in_scope":True,"reference_modes_ready":"9/10"},indent=2))

if __name__=="__main__":
    main()
