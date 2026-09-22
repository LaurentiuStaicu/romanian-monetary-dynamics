from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.verify_validation_recovery_provenance import (
    verify_repository_validation_inputs,
)

ROOT = Path(__file__).resolve().parents[1]


class ValidationRecoveryRepositoryInputIdentityTests(unittest.TestCase):
    def test_repository_validation_inputs_are_exactly_pinned(self) -> None:
        registry = json.loads(
            (ROOT / "data/provenance/validation_recovery_vintage_status.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(len(registry["vintages"]), 1)
        verify_repository_validation_inputs(registry["vintages"][0])

    def test_validation_provenance_verifier_is_exposed_in_local_reproduction_and_ci(self) -> None:
        command = "python scripts/verify_validation_recovery_provenance.py"
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        ci = (ROOT / ".github/workflows/scientific-ci.yml").read_text(encoding="utf-8")
        self.assertIn(command, readme)
        self.assertIn(command, ci)


if __name__ == "__main__":
    unittest.main()
