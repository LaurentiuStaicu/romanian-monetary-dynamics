from __future__ import annotations

import csv
import io
import json
import os
import sys
import urllib.parse
from collections import Counter, defaultdict
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
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

CONTRACT=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_10m_horizontal_gate_contract_2026_09_21.json"
TOPOLOGY=ROOT/"model/dynamics/sectoral_financial_positions_oecd_nonconsolidated_topology_assessment_2026_09_21.json"
OUT=Path(os.environ.get("ECB_QFA_10M_GATE_OUT","ecb_qfa_10m_gate_artifacts"))

def selection_for_measure(c: dict, measure: str) -> dict:
    s=c["source_boundary"]; f=s["fixed_dimensions"]; md=s["measure_dimensions"][measure]
    return {
        "FREQ":s["frequency"],"ADJUSTMENT":f["ADJUSTMENT"],"REF_AREA":s["reference_area"],
        "COUNTERPART_AREA":f["COUNTERPART_AREA"],"SECTOR":s["required_source_sectors"],
        "COUNTERPART_SECTOR":f["COUNTERPART_SECTOR"],"CONSOLIDATION":f["CONSOLIDATION"],
        "ACCOUNTING_ENTRY":s["accounting_entries"],"TRANSACTION":md["TRANSACTION"],
        "INSTR_ASSET":s["instruments"],"MATURITY":sorted(set(s["instrument_maturity"].values())),
        "UNIT_MEASURE":f["UNIT_MEASURE"],"CURRENCY_DENOM":f["CURRENCY_DENOM"],
        "VALUATION":f["VALUATION"],"PRICE_BASE":f["PRICE_BASE"],
        "TRANSFORMATION":f["TRANSFORMATION"],"TABLE_IDENTIFIER":md["TABLE_IDENTIFIER"],
        "DEBT_BREAKDOWN":f["DEBT_BREAKDOWN"],
    }

def exact_rows(data: bytes, c: dict) -> list[dict]:
    s=c["source_boundary"]; f=s["fixed_dimensions"]; periods=set(quarter_range(s["start_period"],s["end_period"]))
    out=[]
    for row in csv.DictReader(io.StringIO(data.decode("utf-8-sig",errors="replace"))):
        sector=(row.get("SECTOR") or "").strip(); instr=(row.get("INSTR_ASSET") or "").strip()
        entry=(row.get("ACCOUNTING_ENTRY") or "").strip(); period=(row.get("TIME_PERIOD") or "").strip()
        if sector not in s["required_source_sectors"] or instr not in s["instruments"] or entry not in s["accounting_entries"] or period not in periods:
            continue
        if (row.get("MATURITY") or "").strip()!=s["instrument_maturity"][instr]:
            continue
        if (row.get("UNIT_MULT") or "").strip()!=f["UNIT_MULT"] or (row.get("CURRENCY") or "").strip()!="RON":
            continue
        out.append(row)
    return out

def row_gate(rows: list[dict], c: dict) -> dict:
    s=c["source_boundary"]; exc=c["semantic_exception"]["exact_key_pattern"]
    periods=quarter_range(s["start_period"],s["end_period"])
    counts=Counter(((r.get("TIME_PERIOD") or "").strip(),(r.get("SECTOR") or "").strip(),
                    (r.get("ACCOUNTING_ENTRY") or "").strip(),(r.get("INSTR_ASSET") or "").strip()) for r in rows)
    missing=[]; duplicates=[]; conflict=[]
    for p in periods:
        for sector in s["required_source_sectors"]:
            for entry in s["accounting_entries"]:
                for instr in s["instruments"]:
                    key=(p,sector,entry,instr); n=counts[key]
                    is_exc=(sector==exc["source_sector"] and entry==exc["accounting_entry"] and instr==exc["instrument"])
                    if is_exc:
                        if n!=0: conflict.append((key,n))
                    elif n==0:
                        missing.append(key)
                    elif n>1:
                        duplicates.append((key,n))
    return {"missing":missing,"duplicates":duplicates,"semantic_conflict":conflict,
            "pass":not missing and not duplicates and not conflict}

