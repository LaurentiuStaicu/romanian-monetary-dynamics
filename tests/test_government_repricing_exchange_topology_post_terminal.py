from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_government_repricing_exchange_topology_post_terminal import (
    ASSESSMENT_PATH,
    audit_government_repricing_exchange_topology_post_terminal,
)

ROOT = Path(__file__).resolve().parents[1]


class GovernmentRepricingExchangeTopologyPostTerminalTests(unittest.TestCase):
    def test_current_exchange_topology_review_passes(self) -> None:
        self.assertEqual(
            audit_government_repricing_exchange_topology_post_terminal(),
            [],
        )

    def test_topology_does_not_promote_realized_ledger_fields(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        discovery = a["source_discovery_result"]
        self.assertTrue(discovery["topology_old_to_new_observed"])
        self.assertFalse(discovery["official_realized_exchange_result_identified_reproducibly"])
        self.assertFalse(discovery["official_realized_accepted_old_principal_by_isin_identified"])
        self.assertFalse(discovery["same_date_opening_outstanding_principal_by_old_isin_identified"])

    def test_gate_1_and_candidate_eligibility_remain_closed(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        adjudication = a["contract_adjudication"]
        self.assertEqual(adjudication["gate_1_status"], "FAIL_UNCHANGED")
        self.assertFalse(adjudication["candidate_eligibility"])
        self.assertFalse(a["current_disposition"]["canonical_government_repricing_ledger_mutation_authorized"])

    def test_secondary_locator_values_are_not_canonical(self) -> None:
        a = json.loads((ROOT / ASSESSMENT_PATH).read_text(encoding="utf-8"))
        self.assertFalse(a["secondary_locator_only"]["canonical_evidence"])
        self.assertFalse(a["contract_adjudication"]["secondary_reported_nominal_or_yield_may_enter_ledger"])


if __name__ == "__main__":
    unittest.main()
