from __future__ import annotations
import unittest
from scripts.audit_oecd_sectoral_financial_positions_window_stability import audit_window_stability
class WindowStabilityTests(unittest.TestCase):
    def test_state(self):
        self.assertEqual(audit_window_stability(),[])
if __name__=="__main__": unittest.main()
