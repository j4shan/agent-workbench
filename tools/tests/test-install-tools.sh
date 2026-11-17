#!/bin/bash
set -euo pipefail
export TOOL_SOURCE_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd -P)"
exec python3 - <<'PY'
import json
import os
from pathlib import Path
import re
import shlex
import subprocess
import sys
import tempfile
import unittest

SOURCE = Path(os.environ['TOOL_SOURCE_DIR'])

class InstallerTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='install tools ')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.bin = self.root / 'bin files'
        self.config = self.root / 'role files'
        self.config.mkdir()
        self.role = self.config / 'content-writer.json'
        self.role.write_text('["existing-model","medium"]\n')
        self.profile = self.root / '.zshrc'
        self.profile.write_text('existing shell configuration\n')
        self.env = dict(os.environ, SUBAGENT_MODELS_DIR=str(self.config))

    def install(self, *args, success=True):
        result = subprocess.run(['/bin/bash', str(SOURCE / 'install-tools.sh'),
             '--bin-dir', str(self.bin), *args], env=self.env, capture_output=True, text=True, timeout=5)
        self.assertEqual(result.returncode == 0, success, result.stderr)
        return result

    def test_install_and_explicit_replacement_preserve_preferences(self):
        self.install()
        for name in ['gpt-exec', 'subagent-model-upsert']:
            target = self.bin / name
            self.assertTrue(os.access(target, os.X_OK))
            self.assertEqual(target.read_bytes(), (SOURCE / (name + '.sh')).read_bytes())
        self.assertEqual(self.role.read_text(), '["existing-model","medium"]\n')
        self.assertEqual(self.profile.read_text(), 'existing shell configuration\n')
        target = self.bin / 'gpt-exec'
        target.write_text('old executable')
        self.install(success=False)
        self.assertEqual(target.read_text(), 'old executable')
        self.install('--force')
        self.assertEqual(target.read_bytes(), (SOURCE / 'gpt-exec.sh').read_bytes())
        self.assertEqual(sorted(p.name for p in self.bin.iterdir()), ['gpt-exec', 'subagent-model-upsert'])
        self.assertEqual(self.role.read_text(), '["existing-model","medium"]\n')

    def test_all_conflicts_checked_before_first_command_is_installed(self):
        self.bin.mkdir()
        existing = self.bin / 'gpt-exec'
        existing.write_text('preserve')
        self.install(success=False)
        self.assertFalse((self.bin / 'subagent-model-upsert').exists())
        self.assertEqual(existing.read_text(), 'preserve')

    def test_directory_conflict_is_never_overwritten(self):
        (self.bin / 'gpt-exec').mkdir(parents=True)
        self.install('--force', success=False)
        self.assertFalse((self.bin / 'subagent-model-upsert').exists())

    def test_installed_commands_work_together(self):
        self.install()
        subprocess.run([str(self.bin / 'subagent-model-upsert'), '--role', 'code-reviewer',
             '--model', 'test-reviewer', '--reasoning-effort', 'high'],
             env=self.env, capture_output=True, text=True, check=True)
        role_file = self.config / 'code-reviewer.json'
        model = subprocess.run(['/usr/bin/plutil', '-extract', '0', 'raw', '-expect', 'string',
             '-o', '-', str(role_file)], check=True, capture_output=True, text=True).stdout.strip()
        effort = subprocess.run(['/usr/bin/plutil', '-extract', '1', 'raw', '-expect', 'string',
             '-o', '-', str(role_file)], check=True, capture_output=True, text=True).stdout.strip()
        stub_dir = self.root / 'stub'
        stub_dir.mkdir()
        stub = stub_dir / 'codex'
        stub.write_text('#!/bin/bash\ncat\n')
        stub.chmod(0o755)
        prompt = self.root / 'request.txt'
        prompt.write_text('Read-only review request\n')
        result = subprocess.run([str(self.bin / 'gpt-exec'), '--prompt-file', str(prompt),
             '--model', model, '--reasoning-effort', effort, '--sandbox', 'read-only',
             '--project', str(self.root)], env=dict(self.env, PATH=str(stub_dir) + os.pathsep + os.environ['PATH']),
             stdin=subprocess.DEVNULL, capture_output=True, text=True, check=True)
        self.assertEqual(result.stdout, prompt.read_text())
        self.assertIn('model=test-reviewer effort=high', result.stderr)

    def test_documented_skill_commands_use_one_snapshot_and_refresh_next_call(self):
        self.install()
        repository = SOURCE.parent
        stub_dir = self.root / 'runtime'
        stub_dir.mkdir()
        capture = self.root / 'runtime capture.json'
        stub = stub_dir / 'codex'
        stub.write_text('#!' + sys.executable + '\nimport json,os,sys\nfrom pathlib import Path\n' +
                       'Path(os.environ["TEST_CAPTURE"]).write_text(json.dumps({"args":sys.argv[1:],"stdin":sys.stdin.read()}))\n')
        stub.chmod(0o755)
        prompt = self.root / 'review request.txt'
        prompt.write_text('Scoped request from a documented invocation.\n')
        env = dict(self.env, PATH=str(stub_dir) + os.pathsep + os.environ['PATH'], TEST_CAPTURE=str(capture))
        documents = ['skills/documentation-writer/SKILL.md', 'README.md']
        for document in documents:
            with self.subTest(document=document):
                text = (repository / document).read_text()
                block = next(b for b in re.findall(r'```bash\n(.*?)\n```', text, re.S) if b.startswith('role_dir='))
                role = 'code-reviewer' if 'code-reviewer.json' in block else 'content-writer'
                role_file = self.config / (role + '.json')
                role_file.write_text('["initial-model","high"]\n')
                block = block.replace('"$HOME/.local/bin/gpt-exec"', shlex.quote(str(self.bin / 'gpt-exec')))
                for placeholder in ['"/absolute/path/to/documentation-request.txt"', '"/absolute/path/to/code-review-request.txt"']:
                    block = block.replace(placeholder, shlex.quote(str(prompt)))
                block = 'request_file=' + shlex.quote(str(prompt)) + '\n' + block
                lines = block.splitlines()
                at = next(i for i, line in enumerate(lines) if line.startswith('role_config='))
                update = shlex.quote(str(self.bin / 'subagent-model-upsert')) + ' --role ' + role + ' --model next-model --reasoning-effort low >/dev/null'
                lines.insert(at + 1, update)
                result = subprocess.run(['/bin/bash', '-c', '\n'.join(lines)], cwd=self.root, env=env,
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                recorded = json.loads(capture.read_text())
                self.assertIn('initial-model', recorded['args'])
                self.assertIn('model_reasoning_effort="high"', recorded['args'])
                self.assertEqual(recorded['stdin'], prompt.read_text())
                result = subprocess.run(['/bin/bash', '-c', block], cwd=self.root, env=env,
                                        capture_output=True, text=True, timeout=5)
                self.assertEqual(result.returncode, 0, result.stderr)
                recorded = json.loads(capture.read_text())
                self.assertIn('next-model', recorded['args'])
                self.assertIn('model_reasoning_effort="low"', recorded['args'])
                if document != 'README.md':
                    capture.unlink()
                    role_file.write_text('["m","high",null]')
                    result = subprocess.run(['/bin/bash', '-c', block], cwd=self.root, env=env,
                                            capture_output=True, text=True, timeout=5)
                    self.assertNotEqual(result.returncode, 0)
                    self.assertFalse(capture.exists())

    def test_invalid_destination(self):
        result = subprocess.run(['/bin/bash', str(SOURCE / 'install-tools.sh'), '--bin-dir', 'relative'],
             env=self.env, capture_output=True, text=True, timeout=3)
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(self.bin.exists())

unittest.main(argv=['installer-tests'], verbosity=2)
PY
