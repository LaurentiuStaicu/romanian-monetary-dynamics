from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CONTRACT_PATH = (
    "model/dynamics/"
    "mof_announced_RON_primary_supply_reference_mode_contract_2026_09_20.json"
)


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_announced_supply_reference_mode_contract(
    contract: dict,
    measurement_design: dict,
    source_review: dict,
    boundary: dict,
    readiness: dict,
    feedback: dict,
    prereg: dict,
    model_contract: dict,
) -> list[str]:
    errors: list[str] = []

    if contract["reference_mode_id"] != "announced_RON_primary_supply_level":
        errors.append("reference-mode id changed")
    concept = contract["concept"]
    if concept["timing"] != "EX_ANTE_AT_OFFICIAL_ISSUANCE_ANNOUNCEMENT":
        errors.append("announced-supply timing changed")
    if concept["unit"] != "million_RON_nominal":
        errors.append("announced-supply unit changed")
    if concept["stock_normalisation_required"] is not False:
        errors.append("announced supply may not require stock normalisation")
    if concept["accepted_or_borrowed_amount_is_not_part_of_measure"] is not True:
        errors.append("accepted/borrowed amount must remain excluded")
    if concept["retail_or_external_issuance_is_not_part_of_measure"] is not True:
        errors.append("retail/external issuance must remain excluded")

    source = contract["official_source_family"]
    structure = source["monthly_order_structure"]
    for key in ("article_1", "annex_1", "annex_2"):
        if key not in structure:
            errors.append(f"monthly order structure missing {key}")

    docs = {item["source_id"]: item for item in contract["pilot_source_documents"]}
    expected_docs = {
        "mof_order_6826_january_2025",
        "mof_order_159_february_2025",
        "mof_order_352_march_2025",
    }
    if set(docs) != expected_docs:
        errors.append("pilot Ministry source-document set changed")

    expected_totals = {
        "mof_order_6826_january_2025": (5200.0, 570.0, 5770.0, "2024-12-30"),
        "mof_order_159_february_2025": (7200.0, 840.0, 8040.0, "2025-01-31"),
        "mof_order_352_march_2025": (7400.0, 840.0, 8240.0, "2025-02-28"),
    }
    for source_id, (base, sson, total, date) in expected_totals.items():
        item = docs[source_id]
        if item["article_1_base_nominal_RON_million"] != base:
            errors.append(f"{source_id}: Article 1 base total changed")
        if item["article_1_SSON_max_RON_million"] != sson:
            errors.append(f"{source_id}: Article 1 SSON total changed")
        if item["article_1_document_total_RON_million"] != total:
            errors.append(f"{source_id}: Article 1 combined total changed")
        if item["order_issue_date"] != date:
            errors.append(f"{source_id}: order issue date changed")
        if base + sson != total:
            errors.append(f"{source_id}: Article 1 arithmetic no longer reconciles")

    jan = docs["mof_order_6826_january_2025"]
    if jan["retained_flash_crosscheck_RON_million"] != 5770.0:
        errors.append("January Flash announced cross-check changed")
    if jan["flash_crosscheck_status"] != "EXACT_MATCH":
        errors.append("January Flash cross-check status changed")
    feb = docs["mof_order_159_february_2025"]
    if feb["retained_flash_crosscheck_RON_million"] != 8040.0:
        errors.append("February Flash announced cross-check changed")
    if feb["flash_crosscheck_status"] != "EXACT_MATCH_FOR_ANNOUNCED_SCHEDULE":
        errors.append("February Flash cross-check status changed")

    schema = contract["event_schema"]
    expected_event_types = {
        "T_BILL_COMPETITIVE_REFERENCE_AUCTION",
        "BENCHMARK_BOND_COMPETITIVE_REFERENCE_AUCTION",
        "BENCHMARK_BOND_SSON",
    }
    if set(schema["allowed_event_types"]) != expected_event_types:
        errors.append("allowed event-type set changed")
    for field in (
        "event_type",
        "event_date",
        "instrument_type",
        "instrument_identity",
        "currency",
        "announced_nominal_RON_million",
    ):
        if field not in schema["required_event_fields"]:
            errors.append(f"required event field missing: {field}")

    rules = contract["component_rules"]
    if set(rules) != expected_event_types:
        errors.append("component-rule set changed")
    if rules["T_BILL_COMPETITIVE_REFERENCE_AUCTION"]["source"] != "Annex 1":
        errors.append("T-bill source annex changed")
    if rules["BENCHMARK_BOND_COMPETITIVE_REFERENCE_AUCTION"]["source"] != "Annex 2":
        errors.append("benchmark competitive source annex changed")
    if rules["BENCHMARK_BOND_SSON"]["source"] != "Annex 2":
        errors.append("SSON source annex changed")
    for event_type, item in rules.items():
        if item["included"] is not True:
            errors.append(f"{event_type}: included status changed")

    aggregation = contract["aggregation_rules"]
    if aggregation["event_level_is_canonical"] is not True:
        errors.append("event-level canonical rule changed")
    if aggregation["monthly_aggregation_allowed"] is not True:
        errors.append("monthly aggregation unexpectedly disabled")
    if aggregation["document_reconciliation_required"] is not True:
        errors.append("document reconciliation must remain required")
    if "event_date" not in aggregation["monthly_bucket_rule"]:
        errors.append("monthly bucket rule no longer uses event date")

    publication = contract["publication_time_rules"]
    if publication["economic_information_date"] != "source_order_issue_date":
        errors.append("economic information date rule changed")
    if publication["exact_intraday_timestamp_required_for_this_reference_mode"] is not False:
        errors.append("intraday timestamp may not be required for level reference mode")
    if publication["exact_intraday_timestamp_required_before_supply_surprise_measure"] is not True:
        errors.append("supply surprise must still require exact pre-announcement timing")

    completed = contract["completed_period_rules"]
    if completed["reference_mode_values_must_use_event_dates_not_future_schedule_status"] is not True:
        errors.append("completed-period event-date rule changed")
    if completed["forward_announced_rows_may_be_labelled_realised_completed_period_supply"] is not False:
        errors.append("forward rows may not be labelled completed-period supply")
    if completed["pilot_cutoff_date"] != "2025-03-31":
        errors.append("pilot cutoff date changed")

    exclusions = set(contract["explicit_exclusions"])
    for required in (
        "TEZAUR retail issuance",
        "FIDELIS retail issuance",
        "Eurobonds and other external-market issuance",
        "accepted/borrowed auction outcomes",
        "submitted bids",
        "secondary-market transactions",
    ):
        if required not in exclusions:
            errors.append(f"required exclusion missing: {required}")

    gate = contract["materialisation_gate"]
    for key in (
        "raw_pdf_retention_required",
        "native_text_extraction_required",
        "all_source_rows_must_reconcile_to_article_1_totals",
        "january_flash_total_must_equal_5770_RON_million",
        "february_flash_announced_schedule_total_must_equal_8040_RON_million",
    ):
        if gate[key] is not True:
            errors.append(f"materialisation gate changed: {key}")
    for key in (
        "ocr_authorized",
        "visual_chart_digitisation_authorized",
        "manual_value_approximation_authorized",
        "reference_mode_promotion_authorized_by_contract_alone",
    ):
        if gate[key] is not False:
            errors.append(f"materialisation gate may not authorize {key}")

    guards = contract["scientific_guards"]
    for key, value in guards.items():
        if value is not False:
            errors.append(f"source contract may not authorize {key}")

    next_task = contract["next_task"]
    if next_task["id"] != "mof_announced_RON_primary_supply_source_vintage_pilot":
        errors.append("source-contract next task changed")
    if next_task["authorization"] != (
        "RAW_SOURCE_RETENTION_EXACT_EVENT_EXTRACTION_AND_REFERENCE_MODE_PILOT_ONLY"
    ):
        errors.append("source-contract next-task authorization changed")
    if next_task["may_promote_reference_mode_only_if_all_reconciliation_gates_pass"] is not True:
        errors.append("reference-mode promotion must remain reconciliation-gated")
    if next_task["may_estimate_supply_to_yield_effect"] is not False:
        errors.append("source contract may not authorize yield-effect estimation")
    if next_task["may_activate_feedback"] is not False:
        errors.append("source contract may not authorize feedback")

    if measurement_design.get("announced_RON_primary_supply_reference_mode_contract") != CONTRACT_PATH:
        errors.append("measurement design lacks announced-supply source contract")
    measure = next(
        item for item in measurement_design["measurement_vector"]
        if item["measure_id"] == "announced_RON_primary_supply_level"
    )
    if measure.get("reference_mode_contract") != CONTRACT_PATH:
        errors.append("announced-supply measure lacks source contract")
    if measure["current_source_status"] != (
        "EXACT_Q1_LEGACY_PILOT_RETAINED_FULL_YEAR_DEFINITION_CHANGED"
    ):
        errors.append("announced-supply legacy measure source status changed")
    if measure.get("primary_recovery_path") is not False:
        errors.append("legacy announced-supply measure may not remain primary recovery path")
    if measurement_design["scientific_effect"]["exact_reference_mode_promoted"] is not False:
        errors.append("source contract may not promote exact reference mode")

    if source_review.get("announced_RON_primary_supply_reference_mode_contract") != CONTRACT_PATH:
        errors.append("source-boundary review lacks announced-supply contract")

    node = next(
        item for item in boundary["variables"]
        if item["id"] == "government_securities_supply_pressure"
    )
    if node.get("announced_RON_primary_supply_reference_mode_contract") != CONTRACT_PATH:
        errors.append("boundary registry lacks announced-supply contract")
    if node["announced_RON_primary_supply_reference_mode_status"] != (
        "LEGACY_Q1_COMBINED_PILOT_RETAINED_NOT_FULL_YEAR_STABLE"
    ):
        errors.append("boundary registry announced-supply status changed")
    if node["current_boundary_class"] != "UNRESOLVED":
        errors.append("source contract may not resolve supply-pressure umbrella")
    if node["current_feedback_activation_authorized"] is not False:
        errors.append("source contract may not activate supply-pressure umbrella")

    link = next(
        item for item in readiness["links"]
        if item["loop_id"] == "government_issuance_yield_loop"
        and item["from"] == "government_debt_issuance"
        and item["to"] == "government_securities_supply_pressure"
    )
    if link.get("announced_RON_primary_supply_reference_mode_contract") != CONTRACT_PATH:
        errors.append("issuance-pressure link lacks announced-supply contract")
    if link["source_boundary_status"] != (
        "STRUCTURED_VECTOR_COMPETITIVE_ONLY_PARTIAL_EXACT_MONTHLY_10_OF_12_EVENT_COMPLETE_9_OF_12_CANONICAL_PROMOTION_BLOCKED_3_REQUIRED_SOURCES_MISSING"
    ):
        errors.append("issuance-pressure link source-contract status changed")
    if link["exact_integrated_equation_ready"] is not False:
        errors.append("source contract may not make integrated equation ready")
    if link["current_activation_authorized"] is not False:
        errors.append("source contract may not activate issuance-pressure link")

    loop = next(
        item for item in feedback["loops"]
        if item["id"] == "government_issuance_yield_loop"
    )
    if loop.get("announced_RON_primary_supply_reference_mode_contract") != CONTRACT_PATH:
        errors.append("feedback registry lacks announced-supply contract")
    if loop["quantitatively_active"] is not False:
        errors.append("source contract may not activate issuance-yield loop")

    bridge = next(
        item for item in prereg["required_bridges_before_any_closed_empirical_loop_claim"]
        if item["id"] == "issuance_to_supply_pressure"
    )
    if bridge.get("announced_RON_primary_supply_reference_mode_contract") != CONTRACT_PATH:
        errors.append("issuance-pressure bridge lacks announced-supply contract")
    if bridge["status"] != (
        "STRUCTURED_VECTOR_COMPETITIVE_ONLY_PARTIAL_EXACT_MONTHLY_10_OF_12_EVENT_COMPLETE_9_OF_12_CANONICAL_PROMOTION_BLOCKED_3_REQUIRED_SOURCES_MISSING"
    ):
        errors.append("issuance-pressure bridge source-contract status changed")

    dynamic = model_contract["dynamic_core"]
    if dynamic.get("mof_announced_RON_primary_supply_reference_mode_contract") != CONTRACT_PATH:
        errors.append("model contract lacks announced-supply source contract")
    if dynamic["mof_announced_RON_primary_supply_reference_mode_status"] != (
        "PASS_EXACT_Q1_LEGACY_COMBINED_PILOT_FULL_YEAR_DEFINITION_NOT_STABLE"
    ):
        errors.append("model contract announced-supply status changed")
    if dynamic["next_government_issuance_yield_empirical_task"] != (
        "mof_announced_RON_primary_reference_auction_full_2025_missing_source_recovery"
    ):
        errors.append("model contract next task changed")
    if dynamic["government_issuance_yield_feedback_activation_authorized"] is not False:
        errors.append("source contract may not authorize issuance-yield feedback")

    return errors


