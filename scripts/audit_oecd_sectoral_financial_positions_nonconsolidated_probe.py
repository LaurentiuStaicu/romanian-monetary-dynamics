from __future__ import annotations

import csv
import hashlib
import io
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "model" / "dynamics" / "sectoral_financial_positions_oecd_nonconsolidated_probe_contract_2026_09_21.json"
OUT = Path(os.environ.get("OECD_NONCONSOLIDATED_TOPOLOGY_OUT", "oecd_nonconsolidated_topology_artifacts"))
USER_AGENT = "romanian-monetary-dynamics/0.2.0 (+OECD non-consolidated topology probe)"

def sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

def local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]

def fetch(url: str, *, accept: str, timeout: int = 90, attempts: int = 2):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept": accept})
    last_error = None
    for attempt in range(1, attempts + 1):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as response:
                return response.read(), dict(response.headers.items()), int(response.status), None
        except urllib.error.HTTPError as exc:
            return exc.read(), dict(exc.headers.items()), int(exc.code), f"HTTPError:{exc.code}"
        except Exception as exc:
            last_error = f"{type(exc).__name__}:{exc}"
            if attempt < attempts:
                time.sleep(1)
    return b"", {}, None, last_error

def dimension_order_from_structure(xml_bytes: bytes) -> list[str]:
    root = ET.fromstring(xml_bytes)
    candidates = []
    for element in root.iter():
        if local_name(element.tag) != "DataStructure":
            continue
        dims = []
        for child in element.iter():
            kind = local_name(child.tag)
            if kind not in {"Dimension", "TimeDimension"}:
                continue
            dim_id = child.attrib.get("id")
            if not dim_id:
                continue
            pos = int(child.attrib.get("position", "10000"))
            dims.append((pos, dim_id, kind == "TimeDimension"))
        if dims:
            candidates.append(dims)
    for dims in candidates:
        ids = {x[1] for x in dims}
        if {"REF_AREA", "FREQ"} <= ids:
            return [dim for _, dim, is_time in sorted(dims) if not is_time and dim != "TIME_PERIOD"]
    raise ValueError("No matching SDMX DataStructure with REF_AREA and FREQ")

def build_country_key(dimension_order: list[str], *, reference_area: str, frequency: str) -> str:
    values = []
    for dim in dimension_order:
        if dim == "REF_AREA":
            values.append(reference_area)
        elif dim == "FREQ":
            values.append(frequency)
        else:
            values.append("")
    if "REF_AREA" not in dimension_order or "FREQ" not in dimension_order:
        raise ValueError("Required key dimensions are absent")
    return ".".join(values)

def inspect_dimension_rows(data: bytes, dimension_order: list[str]) -> dict:
    text = data.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    header = reader.fieldnames or []
    wanted = set(dimension_order) | {
        "TIME_PERIOD", "SECTOR", "ACCOUNTING_ENTRY", "TRANSACTION",
        "INSTR_ASSET", "UNIT_MEASURE", "UNIT_MULT", "CURRENCY",
        "CURRENCY_DENOM", "CONSOLIDATION", "VALUATION", "PRICE_BASE",
        "REF_AREA", "FREQ",
    }
    code_sets = {key: set() for key in wanted if key in header}
    row_count = 0
    romania_identity_present = False
    for row in reader:
        if not any((v or "").strip() for v in row.values()):
            continue
        row_count += 1
        for key in code_sets:
            value = (row.get(key) or "").strip()
            if value:
                code_sets[key].add(value)
        if (row.get("REF_AREA") or "").strip() == "ROU":
            romania_identity_present = True
    return {
        "header": header,
        "data_row_count": row_count,
        "romania_identity_present": romania_identity_present,
        "dimension_code_sets": {k: sorted(v) for k, v in code_sets.items()},
        "numeric_observation_value_review_performed": False,
    }

def household_coverage(sectors: set[str]) -> str:
    if "S1M" in sectors:
        return "PASS_S1M"
    if {"S14", "S15"} <= sectors:
        return "PASS_EXACT_S14_PLUS_S15_COMPONENTS"
    return "FAIL"

def evaluate_result(result: dict, gate: dict) -> tuple[str, list[str]]:
    blockers = []
    if result["structure_http_status"] != gate["required_structure_http_status"] or result["structure_error"]:
        return "INDETERMINATE", ["structure_access"]
    if result["structure_parse_error"]:
        return "INDETERMINATE", ["structure_parse"]
    if result["data_http_status"] != gate["required_data_http_status"] or result["data_error"]:
        return "INDETERMINATE", ["data_access"]
    if result["csv_data_row_count"] <= 0 or not result["romania_identity_present"]:
        return "FAIL", ["romania_rows"]

    codes = {k: set(v) for k, v in result["dimension_code_sets"].items()}
    sectors = codes.get("SECTOR", set())
    for code in gate["required_reporting_sector_codes"]:
        if code not in sectors:
            blockers.append(f"sector:{code}")
    hh = household_coverage(sectors)
    if hh == "FAIL":
        blockers.append("household_sector")
    if "S2" not in sectors:
        blockers.append("sector:S2")
    instruments = codes.get("INSTR_ASSET", set())
    for code in gate["required_instrument_codes"]:
        if code not in instruments:
            blockers.append(f"instrument:{code}")
    entries = codes.get("ACCOUNTING_ENTRY", set())
    for code in gate["required_accounting_entries"]:
        if code not in entries:
            blockers.append(f"accounting_entry:{code}")
    periods = codes.get("TIME_PERIOD", set())
    for p in gate["required_time_periods"]:
        if p not in periods:
            blockers.append(f"period:{p}")
    if blockers:
        return "FAIL", blockers
    return "PASS", []

