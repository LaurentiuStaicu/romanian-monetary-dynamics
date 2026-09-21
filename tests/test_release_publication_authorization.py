from __future__ import annotations

import json
import unittest
from pathlib import Path

from scripts.audit_release_publication_authorization import audit_release_publication_authorization

ROOT = Path(__file__).resolve().parents[1]

class ReleasePublicationAuthorizationTests(unittest.TestCase):
    def test_current_release_publication_state_passes(self):
        self.assertEqual(audit_release_publication_authorization(), [])

    def test_v030_publication_is_one_shot_ci_gated(self):
        auth=json.loads((ROOT/"model/registries/release_publication_authorization.json").read_text(encoding="utf-8"))
        self.assertTrue(auth["publication_authorized"])
        self.assertFalse(auth["trigger_consumed"])
        self.assertEqual(auth["publication_state"],"READY_FOR_PUBLICATION_AFTER_GREEN_MAIN_CI")
        self.assertEqual(auth["release_version"],"0.3.0")
        self.assertEqual(auth["tag"],"v0.3.0")
        self.assertEqual(auth["intended_release_date"],"2026-09-21")
        self.assertEqual(auth["target_commit_strategy"],"SCIENTIFIC_CI_WORKFLOW_RUN_HEAD_SHA")
        self.assertNotIn("exact_release_commit",auth)
        self.assertNotIn("publication_record",auth)

    def test_current_public_release_is_not_advanced_before_tag_exists(self):
        contract=json.loads((ROOT/"model/registries/release_versioning_contract.json").read_text(encoding="utf-8"))
        basis=contract["versioning_basis"]
        self.assertEqual(basis["current_public_release"]["version"],"0.2.0")
        self.assertEqual(basis["current_repository_version"],"0.3.0")
        self.assertEqual(basis["next_public_release_candidate"],"0.3.0")
        self.assertEqual(basis["release_preparation"]["state"],"READY_FOR_PUBLICATION_AFTER_GREEN_MAIN_CI")

    def test_release_has_no_scientific_activation_effect(self):
        auth=json.loads((ROOT/"model/registries/release_publication_authorization.json").read_text(encoding="utf-8"))
        self.assertTrue(all(v is False for v in auth["scientific_effect"].values()))

if __name__=="__main__":
    unittest.main()