def parse_decimal_values(rows: list[dict], c: dict) -> tuple[dict,bool]:
    values={}; finite=True
    for row in rows:
        key=((row.get("TIME_PERIOD") or "").strip(),(row.get("SECTOR") or "").strip(),
             (row.get("ACCOUNTING_ENTRY") or "").strip(),(row.get("INSTR_ASSET") or "").strip())
        raw=(row.get("OBS_VALUE") or "").strip()
        try:
            value=Decimal(raw)
            finite=finite and value.is_finite()
        except (InvalidOperation,ValueError):
            value=Decimal("NaN"); finite=False
        values[key]=value
    s=c["source_boundary"]; exc=c["semantic_exception"]["exact_key_pattern"]
    for p in quarter_range(s["start_period"],s["end_period"]):
        values[(p,exc["source_sector"],exc["accounting_entry"],exc["instrument"])]=Decimal("0")
    return values,finite

def per_instrument_residuals(values: dict, c: dict, measure: str) -> list[dict]:
    s=c["source_boundary"]; mapping=c["horizontal_identity"]["rmd_sector_mapping"]
    out=[]
    for p in quarter_range(s["start_period"],s["end_period"]):
        for instr in s["instruments"]:
            rmd={}
            for rid,terms in mapping.items():
                assets=sum(Decimal(sign)*values[(p,sector,"A",instr)] for sector,sign in terms)
                liabilities=sum(Decimal(sign)*values[(p,sector,"L",instr)] for sector,sign in terms)
                rmd[rid]=assets-liabilities
            residual=sum(rmd.values(),Decimal("0"))
            out.append({"measure":measure,"time_period":p,"instrument":instr,
                        "residual_million_ron":str(residual),
                        "abs_residual_million_ron":str(abs(residual))})
    return out

def fetch_ecb_fx(series_key: str, start: str, end: str) -> dict:
    url=f"https://data-api.ecb.europa.eu/service/data/EXR/{series_key}?"+urllib.parse.urlencode({
        "startPeriod":start,"endPeriod":end,"format":"csvdata"
    })
    body,headers,status,error=fetch(url,accept="text/csv,*/*")
    vals={}
    if status==200 and body:
        for row in csv.DictReader(io.StringIO(body.decode("utf-8-sig",errors="replace"))):
            p=(row.get("TIME_PERIOD") or "").strip(); raw=(row.get("OBS_VALUE") or "").strip()
            if p and raw:
                try: vals[p]=Decimal(raw)
                except InvalidOperation: pass
    return {"url":url,"http_status":status,"error":error,"sha256":sha256(body) if body else None,
            "bytes":len(body),"values":vals}

