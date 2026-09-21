from __future__ import annotations

import argparse
import copy
import json
from collections import Counter
from pathlib import Path

try:
    from scripts.generate_f4_partial_from_snapshot import DEFAULT_VINTAGE, load_vintage
except ModuleNotFoundError:
    from generate_f4_partial_from_snapshot import DEFAULT_VINTAGE, load_vintage

ROOT = Path(__file__).resolve().parents[1]
SECTORS = ("H", "C", "F", "G", "X", "BNR")
HISTORICAL = ROOT / "model" / "accounting" / "f4_partial_2025.json"
ADJUDICATION = ROOT / "model" / "accounting" / "f4_bnr_zero_liability_structural_adjudication_2026_09_21.json"
CONTRACT = ROOT / "model" / "accounting" / "f4_structural_zero_successor_materialization_contract_2026_09_21.json"


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def build(vintage: Path) -> tuple[dict, dict]:
    source, zf, _phase_a, phase_b, provenance = load_vintage(vintage)
    try:
        historical = load_json(HISTORICAL)
        adjudication = load_json(ADJUDICATION)
        contract = load_json(CONTRACT)

        before = phase_b["analyses"]["stock"]["identification_before_structural_zero"]
        after = phase_b["analyses"]["stock"]["identification_with_stock_BNR_zero"]
        flow_rank = phase_b["analyses"]["flow"]["identification_before_structural_zero"]

        if (after["rank"], after["nullity"], after["unique_cell_count"]) != (31, 4, 25):
            raise RuntimeError("Retained Phase B structural-zero stock topology changed")
        if (flow_rank["rank"], flow_rank["nullity"], flow_rank["unique_cell_count"]) != (26, 9, 15):
            raise RuntimeError("Retained Phase B flow topology changed")

        old_unique = set(before["unique_cells"])
        new_unique = set(after["unique_cells"])
        newly_exact = new_unique - old_unique
        expected_new = set(contract["frozen_topology"]["newly_exact_stock_cells"])
        if newly_exact != expected_new:
            raise RuntimeError(f"Unexpected newly exact F4 stock topology: {sorted(newly_exact)}")

        candidates = {
            item["cell"]: item
            for item in phase_b["explicit_derivation_candidates"]["stock"]
            if item.get("rank_uniqueness_confirmed")
        }
        if not expected_new <= set(candidates):
            raise RuntimeError("A newly exact stock cell lacks retained Phase B derivation")

        successor = copy.deepcopy(historical)
        successor["artifact_version"] = "0.2"
        successor["scope"] = "partial_structural_zero_rank_unique_core"
        successor["predecessor_artifact"] = "model/accounting/f4_partial_2025.json"
        successor["structural_adjudication"] = "model/accounting/f4_bnr_zero_liability_structural_adjudication_2026_09_21.json"
        successor["materialization_contract"] = "model/accounting/f4_structural_zero_successor_materialization_contract_2026_09_21.json"

        stock_by_label = {
            f'{cell["holder"]}→{cell["issuer"]}': cell
            for cell in successor["matrices"]["stock"]
        }
        zero_cells = set(adjudication["adjudication"]["exact_zero_cells"])

        for label in sorted(expected_new):
            item = candidates[label]
            cell = stock_by_label[label]
            cell.clear()
            holder, issuer = label.split("→")
            method = item["method"]
            if label in zero_cells:
                method = "ESA2010_structural_zero_from_zero_nonconsolidated_BNR_F4_liability_stock"
            cell.update({
                "holder": holder,
                "issuer": issuer,
                "status": "DERIVED",
                "value": round(float(item["value_million_RON"]), 2),
                "unit": "million_RON",
                "derivation": method,
                "phase_B_rank_uniqueness_confirmed": True,
                "structural_zero_adjudication_applied": True,
                "retained_phase_B_candidate_status": item["status"],
            })
            if "independent_S12_asset_value_million_RON" in item:
                cell["independent_S12_asset_control_million_RON"] = round(
                    float(item["independent_S12_asset_value_million_RON"]), 2
                )
                cell["independent_control_residual_million_RON"] = float(
                    item["independent_residual_million_RON"]
                )

        successor["structural_zero_stock_cells_promoted"] = sorted(zero_cells)
        successor["newly_exact_stock_cells"] = sorted(expected_new)
        successor["remaining_stock_rank_nonunique_cells"] = after["nonunique_cells"]
        successor["remaining_flow_rank_nonunique_cells"] = flow_rank["nonunique_cells"]
        successor.pop("conditional_stock_cells_not_promoted", None)

        counts: dict[str, dict[str, int]] = {}
        for measure in ("stock", "flow"):
            ctr = Counter(cell["status"] for cell in successor["matrices"][measure])
            counts[measure] = dict(sorted(ctr.items()))

        expected_counts = contract["expected_counts"]
        if counts != {
            "stock": dict(sorted(expected_counts["stock"].items())),
            "flow": dict(sorted(expected_counts["flow"].items())),
        }:
            raise RuntimeError(f"Unexpected F4 successor counts: {counts}")

        successor["complete_F4_matrix"] = False
        successor["canonical_benchmark_changed"] = False

        manifest = {
            "materialization_version": "0.2",
            "instrument": "F4",
            "scope": "partial_structural_zero_rank_unique_core",
            "component_path": "model/accounting/f4_partial_structural_2025.json",
            "predecessor_component_path": "model/accounting/f4_partial_2025.json",
            "structural_adjudication": "model/accounting/f4_bnr_zero_liability_structural_adjudication_2026_09_21.json",
            "materialization_contract": "model/accounting/f4_structural_zero_successor_materialization_contract_2026_09_21.json",
            "source_workflow_run_id": source["workflow_run_id"],
            "source_workflow_artifact_id": source["workflow_artifact_id"],
            "source_workflow_artifact_sha256": source["decoded_archive_sha256"],
            "provenance_verification": provenance,
            "counts": counts,
            "rank_boundary": {
                "stock_current": after,
                "flow_current": flow_rank,
            },
            "newly_exact_stock_cells": sorted(expected_new),
            "structural_zero_stock_cells_promoted": sorted(zero_cells),
            "BNR_asset_counterpart_allocation_performed": False,
            "historical_partial_artifact_rewritten": False,
            "canonical_benchmark_2025_changed": False,
            "behavioural_closure_changed": False,
            "status": "PARTIAL_F4_STRUCTURAL_ZERO_CORE_MATERIALIZED_FULL_F4_INCOMPLETE",
        }
        return successor, manifest
    finally:
        zf.close()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--vintage", type=Path, default=DEFAULT_VINTAGE)
    parser.add_argument(
        "--component-output",
        type=Path,
        default=ROOT / "model" / "accounting" / "f4_partial_structural_2025.json",
    )
    parser.add_argument(
        "--manifest-output",
        type=Path,
        default=ROOT / "model" / "accounting" / "f4_structural_zero_materialization_manifest_2026_09_21.json",
    )
    args = parser.parse_args()
    component, manifest = build(args.vintage)
    args.component_output.write_text(
        json.dumps(component, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    args.manifest_output.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    print(json.dumps({
        "counts": manifest["counts"],
        "stock_rank": manifest["rank_boundary"]["stock_current"]["rank"],
        "stock_nullity": manifest["rank_boundary"]["stock_current"]["nullity"],
        "flow_rank": manifest["rank_boundary"]["flow_current"]["rank"],
        "full_F4_complete": False,
    }, indent=2))


if __name__ == "__main__":
    main()
