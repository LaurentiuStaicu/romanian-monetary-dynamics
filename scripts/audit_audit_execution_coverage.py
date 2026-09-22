from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
WORKFLOWS = ROOT / ".github" / "workflows"
AUDIT_NAME = re.compile(r"scripts/(audit_[A-Za-z0-9_]+\.py)")


def workflow_audit_references() -> dict[str, set[str]]:
    references: dict[str, set[str]] = {}
    for path in sorted(WORKFLOWS.glob("*.y*ml")):
        found: set[str] = set()
        for raw_line in path.read_text(encoding="utf-8").splitlines():
            line = raw_line.lstrip()
            if line.startswith("#"):
                continue
            executable = raw_line.split("#", 1)[0]
            found.update(AUDIT_NAME.findall(executable))
        references[path.name] = found
    return references


def main() -> None:
    audit_scripts = {path.name for path in SCRIPTS.glob("audit_*.py")}
    references_by_workflow = workflow_audit_references()
    referenced = set().union(*references_by_workflow.values())

    unreferenced = sorted(audit_scripts - referenced)
    dangling = sorted(referenced - audit_scripts)

    if unreferenced or dangling:
        problems = []
        if unreferenced:
            problems.append(
                "audit scripts without a workflow execution path: "
                + ", ".join(unreferenced)
            )
        if dangling:
            problems.append(
                "workflow references to missing audit scripts: "
                + ", ".join(dangling)
            )
        raise RuntimeError(
            "Audit execution-coverage gate failed:\n- "
            + "\n- ".join(problems)
        )

    print(
        json.dumps(
            {
                "status": "PASS",
                "audit_scripts": len(audit_scripts),
                "workflow_references": len(referenced),
                "workflows_with_audit_references": sum(
                    bool(items) for items in references_by_workflow.values()
                ),
                "unreferenced_audit_scripts": 0,
                "dangling_audit_references": 0,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
