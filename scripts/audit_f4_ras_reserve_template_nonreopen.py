from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ASSESSMENT="model/accounting/f4_ras_reserve_template_nonreopen_diagnostic_2026_09_22.json"

def load(path:str)->dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def audit_f4_ras_reserve_template_nonreopen()->list[str]:
    errors=[]
    a=load(ASSESSMENT)
    reopen=load("model/accounting/reopen_conditions_registry.json")
    f4_state=load("model/accounting/f4_structural_zero_successor_materialization_assessment_2026_09_21.json")
    monitor=load("model/accounting/f4_bnr_cnf_2025_stock_trigger_monitoring_2026_09_21.json")

    if a["decision"]!="NO_REOPEN_ECB_RAS_RESERVE_TEMPLATE_NOT_DEFINITIONALLY_COMPARABLE_OR_COUNTERPART_GRANULAR":
        errors.append("F4 RAS diagnostic decision changed")
    if a["candidate_source"]["observed_dimensions"]["frequency"]!="M":
        errors.append("RAS frequency boundary changed")
    if a["candidate_source"]["observed_dimensions"]["counterpart_sector"]!="S1Q":
        errors.append("RAS counterpart boundary changed")
    if a["candidate_source"]["observed_dimensions"]["functional_category"]!="RT":
        errors.append("RAS functional-category boundary changed")
    if a["candidate_source"]["observed_dimensions"]["currency_denominator"]!="X1":
        errors.append("RAS currency-denominator boundary changed")
    if a["candidate_source"]["observed_dimensions"]["valuation"]!="N":
        errors.append("RAS valuation boundary changed")

    q=a["canonical_QSA_comparison"]["observed_dimensions"]
    if q["frequency"]!="Q" or q["counterpart_sector"]!="S1":
        errors.append("canonical QSA comparison boundary changed")
    if q["currency_denominator"]!="_T" or q["valuation"]!="S":
        errors.append("canonical QSA currency/valuation comparison changed")

    if a["boundary_comparison"]["exact_concept_bridge_validated"] is not False:
        errors.append("RAS-to-QSA exact bridge may not be treated as validated")
    adj=a["adjudication"]
    for key in (
        "current_reopen_trigger_satisfied",
        "new_exact_stock_equations_authorized",
        "BNR_asset_row_allocation_authorized",
        "flow_reopen_authorized",
        "priority_BNR_CNF_2025_trigger_superseded",
    ):
        if adj[key] is not False:
            errors.append(f"F4 RAS diagnostic may not authorize {key}")

    if f4_state["result"]["stock_rank"]!=31:
        errors.append("current F4 stock rank changed")
    if f4_state["result"]["stock_unique_cell_count"]!=25:
        errors.append("current F4 stock uniqueness changed")
    if f4_state["result"]["flow_rank"]!=26:
        errors.append("current F4 flow rank changed")

    f4=reopen["instruments"]["F4"]
    if f4.get("reserve_template_nonreopen_diagnostic")!=ASSESSMENT:
        errors.append("F4 registry lacks RAS non-reopen diagnostic")
    expected="ECB RAS reserve-template F4 stocks with S1Q counterpart aggregation, foreign-currency-only scope and nominal valuation"
    if expected not in f4["evidence_that_does_not_reopen"]:
        errors.append("F4 registry does not block RAS reserve-template substitution")
    if f4.get("priority_stock_reopen_trigger_id")!=monitor["frozen_future_trigger"]["id"]:
        errors.append("F4 priority CNF trigger was displaced")
    if f4.get("current_reopen_gate_open") is not False:
        errors.append("F4 reopen gate must remain closed")

    for key,value in a["scientific_effect"].items():
        if value is not False:
            errors.append(f"F4 RAS diagnostic may not authorize {key}")
    return errors

def main():
    errors=audit_f4_ras_reserve_template_nonreopen()
    if errors:
        raise RuntimeError("F4 RAS reserve-template diagnostic audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "decision":"NO_REOPEN_RAS_NOT_COMPARABLE",
        "F4_stock_rank":31,
        "F4_stock_unique_cells":25,
        "F4_flow_rank":26,
        "priority_trigger":"BNR_CNF_2025_F4_CENTRAL_BANK_ASSET_COUNTERPART_STOCK_MATRIX"
    },indent=2))

if __name__=="__main__":
    main()
