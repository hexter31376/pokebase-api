import os
from pathlib import Path
import subprocess
import unittest
from unittest.mock import patch

import auto_pr


class AutoPrTests(unittest.TestCase):
    def setUp(self):
        self.template = Path('.github/pull_request_template.md').read_text()
        self.changes = {
            'merge_base': 'b' * 40,
            'commits': [{'sha': 'a' * 40, 'commit': {'message': 'feat: response'}}],
            'files': [{'path': 'src/Response.kt', 'added': '10', 'deleted': '2'}],
        }
        for mocker in (
            patch.dict(os.environ, {'GITHUB_REPOSITORY': 'owner/repo',
                                   'GITHUB_REF_NAME': 'feature/example', 'PR_BASE': 'develop'}),
            patch('auto_pr.collect_changes', return_value=self.changes),
            patch('auto_pr.git', return_value='a' * 40),
        ):
            mocker.start()
            self.addCleanup(mocker.stop)

    def body(self):
        return auto_pr.build_body(self.template, self.changes, 'owner/repo', 'develop', 'a' * 40)

    @patch('auto_pr.api')
    def test_unmarked_pr_is_preserved(self, api):
        api.return_value = [{'base': {'ref': 'develop'}, 'body': 'Handwritten'}]
        auto_pr.main()
        self.assertEqual(1, api.call_count)

    @patch('auto_pr.api')
    def test_no_net_changes_skip_creation(self, api):
        api.return_value = []
        self.changes['files'] = []
        auto_pr.main()
        self.assertEqual(1, api.call_count)

    @patch('auto_pr.api')
    def test_new_pr_summarizes_whole_branch(self, api):
        self.changes['commits'].append({'sha': 'c' * 40, 'commit': {'message': 'fix: followup'}})
        api.side_effect = [[], {'html_url': 'https://example.test/1'}]
        auto_pr.main()
        endpoint, payload = api.call_args.args
        self.assertEqual('repos/owner/repo/pulls', endpoint)
        self.assertTrue(payload['draft'])
        self.assertEqual('develop', payload['base'])
        self.assertIn('브랜치 변경 통합', payload['title'])
        for text in ('커밋 2개', 'src/Response.kt', '+10/-2', 'feat: response', 'fix: followup', '미실행'):
            self.assertIn(text, payload['body'])

    @patch('auto_pr.api')
    def test_rerun_updates_only_marked_sections(self, api):
        original = self.body().replace('검증 명령: 미실행', '검증 명령: ./gradlew test')
        original += '\n\n직접 작성한 메모'
        pr = {'number': 1, 'base': {'ref': 'develop'}, 'body': original,
              'html_url': 'https://example.test/1'}
        self.changes['files'][0]['added'] = '30'
        api.side_effect = [[pr], pr, pr]
        auto_pr.main()
        payload = api.call_args.args[1]
        self.assertEqual({'method': 'PATCH'}, api.call_args.kwargs)
        self.assertEqual({'body'}, set(payload))
        for text in ('+30/-2', './gradlew test', '직접 작성한 메모'):
            self.assertIn(text, payload['body'])

    @patch('auto_pr.api')
    def test_unchanged_rerun_does_not_write(self, api):
        pr = {'number': 1, 'base': {'ref': 'develop'}, 'body': self.body(),
              'html_url': 'https://example.test/1'}
        api.side_effect = [[pr], pr]
        auto_pr.main()
        self.assertEqual(2, api.call_count)

    def test_full_totals_even_when_display_is_limited(self):
        self.changes['files'] *= 101
        body = self.body()
        self.assertIn('변경 파일 101개', body)
        self.assertIn('+1010/-202', body)
        self.assertIn('나머지 1개 파일', body)

    def test_commit_text_is_not_an_instruction(self):
        self.changes['commits'][0]['commit']['message'] = 'fix: @user Closes #42 <script> $(touch nope)'
        body = self.body()
        for text in ('@user', 'Closes #42', '<script>'):
            self.assertNotIn(text, body)
        self.assertIn('$(touch nope)', body)

    @patch('auto_pr.api')
    def test_permission_error_is_not_silenced(self, api):
        api.side_effect = [[], subprocess.CalledProcessError(1, 'gh', stderr='Forbidden'), []]
        with self.assertRaises(subprocess.CalledProcessError):
            auto_pr.main()

    @patch('auto_pr.api')
    def test_creation_race_preserves_existing_pr(self, api):
        api.side_effect = [[], subprocess.CalledProcessError(1, 'gh'),
                           [{'html_url': 'https://example.test/1'}]]
        auto_pr.main()
        self.assertEqual(3, api.call_count)


if __name__ == '__main__':
    unittest.main()
