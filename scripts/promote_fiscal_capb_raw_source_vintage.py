from __future__ import annotations

import argparse
import csv
import hashlib
import json
import shutil
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONTRACT = (
    ROOT / "model" / "calibration_validation"
    / "fiscal_capb_raw_source_preservation_contract.json"
)


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def load_contract() -> dict:
    return json.loads(CONTRACT.read_text(encoding="utf-8"))


def pre2022_records(source: Path, contract: dict) -> list[dict[str, object]]:
    audit_path = source / "fiscal_capb_pre2022_source_probe_audit.json"
    audit = json.loads(audit_path.read_text(encoding="utf-8"))
    expected = contract["source_artifacts"]["pre2022"]
    if int(audit["release_count"]) != int(expected["required_release_count"]):
        raise RuntimeError("pre-2022 release-count mismatch")
    if audit["status_counts"] != expected["required_status_counts"]:
        raise RuntimeError("pre-2022 status-count mismatch")
    if audit["target_code"] != contract["target_series"]["code"]:
        raise RuntimeError("pre-2022 target-code mismatch")

    records: list[dict[str, object]] = []
    for item in audit["releases"]:
        raw = source / item["archive_path"]
        if not raw.is_file():
            raise RuntimeError(f"missing pre-2022 raw archive: {item['release_id']}")
        observed = sha256(raw)
        if observed != item["archive_sha256"]:
            raise RuntimeError(f"pre-2022 raw hash mismatch: {item['release_id']}")
        records.append(
            {
                "release_id": item["release_id"],
                "release_label": item["release_label"],
                "release_date": item["release_date"],
                "source_url": item["source_url"],
                "source_artifact_group": "pre2022",
                "source_status": item["status"],
                "archive_sha256": observed,
                "archive_bytes": raw.stat().st_size,
                "source_path": str(raw),
            }
        )
    return records


def post2022_records(source: Path, contract: dict) -> list[dict[str, object]]:
    inventory_path = source / "fiscal_capb_release_inventory.csv"
    expected = contract["source_artifacts"]["from2022"]
    if sha256(inventory_path) != expected["required_inventory_sha256"]:
        raise RuntimeError("2022+ artifact inventory hash mismatch")

    with inventory_path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    if len(rows) != int(expected["required_release_count"]):
        raise RuntimeError("2022+ release-count mismatch")

    records: list[dict[str, object]] = []
    for row in rows:
        if row["target_code"] != contract["target_series"]["code"]:
            raise RuntimeError(f"2022+ target-code mismatch: {row['release_id']}")
        raw = source / "raw" / f"{row['release_id']}.zip"
        if not raw.is_file():
            raise RuntimeError(f"missing 2022+ raw archive: {row['release_id']}")
        observed = sha256(raw)
        if observed != row["archive_sha256"]:
            raise RuntimeError(f"2022+ raw hash mismatch: {row['release_id']}")
        records.append(
            {
                "release_id": row["release_id"],
                "release_label": row["release_label"],
                "release_date": row["release_date"],
                "source_url": row["source_url"],
                "source_artifact_group": "from2022",
                "source_status": row["status"],
                "archive_sha256": observed,
                "archive_bytes": raw.stat().st_size,
                "source_path": str(raw),
            }
        )
    return records


def promote(pre2022: Path, post2022: Path, output: Path) -> dict:
    contract = load_contract()
    if output.exists():
        raise RuntimeError(f"destination already exists: {output}")

    records = pre2022_records(pre2022, contract) + post2022_records(post2022, contract)
    ids = [str(item["release_id"]) for item in records]
    if len(ids) != len(set(ids)):
        raise RuntimeError("duplicate release id across source artifacts")

    output_raw = output / "raw"
    output_raw.mkdir(parents=True, exist_ok=False)

    manifest_records = []
    for item in sorted(records, key=lambda x: str(x["release_date"])):
        source_path = Path(str(item.pop("source_path")))
        dest = output_raw / f"{item['release_id']}.zip"
        shutil.copyfile(source_path, dest)
        copied_hash = sha256(dest)
        if copied_hash != item["archive_sha256"]:
            raise RuntimeError(f"copy hash mismatch: {item['release_id']}")
        manifest_records.append(
            {
                **item,
                "repository_path": str(dest.relative_to(ROOT)),
                "repository_sha256": copied_hash,
                "repository_bytes": dest.stat().st_size,
            }
        )

    evidence = output / "review_evidence"
    evidence.mkdir()
    shutil.copyfile(
        pre2022 / "fiscal_capb_pre2022_source_probe_audit.json",
        evidence / "fiscal_capb_pre2022_source_probe_audit.json",
    )
    shutil.copyfile(
        pre2022 / "snapshot_manifest.json",
        evidence / "pre2022_snapshot_manifest.json",
    )
    shutil.copyfile(
        post2022 / "fiscal_capb_release_inventory.csv",
        evidence / "fiscal_capb_release_inventory_2022_2026.csv",
    )
    shutil.copyfile(
        post2022 / "snapshot_manifest.json",
        evidence / "post2022_snapshot_manifest.json",
    )

    manifest = {
        "snapshot_version": "0.1",
        "snapshot_id": "fiscal-reaction-structural-primary-realtime-raw-vintage-2026-09-20",
        "target_series": contract["target_series"],
        "source_artifacts": contract["source_artifacts"],
        "release_count": len(manifest_records),
        "first_release_date": min(x["release_date"] for x in manifest_records),
        "last_release_date": max(x["release_date"] for x in manifest_records),
        "raw_repository_retained": True,
        "later_live_refetch_required_for_reproduction": False,
        "releases": manifest_records,
        "scientific_effect": contract["scientific_effect"],
    }
    manifest_path = output / "snapshot_manifest.json"
    manifest_path.write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return manifest


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--pre2022", type=Path, required=True)
    parser.add_argument("--from2022", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    manifest = promote(args.pre2022, args.from2022, args.output)
    print(json.dumps({
        "status": "RAW_SOURCE_VINTAGE_READY_FOR_REPOSITORY_REVIEW",
        "release_count": manifest["release_count"],
        "output": str(args.output),
        "estimation_authorized": False,
    }, indent=2))


if __name__ == "__main__":
    main()
