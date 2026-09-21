from __future__ import annotations

import unittest
from scripts.audit_oecd_sectoral_financial_positions_exact_row_gate import audit_oecd_exact_row_gate

class OecdExactRowGateTerminalTests(unittest.TestCase):
    def test_terminal_row_gate_state_passes(self):
        self.assertEqual(audit_oecd_exact_row_gate(),[])

if __name__=="__main__":
    unittest.main()
