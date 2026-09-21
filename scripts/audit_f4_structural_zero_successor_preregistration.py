from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT = "model/accounting/f4_bnr_zero_liability_structural_adjudication_2026_09_21.json"
CONTRACT = "model/accounting/f4_structural_zero_successor_materialization_contract_2026_09_21.json"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_f4_structural_zero_successor_preregistration() -> list[str]:
    errors: list[str] = []
    a = load(ASSESSMENT)
    c = load(CONTRACT)
    predecessor = load("model/accounting/f4_exact_complement_rank_assessment.json")
    coverage = load("model/accounting/f4_loans_coverage_assessment.json")
    historical_manifest = load("model/accounting/f4_partial_materialization_manifest.json")

    if a["decision"] != "PASS_PROMOTE_BNR_F4_STOCK_ZERO_LIABILITY_PARTITION_TO_EXACT_STRUCTURAL_CONSTRAINT":
        errors.append("F4 structural adjudication decision changed")
    expected_zero = {"2025-Q1": 0, "2025-Q2": 0, "2025-Q3": 0, "2025-Q4": 0}
    if coverage["bnr_boundary_evidence"]["stock_F4_liabilities_W0_million_RON"] != expected_zero:
        errors.append("retained BNR F4 liability stock is no longer zero across 2025")
    s = a["structural_inference"]
    if not (s["nonnegative_stock_partition_required"] and s["complete_creditor_partition_required"]):
        errors.append("F4 structural inference prerequisites changed")
    if s["stock_only"] is not True or s["flow_extension_authorized"] is not False:
        errors.append("F4 structural adjudication must remain stock-only")

    cond = predecessor["stock_conditional_BNR_zero_liability_scenario"]
    adj = a["adjudication"]
    if (cond["rank"], cond["nullity"], cond["unique_cell_count"]) != (
        adj["successor_current_stock_rank"],
        adj["successor_current_stock_nullity"],
        adj["successor_current_stock_unique_cell_count"],
    ):
        errors.append("adjudicated stock topology differs from retained exact algebra")
    if set(cond["newly_unique_cells_beyond_unconditional"]) != set(
        adj["newly_current_stock_unique_cells_beyond_predecessor_unconditional"]
    ):
        errors.append("adjudicated newly exact stock topology differs from retained algebra")

    if c["adjudication"] != ASSESSMENT:
        errors.append("F4 successor contract is not bound to the adjudication")
    topo = c["frozen_topology"]
    if (topo["expected_stock_rank"], topo["expected_stock_nullity"], topo["expected_stock_unique_cells"]) != (31,4,25):
        errors.append("F4 successor stock topology changed")
    if (topo["expected_flow_rank"], topo["expected_flow_nullity"], topo["expected_flow_unique_cells"]) != (26,9,15):
        errors.append("F4 successor flow topology changed")
    if set(topo["newly_exact_stock_cells"]) != set(adj["newly_current_stock_unique_cells_beyond_predecessor_unconditional"]):
        errors.append("F4 successor contract new-stock topology disagrees with adjudication")

    rules = c["hard_rules"]
    for key in (
        "offline_generation_only",
        "retained_source_digest_must_match",
        "historical_partial_artifact_must_not_be_rewritten",
        "exact_new_stock_topology_must_match_adjudication",
        "no_flow_structural_zero_promotion",
        "no_BNR_asset_counterpart_allocation",
        "no_missing_to_zero",
        "no_synthetic_allocation",
        "canonical_benchmark_2025_must_remain_unchanged",
        "successor_partial_artifact_must_not_be_relabelled_complete_F4",
    ):
        if rules[key] is not True:
            errors.append(f"F4 successor hard rule changed: {key}")
    if rules["behavioural_closure_may_change"] is not False or rules["version_change"] is not False:
        errors.append("F4 successor contract may not change behaviour/version")

    if historical_manifest["conditional_stock_cells_promoted"] is not False:
        errors.append("historical F4 partial manifest was already rewritten")
    if historical_manifest["counts"]["stock"] != {"DERIVED":3,"NOT_APPLICABLE":1,"OBSERVED":12,"UNRESOLVED":20}:
        errors.append("historical F4 stock materialization changed before successor execution")
    return errors


def main() -> None:
    errors = audit_f4_structural_zero_successor_preregistration()
    if errors:
        raise RuntimeError("F4 structural-zero successor preregistration failed:\n- " + "\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "stock_rank":31,
        "stock_unique_cells":25,
        "flow_rank":26,
        "flow_unique_cells":15,
        "materialization":"PREREGISTERED_NOT_EXECUTED",
        "full_F4_complete":False,
    }, indent=2))


if __name__ == "__main__":
    main()
