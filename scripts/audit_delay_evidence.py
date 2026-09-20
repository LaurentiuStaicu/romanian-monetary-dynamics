from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEEDBACK = ROOT / "model" / "dynamics" / "feedback_registry.json"
DELAY = ROOT / "model" / "dynamics" / "delay_evidence_registry.json"


def audit_delay_evidence(feedback: dict[str, object], delay: dict[str, object]) -> list[str]:
    errors: list[str] = []
    fb = {str(x["id"]): x for x in feedback["delay_candidates"]}
    reg = {str(x["id"]): x for x in delay["delays"]}
    if set(fb) != set(reg):
        errors.append(
            f"delay coverage mismatch; missing={sorted(set(fb)-set(reg))}, "
            f"extra={sorted(set(reg)-set(fb))}"
        )
    vocab = set(delay["status_vocabulary"])
    sources = set(delay["evidence_sources"])
    for delay_id, item in reg.items():
        if delay_id not in fb:
            continue
        current = fb[delay_id]
        if item["current_tau"] != current["tau"]:
            errors.append(f"{delay_id}: current_tau disagrees with feedback registry")
        if item["unit"] != current["unit"]:
            errors.append(f"{delay_id}: unit disagrees with feedback registry")
        if item["active"] is not current["active"]:
            errors.append(f"{delay_id}: active state disagrees with feedback registry")
        if item["evidence_status"] not in vocab:
            errors.append(f"{delay_id}: unsupported evidence status")
        unknown = set(item.get("evidence_sources", [])) - sources
        if unknown:
            errors.append(f"{delay_id}: unknown evidence sources {sorted(unknown)}")
        if not str(item.get("reason", "")).strip():
            errors.append(f"{delay_id}: missing reason")
        if not str(item.get("next_admissible_step", "")).strip():
            errors.append(f"{delay_id}: missing next admissible step")
        if item["scalar_tau_activation_ready"] is True:
            if item["evidence_status"] != "SCALAR_TAU_IDENTIFIED_AND_VALIDATED":
                errors.append(f"{delay_id}: tau ready without validated scalar evidence")
            if not isinstance(item["current_tau"], (int, float)) or item["current_tau"] <= 0:
                errors.append(f"{delay_id}: tau ready without positive numeric tau")
        else:
            if item["current_tau"] != "TBD":
                errors.append(f"{delay_id}: blocked scalar tau must remain TBD")
            if item["active"] is not False:
                errors.append(f"{delay_id}: blocked delay must remain inactive")

    summary = delay["current_summary"]
    if summary["registered_delay_candidates"] != len(fb):
        errors.append("summary registered-delay count is stale")
    ready = sum(x["scalar_tau_activation_ready"] is True for x in reg.values())
    validated = sum(x["evidence_status"] == "SCALAR_TAU_IDENTIFIED_AND_VALIDATED" for x in reg.values())
    active = sum(x["active"] is True for x in reg.values())
    if summary["scalar_tau_activation_ready"] != ready:
        errors.append("summary ready count is stale")
    if summary["scalar_tau_identified_and_validated"] != validated:
        errors.append("summary validated count is stale")
    if summary["active_delay_candidates"] != active:
        errors.append("summary active count is stale")
    if ready == 0 and summary["current_status"] != "ALL_SCALAR_TAU_PARAMETERS_BLOCKED":
        errors.append("summary must report all scalar tau parameters blocked")
    if summary["activation_authorized"] is not False:
        errors.append("delay evidence registry may not authorize activation")
    return errors


def main() -> None:
    feedback = json.loads(FEEDBACK.read_text(encoding="utf-8"))
    delay = json.loads(DELAY.read_text(encoding="utf-8"))
    errors = audit_delay_evidence(feedback, delay)
    if errors:
        raise RuntimeError("Delay evidence audit failed:\n- " + "\n- ".join(errors))
    print(json.dumps({
        "status": "PASS",
        "registered_delay_candidates": len(delay["delays"]),
        "scalar_tau_activation_ready": 0,
        "current_status": delay["current_summary"]["current_status"],
        "activation_authorized": False,
    }, indent=2))


if __name__ == "__main__":
    main()
