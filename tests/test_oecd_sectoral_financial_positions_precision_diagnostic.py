from __future__ import annotations
import unittest
from scripts.audit_oecd_sectoral_financial_positions_precision_diagnostic import audit_oecd_precision_diagnostic

class OecdPrecisionDiagnosticTests(unittest.TestCase):
    def test_precision_diagnostic_terminal_state(self):
        self.assertEqual(audit_oecd_precision_diagnostic(),[])

if __name__=="__main__":
    unittest.main()
