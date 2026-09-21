from __future__ import annotations

import csv
import io
import json
import os
import sys
import urllib.parse
from collections import defaultdict
from datetime import UTC, datetime
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts.audit_oecd_sectoral_financial_positions_nonconsolidated_probe import (
    dimension_order_from_structure, fetch,
)
from scripts.audit_oecd_sectoral_financial_positions_exact_reconciliation import (
    build_selection_key, quarter_range, sha256,
)
from scripts.audit_oecd_sectoral_financial_positions_semantic_adjusted_gate import (
    selection_for_measure, exact_rows, row_gate,
)

CONTRACT=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_official_tolerance_gate_contract_2026_09_21.json"
TOPOLOGY=ROOT/"model/dynamics/sectoral_financial_positions_oecd_nonconsolidated_topology_assessment_2026_09_21.json"
OUT=Path(os.environ.get("ECB_QFA_TOLERANCE_OUT","ecb_qfa_tolerance_artifacts"))

def decimal_values(rows:list[dict],contract:dict)->tuple[dict,bool]:
    vals={}; finite=True
    for row in rows:
        key=((row.get("TIME_PERIOD") or "").strip(),(row.get("SECTOR") or "").strip(),
             (row.get("ACCOUNTING_ENTRY") or "").strip(),(row.get("INSTR_ASSET") or "").strip())
        raw=(row.get("OBS_VALUE") or "").strip()
        try:
            v=Decimal(raw)
            if not v.is_finite(): finite=False
        except (InvalidOperation,ValueError):
            v=Decimal("NaN"); finite=False
        vals[key]=v
    s=contract["source_boundary"]; exc=contract["semantic_exception"]["exact_key_pattern"]
    for p in quarter_range(s["start_period"],s["end_period"]):
        vals[(p,exc["source_sector"],exc["accounting_entry"],exc["instrument"])]=Decimal("0")
    return vals,finite

def fetch_fx(contract:dict)->tuple[dict,bytes]:
    url=contract["fx_threshold_gate"]["api_url"]
    body,headers,status,error=fetch(url,accept="text/csv,*/*",timeout=90,attempts=2)
    out={"url":url,"http_status":status,"error":error,"bytes":len(body),"sha256":sha256(body) if body else None}
    rates=[]
    if status==200 and body:
        for row in csv.DictReader(io.StringIO(body.decode("utf-8-sig",errors="replace"))):
            raw=(row.get("OBS_VALUE") or "").strip()
            period=(row.get("TIME_PERIOD") or "").strip()
            try:
                rate=Decimal(raw)
            except InvalidOperation:
                continue
            if rate.is_finite() and rate>0:
                rates.append((period,rate))
    out["positive_observation_count"]=len(rates)
    if rates:
        p,r=min(rates,key=lambda x:x[1])
        out["minimum_rate_RON_per_EUR"]=str(r)
        out["minimum_rate_period"]=p
        threshold=Decimal(contract["fx_threshold_gate"]["threshold_eur_million"])*r
        out["conservative_threshold_floor_million_RON"]=str(threshold)
    else:
        out["minimum_rate_RON_per_EUR"]=None
        out["minimum_rate_period"]=None
        out["conservative_threshold_floor_million_RON"]=None
    return out,body

def sector_net(vals:dict,p:str,sector:str,instr:str)->Decimal:
    return vals[(p,sector,"A",instr)]-vals[(p,sector,"L",instr)]

def rmd_instrument_residual(vals:dict,p:str,instr:str,contract:dict)->Decimal:
    total=Decimal("0")
    for _,spec in contract["sector_mapping"].items():
        sector_total=Decimal("0")
        for sector,sign in spec["terms"]:
            sector_total += Decimal(str(sign))*sector_net(vals,p,sector,instr)
        total += sector_total
    return total

def diagnostics(vals:dict,p:str,instr:str)->tuple[Decimal,Decimal]:
    s1=sector_net(vals,p,"S1",instr)
    comps=sum((sector_net(vals,p,s,instr) for s in ("S11","S12","S13","S1M")),Decimal("0"))
    s2=sector_net(vals,p,"S2",instr)
    return s1-comps,s1+s2

