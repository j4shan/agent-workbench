"""Behavioral regressions for graph construction, plan parsing, and validation."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SCRIPTS))
import check_plan
import plan_doc
import task_dag


def complete_plan(dag):
    lines = ['# Example', '', '## Problem Statement', '', 'Deliver the requested behavior.', '',
             '**Goals**', '', task_dag.render_goals(dag), '', '## Task DAG', '',
             task_dag.render_table(dag).replace('<observable check>', 'Relevant checks pass'), '', '## Tasks', '']
    for task in dag['tasks']:
        prefix, suffix = {'code': ('src', 'py'), 'config': ('config', 'yaml'),
                          'docs': ('docs', 'md'), 'assets': ('assets', 'png')}[task['category']]
        lines.extend([f"### {task['label']} {task['id']}", '', '**Files**', '',
                      f"- `{prefix}/{task['id']}.{suffix}`", '', '**Consumes**', '', '- —', '',
                      '**Produces**', '', '- —', '', '**Verify**', '', '```bash', 'run-relevant-checks', '```', ''])
    lines.extend(['## Execution Guidelines', '', 'Goals are serial.', ''])
    return '\n'.join(lines)


class GraphTests(unittest.TestCase):
    def test_stable_layers_and_serial_goal_cuts(self):
        tasks = [task_dag.Slice('c', 'first', 'config'), task_dag.Slice('b', 'first', 'docs'),
                 task_dag.Slice('a', 'first', 'code'), task_dag.Slice('d', 'first', 'assets'),
                 task_dag.Slice('ship', 'second', 'docs')]
        dag = task_dag.build([('a', 'c')], tasks, ['first', 'second'])
        self.assertEqual([task['id'] for task in dag['tasks']], ['b', 'a', 'd', 'c', 'ship'])
        self.assertEqual(dag['tasks'][-1]['prereqs'], ['b', 'd', 'c'])
        self.assertEqual(dag['labels']['ship'], 'T5')

    def test_core_rejects_invalid_categories_and_task_identity(self):
        for task in [task_dag.Slice('x', 'g', 'unknown'), task_dag.Slice('', 'g', 'code'),
                     task_dag.Slice('x', '', 'code'), task_dag.Slice(7, 'g', 'code')]:
            with self.subTest(task=task), self.assertRaises(ValueError):
                task_dag.build([], [task], [])

    def test_graph_constraints_are_centralized(self):
        a = task_dag.Slice('a', 'g', 'code')
        b = task_dag.Slice('b', 'g', 'docs')
        c = task_dag.Slice('c', 'g', 'config')
        cases = [([], [a, a], [], 'duplicate task'),
                 ([], [a], ['g', 'empty'], 'empty goal'),
                 ([], [a], [42], 'goal ids'),
                 ([('missing', 'a')], [a], [], 'not a slice'),
                 ([('a', 'b')], [a, task_dag.Slice('b', 'other', 'docs')], [], 'cross-goal'),
                 ([('a', 'b'), ('b', 'a')], [a, b], [], 'cycle detected'),
                 ([('a', 'b'), ('b', 'c'), ('a', 'c')], [a, b, c], [], 'redundant dependency'),
                 ([], [b, task_dag.Slice('other', 'g', 'docs')], [], 'too many tasks')]
        for edges, tasks, goals, message in cases:
            with self.subTest(message=message), self.assertRaisesRegex(ValueError, message):
                task_dag.build(edges, tasks, goals)

    def test_immediate_diamond_is_not_rejected_as_transitive(self):
        tasks = [task_dag.Slice(name, 'g', category) for name, category in
                 [('a', 'code'), ('b', 'docs'), ('c', 'config'), ('d', 'assets')]]
        dag = task_dag.build([('a', 'b'), ('a', 'c'), ('b', 'd'), ('c', 'd')], tasks, [])
        self.assertEqual(dag['tasks'][-1]['prereqs'], ['b', 'c'])

    def test_cli_does_not_wait_for_an_inherited_open_pipe(self):
        read_fd, write_fd = os.pipe()
        try:
            result = subprocess.run([sys.executable, str(SCRIPTS / 'task_dag.py')], stdin=read_fd,
                                    capture_output=True, text=True, timeout=2)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('--input', result.stderr)
        finally:
            os.close(read_fd)
            os.close(write_fd)

    def test_file_input_explicit_stdin_and_legacy_flags_match(self):
        spec = {'goals': ['g'], 'tasks': [{'id': 'a', 'goal': 'g', 'category': 'code'}], 'edges': []}
        script = str(SCRIPTS / 'task_dag.py')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input with spaces.json'
            path.write_text(json.dumps(spec))
            file_result = subprocess.run([sys.executable, script, '--input', str(path), '--format', 'json'],
                                         capture_output=True, text=True, check=True)
        stdin_result = subprocess.run([sys.executable, script, '--input', '-', '--format', 'json'],
                                      input=json.dumps(spec), capture_output=True, text=True, check=True)
        flags_result = subprocess.run([sys.executable, script, '--slice', 'g:code:a', '--format', 'json'],
                                      capture_output=True, text=True, check=True)
        self.assertEqual(file_result.stdout, stdin_result.stdout)
        self.assertEqual(file_result.stdout, flags_result.stdout)

    def test_invalid_json_spec_reports_errors_without_tracebacks(self):
        for spec in [[], {'tasks': 'bad'}, {'tasks': [False]},
                     {'tasks': [{'id': 7, 'goal': 'g', 'category': 'code'}]},
                     {'tasks': [{'id': 'a', 'goal': 'g', 'category': 'bad'}]},
                     {'edges': [['a']]}, {'goals': 'g'}, {'goals': [False]}]:
            with self.subTest(spec=spec):
                result = subprocess.run([sys.executable, str(SCRIPTS / 'task_dag.py'), '--input', '-'],
                                        input=json.dumps(spec), capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn('Traceback', result.stderr)

    def test_existing_output_formats_still_work(self):
        for format in ['all', 'table', 'pairs', 'goals', 'json', 'scaffold']:
            result = subprocess.run([sys.executable, str(SCRIPTS / 'task_dag.py'),
                 '--task', 'g:code:a', '--format', format], capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.strip())


class DocumentTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'plan.md'
        self.dag = task_dag.build([], [task_dag.Slice('implement', 'g', 'code')], [])
        self.text = complete_plan(self.dag)

    def findings(self, text):
        self.path.write_text(text)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            result = check_plan.validate_plan(self.path)
        self.assertEqual(output.getvalue(), '')
        return [message for line, message in result]

    def test_complete_plan_round_trips_and_keeps_fenced_verification(self):
        self.assertEqual(self.findings(self.text), [])
        doc = plan_doc.parse(self.text)
        self.assertIn('run-relevant-checks', doc.task_bodies[0].fields['Verify'])

    def test_fenced_headings_tables_fields_and_placeholders_are_not_structure(self):
        fake = '\n'.join(['### T99 example-only', '**Files**', '- pretend.py',
                          '## Task DAG', '| wrong |', '|---|', '| value |', '<not-a-placeholder>'])
        for opener, closer in [('```markdown', '```'), ('~~~markdown', '~~~'), ('````markdown', '````')]:
            block = '\n' + opener + '\n' + fake + '\n' + closer + '\n'
            if opener.startswith('````'):
                block = block.replace(fake, fake + '\n```\n### T98 still-an-example\n```')
            text = self.text.replace('\n## Execution Guidelines', block + '\n## Execution Guidelines')
            with self.subTest(opener=opener):
                self.assertEqual(self.findings(text), [])
                doc = plan_doc.parse(text)
                self.assertEqual([task.label for task in doc.task_bodies], ['T1'])
                self.assertEqual(len(doc.tables['Task DAG']), 1)
                expected_line = text.splitlines().index('### T1 implement') + 1
                self.assertEqual(doc.task_bodies[0].line, expected_line)

    def test_unfenced_placeholder_is_reported_with_original_line(self):
        text = self.text.replace('Goals are serial.', '<missing requirement>')
        self.path.write_text(text)
        findings = check_plan.validate_plan(self.path)
        expected = text.splitlines().index('<missing requirement>') + 1
        self.assertIn((expected, 'unfilled placeholder <missing requirement>'), findings)

    def test_core_graph_errors_are_reported_by_checker(self):
        for old, new, message in [(' | code | ', ' | unknown | ', 'unknown category'),
                                  (' | implement | ', ' |  | ', 'nonempty string')]:
            with self.subTest(message=message):
                self.assertTrue(any(message in item for item in self.findings(self.text.replace(old, new))))

    def test_checker_rejects_redundant_dependencies(self):
        dag = task_dag.build([('a', 'b'), ('b', 'c')],
                            [task_dag.Slice('a', 'g', 'code'), task_dag.Slice('b', 'g', 'docs'),
                             task_dag.Slice('c', 'g', 'config')], [])
        text = complete_plan(dag).replace('| c | T2 |', '| c | T1, T2 |')
        self.assertTrue(any('redundant dependency' in item for item in self.findings(text)))

    def test_ownership_paths_with_spaces_are_preserved(self):
        dag = task_dag.build([], [task_dag.Slice('first', 'g1', 'code'),
                                  task_dag.Slice('second', 'g2', 'code')], [])
        text = complete_plan(dag).replace('src/first.py', 'src/My File.py').replace('src/second.py', 'src/My File.py')
        self.assertTrue(any('src/My File.py is owned by both' in item for item in self.findings(text)))
        self.assertEqual(check_plan.classify('`src/My File.py`'), 'code')

    def test_dependency_tampering_is_rejected(self):
        dag = task_dag.build([], [task_dag.Slice('first', 'g1', 'code'),
                                  task_dag.Slice('second', 'g2', 'code')], [])
        text = complete_plan(dag).replace('| second | T1 |', '| second | — |')
        self.assertTrue(any('Depends on should be' in item for item in self.findings(text)))

    def test_checker_cli_keeps_explicit_stdin_and_exit_status(self):
        result = subprocess.run([sys.executable, str(SCRIPTS / 'check_plan.py'), '-'],
                                input=self.text, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        result = subprocess.run([sys.executable, str(SCRIPTS / 'check_plan.py'), str(self.path)],
                                capture_output=True, text=True)
        self.assertEqual(result.returncode, 2)


if __name__ == '__main__':
    unittest.main()
