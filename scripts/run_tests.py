"""Isolate every agent/config/remote fixture; never use the real user HOME."""
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from src.config_manager import ConfigManager
import tests.setup_mock_env as setup
import tests.test_live_mock_workflow as live

def main():
    with tempfile.TemporaryDirectory(prefix='vxdevsync_qa_') as directory:
        root=Path(directory);setup.MOCK_ROOT=root/'live';live.MOCK_ROOT=setup.MOCK_ROOT
        agents={name:str(root/'agents'/name) for name in ['anti','codex','claude']}
        with patch.object(ConfigManager,'get_default_agent_paths',staticmethod(lambda:agents)):
            suite=unittest.defaultTestLoader.discover('tests')
            result=unittest.TextTestRunner(verbosity=2).run(suite)
            return 0 if result.wasSuccessful() else 1
if __name__=='__main__':raise SystemExit(main())
