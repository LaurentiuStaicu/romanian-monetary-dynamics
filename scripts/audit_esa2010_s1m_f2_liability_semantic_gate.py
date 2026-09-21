from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
A=ROOT/"model/dynamics/sectoral_financial_positions_esa2010_s1m_f2_liability_semantic_assessment_2026_09_21.json"
C=ROOT/"model/dynamics/sectoral_financial_positions_oecd_semantic_adjusted_exact_gate_contract_2026_09_21.json"

def audit_semantic_gate() -> list[str]:
    e=[]; a=json.loads(A.read_text(encoding="utf-8")); c=json.loads(C.read_text(encoding="utf-8"))
    if a["decision"]!="PASS_INDEPENDENT_ESA2010_SEMANTIC_APPLICABILITY_S1M_L_F2_STRUCTURAL_ZERO_AUTHORIZED_FOR_ONE_NEW_PREREGISTERED_AGGREGATE_GATE":
        e.append("semantic decision changed")
    j=a["adjudication"]
    if j["conclusion"]!="STRUCTURALLY_NOT_APPLICABLE_ON_ESA2010_S1M_L_F2_BOUNDARY":
        e.append("semantic applicability conclusion changed")
    for k in ("currency_component_F21_liability_applicable_to_S1M","deposit_components_F22_F29_liability_applicable_to_S1M","overdraft_exception_creates_F2_liability"):
        if j[k] is not False: e.append(f"semantic applicability relaxed: {k}")
    if j["permitted_reconstruction_treatment"]!="STRUCTURAL_ZERO_BY_NORMATIVE_SEMANTICS":
        e.append("semantic treatment changed")
    for k in ("treatment_is_missing_to_zero","treatment_is_imputation","treatment_is_residual_allocation","treatment_is_post_result_empirical_inference"):
        if j[k] is not False: e.append(f"semantic treatment misclassified: {k}")
    if a["independence_from_prior_result"]["prior_result_used_to_infer_semantics"] is not False:
        e.append("semantic assessment may not depend on prior missingness")
    if a["scientific_effect"]["reference_mode_promoted"] is not False or a["scientific_effect"]["readiness_count_change"]!=0:
        e.append("semantic assessment may not promote readiness")
    x=c["semantic_exception"]
    if x["exact_key_pattern"]!={"source_sector":"S1M","accounting_entry":"L","instrument":"F2"}:
        e.append("semantic exception scope changed")
    if x["value_million_ron"]!=0.0 or x["requires_source_row"] is not False:
        e.append("semantic-zero rule changed")
    if x["may_override_present_nonzero_row"] is not False:
        e.append("semantic exception may not override provider row")
    if not all(c["hard_rules"].values()):
        e.append("a semantic-adjusted hard rule was disabled")
    return e

def main():
    errors=audit_semantic_gate()
    if errors: raise RuntimeError("ESA2010 semantic gate audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({"status":"PASS","semantic_key":"S1M/L/F2","treatment":"STRUCTURAL_ZERO_BY_NORMATIVE_SEMANTICS","reference_mode_promotion":False},indent=2))

if __name__=="__main__":
    main()
