from __future__ import annotations
import unittest
from scripts.audit_oecd_sectoral_financial_positions_decimal_arithmetic_correction import audit_decimal_correction

class OecdDecimalArithmeticCorrectionTests(unittest.TestCase):
    def test_decimal_correction_state(self):
        self.assertEqual(audit_decimal_correction(),[])

if __name__=="__main__":
    unittest.main()
