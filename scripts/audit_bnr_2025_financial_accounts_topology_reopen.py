from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
A = "model/dynamics/bnr_2025_financial_accounts_topology_reopen_assessment_2026_09_21.json"
C = "model/dynamics/bnr_2025_financial_accounts_public_access_recovery_contract.json"
M = "model/registries/reopen_trigger_monitoring_2026_09_21_bnr_financial_accounts_topology.json"
SOURCE_URL = "https://circabc.europa.eu/sd/a/89ddc57a-7e1d-436e-b217-bd266cfb23fd/23%20-%20RO%20-%20CMFB%20FA%20level%203.pdf"
DECISION = "NEW_OFFICIAL_TOPOLOGY_EVIDENCE_CONFIRMED_PUBLIC_ACCESS_RECOVERY_REOPENED_REFERENCE_MODE_UNCHANGED"

def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))

def audit_bnr_2025_financial_accounts_topology_reopen(
    assessment: dict,
    contract: dict,
    monitoring: dict,
    reference_assessment: dict,
    external_screening: dict,
    reference_modes: dict,
    model: dict,
    baseline: dict,
    accounting: dict,
) -> list[str]:
    e: list[str] = []

    if assessment["decision"] != DECISION:
        e.append("topology reopen decision changed")
    if assessment["source"]["url"] != SOURCE_URL:
        e.append("official BNR/CMFB source URL changed")
    if assessment["source"]["institution"] != "National Bank of Romania":
        e.append("source institution changed")
    if assessment["source"]["update_date"] != "2025-09":
        e.append("source update date changed")

    trig = assessment["trigger_evaluation"]
    if trig["changed_official_topology_clue_confirmed"] is not True:
        e.append("changed-topology clue must remain confirmed")
    if trig["new_official_source_confirmed"] is not True:
        e.append("new official source must remain confirmed")
    for key in (
        "exact_public_machine_readable_value_boundary_confirmed",
        "exact_s121_separate_public_counterpart_dimension_confirmed",
        "complete_f2_f8_public_counterpart_value_matrix_confirmed",
        "reference_mode_reopen_authorized",
        "accounting_instrument_reopen_authorized",
    ):
        if trig[key] is not False:
            e.append(f"trigger evaluation may not promote {key}")

    effect = assessment["scientific_effect"]
    if effect["source_discovery_reopened"] is not True:
        e.append("source discovery must be the only reopened scientific path")
    if effect["reference_mode_status_after_review"] != "PARTIAL_SERIES_AVAILABLE":
        e.append("reference mode must remain partial")
    if effect["reference_mode_readiness_count_change"] != 0:
        e.append("reference-mode readiness count may not change")
    for key in (
        "historical_phase_a_d_reinterpreted",
        "accounting_readiness_change",
        "canonical_instrument_completion_change",
        "parameter_estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "version_change_authorized",
    ):
        if effect[key] is not False:
            e.append(f"assessment may not promote {key}")

    state = contract["current_state"]
    if state["execution_authorized"] is not True:
        e.append("one frozen source-topology pass must remain executable")
    if state["execution_completed"] is not True:
        e.append("public-access recovery must be terminal after exact row-gate execution")
    if state["topology_pass"] is not True:
        e.append("public topology gate must remain passed after retained OECD topology review")
    if state["aggregate_reference_mode_gate_pass"] is not False:
        e.append("aggregate exact reference-mode gate must remain failed after exact row coverage FAIL")
    if state["bilateral_accounting_reopen_gate_pass"] is not False:
        e.append("non-counterpart topology path must not reopen bilateral accounting")
    if state.get("terminal_assessment") != "model/dynamics/sectoral_financial_positions_oecd_exact_row_gate_assessment_2026_09_21.json":
        e.append("terminal exact-row assessment pointer changed")
    if state["reference_mode_promotion_authorized"] is not False:
        e.append("reference mode promotion may not be authorized")
    if state["accounting_reopen_authorized"] is not False:
        e.append("accounting reopen may not be authorized")

    for key, value in contract["hard_rules"].items():
        if value is not True:
            e.append(f"public-access hard rule disabled: {key}")

    frozen = contract["frozen_target"]
    if frozen["frequency"] != "quarterly":
        e.append("frozen target must remain quarterly")
    if frozen["required_common_history_quarters_min"] != 40:
        e.append("frozen minimum history changed")
    if frozen["required_instruments"] != ["F2","F3","F4","F5","F6","F7","F8"]:
        e.append("frozen F2-F8 instrument boundary changed")
    if set(frozen["required_rmd_sectors"]) != {"H","C","F","G","X","BNR"}:
        e.append("frozen RMD sector boundary changed")
    if frozen["required_source_sector_semantics"]["BNR"] != "S121 separately observable":
        e.append("S121 separation requirement changed")
    if frozen["missing_to_zero"] is not False or frozen["synthetic_counterparty_allocation"] is not False:
        e.append("frozen target may not permit missing-to-zero or synthetic allocation")

    if monitoring["status"] != "ONE_DECLARED_REOPEN_TRIGGER_SATISFIED_SOURCE_TOPOLOGY_RECOVERY_ONLY":
        e.append("trigger-monitoring status changed")
    d = monitoring["decision"]
    if d["reference_mode_recovery_source_task_open"] is not True:
        e.append("source-topology task must remain explicitly open")
    for key in (
        "accounting_instrument_reopened",
        "reference_mode_promoted",
        "active_calibration_cycle_open",
        "holdout_or_reserved_response_opening_authorized",
        "estimation_or_refit_authorized",
        "system_dynamics_feedback_activation_authorized",
        "behavioural_closure_activation_authorized",
    ):
        if d[key] is not False:
            e.append(f"monitoring may not authorize {key}")
    if d["readiness_count_change"] != 0:
        e.append("monitoring may not change readiness count")

    if reference_assessment["disposition"]["status"] != "PARTIAL_SERIES_AVAILABLE":
        e.append("reference assessment no longer partial")
    if reference_assessment["disposition"]["readiness_count_change"] != 0:
        e.append("reference assessment readiness changed")
    reopen = reference_assessment.get("bnr_2025_topology_reopen", {})
    if reopen.get("assessment") != A or reopen.get("public_access_recovery_contract") != C:
        e.append("reference assessment lacks topology-reopen authority pointers")
    if reopen.get("accounting_readiness_change") is not False:
        e.append("reference assessment may not change accounting readiness")

    screened = next(
        (x for x in external_screening["screened_sources"]
         if x["id"] == "BNR_CMFB_2025_FINANCIAL_ACCOUNTS_STRUCTURAL_METADATA"),
        None,
    )
    if screened is None:
        e.append("external screening lacks BNR/CMFB topology source")
    elif screened["status"] != "NEW_OFFICIAL_TOPOLOGY_TRIGGER_PASS_PUBLIC_ACCESS_RECOVERY_ONLY_NO_PROMOTION":
        e.append("external screening BNR/CMFB source status changed")
    if external_screening["decision"]["reference_mode_readiness_change"] != 0:
        e.append("external screening may not change reference readiness")
    if external_screening["decision"]["current_reference_mode_status"] != "PARTIAL_SERIES_AVAILABLE":
        e.append("external screening may not promote reference mode")

    mode = next(x for x in reference_modes["modes"] if x["id"] == "sectoral_financial_positions")
    if mode["status"] != "PARTIAL_SERIES_AVAILABLE":
        e.append("reference-mode registry may not promote sectoral financial positions")
    if mode.get("bnr_2025_public_access_recovery_status") != "EXECUTED_TOPOLOGY_PASS_EXACT_ROW_GATE_FAIL_NO_PROMOTION":
        e.append("reference-mode registry recovery status changed")

    dc = model["dynamic_core"]
    if dc["reference_mode_ready_count"] != 9 or dc["reference_mode_required_count"] != 10:
        e.append("global reference-mode readiness must remain 9/10")
    if dc["reference_mode_closure_ready"] is not False:
        e.append("reference-mode closure may not become ready")
    if dc.get("sectoral_financial_positions_reference_mode_promotion_authorized") is not False:
        e.append("model contract may not authorize reference-mode promotion")
    if dc.get("sectoral_financial_positions_accounting_reopen_authorized") is not False:
        e.append("model contract may not authorize accounting reopen")
    if dc["behavioural_closure_active"] is not False:
        e.append("behavioural closure changed")

    stage = model["scientific_stage"]
    if stage.get("latest_reopen_trigger_monitoring") != "model/registries/reopen_trigger_monitoring_2026_09_20_post_fiscal_closure.json":
        e.append("historical baseline monitoring pointer may not be rewritten")
    if stage.get("post_terminal_source_topology_trigger_monitoring") != M:
        e.append("model contract post-terminal source-topology monitoring pointer changed")
    if stage.get("active_noncalibration_source_task") is not None:
        e.append("terminal source-topology path must not remain active")
    if stage.get("active_noncalibration_source_subtask") is not None:
        e.append("terminal exact-source subtask must not remain active")
    if stage.get("next_operational_state") != "EVIDENCE_TRIGGERED_BASELINE_HOLD":
        e.append("terminal source path must return to baseline hold")
    if stage.get("calibration_cycle_open") is not False:
        e.append("source-topology recovery may not open calibration")

    auth = baseline["authority"]
    for path in (A,C,M):
        if path not in auth.values():
            e.append(f"scientific baseline authority missing {path}")

    # Accounting Spine remains unchanged: F3 only is complete.
    complete = accounting["current_expected_state"]["canonical_complete_stock_and_flow_instruments"]
    if complete != ["F3"]:
        e.append(f"accounting complete stock+flow instruments changed: {complete}")
    if accounting["current_expected_state"]["canonical_full_2025_stock_flow_benchmark_ready"] is not False:
        e.append("full 2025 Accounting Spine benchmark may not become ready")

    return e

