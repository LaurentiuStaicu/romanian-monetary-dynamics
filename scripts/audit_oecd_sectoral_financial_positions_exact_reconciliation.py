from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import os
import urllib.parse
from collections import Counter, defaultdict
from datetime import UTC, datetime
from pathlib import Path

from scripts.audit_oecd_sectoral_financial_positions_nonconsolidated_probe import (
    dimension_order_from_structure,
    fetch,
)

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"model/dynamics/sectoral_financial_positions_oecd_exact_extraction_reconciliation_contract_2026_09_21.json"
TOPOLOGY=ROOT/"model/dynamics/sectoral_financial_positions_oecd_nonconsolidated_topology_assessment_2026_09_21.json"
OUT=Path(os.environ.get("OECD_EXACT_REFERENCE_OUT","oecd_exact_reference_artifacts"))
USER_AGENT="romanian-monetary-dynamics/0.2.0 (+OECD exact sectoral-financial-position gate)"

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def quarter_range(start: str, end: str) -> list[str]:
    sy,sq=start.split("-Q"); ey,eq=end.split("-Q")
    y=int(sy); q=int(sq); out=[]
    while (y,q) <= (int(ey),int(eq)):
        out.append(f"{y:04d}-Q{q}")
        q+=1
        if q==5:
            y+=1; q=1
    return out

def build_selection_key(order: list[str], selection: dict[str, str | list[str]]) -> str:
    parts=[]
    for dim in order:
        value=selection.get(dim,"")
        if isinstance(value,list):
            parts.append("+".join(value))
        else:
            parts.append(value)
    return ".".join(parts)

def selection_for_measure(contract: dict, measure: str) -> dict:
    source=contract["source"]; fixed=source["fixed_dimensions"]
    md=source["measure_dimensions"][measure]
    return {
        "FREQ":source["frequency"],
        "ADJUSTMENT":fixed["ADJUSTMENT"],
        "REF_AREA":source["reference_area"],
        "COUNTERPART_AREA":fixed["COUNTERPART_AREA"],
        "SECTOR":source["query_sectors"],
        "COUNTERPART_SECTOR":fixed["COUNTERPART_SECTOR"],
        "CONSOLIDATION":fixed["CONSOLIDATION"],
        "ACCOUNTING_ENTRY":fixed["ACCOUNTING_ENTRY"],
        "TRANSACTION":md["TRANSACTION"],
        "INSTR_ASSET":fixed["INSTR_ASSET"],
        "MATURITY":fixed["MATURITY"],
        "UNIT_MEASURE":fixed["UNIT_MEASURE"],
        "CURRENCY_DENOM":fixed["CURRENCY_DENOM"],
        "VALUATION":fixed["VALUATION"],
        "PRICE_BASE":fixed["PRICE_BASE"],
        "TRANSFORMATION":fixed["TRANSFORMATION"],
        "TABLE_IDENTIFIER":md["TABLE_IDENTIFIER"],
        "DEBT_BREAKDOWN":fixed["DEBT_BREAKDOWN"],
    }

def read_exact_metadata(data: bytes, contract: dict, measure: str) -> dict:
    source=contract["source"]; fixed=source["fixed_dimensions"]
    instr_map=contract["instrument_mapping"]
    required_sectors=source["required_mapping_source_sectors"]
    diagnostic_sectors=source["diagnostic_source_sectors"]
    allowed=set(required_sectors+diagnostic_sectors)
    periods=quarter_range(source["start_period"],source["end_period"])
    counts=Counter()
    diagnostic_counts=Counter()
    header=[]
    reader=csv.DictReader(io.StringIO(data.decode("utf-8-sig",errors="replace")))
    header=reader.fieldnames or []
    for row in reader:
        sector=(row.get("SECTOR") or "").strip()
        instr=(row.get("INSTR_ASSET") or "").strip()
        entry=(row.get("ACCOUNTING_ENTRY") or "").strip()
        period=(row.get("TIME_PERIOD") or "").strip()
        if sector not in allowed or instr not in instr_map or entry not in contract["accounting_entries"] or period not in periods:
            continue
        if (row.get("MATURITY") or "").strip()!=instr_map[instr]["MATURITY"]:
            continue
        if (row.get("UNIT_MULT") or "").strip()!=fixed["UNIT_MULT"]:
            continue
        if (row.get("CURRENCY") or "").strip()!="RON":
            continue
        key=(period,sector,entry,instr)
        if sector in required_sectors:
            counts[key]+=1
        else:
            diagnostic_counts[key]+=1

    expected=[(p,s,e,i) for p in periods for s in required_sectors for e in contract["accounting_entries"] for i in instr_map]
    missing=[k for k in expected if counts[k]==0]
    duplicates=[(k,counts[k]) for k in expected if counts[k]>1]
    diagnostic_expected=[(p,s,e,i) for p in periods for s in diagnostic_sectors for e in contract["accounting_entries"] for i in instr_map]
    diagnostic_missing=[k for k in diagnostic_expected if diagnostic_counts[k]==0]
    diagnostic_duplicates=[(k,diagnostic_counts[k]) for k in diagnostic_expected if diagnostic_counts[k]>1]
    return {
        "csv_header":header,
        "expected_required_row_count":len(expected),
        "observed_unique_required_key_count":len(counts),
        "missing_required_rows":missing,
        "duplicate_required_rows":duplicates,
        "diagnostic_missing_rows":diagnostic_missing,
        "diagnostic_duplicate_rows":diagnostic_duplicates,
        "numeric_observation_value_review_performed":False,
    }

