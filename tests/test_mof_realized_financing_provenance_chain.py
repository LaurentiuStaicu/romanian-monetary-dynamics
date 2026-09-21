from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class MoFRealizedFinancingProvenanceChainTests(unittest.TestCase):
    def test_contract_probe_vintage_assessment_chain(self) -> None:
        baseline = load("model/registries/scientific_baseline_manifest.json")
        contract = load(
            "model/dynamics/mof_realized_financing_channel_materialisation_contract_2026_09_21.json"
        )
        probe = load(
            "model/dynamics/mof_realized_financing_channel_source_vintage_probe_contract_2026_09_21.json"
        )
        assessment = load(
            "model/dynamics/mof_realized_financing_channel_source_vintage_assessment_2026_09_21.json"
        )
        vintage = load(
            "data/source_vintages/mof-realized-financing-channels-2025-vintage-2026-09-21/source_vintage_manifest.json"
        )

        probe_path = (
            "model/dynamics/"
            "mof_realized_financing_channel_source_vintage_probe_contract_2026_09_21.json"
        )
        contract_path = (
            "model/dynamics/"
            "mof_realized_financing_channel_materialisation_contract_2026_09_21.json"
        )
        vintage_path = (
            "data/source_vintages/"
            "mof-realized-financing-channels-2025-vintage-2026-09-21/"
            "source_vintage_manifest.json"
        )

        self.assertEqual(probe["governing_contract"], contract_path)
        self.assertEqual(contract["next_gate"]["id"], probe["probe_id"])
        self.assertEqual(vintage["probe_contract"], probe_path)
        self.assertEqual(vintage["governing_contract"], contract_path)
        self.assertEqual(assessment["probe_contract"], probe_path)
        self.assertEqual(assessment["governing_contract"], contract_path)
        self.assertEqual(assessment["source_vintage_manifest"], vintage_path)
        self.assertEqual(
            baseline["authority"][
                "mof_realized_financing_channel_source_vintage_probe_contract"
            ],
            probe_path,
        )
        self.assertEqual(
            baseline["authority"]["mof_realized_financing_channel_source_vintage_manifest"],
            vintage_path,
        )


if __name__ == "__main__":
    unittest.main()
