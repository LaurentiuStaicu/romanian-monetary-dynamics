from __future__ import annotations
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTRACT="model/accounting/f6_oecd_counterpart_reopen_contract_2026_09_21.json"
ASSESSMENT="model/accounting/f6_oecd_counterpart_reopen_assessment_2026_09_21.json"

def load(path:str)->dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def audit_f6_oecd_counterpart_reopen()->list[str]:
    errors=[]
    c=load(CONTRACT); a=load(ASSESSMENT)
    source=load("model/dynamics/sectoral_financial_positions_oecd_counterpart_discovery_assessment.json")
    rank=load("model/accounting/f6_aggregate_rank_assessment.json")
    reopen=load("model/accounting/reopen_conditions_registry.json")
    if a["decision"]!="PASS_F6_REOPEN_TRIGGER_OECD_COUNTERPART_STAGE2_PREREGISTERED":
        errors.append("F6 OECD reopen decision changed")
    if a["topology_only_review"] is not True or a["detailed_value_review_performed"] is not False or a["rank_recomputation_performed"] is not False:
        errors.append("F6 reopen assessment must remain topology-only")
    disc=source["discovery_result"]; src=c["source"]
    if disc["artifact_id"]!=src["retained_workflow_artifact_id"]: errors.append("OECD artifact lineage changed")
    if disc["stocks_raw_sha256"]!=src["stocks_raw_sha256"]: errors.append("OECD stock raw hash changed")
    if disc["flows_raw_sha256"]!=src["flows_raw_sha256"]: errors.append("OECD flow raw hash changed")
    if c["topology_trigger"]["exact_total_present"]!="F6": errors.append("F6 total topology missing")
    if set(c["topology_trigger"]["exact_components_present"])!={"F61","F62","F63","F64","F65","F66"}:
        errors.append("F6 component topology changed")
    if c["topology_trigger"]["central_bank_sector_S121_present"] is not False: errors.append("F6 contract may not invent S121")
    if c["frozen_mapping"]["S12"]!="F + BNR aggregate only": errors.append("F6 S12 boundary relaxed")
    if c["stage2_gate"]["reconciliation"]["tolerance_million_RON"]!="0.1": errors.append("F6 Stage 2 tolerance changed")
    if c["hard_rules"]["no_BNR_residual_allocation"] is not True or c["hard_rules"]["no_post_result_tolerance_change"] is not True:
        errors.append("F6 hard anti-inference rules changed")
    if rank["unconditional_identification"]["stock"]["rank"]!=11 or rank["unconditional_identification"]["stock"]["nullity"]!=24:
        errors.append("F6 predecessor stock rank changed")
    if rank["unconditional_identification"]["flow_2025"]["rank"]!=11 or rank["unconditional_identification"]["flow_2025"]["nullity"]!=24:
        errors.append("F6 predecessor flow rank changed")
    if rank["unconditional_identification"]["stock"]["unique_cell_count"]!=0 or rank["unconditional_identification"]["flow_2025"]["unique_cell_count"]!=0:
        errors.append("F6 predecessor uniqueness was rewritten")
    f6=reopen["instruments"]["F6"]
    if f6.get("selective_reopen_contract")!=CONTRACT: errors.append("F6 registry lacks Stage 2 contract")
    if f6.get("selective_reopen_assessment")!=ASSESSMENT: errors.append("F6 registry lacks topology assessment")
    allowed={"PREREGISTERED_STAGE2_PENDING_EXECUTION","STAGE2_EXECUTED_FAIL_SOURCE_RECONCILIATION_RETURNED_TO_HOLD","STAGE2_EXECUTED_PASS_PENDING_MATERIALIZATION_DECISION"}
    if f6.get("selective_reopen_state") not in allowed: errors.append("F6 selective reopen state invalid")
    if f6.get("reopen_trigger_satisfied") is not True: errors.append("F6 trigger not registered")
    if a["adjudication"]["accounting_readiness_change"] is not False or a["adjudication"]["F6_materialization_change"] is not False:
        errors.append("F6 topology reopen may not change readiness/materialization")
    return errors

def main():
    errors=audit_f6_oecd_counterpart_reopen()
    if errors: raise RuntimeError("F6 OECD counterpart reopen audit failed:\n- "+"\n- ".join(errors))
    state=load("model/accounting/reopen_conditions_registry.json")["instruments"]["F6"]["selective_reopen_state"]
    print(json.dumps({"status":"PASS","trigger":"OECD_F6_COUNTERPART_PUBLICATION","stage2":state,"base_rank_stock":11,"base_rank_flow":11,"accounting_readiness_changed":False},indent=2))

if __name__=="__main__": main()
