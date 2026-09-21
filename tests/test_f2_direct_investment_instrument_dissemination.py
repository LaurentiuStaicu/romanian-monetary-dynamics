from __future__ import annotations
import unittest
from scripts.audit_f2_direct_investment_instrument_dissemination import (
    audit_f2_direct_investment_instrument_dissemination,
)

class F2DirectInvestmentInstrumentDisseminationTests(unittest.TestCase):
    def test_standard_dissemination_does_not_reopen_F2(self)->None:
        self.assertEqual(audit_f2_direct_investment_instrument_dissemination(),[])

if __name__=="__main__": unittest.main()
