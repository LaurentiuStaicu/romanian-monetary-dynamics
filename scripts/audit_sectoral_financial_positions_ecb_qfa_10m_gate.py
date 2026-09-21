from __future__ import annotations

import csv
import io
import json
import os
import sys
import urllib.parse
import urllib.request
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

CONTRACT=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_10m_validation_contract_2026_09_21.json"
TOPOLOGY=ROOT/"model/dynamics/sectoral_financial_positions_oecd_nonconsolidated_topology_assessment_2026_09_21.json"
OUT=Path(os.environ.get("ECB_QFA_10M_OUT","ecb_qfa_10m_artifacts"))
ECB_API="https://data-api.ecb.europa.eu/service/data"

def source_selection(c: dict, measure: str) -> dict:
    s=c["frozen_source"]; f=s["fixed_dimensions"]; md=s["measure_dimensions"][measure]
    return {
        "FREQ":s["frequency"],"ADJUSTMENT":f["ADJUSTMENT"],"REF_AREA":s["reference_area"],
        "COUNTERPART_AREA":f["COUNTERPART_AREA"],
        "SECTOR":s["required_source_sectors"]+s["diagnostic_source_sectors"],
        "COUNTERPART_SECTOR":f["COUNTERPART_SECTOR"],"CONSOLIDATION":f["CONSOLIDATION"],
        "ACCOUNTING_ENTRY":s["accounting_entries"],"TRANSACTION":md["TRANSACTION"],
        "INSTR_ASSET":s["instruments"],"MATURITY":sorted(set(s["instrument_maturity"].values())),
        "UNIT_MEASURE":f["UNIT_MEASURE"],"CURRENCY_DENOM":f["CURRENCY_DENOM"],
        "VALUATION":f["VALUATION"],"PRICE_BASE":f["PRICE_BASE"],"TRANSFORMATION":f["TRANSFORMATION"],
        "TABLE_IDENTIFIER":md["TABLE_IDENTIFIER"],"DEBT_BREAKDOWN":f["DEBT_BREAKDOWN"],
    }

def filter_rows(data: bytes, c: dict) -> list[dict]:
    s=c["frozen_source"]; f=s["fixed_dimensions"]
    periods=set(quarter_range(s["start_period"],s["end_period"]))
    allowed=set(s["required_source_sectors"]+s["diagnostic_source_sectors"])
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
        if (row.get("UNIT_MULT") or "").strip()!=f["UNIT_MULT"] or (row.get("CURRENCY") or "").strip()!="RON":
            continue
        out.append(row)
    return out

def row_gate(rows: list[dict], c: dict) -> dict:
    s=c["frozen_source"]; exc=c["semantic_exception"]["exact_key_pattern"]
    periods=quarter_range(s["start_period"],s["end_period"])
    counts=Counter(((r["TIME_PERIOD"].strip(),r["SECTOR"].strip(),r["ACCOUNTING_ENTRY"].strip(),r["INSTR_ASSET"].strip())) for r in rows)
    missing=[]; duplicates=[]; conflict=[]
    for p in periods:
        for sector in s["required_source_sectors"]:
            for entry in s["accounting_entries"]:
                for instr in s["instruments"]:
                    key=(p,sector,entry,instr); n=counts[key]
                    is_exc=(sector==exc["source_sector"] and entry==exc["accounting_entry"] and instr==exc["instrument"])
                    if is_exc:
                        if n: conflict.append((key,n))
                    else:
                        if n==0: missing.append(key)
                        elif n>1: duplicates.append((key,n))
    return {"missing":missing,"duplicates":duplicates,"semantic_conflict":conflict,"pass":not missing and not duplicates and not conflict}

def parse_values(rows: list[dict], c: dict) -> dict:
    vals={}
    for row in rows:
        key=(row["TIME_PERIOD"].strip(),row["SECTOR"].strip(),row["ACCOUNTING_ENTRY"].strip(),row["INSTR_ASSET"].strip())
        try:
            vals[key]=Decimal((row.get("OBS_VALUE") or "").strip())
        except InvalidOperation:
            vals[key]=None
    s=c["frozen_source"]; exc=c["semantic_exception"]["exact_key_pattern"]
    zero=Decimal(c["semantic_exception"]["value_million_ron"])
    for p in quarter_range(s["start_period"],s["end_period"]):
        vals[(p,exc["source_sector"],exc["accounting_entry"],exc["instrument"])]=zero
    return vals

