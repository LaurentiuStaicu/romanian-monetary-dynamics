from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REPLAY_PATH = ROOT / "model" / "dynamics" / "f3_empirical_replay_2025.json"
DEFAULT_OUTPUT = (
    ROOT / "model" / "dynamics" / "f3_behavior_over_time_diagnostics_2025.json"
)

SECTORS = ("H", "C", "F", "G", "X", "BNR")


def r2(value: float) -> float:
    return round(float(value) + 1e-12, 2)


def pattern(values: list[float]) -> str:
    diffs = [r2(values[index] - values[index - 1]) for index in range(1, len(values))]
    if all(value == 0.0 for value in diffs):
        return "FLAT"
    if all(value > 0.0 for value in diffs):
        return "MONOTONIC_INCREASE"
    if all(value < 0.0 for value in diffs):
        return "MONOTONIC_DECREASE"
    return "MIXED"


def build_diagnostics(replay: dict[str, object]) -> dict[str, object]:
    periods = list(replay["quarterly_values"])
    if periods != ["2025-Q1", "2025-Q2", "2025-Q3", "2025-Q4"]:
        raise RuntimeError(f"Unexpected F3 replay periods: {periods}")

    quarterly_sector_positions: dict[str, dict[str, dict[str, float]]] = {}
    for period in periods:
        rows = replay["quarterly_values"][period]
        quarterly_sector_positions[period] = {}
        for sector in SECTORS:
            assets = r2(
                sum(
                    float(row["stock_million_RON"])
                    for row in rows
                    if row["status"] != "NOT_APPLICABLE"
                    and row["holder"] == sector
                )
            )
            liabilities = r2(
                sum(
                    float(row["stock_million_RON"])
                    for row in rows
                    if row["status"] != "NOT_APPLICABLE"
                    and row["issuer"] == sector
                )
            )
            quarterly_sector_positions[period][sector] = {
                "assets_million_RON": assets,
                "liabilities_million_RON": liabilities,
                "net_f3_position_million_RON": r2(assets - liabilities),
            }

    transition_sector_decomposition: dict[str, dict[str, dict[str, float]]] = {}
    for transition in replay["transitions"]:
        period = str(transition["period"])
        rows = [
            row for row in transition["cells"] if row["status"] == "REPLAYED"
        ]
        transition_sector_decomposition[period] = {}
        for sector in SECTORS:
            asset_transaction = r2(
                sum(
                    float(row["transaction_million_RON"])
                    for row in rows
                    if row["holder"] == sector
                )
            )
            liability_transaction = r2(
                sum(
                    float(row["transaction_million_RON"])
                    for row in rows
                    if row["issuer"] == sector
                )
            )
            asset_other = r2(
                sum(
                    float(row["combined_nontransaction_change_million_RON"])
                    for row in rows
                    if row["holder"] == sector
                )
            )
            liability_other = r2(
                sum(
                    float(row["combined_nontransaction_change_million_RON"])
                    for row in rows
                    if row["issuer"] == sector
                )
            )
            transition_sector_decomposition[period][sector] = {
                "asset_transaction_million_RON": asset_transaction,
                "liability_transaction_million_RON": liability_transaction,
                "net_transaction_million_RON": r2(
                    asset_transaction - liability_transaction
                ),
                "asset_combined_nontransaction_change_million_RON": asset_other,
                "liability_combined_nontransaction_change_million_RON": (
                    liability_other
                ),
                "net_combined_nontransaction_change_million_RON": r2(
                    asset_other - liability_other
                ),
                "net_position_change_million_RON": r2(
                    (asset_transaction - liability_transaction)
                    + (asset_other - liability_other)
                ),
            }

    sector_summary: dict[str, dict[str, object]] = {}
    for sector in SECTORS:
        assets = [
            quarterly_sector_positions[period][sector]["assets_million_RON"]
            for period in periods
        ]
        liabilities = [
            quarterly_sector_positions[period][sector]["liabilities_million_RON"]
            for period in periods
        ]
        net = [
            quarterly_sector_positions[period][sector][
                "net_f3_position_million_RON"
            ]
            for period in periods
        ]
        cumulative_net_transaction = r2(
            sum(
                transition_sector_decomposition[str(transition["period"])][sector][
                    "net_transaction_million_RON"
                ]
                for transition in replay["transitions"]
            )
        )
        cumulative_net_other = r2(
            sum(
                transition_sector_decomposition[str(transition["period"])][sector][
                    "net_combined_nontransaction_change_million_RON"
                ]
                for transition in replay["transitions"]
            )
        )
        net_change = r2(net[-1] - net[0])
        sector_summary[sector] = {
            "q1_to_q4_asset_change_million_RON": r2(assets[-1] - assets[0]),
            "q1_to_q4_liability_change_million_RON": r2(
                liabilities[-1] - liabilities[0]
            ),
            "q1_to_q4_net_position_change_million_RON": net_change,
            "cumulative_q2_q4_net_transaction_million_RON": (
                cumulative_net_transaction
            ),
            "cumulative_q2_q4_net_combined_nontransaction_change_million_RON": (
                cumulative_net_other
            ),
            "decomposition_residual_million_RON": r2(
                net_change - cumulative_net_transaction - cumulative_net_other
            ),
            "observed_asset_pattern": pattern(assets),
            "observed_liability_pattern": pattern(liabilities),
            "observed_net_position_pattern": pattern(net),
        }

    external_boundary_quarterly: dict[str, dict[str, float]] = {}
    for period in periods:
        rows = replay["quarterly_values"][period]
        resident_holdings_of_nonresident = r2(
            sum(
                float(row["stock_million_RON"])
                for row in rows
                if row["status"] != "NOT_APPLICABLE"
                and row["issuer"] == "X"
                and row["holder"] != "X"
            )
        )
        nonresident_holdings_of_resident = r2(
            sum(
                float(row["stock_million_RON"])
                for row in rows
                if row["status"] != "NOT_APPLICABLE"
                and row["holder"] == "X"
                and row["issuer"] != "X"
            )
        )
        external_boundary_quarterly[period] = {
            "resident_holdings_of_nonresident_F3_million_RON": (
                resident_holdings_of_nonresident
            ),
            "nonresident_holdings_of_resident_F3_million_RON": (
                nonresident_holdings_of_resident
            ),
            "net_resident_external_F3_position_million_RON": r2(
                resident_holdings_of_nonresident
                - nonresident_holdings_of_resident
            ),
        }

    external_values = [
        external_boundary_quarterly[period][
            "net_resident_external_F3_position_million_RON"
        ]
        for period in periods
    ]
    external_boundary_summary = {
        "observed_net_external_pattern": pattern(external_values),
        "q1_to_q4_net_external_change_million_RON": r2(
            external_values[-1] - external_values[0]
        ),
    }

    bilateral_q1_to_q4_summary: list[dict[str, object]] = []
    q1_rows = replay["quarterly_values"][periods[0]]
    q4_rows = replay["quarterly_values"][periods[-1]]
    for q1 in q1_rows:
        if q1["status"] == "NOT_APPLICABLE":
            continue
        q4 = next(
            row
            for row in q4_rows
            if row["holder"] == q1["holder"] and row["issuer"] == q1["issuer"]
        )
        transition_cells = [
            next(
                cell
                for cell in transition["cells"]
                if cell["holder"] == q1["holder"]
                and cell["issuer"] == q1["issuer"]
            )
            for transition in replay["transitions"]
        ]
        cumulative_transactions = r2(
            sum(float(cell["transaction_million_RON"]) for cell in transition_cells)
        )
        cumulative_other = r2(
            sum(
                float(cell["combined_nontransaction_change_million_RON"])
                for cell in transition_cells
            )
        )
        stock_change = r2(
            float(q4["stock_million_RON"]) - float(q1["stock_million_RON"])
        )
        absolute_transactions = r2(
            sum(
                abs(float(cell["transaction_million_RON"]))
                for cell in transition_cells
            )
        )
        absolute_other = r2(
            sum(
                abs(float(cell["combined_nontransaction_change_million_RON"]))
                for cell in transition_cells
            )
        )
        total_absolute_activity = absolute_transactions + absolute_other
        bilateral_q1_to_q4_summary.append(
            {
                "cell": f"{q1['holder']}->{q1['issuer']}",
                "holder": q1["holder"],
                "issuer": q1["issuer"],
                "q1_stock_million_RON": q1["stock_million_RON"],
                "q4_stock_million_RON": q4["stock_million_RON"],
                "q1_to_q4_stock_change_million_RON": stock_change,
                "cumulative_q2_q4_transactions_million_RON": (
                    cumulative_transactions
                ),
                "cumulative_q2_q4_combined_nontransaction_change_million_RON": (
                    cumulative_other
                ),
                "decomposition_residual_million_RON": r2(
                    stock_change - cumulative_transactions - cumulative_other
                ),
                "absolute_transaction_activity_million_RON": (
                    absolute_transactions
                ),
                "absolute_combined_nontransaction_activity_million_RON": (
                    absolute_other
                ),
                "transaction_share_of_absolute_change_activity": (
                    None
                    if total_absolute_activity == 0.0
                    else round(
                        absolute_transactions / total_absolute_activity, 6
                    )
                ),
            }
        )

    return {
        "diagnostic_version": "0.1",
        "assessed_on": "2026-09-20",
        "instrument": "F3",
        "scope": (
            "Observed 2025 quarterly debt-securities behaviour derived only "
            "from the retained F3 empirical replay."
        ),
        "replay_source": "model/dynamics/f3_empirical_replay_2025.json",
        "methodology": {
            "behavior_over_time_role": (
                "Descriptive observed behaviour for one complete canonical "
                "instrument. It may inform later problem articulation and "
                "model testing but does not constitute a causal mechanism or "
                "full sectoral-financial-positions reference mode."
            ),
            "stock_flow_decomposition": (
                "For Q2-Q4, observed stock change is decomposed exactly into "
                "financial transactions plus the combined non-transaction "
                "change retained by the F3 replay."
            ),
            "combined_nontransaction_semantics": (
                "Combined revaluations plus other changes in volume; not "
                "decomposed and not assigned causal meaning."
            ),
            "pattern_labels": {
                "FLAT": (
                    "All three quarter-to-quarter changes are exactly zero "
                    "at retained published precision."
                ),
                "MONOTONIC_INCREASE": (
                    "All three quarter-to-quarter changes are strictly positive."
                ),
                "MONOTONIC_DECREASE": (
                    "All three quarter-to-quarter changes are strictly negative."
                ),
                "MIXED": (
                    "Quarter-to-quarter changes do not satisfy the exact flat "
                    "or monotonic rules."
                ),
            },
            "external_methodology_sources": [
                "https://ec.europa.eu/eurostat/documents/3859598/5925693/KS-02-13-269-EN.PDF",
                "https://www.ecb.europa.eu/stats/pdf/eaa/Handbook_on_quarterly_financial_accounts.pdf",
                "https://ocw.mit.edu/courses/15-988-system-dynamics-self-study-fall-1998-spring-1999/resources/building/",
            ],
        },
        "quarterly_sector_positions": quarterly_sector_positions,
        "transition_sector_decomposition": transition_sector_decomposition,
        "sector_summary": sector_summary,
        "external_boundary_quarterly": external_boundary_quarterly,
        "external_boundary_summary": external_boundary_summary,
        "bilateral_q1_to_q4_summary": bilateral_q1_to_q4_summary,
        "current_summary": {
            "quarters_observed": 4,
            "replayed_transitions_used": 3,
            "sectors": 6,
            "in_boundary_bilateral_cells": 35,
            "all_sector_decomposition_residuals_zero": all(
                item["decomposition_residual_million_RON"] == 0.0
                for item in sector_summary.values()
            ),
            "all_bilateral_decomposition_residuals_zero": all(
                item["decomposition_residual_million_RON"] == 0.0
                for item in bilateral_q1_to_q4_summary
            ),
            "canonical_reference_mode_promoted": False,
            "sectoral_financial_positions_reference_mode_status": (
                "PARTIAL_SERIES_AVAILABLE"
            ),
            "full_RMD_empirical_state_claim_allowed": False,
            "causal_interpretation_authorized": False,
            "behavioural_closure_active": False,
            "feedback_activation_authorized": False,
        },
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    replay = json.loads(REPLAY_PATH.read_text(encoding="utf-8"))
    artifact = build_diagnostics(replay)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(artifact, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(json.dumps(artifact["current_summary"], indent=2))


if __name__ == "__main__":
    main()
