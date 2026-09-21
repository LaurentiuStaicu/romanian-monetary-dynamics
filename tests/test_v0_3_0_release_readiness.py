from __future__ import annotations

import json
import unittest
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]

class V030ReleaseReadinessTests(unittest.TestCase):
    def test_release_readiness_preserves_scientific_nonclaims(self)->None:
        a=json.loads((ROOT/"model/registries/v0_3_0_release_readiness_assessment_2026_09_21.json").read_text(encoding="utf-8"))
        self.assertEqual(a["release_classification"]["selected_version"],"0.3.0")
        self.assertEqual(a["milestone_state"]["required_reference_modes_ready"],10)
        self.assertEqual(a["milestone_state"]["required_reference_modes_total"],10)
        self.assertEqual(a["milestone_state"]["accounting_recovery_stage"],"STAGE_COMPLETE_EVIDENCE_TRIGGERED_HOLD")
        self.assertFalse(a["milestone_state"]["model_complete"])
        self.assertEqual(a["milestone_state"]["validated_reference_behavioural_mechanisms"],0)
        self.assertEqual(a["milestone_state"]["quantitative_feedback_structures_active"],0)
        self.assertEqual(a["milestone_state"]["behavioural_closure"],"INACTIVE")
        self.assertEqual(a["decision"],"PREPARE_V0_3_0_AND_PUBLISH_ONLY_AFTER_EXACT_MAIN_RELEASE_COMMIT_PASSES_SCIENTIFIC_CI")

if __name__=="__main__":
    unittest.main()
