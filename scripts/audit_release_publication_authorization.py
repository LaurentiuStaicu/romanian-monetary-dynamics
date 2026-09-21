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
    changelog = (ROOT / "CHANGELOG.md").read_text(encoding="utf-8")

    expected = auth["release_version"]
    if auth["publication_authorized"] is not True:
        errors.append("release publication authorization is not active")
    if auth["tag"] != f"v{expected}":
        errors.append("release tag does not match release version")
    if version != expected:
        errors.append("pyproject version differs from authorized release")
    if im is None or im.group(1) != expected:
        errors.append("package runtime version differs from authorized release")
    if parse_field(citation, "version") != expected:
        errors.append("citation version differs from authorized release")
    if parse_field(citation, "date-released") != auth["intended_release_date"]:
        errors.append("citation release date differs from authorization")
    if f"Version: {expected}" not in readme:
        errors.append("README version badge alt text differs from authorized release")
    if f"## {expected} - {auth['intended_release_date']}" not in changelog:
        errors.append("CHANGELOG lacks authorized release heading/date")

    notes = ROOT / auth["release_notes_path"]
    if not notes.is_file():
        errors.append("authorized versioned release notes are missing")
    else:
        note_text = notes.read_text(encoding="utf-8")
        if f"v{expected}" not in note_text:
            errors.append("versioned release notes do not identify authorized version")

    basis = contract["versioning_basis"]
    prep = basis.get("release_preparation", {})
    if basis["current_repository_version"] != expected:
        errors.append("release contract repository version differs from authorization")
    if basis["next_public_release_candidate"] != expected:
        errors.append("release contract next public candidate differs from authorization")
    if prep.get("state") != "READY_FOR_PUBLICATION_AFTER_GREEN_MAIN_CI":
        errors.append("release preparation state is not publication-ready")
    if prep.get("candidate_version") != expected or prep.get("candidate_tag") != auth["tag"]:
        errors.append("release preparation candidate identity differs from authorization")
    if prep.get("release_notes") != auth["release_notes_path"]:
        errors.append("release preparation notes pointer differs from authorization")

    governance = model["repository_governance"]
    if governance.get("current_repository_version") != expected:
        errors.append("model governance repository version differs from authorization")
    if governance.get("release_or_version_change_authorized") is not False:
        errors.append("historical integration authority must not become release authority")
    if governance.get("release_publication_authorized_by_release_readiness") is not True:
        errors.append("dedicated release-readiness authority is missing")
    if governance.get("release_publication_authorization") != "model/registries/release_publication_authorization.json":
        errors.append("model governance lacks release-publication authorization pointer")

    for key, value in auth["hard_rules"].items():
        if value is not True:
            errors.append(f"release hard rule disabled: {key}")
    for key, value in auth["scientific_effect"].items():
        if value is not False:
            errors.append(f"release preparation may not authorize scientific effect: {key}")
    return errors

def main() -> None:
    errors = audit_release_publication_authorization()
    if errors:
        raise RuntimeError("Release publication authorization audit failed:\n- " + "\n- ".join(errors))
    auth = json.loads(AUTH_PATH.read_text(encoding="utf-8"))
    print(json.dumps({
        "status":"PASS",
        "release_version":auth["release_version"],
        "tag":auth["tag"],
        "publication_authorized":True,
        "publication_trigger":auth["publication_trigger"],
        "scientific_effect":"NONE",
    }, indent=2))

if __name__ == "__main__":
    main()
