from __future__ import annotations

import csv
import io
import json
import urllib.request
from decimal import Decimal, InvalidOperation
from datetime import UTC, datetime
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
CONTRACT=ROOT/"model/dynamics/sectoral_financial_positions_ecb_qfa_materiality_gate_contract_2026_09_21.json"
DIAGNOSTICS=ROOT/"data/source_vintages/oecd-decimal-arithmetic-correction-2026-09-21/exact_decimal_reconciliation_diagnostics.csv"

ECB_EXR_URL=(
    "https://data-api.ecb.europa.eu/service/data/EXR/"
    "Q.RON.EUR.SP00.A?startPeriod=2014-Q1&endPeriod=2026-Q1"
    "&format=csvdata&detail=dataonly"
)
USER_AGENT="romanian-monetary-dynamics/0.2.0 (+ECB QFA materiality gate)"

def quarter_range(start: str, end: str) -> list[str]:
    sy,sq=start.split("-Q"); ey,eq=end.split("-Q")
    y=int(sy); q=int(sq); out=[]
    while (y,q) <= (int(ey),int(eq)):
        out.append(f"{y:04d}-Q{q}")
        q+=1
        if q==5:
            y+=1; q=1
    return out

def fetch_ecb_fx(url: str=ECB_EXR_URL) -> tuple[bytes,int|None,str|None]:
    req=urllib.request.Request(url,headers={"User-Agent":USER_AGENT,"Accept":"text/csv,*/*"})
    try:
        with urllib.request.urlopen(req,timeout=90) as r:
            return r.read(),int(r.status),None
    except Exception as exc:
        return b"",None,f"{type(exc).__name__}:{exc}"

def parse_fx(data: bytes) -> dict[str,Decimal]:
    reader=csv.DictReader(io.StringIO(data.decode("utf-8-sig",errors="replace")))
    out={}
    for row in reader:
        p=(row.get("TIME_PERIOD") or "").strip()
        raw=(row.get("OBS_VALUE") or "").strip()
        if not p or not raw:
            continue
        try:
            out[p]=Decimal(raw)
        except InvalidOperation:
            continue
    return out

def parse_diagnostics() -> list[dict]:
    return list(csv.DictReader(DIAGNOSTICS.open(encoding="utf-8")))

def evaluate_materiality(fx: dict[str,Decimal], rows: list[dict], contract: dict) -> dict:
    cfx=contract["currency_sufficiency_rule"]
    required=quarter_range(cfx["start_period"],cfx["end_period"])
    missing_fx=[p for p in required if p not in fx]
    nonpositive_or_le1=[p for p in required if p in fx and fx[p] <= Decimal("1")]
    threshold=Decimal(contract["retained_diagnostic_gate"]["conservative_threshold_million_ron"])

    expected={(m,p) for m in ("flow","stock") for p in required}
    observed={(r["measure"],r["time_period"]) for r in rows}
    missing_diag=sorted(expected-observed)
    extra_diag=sorted(observed-expected)
    duplicates=[]
    seen=set()
    for r in rows:
        k=(r["measure"],r["time_period"])
        if k in seen: duplicates.append(k)
        seen.add(k)

    cols=[
        "exact_decimal_system_residual_million_ron",
        "exact_decimal_s1_minus_components_million_ron",
        "exact_decimal_s1_plus_s2_million_ron",
    ]
    violations=[]
    maxima={c:Decimal("0") for c in cols}
    for r in rows:
        for c in cols:
            v=abs(Decimal(r[c]))
            if v>maxima[c]: maxima[c]=v
            if v >= threshold:
                violations.append({
                    "measure":r["measure"],
                    "time_period":r["time_period"],
                    "diagnostic":c,
                    "abs_residual_million_ron":str(v),
                })

    fx_values=[fx[p] for p in required if p in fx]
    return {
        "required_fx_quarters":len(required),
        "observed_fx_quarters":len(fx_values),
        "missing_fx_periods":missing_fx,
        "fx_periods_at_or_below_one":nonpositive_or_le1,
        "min_fx_ron_per_eur":str(min(fx_values)) if fx_values else None,
        "max_fx_ron_per_eur":str(max(fx_values)) if fx_values else None,
        "required_diagnostic_rows":len(expected),
        "observed_diagnostic_rows":len(rows),
        "missing_diagnostic_rows":[list(x) for x in missing_diag],
        "extra_diagnostic_rows":[list(x) for x in extra_diag],
        "duplicate_diagnostic_rows":[list(x) for x in duplicates],
        "conservative_threshold_million_ron":str(threshold),
        "max_abs_system_residual_million_ron":str(maxima[cols[0]]),
        "max_abs_resident_additivity_residual_million_ron":str(maxima[cols[1]]),
        "max_abs_external_balance_residual_million_ron":str(maxima[cols[2]]),
        "materiality_violations":violations,
        "pass":(
            not missing_fx and not nonpositive_or_le1
            and len(fx_values)==cfx["required_quarters"]
            and not missing_diag and not extra_diag and not duplicates
            and len(rows)==contract["retained_diagnostic_gate"]["required_rows"]
            and not violations
        ),
    }

def main():
    contract=json.loads(CONTRACT.read_text(encoding="utf-8"))
    data,status,error=fetch_ecb_fx()
    rows=parse_diagnostics()
    audit={
        "audit_version":"0.1",
        "generated_at_utc":datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00","Z"),
        "contract":str(CONTRACT.relative_to(ROOT)),
        "ecb_fx_url":ECB_EXR_URL,
        "ecb_fx_http_status":status,
        "ecb_fx_error":error,
        "oecd_values_reaccessed":False,
        "historical_0_1m_gate_rewritten":False,
        "reference_mode_promotion":False,
        "accounting_readiness_change":False,
        "parameter_estimation":False,
        "feedback_activation":False,
        "behavioural_closure_change":False,
    }
    if status!=200 or error or not data:
        audit["scientific_gate_result"]="INDETERMINATE"
        audit["disposition"]="ECB_FX_ACCESS_INDETERMINATE_NO_SCIENTIFIC_EFFECT"
    else:
        fx=parse_fx(data)
        result=evaluate_materiality(fx,rows,contract)
        audit["materiality_gate"]=result
        if result["pass"]:
            audit["scientific_gate_result"]="PASS"
            audit["disposition"]="ECB_QFA_OFFICIAL_MATERIALITY_ACCEPTABILITY_PASS_PROMOTION_ASSESSMENT_AUTHORIZED"
        else:
            audit["scientific_gate_result"]="FAIL"
            audit["disposition"]="ECB_QFA_OFFICIAL_MATERIALITY_ACCEPTABILITY_FAIL_NO_PROMOTION"
    print(json.dumps(audit,indent=2,ensure_ascii=False))

if __name__=="__main__":
    main()
