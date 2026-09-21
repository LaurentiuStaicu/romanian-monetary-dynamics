from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ASSESSMENT="model/accounting/f2_direct_investment_instrument_dissemination_diagnostic_2026_09_21.json"

def load(path:str)->dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def audit_f2_direct_investment_instrument_dissemination()->list[str]:
    errors=[]
    a=load(ASSESSMENT)
    bridge=load("model/accounting/f21_bpm6_esa_concept_bridge_assessment.json")
    reopen=load("model/accounting/reopen_conditions_registry.json")

    if a["decision"]!="NO_REOPEN_STANDARD_DIRECT_INVESTMENT_DISSEMINATION_DOES_NOT_IDENTIFY_F2_SUBINSTRUMENT":
        errors.append("F2 dissemination diagnostic decision changed")
    if bridge["verdict"]!="BLOCKED_DIRECT_INVESTMENT_F2_SUBINSTRUMENT_NOT_DISSEMINATED":
        errors.append("F2 governing bridge state changed")
    result=bridge["result"]
    if result["direct_investment_F2"]["MIO_NAC_available_for_required_sectors"] is not False:
        errors.append("Direct-Investment F2 unexpectedly became available in predecessor")
    if result["direct_investment_F2"]["MIO_EUR_available_for_required_sectors"] is not False:
        errors.append("Direct-Investment F2 unexpectedly became available in predecessor")
    if result["concept_bridge_pass"] is not False:
        errors.append("blocked F2 concept bridge was rewritten")

    adj=a["adjudication"]
    for key in (
        "standard_BPM6_BOP_IIP_route_can_identify_DI_F2",
        "broad_DI_debt_is_exact_F2_substitute",
        "residual_gap_is_exact_F2_substitute",
        "current_public_evidence_of_Romania_DI_F2_2025",
        "reopen_trigger_satisfied",
    ):
        if adj[key] is not False:
            errors.append(f"F2 negative dissemination boundary relaxed: {key}")

    if a["search_boundary"]["standard_BPM6_BOP_IIP_presentations"]!="EXHAUSTED_FOR_DI_F2_SUBINSTRUMENT":
        errors.append("standard BPM6 search boundary changed")
    if a["search_boundary"]["standard_Eurostat_bop_iip_route"]!="EXHAUSTED_FOR_DI_F2_SUBINSTRUMENT":
        errors.append("Eurostat standard search boundary changed")
    if a["search_boundary"]["standard_BNR_public_IIP_presentation"]!="EXHAUSTED_FOR_DI_F2_SUBINSTRUMENT":
        errors.append("BNR standard search boundary changed")

    for key,value in a["scientific_effect"].items():
        if value is not False:
            errors.append(f"F2 diagnostic may not authorize {key}")

    f2=reopen["instruments"]["F2"]
    if f2.get("standard_dissemination_diagnostic")!=ASSESSMENT:
        errors.append("F2 registry lacks dissemination diagnostic")
    if f2.get("standard_bop_iip_route_state")!="CLOSED_FOR_DI_F2_SUBINSTRUMENT":
        errors.append("F2 standard BOP/IIP route state is stale")
    required="standard Direct-Investment debt-instruments aggregates without an instrument-specific currency-and-deposits split"
    if required not in f2["evidence_that_does_not_reopen"]:
        errors.append("F2 registry does not block broad DI debt aggregate substitution")
    return errors

def main():
    errors=audit_f2_direct_investment_instrument_dissemination()
    if errors:
        raise RuntimeError("F2 dissemination diagnostic audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "decision":"NO_REOPEN_STANDARD_DI_DISSEMINATION_DOES_NOT_IDENTIFY_F2",
        "F2M":"UNCHANGED_MATERIALIZED",
        "F21":"UNCHANGED_UNRESOLVED",
        "total_F2":"UNCHANGED_INCOMPLETE",
        "standard_BOP_IIP_route":"CLOSED_FOR_DI_F2_SUBINSTRUMENT"
    },indent=2))

if __name__=="__main__": main()
