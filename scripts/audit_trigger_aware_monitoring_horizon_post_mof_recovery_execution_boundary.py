from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HORIZON = (
    "model/registries/"
    "trigger_aware_monitoring_horizon_2026_09_22_post_mof_recovery_execution_boundary.json"
)
PREDECESSOR = (
    "model/registries/"
    "trigger_aware_monitoring_horizon_2026_09_22_post_counterpart_workflow_boundary.json"
)
SUCCESSOR = "model/registries/trigger_aware_monitoring_horizon_2026_09_24_post_ameco_autumn_month_confirmation.json"
LATEST = "model/registries/trigger_aware_monitoring_horizon_2026_09_24_post_qsa_release_context_clarification.json"
RECOVERY = (
    "model/dynamics/"
    "mof_announced_RON_primary_reference_auction_missing_source_recovery_assessment_2026_09_20.json"
)

WORKFLOWS = {
    "full_year_source_vintage": (
        ".github/workflows/"
        "mof-announced-ron-primary-reference-auction-full-2025-source-vintage.yml"
    ),
    "missing_official_pdf_probe": (
        ".github/workflows/"
        "mof-announced-ron-primary-reference-auction-missing-official-pdfs.yml"
    ),
    "recovered_official_pdf_promotion": (
        ".github/workflows/"
        "mof-announced-ron-primary-reference-auction-recovered-official-pdfs.yml"
    ),
    "partial_materialisation": (
        ".github/workflows/"
        "mof-announced-ron-primary-reference-auction-partial-2025-materialise.yml"
    ),
}

