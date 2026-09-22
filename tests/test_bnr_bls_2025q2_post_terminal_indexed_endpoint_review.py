from __future__ import annotations

import copy
import json
import unittest
from pathlib import Path

from scripts.audit_bnr_bls_2025q2_post_terminal_indexed_endpoint_review import (
    ASSESSMENT_PATH,
    audit_bnr_bls_2025q2_post_terminal_indexed_endpoint_review,
)

ROOT = Path(__file__).resolve().parents[1]


class BnrBls2025Q2PostTerminalIndexedEndpointReviewTests(unittest.TestCase):
    def test_current_review_passes(self) -> None:
        self.assertEqual(
            audit_bnr_bls_2025q2_post_terminal_indexed_endpoint_review(),
            [],
        )

    def test_opaque_endpoint_is_not_promoted_by_extension_or_domain(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        self.assertTrue(a["newly_observed_public_evidence"]["official_domain"])
        self.assertTrue(a["newly_observed_public_evidence"]["exact_url"].endswith(".xlsx"))
        self.assertFalse(a["semantic_adjudication"]["official_domain_plus_xlsx_extension_is_sufficient_identity"])
        self.assertFalse(a["semantic_adjudication"]["exact_2025q2_bls_workbook_identity_established"])
        self.assertFalse(a["semantic_adjudication"]["trigger_condition_satisfied"])

    def test_panel_remains_frozen_11_of_12(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        self.assertTrue(a["disposition"]["canonical_panel_remains_11_of_12"])
        self.assertEqual(a["disposition"]["missing_round_remains"], "2025-Q2")
        self.assertFalse(a["disposition"]["canonical_panel_mutation_authorized"])


if __name__ == "__main__":
    unittest.main()
