from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT = ROOT / "model/registries/provenance_integrity_terminal_assessment_2026_09_22.json"


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def audit_provenance_integrity_terminal() -> list[str]:
    errors: list[str] = []
    assessment = json.loads(ASSESSMENT.read_text(encoding="utf-8"))
    source = load("data/provenance/source_vintage_inventory_registry.json")
    processed = load("data/provenance/processed_data_inventory_registry.json")
    validation = load("data/provenance/validation_recovery_vintage_status.json")
    model = load("model/registries/model_contract.json")
    baseline = load("model/registries/scientific_baseline_manifest.json")

    expected_status = "PROVENANCE_INTEGRITY_HARDENING_COMPLETE_CURRENT_SCOPE_NO_ACTIVE_REPAIR_TASK"
    if assessment["terminal_state"]["status"] != expected_status:
        errors.append("terminal provenance status changed")

    source_counts = Counter(entry["anchor_type"] for entry in source["entries"])
    if source["directory_count"] != len(source["entries"]):
        errors.append("source-vintage registry directory count is stale")
    if assessment["terminal_state"]["source_vintage_directory_count"] != source["directory_count"]:
        errors.append("terminal source-vintage directory count is stale")
    if dict(source_counts) != assessment["terminal_state"]["source_vintage_anchor_class_counts"]:
        errors.append("terminal source-vintage anchor-class counts are stale")

    processed_counts = Counter(entry["provenance_class"] for entry in processed["entries"])
    if processed["file_count"] != len(processed["entries"]):
        errors.append("processed-data registry file count is stale")
    if assessment["terminal_state"]["processed_csv_count"] != processed["file_count"]:
        errors.append("terminal processed-data count is stale")
    if dict(processed_counts) != assessment["terminal_state"]["processed_provenance_class_counts"]:
        errors.append("terminal processed-data provenance-class counts are stale")

    vintages = validation.get("vintages", [])
    if len(vintages) != 1:
        errors.append("validation-recovery vintage cardinality changed")
    else:
        vintage = vintages[0]
        terminal_validation = assessment["terminal_state"]["validation_recovery"]
        expected = {
            "status": vintage["status"],
            "known_raw_sha256_count": vintage["known_raw_sha256_count"],
            "byte_identical_raw_payloads_retained": vintage["raw_payloads_materialized_in_repository"],
            "raw_payloads_not_recovered": vintage["raw_payloads_not_recovered"],
            "complete_historical_raw_vintage_reproducible": vintage["exact_vintage_reproducible_from_repository"],
            "pinned_repository_input_file_count": len(vintage["repository_validation_inputs"]["files"]),
            "normalized_repository_input_identity_pinned": vintage["repository_validation_inputs"]["scientific_boundary"]["normalized_repository_input_identity_pinned"],
        }
        if terminal_validation != expected:
            errors.append("terminal validation-recovery provenance state is stale")

    authority_pairs = {
        "source_vintage_inventory": (
            model["repository_governance"]["source_vintage_inventory_registry"],
            baseline["authority"]["source_vintage_inventory_registry"],
        ),
        "processed_data_inventory": (
            model["repository_governance"]["processed_data_inventory_registry"],
            baseline["authority"]["processed_data_inventory"],
        ),
        "validation_recovery_vintage_status": (
            model["repository_governance"]["validation_recovery_vintage_status"],
            baseline["authority"]["validation_recovery_vintage_status"],
        ),
    }
    for key, (model_path, baseline_path) in authority_pairs.items():
        terminal_path = assessment["authorities"][key]
        if not (terminal_path == model_path == baseline_path):
            errors.append(f"provenance governance parity drift: {key}")

    terminal_path = "model/registries/provenance_integrity_terminal_assessment_2026_09_22.json"
    if model["repository_governance"].get("provenance_integrity_terminal_assessment") != terminal_path:
        errors.append("model contract does not register provenance terminal assessment")
    if baseline["authority"].get("provenance_integrity_terminal_assessment") != terminal_path:
        errors.append("scientific baseline does not register provenance terminal assessment")

    if assessment["terminal_state"]["central_governance_parity"] is not True:
        errors.append("terminal assessment no longer declares governance parity")
    if assessment["terminal_state"]["active_repair_task"] is not None:
        errors.append("terminal assessment retains an active provenance repair task")
    if assessment["current_disposition"]["next_operational_state"] != "EVIDENCE_TRIGGERED_BASELINE_HOLD":
        errors.append("terminal provenance next operational state changed")
    if assessment["current_disposition"]["repeated_provenance_reaudit_without_trigger_is_progress"] is not False:
        errors.append("terminal assessment permits repeated no-trigger provenance re-audit")
    for key in (
        "live_refetch_authorized",
        "data_rewrite_authorized",
        "historical_artifact_deletion_authorized",
        "estimation_or_refit_authorized",
        "holdout_opening_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "version_bump_required",
    ):
        if assessment["current_disposition"][key] is not False:
            errors.append(f"terminal provenance assessment unexpectedly authorizes {key}")

    if not assessment.get("reopen_conditions"):
        errors.append("terminal provenance assessment lacks reopen conditions")

    return errors


def main() -> None:
    errors = audit_provenance_integrity_terminal()
    if errors:
        raise RuntimeError("Provenance integrity terminal audit failed:\n- " + "\n- ".join(errors))
    assessment = json.loads(ASSESSMENT.read_text(encoding="utf-8"))
    print(json.dumps({
        "status": "PASS",
        "terminal_status": assessment["terminal_state"]["status"],
        "source_vintage_directories": assessment["terminal_state"]["source_vintage_directory_count"],
        "processed_csvs": assessment["terminal_state"]["processed_csv_count"],
        "active_repair_task": assessment["terminal_state"]["active_repair_task"],
        "next_operational_state": assessment["current_disposition"]["next_operational_state"],
        "scientific_state_changed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
