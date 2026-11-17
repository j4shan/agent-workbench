"""Exercise reviewer configuration and the real shared wrapper with a stub runtime."""

import json
import os
from pathlib import Path
import shutil
import re
import shlex
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import review


class ReviewTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='bundled review ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.config = self.root / 'role files'
        self.config.mkdir()
        self.role = self.config / 'code-reviewer.json'
        self.role.write_text('["review-model","high"]\n')
        self.bin = self.root / 'bin files'
        self.bin.mkdir()
        self.wrapper = self.bin / 'gpt-exec'
        shutil.copy2(SCRIPTS.parents[2] / 'tools/gpt-exec.sh', self.wrapper)
        self.wrapper.chmod(0o755)
        self.capture = self.root / 'capture.json'
        stub = self.bin / 'codex'
        stub.write_text('#!' + sys.executable + '\nimport json,os,sys,time\nfrom pathlib import Path\n' +
            'Path(os.environ["TEST_CAPTURE"]).write_text(json.dumps({"args":sys.argv[1:],"stdin":sys.stdin.read(),"pid":os.getpid()}))\n' +
            'if os.environ.get("TEST_HOLD"): time.sleep(30)\n' +
            'sys.exit(int(os.environ.get("TEST_EXIT","0")))\n')
        stub.chmod(0o755)
        self.prompt = self.root / 'review request.txt'
        self.prompt.write_text('PRIVATE REVIEW REQUEST\n')
        self.env = dict(os.environ, SUBAGENT_MODELS_DIR=str(self.config),
                        PATH=str(self.bin) + os.pathsep + os.environ['PATH'], TEST_CAPTURE=str(self.capture))
        self.args = [sys.executable, str(SCRIPTS / 'review.py'), '--project', str(self.root),
                     '--prompt-file', str(self.prompt), '--gpt-exec', str(self.wrapper)]

    def run_review(self, *options, env=None, **kwargs):
        return subprocess.run([*self.args, *options], env=env or self.env,
                              capture_output=True, text=True, timeout=5, **kwargs)

    def test_load_settings_rereads_each_call_and_preserves_unspecified_field(self):
        with patch.dict(os.environ, self.env):
            self.assertEqual(review.load_review_settings(), ('review-model', 'high'))
            self.assertEqual(review.load_review_settings(model='override'), ('override', 'high'))
            self.assertEqual(review.load_review_settings(reasoning_effort='low'), ('review-model', 'low'))
            self.role.write_text('["new-model","medium"]')
            self.assertEqual(review.load_review_settings(), ('new-model', 'medium'))
        self.assertEqual(self.role.read_text(), '["new-model","medium"]')

    def test_invalid_configuration_does_not_launch_or_echo_contents(self):
        for text in ['secret-invalid-json', '{}', '["m"]', '["m","high",null]',
                     '["m",3]', '["","high"]', '["m","bad effort"]']:
            with self.subTest(text=text):
                self.role.write_text(text)
                result = self.run_review()
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('secret-invalid-json', result.stderr)
                self.assertFalse(self.capture.exists())
                self.assertEqual(self.role.read_text(), text)

    def test_missing_configuration_and_invalid_directory_never_fall_back(self):
        self.role.unlink()
        result = self.run_review('--model', 'override', '--reasoning-effort', 'low')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('configuration is missing', result.stderr)
        for directory in ['', 'relative']:
            result = self.run_review(env=dict(self.env, SUBAGENT_MODELS_DIR=directory))
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('absolute', result.stderr)
        self.assertFalse(self.capture.exists())

    def test_read_only_wrapper_receives_settings_and_finite_input(self):
        read_fd, write_fd = os.pipe()
        try:
            result = self.run_review(stdin=read_fd)
        finally:
            os.close(read_fd)
            os.close(write_fd)
        self.assertEqual(result.returncode, 0, result.stderr)
        recorded = json.loads(self.capture.read_text())
        self.assertEqual(recorded['stdin'], self.prompt.read_text())
        self.assertEqual(recorded['args'], ['exec', '--ephemeral', '--model', 'review-model',
            '--config', 'model_reasoning_effort="high"', '--sandbox', 'read-only',
            '--cd', str(self.root.resolve()), '-'])
        self.assertNotIn('PRIVATE REVIEW REQUEST', result.stderr)

    def test_overrides_output_options_and_status_do_not_change_preferences(self):
        before = self.role.read_bytes()
        result = self.run_review('--model', 'override-model', '--reasoning-effort', 'low', '--json',
                                 '--output-last-message', str(self.root / 'final.txt'),
                                 env=dict(self.env, TEST_EXIT='19'))
        self.assertEqual(result.returncode, 19, result.stderr)
        args = json.loads(self.capture.read_text())['args']
        self.assertIn('override-model', args)
        self.assertIn('model_reasoning_effort="low"', args)
        self.assertIn('--json', args)
        self.assertIn('--output-last-message', args)
        self.assertEqual(self.role.read_bytes(), before)

    def test_documented_review_command_runs_the_bundled_helper(self):
        skill = (SCRIPTS.parent / 'SKILL.md').read_text()
        command = next(block for block in re.findall(r'```bash\n(.*?)\n```', skill, re.S)
                       if 'scripts/review.py' in block)
        command = command.replace('.agents/skills/execution-planning/scripts/review.py',
                                  shlex.quote(str(SCRIPTS / 'review.py')))
        command = command.replace('"/absolute/path/to/code-review-request.txt"', shlex.quote(str(self.prompt)))
        command += ' --gpt-exec ' + shlex.quote(str(self.wrapper))
        result = subprocess.run(['/bin/bash', '-c', command], cwd=self.root, env=self.env,
                                capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(self.capture.read_text())['stdin'], self.prompt.read_text())

    def test_missing_tool_invalid_overrides_and_permission_escalation_are_rejected(self):
        for options in [('--gpt-exec', str(self.root / 'missing')), ('--gpt-exec', 'relative'),
                        ('--model', '$(touch bad)'), ('--reasoning-effort', ''),
                        ('--sandbox', 'workspace-write')]:
            with self.subTest(options=options):
                result = self.run_review(*options)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.capture.exists())

    def test_process_identity_and_cancellation_are_preserved(self):
        process = subprocess.Popen(self.args, env=dict(self.env, TEST_HOLD='1'),
                                   stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 5
            while not self.capture.exists():
                self.assertIsNone(process.poll())
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.01)
            recorded = json.loads(self.capture.read_text())
            self.assertEqual(recorded['pid'], process.pid)
            process.terminate()
            process.communicate(timeout=3)
            self.assertEqual(process.returncode, -signal.SIGTERM)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()


if __name__ == '__main__':
    unittest.main()
