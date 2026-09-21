from __future__ import annotations

import csv
import io
import json
import math
import os
import sys
import urllib.parse
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts.audit_oecd_sectoral_financial_positions_nonconsolidated_probe import (
    dimension_order_from_structure,
    fetch,
)
from scripts.audit_oecd_sectoral_financial_positions_exact_reconciliation import (
    build_selection_key,
    quarter_range,
    sha256,
)

CONTRACT=ROOT/"model/dynamics/sectoral_financial_positions_oecd_semantic_adjusted_exact_gate_contract_2026_09_21.json"
TOPOLOGY=ROOT/"model/dynamics/sectoral_financial_positions_oecd_nonconsolidated_topology_assessment_2026_09_21.json"
OUT=Path(os.environ.get("OECD_SEMANTIC_REFERENCE_OUT","oecd_semantic_reference_artifacts"))

def selection_for_measure(contract: dict, measure: str) -> dict:
    s=contract["source_boundary"]; fixed=s["fixed_dimensions"]; md=s["measure_dimensions"][measure]
    return {
        "FREQ":s["frequency"],
        "ADJUSTMENT":fixed["ADJUSTMENT"],
        "REF_AREA":s["reference_area"],
        "COUNTERPART_AREA":fixed["COUNTERPART_AREA"],
        "SECTOR":s["required_source_sectors"]+s["diagnostic_source_sectors"],
        "COUNTERPART_SECTOR":fixed["COUNTERPART_SECTOR"],
        "CONSOLIDATION":fixed["CONSOLIDATION"],
        "ACCOUNTING_ENTRY":s["accounting_entries"],
        "TRANSACTION":md["TRANSACTION"],
        "INSTR_ASSET":s["instruments"],
        "MATURITY":sorted(set(s["instrument_maturity"].values())),
        "UNIT_MEASURE":fixed["UNIT_MEASURE"],
        "CURRENCY_DENOM":fixed["CURRENCY_DENOM"],
        "VALUATION":fixed["VALUATION"],
        "PRICE_BASE":fixed["PRICE_BASE"],
        "TRANSFORMATION":fixed["TRANSFORMATION"],
        "TABLE_IDENTIFIER":md["TABLE_IDENTIFIER"],
        "DEBT_BREAKDOWN":fixed["DEBT_BREAKDOWN"],
    }

def exact_rows(data: bytes, contract: dict) -> list[dict]:
    s=contract["source_boundary"]; fixed=s["fixed_dimensions"]
    allowed=set(s["required_source_sectors"]+s["diagnostic_source_sectors"])
    periods=set(quarter_range(s["start_period"],s["end_period"]))
    out=[]
    for row in csv.DictReader(io.StringIO(data.decode("utf-8-sig",errors="replace"))):
        sector=(row.get("SECTOR") or "").strip()
        instr=(row.get("INSTR_ASSET") or "").strip()
        entry=(row.get("ACCOUNTING_ENTRY") or "").strip()
        period=(row.get("TIME_PERIOD") or "").strip()
        if sector not in allowed or instr not in s["instruments"] or entry not in s["accounting_entries"] or period not in periods:
            continue
        if (row.get("MATURITY") or "").strip()!=s["instrument_maturity"][instr]:
            continue
        if (row.get("UNIT_MULT") or "").strip()!=fixed["UNIT_MULT"]:
            continue
        if (row.get("CURRENCY") or "").strip()!="RON":
            continue
        out.append(row)
    return out

def row_gate(rows: list[dict], contract: dict) -> dict:
    s=contract["source_boundary"]; exc=contract["semantic_exception"]["exact_key_pattern"]
    periods=quarter_range(s["start_period"],s["end_period"])
    counts=Counter(
        ((r.get("TIME_PERIOD") or "").strip(),(r.get("SECTOR") or "").strip(),
         (r.get("ACCOUNTING_ENTRY") or "").strip(),(r.get("INSTR_ASSET") or "").strip())
        for r in rows
    )
    missing=[]; duplicates=[]; exception_present=[]
    for p in periods:
        for sector in s["required_source_sectors"]:
            for entry in s["accounting_entries"]:
                for instr in s["instruments"]:
                    key=(p,sector,entry,instr); n=counts[key]
                    is_exc=(sector==exc["source_sector"] and entry==exc["accounting_entry"] and instr==exc["instrument"])
                    if is_exc:
                        if n!=0:
                            exception_present.append((key,n))
                    else:
                        if n==0: missing.append(key)
                        elif n>1: duplicates.append((key,n))
    return {
        "missing_nonexception_rows":missing,
        "duplicate_nonexception_rows":duplicates,
        "semantic_exception_rows_present":exception_present,
        "row_gate_pass":not missing and not duplicates and not exception_present,
    }

