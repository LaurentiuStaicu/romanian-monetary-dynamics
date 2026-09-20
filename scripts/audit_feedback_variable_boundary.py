from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_PATH = ROOT / "model" / "dynamics" / "feedback_registry.json"
BOUNDARY_PATH = ROOT / "model" / "dynamics" / "feedback_variable_boundary_registry.json"
REFERENCE_PATH = ROOT / "model" / "dynamics" / "reference_modes.json"
MECHANISM_PATH = ROOT / "model" / "empirical_dynamics" / "mechanism_registry.json"
MODEL_PATH = ROOT / "model" / "registries" / "model_contract.json"


def feedback_nodes(feedback: dict[str, object]) -> set[str]:
    nodes: set[str] = set()
    for structure in feedback["loops"]:
        for link in structure["path"]:
            nodes.add(str(link["from"]))
            nodes.add(str(link["to"]))
    return nodes


def audit_feedback_variable_boundary(
    feedback: dict[str, object],
    boundary: dict[str, object],
    references: dict[str, object],
    mechanisms: dict[str, object],
    model: dict[str, object],
) -> list[str]:
    errors: list[str] = []

    expected_nodes = feedback_nodes(feedback)
    entries = boundary.get("variables", [])
    ids = [str(item["id"]) for item in entries]
    observed_nodes = set(ids)

    if len(ids) != len(observed_nodes):
        errors.append("boundary registry contains duplicate variable IDs")

    if observed_nodes != expected_nodes:
        errors.append(
            "feedback-node coverage mismatch; "
            f"missing={sorted(expected_nodes - observed_nodes)}, "
            f"extra={sorted(observed_nodes - expected_nodes)}"
        )

    allowed = set(boundary.get("allowed_current_boundary_classes", []))
    required_allowed = {
        "ENDOGENOUS",
        "EXOGENOUS",
        "OBSERVED_FORCING",
        "POLICY_INPUT",
        "UNRESOLVED",
    }
    if allowed != required_allowed:
        errors.append(
            "boundary-class vocabulary differs from the frozen gate vocabulary"
        )

    by_ref = {
        str(item["id"]): item
        for item in references.get("reference_modes", [])
    }
    by_mechanism = {
        str(item["id"]): item
        for item in mechanisms.get("mechanisms", [])
    }

    closure_active = bool(
        model["dynamic_core"]["behavioural_closure_active"]
    )
    active_structures = [
        str(item["id"])
        for item in feedback["loops"]
        if item.get("quantitatively_active") is True
    ]

    if closure_active:
        errors.append(
            "current boundary registry is frozen for inactive behavioural closure"
        )
    if active_structures:
        errors.append(
            "current boundary registry assumes zero quantitatively active feedback "
            f"structures, observed={active_structures}"
        )

    for item in entries:
        variable_id = str(item["id"])
        classification = str(item.get("current_boundary_class", ""))
        if classification not in allowed:
            errors.append(
                f"{variable_id}: unsupported boundary class {classification!r}"
            )

        if item.get("current_feedback_activation_authorized") is not False:
            errors.append(
                f"{variable_id}: current feedback activation must remain unauthorized"
            )

        if not str(item.get("classification_basis", "")).strip():
            errors.append(
                f"{variable_id}: missing substantive classification basis"
            )

        if not closure_active and classification == "ENDOGENOUS":
            errors.append(
                f"{variable_id}: current ENDOGENOUS classification is prohibited "
                "while behavioural closure is inactive"
            )

        exact_ref = item.get("exact_reference_mode_id")
        related = set(item.get("related_reference_modes", []))
        if exact_ref is not None:
            exact_ref = str(exact_ref)
            if exact_ref not in by_ref:
                errors.append(
                    f"{variable_id}: unknown exact reference mode {exact_ref}"
                )
            elif exact_ref not in related:
                errors.append(
                    f"{variable_id}: exact reference mode must also appear in "
                    "related_reference_modes"
                )

        unknown_related = related - set(by_ref)
        if unknown_related:
            errors.append(
                f"{variable_id}: unknown related reference modes "
                f"{sorted(unknown_related)}"
            )

        if classification == "OBSERVED_FORCING":
            if exact_ref is None:
                errors.append(
                    f"{variable_id}: OBSERVED_FORCING requires an exact reference mode"
                )
            elif exact_ref in by_ref:
                endogeneity = str(
                    by_ref[exact_ref].get("current_endogeneity", "")
                )
                if endogeneity != "EXOGENOUS_OBSERVED_INPUT":
                    errors.append(
                        f"{variable_id}: OBSERVED_FORCING reference mode has "
                        f"current_endogeneity={endogeneity!r}"
                    )

        if classification == "UNRESOLVED":
            if item.get("future_candidate_role") != (
                "ENDOGENOUS_CANDIDATE_IF_ALL_ACTIVATION_GATES_PASS"
            ):
                errors.append(
                    f"{variable_id}: unresolved node must preserve conditional "
                    "future-candidate semantics"
                )

    by_id = {str(item["id"]): item for item in entries}

    policy = by_id.get("policy_rate")
    if policy is None:
        errors.append("policy_rate boundary entry is missing")
    else:
        if policy.get("current_boundary_class") != "OBSERVED_FORCING":
            errors.append(
                "policy_rate must remain OBSERVED_FORCING while the monetary "
                "reaction function is deferred"
            )
        monetary_rule = by_mechanism.get("monetary_policy_reaction_function")
        if monetary_rule is None:
            errors.append("monetary_policy_reaction_function mechanism is missing")
        elif monetary_rule.get("classification") != "DEFERRED":
            errors.append(
                "policy_rate forcing assumption requires the monetary-policy "
                "reaction function to remain DEFERRED"
            )

    # Exact observed targets do not become forcing merely because data exist.
    for variable_id in ("credit_flow", "government_debt_stock"):
        item = by_id.get(variable_id)
        if item is not None and item.get("current_boundary_class") != "UNRESOLVED":
            errors.append(
                f"{variable_id}: observed target availability must not silently "
                "resolve the integrated feedback boundary"
            )

    open_structures = [
        item for item in feedback["loops"]
        if item.get("topology_status") == "OPEN_CHAIN"
    ]
    for structure in open_structures:
        terminal = str(structure["path"][-1]["to"])
        terminal_entry = by_id.get(terminal)
        if terminal_entry is None:
            continue
        if terminal_entry.get("current_boundary_class") == "ENDOGENOUS":
            errors.append(
                f"{terminal}: open-chain terminus may not be made endogenous "
                "to imply closure"
            )
        if "closing_link" in terminal_entry:
            errors.append(
                f"{terminal}: boundary registry may not invent an open-chain closing link"
            )

    state = boundary.get("current_state", {})
    if state.get("behavioural_closure_active") is not False:
        errors.append(
            "boundary current_state must record inactive behavioural closure"
        )
    if state.get("quantitatively_active_feedback_loops") != 0:
        errors.append(
            "boundary current_state must record zero active feedback loops"
        )
    if state.get("endogenous_closure_readiness") != "BLOCKED":
        errors.append(
            "endogenous closure readiness must remain BLOCKED"
        )

    return errors


def main() -> None:
    feedback = json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
    boundary = json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))
    references = json.loads(REFERENCE_PATH.read_text(encoding="utf-8"))
    mechanisms = json.loads(MECHANISM_PATH.read_text(encoding="utf-8"))
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))

    errors = audit_feedback_variable_boundary(
        feedback,
        boundary,
        references,
        mechanisms,
        model,
    )
    if errors:
        raise RuntimeError(
            "Feedback variable boundary audit failed:\n- "
            + "\n- ".join(errors)
        )

    print(
        json.dumps(
            {
                "status": "PASS",
                "registry": str(BOUNDARY_PATH.relative_to(ROOT)),
                "feedback_nodes_checked": len(feedback_nodes(feedback)),
                "current_observed_forcing": [
                    item["id"]
                    for item in boundary["variables"]
                    if item["current_boundary_class"] == "OBSERVED_FORCING"
                ],
                "current_endogenous_nodes": [],
                "endogenous_closure_readiness": "BLOCKED",
                "activation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
