from __future__ import annotations

import argparse
import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
    ROOT
    / "data"
    / "source_vintages"
    / "accounting-f3-2025-vintage-2026-09-18"
)
AUDIT = SOURCE / "qsa_f3_coverage_audit.json"
MANIFEST = SOURCE / "qsa_f3_series_manifest.json"
BENCHMARK = ROOT / "model" / "accounting" / "benchmark_2025.json"
CONTRACT = ROOT / "model" / "dynamics" / "f3_empirical_replay_contract.json"
DEFAULT_OUTPUT = ROOT / "model" / "dynamics" / "f3_empirical_replay_2025.json"

PERIODS = ("2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4")
SECTORS = ("H", "C", "F", "G", "X", "BNR")


def d(value: object) -> Decimal:
    return Decimal(str(value))


def n2(value: Decimal) -> float:
    return float(value.quantize(Decimal("0.01")))


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def series_map(manifest: dict) -> dict[str, dict[str, Decimal]]:
    result: dict[str, dict[str, Decimal]] = {}
    for series in manifest["series"]:
        if series["status"] != "AVAILABLE":
            continue
        result[str(series["key"])] = {
            str(row["period"]): d(row["value_published_precision"])
            for row in series["rows"]
        }
    return result


def canonical_cell_value(
    cell: dict,
    period: str,
    *,
    values: dict[str, dict[str, Decimal]],
) -> float | None:
    if cell["holder"] == "X" and cell["issuer"] == "X":
        return None
    total = Decimal("0")
    for term in cell["canonical_terms"]:
        key = str(term["key"])
        if key not in values or period not in values[key]:
            raise RuntimeError(f"Missing retained source value: {key} {period}")
        total += d(term["coefficient"]) * values[key][period]
    return n2(total)


def benchmark_cells(benchmark: dict, measure: str) -> dict[tuple[str, str], dict]:
    spec = benchmark["matrices"]["F3"][measure]
    default = spec["default"]
    overrides = {
        (str(item["holder"]), str(item["issuer"])): item
        for item in spec["overrides"]
    }
    result: dict[tuple[str, str], dict] = {}
    for holder in SECTORS:
        for issuer in SECTORS:
            item = overrides.get((holder, issuer), {})
            result[(holder, issuer)] = {
                "status": item.get("status", default["status"]),
                "value": item.get("value", default.get("value")),
            }
    return result