def parse_values(data: bytes, contract: dict, measure: str) -> dict[tuple[str,str,str,str],float]:
    source=contract["source"]; fixed=source["fixed_dimensions"]
    instr_map=contract["instrument_mapping"]
    allowed=set(source["required_mapping_source_sectors"]+source["diagnostic_source_sectors"])
    periods=set(quarter_range(source["start_period"],source["end_period"]))
    values={}
    reader=csv.DictReader(io.StringIO(data.decode("utf-8-sig",errors="replace")))
    for row in reader:
        sector=(row.get("SECTOR") or "").strip()
        instr=(row.get("INSTR_ASSET") or "").strip()
        entry=(row.get("ACCOUNTING_ENTRY") or "").strip()
        period=(row.get("TIME_PERIOD") or "").strip()
        if sector not in allowed or instr not in instr_map or entry not in contract["accounting_entries"] or period not in periods:
            continue
        if (row.get("MATURITY") or "").strip()!=instr_map[instr]["MATURITY"]:
            continue
        if (row.get("UNIT_MULT") or "").strip()!=fixed["UNIT_MULT"] or (row.get("CURRENCY") or "").strip()!="RON":
            continue
        key=(period,sector,entry,instr)
        raw=(row.get("OBS_VALUE") or "").strip()
        try:
            value=float(raw)
        except Exception:
            value=math.nan
        values[key]=value
    return values

def construct_and_reconcile(values: dict, contract: dict, measure: str):
    source=contract["source"]; periods=quarter_range(source["start_period"],source["end_period"])
    instrs=list(contract["instrument_mapping"])
    src=defaultdict(float)
    for (period,sector,entry,instr),value in values.items():
        if math.isfinite(value):
            src[(period,sector,entry)]+=value

    constructed=[]
    rec=[]
    finite=True
    for period in periods:
        rmd={}
        for rid,spec in contract["sector_mapping"].items():
            a=sum(sign*src[(period,sector,"A")] for sector,sign in spec["terms"])
            l=sum(sign*src[(period,sector,"L")] for sector,sign in spec["terms"])
            n=a-l
            if not all(math.isfinite(x) for x in (a,l,n)):
                finite=False
            rmd[rid]=(a,l,n)
            constructed.append({
                "measure":measure,"time_period":period,"rmd_sector":rid,
                "assets_million_ron":a,"liabilities_million_ron":l,"net_million_ron":n,
            })
        system=sum(v[2] for v in rmd.values())
        s1=src[(period,"S1","A")]-src[(period,"S1","L")]
        resident_components=sum(
            src[(period,s,"A")]-src[(period,s,"L")]
            for s in ("S11","S12","S13","S1M")
        )
        s2=src[(period,"S2","A")]-src[(period,"S2","L")]
        rec.append({
            "measure":measure,"time_period":period,
            "rmd_system_net_residual_million_ron":system,
            "s1_minus_resident_components_million_ron":s1-resident_components,
            "s1_plus_s2_million_ron":s1+s2,
        })
    return constructed,rec,finite

