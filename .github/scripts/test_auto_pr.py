import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import auto_pr


class AutoPrTests(unittest.TestCase):
    def setUp(self):
        self.environment = patch.dict(os.environ, {
            "GITHUB_REPOSITORY": "owner/repo",
            "GITHUB_REF_NAME": "feature/example",
            "GITHUB_SHA": "a" * 40,
            "PR_BASE": "develop",
        })
        self.environment.start()
        self.addCleanup(self.environment.stop)

    @patch("auto_pr.api")
    def test_existing_pr_is_not_modified(self, api):
        api.return_value = [{"html_url": "https://example.test/pr/1"}]
        auto_pr.main()
        self.assertEqual(api.call_count, 1)

    @patch("auto_pr.api")
    def test_no_changes_skip_creation(self, api):
        api.side_effect = [[], {"ahead_by": 0}]
        auto_pr.main()
        self.assertEqual(api.call_count, 2)

    @patch("auto_pr.api")
    def test_new_pr_is_draft_and_retains_unverified_status(self, api):
        commit = {"sha": "a" * 40, "commit": {"message": "feat: response $(touch nope)\n\nCloses #42"}}
        api.side_effect = [[], {"ahead_by": 1, "total_commits": 1, "commits": [commit]},
                           commit, {"html_url": "https://example.test/pr/2"}]
        auto_pr.main()
        endpoint, payload = api.call_args.args
        self.assertEqual(endpoint, "repos/owner/repo/pulls")
        self.assertTrue(payload["draft"])
        self.assertEqual(payload["base"], "develop")
        self.assertEqual(payload["head"], "feature/example")
        self.assertIn("미실행", payload["body"])
        self.assertNotIn("Closes #42", payload["body"])
        self.assertIn("$(touch nope)", payload["title"])

    @patch("auto_pr.api")
    def test_non_feature_branch_is_ignored(self, api):
        os.environ["GITHUB_REF_NAME"] = "main"
        auto_pr.main()
        api.assert_not_called()

    def test_commit_mentions_are_not_published_as_notifications(self):
        template = Path(".github/pull_request_template.md").read_text()
        body = auto_pr.build_body(template, [{"sha": "abc1234", "commit": {
            "message": "fix: @someone Closes #42 <script>"
        }}], 1)
        self.assertNotIn("@someone", body)
        self.assertNotIn("Closes #42", body)
        self.assertNotIn("<script>", body)

    @patch("auto_pr.api")
    def test_permission_failure_is_not_silenced(self, api):
        commit = {"sha": "a" * 40, "commit": {"message": "feat: example"}}
        api.side_effect = [[], {"ahead_by": 1, "total_commits": 1, "commits": [commit]},
                           commit, subprocess.CalledProcessError(1, "gh", stderr="Forbidden"), []]
        with self.assertRaises(subprocess.CalledProcessError):
            auto_pr.main()

    @patch("auto_pr.api")
    def test_concurrent_manual_pr_creation_is_preserved(self, api):
        commit = {"sha": "a" * 40, "commit": {"message": "feat: example"}}
        api.side_effect = [[], {"ahead_by": 1, "total_commits": 1, "commits": [commit]},
                           commit, subprocess.CalledProcessError(1, "gh"),
                           [{"html_url": "https://example.test/pr/3"}]]
        auto_pr.main()
        self.assertEqual(api.call_count, 5)


if __name__ == "__main__":
    unittest.main()
