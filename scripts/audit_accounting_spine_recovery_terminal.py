from __future__ import annotations

import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ASSESSMENT="model/accounting/accounting_spine_recovery_terminal_assessment_2026_09_21.json"
SUCCESSOR="model/accounting/accounting_spine_recovery_f4_structural_reopen_assessment_2026_09_21.json"

def load(path:str)->dict:
    return json.loads((ROOT/path).read_text(encoding="utf-8"))

def audit_accounting_spine_recovery_terminal()->list[str]:
    errors=[]
    a=load(ASSESSMENT)
    readiness=load("model/accounting/accounting_readiness_gate.json")
    reopen=load("model/accounting/reopen_conditions_registry.json")

    if a["decision"]!="ACCOUNTING_SPINE_RECOVERY_STAGE_COMPLETE_EVIDENCE_TRIGGERED_HOLD":
        errors.append("historical terminal accounting recovery decision changed")

    expected=readiness["current_expected_state"]
    term=a["terminal_state"]
    if set(term["complete_instruments"])!=set(expected["canonical_complete_stock_and_flow_instruments"]):
        errors.append("historical terminal complete instruments disagree with canonical readiness")
    if set(term["incomplete_instruments"])!=set(expected["canonical_incomplete_instruments"]):
        errors.append("historical terminal incomplete instruments disagree with canonical readiness")
    if term["canonical_multi_instrument_stock_initialization_ready"] is not expected["canonical_multi_instrument_stock_initialization_ready"]:
        errors.append("historical terminal stock initialization readiness changed")
    if term["canonical_full_2025_stock_flow_benchmark_ready"] is not expected["canonical_full_2025_stock_flow_benchmark_ready"]:
        errors.append("historical terminal full benchmark readiness changed")
    if term["active_selective_reopen_instruments"]!=[]:
        errors.append("historical terminal checkpoint was rewritten with an active reopen")
    if term["active_unconditional_accounting_recovery_task"] is not None:
        errors.append("historical terminal checkpoint was rewritten with an active task")
    if term["next_operational_state"]!="EVIDENCE_TRIGGERED_ACCOUNTING_SPINE_HOLD":
        errors.append("historical terminal next operational state changed")

    if set(reopen["current_complete_instruments"])!=set(term["complete_instruments"]):
        errors.append("current complete-instrument set changed across successor reopen")
    if set(reopen["current_incomplete_instruments"])!=set(term["incomplete_instruments"]):
        errors.append("current incomplete-instrument set changed across successor reopen")

    current_stage=reopen.get("accounting_recovery_stage_status")
    successor_active=current_stage=="SELECTIVE_REOPEN_F4_STRUCTURAL_ZERO_MATERIALIZATION_PENDING"

    dispositions=a["instrument_dispositions"]
    for inst in term["incomplete_instruments"]:
        if inst not in dispositions:
            errors.append(f"historical terminal assessment lacks disposition for {inst}")
            continue
        reg=reopen["instruments"][inst]
        if not (ROOT/dispositions[inst]["terminal_evidence"][0]).is_file():
            errors.append(f"{inst} historical terminal evidence is missing")
        if inst!="F4" or not successor_active:
            if dispositions[inst]["status"]!=reg["current_status"]:
                errors.append(f"{inst} current status differs without a registered successor")
            if reg.get("current_reopen_gate_open",False) is not False:
                errors.append(f"{inst} retains an unexpected open selective reopen gate")
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

    for key,value in a["stage_completion_rule"].items():
        if value is not True:
            errors.append(f"historical terminal stage completion rule is false: {key}")
    for key,value in a["scientific_nonclaims"].items():
        if value is not False:
            errors.append(f"historical terminal assessment overclaims {key}")
    if a["version_effect"]["version_bump_authorized"] is not False:
        errors.append("historical terminal accounting recovery may not authorize version bump")

    if reopen.get("accounting_recovery_terminal_assessment")!=ASSESSMENT:
        errors.append("reopen registry lost historical terminal assessment")
    if readiness.get("accounting_recovery_terminal_assessment")!=ASSESSMENT:
        errors.append("readiness gate lost historical terminal assessment")

    if successor_active:
        if not (ROOT/SUCCESSOR).is_file():
            errors.append("registered F4 successor reopen assessment is missing")
        else:
            successor=load(SUCCESSOR)
            if successor["predecessor_terminal_assessment"]!=ASSESSMENT:
                errors.append("F4 successor does not preserve terminal predecessor")
            if successor["decision"]!="PASS_POST_TERMINAL_F4_STRUCTURAL_ZERO_TRIGGER_SELECTIVE_REOPEN":
                errors.append("F4 successor reopen decision is stale")
        if reopen.get("accounting_recovery_successor_reopen_assessment")!=SUCCESSOR:
            errors.append("reopen registry lacks F4 successor assessment")
        if readiness.get("accounting_recovery_successor_reopen_assessment")!=SUCCESSOR:
            errors.append("readiness gate lacks F4 successor assessment")
        if reopen.get("active_selective_reopen_instruments")!=["F4"]:
            errors.append("F4 is not the sole active successor reopen")
        if reopen["instruments"]["F4"].get("current_reopen_gate_open") is not True:
            errors.append("F4 successor gate is not open")
    elif current_stage!="STAGE_COMPLETE_EVIDENCE_TRIGGERED_HOLD":
        errors.append("unsupported current Accounting Spine recovery stage")

    return errors

def main():
    errors=audit_accounting_spine_recovery_terminal()
    if errors:
        raise RuntimeError("Accounting Spine terminal/successor audit failed:\n- "+"\n- ".join(errors))
    reopen=load("model/accounting/reopen_conditions_registry.json")
    print(json.dumps({
        "status":"PASS",
        "historical_terminal_decision":"ACCOUNTING_SPINE_RECOVERY_STAGE_COMPLETE_EVIDENCE_TRIGGERED_HOLD",
        "current_stage":reopen["accounting_recovery_stage_status"],
        "complete_instruments":["F3"],
        "incomplete_instruments":["F2","F4","F5","F6","F7","F8"],
        "active_selective_reopen_instruments":reopen.get("active_selective_reopen_instruments",[]),
        "full_2025_stock_flow_benchmark_ready":False
    },indent=2))

if __name__=="__main__":
    main()
