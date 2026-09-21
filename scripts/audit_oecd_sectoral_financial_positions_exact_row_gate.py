from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
ASSESSMENT=ROOT/"model/dynamics/sectoral_financial_positions_oecd_exact_row_gate_assessment_2026_09_21.json"
MISSING=ROOT/"data/source_vintages/oecd-nonconsolidated-sectoral-financial-positions-row-gate-2026-09-21/missing_required_rows.csv"
MANIFEST=ROOT/"data/source_vintages/oecd-nonconsolidated-sectoral-financial-positions-row-gate-2026-09-21/source_vintage_manifest.json"
PUBLIC=ROOT/"model/dynamics/bnr_2025_financial_accounts_public_access_recovery_contract.json"
REFERENCE=ROOT/"model/dynamics/reference_modes.json"
MODEL=ROOT/"model/registries/model_contract.json"
ACCOUNTING=ROOT/"model/accounting/accounting_readiness_gate.json"

def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))

def quarter_range(start_y=2014,start_q=1,end_y=2026,end_q=1):
    out=[]; y=start_y; q=start_q
    while (y,q) <= (end_y,end_q):
        out.append(f"{y:04d}-Q{q}")
        q+=1
        if q==5:
            y+=1; q=1
    return out

def audit_oecd_exact_row_gate() -> list[str]:
    e=[]
    a=load(ASSESSMENT); m=load(MANIFEST); p=load(PUBLIC); rm=load(REFERENCE); model=load(MODEL); acc=load(ACCOUNTING)

    if a["verdict"]!="FAIL_EXACT_REQUIRED_ROW_COVERAGE_S1M_L_F2_MISSING_ALL_PERIODS_NO_VALUE_REVIEW_NO_PROMOTION":
        e.append("terminal exact-row verdict changed")
    g=a["exact_row_gate"]
    if g["periods"]!=49 or g["period_start"]!="2014-Q1" or g["period_end"]!="2026-Q1":
        e.append("frozen row-gate period coverage changed")
    if g["missing_required_rows_total"]!=98 or g["duplicate_required_rows_total"]!=0:
        e.append("terminal missing/duplicate counts changed")
    pat=g["missing_pattern"]
    if (pat["source_sector"],pat["accounting_entry"],pat["instrument"])!=("S1M","L","F2"):
        e.append("terminal missing-key pattern changed")
    if pat["flow_missing_periods"]!=49 or pat["stock_missing_periods"]!=49 or pat["missing_every_period"] is not True:
        e.append("terminal missing-key period coverage changed")
    if a["numeric_observation_value_review_performed"] is not False:
        e.append("numeric values may not have been reviewed after row-gate failure")
    if a["reconciliation_test_performed"] is not False:
        e.append("reconciliation may not run after row-gate failure")
    if a["preregistered_stop_rule_applied"] is not True:
        e.append("preregistered stop rule must remain applied")

    rows=list(csv.DictReader(MISSING.open(encoding="utf-8")))
    if len(rows)!=98:
        e.append(f"retained missing-row evidence count changed: {len(rows)}")
    expected={(measure,period,"S1M","L","F2") for measure in ("flow","stock") for period in quarter_range()}
    observed={(r["measure"],r["time_period"],r["source_sector"],r["accounting_entry"],r["instrument"]) for r in rows}
    if observed!=expected:
        e.append("retained missing-row evidence differs from frozen 49x2 S1M/L/F2 pattern")

    if m["missing_row_count"]!=98 or m["numeric_observation_value_review_performed"] is not False or m["reconciliation_test_performed"] is not False:
        e.append("compact source-vintage manifest changed")
    if m["workflow_artifact"]["id"]!=10634456456:
        e.append("workflow artifact identity changed")
    if m["workflow_artifact"]["zip_sha256"]!="85c9ae9df0e94eea71e6748bcfb81244cb0a85cba023d7b31fdbd403e3ef0b7d":
        e.append("workflow artifact hash changed")

    state=p["current_state"]
    if state["execution_completed"] is not True or state["topology_pass"] is not True:
        e.append("public-access recovery completion/topology state changed")
    if state["aggregate_reference_mode_gate_pass"] is not False or state["bilateral_accounting_reopen_gate_pass"] is not False:
        e.append("terminal aggregate/bilateral gate state changed")
    if state["reference_mode_promotion_authorized"] is not False or state["accounting_reopen_authorized"] is not False:
        e.append("terminal source path may not authorize promotion/reopen")

    mode=next(x for x in rm["modes"] if x["id"]=="sectoral_financial_positions")
    if mode["status"]!="PARTIAL_SERIES_AVAILABLE":
        e.append("sectoral_financial_positions may not be promoted")
    dc=model["dynamic_core"]
    if dc["reference_mode_ready_count"]!=9 or dc["reference_mode_required_count"]!=10:
        e.append("reference-mode readiness must remain 9/10")
    if model["scientific_stage"].get("active_noncalibration_source_task") != "sectoral_financial_positions_ecb_qfa_official_tolerance_gate":
        e.append("historical terminal row gate permits only the independent official-tolerance task")
    if model["scientific_stage"].get("next_operational_state")!="EVIDENCE_TRIGGERED_BASELINE_HOLD":
        e.append("terminal source path must return to baseline hold")
    if acc["current_expected_state"]["canonical_complete_stock_and_flow_instruments"]!=["F3"]:
        e.append("Accounting Spine completion changed")

    return e

def main():
    errors=audit_oecd_exact_row_gate()
    if errors:
        raise RuntimeError("OECD exact-row gate audit failed:\n- "+"\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "topology_gate":"PASS",
        "exact_row_gate":"FAIL",
        "missing_required_rows":98,
        "missing_pattern":"S1M/L/F2 for 49 quarters in flow and stock",
        "numeric_value_review":False,
        "reconciliation_run":False,
        "reference_modes_ready":"9/10",
        "sectoral_financial_positions":"PARTIAL_SERIES_AVAILABLE",
        "scientific_state":"EVIDENCE_TRIGGERED_BASELINE_HOLD",
    },indent=2))

if __name__=="__main__":
    main()
