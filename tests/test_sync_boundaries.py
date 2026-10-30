"""Data boundaries and ordinary sync behavior on disposable trees only."""
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from src.skills_engine import SkillsEngine


class SyncBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.library = self.root / 'library'
        self.agent = self.root / 'agent'
        (self.library / 'skills/demo').mkdir(parents=True)
        (self.agent / 'skills/demo').mkdir(parents=True)
        self.outside = self.root / 'outside'
        self.outside.mkdir()
        self.victim = self.outside / 'keep.txt'
        self.victim.write_bytes(b'KEEP')
        self.source = self.library / 'skills/demo/file.txt'
        self.source.write_bytes(b'NEW')
        self.target = self.agent / 'skills/demo/file.txt'
        self.engine = SkillsEngine()

    def tearDown(self):
        self.temp.cleanup()

    def deploy(self):
        return self.engine.deploy_skills_downstream(self.library, {'codex': str(self.agent)}, ['codex'], [])

    def test_regular_update_preserves_mtime_mode_and_skips_unchanged(self):
        os.utime(self.source, (100, 100))
        self.source.chmod(0o755)
        self.deploy()
        self.assertEqual(self.target.read_bytes(), b'NEW')
        self.assertEqual(self.target.stat().st_mtime_ns, self.source.stat().st_mtime_ns)
        if os.name != 'nt':
            self.assertEqual(self.target.stat().st_mode & 0o777, 0o755)
        inode = self.target.stat().st_ino
        self.deploy()
        self.assertEqual(self.target.stat().st_ino, inode)

    def test_destination_file_symlink_preserves_victim(self):
        self.target.symlink_to(self.victim)
        with self.assertRaises((ValueError, OSError)):
            self.deploy()
        self.assertEqual(self.victim.read_bytes(), b'KEEP')

    def test_destination_directory_symlink_preserves_outside(self):
        self.target.parent.rmdir()
        self.target.parent.symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            self.deploy()
        self.assertFalse((self.outside / 'file.txt').exists())

    def test_destination_hardlink_updates_entry_without_changing_victim(self):
        os.link(self.victim, self.target)
        self.deploy()
        self.assertEqual(self.victim.read_bytes(), b'KEEP')
        self.assertEqual(self.target.read_bytes(), b'NEW')
        self.assertNotEqual(self.target.stat().st_ino, self.victim.stat().st_ino)

    def test_source_symlink_never_materializes_private_bytes(self):
        self.source.unlink()
        self.source.symlink_to(self.victim)
        with self.assertRaises((ValueError, OSError)):
            self.deploy()
        self.assertFalse(self.target.exists())

    def test_source_symlink_upstream_is_refused_before_copy(self):
        self.source.unlink()
        self.target.symlink_to(self.victim)
        with self.assertRaises((ValueError, OSError)):
            self.engine.scan_and_sync_upstream(self.library, {'codex': str(self.agent)}, ['codex'], [], [])
        self.assertFalse(self.source.exists())

    def test_ignored_system_link_does_not_block_normal_sync(self):
        (self.agent / 'skills/.system').symlink_to(self.outside, target_is_directory=True)
        self.deploy()
        self.assertEqual(self.target.read_bytes(), b'NEW')
        self.assertTrue((self.agent / 'skills/.system').is_symlink())

    def test_skills_root_symlink_is_refused(self):
        self.target.parent.rmdir()
        (self.agent / 'skills').rmdir()
        (self.agent / 'skills').symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            self.deploy()
        self.assertFalse((self.outside / 'demo').exists())

    def test_failed_copy_preserves_destination_and_removes_stage(self):
        self.target.write_bytes(b'OLD')
        def failure(source, output):
            output.write(b'partial')
            raise OSError('synthetic disk-full failure')
        with patch('src.safe_sync_io.shutil.copyfileobj', side_effect=failure):
            with self.assertRaises(OSError):
                self.deploy()
        self.assertEqual(self.target.read_bytes(), b'OLD')
        self.assertEqual(list(self.target.parent.glob('.sync_stage_*')), [])

    def test_link_inserted_during_copy_never_changes_outside_file(self):
        from src import safe_sync_io
        original = safe_sync_io.shutil.copyfileobj
        def insert_link(source, output):
            self.target.symlink_to(self.victim)
            original(source, output)
        with patch('src.safe_sync_io.shutil.copyfileobj', side_effect=insert_link):
            self.deploy()
        self.assertEqual(self.victim.read_bytes(), b'KEEP')
        self.assertEqual(self.target.read_bytes(), b'NEW')
        self.assertFalse(self.target.is_symlink())

    def test_rule_writes_also_preserve_hardlink_and_reject_symlink(self):
        from src import safe_sync_io
        os.link(self.victim, self.target)
        safe_sync_io.write_text(self.target.parent, self.target.name, 'rules tiếng Việt')
        self.assertEqual(self.victim.read_bytes(), b'KEEP')
        self.assertEqual(self.target.read_text(), 'rules tiếng Việt')
        self.target.unlink()
        self.target.symlink_to(self.victim)
        with self.assertRaises(ValueError):
            safe_sync_io.write_text(self.target.parent, self.target.name, 'blocked')
        self.assertEqual(self.victim.read_bytes(), b'KEEP')

    def test_replaced_agent_base_cannot_redirect_writes(self):
        external = self.outside / 'skills/demo/file.txt'
        external.parent.mkdir(parents=True)
        external.write_bytes(b'KEEP')
        self.agent.rename(self.root / 'previous_agent')
        self.agent.symlink_to(self.outside, target_is_directory=True)
        with self.assertRaises((ValueError, OSError)):
            self.deploy()
        self.assertEqual(external.read_bytes(), b'KEEP')
