from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_release_publication_authorization import audit_release_publication_authorization

ROOT = Path(__file__).resolve().parents[1]

class ReleasePublicationAuthorizationTests(unittest.TestCase):
    def test_current_release_publication_state_passes(self):
        self.assertEqual(audit_release_publication_authorization(), [])

    def test_v030_publication_is_recorded_and_authorization_consumed(self):
        auth=json.loads((ROOT/"model/registries/release_publication_authorization.json").read_text(encoding="utf-8"))
        self.assertFalse(auth["publication_authorized"])
        self.assertTrue(auth["trigger_consumed"])
        self.assertEqual(auth["publication_state"],"PUBLISHED_AND_AUTHORIZATION_CONSUMED")
        self.assertEqual(auth["release_version"],"0.3.0")
        self.assertEqual(auth["tag"],"v0.3.0")
        self.assertEqual(auth["exact_release_commit"],"33c11b7e10e7e837097da5b34a9251c7bedb3f2c")
        self.assertEqual(auth["published_at"],"2026-09-21T18:57:45Z")
        self.assertTrue((ROOT/auth["publication_record"]).is_file())

    def test_publication_record_matches_exact_release_commit(self):
        auth=json.loads((ROOT/"model/registries/release_publication_authorization.json").read_text(encoding="utf-8"))
        record=json.loads((ROOT/auth["publication_record"]).read_text(encoding="utf-8"))
        self.assertEqual(record["release_version"],"0.3.0")
        self.assertEqual(record["release_target_commit"],auth["exact_release_commit"])
        self.assertEqual(record["tag_target_commit"],auth["exact_release_commit"])
        self.assertEqual(record["release_id"],393215575)
        self.assertTrue(record["github_release_immutable"])
        self.assertEqual(record["publication_workflow_run_id"],35641755584)
        self.assertEqual(record["publication_workflow_conclusion"],"success")

    def test_release_has_no_scientific_activation_effect(self):
        auth=json.loads((ROOT/"model/registries/release_publication_authorization.json").read_text(encoding="utf-8"))
        self.assertTrue(all(v is False for v in auth["scientific_effect"].values()))

if __name__=="__main__":
    unittest.main()
