from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ASSESSMENT="model/accounting/f4_bnr_cnf_2025_stock_trigger_monitoring_2026_09_21.json"

def load(path:str)->dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def audit_f4_bnr_cnf_2025_stock_trigger_monitoring()->list[str]:
    errors=[]
    a=load(ASSESSMENT)
    screening=load("model/dynamics/sectoral_financial_positions_bnr_cnf_source_screening.json")
    execution=load("model/accounting/f4_structural_zero_successor_materialization_assessment_2026_09_21.json")
    reopen=load("model/accounting/reopen_conditions_registry.json")

    if a["decision"]!="NO_REOPEN_MONITOR_BNR_CNF_2025_STOCK_COUNTERPART_PUBLICATION_TRIGGER":
        errors.append("F4 BNR CNF monitoring decision changed")
    if screening["observed_counterpart_matrix"]["period"]!="2024":
        errors.append("retained BNR CNF screened matrix period changed")
    sem=screening["semantic_review"]
    if sem["sector_mapping"]!="PASS_FOR_2024_STOCK_MATRIX":
        errors.append("BNR CNF stock sector mapping no longer passes")
    if sem["counterpart_orientation"]!="PASS_FOR_2024_STOCK_MATRIX":
        errors.append("BNR CNF stock counterpart orientation no longer passes")
    if sem["instrument_mapping_F2_F8"]!="PASS_FOR_2024_STOCK_MATRIX":
        errors.append("BNR CNF instrument mapping no longer passes")
    if sem["consolidation_boundary"]!="PASS_NON_CONSOLIDATED":
        errors.append("BNR CNF non-consolidated boundary changed")
    if execution["result"]["stock_rank"]!=31 or execution["result"]["stock_unique_cell_count"]!=25:
        errors.append("current F4 successor stock state changed")
    if execution["result"]["BNR_asset_counterpart_allocation_performed"] is not False:
        errors.append("BNR asset row was already allocated")
    if a["current_public_review"]["current_reopen_trigger_satisfied"] is not False:
        errors.append("BNR CNF 2025 stock trigger may not be marked satisfied")
    if a["current_public_review"]["absence_is_not_proof_of_nonpublication"] is not True:
        errors.append("monitoring assessment overstates web-search absence")
    trig=a["frozen_future_trigger"]
    if trig["authorized_effect_if_pass"]!="REOPEN_F4_STOCK_ONLY_EXACT_COUNTERPART_MATERIALIZATION_GATE":
        errors.append("future BNR CNF trigger scope changed")
    if trig["flow_reopen_authorized"] is not False or trig["aggregate_reference_mode_reopen_authorized"] is not False:
        errors.append("annual stock trigger may not reopen flow/reference mode")
    if a["monitoring_policy"]["current_state"]!="MONITOR_PUBLICATION_NO_REOPEN":
        errors.append("F4 BNR CNF monitoring state changed")
    if a["monitoring_policy"]["no_repeated_polling_before_new_publication_evidence"] is not True:
        errors.append("F4 monitoring must prohibit repeated polling without evidence")
    for key,value in a["scientific_effect"].items():
        if value is not False:
            errors.append(f"monitoring may not authorize {key}")
    f4=reopen["instruments"]["F4"]
    if f4.get("priority_stock_reopen_monitoring")!=ASSESSMENT:
        errors.append("F4 registry lacks BNR CNF 2025 monitoring assessment")
    if f4.get("priority_stock_reopen_trigger_id")!="BNR_CNF_2025_F4_CENTRAL_BANK_ASSET_COUNTERPART_STOCK_MATRIX":
        errors.append("F4 registry priority stock trigger is stale")
    if f4.get("current_reopen_gate_open") is not False:
        errors.append("monitoring may not open the F4 gate")
    return errors

def main():
    errors=audit_f4_bnr_cnf_2025_stock_trigger_monitoring()
    if errors:
        raise RuntimeError("F4 BNR CNF 2025 monitoring audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "current_state":"MONITOR_PUBLICATION_NO_REOPEN",
        "target":"BNR_CNF_2025_S121_AF4_COUNTERPART_STOCK",
        "earliest_evidence_window":"after 2026-10-31",
        "F4_stock_rank":31,
        "F4_stock_unique_cells":25,
        "reopen_gate_open":False
    },indent=2))

if __name__=="__main__": main()
