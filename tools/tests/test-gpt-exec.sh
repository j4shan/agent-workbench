#!/bin/bash
set -euo pipefail
export TOOL_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
exec python3 - <<'PY'
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

SCRIPT = Path(os.environ['TOOL_SOURCE_DIR']) / 'gpt-exec.sh'

class InvocationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='gpt exec ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin'
        self.bin.mkdir()
        self.capture = self.root / 'capture.json'
        self.prompt = self.root / 'request with spaces.txt'
        self.prompt.write_text('PRIVATE REQUEST: review supplied evidence.\n')
        codex = self.bin / 'codex'
        codex.write_text('#!' + sys.executable + '\n' +
            'import json,os,sys,time\nfrom pathlib import Path\n' +
            'Path(os.environ["TEST_CAPTURE"]).write_text(json.dumps({"args":sys.argv[1:],"stdin":sys.stdin.read()}))\n' +
            'if os.environ.get("TEST_HOLD"): time.sleep(30)\n' +
            'sys.exit(int(os.environ.get("TEST_EXIT", "0")))\n')
        codex.chmod(0o755)
        self.env = dict(os.environ, PATH=str(self.bin) + os.pathsep + os.environ['PATH'],
                        TEST_CAPTURE=str(self.capture))
        self.args = ['--prompt-file', str(self.prompt), '--model', 'test-model',
                     '--reasoning-effort', 'high', '--sandbox', 'read-only', '--project', str(self.root)]

    def call(self, args=None, env=None, **kwargs):
        return subprocess.run(['/bin/bash', str(SCRIPT), *(self.args if args is None else args)],
             env=env or self.env, capture_output=True, text=True, timeout=4, **kwargs)

    def test_open_inherited_pipe_cannot_block_prompt_delivery(self):
        read_fd, write_fd = os.pipe()
        try:
            result = self.call(stdin=read_fd)
            self.assertEqual(result.returncode, 0, result.stderr)
            recorded = json.loads(self.capture.read_text())
            self.assertEqual(recorded['stdin'], self.prompt.read_text())
            self.assertEqual(recorded['args'], ['exec', '--ephemeral', '--model', 'test-model',
                '--config', 'model_reasoning_effort="high"', '--sandbox', 'read-only',
                '--cd', str(self.root.resolve()), '-'])
            self.assertNotIn('PRIVATE REQUEST', result.stderr)
        finally:
            os.close(read_fd)
            os.close(write_fd)

    def test_sandbox_output_options_and_exit_status(self):
        args = list(self.args)
        args[args.index('read-only')] = 'workspace-write'
        output = self.root / 'final output.txt'
        result = self.call(args + ['--json', '--output-last-message', str(output)],
                           env=dict(self.env, TEST_EXIT='23'))
        self.assertEqual(result.returncode, 23, result.stderr)
        recorded = json.loads(self.capture.read_text())['args']
        self.assertIn('workspace-write', recorded)
        self.assertEqual(recorded[-4:], ['--json', '--output-last-message', str(output), '-'])
        self.assertNotIn('--ignore-user-config', recorded)

    def test_invalid_inputs_never_launch_codex(self):
        empty = self.root / 'empty'
        empty.touch()
        fifo = self.root / 'pipe'
        os.mkfifo(fifo)
        bad_args = [[], self.args + ['extra prompt'], self.args + ['--model', 'duplicate'],
                    self.args + ['--dangerously-bypass-approvals-and-sandbox']]
        for old, new in [('test-model', '$(touch bad)'), ('high', 'bad effort'),
                         ('read-only', 'danger-full-access'), (str(self.root), str(self.root / 'absent')),
                         (str(self.prompt), str(empty)), (str(self.prompt), str(fifo)),
                         (str(self.prompt), str(self.root / 'missing'))]:
            bad_args.append([new if arg == old else arg for arg in self.args])
        for args in bad_args:
            with self.subTest(args=args):
                result = self.call(args)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(self.capture.exists())

    def test_missing_runtime_reports_setup_error(self):
        result = self.call(env=dict(self.env, PATH='/usr/bin:/bin'))
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('codex is not on PATH', result.stderr)
        self.assertFalse(self.capture.exists())

    def test_exec_preserves_pid_and_cancellation(self):
        process = subprocess.Popen(['/bin/bash', str(SCRIPT), *self.args],
            env=dict(self.env, TEST_HOLD='1'), stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        try:
            deadline = time.monotonic() + 4
            while not self.capture.exists():
                self.assertIsNone(process.poll())
                self.assertLess(time.monotonic(), deadline)
                time.sleep(0.01)
            process.terminate()
            process.communicate(timeout=3)
            self.assertEqual(process.returncode, -signal.SIGTERM)
        finally:
            if process.poll() is None:
                process.kill()
                process.communicate()

unittest.main(argv=['invocation-tests'], verbosity=2)
PY
