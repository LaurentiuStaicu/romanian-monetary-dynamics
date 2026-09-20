#!/usr/bin/env python3
"""Materialise the Q1 2025 announced-RON primary-supply pilot from retained native text."""

from __future__ import annotations

import argparse
import csv
import json
import re
from collections import defaultdict
from datetime import datetime
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    ROOT
    / "model/dynamics/mof_announced_RON_primary_supply_reference_mode_contract_2026_09_20.json"
)

TBILL_RE = re.compile(
    r"^\s*(RO[A-Z0-9]{10})\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"
    r"(\d+)\s+([\d,]+)\s*$",
    re.MULTILINE,
)

BENCH_RE = re.compile(
    r"^\s*(RO[A-Z0-9]{10})\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"
    r"(\d{2}/\d{2}/\d{4})\s+"
    r"(\d+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+"
    r"([\d,]+)\s+([\d,]+)\s*$",
    re.MULTILINE,
)

ARTICLE1_RE = re.compile(
    r"valoare nominală totală de\s+([\d.]+)\s*milioane\s+lei,\s*"
    r"la care se poate adăuga suma de\s+([\d.]+)\s*milioane\s+lei",
    re.IGNORECASE | re.DOTALL,
)


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def parse_date(value: str) -> datetime:
    return datetime.strptime(value, "%d/%m/%Y")


def iso_date(value: str) -> str:
    return parse_date(value).date().isoformat()


def ron_million(value: str) -> Decimal:
    return Decimal(value.replace(",", "")) / Decimal("1000000")


def article_million(value: str) -> Decimal:
    return Decimal(value.replace(".", ""))


def dstr(value: Decimal) -> str:
    return format(value.quantize(Decimal("0.001")), "f")


