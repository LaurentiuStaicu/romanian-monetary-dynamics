from __future__ import annotations

import json
from pathlib import Path

from scripts.generate_f4_structural_zero_successor_from_snapshot import (
    DEFAULT_VINTAGE,
    build,
)

ROOT = Path(__file__).resolve().parents[1]
EXECUTION = "model/accounting/f4_structural_zero_successor_materialization_assessment_2026_09_21.json"
PREREG_SHA = "f8a78e984fed4300460fcaaafe5b2fcdcef41e68"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_f4_structural_zero_successor_execution() -> list[str]:
    errors: list[str] = []
    e = load(EXECUTION)
    contract = load("model/accounting/f4_structural_zero_successor_materialization_contract_2026_09_21.json")
    committed_component = load("model/accounting/f4_partial_structural_2025.json")
    committed_manifest = load("model/accounting/f4_structural_zero_materialization_manifest_2026_09_21.json")
    historical_component = load("model/accounting/f4_partial_2025.json")
    historical_manifest = load("model/accounting/f4_partial_materialization_manifest.json")
    reopen = load("model/accounting/reopen_conditions_registry.json")

    if e["decision"] != "PASS_F4_STRUCTURAL_ZERO_SUCCESSOR_PARTIAL_MATERIALIZATION_RETURN_TO_HOLD":
        errors.append("F4 successor execution decision changed")
    if e["preregistration_head_sha"] != PREREG_SHA:
        errors.append("F4 successor execution lost the frozen preregistration checkpoint")
    if e["retained_source_archive_sha256"] != historical_manifest["source_workflow_artifact_sha256"]:
        errors.append("F4 successor retained source identity changed")

    regenerated_component, regenerated_manifest = build(DEFAULT_VINTAGE)
    if regenerated_component != committed_component:
        errors.append("committed F4 successor component is not reproducible from retained source")
    if regenerated_manifest != committed_manifest:
        errors.append("committed F4 successor manifest is not reproducible from retained source")

    expected_stock = {"OBSERVED": 12, "DERIVED": 13, "UNRESOLVED": 10, "NOT_APPLICABLE": 1}
    expected_flow = {"DERIVED": 15, "UNRESOLVED": 20, "NOT_APPLICABLE": 1}
    if e["result"]["stock_counts"] != expected_stock:
        errors.append("F4 successor stock counts changed")
    if e["result"]["flow_counts"] != expected_flow:
        errors.append("F4 successor flow counts changed")
    if committed_manifest["counts"]["stock"] != expected_stock:
        errors.append("F4 successor manifest stock counts changed")
    if committed_manifest["counts"]["flow"] != expected_flow:
        errors.append("F4 successor manifest flow counts changed")

    stock_rank = committed_manifest["rank_boundary"]["stock_current"]
    flow_rank = committed_manifest["rank_boundary"]["flow_current"]
    if (stock_rank["rank"], stock_rank["nullity"], stock_rank["unique_cell_count"]) != (31, 4, 25):
        errors.append("F4 successor stock rank boundary changed")
    if (flow_rank["rank"], flow_rank["nullity"], flow_rank["unique_cell_count"]) != (26, 9, 15):
        errors.append("F4 successor flow rank boundary changed")

    zero_cells = set(e["result"]["exact_structural_zero_stock_cells"])
    component_stock = {
        f'{c["holder"]}→{c["issuer"]}': c
        for c in committed_component["matrices"]["stock"]
    }
    for label in zero_cells:
        cell = component_stock[label]
        if cell["status"] != "DERIVED" or cell["value"] != 0:
            errors.append(f"structural-zero stock cell is not exact zero: {label}")
        if cell.get("derivation") != "ESA2010_structural_zero_from_zero_nonconsolidated_BNR_F4_liability_stock":
            errors.append(f"structural-zero provenance changed: {label}")

    if committed_manifest["BNR_asset_counterpart_allocation_performed"] is not False:
        errors.append("F4 successor may not allocate BNR asset row")
    if committed_component["complete_F4_matrix"] is not False:
        errors.append("F4 successor may not claim complete F4")
    if committed_component["canonical_benchmark_changed"] is not False:
        errors.append("F4 successor may not change canonical benchmark")

    if historical_manifest["conditional_stock_cells_promoted"] is not False:
        errors.append("historical F4 partial manifest was rewritten")
    if historical_manifest["counts"]["stock"] != {
        "DERIVED": 3, "NOT_APPLICABLE": 1, "OBSERVED": 12, "UNRESOLVED": 20
    }:
        errors.append("historical F4 partial stock counts changed")
    if historical_component.get("scope") != "partial_unconditional_rank_unique_core":
        errors.append("historical F4 partial artifact scope changed")

    f4 = reopen["instruments"]["F4"]
    if f4.get("current_status") != "PARTIAL_STRUCTURAL_ZERO_CORE_MATERIALIZED":
        errors.append("F4 registry current status is stale")
    if f4.get("successor_materialization_assessment") != EXECUTION:
        errors.append("F4 registry lacks successor execution assessment")
    if f4.get("current_reopen_gate_open") is not False:
        errors.append("F4 successor cycle did not return to hold")
    if f4.get("current_stock_unique_cell_count") != 25:
        errors.append("F4 registry stock unique-cell count is stale")
    if f4.get("current_flow_unique_cell_count") != 15:
        errors.append("F4 registry flow unique-cell count is stale")

    for key, value in e["scientific_effect"].items():
        if key == "F4_status":
            continue
        if value is not False:
            errors.append(f"F4 successor execution may not authorize {key}")

    rules = contract["hard_rules"]
    if rules["historical_partial_artifact_must_not_be_rewritten"] is not True:
        errors.append("F4 historical artifact immutability rule changed")
    return errors


def main() -> None:
    errors = audit_f4_structural_zero_successor_execution()
    if errors:
        raise RuntimeError("F4 structural-zero successor execution audit failed:\n- " + "\n- ".join(errors))
    print(json.dumps({
        "status": "PASS",
        "stock_rank": 31,
        "stock_nullity": 4,
        "stock_unique_cells": 25,
        "flow_rank": 26,
        "flow_nullity": 9,
        "flow_unique_cells": 15,
        "full_F4_complete": False,
        "next_state": "EVIDENCE_TRIGGERED_HOLD",
    }, indent=2))


if __name__ == "__main__":
    main()