def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    scope = contract["query_scope"]
    gate = contract["topology_gate"]
    results = []

    for item in contract["provider"]["dataflows"]:
        structure_body, structure_headers, structure_status, structure_error = fetch(
            item["structure_url"],
            accept="application/vnd.sdmx.structure+xml,application/xml,text/xml,*/*",
        )
        if structure_body:
            (OUT / f'{item["id"]}_structure.xml').write_bytes(structure_body)

        order = []
        query_key = None
        parse_error = None
        if structure_status == 200 and structure_body:
            try:
                order = dimension_order_from_structure(structure_body)
                query_key = build_country_key(order, reference_area=scope["reference_area"], frequency=scope["frequency"])
            except Exception as exc:
                parse_error = f"{type(exc).__name__}:{exc}"

        data_body = b""
        data_headers = {}
        data_status = None
        data_error = None
        data_url = None
        summary = {
            "header": [],
            "data_row_count": 0,
            "romania_identity_present": False,
            "dimension_code_sets": {},
            "numeric_observation_value_review_performed": False,
        }
        if query_key is not None:
            query = urllib.parse.urlencode({
                "startPeriod": scope["start_period"],
                "endPeriod": scope["end_period"],
                "dimensionAtObservation": scope["dimension_at_observation"],
                "format": scope["response_format"],
            })
            data_url = f"{contract['provider']['base_data_url']}/{item['flow_ref']},/{query_key}?{query}"
            data_body, data_headers, data_status, data_error = fetch(
                data_url, accept="text/csv,application/vnd.sdmx.data+csv,*/*"
            )
            if data_body:
                (OUT / f'{item["id"]}_romania.csv').write_bytes(data_body)
            if data_status == 200 and data_body:
                summary = inspect_dimension_rows(data_body, order)

        result = {
            "id": item["id"],
            "flow_ref": item["flow_ref"],
            "structure_url": item["structure_url"],
            "structure_http_status": structure_status,
            "structure_error": structure_error,
            "structure_content_type": structure_headers.get("Content-Type"),
            "structure_bytes": len(structure_body),
            "structure_sha256": sha256(structure_body) if structure_body else None,
            "structure_parse_error": parse_error,
            "dimension_order": order,
            "query_key": query_key,
            "data_url": data_url,
            "data_http_status": data_status,
            "data_error": data_error,
            "data_content_type": data_headers.get("Content-Type"),
            "data_bytes": len(data_body),
            "data_sha256": sha256(data_body) if data_body else None,
            **summary,
        }
        state, blockers = evaluate_result(result, gate)
        result["topology_result_state"] = state
        result["topology_blockers"] = blockers
        results.append(result)

    by_id = {x["id"]: x for x in results}
    required = [by_id.get(x) for x in gate["required_dataflows"]]
    if any(x is None for x in required):
        overall = "INDETERMINATE"
        blockers = ["missing_required_dataflow_result"]
    elif any(x["topology_result_state"] == "INDETERMINATE" for x in required):
        overall = "INDETERMINATE"
        blockers = sorted({b for x in required for b in x["topology_blockers"]})
    elif any(x["topology_result_state"] == "FAIL" for x in required):
        overall = "FAIL"
        blockers = sorted({b for x in required for b in x["topology_blockers"]})
    else:
        period_sets = [set(x["dimension_code_sets"].get("TIME_PERIOD", [])) for x in required]
        common_periods = sorted(set.intersection(*period_sets)) if period_sets else []
        if len(common_periods) < gate["minimum_common_quarters"]:
            overall = "FAIL"
            blockers = [f"common_quarters:{len(common_periods)}<{gate['minimum_common_quarters']}"]
        else:
            overall = "PASS"
            blockers = []

    disposition = {
        "PASS": gate["effect_if_pass"],
        "FAIL": gate["effect_if_fail"],
        "INDETERMINATE": gate["effect_if_indeterminate"],
    }[overall]

    common_periods = []
    if required and all(x is not None for x in required):
        period_sets = [set(x["dimension_code_sets"].get("TIME_PERIOD", [])) for x in required]
        if period_sets:
            common_periods = sorted(set.intersection(*period_sets))

    audit = {
        "audit_version": "0.1",
        "generated_at_utc": datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "phase": contract["phase"],
        "reference_mode": contract["reference_mode"],
        "formal_reference_mode_gate": False,
        "query_scope": scope,
        "results": results,
        "common_time_period_count": len(common_periods),
        "common_time_period_start": common_periods[0] if common_periods else None,
        "common_time_period_end": common_periods[-1] if common_periods else None,
        "required_2025_periods_common": all(p in common_periods for p in gate["required_time_periods"]),
        "topology_gate_result": overall,
        "topology_blockers": blockers,
        "disposition": disposition,
        "numeric_observation_value_review_performed": False,
        "reconciliation_test_performed": False,
        "reference_mode_promotion": False,
        "accounting_reopen": False,
        "parameter_estimation": False,
        "feedback_activation": False,
        "behavioural_closure_change": False,
        "hard_rules": contract["hard_rules"],
    }
    (OUT / "sectoral_financial_positions_oecd_nonconsolidated_probe.json").write_text(
        json.dumps(audit, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps(audit, indent=2, ensure_ascii=False))

if __name__ == "__main__":
    main()
