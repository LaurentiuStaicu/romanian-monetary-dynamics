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

CONTRACT=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_materiality_gate_contract_2026_09_21.json"
TOPOLOGY=ROOT/"model/dynamics/sectoral_financial_positions_oecd_nonconsolidated_topology_assessment_2026_09_21.json"
OUT=Path(os.environ.get("ECB_QFA_MATERIALITY_OUT","ecb_qfa_materiality_artifacts"))

def selection_for_measure(c: dict, measure: str) -> dict:
    s=c["source_boundary"]["oecd"]; fixed=s["fixed_dimensions"]; md=s["measure_dimensions"][measure]
    return {
        "FREQ":s["frequency"],"ADJUSTMENT":fixed["ADJUSTMENT"],"REF_AREA":s["reference_area"],
        "COUNTERPART_AREA":fixed["COUNTERPART_AREA"],
        "SECTOR":s["required_source_sectors"]+s["diagnostic_source_sectors"],
        "COUNTERPART_SECTOR":fixed["COUNTERPART_SECTOR"],"CONSOLIDATION":fixed["CONSOLIDATION"],
        "ACCOUNTING_ENTRY":s["accounting_entries"],"TRANSACTION":md["TRANSACTION"],
        "INSTR_ASSET":s["instruments"],"MATURITY":sorted(set(s["instrument_maturity"].values())),
        "UNIT_MEASURE":fixed["UNIT_MEASURE"],"CURRENCY_DENOM":fixed["CURRENCY_DENOM"],
        "VALUATION":fixed["VALUATION"],"PRICE_BASE":fixed["PRICE_BASE"],
        "TRANSFORMATION":fixed["TRANSFORMATION"],"TABLE_IDENTIFIER":md["TABLE_IDENTIFIER"],
        "DEBT_BREAKDOWN":fixed["DEBT_BREAKDOWN"],
    }

def exact_rows(data: bytes, c: dict) -> list[dict]:
    s=c["source_boundary"]["oecd"]; fixed=s["fixed_dimensions"]
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

def row_gate(rows: list[dict], c: dict) -> dict:
    s=c["source_boundary"]["oecd"]; exc=c["semantic_exception"]["exact_key_pattern"]
    periods=quarter_range(s["start_period"],s["end_period"])
    sectors=s["required_source_sectors"]+s["diagnostic_source_sectors"]
    counts=Counter(
        ((r.get("TIME_PERIOD") or "").strip(),(r.get("SECTOR") or "").strip(),
         (r.get("ACCOUNTING_ENTRY") or "").strip(),(r.get("INSTR_ASSET") or "").strip())
        for r in rows
    )
    missing=[]; dup=[]; conflict=[]
    for p in periods:
        for sector in sectors:
            for entry in s["accounting_entries"]:
                for instr in s["instruments"]:
                    k=(p,sector,entry,instr); n=counts[k]
                    is_exc=(sector==exc["source_sector"] and entry==exc["accounting_entry"] and instr==exc["instrument"])
                    if is_exc:
                        if n!=0: conflict.append((k,n))
                    elif n==0: missing.append(k)
                    elif n>1: dup.append((k,n))
    return {"pass":not missing and not dup and not conflict,"missing":missing,"duplicates":dup,"semantic_conflicts":conflict}

def parse_decimal_values(rows: list[dict], c: dict) -> tuple[dict, list]:
    vals={}; invalid=[]
    for r in rows:
        k=((r.get("TIME_PERIOD") or "").strip(),(r.get("SECTOR") or "").strip(),
           (r.get("ACCOUNTING_ENTRY") or "").strip(),(r.get("INSTR_ASSET") or "").strip())
        raw=(r.get("OBS_VALUE") or "").strip()
        try: vals[k]=Decimal(raw)
        except (InvalidOperation,ValueError):
            invalid.append((k,raw))
    s=c["source_boundary"]["oecd"]; exc=c["semantic_exception"]["exact_key_pattern"]
    for p in quarter_range(s["start_period"],s["end_period"]):
        vals[(p,exc["source_sector"],exc["accounting_entry"],exc["instrument"])]=Decimal("0")
    return vals,invalid

