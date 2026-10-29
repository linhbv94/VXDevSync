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

            ready_file = staging_dir / 'ready.flag'
            plan_path = staging_dir / 'plan.json'
            plan_path.write_text(json.dumps({
                'target': str(target),
                'stage': str(stage),
                'pid': 999999,
                'ready_file': str(ready_file)
            }))

            run_mock = MagicMock(returncode=0)
            with patch('os.kill', side_effect=ProcessLookupError), \
                 patch('subprocess.run', return_value=run_mock) as mock_run, \
                 patch('sys.executable', str(target / 'Contents' / 'MacOS' / 'VXDevSync')):
                apply_mac_update(str(plan_path))

            self.assertTrue((target / 'new_file.txt').is_file())
            self.assertEqual((target / 'new_file.txt').read_text(), 'new')
            self.assertFalse(plan_path.exists())
            self.assertFalse(stage.parent.exists()) # staging cleaned up
            mock_run.assert_called_once_with(['/usr/bin/open', '-n', str(target.resolve())], capture_output=True, timeout=15)

    def test_bridge_api_install_update_delayed_exit_and_blocks_mutations(self):
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
            self.assertTrue(api._shutdown_pending)
            self.assertGreaterEqual(mock_thread_cls.call_count, 1)
            # verify threads are daemon
            for call in mock_thread_cls.call_args_list:
                _, kwargs = call
                self.assertTrue(kwargs.get('daemon'))

        # Verify new mutation is blocked when shutdown is pending
        mutation_res = api.save_config({"general": {"default_tab": "git_sync"}})
        self.assertFalse(mutation_res['success'])
        self.assertIn("khởi động lại", mutation_res['error'])