def parse_values(rows: list[dict], contract: dict) -> tuple[dict, bool]:
    vals={}; finite=True
    for row in rows:
        key=((row.get("TIME_PERIOD") or "").strip(),(row.get("SECTOR") or "").strip(),
             (row.get("ACCOUNTING_ENTRY") or "").strip(),(row.get("INSTR_ASSET") or "").strip())
        raw=(row.get("OBS_VALUE") or "").strip()
        try: value=float(raw)
        except Exception: value=math.nan
        vals[key]=value
        finite=finite and math.isfinite(value)
    s=contract["source_boundary"]; exc=contract["semantic_exception"]["exact_key_pattern"]
    for p in quarter_range(s["start_period"],s["end_period"]):
        vals[(p,exc["source_sector"],exc["accounting_entry"],exc["instrument"])]=0.0
    return vals,finite

def construct(vals: dict, contract: dict, measure: str):
    s=contract["source_boundary"]; periods=quarter_range(s["start_period"],s["end_period"])
    src=defaultdict(float)
    for (p,sector,entry,instr),v in vals.items():
        if math.isfinite(v):
            src[(p,sector,entry)]+=v
    constructed=[]; diagnostics=[]
    for p in periods:
        rmd={}
        for rid,spec in contract["sector_mapping"].items():
            assets=sum(sign*src[(p,sector,"A")] for sector,sign in spec["terms"])
            liabilities=sum(sign*src[(p,sector,"L")] for sector,sign in spec["terms"])
            net=assets-liabilities
            rmd[rid]=(assets,liabilities,net)
            constructed.append({
                "measure":measure,"time_period":p,"rmd_sector":rid,
                "assets_million_ron":assets,"liabilities_million_ron":liabilities,"net_million_ron":net,
            })
        system=sum(x[2] for x in rmd.values())
        s1=src[(p,"S1","A")]-src[(p,"S1","L")]
        components=sum(src[(p,x,"A")]-src[(p,x,"L")] for x in ("S11","S12","S13","S1M"))
        s2=src[(p,"S2","A")]-src[(p,"S2","L")]
        diagnostics.append({
            "measure":measure,"time_period":p,
            "rmd_system_net_residual_million_ron":system,
            "s1_minus_resident_components_million_ron":s1-components,
            "s1_plus_s2_million_ron":s1+s2,
        })
    return constructed,diagnostics

