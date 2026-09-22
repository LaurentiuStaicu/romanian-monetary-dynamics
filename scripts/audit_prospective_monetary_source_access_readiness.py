from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = "model/calibration_validation/prospective_monetary_source_access_readiness_2026_09_22.json"
CONTRACT_PATH = "model/calibration_validation/prospective_monetary_confirmation_contract.json"
STATUS_PATH = "model/calibration_validation/prospective_monetary_confirmation_status.json"
HORIZON_PATH = "model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_source_diagnostics.json"
EXPECTED_DECISION = "MONETARY_SOURCE_ACCESS_READY_WAIT_FOR_OFFICIAL_BNR_EVENT_NO_RESPONSE_PEEK"
EXPECTED_MIR = "MIR.M.RO.B.A2C.A.R.A.2250.RON.N"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_prospective_monetary_source_access_readiness() -> list[str]:
    errors: list[str] = []
    a = load(ASSESSMENT_PATH)
    contract = load(CONTRACT_PATH)
    status = load(STATUS_PATH)
    horizon = load(HORIZON_PATH)
    model = load("model/registries/model_contract.json")
    baseline = load("model/registries/scientific_baseline_manifest.json")

    if a["decision"] != EXPECTED_DECISION:
        errors.append("prospective monetary source-access decision changed")
    if a["frozen_confirmation_contract"] != CONTRACT_PATH:
        errors.append("prospective monetary frozen contract pointer changed")
    if a["current_confirmation_status"] != STATUS_PATH:
        errors.append("prospective monetary status pointer changed")
    if a["governing_trigger_horizon"] != HORIZON_PATH:
        errors.append("prospective monetary horizon pointer changed")

    gate = a["current_gate_state"]
    if gate["next_scheduled_policy_meeting"] != "2026-10-08":
        errors.append("next BNR policy meeting changed")
    if gate["nonzero_policy_rate_events_in_reserved_window"] != 0:
        errors.append("source-access readiness may not create a policy-rate event")
    for key in (
        "identifying_driver_variation_available",
        "formal_confirmation_opened",
        "reserved_response_values_inspected",
    ):
        if gate[key] is not False:
            errors.append(f"monetary gate unexpectedly opened: {key}")
    if gate["status"] != "WAIT_FOR_NEW_POLICY_RATE_EVENT":
        errors.append("prospective monetary driver status changed")

    frozen = contract["prospective_data_boundary"]
    if frozen["reserved_response_series"] != f"ECB {EXPECTED_MIR}":
        errors.append("frozen reserved MIR series changed")
    if frozen["policy_driver"] != "BNR monetary-policy rate":
        errors.append("frozen BNR policy driver changed")
    if frozen["no_response_peeking_before_event"] is not True:
        errors.append("frozen no-peek-before-event rule changed")
    if frozen["no_response_peeking_before_official_release"] is not True:
        errors.append("frozen no-peek-before-release rule changed")

    status_gate = status["identification_gate"]
    if status_gate["nonzero_policy_rate_events_in_reserved_window"] != 0:
        errors.append("current prospective status unexpectedly contains identifying event")
    if status_gate["identifying_driver_variation_available"] is not False:
        errors.append("current prospective status unexpectedly has driver variation")
    if status["prospective_window"]["response_series_values_inspected"] is not False:
        errors.append("reserved MIR values were inspected unexpectedly")

    historical = a["historical_discovery_provenance"]
    if historical["august_2026_decision_report_url"] != contract["current_schedule_evidence"]["last_observed_decision"]["source_url"]:
        errors.append("historical August decision locator no longer matches frozen contract")
    if historical["october_2026_social_calendar_url"] != contract["current_schedule_evidence"]["next_policy_meeting"]["source_url"]:
        errors.append("historical October social-calendar locator no longer matches frozen contract")

    driver = a["authoritative_driver_access"]
    if driver["official_calendar_page"] != status["policy_driver_evidence"]["official_calendar_page"]["source_url"]:
        errors.append("official BNR calendar surface changed")
    if driver["official_decision_release_index"] != "https://www.bnr.ro/2629-politica-monetara":
        errors.append("official BNR decision-release surface changed")
    if driver["exact_2026_10_08_decision_release_url_known"] is not False:
        errors.append("future BNR decision communiqué URL may not be invented")
    for key in (
        "media_or_social_result_substitution_authorized",
        "future_decision_url_guessing_authorized",
        "market_expectation_substitution_authorized",
    ):
        if driver[key] is not False:
            errors.append(f"unsafe BNR driver-source rule enabled: {key}")

    response = a["authoritative_response_access"]
    if response["dataset"] != "MIR":
        errors.append("prospective monetary response dataset changed")
    if response["exact_series_key"] != EXPECTED_MIR:
        errors.append("prospective monetary MIR series key changed")
    if response["exact_series_url"] != f"https://data.ecb.europa.eu/data/datasets/MIR/{EXPECTED_MIR}":
        errors.append("prospective monetary MIR series URL changed")
    if response["october_2026_reference_period_release_date"] != "2026-12-02":
        errors.append("October 2026 MIR response release date changed")
    semantics = response["semantic_identity"]
    expected_semantics = {
        "frequency": "Monthly",
        "reference_area": "Romania",
        "reference_sector": "Deposit-taking corporations except the central bank (S.122)",
        "balance_sheet_item": "Lending for house purchase excluding revolving loans and overdrafts, convenience and extended credit card debt",
        "initial_rate_fixation": "Total",
        "rate_type": "Annualised agreed rate (AAR) / Narrowly defined effective rate (NDER)",
        "amount_category": "Total",
        "counterpart_sector": "Households and non-profit institutions serving households (S.14 and S.15)",
        "currency": "Romanian leu",
        "business_coverage": "New business",
        "unit": "Percent per annum",
    }
    if semantics != expected_semantics:
        errors.append("prospective monetary MIR semantic identity changed")
    for key in (
        "response_value_inspection_authorized_now",
        "alternate_MIR_series_substitution_authorized",
        "APRC_series_substitution_authorized",
        "pure_new_loans_series_substitution_authorized",
    ):
        if response[key] is not False:
            errors.append(f"unsafe prospective response rule enabled: {key}")

    schedule = {
        item["reference_period"]: item["release_date"]
        for item in contract["current_schedule_evidence"]["ECB_MIR_release_calendar"]["scheduled_releases"]
    }
    if schedule.get("2026-10") != "2026-12-02":
        errors.append("frozen contract October MIR release date changed")

    trigger = next((x for x in horizon["horizons"] if x["id"] == "prospective_monetary_policy_event"), None)
    if trigger is None:
        errors.append("monitoring horizon lost prospective monetary trigger")
    else:
        if trigger["next_check_date"] != "2026-10-08":
            errors.append("monitoring horizon next BNR check changed")
        if trigger["downstream_release_gate"]["earliest_official_MIR_release_date"] != "2026-12-02":
            errors.append("monitoring horizon October MIR release gate changed")

    protocol = a["event_day_protocol"]
    if protocol["no_refit_or_respecification"] is not True:
        errors.append("event-day protocol no longer freezes model specification")
    if protocol["no_NFC_holdout_opening"] is not True:
        errors.append("event-day protocol unexpectedly permits NFC holdout")
    if protocol["no_behavioural_activation"] is not True:
        errors.append("event-day protocol unexpectedly permits behavioural activation")

    disposition = a["disposition"]
    if disposition["source_access_ready"] is not True:
        errors.append("prospective monetary source access is no longer ready")
    for key in (
        "policy_event_trigger_satisfied",
        "response_release_gate_open",
        "source_materialisation_task_active",
        "parameter_estimation_authorized",
        "calibration_or_refit_authorized",
        "holdout_opening_authorized",
        "feedback_activation_authorized",
        "behavioural_closure_authorized",
        "model_effect",
    ):
        if disposition[key] is not False:
            errors.append(f"source-access readiness unexpectedly authorizes {key}")

    cv = model["calibration_validation"]
    if cv.get("prospective_monetary_source_access_readiness") != ASSESSMENT_PATH:
        errors.append("model contract does not register monetary source-access readiness")
    if baseline["authority"].get("prospective_monetary_source_access_readiness") != ASSESSMENT_PATH:
        errors.append("scientific baseline does not register monetary source-access readiness")

    return errors


def main() -> None:
    errors = audit_prospective_monetary_source_access_readiness()
    if errors:
        raise RuntimeError(
            "Prospective monetary source-access readiness audit failed:\n- "
            + "\n- ".join(errors)
        )
    a = load(ASSESSMENT_PATH)
    print(json.dumps({
        "status": "PASS",
        "decision": a["decision"],
        "next_policy_meeting": a["current_gate_state"]["next_scheduled_policy_meeting"],
        "official_BNR_decision_surface_ready": True,
        "MIR_series": a["authoritative_response_access"]["exact_series_key"],
        "october_MIR_release": a["authoritative_response_access"]["october_2026_reference_period_release_date"],
        "event_trigger_satisfied": False,
        "response_values_inspected": False,
    }, indent=2))


if __name__ == "__main__":
    main()
