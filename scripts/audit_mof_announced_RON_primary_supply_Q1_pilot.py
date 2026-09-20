from __future__ import annotations

import csv
import hashlib
import json
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PILOT_PATH = (
    "model/dynamics/"
    "mof_announced_RON_primary_supply_reference_mode_pilot_Q1_2025.json"
)
EVENTS_PATH = ROOT / "data/processed/mof_announced_RON_primary_supply_Q1_2025_events.csv"
MONTHLY_PATH = ROOT / "data/processed/mof_announced_RON_primary_supply_Q1_2025_monthly.csv"
VINTAGE_ROOT = ROOT / (
    "data/source_vintages/"
    "mof-announced-ron-primary-supply-pilot-2026-09-20"
)


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def audit_announced_supply_q1_pilot(
    pilot: dict,
    contract: dict,
    manifest: dict,
    measurement_design: dict,
    boundary: dict,
    readiness: dict,
    feedback: dict,
    prereg: dict,
    model_contract: dict,
) -> list[str]:
    errors: list[str] = []

    if pilot["status"] != (
        "PASS_EXACT_Q1_EVENT_LEVEL_PILOT_CANONICAL_PROMOTION_DEFERRED"
    ):
        errors.append("Q1 announced-supply pilot status changed")
    if pilot["reference_mode_id"] != "announced_RON_primary_supply_level":
        errors.append("Q1 pilot reference-mode id changed")
    if pilot["pilot_cutoff_date"] != "2025-03-31":
        errors.append("Q1 pilot cutoff changed")

    if manifest["all_required_anchor_checks_pass"] is not True:
        errors.append("retained prospectus source-vintage anchor gate is not PASS")
    if manifest["status"] != "RAW_SOURCES_RETAINABLE_NATIVE_TEXT_ANCHORS_PASS":
        errors.append("retained prospectus source-vintage status changed")

    identities = pilot["source_identities"]
    manifest_by_id = {item["source_id"]: item for item in manifest["sources"]}
    for source_id, expected in identities.items():
        retained = manifest_by_id[source_id]
        raw_path = VINTAGE_ROOT / retained["raw_path"]
        text_path = VINTAGE_ROOT / retained["native_text_path"]
        if not raw_path.is_file() or not text_path.is_file():
            errors.append(f"{source_id}: retained source file missing")
            continue
        if raw_path.stat().st_size != expected["raw_bytes"]:
            errors.append(f"{source_id}: raw byte size changed")
        if sha256_file(raw_path) != expected["raw_sha256"]:
            errors.append(f"{source_id}: raw SHA-256 changed")
        if text_path.stat().st_size != expected["native_text_bytes"]:
            errors.append(f"{source_id}: native-text byte size changed")
        if sha256_file(text_path) != expected["native_text_sha256"]:
            errors.append(f"{source_id}: native-text SHA-256 changed")
        if retained["raw_sha256"] != expected["raw_sha256"]:
            errors.append(f"{source_id}: manifest raw hash differs from pilot")
        if retained["native_text_sha256"] != expected["native_text_sha256"]:
            errors.append(f"{source_id}: manifest text hash differs from pilot")
        if retained["all_required_anchors_found"] is not True:
            errors.append(f"{source_id}: source anchors no longer pass")

    reconciliations = {
        item["source_id"]: item for item in pilot["document_reconciliation"]
    }
    expected_reconciliation = {
        "mof_order_6826_january_2025": (2, 9, 5200.0, 570.0, 5770.0),
        "mof_order_159_february_2025": (2, 10, 7200.0, 840.0, 8040.0),
        "mof_order_352_march_2025": (2, 10, 7400.0, 840.0, 8240.0),
    }
    for source_id, expected in expected_reconciliation.items():
        item = reconciliations[source_id]
        t_bill_rows, bond_rows, base, sson, total = expected
        if item["parsed_t_bill_rows"] != t_bill_rows:
            errors.append(f"{source_id}: T-bill row count changed")
        if item["parsed_bond_rows"] != bond_rows:
            errors.append(f"{source_id}: bond row count changed")
        if item["parsed_base_nominal_RON_million"] != base:
            errors.append(f"{source_id}: base announced amount changed")
        if item["parsed_SSON_RON_million"] != sson:
            errors.append(f"{source_id}: SSON announced amount changed")
        if item["parsed_document_total_RON_million"] != total:
            errors.append(f"{source_id}: document total changed")
        for key in ("base_reconciles", "SSON_reconciles", "document_total_reconciles"):
            if item[key] is not True:
                errors.append(f"{source_id}: reconciliation gate failed: {key}")

    events = read_csv(EVENTS_PATH)
    if len(events) != 64:
        errors.append(f"expected 64 event rows, observed {len(events)}")

    event_types = defaultdict(int)
    monthly = defaultdict(float)
    completed_count = 0
    forward = []
    for row in events:
        event_types[row["event_type"]] += 1
        amount = float(row["announced_nominal_RON_million"])
        within = row["within_pilot_cutoff"] == "True"
        if within:
            completed_count += 1
            monthly[row["event_date"][:7]] += amount
        else:
            forward.append(row)

    if dict(event_types) != {
        "BENCHMARK_BOND_COMPETITIVE_REFERENCE_AUCTION": 29,
        "BENCHMARK_BOND_SSON": 29,
        "T_BILL_COMPETITIVE_REFERENCE_AUCTION": 6,
    }:
        errors.append(f"event-type counts changed: {dict(event_types)}")
    if completed_count != 63:
        errors.append(f"expected 63 completed-cutoff events, observed {completed_count}")
    if dict(monthly) != {
        "2025-01": 5770.0,
        "2025-02": 8040.0,
        "2025-03": 8165.0,
    }:
        errors.append(f"completed monthly sums changed: {dict(monthly)}")

    if len(forward) != 1:
        errors.append(f"expected one post-cutoff event, observed {len(forward)}")
    else:
        row = forward[0]
        if not (
            row["event_date"] == "2025-04-01"
            and row["event_type"] == "BENCHMARK_BOND_SSON"
            and row["isin"] == "RO45DLJ4EE76"
            and float(row["announced_nominal_RON_million"]) == 75.0
        ):
            errors.append("post-cutoff SSON identity changed")

    monthly_rows = read_csv(MONTHLY_PATH)
    expected_monthly_rows = [
        ("2025-01", 5770.0, 20),
        ("2025-02", 8040.0, 22),
        ("2025-03", 8165.0, 21),
    ]
    if len(monthly_rows) != 3:
        errors.append("monthly pilot row count changed")
    else:
        for row, expected in zip(monthly_rows, expected_monthly_rows):
            period, amount, count = expected
            if row["period"] != period:
                errors.append(f"monthly period changed: {row['period']}")
            if float(row["announced_RON_primary_supply_million"]) != amount:
                errors.append(f"{period}: monthly amount changed")
            if int(row["event_count"]) != count:
                errors.append(f"{period}: monthly event count changed")
            if row["status"] != "COMPLETED_PERIOD_EXACT_EVENT_SUM":
                errors.append(f"{period}: monthly status changed")

    if pilot["completed_monthly_reference_mode"] != {
        "2025-01": 5770.0,
        "2025-02": 8040.0,
        "2025-03": 8165.0,
    }:
        errors.append("pilot monthly reference-mode mapping changed")

    semantics = pilot["semantics"]
    if semantics["ex_ante_announced_supply_only"] is not True:
        errors.append("pilot must remain ex-ante announced supply only")
    for key in (
        "accepted_or_borrowed_amount_included",
        "submitted_bids_included",
        "retail_issuance_included",
        "external_issuance_included",
        "stock_normalisation_used",
        "supply_surprise_constructed",
        "duration_supply_constructed",
    ):
        if semantics[key] is not False:
            errors.append(f"Q1 pilot may not introduce {key}")

    disposition = pilot["scientific_disposition"]
    for key in (
        "canonical_reference_modes_registry_promoted",
        "government_securities_supply_pressure_node_resolved",
        "single_supply_pressure_scalar_selected",
        "yield_effect_estimation_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "public_version_change_authorized",
    ):
        if disposition[key] is not False:
            errors.append(f"Q1 pilot may not promote {key}")
    if disposition["exact_event_level_pilot_materialised"] is not True:
        errors.append("exact event-level pilot must remain materialised")
    if disposition["exact_completed_monthly_pilot_materialised"] is not True:
        errors.append("exact monthly pilot must remain materialised")

    next_gate = pilot["next_gate"]
    if next_gate["id"] != "mof_announced_RON_primary_supply_full_2025_extension":
        errors.append("Q1 pilot next gate changed")
    if next_gate["authorization"] != (
        "SOURCE_VINTAGE_EXTENSION_AND_EXACT_EVENT_MATERIALISATION_ONLY"
    ):
        errors.append("Q1 pilot next-gate authorization changed")
    if next_gate["may_estimate_supply_to_yield_effect"] is not False:
        errors.append("Q1 pilot may not authorize yield-effect estimation")
    if next_gate["may_activate_feedback"] is not False:
        errors.append("Q1 pilot may not authorize feedback")

    measure = next(
        item for item in measurement_design["measurement_vector"]
        if item["measure_id"] == "announced_RON_primary_supply_level"
    )
    if measure.get("reference_mode_pilot_assessment") != PILOT_PATH:
        errors.append("measurement design lacks Q1 pilot assessment")
    if measure["current_source_status"] != (
        "EXACT_Q1_EVENT_LEVEL_PILOT_MATERIALISED_FULL_2025_EXTENSION_PENDING"
    ):
        errors.append("measurement design Q1 pilot status changed")

    node = next(
        item for item in boundary["variables"]
        if item["id"] == "government_securities_supply_pressure"
    )
    if node.get("announced_RON_primary_supply_reference_mode_pilot_assessment") != PILOT_PATH:
        errors.append("boundary registry lacks Q1 pilot assessment")
    if node["announced_RON_primary_supply_reference_mode_status"] != (
        "EXACT_Q1_PILOT_MATERIALISED_NOT_CANONICAL"
    ):
        errors.append("boundary registry Q1 pilot status changed")
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("Q1 pilot may not resolve umbrella node")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("Q1 pilot may not activate umbrella node")

    link = next(
        item for item in readiness["links"]
        if item["loop_id"] == "government_issuance_yield_loop"
        and item["from"] == "government_debt_issuance"
        and item["to"] == "government_securities_supply_pressure"
    )
    if link.get("announced_RON_primary_supply_reference_mode_pilot_assessment") != PILOT_PATH:
        errors.append("issuance-pressure link lacks Q1 pilot assessment")
    if link["source_boundary_status"] != (
        "STRUCTURED_VECTOR_ANNOUNCED_SUPPLY_Q1_PILOT_PASS_FULL_2025_EXTENSION_PENDING"
    ):
        errors.append("issuance-pressure link Q1 status changed")
    if link["exact_integrated_equation_ready"] is not False:
        errors.append("Q1 pilot may not make integrated equation ready")
    if link["current_activation_authorized"] is not False:
        errors.append("Q1 pilot may not activate issuance-pressure link")

    loop = next(
        item for item in feedback["loops"]
        if item["id"] == "government_issuance_yield_loop"
    )
    if loop.get("announced_RON_primary_supply_reference_mode_pilot_assessment") != PILOT_PATH:
        errors.append("feedback registry lacks Q1 pilot assessment")
    if loop["quantitatively_active"] is not False:
        errors.append("Q1 pilot may not activate issuance-yield loop")

    bridge = next(
        item for item in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if item["id"] == "issuance_to_supply_pressure"
    )
    if bridge.get("announced_RON_primary_supply_reference_mode_pilot_assessment") != PILOT_PATH:
        errors.append("issuance-pressure bridge lacks Q1 pilot assessment")
    if bridge["status"] != (
        "STRUCTURED_VECTOR_ANNOUNCED_SUPPLY_Q1_PILOT_PASS_FULL_2025_EXTENSION_PENDING"
    ):
        errors.append("issuance-pressure bridge Q1 status changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("mof_announced_RON_primary_supply_reference_mode_pilot_assessment") != PILOT_PATH:
        errors.append("model contract lacks Q1 pilot assessment")
    if dynamic["mof_announced_RON_primary_supply_reference_mode_status"] != (
        "PASS_EXACT_Q1_EVENT_LEVEL_PILOT_CANONICAL_PROMOTION_DEFERRED"
    ):
        errors.append("model contract Q1 pilot status changed")
    if dynamic["next_government_issuance_yield_empirical_task"] != (
        "mof_announced_RON_primary_supply_full_2025_extension"
    ):
        errors.append("model contract next task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("Q1 pilot may not authorize feedback")

    return errors


def main() -> None:
    pilot = load(PILOT_PATH)
    contract = load(
        "model/dynamics/mof_announced_RON_primary_supply_reference_mode_contract_2026_09_20.json"
    )
    manifest = load(
        "data/source_vintages/mof-announced-ron-primary-supply-pilot-2026-09-20/"
        "source_vintage_manifest.json"
    )
    measurement_design = load(
        "model/dynamics/government_securities_supply_measurement_design_review_2026_09_20.json"
    )
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    readiness = load("model/dynamics/feedback_link_readiness_registry.json")
    feedback = load("model/dynamics/feedback_registry.json")
    prereg = load(
        "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
    )
    model_contract = load("model/registries/model_contract.json")

    errors = audit_announced_supply_q1_pilot(
        pilot,
        contract,
        manifest,
        measurement_design,
        boundary,
        readiness,
        feedback,
        prereg,
        model_contract,
    )
    if errors:
        raise RuntimeError(
            "Announced RON primary-supply Q1 pilot audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(
        json.dumps(
            {
                "status": "PASS",
                "reference_mode_id": "announced_RON_primary_supply_level",
                "source_orders": 3,
                "event_rows_total": 64,
                "completed_event_rows": 63,
                "monthly_reference_mode": {
                    "2025-01": 5770.0,
                    "2025-02": 8040.0,
                    "2025-03": 8165.0,
                },
                "post_cutoff_forward_SSON_RON_million": 75.0,
                "canonical_reference_mode_promoted": False,
                "feedback_activation_authorized": False,
                "next_gate": "mof_announced_RON_primary_supply_full_2025_extension",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
