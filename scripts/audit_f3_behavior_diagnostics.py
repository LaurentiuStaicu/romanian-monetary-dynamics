from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.generate_f3_behavior_diagnostics import build_diagnostics
except ModuleNotFoundError:
    from generate_f3_behavior_diagnostics import build_diagnostics

ROOT = Path(__file__).resolve().parents[1]
REPLAY = ROOT / "model" / "dynamics" / "f3_empirical_replay_2025.json"
ARTIFACT = ROOT / "model" / "dynamics" / "f3_behavior_over_time_diagnostics_2025.json"
CONTRACT = (
    ROOT / "model" / "dynamics" / "f3_behavior_over_time_diagnostics_contract.json"
)
REFERENCE_MODES = ROOT / "model" / "dynamics" / "reference_modes.json"
MODEL_CONTRACT = ROOT / "model" / "registries" / "model_contract.json"


def audit_f3_behavior_diagnostics(
    artifact: dict,
    contract: dict,
    regenerated: dict,
    reference_modes: dict,
    model_contract: dict,
) -> list[str]:
    errors: list[str] = []

    if artifact != regenerated:
        errors.append(
            "committed F3 behavior diagnostics differ from deterministic regeneration"
        )

    if artifact.get("instrument") != "F3":
        errors.append("F3 behavior diagnostics changed instrument scope")
    if contract.get("instrument") != "F3":
        errors.append("F3 behavior contract changed instrument scope")
    if contract.get("scientific_status") != (
        "OBSERVED_F3_INSTRUMENT_SPECIFIC_BEHAVIOR_DIAGNOSTIC"
    ):
        errors.append("F3 behavior diagnostic scientific status is stale")

    summary = artifact.get("current_summary", {})
    if summary.get("quarters_observed") != 4:
        errors.append("F3 diagnostics must retain exactly four quarterly states")
    if summary.get("replayed_transitions_used") != 3:
        errors.append("F3 diagnostics must use exactly Q2-Q4 transitions")
    if summary.get("sectors") != 6:
        errors.append("F3 diagnostics sector count is stale")
    if summary.get("in_boundary_bilateral_cells") != 35:
        errors.append("F3 diagnostics bilateral-cell count is stale")
    if summary.get("all_sector_decomposition_residuals_zero") is not True:
        errors.append("sector-level F3 behavior decompositions do not close")
    if summary.get("all_bilateral_decomposition_residuals_zero") is not True:
        errors.append("bilateral F3 behavior decompositions do not close")
    if summary.get("canonical_reference_mode_promoted") is not False:
        errors.append("F3 diagnostics may not promote a canonical reference mode")
    if summary.get("full_RMD_empirical_state_claim_allowed") is not False:
        errors.append("F3 diagnostics may not claim full-RMD empirical readiness")
    if summary.get("causal_interpretation_authorized") is not False:
        errors.append("F3 diagnostics may not authorize causal interpretation")
    if summary.get("behavioural_closure_active") is not False:
        errors.append("F3 diagnostics may not activate behavioural closure")
    if summary.get("feedback_activation_authorized") is not False:
        errors.append("F3 diagnostics may not authorize feedback activation")

    mode = next(
        item
        for item in reference_modes["modes"]
        if item["id"] == "sectoral_financial_positions"
    )
    if mode["status"] != "OBSERVED_SERIES_AVAILABLE":
        errors.append("current successor promotion of sectoral_financial_positions is missing")
    if mode.get("promotion_assessment") != "model/dynamics/reference_mode_recovery_successor_assessment_2026_09_21.json":
        errors.append("current sectoral reference mode lacks successor promotion lineage")
    dynamic = model_contract["dynamic_core"]
    if dynamic["reference_mode_ready_count"] != 10:
        errors.append("current reference-mode ready count must be 10")
    if dynamic["reference_mode_required_count"] != 10:
        errors.append("reference-mode required count must remain 10")
    if dynamic["reference_mode_closure_ready"] is not True:
        errors.append("current reference-target prerequisite must be ready")
    if dynamic["full_RMD_empirical_state_claim_allowed"] is not False:
        errors.append("model contract may not claim full-RMD empirical readiness")

    allowed_patterns = {
        "FLAT",
        "MONOTONIC_INCREASE",
        "MONOTONIC_DECREASE",
        "MIXED",
    }
    for sector, item in artifact.get("sector_summary", {}).items():
        if item["decomposition_residual_million_RON"] != 0.0:
            errors.append(f"{sector}: sector decomposition residual is non-zero")
        for key in (
            "observed_asset_pattern",
            "observed_liability_pattern",
            "observed_net_position_pattern",
        ):
            if item[key] not in allowed_patterns:
                errors.append(f"{sector}:{key}: unsupported pattern label")

    bilateral = artifact.get("bilateral_q1_to_q4_summary", [])
    if len(bilateral) != 35:
        errors.append("F3 diagnostics must contain 35 bilateral summaries")
    if len({item["cell"] for item in bilateral}) != len(bilateral):
        errors.append("F3 diagnostics contain duplicate bilateral cells")
    for item in bilateral:
        if item["decomposition_residual_million_RON"] != 0.0:
            errors.append(f"{item['cell']}: bilateral decomposition residual non-zero")
        share = item["transaction_share_of_absolute_change_activity"]
        if share is not None and not 0.0 <= float(share) <= 1.0:
            errors.append(f"{item['cell']}: transaction activity share outside [0,1]")

    hard_rules = contract.get("hard_rules", {})
    for key in (
        "observed_behavior_only_no_causal_inference",
        "instrument_scope_is_F3_only",
        "no_projection_beyond_2025_Q4",
        "no_interpolation_or_smoothing",
        "no_arbitrary_pattern_thresholds",
        "combined_nontransaction_change_remains_undecomposed",
        "bilateral_and_sector_decompositions_must_close_exactly",
        "sectoral_financial_positions_reference_mode_must_remain_partial",
        "reference_mode_ready_count_must_remain_9_of_10",
        "full_RMD_empirical_state_claim_not_allowed",
        "behavioural_closure_must_remain_inactive",
        "feedback_activation_not_authorized",
    ):
        if hard_rules.get(key) is not True:
            errors.append(f"F3 behavior hard rule {key} must remain true")

    return errors


def main() -> None:
    replay = json.loads(REPLAY.read_text(encoding="utf-8"))
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    reference_modes = json.loads(REFERENCE_MODES.read_text(encoding="utf-8"))
    model_contract = json.loads(MODEL_CONTRACT.read_text(encoding="utf-8"))
    regenerated = build_diagnostics(replay)

    errors = audit_f3_behavior_diagnostics(
        artifact,
        contract,
        regenerated,
        reference_modes,
        model_contract,
    )
    if errors:
        raise RuntimeError(
            "F3 behavior diagnostics audit failed:\n- " + "\n- ".join(errors)
        )
    print(
        json.dumps(
            {
                "status": "PASS",
                "instrument": "F3",
                "quarters_observed": 4,
                "replayed_transitions_used": 3,
                "in_boundary_bilateral_cells": 35,
                "canonical_reference_mode_promoted": False,
                "causal_interpretation_authorized": False,
                "behavioural_closure_active": False,
                "feedback_activation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
