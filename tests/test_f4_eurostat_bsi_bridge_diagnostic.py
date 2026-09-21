from __future__ import annotations

import unittest

from scripts.audit_f4_eurostat_bsi_bridge_diagnostic import (
    audit_f4_eurostat_bsi_bridge_diagnostic,
)


class F4EurostatBSIBridgeDiagnosticTests(unittest.TestCase):
    def test_rejected_cross_domain_bridge_is_reproducible(self) -> None:
        self.assertEqual(audit_f4_eurostat_bsi_bridge_diagnostic(), [])


if __name__ == "__main__":
    unittest.main()
