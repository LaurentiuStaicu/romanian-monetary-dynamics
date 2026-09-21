from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_release_publication_authorization import audit_release_publication_authorization

ROOT = Path(__file__).resolve().parents[1]

class ReleasePublicationAuthorizationTests(unittest.TestCase):
    def test_current_release_publication_authorization_passes(self):
        self.assertEqual(audit_release_publication_authorization(), [])

    def test_authorized_release_notes_exist(self):
        auth=json.loads((ROOT/"model/registries/release_publication_authorization.json").read_text(encoding="utf-8"))
        self.assertTrue((ROOT/auth["release_notes_path"]).is_file())
        self.assertTrue(auth["publication_authorized"])
        self.assertEqual(auth["release_version"],"0.2.0")
        self.assertEqual(auth["tag"],"v0.2.0")

    def test_release_has_no_scientific_activation_effect(self):
        auth=json.loads((ROOT/"model/registries/release_publication_authorization.json").read_text(encoding="utf-8"))
        self.assertTrue(all(v is False for v in auth["scientific_effect"].values()))

if __name__=="__main__":
    unittest.main()
