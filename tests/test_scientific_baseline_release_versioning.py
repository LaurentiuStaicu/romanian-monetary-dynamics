from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ScientificBaselineReleaseVersioningTests(unittest.TestCase):
    def test_baseline_release_state_matches_canonical_contract(self) -> None:
        manifest = json.loads(
            (ROOT / "model/registries/scientific_baseline_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        contract = json.loads(
            (ROOT / "model/registries/release_versioning_contract.json").read_text(
                encoding="utf-8"
            )
        )
        state = manifest["canonical_state"]["release_versioning"]
        basis = contract["versioning_basis"]

        self.assertEqual(
            state["current_public_release"],
            basis["current_public_release"]["version"],
        )
        self.assertEqual(
            state["current_repository_version"],
            basis["current_repository_version"],
        )
        self.assertIs(
            state["unreleased_changes_present"],
            basis["unreleased_changes_present"],
        )
        self.assertIs(
            state["version_bump_required_now"],
            basis["version_bump_required_now"],
        )
        self.assertEqual(
            state["next_public_release_candidate"],
            basis["next_public_release_candidate"],
        )


if __name__ == "__main__":
    unittest.main()
