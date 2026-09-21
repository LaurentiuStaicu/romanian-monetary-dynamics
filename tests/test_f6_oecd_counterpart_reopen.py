from __future__ import annotations
import unittest
from scripts.audit_f6_oecd_counterpart_reopen import audit_f6_oecd_counterpart_reopen

class F6OECDCounterpartReopenTests(unittest.TestCase):
    def test_topology_trigger_and_stage2_preregistration(self)->None:
        self.assertEqual(audit_f6_oecd_counterpart_reopen(),[])

if __name__=="__main__": unittest.main()
