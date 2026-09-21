from __future__ import annotations
import unittest
from scripts.audit_oecd_sectoral_financial_positions_semantic_adjusted_terminal import audit_semantic_terminal

class SemanticAdjustedTerminalTests(unittest.TestCase):
    def test_terminal_state_passes(self):
        self.assertEqual(audit_semantic_terminal(),[])

if __name__=="__main__": unittest.main()
