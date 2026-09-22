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

    def test_manual_workflows_follow_terminal_reopen_policy(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        boundary = a["workflow_execution_boundary"]
        self.assertEqual(boundary["current_2025q2_candidate_count"], 0)
        self.assertFalse(boundary["manual_rerun_without_trigger_counts_as_scientific_progress"])
        self.assertFalse(boundary["manual_rerun_without_trigger_authorized_as_current_source_task"])
        self.assertFalse(boundary["workflow_rerun_may_mutate_canonical_panel"])

        recovery = json.loads(
            (ROOT / boundary["missing_round_recovery_contract"]).read_text(encoding="utf-8")
        )
        q2 = next(x for x in recovery["rounds"] if x["quarter"] == "2025-Q2")
        self.assertEqual(q2["url_candidates"], [])

        may_probe = (ROOT / boundary["may2025_identity_probe_workflow"]).read_text(
            encoding="utf-8"
        )
        missing_recovery = (
            ROOT / boundary["missing_round_recovery_workflow"]
        ).read_text(encoding="utf-8")
        self.assertIn("HISTORICAL MAY-2025 XLSX IDENTITY RE-PROBE ONLY", may_probe)
        self.assertIn("not a new BLS vintage", may_probe)
        self.assertIn("HISTORICAL PREREGISTERED-CANDIDATE REPLAY", missing_recovery)
        self.assertIn("unchanged rerun is not scientific progress", missing_recovery)


if __name__ == "__main__":
    unittest.main()
