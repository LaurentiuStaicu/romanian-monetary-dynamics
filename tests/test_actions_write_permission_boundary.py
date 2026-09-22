from __future__ import annotations

import unittest

from scripts.audit_actions_write_permission_boundary import (
    ALLOWED_WRITE_WORKFLOWS,
    MOF_MANUAL_WRITE_WORKFLOWS,
    PUBLISHER,
    audit_actions_write_permission_boundary,
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


if __name__ == "__main__":
    unittest.main()