def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("",encoding="utf-8"); return
    with path.open("w",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def main() -> None:
    OUT.mkdir(parents=True,exist_ok=True)
    c=json.loads(CONTRACT.read_text(encoding="utf-8"))
    top=json.loads(TOPOLOGY.read_text(encoding="utf-8"))
    refs={"flow":c["source_boundary"]["flow_dataflow"],"stock":c["source_boundary"]["stock_dataflow"]}
    expected={"flow":top["results"]["flows"]["structure_sha256"],"stock":top["results"]["stocks"]["structure_sha256"]}
    technical=[]; rows={}; req=[]
    for measure in ("flow","stock"):
        structure_id=refs[measure].split(",",1)[1]
        surl=f"https://sdmx.oecd.org/public/rest/dataflow/OECD.SDD.NAD/{structure_id}/?references=all"
        sb,sh,ss,se=fetch(surl,accept="application/vnd.sdmx.structure+xml,application/xml,text/xml,*/*")
        ssha=sha256(sb) if sb else None
        if ss!=200 or se or ssha!=expected[measure]:
            technical.append(f"{measure}:structure")
            req.append({"measure":measure,"structure_url":surl,"structure_http_status":ss,"structure_sha256":ssha})
            continue
        order=dimension_order_from_structure(sb); sel=selection_for_measure(c,measure); key=build_selection_key(order,sel)
        query=urllib.parse.urlencode({"startPeriod":c["source_boundary"]["start_period"],
                                     "endPeriod":c["source_boundary"]["end_period"],
                                     "dimensionAtObservation":"AllDimensions","format":"csvfilewithlabels"})
        url=f"https://sdmx.oecd.org/public/rest/data/{refs[measure]},/{key}?{query}"
        db,dh,ds,de=fetch(url,accept="text/csv,application/vnd.sdmx.data+csv,*/*")
        if db: (OUT/f"{measure}_raw.csv").write_bytes(db)
        req.append({"measure":measure,"data_url":url,"data_http_status":ds,"data_error":de,
                    "data_sha256":sha256(db) if db else None,"data_bytes":len(db)})
        if ds!=200 or de or not db:
            technical.append(f"{measure}:data"); continue
        rows[measure]=exact_rows(db,c)

    fx={}
    for suffix in ("Q.RON.EUR.SP00.A","Q.RON.EUR.SP00.E"):
        fx[suffix]=fetch_ecb_fx(suffix,c["source_boundary"]["start_period"],c["source_boundary"]["end_period"])
        if fx[suffix]["http_status"]!=200 or fx[suffix]["error"] or not fx[suffix]["values"]:
            technical.append(f"fx:{suffix}")

    audit={"audit_version":"0.1","generated_at_utc":datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00","Z"),
           "contract":str(CONTRACT.relative_to(ROOT)),"technical_blockers":technical,"request_records":req,
           "fx_records":{k:{kk:vv for kk,vv in v.items() if kk!="values"} for k,v in fx.items()},
           "row_gate":{},"value_review_performed":False,"horizontal_test_performed":False,
           "reference_mode_promotion":False,"accounting_readiness_change":False}

    if technical:
        audit["scientific_gate_result"]="INDETERMINATE"; audit["disposition"]="SOURCE_OR_FX_ACCESS_INDETERMINATE_NO_SCIENTIFIC_EFFECT"
    else:
        gates={m:row_gate(rows[m],c) for m in ("flow","stock")}; audit["row_gate"]=gates
        if not all(g["pass"] for g in gates.values()):
            audit["scientific_gate_result"]="FAIL"; audit["disposition"]="ROW_OR_SEMANTIC_CONFLICT_FAIL_NO_VALUE_REVIEW"
        else:
            audit["value_review_performed"]=True
            values={}; finite=True
            for measure in ("flow","stock"):
                values[measure],ok=parse_decimal_values(rows[measure],c); finite=finite and ok
            audit["finite_value_gate_pass"]=finite
            fx_periods=set(quarter_range(c["source_boundary"]["start_period"],c["source_boundary"]["end_period"]))
            fx_ok=True; fx_min={}
            for key,record in fx.items():
                present=record["values"]
                if not fx_periods.issubset(set(present)):
                    fx_ok=False
                if present:
                    fx_min[key]=str(min(present.values()))
                    if min(present.values())<=Decimal("1"): fx_ok=False
            audit["fx_safety_check_pass"]=fx_ok; audit["fx_min_ron_per_eur"]=fx_min
            if not finite or not fx_ok:
                audit["scientific_gate_result"]="INDETERMINATE"; audit["disposition"]="FINITE_VALUE_OR_FX_SAFETY_CHECK_FAIL"
            else:
                allres=[]
                for measure in ("flow","stock"): allres.extend(per_instrument_residuals(values[measure],c,measure))
                write_csv(OUT/"per_instrument_horizontal_residuals.csv",allres)
                audit["horizontal_test_performed"]=True
                bound=Decimal(c["official_threshold_gate"]["first_stage_strict_sufficient_bound_million_ron"])
                exceeded=[x for x in allres if Decimal(x["abs_residual_million_ron"])>=bound]
                audit["total_tests"]=len(allres)
                audit["strict_sufficient_bound_million_ron"]=str(bound)
                audit["strict_bound_exceedance_count"]=len(exceeded)
                audit["max_abs_residual_million_ron"]=str(max(Decimal(x["abs_residual_million_ron"]) for x in allres))
                by_instr={}
                for instr in c["source_boundary"]["instruments"]:
                    vals_i=[Decimal(x["abs_residual_million_ron"]) for x in allres if x["instrument"]==instr]
                    by_instr[instr]=str(max(vals_i))
                audit["max_abs_residual_by_instrument_million_ron"]=by_instr
                if exceeded:
                    audit["scientific_gate_result"]="INDETERMINATE"
                    audit["disposition"]="EXACT_EUR_CONVERSION_RULE_REQUIRED_NO_PROMOTION"
                    write_csv(OUT/"strict_10m_ron_exceedances.csv",exceeded)
                else:
                    audit["scientific_gate_result"]="PASS"
                    audit["disposition"]="ECB_QFA_HORIZONTAL_CONSISTENCY_STRICT_SUFFICIENT_PASS_PROMOTION_ASSESSMENT_AUTHORIZED"

    (OUT/"sectoral_financial_positions_ecb_qfa_10m_horizontal_gate.json").write_text(json.dumps(audit,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(audit,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
