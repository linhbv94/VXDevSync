import os
from pathlib import Path
import tempfile
import unittest
from src.adapter_engine import AdapterEngine


class RuleBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.library = self.root / 'library'
        self.agent = self.root / 'agent'
        self.claude = self.root / 'claude'
        for path in [self.library, self.agent, self.claude]:
            path.mkdir()
        self.rules = self.library / 'AGENTS.md'
        self.rules.write_text('Quy tắc dùng chung\n', encoding='utf-8')
        self.victim = self.root / 'private.txt'
        self.victim.write_text('KEEP')
        self.engine = AdapterEngine()

    def tearDown(self):
        self.temp.cleanup()

    def deploy(self):
        return self.engine.deploy_rules_downstream(self.library,
            {'codex': str(self.agent), 'claude': str(self.claude)}, ['codex', 'claude'])

    def test_normal_rules_and_claude_header_are_preserved(self):
        self.deploy()
        self.assertEqual((self.agent / 'AGENTS.md').read_text(), self.rules.read_text())
        self.assertIn(self.rules.read_text(), (self.claude / 'CLAUDE.md').read_text())
        self.assertIn('Claude Code', (self.claude / 'CLAUDE.md').read_text())

    def test_destination_rules_symlink_is_refused(self):
        (self.agent / 'AGENTS.md').symlink_to(self.victim)
        with self.assertRaises(ValueError):
            self.deploy()
        self.assertEqual(self.victim.read_text(), 'KEEP')

    def test_rules_hardlink_does_not_change_outside_inode(self):
        os.link(self.victim, self.agent / 'AGENTS.md')
        self.deploy()
        self.assertEqual(self.victim.read_text(), 'KEEP')
        self.assertEqual((self.agent / 'AGENTS.md').read_text(), self.rules.read_text())

    def test_library_rules_symlink_is_not_read(self):
        self.rules.unlink()
        self.rules.symlink_to(self.victim)
        with self.assertRaises(ValueError):
            self.deploy()
        self.assertFalse((self.agent / 'AGENTS.md').exists())
