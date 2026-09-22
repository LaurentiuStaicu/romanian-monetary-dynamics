from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = "model/calibration_validation/bnr_bls_2025q2_post_terminal_indexed_endpoint_review_2026_09_22.json"
PREDECESSOR_PATH = "model/calibration_validation/bnr_bls_2025q2_source_discovery_terminal_assessment.json"
PANEL_PATH = "data/processed/bnr_bls_realised_rounds.csv"
EXPECTED_URL = "https://www.bnr.ro/uploads/editor/1843119253.xlsx"
EXPECTED_DECISION = "NO_REOPEN_OPAQUE_OFFICIAL_INDEXED_XLSX_ENDPOINT_NOT_SEMANTICALLY_IDENTIFIED"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_bnr_bls_2025q2_post_terminal_indexed_endpoint_review() -> list[str]:
    errors: list[str] = []
    a = load(ASSESSMENT_PATH)
    predecessor = load(PREDECESSOR_PATH)
    model = load("model/registries/model_contract.json")
    baseline = load("model/registries/scientific_baseline_manifest.json")
    horizon = load("model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_f4_structural.json")

    if a["decision"] != EXPECTED_DECISION:
        errors.append("indexed-endpoint review decision changed")
    if a["predecessor_terminal_assessment"] != PREDECESSOR_PATH:
        errors.append("predecessor BLS terminal assessment pointer changed")

    canonical = predecessor["canonical_state"]
    if canonical["observed_quarters"] != 11 or canonical["expected_quarters"] != 12:
        errors.append("historical BLS canonical panel cardinality changed")
    if canonical["missing_quarters"] != ["2025-Q2"]:
        errors.append("historical BLS missing round changed")
    if canonical["panel"] != PANEL_PATH:
        errors.append("historical BLS panel pointer changed")

    target = a["target_semantics"]
    if target["canonical_panel"] != PANEL_PATH:
        errors.append("post-terminal review panel pointer changed")
    if (target["observed_rounds"], target["expected_rounds"], target["missing_round"]) != (11, 12, "2025-Q2"):
        errors.append("post-terminal review panel state changed")

    evidence = a["newly_observed_public_evidence"]
    if evidence["exact_url"] != EXPECTED_URL:
        errors.append("opaque indexed endpoint changed")
    if evidence["official_domain"] is not True or not evidence["exact_url"].startswith("https://www.bnr.ro/"):
        errors.append("indexed endpoint is not pinned to official BNR domain")
    if evidence["public_fetch_observation"] != "REQUEST_REJECTED":
        errors.append("indexed endpoint fetch observation changed")
    for key in (
        "semantic_title_exposed",
        "publication_context_exposed",
        "realised_round_exposed",
        "workbook_bytes_retrieved",
        "content_hash_available",
        "xlsx_signature_verified",
        "workbook_sheet_structure_verified",
        "round_date_verified",
        "six_preregistered_observables_verified",
    ):
        if evidence[key] is not False:
            errors.append(f"unverified indexed-endpoint evidence promoted: {key}")

    semantic = a["semantic_adjudication"]
    for key in (
        "official_domain_plus_xlsx_extension_is_sufficient_identity",
        "opaque_editor_path_is_sufficient_identity",
        "exact_2025q2_bls_workbook_identity_established",
        "definitionally_equivalent_machine_readable_target_established",
        "trigger_condition_satisfied",
    ):
        if semantic[key] is not False:
            errors.append(f"opaque endpoint incorrectly satisfies semantic gate: {key}")

    disposition = a["disposition"]
    if disposition["status"] != "NEW_OFFICIAL_INDEXED_XLSX_ENDPOINT_SEMANTICS_UNRESOLVED_NO_REOPEN":
        errors.append("indexed endpoint disposition changed")
    if disposition["active_source_materialisation_task"] is not None:
        errors.append("opaque endpoint unexpectedly opens source materialisation")
    if disposition["canonical_panel_remains_11_of_12"] is not True:
        errors.append("opaque endpoint unexpectedly changes BLS panel completeness")
    if disposition["missing_round_remains"] != "2025-Q2":
        errors.append("opaque endpoint unexpectedly clears missing BLS round")
    for key in (
        "source_byte_acquisition_authorized",
        "numeric_extraction_authorized",
        "canonical_panel_mutation_authorized",
        "parameter_estimation_authorized",
        "model_selection_authorized",
        "lag_selection_authorized",
        "holdout_opening_authorized",
        "bank_credit_feedback_activation_authorized",
        "behavioural_closure_authorized",
        "model_effect",
    ):
        if disposition[key] is not False:
            errors.append(f"opaque endpoint unexpectedly authorizes {key}")

    rule = a["reopen_rule"]
    if rule["repeated_search_of_same_opaque_url_is_progress"] is not False:
        errors.append("repeated opaque-url search incorrectly counts as progress")
    for key in (
        "filename_or_timestamp_guessing_authorized",
        "opaque_url_semantic_inference_authorized",
        "rounded_report_substitution_authorized",
    ):
        if rule[key] is not False:
            errors.append(f"unsafe BLS reopen rule enabled: {key}")

    workflow_boundary = a.get("workflow_execution_boundary", {})
    expected_workflow_paths = {
        "may2025_identity_probe_workflow": ".github/workflows/bnr-bls-may2025-xlsx-probe.yml",
        "missing_round_recovery_workflow": ".github/workflows/bnr-bls-missing-round-workbook-recovery.yml",
        "missing_round_recovery_contract": "model/calibration_validation/bnr_bls_missing_round_workbook_recovery_contract.json",
    }
    for key, expected in expected_workflow_paths.items():
        if workflow_boundary.get(key) != expected:
            errors.append(f"BLS terminal workflow path changed: {key}")
    if workflow_boundary.get("may2025_identity_probe_current_role") != "HISTORICAL_MAY_2025_IDENTITY_REPROBE_ONLY":
        errors.append("BLS May-2025 identity workflow role changed")
    if workflow_boundary.get("missing_round_recovery_current_role") != "HISTORICAL_PREREGISTERED_CANDIDATE_REPLAY_ONLY_UNTIL_NEW_OFFICIAL_2025Q2_TRIGGER":
        errors.append("BLS missing-round recovery workflow role changed")
    if workflow_boundary.get("current_2025q2_candidate_count") != 0:
        errors.append("BLS workflow boundary unexpectedly reports a 2025-Q2 candidate")
    for key in (
        "manual_rerun_without_trigger_counts_as_scientific_progress",
        "manual_rerun_without_trigger_authorized_as_current_source_task",
        "workflow_rerun_may_mutate_canonical_panel",
    ):
        if workflow_boundary.get(key) is not False:
            errors.append(f"unsafe BLS terminal workflow rule enabled: {key}")

    recovery = load(workflow_boundary["missing_round_recovery_contract"])
    q2 = next((x for x in recovery["rounds"] if x["quarter"] == "2025-Q2"), None)
    if q2 is None:
        errors.append("BLS recovery contract lost 2025-Q2 round")
    else:
        if q2.get("url_candidates") != []:
            errors.append("BLS 2025-Q2 candidate added without a new trigger review")
        if q2.get("discovery_status") != "OFFICIAL_ANNEX_EXISTENCE_KNOWN_EXACT_WORKBOOK_URL_UNIDENTIFIED":
            errors.append("BLS 2025-Q2 frozen discovery status changed")
    if "Do not search for or probe a 2025-Q2 workbook candidate again unless new official BNR evidence" not in recovery.get("source_discovery_reopen_policy", ""):
        errors.append("BLS recovery contract lost terminal reopen policy")

    may_probe_text = (ROOT / workflow_boundary["may2025_identity_probe_workflow"]).read_text(encoding="utf-8")
    recovery_text = (ROOT / workflow_boundary["missing_round_recovery_workflow"]).read_text(encoding="utf-8")
    for token in (
        "HISTORICAL MAY-2025 XLSX IDENTITY RE-PROBE ONLY",
        "not a new BLS vintage",
        "does not",
        "2025-Q2",
    ):
        if token not in may_probe_text:
            errors.append(f"BLS May-2025 workflow lost safeguard: {token}")
    for token in (
        "HISTORICAL PREREGISTERED-CANDIDATE REPLAY",
        "unchanged rerun is not scientific progress",
        "semantically bound 2025-Q2 target",
    ):
        if token not in recovery_text:
            errors.append(f"BLS recovery workflow lost terminal safeguard: {token}")

    cv = model["calibration_validation"]
    if cv.get("bnr_bls_2025q2_source_discovery_terminal_assessment") != PREDECESSOR_PATH:
        errors.append("model contract does not preserve BLS terminal assessment")
    if cv.get("bnr_bls_2025q2_latest_post_terminal_review") != ASSESSMENT_PATH:
        errors.append("model contract does not register latest BLS post-terminal review")
    if cv.get("bnr_bls_2025q2_latest_post_terminal_review_status") != disposition["status"]:
        errors.append("model contract BLS post-terminal status is stale")

    authority = baseline["authority"]
    if authority.get("bnr_bls_2025q2_source_discovery_terminal_assessment") != PREDECESSOR_PATH:
        errors.append("scientific baseline does not preserve BLS terminal assessment")
    if authority.get("bnr_bls_2025q2_latest_post_terminal_review") != ASSESSMENT_PATH:
        errors.append("scientific baseline does not register latest BLS post-terminal review")

    trigger = next((x for x in horizon["horizons"] if x["id"] == "bnr_bls_2025_q2_exact_source"), None)
    if trigger is None:
        errors.append("trigger-aware horizon dropped BLS exact-source trigger")
    else:
        if trigger["mechanism_id"] != "aggregate_bank_credit_response":
            errors.append("BLS trigger mechanism changed")
        if trigger["next_check_type"] != "NEW_OFFICIAL_EVIDENCE_ONLY":
            errors.append("BLS trigger check type changed")

    return errors


def main() -> None:
    errors = audit_bnr_bls_2025q2_post_terminal_indexed_endpoint_review()
    if errors:
        raise RuntimeError("BNR BLS 2025-Q2 post-terminal indexed endpoint audit failed:\n- " + "\n- ".join(errors))
    a = load(ASSESSMENT_PATH)
    print(json.dumps({
        "status": "PASS",
        "decision": a["decision"],
        "indexed_url": a["newly_observed_public_evidence"]["exact_url"],
        "semantic_identity_established": a["semantic_adjudication"]["exact_2025q2_bls_workbook_identity_established"],
        "trigger_satisfied": a["semantic_adjudication"]["trigger_condition_satisfied"],
        "canonical_panel": "11/12",
        "missing_round": "2025-Q2",
        "model_effect": False,
    }, indent=2))


if __name__ == "__main__":
    main()
