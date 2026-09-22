from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTH_PATH = ROOT / "model" / "registries" / "release_publication_authorization.json"
CONTRACT_PATH = ROOT / "model" / "registries" / "release_versioning_contract.json"
MODEL_PATH = ROOT / "model" / "registries" / "model_contract.json"

def parse_field(text: str, name: str) -> str:
    m = re.search(rf"^{re.escape(name)}:\s*[\"']?([^\"'\n]+)[\"']?\s*$", text, re.MULTILINE)
    if m is None:
        raise AssertionError(f"missing field {name}")
    return m.group(1).strip()

def audit_release_publication_authorization() -> list[str]:
    errors: list[str] = []
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    model = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
    with (ROOT / "pyproject.toml").open("rb") as h:
        version = tomllib.load(h)["project"]["version"]

    init_text = (ROOT / "src" / "romania_macro_financial_dynamics" / "__init__.py").read_text(encoding="utf-8")
    im = re.search(r'__version__\s*=\s*"([^"]+)"', init_text)
    citation = (ROOT / "CITATION.cff").read_text(encoding="utf-8")
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    release_index = (ROOT / "releases" / "README.md").read_text(encoding="utf-8")
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")
    status_text = (ROOT / "STATUS.md").read_text(encoding="utf-8")

    expected = auth["release_version"]
    if auth["tag"] != f"v{expected}":
        errors.append("release tag does not match release version")
    if version != expected:
        errors.append("pyproject version differs from release state")
    if im is None or im.group(1) != expected:
        errors.append("package runtime version differs from release state")
    if parse_field(citation, "version") != expected:
        errors.append("citation version differs from release state")
    if parse_field(citation, "date-released") != auth["intended_release_date"]:
        errors.append("citation release date differs from release state")
    if f"Version: {expected}" not in readme:
        errors.append("README version badge alt text differs from release state")
    if f"The current public release is **v{expected}**." not in release_index:
        errors.append("release index introductory current-release sentence is stale")
    if f"- Current public release: **v{expected}**" not in release_index:
        errors.append("release index current-release state is stale")
    if f"- Release date: **{auth['intended_release_date']}**" not in release_index:
        errors.append("release index current-release date is stale")
    if auth.get("exact_release_commit") not in release_index:
        errors.append("release index current-release commit is stale")
    if f"## {expected} - {auth['intended_release_date']}" not in changelog:
        errors.append("CHANGELOG lacks release heading/date")

    status_release = re.search(
        r"^Romanian Monetary Dynamics \(RMD\) \*\*v([^*]+)\*\* is the current public scientific-core release, published on (\d{4}-\d{2}-\d{2}) from the exact Scientific-CI-green commit \x60([0-9a-f]{40})\x60\.",
        status_text,
        re.MULTILINE,
    )
    if status_release is None:
        errors.append("STATUS lacks canonical current-public-release sentence")
    else:
        status_version, status_date, status_commit = status_release.groups()
        if status_version != expected:
            errors.append("STATUS current public release differs from release state")
        if status_date != auth["intended_release_date"]:
            errors.append("STATUS current public release date differs from release state")
        if status_commit != auth.get("exact_release_commit"):
            errors.append("STATUS current public release commit differs from release state")

    notes = ROOT / auth["release_notes_path"]
    if not notes.is_file():
        errors.append("versioned release notes are missing")
    elif f"v{expected}" not in notes.read_text(encoding="utf-8"):
        errors.append("versioned release notes do not identify release version")

    basis = contract["versioning_basis"]
    prep = basis.get("release_preparation", {})
    governance = model["repository_governance"]

    if basis["current_repository_version"] != expected:
        errors.append("release contract repository version differs from release state")
    if governance.get("current_repository_version") != expected:
        errors.append("model governance repository version differs from release state")
    if governance.get("release_or_version_change_authorized") is not False:
        errors.append("historical integration authority must not become release authority")
    if governance.get("release_publication_authorization") != "model/registries/release_publication_authorization.json":
        errors.append("model governance lacks release-publication authorization pointer")

    state = auth.get("publication_state")
    if auth.get("publication_authorized") is True:
        if state not in (None, "READY_FOR_PUBLICATION_AFTER_GREEN_MAIN_CI"):
            errors.append("active authorization has unexpected publication state")
        if basis["next_public_release_candidate"] != expected:
            errors.append("prepublication next candidate differs from authorized release")
        if prep.get("state") != "READY_FOR_PUBLICATION_AFTER_GREEN_MAIN_CI":
            errors.append("release preparation state is not publication-ready")
        if prep.get("candidate_version") != expected or prep.get("candidate_tag") != auth["tag"]:
            errors.append("release preparation candidate identity differs from authorization")
        if governance.get("release_publication_authorized_by_release_readiness") is not True:
            errors.append("dedicated release-readiness authority is missing")
    else:
        if state != "PUBLISHED_AND_AUTHORIZATION_CONSUMED":
            errors.append("inactive authorization must be in published/consumed state")
        if auth.get("trigger_consumed") is not True:
            errors.append("published authorization trigger must be consumed")
        record_path = auth.get("publication_record")
        if not record_path:
            errors.append("published state lacks publication record")
        else:
            record_file = ROOT / record_path
            if not record_file.is_file():
                errors.append("publication record file is missing")
            else:
                record = json.loads(record_file.read_text(encoding="utf-8"))
                if record.get("release_version") != expected or record.get("tag") != auth["tag"]:
                    errors.append("publication record release identity mismatch")
                if record.get("release_target_commit") != auth.get("exact_release_commit"):
                    errors.append("publication record release commit mismatch")
                if record.get("tag_target_commit") != auth.get("exact_release_commit"):
                    errors.append("publication record tag commit mismatch")
                if record.get("github_release_immutable") is not True:
                    errors.append("publication record must preserve immutable release state")
                if record.get("publication_workflow_conclusion") != "success":
                    errors.append("publication workflow did not complete successfully")
        current = basis["current_public_release"]
        if current.get("version") != expected or current.get("tag") != auth["tag"]:
            errors.append("current public release differs from published release")
        if current.get("release_target_commit") != auth.get("exact_release_commit"):
            errors.append("current public release commit differs from published release")
        if prep.get("state") != "PUBLISHED_AND_FINALIZED" or prep.get("publication_complete") is not True:
            errors.append("release preparation is not finalized after publication")
        if governance.get("current_public_release") != expected:
            errors.append("model governance current public release differs from published release")
        if governance.get("release_publication_authorized_by_release_readiness") is not False:
            errors.append("one-shot publication authority must be inactive after publication")

    for key, value in auth["hard_rules"].items():
        if value is not True:
            errors.append(f"release hard rule disabled: {key}")
    for key, value in auth["scientific_effect"].items():
        if value is not False:
            errors.append(f"release process may not authorize scientific effect: {key}")
    return errors

def main() -> None:
    errors = audit_release_publication_authorization()
    if errors:
        raise RuntimeError("Release publication-state audit failed:\n- " + "\n- ".join(errors))
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    print(json.dumps({
        "status": "PASS",
        "release_version": auth["release_version"],
        "tag": auth["tag"],
        "publication_authorized": auth["publication_authorized"],
        "publication_state": auth.get("publication_state", "PREPUBLICATION"),
        "exact_release_commit": auth.get("exact_release_commit"),
        "scientific_effect": "NONE",
    }, indent=2))

if __name__ == "__main__":
    main()
