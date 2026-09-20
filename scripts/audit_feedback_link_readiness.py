from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FEEDBACK_PATH = ROOT / "model" / "dynamics" / "feedback_registry.json"
LINK_PATH = ROOT / "model" / "dynamics" / "feedback_link_readiness_registry.json"
BOUNDARY_PATH = ROOT / "model" / "dynamics" / "feedback_variable_boundary_registry.json"
MECHANISM_PATH = ROOT / "model" / "empirical_dynamics" / "mechanism_registry.json"


def canonical_link_key(loop_id: str, source: str, target: str) -> str:
    return f"{loop_id}|{source}|{target}"


def feedback_link_keys(feedback: dict[str, object]) -> set[str]:
    return {
        canonical_link_key(str(loop["id"]), str(link["from"]), str(link["to"]))
        for loop in feedback["loops"]
        for link in loop["path"]
    }


def compute_loop_readiness(
    feedback: dict[str, object],
    registry: dict[str, object],
    boundary: dict[str, object],
    mechanisms: dict[str, object],
) -> list[dict[str, object]]:
    boundary_by = {str(item["id"]): item for item in boundary["variables"]}
    links_by_loop: dict[str, list[dict[str, object]]] = {}
    for item in registry["links"]:
        links_by_loop.setdefault(str(item["loop_id"]), []).append(item)

    delay_by = {str(item["id"]): item for item in feedback["delay_candidates"]}
    mechanisms_by_loop: dict[str, list[dict[str, str]]] = {}
    for item in mechanisms["mechanisms"]:
        loop_id = item.get("maps_to_dynamic_core_loop")
        if loop_id:
            mechanisms_by_loop.setdefault(str(loop_id), []).append(
                {
                    "id": str(item["id"]),
                    "classification": str(item["classification"]),
                }
            )

    result: list[dict[str, object]] = []
    for loop in feedback["loops"]:
        loop_id = str(loop["id"])
        link_rows = links_by_loop.get(loop_id, [])
        nodes = []
        for link in loop["path"]:
            for node in (str(link["from"]), str(link["to"])):
                if node not in nodes:
                    nodes.append(node)
        unresolved = [
            node
            for node in nodes
            if boundary_by[node]["current_boundary_class"] == "UNRESOLVED"
        ]
        delays = [
            delay_by[str(delay_id)]
            for delay_id in loop.get("delay_candidates", [])
        ]
        mapped = mechanisms_by_loop.get(loop_id, [])
        blockers: list[str] = []
        if any(
            item.get("exact_integrated_equation_ready") is not True
            for item in link_rows
        ):
            blockers.append("EXACT_LINK_EQUATION_COVERAGE_INCOMPLETE")
        if unresolved:
            blockers.append("UNRESOLVED_FEEDBACK_BOUNDARY_NODES")
        if any(
            item.get("tau") == "TBD" or item.get("active") is False
            for item in delays
        ):
            blockers.append("DELAY_SPECIFICATION_NOT_ACTIVATION_READY")
        if not mapped or all(
            item["classification"] != "ACTIVATED" for item in mapped
        ):
            blockers.append("NO_ACTIVATED_EMPIRICAL_MECHANISM")
        if loop.get("topology_status") == "OPEN_CHAIN":
            blockers.append("OPEN_CHAIN_NOT_CLOSED")

        result.append(
            {
                "loop_id": loop_id,
                "topology_status": loop["topology_status"],
                "path_link_count": len(link_rows),
                "exact_integrated_link_forms_ready": sum(
                    item.get("exact_integrated_equation_ready") is True
                    for item in link_rows
                ),
                "unresolved_boundary_nodes": unresolved,
                "delay_candidates": list(loop.get("delay_candidates", [])),
                "mapped_mechanisms": mapped,
                "activation_status": "READY" if not blockers else "BLOCKED",
                "blockers": blockers,
                "quantitative_activation_authorized": False,
            }
        )
    return result


