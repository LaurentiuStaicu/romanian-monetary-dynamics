from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCIENTIFIC_CI = ROOT / ".github" / "workflows" / "scientific-ci.yml"

DEDICATED = (
    (
        "model/dynamics/sectoral_financial_positions_eurostat_counterpart_probe_contract.json",
        ".github/workflows/sectoral-financial-positions-eurostat-counterpart-probe.yml",
        "probe-eurostat-counterpart-data",
    ),
    (
        "model/dynamics/sectoral_financial_positions_oecd_counterpart_probe_contract.json",
        ".github/workflows/sectoral-financial-positions-oecd-counterpart-probe.yml",
        "probe-oecd-counterpart-data",
    ),
)


class ManualLiveSourceDispatchBridgeTests(unittest.TestCase):
    def test_scientific_ci_is_dispatchable_but_hosts_no_live_provider_jobs(self) -> None:
        text = SCIENTIFIC_CI.read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("verify-baseline:", text)
        for forbidden in (
            "manual-eurostat-counterpart-probe:",
            "manual-oecd-counterpart-probe:",
            "manual-bnr-bls-missing-round-recovery:",
            "manual-oecd-nonconsolidated-topology-probe:",
            "manual-oecd-exact-reference-reconciliation:",
            "manual-oecd-semantic-adjusted-reference-reconciliation:",
            "manual-ecb-qfa-10m-horizontal-consistency-gate:",
            "audit/scientific-integrity-2026-09-18",
            "source-topology/oecd-nonconsolidated-sectoral-financial-positions-2026-09-21",
            "model/esa2010-s1m-f2-liability-semantic-gate-2026-09-21",
            "model/ecb-qfa-10m-horizontal-consistency-gate-2026-09-21",
        ):
            self.assertNotIn(forbidden, text)

    def test_counterpart_contracts_use_dedicated_manual_workflows(self) -> None:
        for relative, expected_workflow, expected_job in DEDICATED:
            contract = json.loads((ROOT / relative).read_text(encoding="utf-8"))
            policy = contract["execution_policy"]
            bridge = policy["manual_dispatch_bridge"]

            self.assertEqual(policy["trigger"], "workflow_dispatch")
            self.assertTrue(policy["live_source_refresh_manual_only"])
            self.assertTrue(policy["workflow_present_on_default_branch_now"])
            self.assertEqual(
                policy["current_execution_state"],
                "DEDICATED_WORKFLOW_DISPATCH_AVAILABLE_TRIGGER_CONDITIONED_HISTORICAL_REPLAY",
            )
            self.assertEqual(bridge["workflow"], expected_workflow)
            self.assertEqual(bridge["trigger"], "workflow_dispatch")
            self.assertEqual(bridge["job"], expected_job)
            self.assertTrue(bridge["workflow_exists_on_default_branch"])
            self.assertFalse(bridge["automatic_pull_request_or_push_execution"])

            workflow = (ROOT / expected_workflow).read_text(encoding="utf-8")
            self.assertIn("workflow_dispatch:", workflow)
            self.assertNotIn("pull_request:", workflow)

            historical = policy["historical_manual_rerun_bridge"]
            self.assertEqual(historical["status"], "RETIRED_2026-09-23")
            self.assertEqual(
                historical["workflow"],
                ".github/workflows/scientific-ci.yml",
            )
            self.assertEqual(
                historical["required_head_ref"],
                "audit/scientific-integrity-2026-09-18",
            )


    def test_completed_live_gates_have_one_acknowledged_manual_replay_workflow(self) -> None:
        relative = (
            ".github/workflows/"
            "sectoral-financial-positions-historical-live-gate-replay.yml"
        )
        text = (ROOT / relative).read_text(encoding="utf-8")
        self.assertIn("workflow_dispatch:", text)
        self.assertNotIn("pull_request:", text)
        self.assertIn("permissions:\n  contents: read", text)
        self.assertIn("acknowledge_no_scientific_reopen:", text)
        for script in (
            "audit_oecd_sectoral_financial_positions_nonconsolidated_probe.py",
            "audit_oecd_sectoral_financial_positions_exact_reconciliation.py",
            "audit_oecd_sectoral_financial_positions_semantic_adjusted_gate.py",
            "audit_ecb_qfa_10m_horizontal_consistency_gate.py",
        ):
            self.assertIn(f"scripts/{script}", text)


if __name__ == "__main__":
    unittest.main()