def fetch_ecb_fx(c: dict) -> tuple[dict[str,Decimal], dict]:
    url=c["source_boundary"]["ecb_exchange_rate"]["api_url"]
    req=urllib.request.Request(url,headers={"User-Agent":"romanian-monetary-dynamics/0.2.0","Accept":"text/csv"})
    with urllib.request.urlopen(req,timeout=90) as resp:
        data=resp.read(); status=int(resp.status)
    rows=list(csv.DictReader(io.StringIO(data.decode("utf-8-sig",errors="replace"))))
    fx={}
    for r in rows:
        p=(r.get("TIME_PERIOD") or "").strip(); raw=(r.get("OBS_VALUE") or "").strip()
        if p and raw:
            try: fx[p]=Decimal(raw)
            except InvalidOperation: pass
    return fx,{"url":url,"http_status":status,"bytes":len(data),"sha256":sha256(data)}

def source_net(vals: dict, p: str, sector: str, instr: str) -> Decimal:
    return vals[(p,sector,"A",instr)]-vals[(p,sector,"L",instr)]

def instrument_diagnostics(vals: dict, fx: dict[str,Decimal], c: dict, measure: str) -> list[dict]:
    s=c["source_boundary"]["oecd"]; threshold=Decimal(c["official_materiality_rule"]["threshold_million_eur"])
    rows=[]
    for p in quarter_range(s["start_period"],s["end_period"]):
        rate=fx[p]
        for instr in s["instruments"]:
            n={sector:source_net(vals,p,sector,instr) for sector in s["required_source_sectors"]+s["diagnostic_source_sectors"]}
            h=n["S1M"]; corp=n["S11"]; fin=n["S12"]-n["S121"]; gov=n["S13"]; bnr=n["S121"]; ext=n["S2"]
            system=h+corp+fin+gov+bnr+ext
            agg=n["S1"]-(n["S11"]+n["S12"]+n["S13"]+n["S1M"])
            external=n["S1"]+n["S2"]
            for identity,resid in (("rmd_horizontal_system",system),("s1_sector_aggregation",agg),("s1_plus_s2_horizontal",external)):
                eur=abs(resid)/rate
                rows.append({
                    "measure":measure,"time_period":p,"instrument":instr,"identity":identity,
                    "residual_million_ron":str(resid),"ecb_eurron_quarter_average":str(rate),
                    "abs_residual_million_eur":str(eur),
                    "threshold_million_eur":str(threshold),"pass":eur<threshold,
                })
    return rows

def aggregate_diagnostics(vals_by_measure: dict, fx: dict[str,Decimal], c: dict) -> list[dict]:
    s=c["source_boundary"]["oecd"]; threshold=Decimal(c["official_materiality_rule"]["threshold_million_eur"])
    out=[]
    for measure,vals in vals_by_measure.items():
        for p in quarter_range(s["start_period"],s["end_period"]):
            rate=fx[p]
            system=Decimal("0")
            for instr in s["instruments"]:
                n={sector:source_net(vals,p,sector,instr) for sector in s["required_source_sectors"]}
                system += n["S1M"]+n["S11"]+(n["S12"]-n["S121"])+n["S13"]+n["S121"]+n["S2"]
            eur=abs(system)/rate
            out.append({
                "measure":measure,"time_period":p,"identity":"aggregate_f2_f8_rmd_system",
                "residual_million_ron":str(system),"ecb_eurron_quarter_average":str(rate),
                "abs_residual_million_eur":str(eur),"threshold_million_eur":str(threshold),
                "pass":eur<threshold,
            })
    return out

def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("",encoding="utf-8"); return
    with path.open("w",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0])); w.writeheader(); w.writerows(rows)

