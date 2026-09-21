from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT = ROOT / "model/accounting/f4_eurostat_bsi_bridge_diagnostic_2026_09_21.json"


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def audit_f4_eurostat_bsi_bridge_diagnostic() -> list[str]:
    errors: list[str] = []
    a = json.loads(ASSESSMENT.read_text(encoding="utf-8"))
    eurostat = load("model/dynamics/sectoral_financial_positions_eurostat_counterpart_discovery_assessment.json")
    bsi = load("model/dynamics/private_credit_reference_snapshot.json")
    f4 = load("model/accounting/f4_exact_complement_rank_assessment.json")
    reopen = load("model/accounting/reopen_conditions_registry.json")

    if a["decision"] != "NO_REOPEN_BSI_FINANCIAL_ACCOUNTS_CONCEPT_BRIDGE_NOT_EXACT":
        errors.append("F4 bridge diagnostic decision changed")
    if a["formal_materialization_gate"] is not False:
        errors.append("diagnostic may not be a materialization gate")

    if eurostat["discovery_result"]["artifact_id"] != a["source_lineage"]["eurostat"]["retained_workflow_artifact_id"]:
        errors.append("Eurostat retained artifact lineage changed")
    if eurostat["discovery_result"]["raw_response_sha256"] != a["source_lineage"]["eurostat"]["retained_raw_sha256"]:
        errors.append("Eurostat retained raw hash changed")
    if bsi["provenance"]["workflow_artifact_id"] != a["source_lineage"]["ecb_bsi"]["retained_workflow_artifact_id"]:
        errors.append("BSI retained artifact lineage changed")

    bench = bsi["benchmark_2025"]
    nfc_stock = Decimal(str(bench["nfc_stock"][-1]))
    hh_stock = Decimal(str(bench["households_npish_stock"][-1]))
    nfc_flow = sum(Decimal(str(x)) for x in bench["nfc_flow"])
    hh_flow = sum(Decimal(str(x)) for x in bench["households_npish_flow"])

    cases = a["tested_bridge"]["cases"]
    recomputed = {
        "nfc_stock_2025_q4": (Decimal(cases["nfc_stock_2025_q4"]["eurostat_mfi_f4_mio_eur"]), nfc_stock),
        "households_npish_stock_2025_q4": (Decimal(cases["households_npish_stock_2025_q4"]["eurostat_mfi_f4_mio_eur"]), hh_stock),
        "nfc_transactions_2025": (Decimal(cases["nfc_transactions_2025"]["eurostat_mfi_f4_mio_eur"]), nfc_flow),
        "households_npish_transactions_2025": (Decimal(cases["households_npish_transactions_2025"]["eurostat_mfi_f4_mio_eur"]), hh_flow),
    }
    bsi_fields = {
        "nfc_stock_2025_q4": "bsi_mfis_ex_ncb_loans_mio_eur",
        "households_npish_stock_2025_q4": "bsi_mfis_ex_ncb_loans_mio_eur",
        "nfc_transactions_2025": "bsi_mfis_ex_ncb_financial_transactions_mio_eur",
        "households_npish_transactions_2025": "bsi_mfis_ex_ncb_financial_transactions_mio_eur",
    }
    for key, (fa_value, bsi_value) in recomputed.items():
        recorded_bsi = Decimal(cases[key][bsi_fields[key]])
        recorded_residual = Decimal(cases[key]["residual_mio_eur"])
        if bsi_value != recorded_bsi:
            errors.append(f"{key}: retained BSI value changed")
        if fa_value - bsi_value != recorded_residual:
            errors.append(f"{key}: bridge residual is not reproducible")
        if recorded_residual == 0:
            errors.append(f"{key}: diagnostic unexpectedly became an exact identity")

    if a["methodological_adjudication"]["exact_concept_bridge_validated"] is not False:
        errors.append("cross-domain exact bridge may not be treated as validated")
    for key in (
        "new_rank_equations_authorized",
        "bnr_counterpart_allocation_authorized",
        "f4_reopen_trigger_satisfied",
        "f4_materialization_change",
        "canonical_benchmark_change",
        "complete_f4_matrix",
    ):
        if a["accounting_effect"][key] is not False:
            errors.append(f"diagnostic may not authorize {key}")

    if f4["unconditional_identification"]["stock"]["unique_cell_count"] != 15:
        errors.append("F4 unconditional stock uniqueness changed")
    if f4["unconditional_identification"]["flow"]["unique_cell_count"] != 15:
        errors.append("F4 unconditional flow uniqueness changed")

    f4_reopen = reopen["instruments"]["F4"]
    if f4_reopen.get("bridge_diagnostic") != "model/accounting/f4_eurostat_bsi_bridge_diagnostic_2026_09_21.json":
        errors.append("F4 reopen registry does not register bridge diagnostic")
    expected_phrase = "subtracting ECB BSI MFIs-excluding-NCB loan series"
    if not any(expected_phrase in item for item in f4_reopen["evidence_that_does_not_reopen"]):
        errors.append("F4 reopen registry does not block the rejected BSI subtraction shortcut")

    return errors


def main() -> None:
    errors = audit_f4_eurostat_bsi_bridge_diagnostic()
    if errors:
        raise RuntimeError("F4 Eurostat-BSI bridge diagnostic audit failed:\n- " + "\n- ".join(errors))
    print(json.dumps({
        "status": "PASS",
        "decision": "NO_REOPEN_BSI_FINANCIAL_ACCOUNTS_CONCEPT_BRIDGE_NOT_EXACT",
        "f4_unconditional_unique_stock_cells": 15,
        "f4_unconditional_unique_flow_cells": 15,
        "f4_reopen_trigger_satisfied": False,
        "canonical_benchmark_changed": False,
    }, indent=2))


if __name__ == "__main__":
    main()