def write_csv(path: Path, rows: list[dict]):
    if not rows:
        path.write_text("",encoding="utf-8"); return
    with path.open("w",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    c=json.loads(CONTRACT.read_text(encoding="utf-8"))
    top=json.loads(TOPOLOGY.read_text(encoding="utf-8"))
    expected_hash={"flow":top["results"]["flows"]["structure_sha256"],"stock":top["results"]["stocks"]["structure_sha256"]}
    refs={"flow":c["source_boundary"]["flow_dataflow"],"stock":c["source_boundary"]["stock_dataflow"]}
    raw={}; rows={}; requests=[]; technical=[]
    for measure in ("flow","stock"):
        structure_id=refs[measure].split(",",1)[1]
        structure_url=f"https://sdmx.oecd.org/public/rest/dataflow/OECD.SDD.NAD/{structure_id}/?references=all"
        sb,sh,ss,se=fetch(structure_url,accept="application/vnd.sdmx.structure+xml,application/xml,text/xml,*/*")
        s_hash=sha256(sb) if sb else None
        if ss!=200 or se or s_hash!=expected_hash[measure]:
            technical.append(f"{measure}:structure")
            requests.append({"measure":measure,"structure_http_status":ss,"structure_sha256":s_hash})
            continue
        order=dimension_order_from_structure(sb)
        sel=selection_for_measure(c,measure)
        key=build_selection_key(order,sel)
        query=urllib.parse.urlencode({
            "startPeriod":c["source_boundary"]["start_period"],
            "endPeriod":c["source_boundary"]["end_period"],
            "dimensionAtObservation":"AllDimensions",
            "format":"csvfilewithlabels",
        })
        url=f"https://sdmx.oecd.org/public/rest/data/{refs[measure]},/{key}?{query}"
        db,dh,ds,de=fetch(url,accept="text/csv,application/vnd.sdmx.data+csv,*/*")
        if db: (OUT/f"{measure}_raw.csv").write_bytes(db)
        requests.append({
            "measure":measure,"structure_url":structure_url,"structure_http_status":ss,"structure_sha256":s_hash,
            "dimension_order":order,"selection_key":key,"data_url":url,"data_http_status":ds,
            "data_error":de,"data_bytes":len(db),"data_sha256":sha256(db) if db else None,
        })
        if ds!=200 or de or not db:
            technical.append(f"{measure}:data"); continue
        raw[measure]=db; rows[measure]=exact_rows(db,c)

    audit={
        "audit_version":"0.1",
        "generated_at_utc":datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "contract":str(CONTRACT.relative_to(ROOT)),
        "semantic_assessment":c["semantic_assessment"],
        "technical_blockers":technical,
        "request_records":requests,
        "row_gate":{},
        "numeric_observation_value_review_performed":False,
        "reconciliation_test_performed":False,
        "reference_mode_promotion":False,
        "accounting_readiness_change":False,
    }
    if technical:
        audit["scientific_gate_result"]="INDETERMINATE"
        audit["disposition"]="SOURCE_ACCESS_INDETERMINATE_NO_SCIENTIFIC_EFFECT"
    else:
        gates={m:row_gate(rows[m],c) for m in ("flow","stock")}
        audit["row_gate"]=gates
        if not all(g["row_gate_pass"] for g in gates.values()):
            audit["scientific_gate_result"]="FAIL"
            audit["disposition"]="SEMANTIC_ADJUSTED_ROW_GATE_FAIL_NO_VALUE_REVIEW_NO_PROMOTION"
        else:
            audit["numeric_observation_value_review_performed"]=True
            all_source=[]; all_constructed=[]; all_diag=[]; finite=True
            for measure in ("flow","stock"):
                vals,f=parse_values(rows[measure],c); finite=finite and f
                exc=c["semantic_exception"]["exact_key_pattern"]
                for (p,sector,entry,instr),v in sorted(vals.items()):
                    all_source.append({
                        "measure":measure,"time_period":p,"source_sector":sector,
                        "accounting_entry":entry,"instrument":instr,"value_million_ron":v,
                        "value_origin":"ESA2010_STRUCTURAL_ZERO" if (sector,entry,instr)==(exc["source_sector"],exc["accounting_entry"],exc["instrument"]) else "OECD_OBS_VALUE",
                    })
                constructed,diag=construct(vals,c,measure)
                all_constructed.extend(constructed); all_diag.extend(diag)
            write_csv(OUT/"exact_filtered_source_rows_with_semantic_zero.csv",all_source)
            write_csv(OUT/"constructed_reference_series.csv",all_constructed)
            write_csv(OUT/"reconciliation_diagnostics.csv",all_diag)
            audit["reconciliation_test_performed"]=True
            stock_tol=c["value_and_reconciliation_gate"]["stock_system_residual_tolerance_million_ron"]
            flow_tol=c["value_and_reconciliation_gate"]["flow_system_residual_tolerance_million_ron"]
            violations=[x for x in all_diag if abs(x["rmd_system_net_residual_million_ron"])>(flow_tol if x["measure"]=="flow" else stock_tol)]
            audit["finite_value_gate_pass"]=finite
            audit["reconciliation_violation_count"]=len(violations)
            audit["max_abs_stock_residual_million_ron"]=max(abs(x["rmd_system_net_residual_million_ron"]) for x in all_diag if x["measure"]=="stock")
            audit["max_abs_flow_residual_million_ron"]=max(abs(x["rmd_system_net_residual_million_ron"]) for x in all_diag if x["measure"]=="flow")
            audit["max_abs_s1_component_residual_million_ron"]=max(abs(x["s1_minus_resident_components_million_ron"]) for x in all_diag)
            audit["max_abs_s1_plus_s2_residual_million_ron"]=max(abs(x["s1_plus_s2_million_ron"]) for x in all_diag)
            if finite and not violations:
                audit["scientific_gate_result"]="PASS"
                audit["disposition"]="SEMANTIC_ADJUSTED_EXACT_GATE_PASS_PROMOTION_ASSESSMENT_AUTHORIZED"
            else:
                audit["scientific_gate_result"]="FAIL"
                audit["disposition"]="SEMANTIC_ADJUSTED_VALUE_OR_RECONCILIATION_FAIL_NO_PROMOTION"

    (OUT/"sectoral_financial_positions_oecd_semantic_adjusted_gate.json").write_text(json.dumps(audit,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(audit,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