def main() -> None:
    errors = audit_bnr_2025_financial_accounts_topology_reopen(
        load(A),
        load(C),
        load(M),
        load("model/dynamics/sectoral_financial_positions_reference_assessment.json"),
        load("model/dynamics/sectoral_financial_positions_external_source_screening.json"),
        load("model/dynamics/reference_modes.json"),
        load("model/registries/model_contract.json"),
        load("model/registries/scientific_baseline_manifest.json"),
        load("model/accounting/accounting_readiness_gate.json"),
    )
    if errors:
        raise RuntimeError("BNR 2025 financial-accounts topology reopen audit failed:\n- " + "\n- ".join(errors))
    print(json.dumps({
        "status":"PASS",
        "trigger":"CHANGED_OFFICIAL_TOPOLOGY_SOURCE",
        "authorized_scope":"TOPOLOGY_PASS_EXACT_ROW_GATE_FAIL_PATH_CLOSED",
        "reference_modes_ready":"9/10",
        "sectoral_financial_positions":"PARTIAL_SERIES_AVAILABLE",
        "accounting_complete_stock_and_flow_instruments":["F3"],
        "reference_mode_promotion_authorized":False,
        "accounting_reopen_authorized":False,
        "calibration_open":False,
    }, indent=2))

if __name__ == "__main__":
    main()
