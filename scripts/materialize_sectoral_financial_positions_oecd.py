from __future__ import annotations

import csv
import json
import os
import sys
import urllib.parse
from datetime import UTC, datetime
from decimal import Decimal
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0,str(ROOT))

from scripts.audit_oecd_sectoral_financial_positions_nonconsolidated_probe import dimension_order_from_structure, fetch
from scripts.audit_oecd_sectoral_financial_positions_exact_reconciliation import build_selection_key, quarter_range, sha256
from scripts.audit_sectoral_financial_positions_ecb_qfa_10m_gate import source_selection, filter_rows, row_gate, parse_values

CONTRACT=ROOT/"model/dynamics/sectoral_financial_positions_materialisation_contract_2026_09_21.json"
VALIDATION=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_10m_validation_contract_2026_09_21.json"
OUT=Path(os.environ.get("SECTORAL_POSITIONS_OUT","sectoral_financial_positions_materialisation_artifacts"))

def write_csv(path: Path, rows: list[dict]) -> None:
    with path.open("w",encoding="utf-8",newline="") as h:
        w=csv.DictWriter(h,fieldnames=list(rows[0]))
        w.writeheader(); w.writerows(rows)

def main() -> None:
    OUT.mkdir(parents=True,exist_ok=True)
    c=json.loads(CONTRACT.read_text(encoding="utf-8"))
    v=json.loads(VALIDATION.read_text(encoding="utf-8"))
    source=v["frozen_source"]
    refs={"flow":source["oecd_flow_dataflow"],"stock":source["oecd_stock_dataflow"]}
    expected={"flow":c["exact_source"]["expected_flow_sha256"],"stock":c["exact_source"]["expected_stock_sha256"]}
    values={}
    requests=[]

    for measure in ("flow","stock"):
        structure_id=refs[measure].split(",",1)[1]
        structure_url=f"https://sdmx.oecd.org/public/rest/dataflow/OECD.SDD.NAD/{structure_id}/?references=all"
        sb,sh,ss,se=fetch(structure_url,accept="application/vnd.sdmx.structure+xml,application/xml,text/xml,*/*")
        if ss!=200 or se or not sb:
            raise RuntimeError(f"{measure} OECD structure unavailable")
        order=dimension_order_from_structure(sb)
        selection=source_selection(v,measure)
        if not set(selection).issubset(set(order)):
            raise RuntimeError(f"{measure} required dimensions missing")
        key=build_selection_key(order,selection)
        q=urllib.parse.urlencode({
            "startPeriod":source["start_period"],"endPeriod":source["end_period"],
            "dimensionAtObservation":"AllDimensions","format":"csvfilewithlabels"
        })
        url=f"https://sdmx.oecd.org/public/rest/data/{refs[measure]},/{key}?{q}"
        db,dh,ds,de=fetch(url,accept="text/csv,application/vnd.sdmx.data+csv,*/*")
        digest=sha256(db) if db else None
        requests.append({"measure":measure,"url":url,"http_status":ds,"sha256":digest})
        if ds!=200 or de or digest!=expected[measure]:
            raise RuntimeError(f"{measure} source bytes differ from validated gate")
        rows=filter_rows(db,v)
        rg=row_gate(rows,v)
        if not rg["pass"]:
            raise RuntimeError(f"{measure} row gate no longer passes: {rg}")
        values[measure]=parse_values(rows,v)
        if any(x is None for x in values[measure].values()):
            raise RuntimeError(f"{measure} contains non-finite/unparseable values")

    periods=quarter_range(c["exact_source"]["period_start"],c["exact_source"]["period_end"])
    breakdown=[]; aggregate=[]
    for measure in ("flow","stock"):
        vals=values[measure]
        for p in periods:
            for rid,terms in c["sector_mapping"].items():
                sector_assets=Decimal("0"); sector_liabilities=Decimal("0")
                for instr in c["instruments"]:
                    assets=sum(Decimal(str(sign))*vals[(p,sector,"A",instr)] for sector,sign in terms)
                    liabilities=sum(Decimal(str(sign))*vals[(p,sector,"L",instr)] for sector,sign in terms)
                    net=assets-liabilities
                    breakdown.append({
                        "time_period":p,"measure":measure,"rmd_sector":rid,"instrument":instr,
                        "assets_million_ron":str(assets),"liabilities_million_ron":str(liabilities),
                        "net_million_ron":str(net)
                    })
                    sector_assets+=assets; sector_liabilities+=liabilities
                aggregate.append({
                    "time_period":p,"measure":measure,"rmd_sector":rid,
                    "assets_million_ron":str(sector_assets),
                    "liabilities_million_ron":str(sector_liabilities),
                    "net_million_ron":str(sector_assets-sector_liabilities)
                })

    if len(aggregate)!=c["required_row_counts"]["reference_series"]:
        raise RuntimeError(f"unexpected reference-series row count: {len(aggregate)}")
    if len(breakdown)!=c["required_row_counts"]["instrument_breakdown"]:
        raise RuntimeError(f"unexpected instrument-breakdown row count: {len(breakdown)}")

    write_csv(OUT/"sectoral_financial_positions_oecd_2014Q1_2026Q1.csv",aggregate)
    write_csv(OUT/"sectoral_financial_positions_oecd_instrument_breakdown_2014Q1_2026Q1.csv",breakdown)

    provenance={
        "provenance_version":"0.1",
        "generated_at_utc":datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "contract":str(CONTRACT.relative_to(ROOT)),
        "validation_authority":c["authorization"],
        "source_requests":requests,
        "sector_mapping":c["sector_mapping"],
        "instruments":c["instruments"],
        "semantic_exception":c["semantic_exception"],
        "period_start":periods[0],"period_end":periods[-1],"common_quarters":len(periods),
        "reference_series_rows":len(aggregate),"instrument_breakdown_rows":len(breakdown),
        "reference_series_sha256":sha256((OUT/"sectoral_financial_positions_oecd_2014Q1_2026Q1.csv").read_bytes()),
        "instrument_breakdown_sha256":sha256((OUT/"sectoral_financial_positions_oecd_instrument_breakdown_2014Q1_2026Q1.csv").read_bytes()),
        "accounting_spine_promotion":False,
        "behavioural_effect":"NONE"
    }
    (OUT/"sectoral_financial_positions_oecd_2014Q1_2026Q1.json").write_text(json.dumps(provenance,indent=2,ensure_ascii=False)+"\n",encoding="utf-8")
    print(json.dumps(provenance,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
