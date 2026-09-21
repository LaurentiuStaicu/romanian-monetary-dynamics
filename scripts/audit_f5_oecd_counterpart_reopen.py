from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = "model/accounting/f5_oecd_counterpart_reopen_contract_2026_09_21.json"
ASSESSMENT = "model/accounting/f5_oecd_counterpart_reopen_assessment_2026_09_21.json"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_f5_oecd_counterpart_reopen() -> list[str]:
    errors: list[str] = []
    c = load(CONTRACT)
    a = load(ASSESSMENT)
    source = load("model/dynamics/sectoral_financial_positions_oecd_counterpart_discovery_assessment.json")
    rank = load("model/accounting/f5_component_aware_rank_assessment.json")
    reopen = load("model/accounting/reopen_conditions_registry.json")

    if a["decision"] != "PASS_F5_REOPEN_TRIGGER_OECD_F512_F519_COUNTERPART_STAGE2_PREREGISTERED":
        errors.append("F5 OECD reopen decision changed")
    if a["topology_only_review"] is not True or a["detailed_value_review_performed"] is not False:
        errors.append("reopen assessment must remain topology-only")
    if a["rank_recomputation_performed"] is not False:
        errors.append("rank may not be recomputed in the reopen assessment")

    src = c["source"]
    disc = source["discovery_result"]
    if disc["artifact_id"] != src["retained_workflow_artifact_id"]:
        errors.append("OECD counterpart artifact lineage changed")
    if disc["stocks_raw_sha256"] != src["stocks_raw_sha256"]:
        errors.append("OECD stock raw hash changed")
    if disc["flows_raw_sha256"] != src["flows_raw_sha256"]:
        errors.append("OECD flow raw hash changed")

    inst = source["review_results"]["INSTRUMENT_MAPPING"]
    if inst["status"] != "PASS":
        errors.append("retained OECD instrument mapping no longer passes")
    for component in ("F512", "F519"):
        if component not in c["topology_trigger"]["exact_components_present"]:
            errors.append(f"missing preregistered component {component}")

    if c["topology_trigger"]["central_bank_sector_S121_present"] is not False:
        errors.append("contract may not invent S121 coverage")
    if c["frozen_mapping"]["S12"] != "F + BNR aggregate only":
        errors.append("S12 mapping was relaxed")
    if c["stage2_gate"]["reconciliation"]["tolerance_million_RON"] != "0.1":
        errors.append("Stage 2 tolerance changed after preregistration")
    if c["hard_rules"]["no_BNR_residual_allocation"] is not True:
        errors.append("BNR residual allocation must remain prohibited")
    if c["hard_rules"]["no_post_result_tolerance_change"] is not True:
        errors.append("post-result tolerance change must remain prohibited")

    if rank["exact_rank"]["stock"]["rank"] != 73 or rank["exact_rank"]["flow_2025"]["rank"] != 73:
        errors.append("predecessor F5 base rank changed")
    if rank["exact_rank"]["stock"]["unique_F5_total_cells"] != 0:
        errors.append("predecessor F5 stock state was rewritten")
    if rank["exact_rank"]["flow_2025"]["unique_F5_total_cells"] != 0:
        errors.append("predecessor F5 flow state was rewritten")

    f5 = reopen["instruments"]["F5"]
    if f5.get("selective_reopen_contract") != CONTRACT:
        errors.append("F5 reopen registry does not register Stage 2 contract")
    if f5.get("selective_reopen_assessment") != ASSESSMENT:
        errors.append("F5 reopen registry does not register trigger assessment")
    if f5.get("selective_reopen_state") != "PREREGISTERED_STAGE2_PENDING_EXECUTION":
        errors.append("F5 selective reopen state is stale")
    if f5.get("reopen_trigger_satisfied") is not True:
        errors.append("F5 reopen trigger is not registered as satisfied")

    if a["adjudication"]["accounting_readiness_change"] is not False:
        errors.append("topology reopen may not change accounting readiness")
    if a["adjudication"]["F5_materialization_change"] is not False:
        errors.append("topology reopen may not materialize F5")
    return errors


def main() -> None:
    errors = audit_f5_oecd_counterpart_reopen()
    if errors:
        raise RuntimeError("F5 OECD counterpart reopen audit failed:\n- " + "\n- ".join(errors))
    print(json.dumps({
        "status": "PASS",
        "reopen_trigger": "OECD_F512_F519_COUNTERPART_PUBLICATION",
        "stage2": "PREREGISTERED_PENDING_EXECUTION",
        "base_rank_stock": 73,
        "base_rank_flow": 73,
        "accounting_readiness_changed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