def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("",encoding="utf-8"); return
    with path.open("w",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

def main() -> None:
    OUT.mkdir(parents=True,exist_ok=True)
    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    topology=json.loads(TOPOLOGY.read_text(encoding="utf-8"))
    expected_hash={
        "flow":topology["results"]["flows"]["structure_sha256"],
        "stock":topology["results"]["stocks"]["structure_sha256"],
    }
    flow_ref={"flow":contract["source"]["flow_dataflow"],"stock":contract["source"]["stock_dataflow"]}
    table_id={"flow":"flows_exact","stock":"stocks_exact"}
    raw={}
    result_rows={}
    technical=[]
    request_records=[]

    for measure in ("flow","stock"):
        structure_id=flow_ref[measure].split(",",1)[1]
        structure_url=f"https://sdmx.oecd.org/public/rest/dataflow/OECD.SDD.NAD/{structure_id}/?references=all"
        sb,sh,ss,se=fetch(structure_url,accept="application/vnd.sdmx.structure+xml,application/xml,text/xml,*/*")
        s_hash=sha256(sb) if sb else None
        if ss!=200 or se or s_hash!=expected_hash[measure]:
            technical.append(f"{measure}:structure_access_or_hash")
            request_records.append({"measure":measure,"structure_url":structure_url,"structure_http_status":ss,"structure_sha256":s_hash,"expected_structure_sha256":expected_hash[measure]})
            continue
        order=dimension_order_from_structure(sb)
        selection=selection_for_measure(contract,measure)
        key=build_selection_key(order,selection)
        query=urllib.parse.urlencode({
            "startPeriod":contract["source"]["start_period"],
            "endPeriod":contract["source"]["end_period"],
            "dimensionAtObservation":"AllDimensions",
            "format":"csvfilewithlabels",
        })
        data_url=f"https://sdmx.oecd.org/public/rest/data/{flow_ref[measure]},/{key}?{query}"
        db,dh,ds,de=fetch(data_url,accept="text/csv,application/vnd.sdmx.data+csv,*/*")
        if db:
            (OUT/f"{table_id[measure]}_raw.csv").write_bytes(db)
        request_records.append({
            "measure":measure,"structure_url":structure_url,"structure_http_status":ss,
            "structure_sha256":s_hash,"dimension_order":order,"selection_key":key,
            "data_url":data_url,"data_http_status":ds,"data_error":de,
            "data_bytes":len(db),"data_sha256":sha256(db) if db else None,
        })
        if ds!=200 or de or not db:
            technical.append(f"{measure}:data_access")
            continue
        raw[measure]=db
        result_rows[measure]=read_exact_metadata(db,contract,measure)

    audit={
        "audit_version":"0.1",
        "generated_at_utc":datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "contract":str(CONTRACT.relative_to(ROOT)),
        "topology_assessment":str(TOPOLOGY.relative_to(ROOT)),
        "request_records":request_records,
        "technical_blockers":technical,
        "row_gate":result_rows,
        "numeric_observation_value_review_performed":False,
        "reconciliation_test_performed":False,
        "reference_mode_promotion":False,
        "accounting_readiness_change":False,
        "parameter_estimation":False,
        "feedback_activation":False,
        "behavioural_closure_change":False,
    }

    if technical:
        audit["scientific_gate_result"]="INDETERMINATE"
        audit["disposition"]="SOURCE_ACCESS_OR_STRUCTURE_CHANGED_NO_SCIENTIFIC_EFFECT"
    else:
        missing=[]
        duplicates=[]
        for measure in ("flow","stock"):
            missing.extend([(measure,*x) for x in result_rows[measure]["missing_required_rows"]])
            duplicates.extend([(measure,*x[0],x[1]) for x in result_rows[measure]["duplicate_required_rows"]])
        write_csv(OUT/"missing_required_rows.csv",[
            {"measure":m,"time_period":p,"source_sector":s,"accounting_entry":e,"instrument":i}
            for m,p,s,e,i in missing
        ])
        if missing or duplicates:
            audit["scientific_gate_result"]="FAIL"
            audit["disposition"]="EXACT_REQUIRED_ROW_COVERAGE_FAIL_NO_VALUE_REVIEW_NO_PROMOTION"
            audit["missing_required_row_count"]=len(missing)
            audit["duplicate_required_row_count"]=len(duplicates)
        else:
            audit["numeric_observation_value_review_performed"]=True
            all_constructed=[]; all_rec=[]; finite=True
            raw_rows=[]
            for measure in ("flow","stock"):
                vals=parse_values(raw[measure],contract,measure)
                finite=finite and all(math.isfinite(v) for v in vals.values())
                for (period,sector,entry,instr),value in sorted(vals.items()):
                    raw_rows.append({"measure":measure,"time_period":period,"source_sector":sector,"accounting_entry":entry,"instrument":instr,"value_million_ron":value})
                constructed,rec,f=construct_and_reconcile(vals,contract,measure)
                finite=finite and f
                all_constructed.extend(constructed); all_rec.extend(rec)
            write_csv(OUT/"exact_filtered_source_rows.csv",raw_rows)
            write_csv(OUT/"constructed_reference_series.csv",all_constructed)
            write_csv(OUT/"reconciliation_diagnostics.csv",all_rec)
            audit["reconciliation_test_performed"]=True
            stock_tol=contract["validation_gates"]["represented_system_stock_reconciliation_tolerance_million_ron"]
            flow_tol=contract["validation_gates"]["represented_system_flow_reconciliation_tolerance_million_ron"]
            violations=[]
            for row in all_rec:
                tol=flow_tol if row["measure"]=="flow" else stock_tol
                if abs(row["rmd_system_net_residual_million_ron"])>tol:
                    violations.append(row)
            audit["finite_value_gate_pass"]=finite
            audit["reconciliation_violation_count"]=len(violations)
            audit["max_abs_stock_residual_million_ron"]=max((abs(x["rmd_system_net_residual_million_ron"]) for x in all_rec if x["measure"]=="stock"),default=None)
            audit["max_abs_flow_residual_million_ron"]=max((abs(x["rmd_system_net_residual_million_ron"]) for x in all_rec if x["measure"]=="flow"),default=None)
            if finite and not violations:
                audit["scientific_gate_result"]="PASS"
                audit["disposition"]="EXACT_EXTRACTION_AND_RECONCILIATION_PASS_PROMOTION_ASSESSMENT_AUTHORIZED"
            else:
                audit["scientific_gate_result"]="FAIL"
                audit["disposition"]="VALUE_OR_RECONCILIATION_GATE_FAIL_NO_PROMOTION"

    (OUT/"sectoral_financial_positions_oecd_exact_extraction_reconciliation.json").write_text(
        json.dumps(audit,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"
    )
    print(json.dumps(audit,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
