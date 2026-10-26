import json
import tempfile
import unittest
from pathlib import Path
from src.config_manager import ConfigManager
from src.bridge_api import BridgeApi
class MutationGuardTests(unittest.TestCase):
    def test_corrupt_config_preserved_and_autoscan_disabled(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'config.json';p.write_text('{broken',encoding='utf-8');config=ConfigManager(custom_dir=Path(folder))
            self.assertEqual(p.read_text(),'{broken');self.assertFalse(config.config.general.auto_scan_on_startup)
    def test_update_and_sync_share_nonblocking_guard(self):
        with tempfile.TemporaryDirectory() as folder:
            api=BridgeApi(ConfigManager(custom_dir=Path(folder)));api._mutation_lock.acquire()
            try:
                self.assertFalse(api.install_update()['success']);self.assertFalse(api.sync_git_repos([])['success'])
            finally:api._mutation_lock.release()
    def test_atomic_config_save_retains_previous(self):
        with tempfile.TemporaryDirectory() as folder:
            config=ConfigManager(custom_dir=Path(folder));before=config.config_file.read_bytes();config.config.general.theme='light';self.assertTrue(config.save_config())
            self.assertEqual((Path(folder)/'config_previous.json').read_bytes(),before);self.assertEqual(json.loads(config.config_file.read_text())['general']['theme'],'light')
    def test_bridge_does_not_expose_internal_git_or_filesystem_engines(self):
        with tempfile.TemporaryDirectory() as folder:
            api=BridgeApi(ConfigManager(custom_dir=Path(folder)))
            for name in ['git_engine','skills_engine','adapter_engine','config_manager','window_getter']:
                self.assertNotIn(name,[n for n in dir(api) if not n.startswith('_')])