def extract_document(text: str, doc: dict, cutoff: datetime) -> tuple[list[dict], dict]:
    article = ARTICLE1_RE.search(text)
    if not article:
        raise RuntimeError(f"{doc['source_id']}: Article 1 totals not found")
    printed_base = article_million(article.group(1))
    printed_sson = article_million(article.group(2))

    t_rows = list(TBILL_RE.finditer(text))
    b_rows = list(BENCH_RE.finditer(text))
    if not t_rows:
        raise RuntimeError(f"{doc['source_id']}: no Annex 1 T-bill rows parsed")
    if not b_rows:
        raise RuntimeError(f"{doc['source_id']}: no Annex 2 benchmark rows parsed")

    events: list[dict] = []
    t_total = Decimal("0")
    b_comp_total = Decimal("0")
    b_sson_total = Decimal("0")

    for row_number, match in enumerate(t_rows, start=1):
        isin, auction, issue, maturity, days, amount = match.groups()
        amount_m = ron_million(amount)
        t_total += amount_m
        event_date = iso_date(auction)
        events.append(
            {
                "source_id": doc["source_id"],
                "source_order_number": doc["order_number"],
                "source_order_issue_date": doc["order_issue_date"],
                "source_annex": "1",
                "source_row_number": row_number,
                "event_type": "T_BILL_COMPETITIVE_REFERENCE_AUCTION",
                "event_date": event_date,
                "instrument_type": "T_BILL_DISCOUNT",
                "instrument_identity": isin,
                "isin": isin,
                "currency": "RON",
                "announced_nominal_RON_million": dstr(amount_m),
                "auction_date": event_date,
                "sson_date": "",
                "issue_date": iso_date(issue),
                "maturity_date": iso_date(maturity),
                "original_maturity": days,
                "original_maturity_unit": "days",
                "residual_maturity_years": "",
                "coupon_pct": "",
                "accrued_interest_RON_per_security": "",
                "completed_by_cutoff": parse_date(auction) <= cutoff,
            }
        )

    for row_number, match in enumerate(b_rows, start=1):
        (
            isin,
            auction,
            sson,
            issue,
            maturity,
            years,
            residual,
            coupon,
            accrued,
            comp_amount,
            sson_amount,
        ) = match.groups()
        comp_m = ron_million(comp_amount)
        sson_m = ron_million(sson_amount)
        b_comp_total += comp_m
        b_sson_total += sson_m

        common = {
            "source_id": doc["source_id"],
            "source_order_number": doc["order_number"],
            "source_order_issue_date": doc["order_issue_date"],
            "source_annex": "2",
            "source_row_number": row_number,
            "instrument_type": "BENCHMARK_BOND",
            "instrument_identity": isin,
            "isin": isin,
            "currency": "RON",
            "auction_date": iso_date(auction),
            "sson_date": iso_date(sson),
            "issue_date": iso_date(issue),
            "maturity_date": iso_date(maturity),
            "original_maturity": years,
            "original_maturity_unit": "years",
            "residual_maturity_years": residual,
            "coupon_pct": coupon,
            "accrued_interest_RON_per_security": accrued,
        }
        competitive_date = iso_date(auction)
        events.append(
            {
                **common,
                "event_type": "BENCHMARK_BOND_COMPETITIVE_REFERENCE_AUCTION",
                "event_date": competitive_date,
                "announced_nominal_RON_million": dstr(comp_m),
                "completed_by_cutoff": parse_date(auction) <= cutoff,
            }
        )
        sson_date = iso_date(sson)
        events.append(
            {
                **common,
                "event_type": "BENCHMARK_BOND_SSON",
                "event_date": sson_date,
                "announced_nominal_RON_million": dstr(sson_m),
                "completed_by_cutoff": parse_date(sson) <= cutoff,
            }
        )

    expected_base = Decimal(str(doc["article_1_base_nominal_RON_million"]))
    expected_sson = Decimal(str(doc["article_1_SSON_max_RON_million"]))
    expected_total = Decimal(str(doc["article_1_document_total_RON_million"]))
    parsed_base = t_total + b_comp_total
    parsed_total = parsed_base + b_sson_total

    checks = {
        "printed_base_matches_contract": printed_base == expected_base,
        "printed_SSON_matches_contract": printed_sson == expected_sson,
        "annex1_plus_annex2_competitive_matches_article1_base": (
            parsed_base == expected_base
        ),
        "annex2_SSON_matches_article1_SSON": b_sson_total == expected_sson,
        "all_event_rows_match_article1_combined": parsed_total == expected_total,
    }
    if not all(checks.values()):
        raise RuntimeError(
            f"{doc['source_id']}: document reconciliation failed: {checks}"
        )

    return events, {
        "source_id": doc["source_id"],
        "order_number": doc["order_number"],
        "order_issue_date": doc["order_issue_date"],
        "t_bill_row_count": len(t_rows),
        "benchmark_row_count": len(b_rows),
        "t_bill_competitive_RON_million": float(t_total),
        "benchmark_competitive_RON_million": float(b_comp_total),
        "benchmark_SSON_RON_million": float(b_sson_total),
        "parsed_base_RON_million": float(parsed_base),
        "parsed_combined_RON_million": float(parsed_total),
        "expected_base_RON_million": float(expected_base),
        "expected_SSON_RON_million": float(expected_sson),
        "expected_combined_RON_million": float(expected_total),
        "checks": checks,
    }


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--source-root", required=True)
    parser.add_argument("--events-out", required=True)
    parser.add_argument("--monthly-out", required=True)
    parser.add_argument("--assessment-out", required=True)
    args = parser.parse_args()

    source_root = Path(args.source_root)
    contract = load_json(CONTRACT_PATH)
    manifest = load_json(source_root / "source_vintage_manifest.json")
    cutoff = datetime.strptime(
        contract["completed_period_rules"]["pilot_cutoff_date"], "%Y-%m-%d"
    )

    all_events: list[dict] = []
    reconciliations: list[dict] = []
    for doc in contract["pilot_source_documents"]:
        text_path = source_root / "native_text" / f"{doc['source_id']}.txt"
        text = text_path.read_text(encoding="utf-8")
        events, reconciliation = extract_document(text, doc, cutoff)
        all_events.extend(events)
        reconciliations.append(reconciliation)

    all_events.sort(
        key=lambda row: (
            row["event_date"],
            row["event_type"],
            row["instrument_identity"],
        )
    )

    monthly = defaultdict(
        lambda: {
            "event_count": 0,
            "T_BILL_COMPETITIVE_REFERENCE_AUCTION": Decimal("0"),
            "BENCHMARK_BOND_COMPETITIVE_REFERENCE_AUCTION": Decimal("0"),
            "BENCHMARK_BOND_SSON": Decimal("0"),
        }
    )
    forward_events = []
    for row in all_events:
        if not row["completed_by_cutoff"]:
            forward_events.append(row)
            continue
        month = row["event_date"][:7]
        bucket = monthly[month]
        bucket["event_count"] += 1
        bucket[row["event_type"]] += Decimal(row["announced_nominal_RON_million"])

    monthly_rows = []
    for month in sorted(monthly):
        bucket = monthly[month]
        total = (
            bucket["T_BILL_COMPETITIVE_REFERENCE_AUCTION"]
            + bucket["BENCHMARK_BOND_COMPETITIVE_REFERENCE_AUCTION"]
            + bucket["BENCHMARK_BOND_SSON"]
        )
        monthly_rows.append(
            {
                "month": month,
                "announced_RON_primary_supply_million": dstr(total),
                "event_count": bucket["event_count"],
                "t_bill_competitive_RON_million": dstr(
                    bucket["T_BILL_COMPETITIVE_REFERENCE_AUCTION"]
                ),
                "benchmark_competitive_RON_million": dstr(
                    bucket["BENCHMARK_BOND_COMPETITIVE_REFERENCE_AUCTION"]
                ),
                "benchmark_SSON_RON_million": dstr(
                    bucket["BENCHMARK_BOND_SSON"]
                ),
                "status": "COMPLETED_PERIOD_EXACT_EVENT_AGGREGATION",
            }
        )

    expected_monthly = {
        "2025-01": Decimal("5770"),
        "2025-02": Decimal("8040"),
        "2025-03": Decimal("8165"),
    }
    observed_monthly = {
        row["month"]: Decimal(row["announced_RON_primary_supply_million"])
        for row in monthly_rows
    }
    if observed_monthly != expected_monthly:
        raise RuntimeError(
            f"monthly pilot values changed: {observed_monthly!r}"
        )

    if len(forward_events) != 1:
        raise RuntimeError(
            f"expected one post-cutoff forward event, found {len(forward_events)}"
        )
    forward = forward_events[0]
    if not (
        forward["event_type"] == "BENCHMARK_BOND_SSON"
        and forward["event_date"] == "2025-04-01"
        and Decimal(forward["announced_nominal_RON_million"]) == Decimal("75")
        and forward["instrument_identity"] == "RO45DLJ4EE76"
    ):
        raise RuntimeError(f"unexpected post-cutoff forward event: {forward}")

    event_fields = [
        "source_id",
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
        "announced_nominal_RON_million",
        "auction_date",
        "sson_date",
        "issue_date",
        "maturity_date",
        "original_maturity",
        "original_maturity_unit",
        "residual_maturity_years",
        "coupon_pct",
        "accrued_interest_RON_per_security",
        "completed_by_cutoff",
    ]
    monthly_fields = [
        "month",
        "announced_RON_primary_supply_million",
        "event_count",
        "t_bill_competitive_RON_million",
        "benchmark_competitive_RON_million",
        "benchmark_SSON_RON_million",
        "status",
    ]
    write_csv(Path(args.events_out), all_events, event_fields)
    write_csv(Path(args.monthly_out), monthly_rows, monthly_fields)

    source_by_id = {item["source_id"]: item for item in manifest["sources"]}
    assessment = {
        "assessment_version": "0.1",
        "assessed_on": "2026-09-20",
        "reference_mode_id": "announced_RON_primary_supply_level",
        "contract": str(CONTRACT_PATH.relative_to(ROOT)),
        "retained_source_vintage": (
            "data/source_vintages/"
            "mof-announced-ron-primary-supply-pilot-2026-09-20/"
            "source_vintage_manifest.json"
        ),
        "source_identity": {
            source_id: {
                "raw_sha256": item["raw_sha256"],
                "native_text_sha256": item["native_text_sha256"],
                "raw_bytes": item["raw_bytes"],
                "response_metadata": item["response_metadata"],
            }
            for source_id, item in sorted(source_by_id.items())
        },
        "document_reconciliations": reconciliations,
        "event_level_pilot": {
            "artifact": "data/processed/government_securities_announced_RON_primary_supply_2025Q1_events.csv",
            "event_count_all_scheduled": len(all_events),
            "event_count_completed_by_cutoff": sum(
                bool(row["completed_by_cutoff"]) for row in all_events
            ),
            "cutoff_date": contract["completed_period_rules"]["pilot_cutoff_date"],
            "post_cutoff_forward_event_count": len(forward_events),
            "post_cutoff_forward_events": [
                {
                    "event_date": row["event_date"],
                    "event_type": row["event_type"],
                    "isin": row["isin"],
                    "announced_nominal_RON_million": float(
                        Decimal(row["announced_nominal_RON_million"])
                    ),
                    "source_id": row["source_id"],
                }
                for row in forward_events
            ],
        },
        "monthly_pilot": {
            "artifact": "data/processed/government_securities_announced_RON_primary_supply_2025Q1_monthly.csv",
            "values_RON_million": {
                row["month"]: float(
                    Decimal(row["announced_RON_primary_supply_million"])
                )
                for row in monthly_rows
            },
            "january_flash_crosscheck": "PASS_5770",
            "february_flash_announced_schedule_crosscheck": "PASS_8040",
            "march_order_total_not_equal_march_event_month_by_design": True,
            "march_difference_RON_million": 75.0,
            "march_difference_reason": (
                "RO45DLJ4EE76 SSON belongs to 2025-04-01 under the frozen "
                "event-date aggregation rule."
            ),
        },
        "pilot_result": {
            "status": "PASS_EXACT_EVENT_LEVEL_AND_MONTHLY_Q1_PILOT",
            "raw_source_retention_complete": True,
            "native_text_extraction_complete": True,
            "all_document_reconciliations_pass": True,
            "monthly_event_date_aggregation_pass": True,
            "reference_mode_pilot_materialised": True,
            "full_reference_mode_promoted": False,
        },
        "scientific_effect": {
            "supply_surprise_materialised": False,
            "duration_supply_materialised": False,
            "yield_effect_estimation_authorized": False,
            "government_securities_supply_pressure_node_resolved": False,
            "feedback_activation_authorized": False,
            "behavioural_closure_authorized": False,
            "public_version_change_authorized": False,
        },
        "next_gate": {
            "id": "mof_announced_RON_primary_supply_full_2025_extension_contract",
            "authorization": "SOURCE_EXTENSION_AND_REFERENCE_MODE_MATERIALISATION_ONLY",
            "task": (
                "Extend the proven event-level extraction contract across all 2025 "
                "monthly Ministry issuance orders, preserving event-date aggregation "
                "and document reconciliation before any full reference-mode promotion."
            ),
            "may_estimate_supply_to_yield_effect": False,
            "may_activate_feedback": False,
        },
    }
    Path(args.assessment_out).parent.mkdir(parents=True, exist_ok=True)
    Path(args.assessment_out).write_text(
        json.dumps(assessment, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": assessment["pilot_result"]["status"],
                "events_all_scheduled": len(all_events),
                "events_completed_by_cutoff": assessment["event_level_pilot"][
                    "event_count_completed_by_cutoff"
                ],
                "monthly_values_RON_million": assessment["monthly_pilot"][
                    "values_RON_million"
                ],
                "post_cutoff_forward_event": assessment["event_level_pilot"][
                    "post_cutoff_forward_events"
                ],
                "full_reference_mode_promoted": False,
                "feedback_activation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
