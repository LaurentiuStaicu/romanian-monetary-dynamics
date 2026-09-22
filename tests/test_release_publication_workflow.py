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

    def test_workflow_scopes_write_permission_to_authorized_publish_job(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        header, jobs = text.split("jobs:", 1)
        check, publish = jobs.split("  publish-release:", 1)

        self.assertIn("permissions:", header)
        self.assertIn("contents: read", header)
        self.assertNotIn("contents: write", header)

        self.assertIn("  check-authorization:", jobs)
        self.assertNotIn("contents: write", check)
        self.assertIn("authorized: ${{ steps.auth.outputs.authorized }}", check)

        self.assertIn("needs: check-authorization", publish)
        self.assertIn(
            "if: needs.check-authorization.outputs.authorized == 'true'",
            publish,
        )
        self.assertIn("permissions:", publish)
        self.assertIn("contents: write", publish)
        self.assertIn("audit_release_publication_authorization.py", publish)

    def test_authorization_metadata_flows_from_read_job_to_publish_job(self):
        text=WORKFLOW.read_text(encoding="utf-8")
        for key in ("tag", "title", "notes"):
            self.assertIn(f"{key}: ${{{{ steps.auth.outputs.{key} }}}}", text)
            self.assertIn(
                f"${{{{ needs.check-authorization.outputs.{key} }}}}",
                text,
            )

if __name__=="__main__":
    unittest.main()
