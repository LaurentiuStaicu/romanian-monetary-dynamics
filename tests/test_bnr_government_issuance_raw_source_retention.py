from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_bnr_government_issuance_raw_source_retention import (
    EXPECTED_BYTES,
    EXPECTED_SHA256,
    audit_bnr_raw_source_retention,
    file_sha256,
)

ROOT = Path(__file__).resolve().parents[1]


def load(path: str) -> dict:
    return json.loads((ROOT / path).read_text(encoding="utf-8"))


class BNRGovernmentIssuanceRawSourceRetentionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.manifest = load(
            "data/source_vintages/bnr-government-issuance-2025-vintage-2026-09-20/"
            "source_vintage_manifest.json"
        )
        self.acquisition = load(
            "model/dynamics/government_debt_issuance_bnr_raw_source_acquisition_contract.json"
        )
        self.retention = load(
            "model/dynamics/government_debt_issuance_bnr_raw_source_retention_assessment_2025.json"
        )
        self.snapshot = load(
            "model/dynamics/government_debt_issuance_bnr_pilot_2025.json"
        )
        self.materialisation = load(
            "model/dynamics/government_debt_issuance_materialisation_contract.json"
        )
        self.review = load(
            "model/dynamics/government_debt_issuance_source_boundary_review.json"
        )

    def audit(self, **overrides):
        return audit_bnr_raw_source_retention(
            overrides.get("manifest", self.manifest),
            overrides.get("acquisition", self.acquisition),
            overrides.get("retention", self.retention),
            overrides.get("snapshot", self.snapshot),
            overrides.get("materialisation", self.materialisation),
            overrides.get("review", self.review),
        )

    def test_current_retained_vintage_passes(self) -> None:
        self.assertEqual(self.audit(), [])

    def test_retained_pdf_matches_frozen_identity(self) -> None:
        raw_path = (
            ROOT
            / "data/source_vintages/bnr-government-issuance-2025-vintage-2026-09-20"
            / self.manifest["raw_source"]["path"]
        )
        self.assertEqual(raw_path.stat().st_size, EXPECTED_BYTES)
        self.assertEqual(file_sha256(raw_path), EXPECTED_SHA256)

    def test_hash_mutation_is_detected(self) -> None:
        mutated = copy.deepcopy(self.manifest)
        mutated["raw_source"]["sha256"] = "0" * 64
        errors = self.audit(manifest=mutated)
        self.assertTrue(
            any("manifest SHA-256 changed" in error for error in errors)
        )

    def test_raw_retention_does_not_promote_feedback(self) -> None:
        effect = self.retention["scientific_effect"]
        self.assertTrue(effect["raw_source_retention_blocker_closed"])
        self.assertFalse(effect["canonical_reference_mode_promoted"])
        self.assertFalse(effect["generic_government_debt_issuance_node_resolved"])
        self.assertFalse(effect["estimation_authorized"])
        self.assertFalse(effect["feedback_activation_authorized"])

    def test_manual_feedback_promotion_is_detected(self) -> None:
        mutated = copy.deepcopy(self.retention)
        mutated["scientific_effect"]["feedback_activation_authorized"] = True
        errors = self.audit(retention=mutated)
        self.assertTrue(
            any(
                "raw-source retention may not promote feedback_activation_authorized"
                in error
                for error in errors
            )
        )


if __name__ == "__main__":
    unittest.main()
