from __future__ import annotations
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
ASSESSMENT="model/accounting/accounting_spine_recovery_f4_structural_reopen_assessment_2026_09_21.json"

def load(path:str)->dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def audit_accounting_spine_f4_structural_reopen()->list[str]:
    errors=[]
    a=load(ASSESSMENT)
    terminal=load(a["predecessor_terminal_assessment"])
    structural=load(a["trigger_assessment"])
    readiness=load("model/accounting/accounting_readiness_gate.json")
    reopen=load("model/accounting/reopen_conditions_registry.json")
    baseline=load("model/registries/scientific_baseline_manifest.json")

    if terminal["decision"]!="ACCOUNTING_SPINE_RECOVERY_STAGE_COMPLETE_EVIDENCE_TRIGGERED_HOLD":
        errors.append("historical Accounting Spine terminal assessment changed")
    if structural["decision"]!="PASS_PROMOTE_BNR_F4_STOCK_ZERO_LIABILITY_PARTITION_TO_EXACT_STRUCTURAL_CONSTRAINT":
        errors.append("F4 structural trigger is not satisfied")
    if a["trigger_satisfied"] is not True:
        errors.append("successor reopen trigger is not satisfied")
    current=a["current_state"]
    if readiness.get("accounting_recovery_stage_status")!=current["accounting_recovery_stage_status"]:
        errors.append("readiness gate selective reopen status is stale")
    if readiness.get("next_operational_state")!=current["next_operational_state"]:
        errors.append("readiness gate next operational state is stale")
    if readiness.get("accounting_recovery_successor_reopen_assessment")!=ASSESSMENT:
        errors.append("readiness gate lacks successor reopen assessment")
    if reopen.get("accounting_recovery_stage_status")!=current["accounting_recovery_stage_status"]:
        errors.append("reopen registry selective reopen status is stale")
    if reopen.get("active_selective_reopen_instruments")!=["F4"]:
        errors.append("F4 is not the sole active accounting selective reopen")
    if reopen.get("active_unconditional_accounting_recovery_task")!=current["active_unconditional_accounting_recovery_task"]:
        errors.append("active F4 successor materialization task is stale")
    f4=reopen["instruments"]["F4"]
    if f4.get("current_status")!="PARTIAL_STRUCTURAL_ZERO_RANK_EXPANDED_PENDING_SUCCESSOR_MATERIALIZATION":
        errors.append("F4 current status is stale")
    if f4.get("current_reopen_gate_open") is not True:
        errors.append("F4 successor materialization gate is not open")
    if f4.get("current_stock_unique_cell_count")!=25:
        errors.append("F4 current stock unique-cell count is stale")
    acc=baseline["canonical_state"]["accounting"]
    if acc.get("recovery_stage_status")!=current["accounting_recovery_stage_status"]:
        errors.append("baseline accounting selective reopen status is stale")
    if acc.get("active_selective_reopen_instruments")!=["F4"]:
        errors.append("baseline does not register F4 selective reopen")
    if acc.get("active_unconditional_recovery_task")!=current["active_unconditional_accounting_recovery_task"]:
        errors.append("baseline F4 active task is stale")
    for key,value in a["scientific_effect"].items():
        if value is not False:
            errors.append(f"F4 reopen may not authorize {key}")
    return errors

def main():
    errors=audit_accounting_spine_f4_structural_reopen()
    if errors:
        raise RuntimeError("F4 post-terminal selective reopen audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({
      "status":"PASS",
      "stage":"SELECTIVE_REOPEN_F4_STRUCTURAL_ZERO_MATERIALIZATION_PENDING",
      "active_task":"F4_STRUCTURAL_ZERO_SUCCESSOR_MATERIALIZATION_GATE",
      "stock_unique_cells":25,
      "flow_unique_cells":15
    },indent=2))

if __name__=="__main__": main()
