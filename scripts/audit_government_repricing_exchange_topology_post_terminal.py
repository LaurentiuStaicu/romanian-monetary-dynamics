from __future__ import annotations

import csv
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT_PATH = "model/calibration_validation/government_repricing_exchange_topology_post_terminal_assessment_2026_09_22.json"
PREDECESSOR_PATH = "model/calibration_validation/government_repricing_ledger_assessment.json"
CONTRACT_PATH = "model/calibration_validation/government_repricing_ledger_contract.json"
LEDGER_PATH = "data/processed/government_repricing_ledger.csv"
EXPECTED_DECISION = "NO_REOPEN_EXCHANGE_TOPOLOGY_ONLY_REALIZED_MATCHED_LEDGER_FIELDS_UNRESOLVED"


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


def audit_government_repricing_exchange_topology_post_terminal() -> list[str]:
    errors: list[str] = []
    a = load(ASSESSMENT_PATH)
    predecessor = load(PREDECESSOR_PATH)
    contract = load(CONTRACT_PATH)
    model = load("model/registries/model_contract.json")
    baseline = load("model/registries/scientific_baseline_manifest.json")
    horizon = load("model/registries/trigger_aware_monitoring_horizon_2026_09_22_post_f4_structural.json")

    if a["decision"] != EXPECTED_DECISION:
        errors.append("exchange-topology post-terminal decision changed")
    if a["predecessor_ledger_assessment"] != PREDECESSOR_PATH:
        errors.append("government repricing predecessor assessment pointer changed")
    if a["contract"] != CONTRACT_PATH:
        errors.append("government repricing contract pointer changed")

    old_to_new = a["new_official_evidence"]["may_2025_exchange_prospect"]["old_to_new_topology"]
    expected = {
        "2025-05-21": ({"RODD24CXRK47", "ROJ0LNOCKHR8"}, "ROXL7LT7QZ66"),
        "2025-05-28": ({"RO7EKTXSRHD6", "ROHRVN7NLNO2"}, "RODFIUK7ZV55"),
    }
    if len(old_to_new) != 2:
        errors.append("May 2025 exchange topology cardinality changed")
    for item in old_to_new:
        date = item["operation_date"]
        if date not in expected:
            errors.append(f"unexpected exchange-operation date: {date}")
            continue
        old_expected, new_expected = expected[date]
        if {x["isin"] for x in item["old_isins"]} != old_expected:
            errors.append(f"old-side exchange ISINs changed for {date}")
        if item["new_isin"]["isin"] != new_expected:
            errors.append(f"new-side exchange ISIN changed for {date}")

    discovery = a["source_discovery_result"]
    if discovery["topology_old_to_new_observed"] is not True:
        errors.append("official exchange topology no longer marked observed")
    if discovery["official_result_publication_obligation_observed"] is not True:
        errors.append("official result-publication rule no longer preserved")
    for key in (
        "official_realized_exchange_result_identified_reproducibly",
        "official_realized_accepted_old_principal_by_isin_identified",
        "official_realized_new_principal_identified",
        "same_date_opening_outstanding_principal_by_old_isin_identified",
        "matched_old_effective_rate_identified",
        "matched_new_or_reset_effective_rate_identified",
    ):
        if discovery[key] is not False:
            errors.append(f"unresolved exchange field incorrectly promoted: {key}")

    adjudication = a["contract_adjudication"]
    if adjudication["exchange_prospect_satisfies_matched_event_topology_only"] is not True:
        errors.append("exchange prospect topology-only classification changed")
    for key in (
        "exchange_prospect_satisfies_gate_1_ledger_completeness",
        "price_announcement_satisfies_realized_principal",
        "coupon_is_effective_rate",
        "indicative_new_nominal_is_realized_principal",
        "secondary_reported_nominal_or_yield_may_enter_ledger",
    ):
        if adjudication[key] is not False:
            errors.append(f"prohibited exchange inference enabled: {key}")
    if adjudication["gate_1_status"] != "FAIL_UNCHANGED":
        errors.append("government repricing Gate 1 unexpectedly changed")
    if adjudication["gate_4_status"] != "FAIL_BEFORE_ESTIMATION":
        errors.append("government repricing identification gate unexpectedly changed")
    if adjudication["candidate_eligibility"] is not False or adjudication["validated_eligibility"] is not False:
        errors.append("exchange topology may not create mechanism eligibility")

    if predecessor["gate_results"]["gate_1_ledger_completeness"]["status"] != "FAIL":
        errors.append("predecessor ledger Gate 1 no longer FAIL")
    if predecessor["gate_results"]["gate_4_parameter_identification"]["status"] != "FAIL_BEFORE_ESTIMATION":
        errors.append("predecessor identification gate changed")
    if predecessor["candidate_eligibility"] is not False:
        errors.append("predecessor government mechanism became candidate unexpectedly")

    with (ROOT / LEDGER_PATH).open(newline="", encoding="utf-8") as fh:
        rows = list(csv.DictReader(fh))
    if any((row.get("opening_outstanding_principal") or "").strip() for row in rows):
        errors.append("canonical repricing ledger now contains opening principal without a reviewed successor")
    if any((row.get("principal_repriced") or "").strip() for row in rows):
        errors.append("canonical repricing ledger now contains realized repriced principal without a reviewed successor")
    if any((row.get("old_effective_rate_pct") or "").strip() for row in rows):
        errors.append("canonical repricing ledger now contains old effective rates without a reviewed successor")
    if any((row.get("new_or_marginal_rate_pct") or "").strip() for row in rows):
        errors.append("canonical repricing ledger now contains new/marginal rates without a reviewed successor")

    required_fields = set(contract["ledger_schema"]["required_fields"])
    for name in (
        "opening_outstanding_principal",
        "principal_repriced",
        "old_effective_rate",
        "new_or_reset_effective_rate",
    ):
        if name not in required_fields:
            errors.append(f"government repricing contract dropped required matched field: {name}")

    cv = model["calibration_validation"]
    if cv.get("government_repricing_ledger_assessment") != PREDECESSOR_PATH:
        errors.append("model contract predecessor repricing assessment pointer changed")
    if cv.get("government_repricing_latest_exchange_topology_review") != ASSESSMENT_PATH:
        errors.append("model contract does not register latest exchange-topology review")
    if cv.get("government_repricing_latest_exchange_topology_status") != a["current_disposition"]["status"]:
        errors.append("model contract exchange-topology status is stale")

    authority = baseline["authority"]
    if authority.get("government_repricing_exchange_topology_post_terminal_assessment") != ASSESSMENT_PATH:
        errors.append("scientific baseline does not register exchange-topology post-terminal assessment")

    trigger = next((x for x in horizon["horizons"] if x["id"] == "government_repricing_ledger"), None)
    if trigger is None:
        errors.append("monitoring horizon dropped government repricing trigger")
    else:
        if trigger["next_check_type"] != "NEW_OFFICIAL_EVIDENCE_ONLY":
            errors.append("government repricing trigger check type changed")
        required_phrase = "realised repriced/refinanced principal"
        if required_phrase not in trigger["trigger"]:
            errors.append("government repricing trigger no longer requires realized principal")

    disposition = a["current_disposition"]
    if disposition["status"] != "NEW_OFFICIAL_EXCHANGE_TOPOLOGY_RESULT_UNRESOLVED_NO_REOPEN":
        errors.append("exchange-topology disposition changed")
    for key in (
        "canonical_government_repricing_ledger_mutation_authorized",
        "source_materialisation_task_active",
        "parameter_estimation_authorized",
        "calibration_or_refit_authorized",
        "holdout_opening_authorized",
        "government_refinancing_interest_feedback_activation_authorized",
        "behavioural_closure_authorized",
        "model_effect",
    ):
        if disposition[key] is not False:
            errors.append(f"exchange topology unexpectedly authorizes {key}")

    rule = a["next_reopen_trigger"]
    for key in (
        "repeated_prospect_search_is_progress",
        "infer_realized_principal_from_outstanding_stock_changes",
        "infer_old_effective_rate_from_coupon_or_price_alone",
        "infer_new_effective_rate_from_coupon_alone",
        "use_secondary_locator_values_as_canonical",
    ):
        if rule[key] is not False:
            errors.append(f"unsafe government repricing source rule enabled: {key}")

    return errors


def main() -> None:
    errors = audit_government_repricing_exchange_topology_post_terminal()
    if errors:
        raise RuntimeError("Government repricing exchange-topology audit failed:\n- " + "\n- ".join(errors))
    a = load(ASSESSMENT_PATH)
    print(json.dumps({
        "status": "PASS",
        "decision": a["decision"],
        "matched_exchange_topology_observed": True,
        "realized_result_identified": False,
        "gate_1": a["contract_adjudication"]["gate_1_status"],
        "candidate_eligibility": False,
        "model_effect": False,
    }, indent=2))


if __name__ == "__main__":
    main()
