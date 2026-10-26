"""Release acceptance regressions. Only disposable local fixtures and bare remotes."""
import json
import os
import subprocess
import tempfile
import unittest
from pathlib import Path
from src.bridge_api import BridgeApi
from src.config_manager import ConfigManager
from src.git_engine import GitEngine
from src.skills_engine import SkillsEngine

class ReleaseSafetyTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='vxdevsync_release_qa_')
        self.root = Path(self.temp.name)
        self.lib = self.root / 'library'
        (self.lib / 'skills' / 'sample').mkdir(parents=True)
        (self.lib / 'skills' / 'sample' / 'SKILL.md').write_text('keep me', encoding='utf-8')
        self.config = ConfigManager(custom_dir=self.root / 'config')
        self.config.config.skills_sync.skills_lib = str(self.lib)
        self.config.config.skills_sync.custom_agent_paths = {a: str(self.root/'agents'/a) for a in ['anti','codex','claude']}
        self.config.config.skills_sync.agents = {'anti':0,'codex':0,'claude':0}
        self.api = BridgeApi(self.config)
    def tearDown(self):
        self.temp.cleanup()
    def git(self, path, *args):
        return subprocess.check_output(['git', '-C', str(path), *args], stderr=subprocess.STDOUT, text=True).strip()
    def repositories(self):
        remote=self.root/'remote.git'; local=self.root/'local'; peer=self.root/'peer'
        self.git(self.root,'init','--bare',str(remote))
        self.git(self.root,'init','-b','main',str(local))
        for key,value in [('user.name','QA fixture'),('user.email','qa@example.invalid')]:self.git(local,'config',key,value)
        (local/'base.txt').write_text('base',encoding='utf-8');self.git(local,'add','base.txt');self.git(local,'commit','-m','base');self.git(local,'remote','add','origin',str(remote));self.git(local,'push','-u','origin','main')
        self.git(self.root,'clone','-b','main',str(remote),str(peer))
        for key,value in [('user.name','QA fixture'),('user.email','qa@example.invalid')]:self.git(peer,'config',key,value)
        return remote,local,peer
    def test_inventory_does_not_delete_files(self):
        (self.lib/'.vxdevsync').mkdir();(self.lib/'.vxdevsync/tombstones.json').write_text(json.dumps({'tombstones':[{'name':'sample'}]}),encoding='utf-8')
        self.api.get_skills_inventory()
        self.assertTrue((self.lib/'skills/sample/SKILL.md').exists(), 'Reading inventory must never apply destructive tombstones')
    def test_delete_rejects_parent_traversal(self):
        victim=self.root/'victim';victim.mkdir();(victim/'keep.txt').write_text('outside skill root',encoding='utf-8')
        with self.assertRaises(ValueError):SkillsEngine().execute_delete_cascade(['../../victim'],self.lib,{},[])
        self.assertTrue((victim/'keep.txt').exists())
    def test_smart_sync_pushes_ahead_commit(self):
        remote,local,_=self.repositories();(local/'next.txt').write_text('local change',encoding='utf-8');self.git(local,'add','next.txt');self.git(local,'commit','-m','ahead')
        expected=self.git(local,'rev-parse','HEAD');result=GitEngine().sync_single_repo(local,'smart_sync')
        self.assertTrue(result['success']);self.assertEqual(self.git(remote,'rev-parse','refs/heads/main'),expected,'Smart Sync must push ahead commits')
    def test_pull_skips_dirty_repo_before_mutation(self):
        _,local,peer=self.repositories();before=self.git(local,'rev-parse','HEAD');(local/'untracked.txt').write_text('uncommitted',encoding='utf-8');(peer/'remote.txt').write_text('remote change',encoding='utf-8');self.git(peer,'add','remote.txt');self.git(peer,'commit','-m','behind');self.git(peer,'push')
        result=GitEngine().sync_single_repo(local,'pull')
        self.assertFalse(result['success']);self.assertEqual(self.git(local,'rev-parse','HEAD'),before)
    def test_unconfigured_library_does_not_default_to_cwd(self):
        self.config.config.skills_sync.skills_lib='';cwd=Path.cwd();work=self.root/'work';work.mkdir()
        try:
            os.chdir(work);result=self.api.sync_skills_unified()
        finally:os.chdir(cwd)
        self.assertFalse(result['success']);self.assertEqual(list(work.iterdir()),[])
    def test_skills_sync_does_not_commit_unrelated_files(self):
        remote=self.root/'library_remote.git'
        self.git(self.root,'init','--bare',str(remote));self.git(self.lib,'init','-b','main')
        self.git(self.lib,'config','user.name','QA fixture');self.git(self.lib,'config','user.email','qa@example.invalid')
        self.git(self.lib,'add','skills');self.git(self.lib,'commit','-m','skills');self.git(self.lib,'remote','add','origin',str(remote));self.git(self.lib,'push','-u','origin','main')
        (self.lib/'private_note.txt').write_text('must stay untracked',encoding='utf-8')
        result=self.api.sync_skills_unified()
        tracked=self.git(self.lib,'ls-files','private_note.txt')
        self.assertEqual(tracked,'','Skills sync must not stage or publish unrelated files')

    def test_library_retries_push_without_new_file_changes(self):
        remote,local,_=self.repositories()
        (local/'skills/sample').mkdir(parents=True)
        (local/'skills/sample/SKILL.md').write_text('queued',encoding='utf-8')
        self.git(local,'add','skills');self.git(local,'commit','-m','queued local commit')
        expected=self.git(local,'rev-parse','HEAD')
        committed,pushed,message=self.api._commit_library_changes(local,'retry')
        self.assertFalse(committed);self.assertTrue(pushed)
        self.assertEqual(self.git(remote,'rev-parse','refs/heads/main'),expected)
