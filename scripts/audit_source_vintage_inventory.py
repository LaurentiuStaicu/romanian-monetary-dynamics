from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/provenance/source_vintage_inventory_registry.json"
SOURCE_ROOT = ROOT / "data/source_vintages"
SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def load(relative: str) -> dict:
    return json.loads((ROOT / relative).read_text(encoding="utf-8"))


def collect_strings(value: object) -> list[str]:
    if isinstance(value, str):
        return [value]
    if isinstance(value, list):
        out: list[str] = []
        for item in value:
            out.extend(collect_strings(item))
        return out
    if isinstance(value, dict):
        out = []
        for item in value.values():
            out.extend(collect_strings(item))
        return out
    return []


def audit_source_vintage_inventory() -> list[str]:
    errors: list[str] = []
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    entries = registry["entries"]
    allowed = set(registry["allowed_anchor_types"])

    actual_dirs = sorted(
        str(path.relative_to(ROOT))
        for path in SOURCE_ROOT.iterdir()
        if path.is_dir()
    )
    registered_dirs = [entry["directory"] for entry in entries]

    if len(registered_dirs) != len(set(registered_dirs)):
        errors.append("source-vintage inventory contains duplicate directories")
    if sorted(registered_dirs) != actual_dirs:
        missing = sorted(set(actual_dirs) - set(registered_dirs))
        stale = sorted(set(registered_dirs) - set(actual_dirs))
        errors.append(
            f"source-vintage inventory coverage mismatch: missing={missing}, stale={stale}"
        )
    if registry["directory_count"] != len(entries):
        errors.append("source-vintage inventory directory_count is stale")
    if registry["directory_count"] != len(actual_dirs):
        errors.append("source-vintage inventory count disagrees with repository")

    for entry in entries:
        directory = ROOT / entry["directory"]
        anchor = ROOT / entry["anchor"]
        anchor_type = entry["anchor_type"]

        if anchor_type not in allowed:
            errors.append(f"{entry['directory']}: unsupported anchor type {anchor_type}")
            continue
        if not directory.is_dir():
            errors.append(f"{entry['directory']}: retained directory missing")
            continue
        if not anchor.is_file():
            errors.append(f"{entry['directory']}: provenance anchor missing: {entry['anchor']}")
            continue
        if not isinstance(entry.get("reason"), str) or not entry["reason"].strip():
            errors.append(f"{entry['directory']}: provenance classification lacks reason")

        try:
            payload = json.loads(anchor.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            errors.append(f"{entry['directory']}: anchor is not valid JSON")
            continue

        if anchor_type in {"LOCAL_MANIFEST", "LOCAL_AUDIT_ANCHOR"}:
            if anchor.parent != directory:
                errors.append(
                    f"{entry['directory']}: local provenance anchor is outside its directory"
                )

        if anchor_type == "LOCAL_AUDIT_ANCHOR":
            strings = collect_strings(payload)
            if not any(SHA256_RE.fullmatch(value) for value in strings):
                errors.append(
                    f"{entry['directory']}: local audit anchor contains no SHA-256 identity"
                )

        if anchor_type == "EXTERNAL_REVIEW_COPY_ANCHOR":
            if entry["directory"] != (
                "data/source_vintages/"
                "fiscal-reaction-capb-realtime-artifact-review-2026-09-20"
            ):
                errors.append(
                    f"{entry['directory']}: unexpected external review-copy exception"
                )
                continue
            source = payload.get("source_materialisation", {})
            if source.get("repository_text_evidence_path") != entry["directory"]:
                errors.append("CAPB review-copy assessment path does not match inventory")
            if source.get("exact_source_vintage_reproducibility_claim_allowed") is not False:
                errors.append("CAPB review copy may not claim exact source-vintage reproducibility")
            if source.get("reproducibility_classification") != (
                "ARTIFACT_HASH_IDENTITY_PLUS_NORMALIZED_REPOSITORY_REVIEW_COPIES"
            ):
                errors.append("CAPB review-copy reproducibility classification changed")
            for key in (
                "artifact_zip_sha256",
                "inventory_sha256",
                "repository_inventory_review_copy_sha256",
            ):
                value = source.get(key)
                if not isinstance(value, str) or not SHA256_RE.fullmatch(value):
                    errors.append(f"CAPB review-copy assessment lacks valid {key}")

            preservation = load(
                "model/calibration_validation/"
                "fiscal_capb_raw_source_preservation_assessment_2026_09_20.json"
            )
            retained = preservation["retained_source_vintage"]
            if retained["raw_repository_retained"] is not True:
                errors.append("CAPB successor raw source is not retained")
            if retained["later_live_refetch_required_for_reproduction"] is not False:
                errors.append("CAPB successor raw source still requires live refetch")
            if preservation["verification"]["exact_reviewed_artifact_identity_preserved"] is not True:
                errors.append("CAPB successor does not preserve reviewed artifact identity")

    return errors


def main() -> None:
    errors = audit_source_vintage_inventory()
    if errors:
        raise RuntimeError(
            "Source-vintage inventory audit failed:\n- " + "\n- ".join(errors)
        )
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    for entry in registry["entries"]:
        anchor_type = entry["anchor_type"]
        counts[anchor_type] = counts.get(anchor_type, 0) + 1
    print(
        json.dumps(
            {
                "status": "PASS",
                "source_vintage_directories": registry["directory_count"],
                "anchor_type_counts": counts,
                "unregistered_directories": 0,
                "reproducibility_classifications_upgraded": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