def fetch_ecb_fx(series: str, start: str, end: str):
    url=f"{ECB_API}/EXR/{series}?"+urllib.parse.urlencode({"startPeriod":start,"endPeriod":end,"format":"csvdata"})
    req=urllib.request.Request(url,headers={"User-Agent":"romanian-monetary-dynamics/0.2.0","Accept":"text/csv,*/*"})
    try:
        with urllib.request.urlopen(req,timeout=90) as response:
            body=response.read(); status=int(response.status)
    except Exception as exc:
        return {},url,None,f"{type(exc).__name__}:{exc}",b""
    text=body.decode("utf-8-sig",errors="replace")
    rows=list(csv.DictReader(io.StringIO(text)))
    values={}
    for row in rows:
        p=(row.get("TIME_PERIOD") or "").strip()
        raw=(row.get("OBS_VALUE") or "").strip()
        if p and raw:
            try: values[p]=Decimal(raw)
            except InvalidOperation: pass
    return values,url,status,None,body

def instrument_diagnostics(vals: dict, fx: dict, c: dict, measure: str) -> list[dict]:
    s=c["frozen_source"]; threshold=Decimal(c["official_validation_rule"]["threshold_eur_million"])
    sectors=s["required_source_sectors"]; out=[]
    for p in quarter_range(s["start_period"],s["end_period"]):
        rate=fx[p]
        for instr in s["instruments"]:
            assets=sum(vals[(p,sector,"A",instr)] for sector in sectors)
            liabilities=sum(vals[(p,sector,"L",instr)] for sector in sectors)
            residual_ron=assets-liabilities
            residual_eur=residual_ron/rate
            out.append({
                "measure":measure,"time_period":p,"instrument":instr,
                "assets_million_ron":str(assets),"liabilities_million_ron":str(liabilities),
                "residual_million_ron":str(residual_ron),"ron_per_eur":str(rate),
                "residual_million_eur":str(residual_eur),
                "abs_residual_below_ecb_10m":abs(residual_eur)<threshold,
            })
    return out

def system_diagnostics(inst: list[dict]) -> list[dict]:
    grouped=defaultdict(Decimal)
    for row in inst:
        grouped[(row["measure"],row["time_period"])]+=Decimal(row["residual_million_eur"])
    return [{"measure":m,"time_period":p,"aggregate_f2_f8_residual_million_eur":str(v)}
            for (m,p),v in sorted(grouped.items())]

