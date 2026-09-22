from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ProvenanceGovernanceParityTests(unittest.TestCase):
    def test_model_contract_and_baseline_register_same_provenance_authorities(self) -> None:
        model = json.loads(
            (ROOT / "model/registries/model_contract.json").read_text(encoding="utf-8")
        )
        baseline = json.loads(
            (ROOT / "model/registries/scientific_baseline_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        governance = model["repository_governance"]
        authority = baseline["authority"]

        self.assertEqual(
            governance["source_vintage_inventory_registry"],
            authority["source_vintage_inventory_registry"],
        )
        self.assertEqual(
            governance["processed_data_inventory_registry"],
            authority["processed_data_inventory"],
        )
        self.assertEqual(
            governance["validation_recovery_vintage_status"],
            authority["validation_recovery_vintage_status"],
        )

    def test_all_registered_provenance_governance_authorities_exist(self) -> None:
        model = json.loads(
            (ROOT / "model/registries/model_contract.json").read_text(encoding="utf-8")
        )
        governance = model["repository_governance"]
        for key in (
            "source_vintage_inventory_registry",
            "processed_data_inventory_registry",
            "validation_recovery_vintage_status",
        ):
            self.assertTrue((ROOT / governance[key]).is_file(), key)


if __name__ == "__main__":
    unittest.main()