class UpdaterControllerTests(unittest.TestCase):
    def mac_fixture(self, root, ready_outside=False):
        import plistlib
        target=root/'VXDevSync.app'; stage=root/'.vxdevsync_update_fixture'/'VXDevSync.app'
        for app, version in [(target,'1.0.2'),(stage,'1.0.3')]:
            (app/'Contents').mkdir(parents=True)
            with (app/'Contents/Info.plist').open('wb') as out:
                plistlib.dump({'CFBundleIdentifier':APP_ID,'CFBundleShortVersionString':version},out)
        (target/'marker').write_text('old'); (stage/'marker').write_text('new')
        ready=(root/'outside_ready') if ready_outside else stage.parent/'ready.flag'
        plan=stage.parent/'plan.json'
        plan.write_text(json.dumps({'target':str(target),'stage':str(stage),'pid':999999,'ready_file':str(ready)}))
        return target,stage,plan

    def test_relaunch_error_and_timeout_restore_old_bundle(self):
        import subprocess
        from unittest.mock import patch,MagicMock
        from src.updater import apply_mac_update
        for timeout in [False,True]:
            with self.subTest(timeout=timeout), tempfile.TemporaryDirectory() as folder:
                root=Path(folder);target,stage,plan=self.mac_fixture(root)
                kwargs={'side_effect':subprocess.TimeoutExpired('open',15)} if timeout else {'return_value':MagicMock(returncode=1,stderr=b'launch failed')}
                with patch('os.kill',side_effect=ProcessLookupError),patch('subprocess.run',**kwargs),patch('sys.executable',str(target/'Contents/MacOS/VXDevSync')):
                    with self.assertRaises(RuntimeError):apply_mac_update(plan)
                self.assertEqual((target/'marker').read_text(),'old')
                receipt=json.loads((root/'.vxdevsync_update_receipt.json').read_text())
                self.assertEqual(receipt['state'],'relaunch_failed')
                self.assertEqual((Path(receipt['failed_bundle'])/'marker').read_text(),'new')

    def test_ready_file_cannot_escape_stage(self):
        from unittest.mock import patch
        from src.updater import apply_mac_update
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target,stage,plan=self.mac_fixture(root,ready_outside=True)
            with patch('sys.executable',str(target/'Contents/MacOS/VXDevSync')):
                with self.assertRaises(ValueError):apply_mac_update(plan)
            self.assertFalse((root/'outside_ready').exists());self.assertEqual((target/'marker').read_text(),'old')

    def test_fast_child_startup_confirmation_is_not_overwritten(self):
        from unittest.mock import patch,MagicMock
        from src.updater import apply_mac_update,AppUpdater
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target,stage,plan=self.mac_fixture(root)
            def launch(*args,**kwargs):
                with patch('sys.frozen',True,create=True),patch('src.updater.VERSION','1.0.3'):
                    AppUpdater()
                return MagicMock(returncode=0)
            with patch('os.kill',side_effect=ProcessLookupError),patch('subprocess.run',side_effect=launch),patch('sys.executable',str(target/'Contents/MacOS/VXDevSync')):
                apply_mac_update(plan)
            self.assertEqual(json.loads((root/'.vxdevsync_update_receipt.json').read_text())['state'],'completed')

    def test_updater_single_flight_rejects_second_thread(self):
        import threading
        from src.updater import AppUpdater
        updater=AppUpdater();entered=threading.Event();release=threading.Event()
        def held_operation():
            updater._operation_lock.acquire();entered.set();release.wait(2);updater._operation_lock.release()
        thread=threading.Thread(target=held_operation);thread.start();self.assertTrue(entered.wait(1))
        try:
            with self.assertRaisesRegex(ValueError,'operation_busy'):updater.check()
        finally:release.set();thread.join(2)
        self.assertFalse(thread.is_alive())

    def test_windows_unicode_receipt_confirms_loaded_version(self):
        import configparser
        from unittest.mock import patch
        from src.updater import AppUpdater
        from src.version import VERSION
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target=root/'Thư mục chương trình'/'VXDevSync';target.mkdir(parents=True)
            executable=target/'VXDevSync.exe';executable.write_bytes(b'fixture')
            receipt=root/'Thư mục chương trình'/'.vxdevsync_update_receipt.ini'
            receipt.write_text('[Update]\nstate=awaiting_launch_confirmation\ntarget='+str(target)+'\nversion='+VERSION+'\n',encoding='utf-16')
            with patch('sys.platform','win32'),patch('sys.frozen',True,create=True),patch('sys.executable',str(executable)):
                AppUpdater()
            document=configparser.ConfigParser();document.read(receipt,encoding='utf-16')
            self.assertEqual(document['Update']['state'],'completed')
            self.assertEqual(document['Update']['target'],str(target))

    def test_staged_bundle_change_after_ack_never_replaces_current_app(self):
        from unittest.mock import patch
        from src.updater import apply_mac_update
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target,stage,plan=self.mac_fixture(root)
            def parent_exited(*args):
                (stage/'marker').write_text('tampered after ack')
                raise ProcessLookupError
            with patch('os.kill',side_effect=parent_exited),patch('sys.executable',str(target/'Contents/MacOS/VXDevSync')),patch('subprocess.run') as launch:
                launch.side_effect = AssertionError('must reject before launch')
                with self.assertRaisesRegex(ValueError,'staging|Staging'):
                    apply_mac_update(plan)
            self.assertEqual((target/'marker').read_text(),'old')
            self.assertFalse(any(root.glob('.vxdevsync_backup_*.app')))

    def test_changed_target_identity_after_ack_is_not_replaced(self):
        import shutil
        from unittest.mock import patch
        from src.updater import apply_mac_update
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder);target,stage,plan=self.mac_fixture(root)
            previous=root/'User_kept_old.app'
            def parent_exited(*args):
                target.rename(previous)
                shutil.copytree(previous,target)
                (target/'marker').write_text('user replacement')
                raise ProcessLookupError
            with patch('os.kill',side_effect=parent_exited),patch('sys.executable',str(target/'Contents/MacOS/VXDevSync')),patch('subprocess.run') as launch:
                launch.side_effect = AssertionError('must reject before launch')
                with self.assertRaisesRegex(ValueError,'bundle|Bundle'):
                    apply_mac_update(plan)
            self.assertEqual((target/'marker').read_text(),'user replacement')
            self.assertEqual((previous/'marker').read_text(),'old')
