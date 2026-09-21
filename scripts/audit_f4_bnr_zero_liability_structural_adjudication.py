from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT = "model/accounting/f4_bnr_zero_liability_structural_adjudication_2026_09_21.json"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_f4_bnr_zero_liability_structural_adjudication() -> list[str]:
    errors: list[str] = []
    a = load(ASSESSMENT)
    predecessor = load("model/accounting/f4_exact_complement_rank_assessment.json")
    coverage = load("model/accounting/f4_loans_coverage_assessment.json")
    partial = load("model/accounting/f4_partial_materialization_manifest.json")
    reopen = load("model/accounting/reopen_conditions_registry.json")

    if a["decision"] != "PASS_PROMOTE_BNR_F4_STOCK_ZERO_LIABILITY_PARTITION_TO_EXACT_STRUCTURAL_CONSTRAINT":
        errors.append("F4 structural-zero decision changed")
    if a.get("source_coverage_assessment") != "model/accounting/f4_loans_coverage_assessment.json":
        errors.append("F4 structural-zero source coverage authority changed")

    evidence = coverage["bnr_boundary_evidence"]
    expected = {"2025-Q1": 0, "2025-Q2": 0, "2025-Q3": 0, "2025-Q4": 0}
    if evidence["stock_F4_liabilities_W0_million_RON"] != expected:
        errors.append("retained BNR F4 liability stock is no longer zero across 2025")
    if any(v != 0 for v in evidence["quarterly_F4_liability_transactions_million_RON"].values()):
        errors.append("retained BNR transaction diagnostic changed")

    s = a["structural_argument"]
    if s["stock_only"] is not True or s["flow_extension_authorized"] is not False:
        errors.append("F4 structural-zero adjudication must remain stock-only")
    if s["no_consolidation_netting"] is not True:
        errors.append("F4 structural-zero argument requires non-consolidated stock semantics")
    if s["no_missing_to_zero"] is not True or s["no_residual_allocation"] is not True:
        errors.append("F4 structural-zero argument may not use missing-to-zero or residual allocation")

    cond = predecessor["stock_conditional_BNR_zero_liability_scenario"]
    adj = a["adjudication"]
    if cond["source_condition_pass"] is not True:
        errors.append("historical F4 source condition no longer passes")
    if (cond["rank"], cond["nullity"], cond["unique_cell_count"]) != (
        adj["successor_current_stock_rank"],
        adj["successor_current_stock_nullity"],
        adj["successor_current_stock_unique_cell_count"],
    ):
        errors.append("successor stock rank does not preserve exact predecessor conditional algebra")
    if set(cond["newly_unique_cells_beyond_unconditional"]) != set(adj["newly_current_stock_unique_cells_beyond_predecessor_unconditional"]):
        errors.append("successor stock unique-cell expansion differs from predecessor exact algebra")
    if set(cond["nonunique_cells"]) != set(adj["remaining_stock_nonunique_cells"]):
        errors.append("successor remaining stock topology differs from predecessor exact algebra")

    flow = predecessor["unconditional_identification"]["flow"]
    if (flow["rank"], flow["nullity"], flow["unique_cell_count"]) != (
        adj["successor_current_flow_rank"],
        adj["successor_current_flow_nullity"],
        adj["successor_current_flow_unique_cell_count"],
    ):
        errors.append("F4 flow state changed during stock-only adjudication")

    if partial["conditional_stock_cells_promoted"] is not False:
        errors.append("historical F4 partial artifact was rewritten before successor materialization")
    if a["materialization_effect"]["materialization_authorized_by_this_assessment"] is not False:
        errors.append("structural adjudication may not itself materialize cells")
    if a["materialization_effect"]["existing_f4_partial_2025_must_remain_historical"] is not True:
        errors.append("historical F4 partial artifact must remain immutable")

    f4 = reopen["instruments"]["F4"]
    if f4.get("structural_zero_adjudication") != ASSESSMENT:
        errors.append("F4 reopen registry does not register structural-zero adjudication")
    if f4.get("current_stock_rank") != 31 or f4.get("current_stock_nullity") != 4:
        errors.append("F4 registry current stock rank is stale")
    if f4.get("current_stock_unique_cell_count") != 25:
        errors.append("F4 registry current stock unique-cell count is stale")
    if f4.get("current_flow_rank") != 26 or f4.get("current_flow_nullity") != 9:
        errors.append("F4 registry flow rank changed")

    for key, value in a["system_effect"].items():
        if value is not False:
            errors.append(f"F4 structural adjudication may not authorize {key}")

    return errors


def main() -> None:
    errors = audit_f4_bnr_zero_liability_structural_adjudication()
    if errors:
        raise RuntimeError("F4 BNR structural-zero adjudication audit failed:\n- " + "\n- ".join(errors))
    print(json.dumps({
        "status": "PASS",
        "stock_rank": 31,
        "stock_nullity": 4,
        "stock_unique_cells": 25,
        "flow_rank": 26,
        "flow_nullity": 9,
        "flow_unique_cells": 15,
        "materialization_authorized": False,
        "full_F4_complete": False,
    }, indent=2))


if __name__ == "__main__":
    main()
