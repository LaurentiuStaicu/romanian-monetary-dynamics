from __future__ import annotations

import json
from pathlib import Path

try:
    from scripts.generate_government_f3_holder_diagnostic import build
except ModuleNotFoundError:
    from generate_government_f3_holder_diagnostic import build

ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    replay = json.loads(
        (ROOT / "model/dynamics/f3_empirical_replay_2025.json").read_text(
            encoding="utf-8"
        )
    )
    artifact_path = ROOT / "model/dynamics/government_f3_holder_diagnostic_2025.json"
    artifact = json.loads(artifact_path.read_text(encoding="utf-8"))
    regenerated = build(replay)
    contract = json.loads(
        (ROOT / "model/dynamics/government_f3_holder_diagnostic_contract.json").read_text(
            encoding="utf-8"
        )
    )
    boundary = json.loads(
        (ROOT / "model/dynamics/feedback_variable_boundary_registry.json").read_text(
            encoding="utf-8"
        )
    )
    errors = []
    if artifact != regenerated:
        errors.append("government F3 holder diagnostic differs from deterministic regeneration")
    if artifact["current_summary"]["all_transition_decomposition_residuals_zero"] is not True:
        errors.append("government F3 transition decompositions do not close")
    for key in (
        "net_incurrence_is_gross_issuance",
        "net_incurrence_is_refinancing_need",
        "holder_composition_is_supply_pressure",
        "feedback_activation_authorized",
    ):
        if artifact["current_summary"][key] is not False:
            errors.append(f"forbidden diagnostic promotion: {key}")
    if contract["feedback_activation_authorized"] is not False:
        errors.append("contract may not authorize feedback activation")
    by_id = {item["id"]: item for item in boundary["variables"]}
    for node in (
        "government_debt_issuance",
        "government_debt_stock",
        "government_securities_supply_pressure",
    ):
        if by_id[node]["current_boundary_class"] != "UNRESOLVED":
            errors.append(f"{node}: F3 diagnostic may not resolve feedback boundary")
        if by_id[node]["current_feedback_activation_authorized"] is not False:
            errors.append(f"{node}: F3 diagnostic may not authorize feedback")
    if errors:
        raise RuntimeError("Government F3 holder diagnostic audit failed:\n- " + "\n- ".join(errors))
    print(json.dumps({
        "status": "PASS",
        "issuer": "G",
        "instrument": "F3",
        "feedback_boundary_resolution": "UNCHANGED_UNRESOLVED",
        "feedback_activation_authorized": False,
    }, indent=2))


if __name__ == "__main__":
    main()
