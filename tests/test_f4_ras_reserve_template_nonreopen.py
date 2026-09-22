from __future__ import annotations
import unittest
from scripts.audit_f4_ras_reserve_template_nonreopen import audit_f4_ras_reserve_template_nonreopen

class F4RASReserveTemplateNonreopenTests(unittest.TestCase):
    def test_ras_does_not_reopen_f4(self)->None:
        self.assertEqual(audit_f4_ras_reserve_template_nonreopen(),[])

if __name__=="__main__":
    unittest.main()
