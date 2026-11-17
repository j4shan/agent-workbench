#!/bin/bash
set -euo pipefail
export TOOL_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
exec python3 - <<'PY'
import json
import os
from pathlib import Path
import signal
import stat
import subprocess
import tempfile
import time
import unittest

SCRIPT = Path(os.environ['TOOL_SOURCE_DIR']) / 'subagent-model-upsert.sh'

class UpsertTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='model upsert ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.directory = self.root / 'role files'
        self.role = self.directory / 'content-writer.json'
        self.env = dict(os.environ, SUBAGENT_MODELS_DIR=str(self.directory))

    def call(self, *args, success=True, env=None):
        result = subprocess.run(['/bin/bash', str(SCRIPT), '--role', 'content-writer', *args],
                                env=env or self.env, capture_output=True, text=True, timeout=15)
        self.assertEqual(result.returncode == 0, success, result.stderr)
        return result

    def create(self):
        self.call('--model', 'gpt-6.1-sol', '--reasoning-effort', 'high')

    def assert_clean(self):
        self.assertEqual(sorted(p.name for p in self.directory.iterdir()), ['content-writer.json'])

    def test_create_and_partial_updates(self):
        self.create()
        self.assertEqual(self.role.read_text(), '["gpt-6.1-sol","high"]\n')
        self.assertEqual(stat.S_IMODE(self.role.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.directory.stat().st_mode), 0o700)
        self.call('--model', 'provider/new-model')
        self.assertEqual(json.loads(self.role.read_text()), ['provider/new-model', 'high'])
        self.call('--reasoning-effort', 'low')
        self.assertEqual(json.loads(self.role.read_text()), ['provider/new-model', 'low'])
        self.assert_clean()

    def test_missing_fields_and_bad_arguments(self):
        for args in [('--model', 'model'), ('--reasoning-effort', 'high'), (),
                     ('--model', 'bad model', '--reasoning-effort', 'high'),
                     ('--model', '$(touch bad)', '--reasoning-effort', 'high'),
                     ('--model', 'model', '--reasoning-effort', ''),
                     ('--model', 'model', '--model', 'other'),
                     ('--role', '../escape', '--model', 'model'),
                     ('--lock-timeout', 'no', '--model', 'model'),
                     ('--lock-timeout', '61', '--model', 'model'),
                     ('--unknown', 'x')]:
            with self.subTest(args=args):
                self.call(*args, success=False)
                self.assertFalse(self.role.exists())

    def test_invalid_directory_override(self):
        for value in ['', 'relative/path']:
            self.call('--model', 'model', '--reasoning-effort', 'high', success=False,
                      env=dict(self.env, SUBAGENT_MODELS_DIR=value))

    def test_rejects_malformed_pairs_without_modifying_them(self):
        self.directory.mkdir()
        for content in ['not json', '{}', '["m"]', '["m","high","extra"]', '["m","high",null]', '["m","high",{}]',
                        '["m",3]', '[3,"high"]', '["","high"]', '["m",""]',
                        '["m","bad effort"]', '{"0":"m","1":"high"}']:
            with self.subTest(content=content):
                self.role.write_text(content)
                self.call('--model', 'new-model', success=False)
                self.assertEqual(self.role.read_text(), content)
                self.assert_clean()

    def test_symlink_role_is_preserved(self):
        self.directory.mkdir()
        target = self.root / 'external.json'
        target.write_text('["original","high"]')
        self.role.symlink_to(target)
        self.call('--model', 'new-model', success=False)
        self.assertTrue(self.role.is_symlink())
        self.assertEqual(target.read_text(), '["original","high"]')

    def test_timeout_and_interrupted_waiter_leave_other_lock_intact(self):
        self.create()
        lock = Path(str(self.role) + '.lock')
        lock.mkdir()
        result = self.call('--model', 'other', '--lock-timeout', '0', success=False)
        self.assertIn('lock timeout', result.stderr)
        process = subprocess.Popen(['/bin/bash', str(SCRIPT), '--role', 'content-writer',
            '--model', 'other', '--lock-timeout', '5'], env=self.env,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(0.15)
        process.terminate()
        process.communicate(timeout=3)
        self.assertEqual(process.returncode, 143)
        self.assertTrue(lock.is_dir())
        self.assertEqual(json.loads(self.role.read_text()), ['gpt-6.1-sol', 'high'])
        lock.rmdir()

    def test_failed_commit_preserves_previous_file_and_cleans_staging(self):
        self.create()
        before = self.role.read_bytes()
        bin_dir = self.root / 'failure-bin'
        bin_dir.mkdir()
        fake_mv = bin_dir / 'mv'
        fake_mv.write_text('#!/bin/bash\nexit 86\n')
        fake_mv.chmod(0o755)
        self.call('--model', 'other', success=False,
                  env=dict(self.env, PATH=str(bin_dir) + os.pathsep + os.environ['PATH']))
        self.assertEqual(self.role.read_bytes(), before)
        self.assert_clean()

    def test_concurrent_partial_updates_do_not_lose_fields(self):
        self.create()
        processes = [subprocess.Popen(['/bin/bash', str(SCRIPT), '--role', 'content-writer', *args],
                     env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                     for args in [('--model', 'new-model'), ('--reasoning-effort', 'low')]]
        for process in processes:
            stdout, stderr = process.communicate(timeout=15)
            self.assertEqual(process.returncode, 0, stderr)
        self.assertEqual(json.loads(self.role.read_text()), ['new-model', 'low'])
        self.assert_clean()

    def test_readers_see_only_complete_pairs(self):
        self.create()
        processes = [subprocess.Popen(['/bin/bash', str(SCRIPT), '--role', 'content-writer',
                     '--model', 'model-' + str(i), '--reasoning-effort', 'effort-' + str(i)],
                     env=self.env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                     for i in range(6)]
        allowed = [['gpt-6.1-sol', 'high']] + [['model-' + str(i), 'effort-' + str(i)] for i in range(6)]
        deadline = time.monotonic() + 15
        while any(p.poll() is None for p in processes):
            self.assertLess(time.monotonic(), deadline)
            self.assertIn(json.loads(self.role.read_text()), allowed)
            time.sleep(0.002)
        for process in processes:
            stdout, stderr = process.communicate(timeout=1)
            self.assertEqual(process.returncode, 0, stderr)
        self.assert_clean()

unittest.main(argv=['upsert-tests'], verbosity=2)
PY
