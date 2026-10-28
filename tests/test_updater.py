import base64
import hashlib
import io
import json
import tarfile
import tempfile
import unittest
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from src.updater import canonical,verify_manifest,verify_package,extract_mac_archive,semver
from src.version import APP_ID,REPOSITORY

class UpdaterTests(unittest.TestCase):
    def setUp(self):
        self.key=Ed25519PrivateKey.generate()
        self.public=base64.b64encode(self.key.public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)).decode()
        self.payload={'app_id':APP_ID,'version':'1.0.1','platforms':{'windows_x64':{'url':f'https://github.com/{REPOSITORY}/releases/download/v1.0.1/vxdevsync_1.0.1_windows_x64_setup.exe','size':4,'sha256':hashlib.sha256(b'test').hexdigest()}}}
    def signed(self,payload=None):
        p=payload or self.payload
        return {'payload':p,'signature':base64.b64encode(self.key.sign(canonical(p))).decode()}
    def test_signed_manifest_and_tamper(self):
        document=self.signed();self.assertEqual(verify_manifest(document,self.public)['version'],'1.0.1')
        document['payload']['version']='9.0.0'
        with self.assertRaises(Exception):verify_manifest(document,self.public)
    def test_signed_but_wrong_repo_or_app_rejected(self):
        self.payload['platforms']['windows_x64']['url']='https://example.invalid/installer.exe'
        with self.assertRaises(ValueError):verify_manifest(self.signed(),self.public)
        self.payload['app_id']='different.app'
        with self.assertRaises(ValueError):verify_manifest(self.signed(),self.public)
    def test_wrong_key_rejected(self):
        other=Ed25519PrivateKey.generate().public_key().public_bytes(serialization.Encoding.Raw,serialization.PublicFormat.Raw)
        with self.assertRaises(Exception):verify_manifest(self.signed(),base64.b64encode(other).decode())
    def test_package_corruption_rejected_before_install(self):
        with tempfile.TemporaryDirectory() as folder:
            p=Path(folder)/'package';p.write_bytes(b'test');verify_package(p,self.payload['platforms']['windows_x64']);p.write_bytes(b'Test')
            with self.assertRaises(ValueError):verify_package(p,self.payload['platforms']['windows_x64'])
    def test_archive_traversal_rejected_without_outside_write(self):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);archive=root/'bad.tar.gz';dest=root/'stage';dest.mkdir()
            with tarfile.open(archive,'w:gz') as t:
                m=tarfile.TarInfo('../outside');m.size=4;t.addfile(m,io.BytesIO(b'evil'))
            with self.assertRaises(ValueError):extract_mac_archive(archive,dest,'1.0.1')
            self.assertFalse((root/'outside').exists())
    def test_semver_rejects_same_or_older_as_new(self):
        self.assertFalse(semver('1.0.0')>semver('1.0.0'));self.assertFalse(semver('0.9.9')>semver('1.0.0'));self.assertTrue(semver('1.0.10')>semver('1.0.9'))
    def test_mac_swap_keeps_previous_bundle(self):
        from src.updater import swap_mac_bundle
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);old=root/'VXDevSync.app';stage=root/'new.app';old.mkdir();stage.mkdir();(old/'marker').write_text('old');(stage/'marker').write_text('new')
            backup=swap_mac_bundle(stage,old)
            self.assertEqual((old/'marker').read_text(),'new');self.assertEqual((backup/'marker').read_text(),'old')
    def test_mac_swap_rolls_back_failed_install(self):
        from src.updater import swap_mac_bundle
        from unittest.mock import patch
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);old=root/'VXDevSync.app';stage=root/'new.app';old.mkdir();stage.mkdir();(old/'marker').write_text('old')
            rename=Path.rename
            def failing(path,target):
                if path==stage:raise OSError('fixture install failure')
                return rename(path,target)
            with patch.object(Path,'rename',failing):
                with self.assertRaises(OSError):swap_mac_bundle(stage,old)
            self.assertEqual((old/'marker').read_text(),'old')
    def test_get_ssl_context_returns_valid_context(self):
        import ssl
        import os
        from unittest.mock import patch
        from src.updater import get_ssl_context
        ctx = get_ssl_context()
        self.assertIsNotNone(ctx)
        self.assertTrue(ctx.check_hostname)
        self.assertEqual(ctx.verify_mode, ssl.CERT_REQUIRED)
        
        # Test custom SSL_CERT_FILE override
        with tempfile.NamedTemporaryFile(suffix='.pem') as f:
            f.write(b'-----BEGIN CERTIFICATE-----\n-----END CERTIFICATE-----\n')
            f.flush()
            with patch.dict(os.environ, {'SSL_CERT_FILE': f.name}):
                custom_ctx = get_ssl_context()
                self.assertIsNotNone(custom_ctx)
                self.assertTrue(custom_ctx.check_hostname)

    def test_apply_mac_update_flow(self):
        import plistlib
        from unittest.mock import patch, MagicMock
        from src.updater import apply_mac_update
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            target = root / 'VXDevSync.app'
            target.mkdir()
            (target / 'Contents').mkdir()
            with (target / 'Contents' / 'Info.plist').open('wb') as f:
                plistlib.dump({'CFBundleIdentifier': APP_ID, 'CFBundleShortVersionString': '1.0.2'}, f)
            (target / 'old_file.txt').write_text('old')

            staging_dir = root / '.vxdevsync_update_test'
            staging_dir.mkdir()
            stage = staging_dir / 'VXDevSync.app'
            stage.mkdir()
            (stage / 'Contents').mkdir()
            with (stage / 'Contents' / 'Info.plist').open('wb') as f:
                plistlib.dump({'CFBundleIdentifier': APP_ID, 'CFBundleShortVersionString': '1.0.3'}, f)
            (stage / 'new_file.txt').write_text('new')

            plan_path = staging_dir / 'plan.json'
            plan_path.write_text(json.dumps({
                'target': str(target),
                'stage': str(stage),
                'pid': 999999
            }))

            with patch('os.kill', side_effect=ProcessLookupError), \
                 patch('subprocess.Popen') as mock_popen, \
                 patch('sys.executable', str(target / 'Contents' / 'MacOS' / 'VXDevSync')):
                apply_mac_update(str(plan_path))

            self.assertTrue((target / 'new_file.txt').is_file())
            self.assertEqual((target / 'new_file.txt').read_text(), 'new')
            self.assertFalse(plan_path.exists())
            self.assertFalse(stage.parent.exists()) # staging cleaned up
            mock_popen.assert_called_once_with(['/usr/bin/open', '-n', str(target.resolve())], close_fds=True)

    def test_bridge_api_install_update_delayed_exit(self):
        from unittest.mock import patch, MagicMock
        from src.bridge_api import BridgeApi
        window_mock = MagicMock()
        api = BridgeApi(config_manager=MagicMock(), window_getter=lambda: window_mock)
        updater_mock = MagicMock()
        updater_mock.install.return_value = {'success': True, 'restart_required': True}
        api._updater = updater_mock

        with patch('threading.Thread') as mock_thread_cls:
            res = api.install_update()
            self.assertTrue(res['success'])
            mock_thread_cls.assert_called_once()
            # verify thread is daemon
            _, kwargs = mock_thread_cls.call_args
            self.assertTrue(kwargs.get('daemon'))
