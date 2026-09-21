from __future__ import annotations

import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-authorized-release.yml"

class ReleasePublicationWorkflowTests(unittest.TestCase):
    def test_publication_is_green_main_ci_gated(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("workflow_run:",text)
        self.assertIn("Scientific CI",text)
        self.assertIn("github.event.workflow_run.conclusion == 'success'",text)
        self.assertIn("github.event.workflow_run.event == 'push'",text)
        self.assertIn("github.event.workflow_run.head_branch == 'main'",text)

    def test_publication_uses_exact_green_sha(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("github.event.workflow_run.head_sha",text)
        self.assertIn('RELEASE_SHA:',text)
        self.assertIn('--target "$RELEASE_SHA"',text)

    def test_existing_tag_is_never_moved(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("refusing to move it",text)
        self.assertNotIn("git tag -f",text)
        self.assertNotIn("git push -f",text)

    def test_workflow_requires_contents_write_only_for_publication(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        self.assertIn("permissions:",text)
        self.assertIn("contents: write",text)
        self.assertIn("audit_release_publication_authorization.py",text)

if __name__=="__main__":
    unittest.main()
