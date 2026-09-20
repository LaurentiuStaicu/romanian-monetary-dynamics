from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.promote_mof_announced_RON_primary_reference_auction_recovered_official_pdfs import (
    BASELINE_RETAINED,
    CONTRACT_PATH,
    MANIFEST_PATH,
    RECOVERED,
    UNRESOLVED,
    verify_manifest_state,
)

ROOT = Path(__file__).resolve().parents[1]


class MOFRecoveredOfficialPDFPromotionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.contract = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
        self.manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
        self.docs = {item["source_id"]: item for item in self.contract["documents"]}

    def test_transition_partition_is_exactly_4_plus_5_plus_3(self) -> None:
        self.assertEqual(len(BASELINE_RETAINED), 4)
        self.assertEqual(len(RECOVERED), 5)
        self.assertEqual(len(UNRESOLVED), 3)
        self.assertFalse(BASELINE_RETAINED & RECOVERED)
        self.assertFalse(BASELINE_RETAINED & UNRESOLVED)
        self.assertFalse(RECOVERED & UNRESOLVED)
        self.assertEqual(
            BASELINE_RETAINED | RECOVERED | UNRESOLVED,
            {item["source_id"] for item in self.contract["documents"]},
        )

    def test_manifest_is_exactly_pre_or_post_recovery_state(self) -> None:
        state = verify_manifest_state(self.manifest, self.contract)
        self.assertIn(state, {"PRE_RECOVERY_4", "POST_RECOVERY_9"})

    def test_recovered_contract_entries_freeze_url_profile_and_probe_sha(self) -> None:
        for source_id in RECOVERED:
            doc = self.docs[source_id]
            self.assertTrue(doc["known_official_pdf_url"].startswith("https://"))
            self.assertIn(
                doc["official_pdf_identity_profile"],
                {
                    "MINISTRY_PROSPECT_PDF_WITH_FROZEN_LEGAL_METADATA",
                    "LEGAL_PUBLICATION_PDF",
                },
            )
            self.assertRegex(
                doc["recovery_probe_expected_pdf_sha256"],
                r"^[0-9a-f]{64}$",
            )

    def test_unresolved_sources_remain_without_frozen_pdf_recovery(self) -> None:
        for source_id in UNRESOLVED:
            doc = self.docs[source_id]
            self.assertIsNone(doc.get("known_official_pdf_url"))
            self.assertIsNone(doc.get("recovery_probe_expected_pdf_sha256"))

    def test_recovery_does_not_change_model_scientific_permissions(self) -> None:
        rules = self.contract["hard_rules"]
        self.assertTrue(rules["no_canonical_reference_mode_promotion"])
        self.assertTrue(rules["no_yield_effect_estimation"])
        self.assertTrue(rules["no_feedback_activation"])
        self.assertTrue(rules["no_behavioural_closure_change"])
        self.assertTrue(rules["no_public_version_change"])


if __name__ == "__main__":
    unittest.main()