def audit_feedback_link_readiness(
    feedback: dict[str, object],
    registry: dict[str, object],
    boundary: dict[str, object],
    mechanisms: dict[str, object],
) -> list[str]:
    errors: list[str] = []
    expected = feedback_link_keys(feedback)
    rows = registry.get("links", [])
    keys = [str(item["link_key"]) for item in rows]

    if len(keys) != len(set(keys)):
        errors.append("feedback-link registry contains duplicate link keys")
    if set(keys) != expected:
        errors.append(
            "feedback-link coverage mismatch; "
            f"missing={sorted(expected - set(keys))}, "
            f"extra={sorted(set(keys) - expected)}"
        )

    feedback_by_id = {str(item["id"]): item for item in feedback["loops"]}
    mechanism_ids = {str(item["id"]) for item in mechanisms["mechanisms"]}
    mechanism_by_id = {str(item["id"]): item for item in mechanisms["mechanisms"]}
    vocabulary = set(registry["readiness_status_vocabulary"])

    for item in rows:
        key = str(item["link_key"])
        loop_id = str(item["loop_id"])
        loop = feedback_by_id.get(loop_id)
        if loop is None:
            errors.append(f"{key}: unknown feedback loop {loop_id}")
            continue

        matching = [
            link
            for link in loop["path"]
            if str(link["from"]) == str(item["from"])
            and str(link["to"]) == str(item["to"])
        ]
        if len(matching) != 1:
            errors.append(f"{key}: link identity does not match feedback path")
            continue
        if str(item["sign"]) != str(matching[0]["sign"]):
            errors.append(f"{key}: link sign is stale relative to feedback registry")

        status = str(item.get("readiness_status", ""))
        if status not in vocabulary:
            errors.append(f"{key}: unsupported readiness status {status!r}")

        unknown = set(item.get("related_mechanisms", [])) - mechanism_ids
        if unknown:
            errors.append(f"{key}: unknown related mechanisms {sorted(unknown)}")

        target_specific_pointer = item.get("target_specific_implementation_pointer")
        if target_specific_pointer is not None:
            related = [
                mechanism_by_id[mechanism_id]
                for mechanism_id in item.get("related_mechanisms", [])
                if mechanism_id in mechanism_by_id
            ]
            matching_implementations = [
                mechanism
                for mechanism in related
                if mechanism.get("implementation") == target_specific_pointer
            ]
            if len(matching_implementations) != 1:
                errors.append(
                    f"{key}: target-specific implementation pointer does not map "
                    "to exactly one related mechanism"
                )
            if status != "PARTIAL_TARGET_SPECIFIC_FORM_NOT_INTEGRATED":
                errors.append(
                    f"{key}: target-specific implementation requires partial-not-integrated status"
                )
            if item.get("exact_integrated_equation_ready") is not False:
                errors.append(
                    f"{key}: target-specific implementation may not imply exact integrated readiness"
                )
            if not str(item.get("target_specific_scope", "")).strip():
                errors.append(
                    f"{key}: target-specific implementation lacks explicit scope"
                )

        ready = item.get("exact_integrated_equation_ready")
        pointer = item.get("equation_pointer")
        if ready is True:
            if status != "EXACT_INTEGRATED_LINK_FORM_READY":
                errors.append(
                    f"{key}: exact-ready link must use EXACT_INTEGRATED_LINK_FORM_READY"
                )
            if not isinstance(pointer, str) or not pointer.strip():
                errors.append(f"{key}: exact-ready link requires equation_pointer")
        else:
            if status == "EXACT_INTEGRATED_LINK_FORM_READY":
                errors.append(
                    f"{key}: readiness status claims exact form without exact-ready flag"
                )
            if pointer is not None:
                errors.append(
                    f"{key}: non-ready link may not expose a canonical equation pointer"
                )

        if item.get("current_activation_authorized") is not False:
            errors.append(f"{key}: link registry may not authorize activation")
        if not str(item.get("reason", "")).strip():
            errors.append(f"{key}: missing readiness reason")

    exact_ready = sum(
        item.get("exact_integrated_equation_ready") is True for item in rows
    )
    summary = registry["current_summary"]
    if summary["registered_feedback_links"] != len(expected):
        errors.append("feedback-link summary registered-link count is stale")
    if summary["exact_integrated_link_forms_ready"] != exact_ready:
        errors.append("feedback-link summary exact-ready count is stale")
    if summary["activation_authorized"] is not False:
        errors.append("feedback-link summary may not authorize activation")

    computed = compute_loop_readiness(
        feedback, registry, boundary, mechanisms
    )
    if computed != registry.get("loop_activation_readiness"):
        errors.append("per-loop activation-readiness matrix is stale")
    ready_loops = sum(
        item["activation_status"] == "READY" for item in computed
    )
    if summary["feedback_structures_with_all_links_exact_ready"] != ready_loops:
        errors.append("feedback-link summary ready-loop count is stale")
    if ready_loops == 0 and summary["current_status"] != (
        "BLOCKED_ALL_REGISTERED_STRUCTURES"
    ):
        errors.append("feedback-link summary must report all structures blocked")

    for item in computed:
        if item["quantitative_activation_authorized"] is not False:
            errors.append(
                f"{item['loop_id']}: readiness matrix may not authorize activation"
            )
        if item["topology_status"] == "OPEN_CHAIN" and (
            "OPEN_CHAIN_NOT_CLOSED" not in item["blockers"]
        ):
            errors.append(
                f"{item['loop_id']}: open chain lacks closure blocker"
            )

    return errors


def main() -> None:
    feedback = json.loads(FEEDBACK_PATH.read_text(encoding="utf-8"))
    registry = json.loads(LINK_PATH.read_text(encoding="utf-8"))
    boundary = json.loads(BOUNDARY_PATH.read_text(encoding="utf-8"))
    mechanisms = json.loads(MECHANISM_PATH.read_text(encoding="utf-8"))
    errors = audit_feedback_link_readiness(
        feedback, registry, boundary, mechanisms
    )
    if errors:
        raise RuntimeError(
            "Feedback link readiness audit failed:\n- " + "\n- ".join(errors)
        )
    print(
        json.dumps(
            {
                "status": "PASS",
                "registered_feedback_links": len(registry["links"]),
                "exact_integrated_link_forms_ready": registry["current_summary"][
                    "exact_integrated_link_forms_ready"
                ],
                "loop_activation_readiness": registry[
                    "loop_activation_readiness"
                ],
                "activation_authorized": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
