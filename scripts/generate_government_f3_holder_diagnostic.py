from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "model" / "dynamics" / "f3_empirical_replay_2025.json"
DEFAULT_OUTPUT = ROOT / "model" / "dynamics" / "government_f3_holder_diagnostic_2025.json"
HOLDERS = ("H", "C", "F", "G", "X", "BNR")


def r2(value: float) -> float:
    return round(float(value) + 1e-12, 2)


def r6(value: float) -> float:
    return round(float(value) + 1e-12, 6)


def build(replay: dict) -> dict:
    quarters = {}
    for period, rows in replay["quarterly_values"].items():
        gov_rows = [
            row for row in rows
            if row["issuer"] == "G" and row["status"] != "NOT_APPLICABLE"
        ]
        total = r2(sum(float(row["stock_million_RON"]) for row in gov_rows))
        holders = {}
        for holder in HOLDERS:
            row = next(item for item in gov_rows if item["holder"] == holder)
            stock = float(row["stock_million_RON"])
            holders[holder] = {
                "stock_million_RON": stock,
                "share": None if total == 0.0 else r6(stock / total),
            }
        domestic = r2(
            sum(
                float(row["stock_million_RON"])
                for row in gov_rows
                if row["holder"] != "X"
            )
        )
        shares = [float(holders[h]["share"] or 0.0) for h in HOLDERS]
        hhi = r6(sum(share * share for share in shares))
        quarters[period] = {
            "total_government_F3_liabilities_million_RON": total,
            "domestic_holder_stock_million_RON": domestic,
            "nonresident_holder_stock_million_RON": holders["X"]["stock_million_RON"],
            "domestic_holder_share": None if total == 0.0 else r6(domestic / total),
            "nonresident_holder_share": holders["X"]["share"],
            "holder_concentration_hhi": hhi,
            "effective_holder_count": None if hhi == 0.0 else r6(1.0 / hhi),
            "holders": holders,
        }

    transitions = {}
    for transition in replay["transitions"]:
        rows = [
            row for row in transition["cells"]
            if row["issuer"] == "G" and row["status"] == "REPLAYED"
        ]
        holders = {}
        transaction = other = stock_change = 0.0
        for holder in HOLDERS:
            row = next(item for item in rows if item["holder"] == holder)
            change = r2(
                float(row["closing_stock_million_RON"])
                - float(row["opening_stock_million_RON"])
            )
            holders[holder] = {
                "net_incurrence_million_RON": row["transaction_million_RON"],
                "combined_nontransaction_change_million_RON": row[
                    "combined_nontransaction_change_million_RON"
                ],
                "stock_change_million_RON": change,
            }
            transaction += float(row["transaction_million_RON"])
            other += float(row["combined_nontransaction_change_million_RON"])
            stock_change += change
        transitions[str(transition["period"])] = {
            "total_government_F3_net_incurrence_million_RON": r2(transaction),
            "total_combined_nontransaction_change_million_RON": r2(other),
            "total_stock_change_million_RON": r2(stock_change),
            "decomposition_residual_million_RON": r2(
                stock_change - transaction - other
            ),
            "holders": holders,
        }

    q1 = quarters["2025-Q1"]
    q4 = quarters["2025-Q4"]
    holder_summary = {}
    for holder in HOLDERS:
        q1_stock = float(q1["holders"][holder]["stock_million_RON"])
        q4_stock = float(q4["holders"][holder]["stock_million_RON"])
        q1_share = float(q1["holders"][holder]["share"])
        q4_share = float(q4["holders"][holder]["share"])
        holder_summary[holder] = {
            "q1_stock_million_RON": q1_stock,
            "q4_stock_million_RON": q4_stock,
            "stock_change_million_RON": r2(q4_stock - q1_stock),
            "q1_share": q1_share,
            "q4_share": q4_share,
            "share_change_percentage_points": r6((q4_share - q1_share) * 100.0),
        }

    return {
        "diagnostic_version": "0.1",
        "assessed_on": "2026-09-20",
        "contract": "model/dynamics/government_f3_holder_diagnostic_contract.json",
        "source_replay": "model/dynamics/f3_empirical_replay_2025.json",
        "issuer": "G",
        "instrument": "F3",
        "quarterly_holder_composition": quarters,
        "transition_net_incurrence_and_other_flows": transitions,
        "q1_to_q4_holder_summary": holder_summary,
        "current_summary": {
            "total_government_F3_liability_change_q1_to_q4_million_RON": r2(
                float(q4["total_government_F3_liabilities_million_RON"])
                - float(q1["total_government_F3_liabilities_million_RON"])
            ),
            "nonresident_holder_share_q1": q1["nonresident_holder_share"],
            "nonresident_holder_share_q4": q4["nonresident_holder_share"],
            "nonresident_holder_share_change_percentage_points": r6(
                (
                    float(q4["nonresident_holder_share"])
                    - float(q1["nonresident_holder_share"])
                )
                * 100.0
            ),
            "all_transition_decomposition_residuals_zero": all(
                item["decomposition_residual_million_RON"] == 0.0
                for item in transitions.values()
            ),
            "net_incurrence_is_gross_issuance": False,
            "net_incurrence_is_refinancing_need": False,
            "holder_composition_is_supply_pressure": False,
            "feedback_activation_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    artifact = build(replay)
    args.output.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifact["current_summary"], indent=2))


if __name__ == "__main__":
    main()
