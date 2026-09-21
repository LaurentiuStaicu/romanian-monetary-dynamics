from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
A=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_10m_threshold_assessment_2026_09_21.json"
C=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_10m_horizontal_gate_contract_2026_09_21.json"
M=ROOT/"model/registries/model_contract.json"

def audit_ecb_qfa_10m_preregistration():
    e=[]; a=json.loads(A.read_text()); c=json.loads(C.read_text()); m=json.loads(M.read_text())
    if a["decision"]!="PASS_OFFICIAL_DOMAIN_SPECIFIC_QFA_INTERNAL_CONSISTENCY_THRESHOLD_NEW_PER_INSTRUMENT_GATE_AUTHORIZED":
        e.append("threshold assessment decision changed")
    if any(x["threshold_eur_million"]!=10 for x in a["official_evidence"]):
        e.append("official ECB threshold changed")
    ap=a["applicability"]
    if ap["applies_per_instrument"] is not True or ap["aggregate_across_F2_F8_only_is_insufficient"] is not True:
        e.append("horizontal-consistency applicability changed")
    if a["conservative_currency_bridge"]["strict_sufficient_bound_million_ron"]!=10:
        e.append("strict sufficient RON bound changed")
    g=c["official_threshold_gate"]
    if g["ecb_threshold_eur_million"]!="10" or g["first_stage_strict_sufficient_bound_million_ron"]!="10":
        e.append("gate threshold changed")
    if c["source_boundary"]["instruments"]!=["F2","F3","F4","F5","F6","F7","F8"]:
        e.append("instrument boundary changed")
    if not all(c["hard_rules"].values()):
        e.append("a hard rule was disabled")
    if m["dynamic_core"]["reference_mode_ready_count"]!=9 or m["dynamic_core"]["reference_mode_required_count"]!=10:
        e.append("preregistration may not change readiness")
    if m["dynamic_core"]["sectoral_financial_positions_reference_mode_status"]!="PARTIAL_SERIES_AVAILABLE":
        e.append("preregistration may not promote sectoral mode")
    return e

def main():
    errors=audit_ecb_qfa_10m_preregistration()
    if errors: raise RuntimeError("ECB QFA 10m preregistration audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({"status":"PASS","ecb_threshold_eur_million":10,"test_level":"PER_INSTRUMENT","strict_sufficient_bound_million_ron":10,"reference_modes_ready":"9/10"},indent=2))
if __name__=="__main__": main()
