from __future__ import annotations

import unittest

from scripts.audit_actions_write_permission_boundary import (
    ALLOWED_WRITE_WORKFLOWS,
    MOF_MANUAL_WRITE_WORKFLOWS,
    PUBLISHER,
    audit_actions_write_permission_boundary,
    workflow_uses_pull_request_target,
)


class ActionsWritePermissionBoundaryTests(unittest.TestCase):
    def test_current_actions_write_boundary_passes(self) -> None:
        self.assertEqual(audit_actions_write_permission_boundary(), [])

    def test_allowlist_is_explicit_and_narrow(self) -> None:
        self.assertEqual(
            ALLOWED_WRITE_WORKFLOWS,
            MOF_MANUAL_WRITE_WORKFLOWS | {PUBLISHER},
        )
        self.assertEqual(len(MOF_MANUAL_WRITE_WORKFLOWS), 3)
        self.assertEqual(len(ALLOWED_WRITE_WORKFLOWS), 4)

    def test_all_workflows_declare_permissions_explicitly(self) -> None:
        self.assertEqual(audit_actions_write_permission_boundary(), [])


    def test_pull_request_target_detection_is_explicit_and_comment_safe(self) -> None:
        self.assertTrue(
            workflow_uses_pull_request_target(
                "on:\n  pull_request_target:\npermissions:\n  contents: read\njobs:\n"
            )
        )
        self.assertTrue(
            workflow_uses_pull_request_target(
                "on: [push, pull_request_target]\npermissions:\n  contents: read\njobs:\n"
            )
        )
        self.assertFalse(
            workflow_uses_pull_request_target(
                "on:\n  pull_request:\n# pull_request_target is intentionally forbidden\n"
                "permissions:\n  contents: read\njobs:\n"
            )
        )

if __name__ == "__main__":
    unittest.main()