def main() -> None:
    OUT.mkdir(parents=True,exist_ok=True)
    c=json.loads(CONTRACT.read_text(encoding="utf-8"))
    top=json.loads(TOPOLOGY.read_text(encoding="utf-8"))
    refs={"flow":c["source_boundary"]["oecd"]["flow_dataflow"],"stock":c["source_boundary"]["oecd"]["stock_dataflow"]}
    expected={"flow":top["results"]["flows"]["structure_sha256"],"stock":top["results"]["stocks"]["structure_sha256"]}
    requests=[]; gates={}; values={}; technical=[]

    for measure in ("flow","stock"):
        sid=refs[measure].split(",",1)[1]
        surl=f"https://sdmx.oecd.org/public/rest/dataflow/OECD.SDD.NAD/{sid}/?references=all"
        sb,sh,ss,se=fetch(surl,accept="application/vnd.sdmx.structure+xml,application/xml,text/xml,*/*")
        ssha=sha256(sb) if sb else None
        if ss!=200 or se or ssha!=expected[measure]:
            technical.append(f"{measure}:structure"); continue
        order=dimension_order_from_structure(sb)
        sel=selection_for_measure(c,measure); key=build_selection_key(order,sel)
        q=urllib.parse.urlencode({"startPeriod":c["source_boundary"]["oecd"]["start_period"],"endPeriod":c["source_boundary"]["oecd"]["end_period"],"dimensionAtObservation":"AllDimensions","format":"csvfilewithlabels"})
        url=f"https://sdmx.oecd.org/public/rest/data/{refs[measure]},/{key}?{q}"
        db,dh,ds,de=fetch(url,accept="text/csv,application/vnd.sdmx.data+csv,*/*")
        if db: (OUT/f"{measure}_raw.csv").write_bytes(db)
        requests.append({"measure":measure,"structure_url":surl,"structure_sha256":ssha,"selection_key":key,"data_url":url,"data_http_status":ds,"data_error":de,"data_sha256":sha256(db) if db else None,"data_bytes":len(db)})
        if ds!=200 or de or not db:
            technical.append(f"{measure}:data"); continue
        erows=exact_rows(db,c); gates[measure]=row_gate(erows,c)
        if not gates[measure]["pass"]: continue
        vals,invalid=parse_decimal_values(erows,c)
        if invalid:
            gates[measure]["invalid_numeric_values"]=invalid
        else:
            values[measure]=vals

    fx={}; fxmeta={}
    try:
        fx,fxmeta=fetch_ecb_fx(c)
    except Exception as exc:
        technical.append(f"ecb_fx:{type(exc).__name__}:{exc}")

    required_periods=quarter_range(c["source_boundary"]["oecd"]["start_period"],c["source_boundary"]["oecd"]["end_period"])
    missing_fx=[p for p in required_periods if p not in fx]
    if missing_fx: technical.append("ecb_fx_missing_periods")

    audit={
        "audit_version":"0.1","generated_at_utc":datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "contract":str(CONTRACT.relative_to(ROOT)),"requests":requests,"ecb_fx":fxmeta,
        "technical_blockers":technical,"row_gates":gates,"missing_fx_periods":missing_fx,
        "numeric_observation_value_review_performed":bool(values),
        "exact_decimal_arithmetic":True,"reference_mode_promotion":False,"accounting_readiness_change":False,
    }
    if technical:
        audit["scientific_gate_result"]="INDETERMINATE"; audit["disposition"]="SOURCE_OR_FX_ACCESS_INDETERMINATE_NO_PROMOTION"
    elif any(not gates.get(m,{}).get("pass",False) for m in ("flow","stock")) or len(values)!=2:
        audit["scientific_gate_result"]="FAIL"; audit["disposition"]="ROW_OR_NUMERIC_GATE_FAIL_NO_PROMOTION"
    else:
        instrument=[]
        for m in ("flow","stock"): instrument.extend(instrument_diagnostics(values[m],fx,c,m))
        aggregate=aggregate_diagnostics(values,fx,c)
        write_csv(OUT/"instrument_level_ecb_materiality_diagnostics.csv",instrument)
        write_csv(OUT/"aggregate_ecb_materiality_diagnostics.csv",aggregate)
        violations=[r for r in instrument+aggregate if not r["pass"]]
        max_eur=max(Decimal(r["abs_residual_million_eur"]) for r in instrument+aggregate)
        audit["instrument_identity_test_count"]=len(instrument)
        audit["aggregate_identity_test_count"]=len(aggregate)
        audit["materiality_violation_count"]=len(violations)
        audit["max_abs_residual_million_eur"]=str(max_eur)
        audit["minimum_ecb_eurron_rate"]=str(min(fx[p] for p in required_periods))
        audit["maximum_ecb_eurron_rate"]=str(max(fx[p] for p in required_periods))
        if violations:
            audit["scientific_gate_result"]="FAIL"; audit["disposition"]="ECB_QFA_10M_MATERIALITY_GATE_FAIL_NO_PROMOTION"
        else:
            audit["scientific_gate_result"]="PASS"; audit["disposition"]="ECB_QFA_10M_MATERIALITY_GATE_PASS_PROMOTION_ASSESSMENT_AUTHORIZED"

    (OUT/"sectoral_financial_positions_ecb_qfa_materiality_gate.json").write_text(json.dumps(audit,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(audit,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
