from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_actions_write_permission_boundary import (
    ALLOWED_WRITE_WORKFLOWS,
    audit_actions_write_permission_boundary,
    workflow_paths,
    workflow_uses_pull_request_target,
)

ROOT = Path(__file__).resolve().parents[1]
ASSESSMENT = (
    ROOT
    / "model"
    / "registries"
    / "repository_execution_governance_terminal_assessment_2026_09_24.json"
)


class RepositoryExecutionGovernanceTerminalAssessmentTests(unittest.TestCase):
    def setUp(self) -> None:
        self.a = json.loads(ASSESSMENT.read_text(encoding="utf-8"))

    def test_terminal_decision_and_hardening_series_are_frozen(self) -> None:
        self.assertEqual(
            self.a["terminal_state"]["status"],
            "REPOSITORY_EXECUTION_GOVERNANCE_HARDENING_COMPLETE_CURRENT_SCOPE_NO_ACTIVE_REPAIR_TASK",
        )
        self.assertEqual(
            self.a["decision"],
            "CLOSE_REPOSITORY_EXECUTION_GOVERNANCE_HARDENING_AT_CURRENT_SCOPE_REOPEN_ONLY_ON_DECLARED_TRIGGER",
        )
        self.assertEqual(
            self.a["hardening_series"]["pull_requests"],
            list(range(213, 225)),
        )
        self.assertEqual(
            self.a["evidence_base_through_commit"],
            "c5b890483db8398807264b39341c80bfd61dfdc2",
        )

    def test_current_actions_surface_matches_closure_snapshot(self) -> None:
        state = self.a["terminal_state"]
        paths = workflow_paths()
        self.assertEqual(audit_actions_write_permission_boundary(), [])
        self.assertEqual(len(paths), state["workflow_count_at_closure"])
        self.assertEqual(
            len(ALLOWED_WRITE_WORKFLOWS),
            state["write_capable_workflow_count_at_closure"],
        )
        self.assertEqual(
            sum(
                workflow_uses_pull_request_target(path.read_text(encoding="utf-8"))
                for path in paths
            ),
            state["pull_request_target_workflow_count_at_closure"],
        )
        self.assertTrue(state["explicit_top_level_permissions_required"])
        self.assertTrue(state["pull_request_target_forbidden_repository_wide"])
        self.assertTrue(state["scientific_ci_offline_on_pull_request_and_push"])
        self.assertTrue(state["pull_request_direct_provider_access_forbidden"])
        self.assertTrue(state["audit_scripts_require_workflow_execution_path"])

    def test_model_contract_and_baseline_register_same_terminal_authority(self) -> None:
        model = json.loads(
            (ROOT / "model/registries/model_contract.json").read_text(encoding="utf-8")
        )
        baseline = json.loads(
            (ROOT / "model/registries/scientific_baseline_manifest.json").read_text(
                encoding="utf-8"
            )
        )
        expected = (
            "model/registries/"
            "repository_execution_governance_terminal_assessment_2026_09_24.json"
        )
        self.assertEqual(
            model["repository_governance"]["execution_governance_terminal_assessment"],
            expected,
        )
        self.assertEqual(
            baseline["authority"][
                "repository_execution_governance_terminal_assessment"
            ],
            expected,
        )
        self.assertTrue((ROOT / expected).is_file())

    def test_declared_authorities_exist(self) -> None:
        for key, relative in self.a["authorities"].items():
            self.assertTrue((ROOT / relative).is_file(), key)

    def test_closure_has_no_scientific_or_release_activation_effect(self) -> None:
        disposition = self.a["current_disposition"]
        self.assertEqual(
            disposition["next_operational_state"],
            "EVIDENCE_TRIGGERED_BASELINE_HOLD",
        )
        self.assertFalse(
            disposition["repeated_execution_governance_reaudit_without_trigger_is_progress"]
        )
        self.assertFalse(disposition["new_execution_governance_rule_required_now"])
        self.assertIsNone(disposition["active_execution_governance_repair_task"])
        self.assertFalse(disposition["live_refetch_authorized_by_this_assessment"])
        self.assertFalse(disposition["estimation_or_refit_authorized"])
        self.assertFalse(disposition["holdout_opening_authorized"])
        self.assertFalse(disposition["feedback_activation_authorized"])
        self.assertFalse(disposition["behavioural_closure_authorized"])
        self.assertFalse(disposition["version_bump_required"])


if __name__ == "__main__":
    unittest.main()
