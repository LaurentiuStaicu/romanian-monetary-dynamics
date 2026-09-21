from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTRACT="model/accounting/f8_oecd_counterpart_reopen_contract_2026_09_21.json"
ASSESSMENT="model/accounting/f8_oecd_counterpart_reopen_assessment_2026_09_21.json"

def load(path:str)->dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def audit_f8_oecd_counterpart_reopen()->list[str]:
    errors=[]
    c=load(CONTRACT); a=load(ASSESSMENT)
    source=load("model/dynamics/sectoral_financial_positions_oecd_counterpart_discovery_assessment.json")
    rank=load("model/accounting/f8_aggregate_rank_assessment.json")
    reopen=load("model/accounting/reopen_conditions_registry.json")
    if a["decision"]!="PASS_F8_REOPEN_TRIGGER_OECD_COUNTERPART_STAGE2_PREREGISTERED": errors.append("F8 OECD reopen decision changed")
    if a["topology_only_review"] is not True or a["detailed_value_review_performed"] is not False or a["rank_recomputation_performed"] is not False: errors.append("F8 reopen assessment must remain topology-only")
    disc=source["discovery_result"]; src=c["source"]
    if disc["artifact_id"]!=src["retained_workflow_artifact_id"]: errors.append("OECD artifact lineage changed")
    if disc["stocks_raw_sha256"]!=src["stocks_raw_sha256"]: errors.append("OECD stock raw hash changed")
    if disc["flows_raw_sha256"]!=src["flows_raw_sha256"]: errors.append("OECD flow raw hash changed")
    if c["topology_trigger"]["exact_total_present"]!="F8": errors.append("F8 total topology missing")
    if set(c["topology_trigger"]["exact_components_present"])!={"F81","F89"}: errors.append("F8 component topology changed")
    if c["topology_trigger"]["central_bank_sector_S121_present"] is not False: errors.append("F8 contract may not invent S121")
    if c["topology_trigger"]["observed_maturity_code"]!="T": errors.append("F8 observed maturity topology changed")
    if c["frozen_mapping"]["S12"]!="F + BNR aggregate only": errors.append("F8 S12 boundary relaxed")
    if c["stage2_gate"]["reconciliation"]["tolerance_million_RON"]!="0.1": errors.append("F8 Stage 2 tolerance changed")
    if c["hard_rules"]["no_conditional_BNR_zero_promotion"] is not True: errors.append("F8 conditional BNR zero may not be promoted")
    if rank["unconditional_identification"]["stock"]["rank"]!=11 or rank["unconditional_identification"]["stock"]["nullity"]!=24: errors.append("F8 predecessor stock rank changed")
    if rank["unconditional_identification"]["flow"]["rank"]!=11 or rank["unconditional_identification"]["flow"]["nullity"]!=24: errors.append("F8 predecessor flow rank changed")
    if rank["unconditional_identification"]["stock"]["unique_cell_count"]!=0 or rank["unconditional_identification"]["flow"]["unique_cell_count"]!=0: errors.append("F8 predecessor uniqueness changed")
    if rank["conditional_stock_BNR_zero_scenario"]["promoted"] is not False: errors.append("historical conditional BNR zeros were promoted")
    f8=reopen["instruments"]["F8"]
    if f8.get("selective_reopen_contract")!=CONTRACT: errors.append("F8 registry lacks Stage 2 contract")
    if f8.get("selective_reopen_assessment")!=ASSESSMENT: errors.append("F8 registry lacks topology assessment")
    if f8.get("selective_reopen_state")!="PREREGISTERED_STAGE2_PENDING_EXECUTION": errors.append("F8 selective reopen state stale")
    if f8.get("reopen_trigger_satisfied") is not True: errors.append("F8 trigger not registered")
    if a["adjudication"]["accounting_readiness_change"] is not False or a["adjudication"]["F8_materialization_change"] is not False: errors.append("F8 topology reopen may not change readiness/materialization")
    if a["adjudication"]["conditional_BNR_zero_stock_promotion"] is not False: errors.append("F8 topology reopen may not promote conditional BNR zeros")
    return errors

def main():
    errors=audit_f8_oecd_counterpart_reopen()
    if errors: raise RuntimeError("F8 OECD counterpart reopen audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({"status":"PASS","trigger":"OECD_F8_COUNTERPART_PUBLICATION","stage2":"PREREGISTERED_PENDING_EXECUTION","base_rank_stock":11,"base_rank_flow":11,"accounting_readiness_changed":False},indent=2))

if __name__=="__main__": main()
