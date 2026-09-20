#!/usr/bin/env python3
"""Materialise the supportable competitive-only 2025 supply candidate.

The full-year candidate is restricted to competitive Treasury-bill and benchmark
reference-auction targets. SSON is never included. Missing raw-source coverage is
retained as unavailable, never zero or inferred.

The current source vintage retains 9/12 required April-December legal source
documents. This script distinguishes:
- exact final months with complete event-level materialisation;
- exact final monthly totals that are directly observed but whose event set is
  incomplete because a required base source is unavailable;
- unavailable final months.

Versioned base/amendment rows remain explicit. Superseded rows are historical
information-time evidence and are never silently double-counted into final
monthly values.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import unicodedata
from collections import defaultdict
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VINTAGE_ROOT = ROOT / (
    "data/source_vintages/"
    "mof-announced-ron-primary-reference-auction-full-2025-vintage-2026-09-20"
)
MANIFEST_PATH = VINTAGE_ROOT / "source_vintage_manifest.json"
Q1_EVENTS_PATH = ROOT / "data/processed/mof_announced_RON_primary_supply_Q1_2025_events.csv"
DEFINITION_REVIEW_PATH = ROOT / (
    "model/dynamics/"
    "mof_announced_RON_primary_supply_full_2025_definition_review_2026_09_20.json"
)

T_BILL_ROW = re.compile(
    r"^\s*(RO[A-Z0-9]{10})\s+"
    r"(\d{1,2}/\d{1,2}/\d{4})\s+"
    r"(\d{1,2}/\d{1,2}/\d{4})\s+"
    r"(\d{1,2}/\d{1,2}/\d{4})\s+"
    r"(\d+)\s+([\d.,]+)\s*$"
)

BOND_ROW = re.compile(
    r"^\s*(RO[A-Z0-9]{10})\s+"
    r"(\d{1,2}/\d{1,2}/\d{4})\s+"
    r"(\d{1,2}/\d{1,2}/\d{4})\s+"
    r"(\d{1,2}/\d{1,2}/\d{4})\s+"
    r"(\d{1,2}/\d{1,2}/\d{4})\s+"
    r"(\d+)\s+([0-9]+(?:[.,][0-9]+)?)\s+"
    r"([0-9]+(?:[.,][0-9]+)?)\s+"
    r"([0-9]+(?:[.,][0-9]+)?)\s+"
    r"([\d.,]+)\s+([\d.,]+)\s*$"
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
        char for char in decomposed if not unicodedata.combining(char)
    )
    return " ".join(without_marks.split()).casefold()


def iso_date(value: str) -> str:
    return datetime.strptime(value, "%d/%m/%Y").date().isoformat()


def parse_romanian_number(value: str) -> float:
    value = value.strip()
    if "," in value and "." in value:
        if value.rfind(",") > value.rfind("."):
            value = value.replace(".", "").replace(",", ".")
        else:
            value = value.replace(",", "")
    elif "," in value:
        parts = value.split(",")
        if len(parts) > 1 and all(part.isdigit() for part in parts):
            if all(len(part) == 3 for part in parts[1:]):
                value = "".join(parts)
            else:
                value = value.replace(",", ".")
        else:
            value = value.replace(",", ".")
    elif "." in value:
        parts = value.split(".")
        if len(parts) > 1 and all(part.isdigit() for part in parts):
            if all(len(part) == 3 for part in parts[1:]):
                value = "".join(parts)
    return float(value)


def parse_ron_integer(value: str) -> int:
    parsed = parse_romanian_number(value)
    if parsed != int(parsed):
        raise RuntimeError(f"expected integer RON amount, observed {value}")
    return int(parsed)


def parse_article_1_base(text: str) -> float:
    n = normalized(text)
    patterns = [
        r"valoare nominala totala de ([0-9.]+) milioane lei, la care se poate adauga suma de",
        r"valoare nominala totala de ([0-9.]+) milioane lei la care se poate adauga suma de",
        r"valoare nominala totala de ([0-9.]+) milioane lei, la care se poate adauga 15%",
        r"valoare nominala totala de ([0-9.]+) milioane lei la care se poate adauga 15%",
    ]
    for pattern in patterns:
        match = re.search(pattern, n)
        if match:
            return float(match.group(1).replace(".", ""))
    raise RuntimeError("could not parse Article 1 competitive base total")


def split_annexes(text: str) -> tuple[str, str]:
    m1 = re.search(r"\bAnexa\s+(?:nr\.\s*)?1\b", text, flags=re.IGNORECASE)
    if not m1:
        raise RuntimeError("Annex 1 marker not found")
    m2 = re.search(
        r"\bAnexa\s+(?:nr\.\s*)?2\b",
        text[m1.end():],
        flags=re.IGNORECASE,
    )
    if not m2:
        raise RuntimeError("Annex 2 marker not found")
    m2_start = m1.end() + m2.start()
    return text[m1.end():m2_start], text[m2_start:]


def extract_native_text(pdf_path: Path, text_path: Path) -> None:
    text_path.parent.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        ["pdftotext", "-layout", str(pdf_path), str(text_path)],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"pdftotext failed for {pdf_path.name}: {result.stderr.strip()}"
        )
    if not text_path.is_file() or text_path.stat().st_size == 0:
        raise RuntimeError(f"pdftotext produced no text for {pdf_path.name}")


def competitive_event(
    retained: dict,
    annex: str,
    row_number: int,
    event_type: str,
    event_date: str,
    instrument_type: str,
    isin: str,
    amount_ron: int,
    issue_date: str,
    maturity_date: str,
    original_maturity: int,
    original_unit: str,
    residual_years: float | None,
    coupon: float | None,
    accrued: float | None,
) -> dict:
    return {
        "source_id": retained["source_id"],
        "source_url": retained.get("official_pdf_url"),
        "source_order_number": retained["order_number"],
        "source_order_issue_date": retained["order_date"],
        "source_publication_date": retained["publication_date"],
        "source_version_role": retained["version_role"],
        "supersedes_order_if_any": retained.get("supersedes"),
        "source_annex": annex,
        "source_row_number": row_number,
        "event_type": event_type,
        "event_date": event_date,
        "instrument_type": instrument_type,
        "instrument_identity": isin,
        "isin": isin,
        "currency": "RON",
        "announced_nominal_RON": amount_ron,
        "announced_nominal_RON_million": amount_ron / 1_000_000,
        "issue_date": issue_date,
        "maturity_date": maturity_date,
        "original_maturity_days_or_years": original_maturity,
        "original_maturity_unit": original_unit,
        "residual_maturity_years": residual_years,
        "coupon_pct": coupon,
        "accrued_interest_RON_per_security": accrued,
    }


def parse_competitive_events(retained: dict, text: str) -> tuple[list[dict], dict]:
    annex1, annex2 = split_annexes(text)
    events: list[dict] = []

    t_rows = []
    for line in annex1.splitlines():
        match = T_BILL_ROW.match(line)
        if match:
            t_rows.append(match.groups())
    for row_number, row in enumerate(t_rows, start=1):
        isin, auction, issue, maturity, days, amount = row
        amount_ron = parse_ron_integer(amount)
        events.append(
            competitive_event(
                retained,
                "Annex 1",
                row_number,
                "T_BILL_COMPETITIVE_REFERENCE_AUCTION",
                iso_date(auction),
                "DISCOUNT_TREASURY_BILL",
                isin,
                amount_ron,
                iso_date(issue),
                iso_date(maturity),
                int(days),
                "days",
                None,
                None,
                None,
            )
        )

    b_rows = []
    for line in annex2.splitlines():
        match = BOND_ROW.match(line)
        if match:
            b_rows.append(match.groups())
    for row_number, row in enumerate(b_rows, start=1):
        (
            isin,
            auction,
            _sson_date,
            issue,
            maturity,
            original_years,
            residual_years,
            coupon,
            accrued,
            ref_amount,
            _sson_amount,
        ) = row
        amount_ron = parse_ron_integer(ref_amount)
        events.append(
            competitive_event(
                retained,
                "Annex 2",
                row_number,
                "BENCHMARK_BOND_COMPETITIVE_REFERENCE_AUCTION",
                iso_date(auction),
                "BENCHMARK_GOVERNMENT_BOND",
                isin,
                amount_ron,
                iso_date(issue),
                iso_date(maturity),
                int(original_years),
                "years",
                parse_romanian_number(residual_years),
                parse_romanian_number(coupon),
                parse_romanian_number(accrued),
            )
        )

    if not t_rows and not b_rows:
        raise RuntimeError(f"{retained['source_id']}: no competitive rows parsed")

    parsed_base = sum(x["announced_nominal_RON_million"] for x in events)
    article_base = parse_article_1_base(text)
    reconciliation = {
        "source_id": retained["source_id"],
        "month": retained["month"],
        "version_role": retained["version_role"],
        "parsed_t_bill_rows": len(t_rows),
        "parsed_bond_rows": len(b_rows),
        "parsed_competitive_event_count": len(events),
        "article_1_competitive_base_RON_million": article_base,
        "parsed_competitive_RON_million": parsed_base,
        "competitive_base_reconciles": parsed_base == article_base,
    }
    return events, reconciliation


def annotate_event_role(events: list[dict], role: str) -> list[dict]:
    for event in events:
        event["materialisation_role"] = role
    return events


def parse_bond_only_partial_events(
    retained: dict,
    text: str,
) -> tuple[list[dict], dict]:
    events: list[dict] = []
    b_rows = []
    for line in text.splitlines():
        match = BOND_ROW.match(line)
        if match:
            b_rows.append(match.groups())

    for row_number, row in enumerate(b_rows, start=1):
        (
            isin,
            auction,
            _sson_date,
            issue,
            maturity,
            original_years,
            residual_years,
            coupon,
            accrued,
            ref_amount,
            _sson_amount,
        ) = row
        events.append(
            competitive_event(
                retained,
                "Annex 2 replacement",
                row_number,
                "BENCHMARK_BOND_COMPETITIVE_REFERENCE_AUCTION",
                iso_date(auction),
                "BENCHMARK_GOVERNMENT_BOND",
                isin,
                parse_ron_integer(ref_amount),
                iso_date(issue),
                iso_date(maturity),
                int(original_years),
                "years",
                parse_romanian_number(residual_years),
                parse_romanian_number(coupon),
                parse_romanian_number(accrued),
            )
        )

    if not b_rows:
        raise RuntimeError(f"{retained['source_id']}: no partial bond rows parsed")

    parsed_partial = sum(
        float(event["announced_nominal_RON_million"]) for event in events
    )
    direct_final_total = parse_article_1_base(text)
    reconciliation = {
        "source_id": retained["source_id"],
        "month": retained["month"],
        "version_role": retained["version_role"],
        "parsed_t_bill_rows": 0,
        "parsed_bond_rows": len(b_rows),
        "parsed_competitive_event_count": len(events),
        "parsed_partial_competitive_RON_million": parsed_partial,
        "direct_final_monthly_total_RON_million": direct_final_total,
        "event_set_complete": False,
        "missing_event_rows_inferred": False,
        "final_monthly_total_directly_observed": True,
    }
    return events, reconciliation


def read_q1_competitive_events() -> list[dict]:
    rows: list[dict] = []
    with Q1_EVENTS_PATH.open(encoding="utf-8", newline="") as handle:
        for row in csv.DictReader(handle):
            if row["event_type"] == "BENCHMARK_BOND_SSON":
                continue
            rows.append(
                {
                    **row,
                    "source_publication_date": "",
                    "source_version_role": "LEGACY_Q1_FROZEN_BASE",
                    "supersedes_order_if_any": "",
                    "materialisation_role": "FINAL_EVENT",
                    "announced_nominal_RON": int(row["announced_nominal_RON"]),
                    "announced_nominal_RON_million": float(
                        row["announced_nominal_RON_million"]
                    ),
                    "source_row_number": int(row["source_row_number"]),
                    "original_maturity_days_or_years": int(
                        row["original_maturity_days_or_years"]
                    ),
                    "residual_maturity_years": (
                        float(row["residual_maturity_years"])
                        if row["residual_maturity_years"]
                        else None
                    ),
                    "coupon_pct": (
                        float(row["coupon_pct"]) if row["coupon_pct"] else None
                    ),
                    "accrued_interest_RON_per_security": (
                        float(row["accrued_interest_RON_per_security"])
                        if row["accrued_interest_RON_per_security"]
                        else None
                    ),
                }
            )
    return rows


def write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key) for key in fieldnames})


def materialise(out_dir: Path) -> dict:
    manifest = load_json(MANIFEST_PATH)
    review = load_json(DEFINITION_REVIEW_PATH)
    docs = {item["source_id"]: item for item in manifest["documents"]}

    if review["full_year_measurement_design"]["canonical_candidate_id"] != (
        "announced_RON_primary_reference_auction_supply_level"
    ):
        raise RuntimeError("full-year candidate definition changed")
    if manifest["canonical_reference_mode_promoted"] is not False:
        raise RuntimeError("source-vintage manifest unexpectedly promotes reference mode")
    if manifest["feedback_activation_authorized"] is not False:
        raise RuntimeError("source-vintage manifest unexpectedly authorizes feedback")

    required_retained = {
        "mof_order_541_april_2025",
        "mof_order_728_may_2025",
        "mof_order_752_may_2025_amendment",
        "mof_order_871_june_2025",
        "mof_order_1088_july_2025",
        "mof_order_1452_september_2025",
        "mof_order_1626_october_2025",
        "mof_order_1831_november_2025_amendment",
        "mof_order_1928_december_2025",
    }
    required_unavailable = {
        "mof_order_1221_august_2025",
        "mof_order_1795_november_2025",
        "mof_order_1998_december_2025_amendment",
    }
    observed_retained = {
        source_id for source_id, item in docs.items() if item["raw_source_retained"]
    }
    observed_unavailable = set(docs) - observed_retained
    if observed_retained != required_retained:
        raise RuntimeError(
            "retained source set changed; 9/12 materialisation contract requires review"
        )
    if observed_unavailable != required_unavailable:
        raise RuntimeError("unavailable source set changed")
    if manifest["raw_sources_retained_count"] != 9:
        raise RuntimeError("source-vintage retained count must be exactly 9")
    if manifest["raw_sources_unavailable_count"] != 3:
        raise RuntimeError("source-vintage unavailable count must be exactly 3")

    q1_events = read_q1_competitive_events()
    all_events = list(q1_events)
    reconciliations: list[dict] = []
    native_text_identities: dict[str, dict] = {}
    texts: dict[str, str] = {}

    native_out = out_dir / "native_text"
    for source_id in sorted(required_retained):
        retained = docs[source_id]
        pdf_path = VINTAGE_ROOT / retained["official_pdf_path"]
        if sha256_file(pdf_path) != retained["official_pdf_sha256"]:
            raise RuntimeError(f"{source_id}: retained PDF hash changed")

        text_path = native_out / f"{source_id}.txt"
        extract_native_text(pdf_path, text_path)
        text = text_path.read_text(encoding="utf-8")
        texts[source_id] = text
        native_text_identities[source_id] = {
            "pdf_sha256": retained["official_pdf_sha256"],
            "native_text_bytes": text_path.stat().st_size,
            "native_text_sha256": sha256_file(text_path),
        }

    final_full_source_roles = {
        "mof_order_541_april_2025": "FINAL_EVENT",
        "mof_order_871_june_2025": "FINAL_EVENT",
        "mof_order_1088_july_2025": "FINAL_EVENT",
        "mof_order_1452_september_2025": "FINAL_EVENT",
        "mof_order_1626_october_2025": "FINAL_EVENT",
    }
    for source_id, role in final_full_source_roles.items():
        events, reconciliation = parse_competitive_events(
            docs[source_id], texts[source_id]
        )
        if not reconciliation["competitive_base_reconciles"]:
            raise RuntimeError(
                f"{source_id}: competitive rows do not reconcile to Article 1 base"
            )
        all_events.extend(annotate_event_role(events, role))
        reconciliations.append(reconciliation)

    # Preserve the original May base order as information-time history only.
    may_base_events, may_base_reconciliation = parse_competitive_events(
        docs["mof_order_728_may_2025"],
        texts["mof_order_728_may_2025"],
    )
    if not may_base_reconciliation["competitive_base_reconciles"]:
        raise RuntimeError("May base order does not reconcile")
    all_events.extend(
        annotate_event_role(
            may_base_events,
            "SUPERSEDED_INFORMATION_TIME_HISTORY",
        )
    )
    reconciliations.append(may_base_reconciliation)

    # OMF 752 replaces Article 1 of both May annexes, so its rows form the
    # complete final May event set.
    may_final_events, may_final_reconciliation = parse_competitive_events(
        docs["mof_order_752_may_2025_amendment"],
        texts["mof_order_752_may_2025_amendment"],
    )
    if not may_final_reconciliation["competitive_base_reconciles"]:
        raise RuntimeError("May amendment rows do not reconcile to final Article 1")
    if may_final_reconciliation["article_1_competitive_base_RON_million"] != 4000.0:
        raise RuntimeError("May final competitive total changed")
    all_events.extend(annotate_event_role(may_final_events, "FINAL_EVENT"))
    reconciliations.append(may_final_reconciliation)

    # OMF 1831 provides the exact final November monthly total and replaces
    # Annex 2, but OMF 1795 (base) is still unavailable. Retain the directly
    # observed Annex-2 rows as a partial final event set; never infer Annex 1.
    november_events, november_reconciliation = parse_bond_only_partial_events(
        docs["mof_order_1831_november_2025_amendment"],
        texts["mof_order_1831_november_2025_amendment"],
    )
    if november_reconciliation["direct_final_monthly_total_RON_million"] != 5800.0:
        raise RuntimeError("November direct final monthly total changed")
    if november_reconciliation["parsed_partial_competitive_RON_million"] != 5300.0:
        raise RuntimeError("November retained Annex-2 total changed")
    all_events.extend(
        annotate_event_role(
            november_events,
            "PARTIAL_FINAL_EVENT_SET_BASE_ANNEX1_UNAVAILABLE",
        )
    )
    reconciliations.append(november_reconciliation)

    # OMF 1928 is a December base-order history point only. OMF 1998 remains
    # unavailable, so the final December monthly value must remain unavailable.
    december_base_total = parse_article_1_base(
        texts["mof_order_1928_december_2025"]
    )
    if december_base_total != 4500.0:
        raise RuntimeError("December base-order total changed")

    all_events.sort(
        key=lambda x: (
            x["event_date"],
            str(x["source_order_number"]),
            x["source_annex"],
            int(x["source_row_number"]),
            x["event_type"],
        )
    )

    coverage = {
        "2025-01": "EXACT_FINAL_EVENT_COMPLETE_FROM_FROZEN_Q1",
        "2025-02": "EXACT_FINAL_EVENT_COMPLETE_FROM_FROZEN_Q1",
        "2025-03": "EXACT_FINAL_EVENT_COMPLETE_FROM_FROZEN_Q1",
        "2025-04": "EXACT_FINAL_EVENT_COMPLETE_RETAINED_BASE_NO_AMENDMENT_IDENTIFIED",
        "2025-05": "EXACT_FINAL_EVENT_COMPLETE_FROM_RETAINED_AMENDMENT_752",
        "2025-06": "EXACT_FINAL_EVENT_COMPLETE_RETAINED_BASE_NO_AMENDMENT_IDENTIFIED",
        "2025-07": "EXACT_FINAL_EVENT_COMPLETE_RETAINED_BASE_NO_AMENDMENT_IDENTIFIED",
        "2025-08": "UNAVAILABLE_BASE_ORDER_1221_RAW_SOURCE_NOT_RETAINED",
        "2025-09": "EXACT_FINAL_EVENT_COMPLETE_RETAINED_BASE_NO_AMENDMENT_IDENTIFIED",
        "2025-10": "EXACT_FINAL_EVENT_COMPLETE_RETAINED_BASE_NO_AMENDMENT_IDENTIFIED",
        "2025-11": "EXACT_FINAL_MONTHLY_TOTAL_FROM_RETAINED_AMENDMENT_1831_EVENT_LEVEL_INCOMPLETE_BASE_1795_UNAVAILABLE",
        "2025-12": "UNAVAILABLE_FINAL_AMENDMENT_1998_RAW_SOURCE_NOT_RETAINED_BASE_1928_RETAINED",
    }
    exact_final_months = {
        month for month, status in coverage.items() if status.startswith("EXACT_FINAL")
    }
    event_complete_months = {
        month for month, status in coverage.items() if "EVENT_COMPLETE" in status
    }

    final_event_sums = defaultdict(float)
    final_event_counts = defaultdict(int)
    for event in all_events:
        if event.get("materialisation_role") != "FINAL_EVENT":
            continue
        month = event["event_date"][:7]
        final_event_sums[month] += float(event["announced_nominal_RON_million"])
        final_event_counts[month] += 1

    expected_event_complete_values = {
        "2025-01": 5200.0,
        "2025-02": 7200.0,
        "2025-03": 7400.0,
        "2025-04": 6900.0,
        "2025-05": 4000.0,
        "2025-06": 5100.0,
        "2025-07": 5800.0,
        "2025-09": 6200.0,
        "2025-10": 7000.0,
    }
    for month, expected in expected_event_complete_values.items():
        observed = final_event_sums[month]
        if observed != expected:
            raise RuntimeError(
                f"{month}: final competitive event sum changed: {observed} != {expected}"
            )

    exact_monthly_values = dict(expected_event_complete_values)
    exact_monthly_values["2025-11"] = 5800.0

    monthly_value_source = {
        "2025-01": "FROZEN_Q1_COMPETITIVE_SUBSET",
        "2025-02": "FROZEN_Q1_COMPETITIVE_SUBSET",
        "2025-03": "FROZEN_Q1_COMPETITIVE_SUBSET",
        "2025-04": "mof_order_541_april_2025",
        "2025-05": "mof_order_752_may_2025_amendment",
        "2025-06": "mof_order_871_june_2025",
        "2025-07": "mof_order_1088_july_2025",
        "2025-09": "mof_order_1452_september_2025",
        "2025-10": "mof_order_1626_october_2025",
        "2025-11": "mof_order_1831_november_2025_amendment",
    }

    monthly_rows = []
    for month in [f"2025-{m:02d}" for m in range(1, 13)]:
        exact = month in exact_final_months
        event_complete = month in event_complete_months
        monthly_rows.append(
            {
                "period": month,
                "announced_RON_primary_reference_auction_supply_million": (
                    exact_monthly_values[month] if exact else None
                ),
                "event_count": (
                    final_event_counts[month] if event_complete else None
                ),
                "event_level_complete": event_complete,
                "monthly_value_source_id": monthly_value_source.get(month),
                "status": coverage[month],
            }
        )

    event_fields = [
        "source_id",
        "source_url",
        "source_order_number",
        "source_order_issue_date",
        "source_publication_date",
        "source_version_role",
        "supersedes_order_if_any",
        "materialisation_role",
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
    ]
    events_path = out_dir / (
        "mof_announced_RON_primary_reference_auction_partial_2025_events.csv"
    )
    monthly_path = out_dir / (
        "mof_announced_RON_primary_reference_auction_partial_2025_monthly.csv"
    )
    write_csv(events_path, all_events, event_fields)
    write_csv(
        monthly_path,
        monthly_rows,
        [
            "period",
            "announced_RON_primary_reference_auction_supply_million",
            "event_count",
            "event_level_complete",
            "monthly_value_source_id",
            "status",
        ],
    )

    may_base_total = sum(
        float(event["announced_nominal_RON_million"])
        for event in may_base_events
    )
    may_final_total = sum(
        float(event["announced_nominal_RON_million"])
        for event in may_final_events
    )

    assessment = {
        "assessment_version": "0.2",
        "assessed_on": "2026-09-20",
        "candidate_id": "announced_RON_primary_reference_auction_supply_level",
        "status": "PARTIAL_EXACT_MONTHLY_10_OF_12_EVENT_COMPLETE_9_OF_12_CANONICAL_PROMOTION_BLOCKED_3_REQUIRED_SOURCES_MISSING",
        "definition_review": str(DEFINITION_REVIEW_PATH.relative_to(ROOT)),
        "source_vintage_manifest": str(MANIFEST_PATH.relative_to(ROOT)),
        "event_level_series": "data/processed/mof_announced_RON_primary_reference_auction_partial_2025_events.csv",
        "monthly_series": "data/processed/mof_announced_RON_primary_reference_auction_partial_2025_monthly.csv",
        "source_coverage": {
            "required_document_count": 12,
            "retained_document_count": 9,
            "missing_document_count": 3,
            "missing_source_ids": sorted(required_unavailable),
        },
        "native_text_identities": native_text_identities,
        "document_reconciliation": reconciliations,
        "coverage_by_month": coverage,
        "exact_final_months": sorted(exact_final_months),
        "event_level_complete_final_months": sorted(event_complete_months),
        "monthly_only_exact_final_months": ["2025-11"],
        "exact_final_monthly_values_RON_million": {
            month: exact_monthly_values[month]
            for month in sorted(exact_final_months)
        },
        "may_version_history": {
            "base_source_id": "mof_order_728_may_2025",
            "base_competitive_event_count": len(may_base_events),
            "base_competitive_RON_million": may_base_total,
            "base_is_final": False,
            "final_amendment_source_id": "mof_order_752_may_2025_amendment",
            "final_competitive_event_count": len(may_final_events),
            "final_competitive_RON_million": may_final_total,
            "final_monthly_value_authorized": True,
            "base_rows_retained_as_information_time_history": True,
        },
        "november_direct_monthly_total": {
            "source_id": "mof_order_1831_november_2025_amendment",
            "final_monthly_total_RON_million": 5800.0,
            "materialised_annex2_event_count": len(november_events),
            "materialised_annex2_competitive_RON_million": (
                november_reconciliation["parsed_partial_competitive_RON_million"]
            ),
            "event_level_complete": False,
            "missing_base_source_id": "mof_order_1795_november_2025",
            "missing_annex1_event_inferred": False,
            "monthly_total_is_direct_source_value_not_event_sum": True,
        },
        "december_base_order_history": {
            "source_id": "mof_order_1928_december_2025",
            "base_competitive_RON_million": december_base_total,
            "final_monthly_value_authorized": False,
            "missing_final_amendment_source_id": "mof_order_1998_december_2025_amendment",
            "reason": "OMF 1998/2025 final amendment raw source is not retained.",
        },
        "scientific_guards": {
            "SSON_included_in_candidate": False,
            "accepted_or_borrowed_amount_included": False,
            "missing_months_treated_as_zero": False,
            "unretained_amendment_inferred": False,
            "missing_event_rows_inferred": False,
            "monthly_total_promoted_to_synthetic_event_rows": False,
            "canonical_reference_mode_promoted": False,
            "government_securities_supply_pressure_node_resolved": False,
            "yield_effect_estimation_authorized": False,
            "feedback_activation_authorized": False,
            "behavioural_closure_authorized": False,
            "public_version_change_authorized": False,
        },
        "next_gate": {
            "id": "mof_announced_RON_primary_reference_auction_full_2025_missing_source_recovery",
            "authorization": "OFFICIAL_SOURCE_RECOVERY_ONLY",
            "required_source_ids": sorted(required_unavailable),
            "event_materialisation_for_missing_sources_authorized": False,
            "canonical_promotion_before_complete_required_source_coverage": False,
        },
    }
    assessment_path = out_dir / (
        "mof_announced_RON_primary_reference_auction_partial_2025_assessment.json"
    )
    assessment_path.write_text(
        json.dumps(assessment, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(
        json.dumps(
            {
                "status": assessment["status"],
                "exact_final_months": assessment["exact_final_months"],
                "event_level_complete_final_months": assessment[
                    "event_level_complete_final_months"
                ],
                "monthly_only_exact_final_months": assessment[
                    "monthly_only_exact_final_months"
                ],
                "exact_final_values_RON_million": assessment[
                    "exact_final_monthly_values_RON_million"
                ],
                "missing_source_ids": assessment["next_gate"]["required_source_ids"],
                "canonical_reference_mode_promoted": False,
                "feedback_activation_authorized": False,
                "next_gate": assessment["next_gate"]["id"],
            },
            indent=2,
        )
    )
    return assessment


def main() -> None:
    out_dir = Path("mof_announced_reference_auction_partial_2025_materialised")
    out_dir.mkdir(parents=True, exist_ok=True)
    materialise(out_dir)


if __name__ == "__main__":
    main()
