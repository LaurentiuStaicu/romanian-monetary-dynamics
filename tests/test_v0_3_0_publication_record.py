from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class V030PublicationRecordTests(unittest.TestCase):
    def test_immutable_publication_identity(self)->None:
        r=json.loads((ROOT/"model/registries/v0_3_0_release_publication_record_2026_09_21.json").read_text(encoding="utf-8"))
        self.assertEqual(r["release_version"],"0.3.0")
        self.assertEqual(r["tag"],"v0.3.0")
        self.assertEqual(r["release_target_commit"],"33c11b7e10e7e837097da5b34a9251c7bedb3f2c")
        self.assertEqual(r["tag_target_commit"],r["release_target_commit"])
        self.assertEqual(r["release_id"],393215575)
        self.assertTrue(r["github_release_immutable"])
        self.assertEqual(r["publication_workflow_conclusion"],"success")
        self.assertFalse(r["historical_release_mutation"])
        self.assertTrue(all(v is False for v in r["scientific_effect"].values()))

if __name__=="__main__":
    unittest.main()
