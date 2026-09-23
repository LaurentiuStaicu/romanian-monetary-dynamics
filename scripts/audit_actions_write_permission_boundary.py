from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW_DIR = ROOT / ".github" / "workflows"

PUBLISHER = ".github/workflows/publish-authorized-release.yml"
MOF_MANUAL_WRITE_WORKFLOWS = {
    ".github/workflows/mof-announced-ron-primary-reference-auction-full-2025-source-vintage.yml",
    ".github/workflows/mof-announced-ron-primary-reference-auction-partial-2025-materialise.yml",
    ".github/workflows/mof-announced-ron-primary-reference-auction-recovered-official-pdfs.yml",
}
ALLOWED_WRITE_WORKFLOWS = MOF_MANUAL_WRITE_WORKFLOWS | {PUBLISHER}

WRITE_SCOPE_RE = re.compile(r"^(?P<indent>\s*)(?P<scope>[A-Za-z0-9_-]+):\s*write\s*(?:#.*)?$")
WRITE_ALL_RE = re.compile(r"^\s*permissions:\s*write-all\s*(?:#.*)?$")


def workflow_paths() -> list[Path]:
    return sorted(
        p
        for p in WORKFLOW_DIR.iterdir()
        if p.is_file() and p.suffix in {".yml", ".yaml"}
    )


def write_occurrences(text: str) -> list[tuple[int, str, int]]:
    out: list[tuple[int, str, int]] = []
    for number, line in enumerate(text.splitlines(), start=1):
        match = WRITE_SCOPE_RE.match(line)
        if match:
            out.append((number, match.group("scope"), len(match.group("indent"))))
    return out


def workflow_uses_pull_request_target(text: str) -> bool:
    """Detect the privileged pull_request_target trigger in workflow event syntax."""
    header = text.split("\njobs:", 1)[0]
    for raw_line in header.splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if re.match(r"^pull_request_target\s*:", line):
            return True
        if re.match(r"^on\s*:", line) and re.search(
            r"\bpull_request_target\b", line
        ):
            return True
    return False


def audit_actions_write_permission_boundary() -> list[str]:
    errors: list[str] = []
    discovered: dict[str, list[tuple[int, str, int]]] = {}

    for path in workflow_paths():
        relative = path.relative_to(ROOT).as_posix()
        text = path.read_text(encoding="utf-8")
        lines = text.splitlines()

        if not any(line.startswith("permissions:") for line in lines):
            errors.append(
                f"{relative}: workflow must declare top-level permissions explicitly"
            )

        if any(WRITE_ALL_RE.match(line) for line in lines):
            errors.append(f"{relative}: permissions: write-all is forbidden")

        if workflow_uses_pull_request_target(text):
            errors.append(
                f"{relative}: pull_request_target is forbidden by repository policy; "
                "use pull_request or require an explicit governance redesign"
            )

        occurrences = write_occurrences(text)
        if occurrences:
            discovered[relative] = occurrences

    unexpected_paths = set(discovered) - ALLOWED_WRITE_WORKFLOWS
    missing_paths = ALLOWED_WRITE_WORKFLOWS - set(discovered)
    if unexpected_paths:
        errors.append(
            "unexpected write-capable workflows: " + ", ".join(sorted(unexpected_paths))
        )
    if missing_paths:
        errors.append(
            "declared write-boundary workflows lost their expected write scope: "
            + ", ".join(sorted(missing_paths))
        )

    for relative, occurrences in discovered.items():
        for line, scope, _indent in occurrences:
            if scope != "contents":
                errors.append(
                    f"{relative}:{line}: only contents: write is allowed; found {scope}: write"
                )

    for relative in MOF_MANUAL_WRITE_WORKFLOWS:
        path = ROOT / relative
        text = path.read_text(encoding="utf-8")
        occurrences = discovered.get(relative, [])
        if len(occurrences) != 1:
            errors.append(f"{relative}: expected exactly one contents: write occurrence")
        elif occurrences[0][2] != 2:
            errors.append(
                f"{relative}:{occurrences[0][0]}: MoF contents: write must remain workflow-level"
            )

        for token in (
            "workflow_dispatch:",
            "EVIDENCE-TRIGGERED MANUAL RECOVERY ONLY",
            "trigger_condition:",
            "evidence_reference:",
            "evidence_verified:",
            "inputs.evidence_verified == true",
        ):
            if token not in text:
                errors.append(f"{relative}: missing manual evidence safeguard {token!r}")
        if "\n  push:" in text:
            errors.append(f"{relative}: automatic push trigger is forbidden")
        if "\n  schedule:" in text:
            errors.append(f"{relative}: polling schedule is forbidden")
        if "\n  pull_request:" in text or "\n  pull_request_target:" in text:
            errors.append(f"{relative}: PR-triggered write capability is forbidden")

    publisher_text = (ROOT / PUBLISHER).read_text(encoding="utf-8")
    publisher_occurrences = discovered.get(PUBLISHER, [])
    if len(publisher_occurrences) != 1:
        errors.append(f"{PUBLISHER}: expected exactly one contents: write occurrence")
    elif publisher_occurrences[0][2] != 6:
        errors.append(
            f"{PUBLISHER}:{publisher_occurrences[0][0]}: publisher write scope must remain job-level"
        )

    try:
        publisher_header, publisher_jobs = publisher_text.split("jobs:", 1)
        authorization_job, publish_job = publisher_jobs.split("  publish-release:", 1)
    except ValueError:
        errors.append(f"{PUBLISHER}: publisher job topology is not parseable")
    else:
        if "contents: read" not in publisher_header:
            errors.append(f"{PUBLISHER}: default workflow token is not read-only")
        if "contents: write" in publisher_header:
            errors.append(f"{PUBLISHER}: global contents write is forbidden")
        if "  check-authorization:" not in publisher_jobs:
            errors.append(f"{PUBLISHER}: missing read-only authorization job")
        if "contents: write" in authorization_job:
            errors.append(f"{PUBLISHER}: authorization job may not have write access")
        for token in (
            "needs: check-authorization",
            "if: needs.check-authorization.outputs.authorized == 'true'",
            "permissions:",
            "contents: write",
        ):
            if token not in publish_job:
                errors.append(f"{PUBLISHER}: publish job lost safeguard {token!r}")

    return errors


def main() -> None:
    errors = audit_actions_write_permission_boundary()
    if errors:
        raise RuntimeError(
            "GitHub Actions write-permission boundary audit failed:\n- "
            + "\n- ".join(errors)
        )

    discovered = {}
    for path in workflow_paths():
        occurrences = write_occurrences(path.read_text(encoding="utf-8"))
        if occurrences:
            discovered[path.relative_to(ROOT).as_posix()] = [
                {"line": line, "scope": scope, "indent": indent}
                for line, scope, indent in occurrences
            ]

    import json

    print(
        json.dumps(
            {
                "status": "PASS",
                "workflow_count": len(workflow_paths()),
                "explicit_permissions_required": True,
                "write_capable_workflow_count": len(discovered),
                "write_capable_workflows": discovered,
                "policy": "EXACT_ALLOWLIST_LEAST_PRIVILEGE",
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
