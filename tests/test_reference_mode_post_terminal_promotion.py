from __future__ import annotations
import unittest
from scripts.audit_reference_mode_post_terminal_promotion import audit_reference_mode_post_terminal_promotion

class PostTerminalReferenceModePromotionTests(unittest.TestCase):
    def test_current_promotion_state(self):
        self.assertEqual(audit_reference_mode_post_terminal_promotion(),[])

if __name__=="__main__":
    unittest.main()