TARGET_BRANCHES = {
    "full_year_source_vintage": (
        "source-vintage/"
        "mof-announced-ron-primary-reference-auction-full-2025-2026-09-20"
    ),
    "missing_official_pdf_probe": (
        "recovery/"
        "mof-announced-ron-primary-reference-auction-missing-sources-2026-09-20"
    ),
    "recovered_official_pdf_promotion": (
        "recovery/"
        "mof-announced-ron-primary-reference-auction-missing-sources-2026-09-20"
    ),
    "partial_materialisation": (
        "recovery/"
        "mof-announced-ron-primary-reference-auction-missing-sources-2026-09-20"
    ),
}


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_trigger_aware_monitoring_horizon_post_mof_recovery_execution_boundary() -> list[str]:
    errors: list[str] = []
    h = load(HORIZON)
    p = load(PREDECESSOR)
    recovery = load(RECOVERY)
    model = load("model/registries/model_contract.json")
    baseline = load("model/registries/scientific_baseline_manifest.json")

    if h["registry_version"] != "0.8":
        errors.append("MoF-recovery monitoring horizon version changed")
    if h["supersedes"] != PREDECESSOR:
        errors.append("MoF-recovery predecessor changed")

    if [x["id"] for x in h["horizons"]] != [x["id"] for x in p["horizons"]]:
        errors.append("existing trigger identity/order changed")
    current_by_id = {x["id"]: x for x in h["horizons"]}
    prior_by_id = {x["id"]: x for x in p["horizons"]}
    for trigger_id in current_by_id:
        if current_by_id[trigger_id] != prior_by_id[trigger_id]:
            errors.append(f"existing trigger content changed: {trigger_id}")

    if recovery["path_disposition"]["state"] != "EVIDENCE_TRIGGERED_HOLD":
        errors.append("MoF recovery no longer on evidence-triggered hold")
    if recovery["path_disposition"]["active_polling"] is not False:
        errors.append("MoF recovery assessment unexpectedly enables active polling")
    if recovery["path_disposition"]["remaining_required_source_count"] != 3:
        errors.append("MoF remaining-source count changed")
    if recovery["scientific_effect"]["full_year_source_recovery_complete"] is not False:
        errors.append("MoF full-year recovery unexpectedly complete")
    if recovery["scientific_effect"]["canonical_reference_mode_promoted"] is not False:
        errors.append("MoF full-year canonical reference mode unexpectedly promoted")

    expected_conditions = [
        "stable_official_pdf_or_file_transport",
        "portal_transport_becomes_reproducible",
        "verifiable_official_raw_file_supplied",
    ]
    actual_conditions = [x["id"] for x in recovery["reopen_conditions"]]
    if actual_conditions != expected_conditions:
        errors.append("MoF recovery reopen-condition identities changed")

    expected_unresolved = [
        "mof_order_1221_august_2025",
        "mof_order_1795_november_2025",
        "mof_order_1998_december_2025_amendment",
    ]
    actual_unresolved = [x["source_id"] for x in recovery["missing_sources"]]
    if actual_unresolved != expected_unresolved:
        errors.append("MoF unresolved official-source identities changed")

    rules = h["monitoring_rules"]
    for key in (
        "no_repeated_probe_without_trigger",
        "no_provider_polling_counts_as_scientific_progress",
        "mof_full_2025_recovery_active_polling_disabled",
        "mof_full_2025_recovery_requires_declared_new_evidence_trigger",
        "mof_full_2025_manual_rerun_without_trigger_is_not_scientific_progress",
    ):
        if rules.get(key) is not True:
            errors.append(f"monitoring hard rule disabled: {key}")

    boundary = h.get("mof_full_2025_recovery_execution_boundary", {})
    if boundary.get("governing_assessment") != RECOVERY:
        errors.append("MoF recovery execution-boundary assessment pointer changed")
    if boundary.get("current_role") != "EVIDENCE_TRIGGERED_MANUAL_RECOVERY_ONLY":
        errors.append("MoF recovery execution-boundary role changed")
    if boundary.get("current_execution_authorized") is not False:
        errors.append("MoF recovery execution unexpectedly authorized")
    if boundary.get("active_polling") is not False:
        errors.append("MoF recovery execution boundary enables active polling")
    if boundary.get("remaining_required_source_count") != 3:
        errors.append("MoF execution-boundary remaining-source count changed")
    if boundary.get("unresolved_source_ids") != expected_unresolved:
        errors.append("MoF execution-boundary unresolved sources changed")
    if boundary.get("declared_reopen_conditions") != expected_conditions:
        errors.append("MoF execution-boundary reopen conditions changed")
    if boundary.get("workflows") != WORKFLOWS:
        errors.append("MoF execution-boundary workflow registry changed")
    for key in (
        "manual_rerun_without_trigger_counts_as_scientific_progress",
        "unchanged_provider_response_is_trigger",
        "repeated_same_endpoint_polling_authorized",
        "canonical_reference_mode_promotion_authorized_now",
        "yield_effect_estimation_authorized_now",
        "feedback_activation_authorized_now",
        "behavioural_closure_change_authorized_now",
    ):
        if boundary.get(key) is not False:
            errors.append(f"unsafe MoF recovery execution rule enabled: {key}")

    requirements = boundary.get("manual_dispatch_requirements", {})
    for key in (
        "trigger_condition_required",
        "evidence_reference_required",
        "evidence_verified_confirmation_required",
        "target_branch_must_be_explicit",
    ):
        if requirements.get(key) is not True:
            errors.append(f"MoF manual dispatch requirement disabled: {key}")

    for name, relative in WORKFLOWS.items():
        text = (ROOT / relative).read_text(encoding="utf-8")
        if "workflow_dispatch:" not in text:
            errors.append(f"MoF recovery workflow lost manual dispatch: {name}")
        if "\n  push:" in text:
            errors.append(f"MoF recovery workflow regained automatic push trigger: {name}")
        if "\n  schedule:" in text:
            errors.append(f"MoF recovery workflow gained polling schedule: {name}")
        for token in (
            "EVIDENCE-TRIGGERED MANUAL RECOVERY ONLY",
            "trigger_condition:",
            "evidence_reference:",
            "evidence_verified:",
            "inputs.evidence_verified == true",
            TARGET_BRANCHES[name],
        ):
            if token not in text:
                errors.append(f"MoF recovery workflow lost safeguard {token!r}: {name}")

    probe_text = (ROOT / WORKFLOWS["missing_official_pdf_probe"]).read_text(encoding="utf-8")
    if "contents: read" not in probe_text or "contents: write" in probe_text:
        errors.append("MoF evidence probe is not read-only")
    for name in (
        "full_year_source_vintage",
        "recovered_official_pdf_promotion",
        "partial_materialisation",
    ):
        text = (ROOT / WORKFLOWS[name]).read_text(encoding="utf-8")
        if "contents: write" not in text:
            errors.append(f"authorized retention workflow lost required write scope: {name}")

    d = h["current_disposition"]
    if d.get("mof_full_2025_recovery_execution_authorized_now") is not False:
        errors.append("MoF current recovery execution unexpectedly authorized")
    if d.get("mof_full_2025_recovery_active_polling") is not False:
        errors.append("MoF current recovery active polling unexpectedly enabled")
    if d.get("mof_full_2025_remaining_required_source_count") != 3:
        errors.append("MoF current remaining-source count changed")
    if d.get("mof_full_2025_recovery_trigger_satisfied") is not False:
        errors.append("MoF recovery trigger unexpectedly satisfied")
    for key in (
        "any_monitoring_gate_open_now",
        "active_source_task_open",
        "estimation_or_refit_authorized",
        "system_dynamics_activation_authorized",
        "behavioural_closure_authorized",
        "reference_mode_promotion_authorized",
    ):
        if d.get(key) is not False:
            errors.append(f"successor unexpectedly authorizes {key}")

    ms = model["scientific_stage"]
    bs = baseline["canonical_state"]["scientific_stage"]
    if ms["trigger_aware_monitoring_horizon"] != LATEST:
        errors.append("model contract does not point to MoF-recovery successor")
    if ms["immediate_previous_trigger_aware_monitoring_horizon"] != SUCCESSOR:
        errors.append("model contract immediate monitoring predecessor changed")
    if bs["trigger_aware_monitoring_horizon"] != LATEST:
        errors.append("baseline canonical state does not point to MoF-recovery successor")
    if bs["immediate_previous_trigger_aware_monitoring_horizon"] != SUCCESSOR:
        errors.append("baseline immediate monitoring predecessor changed")
    if baseline["authority"].get("trigger_aware_monitoring_horizon") != LATEST:
        errors.append("baseline generic monitoring authority is stale")
    if (
        baseline["authority"].get(
            "trigger_aware_monitoring_horizon_post_mof_recovery_execution_boundary"
        )
        != HORIZON
    ):
        errors.append("baseline does not register MoF-recovery successor authority")
    if (
        baseline["authority"].get("trigger_aware_monitoring_horizon_post_counterpart_workflow_boundary")
        != PREDECESSOR
    ):
        errors.append("baseline lost predecessor counterpart-workflow authority")
    if baseline.get("manifest_version") != "1.14":
        errors.append("scientific baseline manifest version did not advance to 1.12")

    release = baseline["canonical_state"]["release_versioning"]
    if release["current_public_release"] != "0.3.0":
        errors.append("public release changed during MoF recovery governance hardening")
    if release["version_bump_required_now"] is not False:
        errors.append("MoF recovery governance hardening unexpectedly requires public version bump")

    return errors


def main() -> None:
    errors = audit_trigger_aware_monitoring_horizon_post_mof_recovery_execution_boundary()
    if errors:
        raise RuntimeError(
            "Post-MoF-recovery execution-boundary audit failed:\n- "
            + "\n- ".join(errors)
        )
    h = load(HORIZON)
    print(
        json.dumps(
            {
                "status": "PASS",
                "registry_version": h["registry_version"],
                "scientific_state": h["governing_state"]["current_scientific_state"],
                "mof_recovery_execution_authorized_now": h["current_disposition"][
                    "mof_full_2025_recovery_execution_authorized_now"
                ],
                "mof_recovery_active_polling": h["current_disposition"][
                    "mof_full_2025_recovery_active_polling"
                ],
                "remaining_required_source_count": h["current_disposition"][
                    "mof_full_2025_remaining_required_source_count"
                ],
                "next_dated_check": h["current_disposition"]["next_dated_check"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
