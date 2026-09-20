#!/usr/bin/env python3
"""Probe preregistered ECB denominator candidates for supply-load diagnostics.

No candidate is selected here. The script retains exact provider responses,
records invalid/empty keys explicitly, and exposes metadata/values only for
semantic boundary comparison.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "model/dynamics/government_securities_supply_load_ecb_denominator_probe_contract.json"
)
SCRIPT_PATH = Path(__file__).resolve()


def sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def load_contract() -> dict:
    return json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))


def parse_csv_payload(payload: bytes) -> dict:
    text = payload.decode("utf-8-sig", errors="replace")
    reader = csv.DictReader(io.StringIO(text))
    fieldnames = reader.fieldnames or []
    rows = list(reader)
    periods = []
    values = []
    for row in rows:
        period = row.get("TIME_PERIOD")
        value = row.get("OBS_VALUE")
        if period:
            periods.append(period)
        if value not in (None, ""):
            try:
                values.append(float(value))
            except ValueError:
                pass
    return {
        "columns": fieldnames,
        "row_count": len(rows),
        "time_periods": periods,
        "numeric_observation_count": len(values),
        "numeric_observations": values,
    }


def fetch_candidate(candidate: dict, contract: dict, out_dir: Path) -> dict:
    acquisition = contract["acquisition"]
    query = urlencode(
        {
            "startPeriod": contract["period_window"]["start"],
            "endPeriod": contract["period_window"]["end"],
            "format": acquisition["format"],
        }
    )
    url = (
        f"{acquisition['base_url']}/{candidate['dataset']}/"
        f"{candidate['series_key']}?{query}"
    )
    request = Request(
        url,
        headers={
            "Accept": acquisition["accept"],
            "User-Agent": (
                "Romanian-Monetary-Dynamics-source-probe/0.1 "
                "(https://github.com/LaurentiuStaicu/romanian-monetary-dynamics)"
            ),
        },
    )

    raw_dir = out_dir / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)
    safe_name = candidate["candidate_id"] + ".csv"
    raw_path = raw_dir / safe_name

    try:
        with urlopen(request, timeout=90) as response:
            status = int(response.getcode())
            payload = response.read()
            response_meta = {
                "content_type": response.headers.get("Content-Type"),
                "last_modified": response.headers.get("Last-Modified"),
                "etag": response.headers.get("ETag"),
            }
    except HTTPError as exc:
        body = exc.read()
        return {
            "candidate_id": candidate["candidate_id"],
            "dataset": candidate["dataset"],
            "series_key": candidate["series_key"],
            "full_series_id": candidate["full_series_id"],
            "request_url": url,
            "http_status": int(exc.code),
            "transport_ok": False,
            "valid_nonempty_csv": False,
            "error_body_sha256": sha256_bytes(body),
            "error_body_preview": body.decode("utf-8", errors="replace")[:500],
            "eligible_for_selection_now": False,
        }
    except URLError as exc:
        return {
            "candidate_id": candidate["candidate_id"],
            "dataset": candidate["dataset"],
            "series_key": candidate["series_key"],
            "full_series_id": candidate["full_series_id"],
            "request_url": url,
            "http_status": None,
            "transport_ok": False,
            "valid_nonempty_csv": False,
            "transport_error": str(exc.reason),
            "eligible_for_selection_now": False,
        }

    raw_path.write_bytes(payload)
    parsed = parse_csv_payload(payload)
    valid = (
        status == 200
        and parsed["row_count"] > 0
        and "TIME_PERIOD" in parsed["columns"]
        and "OBS_VALUE" in parsed["columns"]
    )
    return {
        "candidate_id": candidate["candidate_id"],
        "dataset": candidate["dataset"],
        "series_key": candidate["series_key"],
        "full_series_id": candidate["full_series_id"],
        "expected_semantics": candidate["expected_semantics"],
        "role": candidate.get("role"),
        "request_url": url,
        "http_status": status,
        "transport_ok": True,
        "response_metadata": response_meta,
        "raw_path": f"raw/{safe_name}",
        "raw_bytes": len(payload),
        "raw_sha256": sha256_bytes(payload),
        "valid_nonempty_csv": valid,
        "csv": parsed,
        "eligible_for_selection_now": False,
    }


def run_probe(out_dir: Path) -> dict:
    contract = load_contract()
    out_dir.mkdir(parents=True, exist_ok=True)
    results = [
        fetch_candidate(candidate, contract, out_dir)
        for candidate in contract["candidates"]
    ]
    valid_count = sum(bool(item["valid_nonempty_csv"]) for item in results)
    manifest = {
        "snapshot_id": "ecb-supply-load-denominator-candidates-2026-09-20",
        "fetched_at_utc": (
            datetime.now(timezone.utc).replace(microsecond=0).isoformat()
        ),
        "contract": str(CONTRACT_PATH.relative_to(ROOT)),
        "fetcher_script": str(SCRIPT_PATH.relative_to(ROOT)),
        "fetcher_script_sha256": sha256_file(SCRIPT_PATH),
        "period_window": contract["period_window"],
        "candidates": results,
        "valid_candidate_count": valid_count,
        "candidate_count": len(results),
        "denominator_selected": False,
        "selection_guards": contract["selection_guards"],
        "scientific_guards": contract["scientific_guards"],
        "status": (
            "PROBE_COMPLETE_AT_LEAST_ONE_VALID_CANDIDATE"
            if valid_count
            else "PROBE_COMPLETE_NO_VALID_CANDIDATE_KEYS"
        ),
    }
    manifest_path = out_dir / "ecb_denominator_probe_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(
        json.dumps(
            {
                "status": manifest["status"],
                "valid_candidate_count": valid_count,
                "candidates": [
                    {
                        "candidate_id": item["candidate_id"],
                        "http_status": item["http_status"],
                        "valid_nonempty_csv": item["valid_nonempty_csv"],
                        "row_count": item.get("csv", {}).get("row_count"),
                        "time_periods": item.get("csv", {}).get("time_periods"),
                    }
                    for item in results
                ],
                "denominator_selected": False,
                "feedback_activation_authorized": False,
            },
            indent=2,
        )
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="ecb_supply_load_denominator_probe_artifacts",
    )
    args = parser.parse_args()
    run_probe(Path(args.output))


if __name__ == "__main__":
    main()