def write_csv(path:Path,rows:list[dict])->None:
    if not rows:
        path.write_text("",encoding="utf-8"); return
    with path.open("w",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

def main()->None:
    OUT.mkdir(parents=True,exist_ok=True)
    c=json.loads(CONTRACT.read_text(encoding="utf-8"))
    top=json.loads(TOPOLOGY.read_text(encoding="utf-8"))
    expected_hash={"flow":top["results"]["flows"]["structure_sha256"],"stock":top["results"]["stocks"]["structure_sha256"]}
    refs={"flow":c["source_boundary"]["flow_dataflow"],"stock":c["source_boundary"]["stock_dataflow"]}
    technical=[]; requests=[]; rows={}

    fx,fx_body=fetch_fx(c)
    if fx_body:(OUT/"ecb_exr_ron_eur_daily.csv").write_bytes(fx_body)
    if fx["http_status"]!=c["fx_threshold_gate"]["required_http_status"] or fx["error"]:
        technical.append("fx_access")
    if fx["positive_observation_count"]<c["fx_threshold_gate"]["minimum_observation_count"]:
        technical.append("fx_observation_count")
    threshold=Decimal(fx["conservative_threshold_floor_million_RON"]) if fx["conservative_threshold_floor_million_RON"] else None

    for measure in ("flow","stock"):
        structure_id=refs[measure].split(",",1)[1]
        structure_url=f"https://sdmx.oecd.org/public/rest/dataflow/OECD.SDD.NAD/{structure_id}/?references=all"
        sb,sh,ss,se=fetch(structure_url,accept="application/vnd.sdmx.structure+xml,application/xml,text/xml,*/*")
        s_hash=sha256(sb) if sb else None
        if ss!=200 or se or s_hash!=expected_hash[measure]:
            technical.append(f"{measure}:structure")
            requests.append({"measure":measure,"structure_http_status":ss,"structure_sha256":s_hash,"expected_structure_sha256":expected_hash[measure]})
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
        if db:(OUT/f"{measure}_raw.csv").write_bytes(db)
        requests.append({"measure":measure,"structure_url":structure_url,"structure_http_status":ss,"structure_sha256":s_hash,
                         "dimension_order":order,"selection_key":key,"data_url":url,"data_http_status":ds,"data_error":de,
                         "data_bytes":len(db),"data_sha256":sha256(db) if db else None})
        if ds!=200 or de or not db:
            technical.append(f"{measure}:data")
            continue
        rows[measure]=exact_rows(db,c)

    audit={
        "audit_version":"0.1",
        "generated_at_utc":datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "contract":str(CONTRACT.relative_to(ROOT)),
        "tolerance_authority":c["tolerance_authority"],
        "fx_threshold":fx,
        "technical_blockers":technical,
        "request_records":requests,
        "row_gate":{},
        "numeric_observation_value_review_performed":False,
        "exact_decimal_arithmetic":True,
        "reference_mode_promotion":False,
        "accounting_readiness_change":False,
    }
    if technical or threshold is None:
        audit["scientific_gate_result"]="INDETERMINATE"
        audit["disposition"]="SOURCE_OR_FX_ACCESS_INDETERMINATE_NO_SCIENTIFIC_EFFECT"
    else:
        gates={m:row_gate(rows[m],c) for m in ("flow","stock")}
        audit["row_gate"]=gates
        if not all(g["row_gate_pass"] for g in gates.values()):
            audit["scientific_gate_result"]="FAIL"
            audit["disposition"]="OFFICIAL_TOLERANCE_ROW_GATE_FAIL_NO_VALUE_REVIEW_NO_PROMOTION"
        else:
            audit["numeric_observation_value_review_performed"]=True
            vals={}; finite=True
            for measure in ("flow","stock"):
                vals[measure],f=decimal_values(rows[measure],c)
                finite=finite and f
            periods=quarter_range(c["source_boundary"]["start_period"],c["source_boundary"]["end_period"])
            instruments=c["source_boundary"]["instruments"]
            instrument_rows=[]; aggregate_rows=[]; violations=[]
            for measure in ("flow","stock"):
                for p in periods:
                    agg=Decimal("0")
                    for instr in instruments:
                        resid=rmd_instrument_residual(vals[measure],p,instr,c)
                        d1,d2=diagnostics(vals[measure],p,instr)
                        agg+=resid
                        passed=abs(resid)<=threshold
                        row={"measure":measure,"time_period":p,"instrument":instr,
                             "residual_million_ron":str(resid),"threshold_floor_million_ron":str(threshold),
                             "pass":passed,"s1_minus_components_million_ron":str(d1),"s1_plus_s2_million_ron":str(d2)}
                        instrument_rows.append(row)
                        if not passed:violations.append(row)
                    apass=abs(agg)<=threshold
                    aggregate_rows.append({"measure":measure,"time_period":p,"aggregate_residual_million_ron":str(agg),
                                           "threshold_floor_million_ron":str(threshold),"pass":apass})
                    if not apass:
                        violations.append({"measure":measure,"time_period":p,"instrument":"AGGREGATE","residual_million_ron":str(agg),
                                           "threshold_floor_million_ron":str(threshold),"pass":False})
            write_csv(OUT/"per_instrument_horizontal_consistency.csv",instrument_rows)
            write_csv(OUT/"aggregate_system_consistency.csv",aggregate_rows)
            audit["finite_value_gate_pass"]=finite
            audit["per_instrument_test_count"]=len(instrument_rows)
            audit["per_instrument_violation_count"]=sum(1 for x in instrument_rows if not x["pass"])
            audit["aggregate_test_count"]=len(aggregate_rows)
            audit["aggregate_violation_count"]=sum(1 for x in aggregate_rows if not x["pass"])
            audit["maximum_abs_per_instrument_residual_million_ron"]=str(max(abs(Decimal(x["residual_million_ron"])) for x in instrument_rows))
            audit["maximum_abs_aggregate_residual_million_ron"]=str(max(abs(Decimal(x["aggregate_residual_million_ron"])) for x in aggregate_rows))
            audit["minimum_threshold_margin_ratio"]=str(
                threshold/max(
                    max(abs(Decimal(x["residual_million_ron"])) for x in instrument_rows),
                    max(abs(Decimal(x["aggregate_residual_million_ron"])) for x in aggregate_rows),
                )
            )
            required=set(c["source_boundary"]["required_2025_quarters"])
            common=set(periods)
            coverage=(len(periods)>=c["source_boundary"]["minimum_common_quarters"] and required<=common)
            audit["common_quarter_count"]=len(periods)
            audit["coverage_gate_pass"]=coverage
            if finite and coverage and not violations:
                audit["scientific_gate_result"]="PASS"
                audit["disposition"]="OFFICIAL_ECB_QFA_TOLERANCE_GATE_PASS_PROMOTION_ASSESSMENT_AUTHORIZED"
            else:
                audit["scientific_gate_result"]="FAIL"
                audit["disposition"]="OFFICIAL_ECB_QFA_TOLERANCE_GATE_FAIL_NO_PROMOTION"

    (OUT/"sectoral_financial_positions_ecb_qfa_official_tolerance_gate.json").write_text(
        json.dumps(audit,indent=2,ensure_ascii=False)+"\n",encoding="utf-8"
    )
    print(json.dumps(audit,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
