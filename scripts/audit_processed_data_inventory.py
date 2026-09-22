from __future__ import annotations

import csv
import hashlib
import io
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "data/provenance/processed_data_inventory_registry.json"
PROCESSED_ROOT = ROOT / "data/processed"


def git_blob_sha1(data: bytes) -> str:
    header = f"blob {len(data)}\0".encode("ascii")
    return hashlib.sha1(header + data).hexdigest()


def audit_processed_data_inventory() -> list[str]:
    errors: list[str] = []
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    entries = registry["entries"]
    allowed = set(registry["allowed_provenance_classes"])
    rules = registry.get("rules", {})
    if rules.get("declared_sidecar_must_bind_exact_processed_artifact") is not True:
        errors.append("processed-data inventory sidecar-binding rule is not enabled")

    actual = sorted(
        str(path.relative_to(ROOT))
        for path in PROCESSED_ROOT.iterdir()
        if path.is_file() and path.suffix.lower() == ".csv"
    )
    registered = [entry["path"] for entry in entries]

    if len(registered) != len(set(registered)):
        errors.append("processed-data inventory contains duplicate paths")
    if sorted(registered) != actual:
        missing = sorted(set(actual) - set(registered))
        stale = sorted(set(registered) - set(actual))
        errors.append(f"processed-data inventory coverage mismatch: missing={missing}, stale={stale}")
    if registry["file_count"] != len(entries) or registry["file_count"] != len(actual):
        errors.append("processed-data inventory file_count is stale")

    for entry in entries:
        path = ROOT / entry["path"]
        provenance_class = entry["provenance_class"]
        if provenance_class not in allowed:
            errors.append(f"{entry['path']}: unsupported provenance class {provenance_class}")
            continue
        if not path.is_file():
            errors.append(f"{entry['path']}: processed file missing")
            continue

        data = path.read_bytes()
        observed_sha = git_blob_sha1(data)
        if observed_sha != entry["git_blob_sha1"]:
            errors.append(
                f"{entry['path']}: Git blob identity changed "
                f"(expected {entry['git_blob_sha1']}, got {observed_sha})"
            )

        try:
            header = next(csv.reader(io.StringIO(data.decode("utf-8-sig"))))
        except Exception as exc:
            errors.append(f"{entry['path']}: CSV header could not be parsed: {exc}")
            continue
        missing_columns = sorted(set(entry["required_columns"]) - set(header))
        if missing_columns:
            errors.append(f"{entry['path']}: required provenance columns missing: {missing_columns}")

        authorities = entry.get("authorities", [])
        if not authorities:
            errors.append(f"{entry['path']}: no semantic/provenance authority declared")
        authority_texts: list[str] = []
        for relative in authorities:
            authority = ROOT / relative
            if not authority.is_file():
                errors.append(f"{entry['path']}: authority missing: {relative}")
                continue
            authority_texts.append(authority.read_text(encoding="utf-8", errors="replace"))

        sidecar = entry.get("provenance_sidecar")
        if provenance_class == "SIDECAR_JSON" and not sidecar:
            errors.append(f"{entry['path']}: SIDECAR_JSON entry lacks provenance_sidecar")
        if sidecar:
            sidecar_path = ROOT / sidecar
            if not sidecar_path.is_file():
                errors.append(f"{entry['path']}: provenance sidecar missing: {sidecar}")
            else:
                try:
                    payload = json.loads(sidecar_path.read_text(encoding="utf-8"))
                except json.JSONDecodeError:
                    errors.append(f"{entry['path']}: provenance sidecar is not valid JSON")
                else:
                    if not payload:
                        errors.append(f"{entry['path']}: provenance sidecar is empty")
                    if payload.get("processed_artifact") != entry["path"]:
                        errors.append(
                            f"{entry['path']}: provenance sidecar does not bind the exact processed artifact"
                        )

        if provenance_class in {"ASSESSMENT_EMBEDDED", "ASSESSMENT_PLUS_SOURCE_VINTAGE", "LEGACY_RECONCILED_BY_SUCCESSOR"}:
            combined = "\n".join(authority_texts)
            if entry["path"] not in combined:
                errors.append(
                    f"{entry['path']}: no declared authority explicitly references the processed artifact"
                )

        if provenance_class == "ASSESSMENT_PLUS_SOURCE_VINTAGE":
            anchors = entry.get("source_vintage_anchors", [])
            if not anchors:
                errors.append(f"{entry['path']}: source-vintage-backed entry lacks anchors")
            for relative in anchors:
                if not (ROOT / relative).is_file():
                    errors.append(f"{entry['path']}: source-vintage anchor missing: {relative}")

        if provenance_class == "LEGACY_RECONCILED_BY_SUCCESSOR":
            if len(authorities) < 1:
                errors.append(f"{entry['path']}: legacy entry lacks successor reconciliation authority")

        for key in ("role", "scientific_boundary"):
            if not isinstance(entry.get(key), str) or not entry[key].strip():
                errors.append(f"{entry['path']}: {key} is empty")

    return errors


def main() -> None:
    errors = audit_processed_data_inventory()
    if errors:
        raise RuntimeError("Processed-data inventory audit failed:\n- " + "\n- ".join(errors))
    registry = json.loads(REGISTRY.read_text(encoding="utf-8"))
    classes: dict[str, int] = {}
    for entry in registry["entries"]:
        classes[entry["provenance_class"]] = classes.get(entry["provenance_class"], 0) + 1
    print(json.dumps({
        "status": "PASS",
        "processed_csv_count": registry["file_count"],
        "provenance_classes": classes,
        "unregistered_processed_csvs": 0,
        "scientific_state_changed": False
    }, indent=2))


if __name__ == "__main__":
    main()
