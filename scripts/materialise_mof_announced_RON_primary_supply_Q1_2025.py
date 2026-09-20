#!/usr/bin/env python3
"""Materialise the exact Q1 2025 announced-RON primary-supply pilot.

Reads only repository-retained Ministry PDFs/native text and the frozen source
contract. It performs no OCR, no manual approximation, no yield-effect
estimation and no feedback activation.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import re
import unicodedata
from collections import defaultdict
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = ROOT / (
    "model/dynamics/"
    "mof_announced_RON_primary_supply_reference_mode_contract_2026_09_20.json"
)
VINTAGE_ROOT = ROOT / (
    "data/source_vintages/"
    "mof-announced-ron-primary-supply-pilot-2026-09-20"
)
MANIFEST_PATH = VINTAGE_ROOT / "source_vintage_manifest.json"
FLASH_ASSESSMENT_PATH = ROOT / (
    "model/dynamics/"
    "government_securities_supply_pressure_source_vintage_probe_assessment_2026_09_20.json"
)

T_BILL_ROW = re.compile(
    r"^\s*(RO[A-Z0-9]{10})\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"
    r"(\d+)\s+([\d,]+)\s*$"
)

BOND_ROW = re.compile(
    r"^\s*(RO[A-Z0-9]{10})\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"
    r"(\d+)\s+([0-9]+(?:\.[0-9]+)?)\s+"
    r"([0-9]+(?:\.[0-9]+)?)\s+"
    r"([0-9]+(?:\.[0-9]+)?)\s+"
    r"([\d,]+)\s+([\d,]+)\s*$"
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def normalized(text: str) -> str:
    decomposed = unicodedata.normalize("NFKD", text)
    without_marks = "".join(
        char for char in decomposed
        if not unicodedata.combining(char)
    )
    return " ".join(without_marks.split()).casefold()


def iso_date(value: str) -> str:
    return datetime.strptime(value, "%d/%m/%Y").date().isoformat()


def parse_ron_integer(value: str) -> int:
    return int(value.replace(",", ""))


def parse_article_1_totals(text: str) -> tuple[float, float]:
    n = normalized(text)
    match = re.search(
        r"valoare nominala totala de ([0-9.]+) milioane lei, "
        r"la care se poate adauga suma de ([0-9.]+) milioane lei",
        n,
    )
    if not match:
        raise RuntimeError("could not parse Article 1 base/SSON totals")
    base = float(match.group(1).replace(".", ""))
    sson = float(match.group(2).replace(".", ""))
    return base, sson


def split_annexes(text: str) -> tuple[str, str]:
    m1 = re.search(r"\bAnexa\s+1\b", text, flags=re.IGNORECASE)
    if not m1:
        raise RuntimeError("Annex 1 marker not found")
    m2 = re.search(r"\bAnexa\s+2\b", text[m1.end():], flags=re.IGNORECASE)
    if not m2:
        raise RuntimeError("Annex 2 marker not found")
    m2_start = m1.end() + m2.start()
    return text[m1.end():m2_start], text[m2_start:]


def base_lineage(source: dict, annex: str, row_number: int) -> dict:
    return {
        "source_id": source["source_id"],
        "source_url": source["url"],
        "source_order_number": source["order_number"],
        "source_order_issue_date": source["order_issue_date"],
        "source_annex": annex,
        "source_row_number": row_number,
    }


def parse_source_events(source: dict, text: str) -> tuple[list[dict], dict]:
    annex1, annex2 = split_annexes(text)
    events: list[dict] = []

    t_bill_rows = []
    for line in annex1.splitlines():
        match = T_BILL_ROW.match(line)
        if match:
            t_bill_rows.append(match.groups())
    if not t_bill_rows:
        raise RuntimeError(f"{source['source_id']}: no Annex 1 rows parsed")

    for row_number, row in enumerate(t_bill_rows, start=1):
        isin, auction, issue, maturity, days, amount = row
        amount_ron = parse_ron_integer(amount)
        event = {
            **base_lineage(source, "Annex 1", row_number),
            "event_type": "T_BILL_COMPETITIVE_REFERENCE_AUCTION",
            "event_date": iso_date(auction),
            "instrument_type": "DISCOUNT_TREASURY_BILL",
            "instrument_identity": isin,
            "isin": isin,
            "currency": "RON",
            "announced_nominal_RON": amount_ron,
            "announced_nominal_RON_million": amount_ron / 1_000_000,
            "issue_date": iso_date(issue),
            "maturity_date": iso_date(maturity),
            "original_maturity_days_or_years": int(days),
            "original_maturity_unit": "days",
            "residual_maturity_years": None,
            "coupon_pct": None,
            "accrued_interest_RON_per_security": None,
        }
        events.append(event)

    bond_rows = []
    for line in annex2.splitlines():
        match = BOND_ROW.match(line)
        if match:
            bond_rows.append(match.groups())
    if not bond_rows:
        raise RuntimeError(f"{source['source_id']}: no Annex 2 rows parsed")

    for row_number, row in enumerate(bond_rows, start=1):
        (
            isin,
            auction,
            sson_date,
            issue,
            maturity,
            original_years,
            residual_years,
            coupon,
            accrued,
            ref_amount,
            sson_amount,
        ) = row
        common = {
            "instrument_type": "BENCHMARK_GOVERNMENT_BOND",
            "instrument_identity": isin,
            "isin": isin,
            "currency": "RON",
            "issue_date": iso_date(issue),
            "maturity_date": iso_date(maturity),
            "original_maturity_days_or_years": int(original_years),
            "original_maturity_unit": "years",
            "residual_maturity_years": float(residual_years),
            "coupon_pct": float(coupon),
            "accrued_interest_RON_per_security": float(accrued),
        }
        ref_ron = parse_ron_integer(ref_amount)
        events.append(
            {
                **base_lineage(source, "Annex 2", row_number),
                **common,
                "event_type": "BENCHMARK_BOND_COMPETITIVE_REFERENCE_AUCTION",
                "event_date": iso_date(auction),
                "announced_nominal_RON": ref_ron,
                "announced_nominal_RON_million": ref_ron / 1_000_000,
            }
        )
        sson_ron = parse_ron_integer(sson_amount)
        events.append(
            {
                **base_lineage(source, "Annex 2", row_number),
                **common,
                "event_type": "BENCHMARK_BOND_SSON",
                "event_date": iso_date(sson_date),
                "announced_nominal_RON": sson_ron,
                "announced_nominal_RON_million": sson_ron / 1_000_000,
            }
        )

    parsed_base = sum(
        event["announced_nominal_RON_million"]
        for event in events
        if event["event_type"] != "BENCHMARK_BOND_SSON"
    )
    parsed_sson = sum(
        event["announced_nominal_RON_million"]
        for event in events
        if event["event_type"] == "BENCHMARK_BOND_SSON"
    )
    article_base, article_sson = parse_article_1_totals(text)
    reconciliation = {
        "source_id": source["source_id"],
        "parsed_t_bill_rows": len(t_bill_rows),
        "parsed_bond_rows": len(bond_rows),
        "parsed_event_count": len(events),
        "article_1_base_nominal_RON_million_from_native_text": article_base,
        "article_1_SSON_max_RON_million_from_native_text": article_sson,
        "parsed_base_nominal_RON_million": parsed_base,
        "parsed_SSON_RON_million": parsed_sson,
        "parsed_document_total_RON_million": parsed_base + parsed_sson,
        "base_reconciles": parsed_base == article_base == source[
            "article_1_base_nominal_RON_million"
        ],
        "SSON_reconciles": parsed_sson == article_sson == source[
            "article_1_SSON_max_RON_million"
        ],
        "document_total_reconciles": (
            parsed_base + parsed_sson
            == source["article_1_document_total_RON_million"]
        ),
    }
    return events, reconciliation


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def materialise(out_dir: Path) -> dict:
    contract = load_json(CONTRACT_PATH)
    manifest = load_json(MANIFEST_PATH)
    flash = load_json(FLASH_ASSESSMENT_PATH)

    if manifest["contract"] != str(CONTRACT_PATH.relative_to(ROOT)):
        raise RuntimeError("retained source vintage is bound to a different contract")
    if manifest["all_required_anchor_checks_pass"] is not True:
        raise RuntimeError("retained source-vintage anchor gate is not PASS")

    source_manifest = {
        item["source_id"]: item for item in manifest["sources"]
    }
    if set(source_manifest) != {
        item["source_id"] for item in contract["pilot_source_documents"]
    }:
        raise RuntimeError("retained source-vintage document set differs from contract")

    all_events: list[dict] = []
    reconciliations: list[dict] = []
    source_identities: dict[str, dict] = {}

    for source in contract["pilot_source_documents"]:
        retained = source_manifest[source["source_id"]]
        raw_path = VINTAGE_ROOT / retained["raw_path"]
        text_path = VINTAGE_ROOT / retained["native_text_path"]
        if sha256_file(raw_path) != retained["raw_sha256"]:
            raise RuntimeError(f"{source['source_id']}: retained raw hash changed")
        if sha256_file(text_path) != retained["native_text_sha256"]:
            raise RuntimeError(f"{source['source_id']}: retained text hash changed")

        text = text_path.read_text(encoding="utf-8")
        events, reconciliation = parse_source_events(source, text)
        if not (
            reconciliation["base_reconciles"]
            and reconciliation["SSON_reconciles"]
            and reconciliation["document_total_reconciles"]
        ):
            raise RuntimeError(
                f"{source['source_id']}: parsed rows fail Article 1 reconciliation"
            )
        all_events.extend(events)
        reconciliations.append(reconciliation)
        source_identities[source["source_id"]] = {
            "raw_bytes": retained["raw_bytes"],
            "raw_sha256": retained["raw_sha256"],
            "native_text_bytes": retained["native_text_bytes"],
            "native_text_sha256": retained["native_text_sha256"],
            "http_last_modified": retained["response_metadata"]["last_modified"],
            "etag": retained["response_metadata"]["etag"],
        }

    by_source = {item["source_id"]: item for item in reconciliations}
    if by_source["mof_order_6826_january_2025"][
        "parsed_document_total_RON_million"
    ] != flash["extractability_results"]["flash_auction_table_native_text"][
        "january_2025"
    ]["total_announced_RON_million"]:
        raise RuntimeError("January prospectus total differs from retained Flash total")
    if by_source["mof_order_159_february_2025"][
        "parsed_document_total_RON_million"
    ] != flash["extractability_results"]["flash_auction_table_native_text"][
        "february_2025"
    ]["total_announced_RON_million"]:
        raise RuntimeError("February prospectus total differs from retained Flash schedule")

    cutoff = date.fromisoformat(contract["completed_period_rules"]["pilot_cutoff_date"])
    for event in all_events:
        event["within_pilot_cutoff"] = date.fromisoformat(event["event_date"]) <= cutoff

    all_events.sort(
        key=lambda x: (
            x["event_date"],
            x["source_order_number"],
            x["source_annex"],
            x["source_row_number"],
            x["event_type"],
        )
    )

    monthly = defaultdict(float)
    monthly_counts = defaultdict(int)
    for event in all_events:
        if event["within_pilot_cutoff"]:
            month = event["event_date"][:7]
            monthly[month] += event["announced_nominal_RON_million"]
            monthly_counts[month] += 1

    monthly_rows = [
        {
            "period": period,
            "announced_RON_primary_supply_million": monthly[period],
            "event_count": monthly_counts[period],
            "status": "COMPLETED_PERIOD_EXACT_EVENT_SUM",
        }
        for period in sorted(monthly)
    ]

    expected_monthly = {
        "2025-01": 5770.0,
        "2025-02": 8040.0,
        "2025-03": 8165.0,
    }
    observed_monthly = {
        row["period"]: row["announced_RON_primary_supply_million"]
        for row in monthly_rows
    }
    if observed_monthly != expected_monthly:
        raise RuntimeError(
            f"completed-period monthly sums changed: {observed_monthly}"
        )

    forward_events = [
        event for event in all_events if not event["within_pilot_cutoff"]
    ]
    if len(forward_events) != 1:
        raise RuntimeError(
            f"expected exactly one post-cutoff announced event, observed {len(forward_events)}"
        )
    only_forward = forward_events[0]
    if not (
        only_forward["event_date"] == "2025-04-01"
        and only_forward["event_type"] == "BENCHMARK_BOND_SSON"
        and only_forward["announced_nominal_RON_million"] == 75.0
    ):
        raise RuntimeError("post-cutoff event identity changed")

    event_fields = [
        "source_id",
        "source_url",
        "source_order_number",
        "source_order_issue_date",
        "source_annex",
        "source_row_number",
        "event_type",
        "event_date",
        "instrument_type",
        "instrument_identity",
        "isin",
        "currency",
        "announced_nominal_RON",
        "announced_nominal_RON_million",
        "issue_date",
        "maturity_date",
        "original_maturity_days_or_years",
        "original_maturity_unit",
        "residual_maturity_years",
        "coupon_pct",
        "accrued_interest_RON_per_security",
        "within_pilot_cutoff",
    ]
    events_path = out_dir / "mof_announced_RON_primary_supply_Q1_2025_events.csv"
    monthly_path = out_dir / "mof_announced_RON_primary_supply_Q1_2025_monthly.csv"
    write_csv(events_path, all_events, event_fields)
    write_csv(
        monthly_path,
        monthly_rows,
        [
            "period",
            "announced_RON_primary_supply_million",
            "event_count",
            "status",
        ],
    )

    assessment = {
        "pilot_version": "0.1",
        "assessed_on": "2026-09-20",
        "reference_mode_id": "announced_RON_primary_supply_level",
        "status": "PASS_EXACT_Q1_EVENT_LEVEL_PILOT_CANONICAL_PROMOTION_DEFERRED",
        "contract": str(CONTRACT_PATH.relative_to(ROOT)),
        "source_vintage_manifest": str(MANIFEST_PATH.relative_to(ROOT)),
        "source_identities": source_identities,
        "event_level_series": "data/processed/mof_announced_RON_primary_supply_Q1_2025_events.csv",
        "monthly_series": "data/processed/mof_announced_RON_primary_supply_Q1_2025_monthly.csv",
        "pilot_cutoff_date": cutoff.isoformat(),
        "document_reconciliation": reconciliations,
        "coverage": {
            "source_orders": 3,
            "event_rows_total_including_forward_schedule": len(all_events),
            "completed_event_rows_through_cutoff": sum(
                bool(event["within_pilot_cutoff"]) for event in all_events
            ),
            "forward_events_after_cutoff": len(forward_events),
            "completed_months": [row["period"] for row in monthly_rows],
        },
        "completed_monthly_reference_mode": observed_monthly,
        "forward_schedule_not_in_completed_reference_mode": [
            {
                "event_date": event["event_date"],
                "event_type": event["event_type"],
                "isin": event["isin"],
                "announced_nominal_RON_million": event[
                    "announced_nominal_RON_million"
                ],
                "source_id": event["source_id"],
            }
            for event in forward_events
        ],
        "crosschecks": {
            "january_flash_announced_total_RON_million": 5770.0,
            "january_crosscheck": "PASS_EXACT",
            "february_flash_announced_schedule_total_RON_million": 8040.0,
            "february_crosscheck": "PASS_EXACT",
            "march_document_total_RON_million": 8240.0,
            "march_completed_period_RON_million": 8165.0,
            "march_difference_due_to_2025_04_01_SSON_RON_million": 75.0,
        },
        "semantics": {
            "ex_ante_announced_supply_only": True,
            "accepted_or_borrowed_amount_included": False,
            "submitted_bids_included": False,
            "retail_issuance_included": False,
            "external_issuance_included": False,
            "stock_normalisation_used": False,
            "supply_surprise_constructed": False,
            "duration_supply_constructed": False,
        },
        "scientific_disposition": {
            "exact_event_level_pilot_materialised": True,
            "exact_completed_monthly_pilot_materialised": True,
            "canonical_reference_modes_registry_promoted": False,
            "reason_canonical_promotion_deferred": (
                "The Q1 pilot validates event-level semantics and reconciliation, "
                "but canonical reference-mode promotion is deferred until the same "
                "contract is extended across the completed 2025 source horizon."
            ),
            "government_securities_supply_pressure_node_resolved": False,
            "single_supply_pressure_scalar_selected": False,
            "yield_effect_estimation_authorized": False,
            "feedback_activation_authorized": False,
            "behavioural_closure_authorized": False,
            "public_version_change_authorized": False,
        },
        "next_gate": {
            "id": "mof_announced_RON_primary_supply_full_2025_extension",
            "authorization": "SOURCE_VINTAGE_EXTENSION_AND_EXACT_EVENT_MATERIALISATION_ONLY",
            "task": (
                "Extend the same frozen event schema and reconciliation rules to "
                "April-December 2025 Ministry monthly issuance orders, retaining "
                "exact raw PDFs/native text and preserving event-date bucketing."
            ),
            "may_promote_canonical_reference_mode_after_full_2025_reconciliation": True,
            "may_estimate_supply_to_yield_effect": False,
            "may_activate_feedback": False,
        },
    }
    assessment_path = out_dir / "mof_announced_RON_primary_supply_reference_mode_pilot_Q1_2025.json"
    assessment_path.write_text(
        json.dumps(assessment, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": assessment["status"],
                "event_rows_total": len(all_events),
                "completed_event_rows": assessment["coverage"][
                    "completed_event_rows_through_cutoff"
                ],
                "monthly_reference_mode": observed_monthly,
                "forward_event": assessment[
                    "forward_schedule_not_in_completed_reference_mode"
                ],
                "canonical_reference_mode_promoted": False,
                "feedback_activation_authorized": False,
                "next_gate": assessment["next_gate"]["id"],
            },
            indent=2,
        )
    )
    return assessment


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--output",
        default="mof_announced_supply_materialised",
    )
    args = parser.parse_args()
    out_dir = Path(args.output)
    out_dir.mkdir(parents=True, exist_ok=True)
    materialise(out_dir)


if __name__ == "__main__":
    main()