def write_csv(path: Path, rows: list[dict]):
    if not rows: path.write_text("",encoding="utf-8"); return
    with path.open("w",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    c=json.loads(CONTRACT.read_text(encoding="utf-8")); top=json.loads(TOPOLOGY.read_text(encoding="utf-8"))
    refs={"flow":c["frozen_source"]["oecd_flow_dataflow"],"stock":c["frozen_source"]["oecd_stock_dataflow"]}
    expected_raw={"flow":c["frozen_source"]["expected_flow_raw_sha256"],"stock":c["frozen_source"]["expected_stock_raw_sha256"]}
    expected_structure={"flow":top["results"]["flows"]["structure_sha256"],"stock":top["results"]["stocks"]["structure_sha256"]}
    raw={}; rows={}; requests=[]; blockers=[]
    for measure in ("flow","stock"):
        structure_id=refs[measure].split(",",1)[1]
        structure_url=f"https://sdmx.oecd.org/public/rest/dataflow/OECD.SDD.NAD/{structure_id}/?references=all"
        sb,sh,ss,se=fetch(structure_url,accept="application/vnd.sdmx.structure+xml,application/xml,text/xml,*/*")
        if ss!=200 or se or sha256(sb)!=expected_structure[measure]:
            blockers.append(f"{measure}:structure_changed_or_unavailable"); continue
        order=dimension_order_from_structure(sb); key=build_selection_key(order,source_selection(c,measure))
        q=urllib.parse.urlencode({"startPeriod":c["frozen_source"]["start_period"],"endPeriod":c["frozen_source"]["end_period"],"dimensionAtObservation":"AllDimensions","format":"csvfilewithlabels"})
        url=f"https://sdmx.oecd.org/public/rest/data/{refs[measure]},/{key}?{q}"
        db,dh,ds,de=fetch(url,accept="text/csv,application/vnd.sdmx.data+csv,*/*")
        digest=sha256(db) if db else None
        requests.append({"measure":measure,"data_url":url,"http_status":ds,"sha256":digest,"expected_sha256":expected_raw[measure]})
        if ds!=200 or de or digest!=expected_raw[measure]:
            blockers.append(f"{measure}:source_vintage_changed_or_unavailable"); continue
        raw[measure]=db; rows[measure]=filter_rows(db,c)

    fx={}; fx_records=[]
    for measure,series in (("flow",c["exchange_rate_conversion"]["flow_series"]),("stock",c["exchange_rate_conversion"]["stock_series"])):
        values,url,status,error,body=fetch_ecb_fx(series,c["frozen_source"]["start_period"],c["frozen_source"]["end_period"])
        fx[measure]=values
        fx_records.append({"measure":measure,"series":series,"url":url,"http_status":status,"error":error,"sha256":sha256(body) if body else None,"count":len(values)})
        expected_periods=set(quarter_range(c["frozen_source"]["start_period"],c["frozen_source"]["end_period"]))
        if status!=200 or error or set(values)!=expected_periods:
            blockers.append(f"{measure}:ecb_fx_incomplete")

    audit={
        "audit_version":"0.1","generated_at_utc":datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "contract":str(CONTRACT.relative_to(ROOT)),"source_requests":requests,"fx_requests":fx_records,
        "technical_blockers":blockers,"row_gate":{},"numeric_review_performed":False,
        "official_ecb_validation_performed":False,"reference_mode_promotion":False
    }
    if blockers:
        audit["scientific_gate_result"]="INDETERMINATE"; audit["disposition"]="SOURCE_OR_FX_BOUNDARY_CHANGED_NO_PROMOTION"
    else:
        gates={m:row_gate(rows[m],c) for m in ("flow","stock")}; audit["row_gate"]=gates
        if not all(g["pass"] for g in gates.values()):
            audit["scientific_gate_result"]="FAIL"; audit["disposition"]="ROW_OR_SEMANTIC_GATE_FAIL_NO_PROMOTION"
        else:
            vals={m:parse_values(rows[m],c) for m in ("flow","stock")}
            if any(v is None for m in vals.values() for v in m.values()):
                audit["scientific_gate_result"]="FAIL"; audit["disposition"]="NONFINITE_VALUE_FAIL_NO_PROMOTION"
            else:
                audit["numeric_review_performed"]=True; audit["official_ecb_validation_performed"]=True
                inst=instrument_diagnostics(vals["flow"],fx["flow"],c,"flow")+instrument_diagnostics(vals["stock"],fx["stock"],c,"stock")
                sysdiag=system_diagnostics(inst); write_csv(OUT/"per_instrument_ecb_validation.csv",inst); write_csv(OUT/"aggregate_system_diagnostic.csv",sysdiag)
                failures=[x for x in inst if not x["abs_residual_below_ecb_10m"]]
                threshold=Decimal(c["official_validation_rule"]["threshold_eur_million"])
                audit.update({
                    "per_instrument_test_count":len(inst),"per_instrument_failure_count":len(failures),
                    "per_instrument_pass_count":len(inst)-len(failures),
                    "max_abs_per_instrument_residual_million_eur":str(max(abs(Decimal(x["residual_million_eur"])) for x in inst)),
                    "max_abs_aggregate_f2_f8_residual_million_eur":str(max(abs(Decimal(x["aggregate_f2_f8_residual_million_eur"])) for x in sysdiag)),
                    "threshold_eur_million":str(threshold),
                })
                if failures:
                    audit["scientific_gate_result"]="FAIL"; audit["disposition"]="ECB_QFA_10M_PER_INSTRUMENT_VALIDATION_FAIL_NO_PROMOTION"
                else:
                    audit["scientific_gate_result"]="PASS"; audit["disposition"]="ECB_QFA_10M_PER_INSTRUMENT_VALIDATION_PASS_PROMOTION_ASSESSMENT_AUTHORIZED"
    (OUT/"sectoral_financial_positions_ecb_qfa_10m_validation.json").write_text(json.dumps(audit,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(audit,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
