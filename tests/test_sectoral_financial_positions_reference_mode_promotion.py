from __future__ import annotations
import unittest
from scripts.audit_sectoral_financial_positions_reference_mode_promotion import audit_reference_mode_promotion

class SectoralFinancialPositionsPromotionTests(unittest.TestCase):
    def test_promoted_reference_mode_state(self):
        self.assertEqual(audit_reference_mode_promotion(),[])

if __name__=="__main__":
    unittest.main()
