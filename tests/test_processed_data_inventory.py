from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_processed_data_inventory import audit_processed_data_inventory

ROOT = Path(__file__).resolve().parents[1]


class ProcessedDataInventoryTests(unittest.TestCase):
    def test_every_processed_csv_has_pinned_provenance_coverage(self) -> None:
        self.assertEqual(audit_processed_data_inventory(), [])

    def test_declared_sidecars_bind_exact_processed_artifact(self) -> None:
        registry = json.loads(
            (ROOT / "data/provenance/processed_data_inventory_registry.json").read_text(
                encoding="utf-8"
            )
        )
        for entry in registry["entries"]:
            sidecar = entry.get("provenance_sidecar")
            if not sidecar:
                continue
            payload = json.loads((ROOT / sidecar).read_text(encoding="utf-8"))
            self.assertEqual(payload.get("processed_artifact"), entry["path"])

    def test_legacy_monetary_diagnostic_is_not_current_validation_input(self) -> None:
        registry = json.loads(
            (ROOT / "data/provenance/processed_data_inventory_registry.json").read_text(
                encoding="utf-8"
            )
        )
        entry = next(
            item for item in registry["entries"]
            if item["path"] == "data/processed/monetary_pass_through_bnr_2024_2025.csv"
        )
        self.assertEqual(entry["provenance_class"], "LEGACY_RECONCILED_BY_SUCCESSOR")
        self.assertEqual(
            entry["authorities"],
            ["model/calibration_validation/monetary_pass_through_legacy_processed_dataset_assessment_2026_09_22.json"],
        )
        assessment = json.loads((ROOT / entry["authorities"][0]).read_text(encoding="utf-8"))
        self.assertFalse(
            assessment["reconciliation"]["current_validation_recovery_consumes_historical_processed_artifact"]
        )
        self.assertEqual(
            assessment["successor_validation_boundary"]["canonical_input_root"],
            "data/raw/validation_recovery",
        )
        self.assertFalse(assessment["scientific_effect"]["validation_recovery_results_changed"])

    def test_processed_inventory_gate_is_exposed_in_local_reproduction_and_ci(self) -> None:
        command = "python scripts/audit_processed_data_inventory.py"
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        ci = (ROOT / ".github/workflows/scientific-ci.yml").read_text(encoding="utf-8")
        self.assertIn(command, readme)
        self.assertIn(command, ci)


if __name__ == "__main__":
    unittest.main()
