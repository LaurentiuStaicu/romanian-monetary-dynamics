from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

def load(path:str)->dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def audit_accounting_spine_recovery_terminal()->list[str]:
    errors=[]
    readiness=load("model/accounting/accounting_readiness_gate.json")
    assessment_path=readiness["accounting_recovery_terminal_assessment"]
    a=load(assessment_path)
    reopen=load("model/accounting/reopen_conditions_registry.json")

    if a["decision"]!="ACCOUNTING_SPINE_RECOVERY_STAGE_COMPLETE_EVIDENCE_TRIGGERED_HOLD":
        errors.append("terminal accounting recovery decision changed")

    expected=readiness["current_expected_state"]
    term=a["terminal_state"]
    if set(term["complete_instruments"])!=set(expected["canonical_complete_stock_and_flow_instruments"]):
        errors.append("terminal complete instruments disagree with readiness gate")
    if set(term["incomplete_instruments"])!=set(expected["canonical_incomplete_instruments"]):
        errors.append("terminal incomplete instruments disagree with readiness gate")
    if term["canonical_multi_instrument_stock_initialization_ready"] is not expected["canonical_multi_instrument_stock_initialization_ready"]:
        errors.append("terminal stock initialization readiness is stale")
    if term["canonical_full_2025_stock_flow_benchmark_ready"] is not expected["canonical_full_2025_stock_flow_benchmark_ready"]:
        errors.append("terminal full benchmark readiness is stale")
    if term["active_selective_reopen_instruments"]!=[]:
        errors.append("terminal accounting recovery may not retain an active selective reopen")
    if term["active_unconditional_accounting_recovery_task"] is not None:
        errors.append("terminal accounting recovery may not retain an unconditional task")
    if term["next_operational_state"]!="EVIDENCE_TRIGGERED_ACCOUNTING_SPINE_HOLD":
        errors.append("terminal next operational state changed")

    if set(reopen["current_complete_instruments"])!=set(term["complete_instruments"]):
        errors.append("reopen registry complete set disagrees with terminal assessment")
    if set(reopen["current_incomplete_instruments"])!=set(term["incomplete_instruments"]):
        errors.append("reopen registry incomplete set disagrees with terminal assessment")

    dispositions=a["instrument_dispositions"]
    for inst in term["incomplete_instruments"]:
        if inst not in dispositions:
            errors.append(f"terminal assessment lacks disposition for {inst}")
            continue
        reg=reopen["instruments"][inst]
        if dispositions[inst]["status"]!=reg["current_status"]:
            errors.append(f"{inst} terminal status disagrees with reopen registry")
        if dispositions[inst]["current_reopen_gate_open"] is not False:
            errors.append(f"{inst} terminal disposition claims open gate")
        if reg.get("current_reopen_gate_open",False) is not False:
            errors.append(f"{inst} registry retains an open selective reopen gate")
        trigger=reg.get("reopen_when")
        if not trigger:
            errors.append(f"{inst} lacks reopen trigger")
        for path in dispositions[inst]["terminal_evidence"]:
            if not (ROOT/path).is_file():
                errors.append(f"{inst} terminal evidence missing: {path}")

    if reopen["instruments"]["F2"].get("standard_bop_iip_route_state")!="CLOSED_FOR_DI_F2_SUBINSTRUMENT":
        errors.append("F2 standard dissemination route is not closed")
    for inst in ("F5","F6","F7","F8"):
        state=reopen["instruments"][inst].get("selective_reopen_state")
        if not state or "RETURNED_TO_HOLD" not in state:
            errors.append(f"{inst} selective reopen has not returned to hold")
        if reopen["instruments"][inst].get("reopen_trigger_satisfied") is not True:
            errors.append(f"{inst} historical reopen trigger state was lost")

    rules=a["stage_completion_rule"]
    for key,value in rules.items():
        if value is not True:
            errors.append(f"terminal stage completion rule is false: {key}")

    nonclaims=a["scientific_nonclaims"]
    for key,value in nonclaims.items():
        if value is not False:
            errors.append(f"terminal assessment overclaims {key}")

    if a["version_effect"]["version_bump_authorized"] is not False:
        errors.append("terminal accounting recovery may not authorize version bump")

    if reopen.get("accounting_recovery_stage_status")!="STAGE_COMPLETE_EVIDENCE_TRIGGERED_HOLD":
        errors.append("reopen registry lacks terminal accounting recovery stage status")
    if reopen.get("accounting_recovery_terminal_assessment")!=assessment_path:
        errors.append("reopen registry does not register terminal assessment")
    if readiness.get("accounting_recovery_terminal_assessment")!=assessment_path:
        errors.append("readiness gate does not register terminal assessment")
    return errors

def main():
    errors=audit_accounting_spine_recovery_terminal()
    if errors:
        raise RuntimeError("Accounting Spine terminal recovery audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "decision":"ACCOUNTING_SPINE_RECOVERY_STAGE_COMPLETE_EVIDENCE_TRIGGERED_HOLD",
        "complete_instruments":["F3"],
        "incomplete_instruments":["F2","F4","F5","F6","F7","F8"],
        "active_selective_reopen_instruments":[],
        "full_2025_stock_flow_benchmark_ready":False
    },indent=2))

if __name__=="__main__":
    main()