def main() -> None:
    contract = load(CONTRACT_PATH)
    measurement_design = load(
        "model/dynamics/government_securities_supply_measurement_design_review_2026_09_20.json"
    )
    source_review = load(
        "model/dynamics/government_securities_supply_pressure_source_boundary_review_2026_09_20.json"
    )
    boundary = load("model/dynamics/feedback_variable_boundary_registry.json")
    readiness = load("model/dynamics/feedback_link_readiness_registry.json")
    feedback = load("model/dynamics/feedback_registry.json")
    prereg = load(
        "model/dynamics/government_issuance_yield_boundary_preregistration_2026_09_20.json"
    )
    model_contract = load("model/registries/model_contract.json")

    errors = audit_announced_supply_reference_mode_contract(
        contract,
        measurement_design,
        source_review,
        boundary,
        readiness,
        feedback,
        prereg,
        model_contract,
    )
    if errors:
        raise RuntimeError(
            "Announced RON primary-supply reference-mode contract audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(
        json.dumps(
            {
                "status": "PASS",
                "reference_mode_id": "announced_RON_primary_supply_level",
                "pilot_source_documents": 3,
                "allowed_event_types": 3,
                "january_document_total_RON_million": 5770.0,
                "february_document_total_RON_million": 8040.0,
                "march_document_total_RON_million": 8240.0,
                "stock_normalisation_required": False,
                "reference_mode_promoted": False,
                "feedback_activation_authorized": False,
                "next_task": "mof_announced_RON_primary_reference_auction_supply_full_2025_source_vintage",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
