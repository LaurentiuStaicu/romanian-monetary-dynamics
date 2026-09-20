from __future__ import annotations

import json
from pathlib import Path

from romania_macro_financial_dynamics.dynamics import (
    advance_empirical_replay_position,
)
try:
    from scripts.generate_f3_empirical_replay import (
        AUDIT,
        BENCHMARK,
        MANIFEST,
        build_artifact,
        load,
    )
except ModuleNotFoundError:
    from generate_f3_empirical_replay import (
        AUDIT,
        BENCHMARK,
        MANIFEST,
        build_artifact,
        load,
    )

ROOT = Path(__file__).resolve().parents[1]
ARTIFACT = ROOT / "model" / "dynamics" / "f3_empirical_replay_2025.json"
CONTRACT = ROOT / "model" / "dynamics" / "f3_empirical_replay_contract.json"


def audit_f3_empirical_replay(
    artifact: dict,
    contract: dict,
    regenerated: dict,
) -> list[str]:
    errors: list[str] = []

    if artifact != regenerated:
        errors.append(
            "committed F3 replay artifact differs from deterministic regeneration"
        )

    if artifact.get("instrument") != "F3":
        errors.append("F3 replay artifact changed instrument scope")
    if contract.get("instrument") != "F3":
        errors.append("F3 replay contract changed instrument scope")
    if contract.get("scientific_status") != (
        "PARTIAL_INSTRUMENT_SPECIFIC_EMPIRICAL_REPLAY"
    ):
        errors.append("F3 replay scientific status is stale")

    summary = artifact.get("summary", {})
    if summary.get("replayed_transitions") != 3:
        errors.append("F3 replay must contain exactly Q2-Q4 transitions")
    if summary.get("numeric_replayed_cell_transitions") != 105:
        errors.append("F3 replay numeric transition count is stale")
    if summary.get("max_abs_identity_residual_million_RON") != 0.0:
        errors.append("F3 replay stock identity residual is non-zero")
    if (
        summary.get(
            "max_abs_q4_stock_vs_canonical_benchmark_residual_million_RON"
        )
        != 0.0
    ):
        errors.append("F3 Q4 stock no longer reproduces the canonical benchmark")
    if (
        summary.get(
            "max_abs_annual_transaction_sum_vs_canonical_benchmark_residual_million_RON"
        )
        != 0.0
    ):
        errors.append(
            "F3 quarterly transactions no longer reproduce the annual benchmark"
        )
    if summary.get("q1_transition_replayed") is not False:
        errors.append("Q1 may not be replayed without retained 2024-Q4 opening stock")
    if summary.get("full_RMD_empirical_state_claim_allowed") is not False:
        errors.append("F3-only replay may not claim full-RMD empirical readiness")
    if summary.get("behavioural_closure_active") is not False:
        errors.append("F3 replay may not activate behavioural closure")
    if summary.get("feedback_activation_authorized") is not False:
        errors.append("F3 replay may not authorize feedback activation")

    if any(
        value != 0.0
        for value in summary.get(
            "system_net_financial_worth_residual_million_RON_by_quarter", {}
        ).values()
    ):
        errors.append("F3 replay violates double-entry system conservation")

    nonzero_nontransaction = 0
    for transition in artifact.get("transitions", []):
        for cell in transition.get("cells", []):
            if cell.get("status") == "NOT_APPLICABLE":
                continue
            opening = float(cell["opening_stock_million_RON"])
            transaction = float(cell["transaction_million_RON"])
            other = float(cell["combined_nontransaction_change_million_RON"])
            closing = float(cell["closing_stock_million_RON"])
            replayed = advance_empirical_replay_position(
                opening,
                transaction=transaction,
                combined_nontransaction_change=other,
            )
            if round(replayed, 2) != closing:
                errors.append(
                    f"{transition['period']} {cell['holder']}->{cell['issuer']}: "
                    "runtime replay does not close to observed stock"
                )
            if other != 0.0:
                nonzero_nontransaction += 1

    if nonzero_nontransaction == 0:
        errors.append(
            "F3 replay unexpectedly has no non-transaction changes; "
            "transaction-only interpretation may have leaked in"
        )

    hard_rules = contract.get("hard_rules", {})
    for key in (
        "instrument_scope_is_F3_only",
        "no_missing_value_imputation",
        "combined_nontransaction_change_must_not_be_relabelled_as_revaluation",
        "combined_nontransaction_change_must_not_be_relabelled_as_other_volume_change",
        "replay_is_accounting_identity_not_behavioural_equation",
        "replay_does_not_validate_or_activate_feedback",
        "replay_must_not_be_described_as_full_RMD",
    ):
        if hard_rules.get(key) is not True:
            errors.append(f"F3 replay hard rule {key} must remain true")

    return errors


def main() -> None:
    artifact = json.loads(ARTIFACT.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT.read_text(encoding="utf-8"))
    regenerated = build_artifact(load(AUDIT), load(MANIFEST), load(BENCHMARK))
    errors = audit_f3_empirical_replay(artifact, contract, regenerated)
    if errors:
        raise RuntimeError(
            "F3 empirical replay audit failed:\n- " + "\n- ".join(errors)
        )
    print(
        json.dumps(
            {
                "status": "PASS",
                "instrument": "F3",
                "replayed_transitions": 3,
                "numeric_replayed_cell_transitions": 105,
                "max_abs_identity_residual_million_RON": 0.0,
                "full_RMD_empirical_state_claim_allowed": False,
                "behavioural_closure_active": False,
                "feedback_activation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