def build_artifact(
    audit: dict,
    manifest: dict,
    benchmark: dict,
) -> dict:
    values = series_map(manifest)
    cells_by_key = {
        (str(item["measure"]), str(item["holder"]), str(item["issuer"])): item
        for item in audit["cells"]
    }

    required_series = {
        str(term["key"])
        for cell in audit["cells"]
        for term in cell["canonical_terms"]
    }
    missing = sorted(
        key
        for key in required_series
        if key not in values or any(period not in values[key] for period in PERIODS)
    )
    if missing:
        raise RuntimeError(f"Retained F3 quarterly source coverage incomplete: {missing}")

    quarterly: dict[str, list[dict]] = {}
    for period in PERIODS:
        rows: list[dict] = []
        for holder in SECTORS:
            for issuer in SECTORS:
                stock_cell = cells_by_key[("stock", holder, issuer)]
                flow_cell = cells_by_key[("flow", holder, issuer)]
                outside = holder == "X" and issuer == "X"
                rows.append(
                    {
                        "holder": holder,
                        "issuer": issuer,
                        "status": "NOT_APPLICABLE" if outside else "AVAILABLE",
                        "stock_million_RON": canonical_cell_value(
                            stock_cell, period, values=values
                        ),
                        "transaction_million_RON": canonical_cell_value(
                            flow_cell, period, values=values
                        ),
                    }
                )
        quarterly[period] = rows

    transitions: list[dict] = []
    max_identity_residual = Decimal("0")
    for index in range(1, len(PERIODS)):
        period = PERIODS[index]
        opening_period = PERIODS[index - 1]
        cells: list[dict] = []
        for current, opening_row in zip(
            quarterly[period], quarterly[opening_period], strict=True
        ):
            if current["status"] == "NOT_APPLICABLE":
                cells.append(
                    {
                        "holder": current["holder"],
                        "issuer": current["issuer"],
                        "status": "NOT_APPLICABLE",
                        "opening_stock_million_RON": None,
                        "transaction_million_RON": None,
                        "combined_nontransaction_change_million_RON": None,
                        "closing_stock_million_RON": None,
                        "replay_closing_stock_million_RON": None,
                        "identity_residual_million_RON": None,
                    }
                )
                continue

            opening = d(opening_row["stock_million_RON"])
            transaction = d(current["transaction_million_RON"])
            closing = d(current["stock_million_RON"])
            other = (closing - opening - transaction).quantize(Decimal("0.01"))
            replay = (opening + transaction + other).quantize(Decimal("0.01"))
            residual = (closing - replay).quantize(Decimal("0.01"))
            max_identity_residual = max(max_identity_residual, abs(residual))
            cells.append(
                {
                    "holder": current["holder"],
                    "issuer": current["issuer"],
                    "status": "REPLAYED",
                    "opening_stock_million_RON": n2(opening),
                    "transaction_million_RON": n2(transaction),
                    "combined_nontransaction_change_million_RON": n2(other),
                    "closing_stock_million_RON": n2(closing),
                    "replay_closing_stock_million_RON": n2(replay),
                    "identity_residual_million_RON": n2(residual),
                }
            )
        transitions.append(
            {
                "period": period,
                "opening_period": opening_period,
                "cells": cells,
            }
        )

    stock_benchmark = benchmark_cells(benchmark, "stock")
    flow_benchmark = benchmark_cells(benchmark, "flow")
    max_q4_stock_residual = Decimal("0")
    max_annual_flow_residual = Decimal("0")
    for holder in SECTORS:
        for issuer in SECTORS:
            if holder == "X" and issuer == "X":
                continue
            q4_row = next(
                row
                for row in quarterly["2025-Q4"]
                if row["holder"] == holder and row["issuer"] == issuer
            )
            q4_residual = d(q4_row["stock_million_RON"]) - d(
                stock_benchmark[(holder, issuer)]["value"]
            )
            max_q4_stock_residual = max(max_q4_stock_residual, abs(q4_residual))

            annual_transaction = sum(
                (
                    d(
                        next(
                            row
                            for row in quarterly[period]
                            if row["holder"] == holder and row["issuer"] == issuer
                        )["transaction_million_RON"]
                    )
                    for period in PERIODS
                ),
                Decimal("0"),
            )
            flow_residual = annual_transaction - d(
                flow_benchmark[(holder, issuer)]["value"]
            )
            max_annual_flow_residual = max(
                max_annual_flow_residual, abs(flow_residual)
            )

    net_financial_worth_residual = {}
    for period in PERIODS:
        assets = sum(
            (
                d(row["stock_million_RON"])
                for row in quarterly[period]
                if row["status"] != "NOT_APPLICABLE"
            ),
            Decimal("0"),
        )
        liabilities = sum(
            (
                d(row["stock_million_RON"])
                for row in quarterly[period]
                if row["status"] != "NOT_APPLICABLE"
            ),
            Decimal("0"),
        )
        net_financial_worth_residual[period] = n2(assets - liabilities)

    return {
        "replay_version": "0.1",
        "instrument": "F3",
        "contract": "model/dynamics/f3_empirical_replay_contract.json",
        "source_vintage": (
            "data/source_vintages/accounting-f3-2025-vintage-2026-09-18"
        ),
        "value_precision_decimals": 2,
        "quarterly_values": quarterly,
        "transitions": transitions,
        "summary": {
            "retained_quarters": 4,
            "replayed_transitions": 3,
            "in_boundary_cells_per_transition": 35,
            "numeric_replayed_cell_transitions": 105,
            "max_abs_identity_residual_million_RON": n2(max_identity_residual),
            "max_abs_q4_stock_vs_canonical_benchmark_residual_million_RON": n2(
                max_q4_stock_residual
            ),
            "max_abs_annual_transaction_sum_vs_canonical_benchmark_residual_million_RON": n2(
                max_annual_flow_residual
            ),
            "system_net_financial_worth_residual_million_RON_by_quarter": (
                net_financial_worth_residual
            ),
            "q1_transition_replayed": False,
            "q1_nonreplay_reason": (
                "2024-Q4 opening stock is not in the retained F3 source vintage."
            ),
            "full_RMD_empirical_state_claim_allowed": False,
            "behavioural_closure_active": False,
            "feedback_activation_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    artifact = build_artifact(load(AUDIT), load(MANIFEST), load(BENCHMARK))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifact["summary"], indent=2))


if __name__ == "__main__":
    main()
