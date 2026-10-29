"""Signed release metadata, bounded downloads and platform update staging.

Only release-owned URLs are accepted. Config/git/skills paths are never installer targets.
"""
import base64
import hashlib
import json
import os
import platform
import plistlib
import re
import shutil
import ssl
import subprocess
import sys
import tarfile
import tempfile
import time
import uuid
import threading
import configparser
from functools import wraps
from pathlib import Path
from urllib.request import urlopen
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from src.version import VERSION, APP_ID, REPOSITORY

MAX_PACKAGE = 512 * 1024 * 1024

def get_ssl_context():
    """Tạo SSL context có xác thực CA, hỗ trợ SSL_CERT_FILE tùy chỉnh, default certs và certifi."""
    # 1. Nếu người dùng cấu hình SSL_CERT_FILE tùy chỉnh, ưu tiên sử dụng
    custom_cafile = os.environ.get('SSL_CERT_FILE')
    if custom_cafile and os.path.isfile(custom_cafile):
        try:
            return ssl.create_default_context(cafile=custom_cafile)
        except Exception:
            pass

    # 2. Khởi tạo default context và nạp trust store mặc định của hệ thống
    try:
        context = ssl.create_default_context()
        context.load_default_certs()
    except Exception:
        context = ssl.create_default_context()

    # 3. Bổ sung thêm Mozilla CA roots từ certifi nếu có
    certifi_loaded = False
    try:
        import certifi
        cafile = certifi.where()
        if cafile and os.path.isfile(cafile):
            context.load_verify_locations(cafile=cafile)
            certifi_loaded = True
    except Exception:
        pass

    # 4. Nếu chưa nạp được certifi, nạp bổ sung các bundle CA hệ thống macOS / Linux
    if not certifi_loaded:
        for cafile in (
            '/etc/ssl/cert.pem',
            '/private/etc/ssl/cert.pem',
            '/etc/pki/tls/certs/ca-bundle.crt',
            '/etc/ssl/certs/ca-certificates.crt',
        ):
            if os.path.isfile(cafile):
                try:
                    context.load_verify_locations(cafile=cafile)
                    break
                except Exception:
                    pass

    return context

def canonical(payload):
    return json.dumps(payload, sort_keys=True, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')

def semver(value):
    if not isinstance(value, str) or not re.fullmatch(r'(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)', value):
        raise ValueError('Phiên bản cập nhật không hợp lệ')
    return tuple(map(int, value.split('.')))

def verify_manifest(document, public_key):
    payload = document['payload']
    signature = base64.b64decode(document['signature'], validate=True)
    Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key, validate=True)).verify(signature, canonical(payload))
    if payload.get('app_id') != APP_ID:
        raise ValueError('Gói cập nhật không thuộc VXDevSync')
    semver(payload['version'])
    if not isinstance(payload.get('platforms'), dict) or not payload['platforms']:
        raise ValueError('Manifest không có platform hợp lệ')
    for name, item in payload['platforms'].items():
        if name not in ('macos_silicon', 'macos_intel', 'windows_x64'):
            raise ValueError('Platform không hợp lệ')
        suffix = '.exe' if name == 'windows_x64' else '.app.tar.gz'
        filename = f"vxdevsync_{payload['version']}_{name}{'_setup' if name == 'windows_x64' else ''}{suffix}"
        if item['url'] != f"https://github.com/{REPOSITORY}/releases/download/v{payload['version']}/{filename}":
            raise ValueError('URL cập nhật không thuộc release đã ký')
        if not re.fullmatch('[a-f0-9]{64}', item['sha256']) or type(item['size']) is not int or not 0 < item['size'] <= MAX_PACKAGE:
            raise ValueError('Digest/kích thước gói không hợp lệ')
    return payload

def platform_key():
    if sys.platform == 'win32' and platform.machine().lower() in ('amd64', 'x86_64'):
        return 'windows_x64'
    if sys.platform == 'darwin':
        return 'macos_silicon' if platform.machine().lower() == 'arm64' else 'macos_intel'
    raise ValueError('Nền tảng chưa được hỗ trợ cập nhật')

def verify_package(path, entry):
    if path.stat().st_size != entry['size']:
        raise ValueError('Gói tải về không đầy đủ')
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(65536), b''):
            digest.update(chunk)
    if digest.hexdigest() != entry['sha256']:
        raise ValueError('Chữ ký/digest gói tải về không khớp')

def extract_mac_archive(archive, destination, version):
    destination = destination.resolve()
    with tarfile.open(archive, 'r:gz') as tar:
        members = tar.getmembers()
        if sum(m.size for m in members) > MAX_PACKAGE * 3:
            raise ValueError('Archive vượt giới hạn')
        # Validate all entries before writing, including safe framework symlinks.
        for member in members:
            path = destination / member.name
            if not path.resolve().is_relative_to(destination) or not (member.name.startswith('VXDevSync.app/') or (member.name == 'VXDevSync.app' and member.isdir())):
                raise ValueError('Archive path không an toàn')
            if not (member.isdir() or member.isfile() or member.issym()):
                raise ValueError('Archive chứa entry không được hỗ trợ')
            if member.issym() and (Path(member.linkname).is_absolute() or not (path.parent/member.linkname).resolve().is_relative_to(destination)):
                raise ValueError('Archive symlink thoát thư mục')
        # Regular files first; no write is permitted through a symlink.
        for member in members:
            path = destination/member.name
            if member.isdir():
                path.mkdir(parents=True, exist_ok=True)
            elif member.isfile():
                path.parent.mkdir(parents=True, exist_ok=True)
                with tar.extractfile(member) as source, path.open('xb') as target:
                    shutil.copyfileobj(source, target)
                path.chmod(member.mode & 0o777)
        for member in members:
            if member.issym():
                path=destination/member.name;path.parent.mkdir(parents=True,exist_ok=True);path.symlink_to(member.linkname)
    app=destination/'VXDevSync.app'
    with (app/'Contents/Info.plist').open('rb') as f:
        info=plistlib.load(f)
    if info.get('CFBundleIdentifier') != APP_ID or info.get('CFBundleShortVersionString') != version:
        raise ValueError('Bundle identifier/version không khớp release')
    return app

def swap_mac_bundle(stage, target):
    backup=target.with_name('.vxdevsync_backup_'+uuid.uuid4().hex+'.app')
    if target.is_symlink() or stage.is_symlink() or not target.is_dir() or not stage.is_dir():
        raise ValueError('Bundle/staging không hợp lệ')
    target.rename(backup)
    try:
        stage.rename(target)
    except BaseException:
        backup.rename(target)
        raise
    return backup

def write_receipt(path, value):
    """Atomic local receipt; no credentials and no removal of the previous bundle."""
    path = Path(path)
    temporary = path.with_name(path.name + '.' + uuid.uuid4().hex + '.tmp')
    try:
        with temporary.open('x', encoding='utf-8') as output:
            os.chmod(temporary, 0o600)
            json.dump(value, output, ensure_ascii=False)
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def serialized_updater(function):
    @wraps(function)
    def run(self, *args, **kwargs):
        if not self._operation_lock.acquire(blocking=False):
            raise ValueError('operation_busy: cập nhật đang được xử lý')
        try:
            return function(self, *args, **kwargs)
        except BaseException as error:
            self._publish('error', error=str(error), error_code='update_failed')
            raise
        finally:
            self._operation_lock.release()
    return run


def bundle_snapshot(path):
    """Read-only identity/content snapshot. Never follows bundle symlinks."""
    path = Path(path)
    metadata = path.lstat()
    if path.is_symlink() or not path.is_dir():
        raise ValueError('Bundle/staging không hợp lệ')
    digest = hashlib.sha256()
    for directory, dirs, files in os.walk(path, followlinks=False):
        dirs.sort()
        for name in sorted(dirs + files):
            entry = Path(directory) / name
            relative = entry.relative_to(path).as_posix().encode('utf-8')
            stat = entry.lstat()
            digest.update(len(relative).to_bytes(8, 'big') + relative)
            digest.update(str(stat.st_mode & 0o7777).encode() + b'\0')
            if entry.is_symlink():
                value = os.readlink(entry).encode('utf-8')
                digest.update(b'link\0' + len(value).to_bytes(8, 'big') + value)
            elif entry.is_file():
                digest.update(b'file\0' + stat.st_size.to_bytes(8, 'big'))
                with entry.open('rb') as stream:
                    for block in iter(lambda: stream.read(65536), b''):
                        digest.update(block)
            elif entry.is_dir():
                digest.update(b'dir\0')
            else:
                raise ValueError('Bundle/staging chứa entry không hỗ trợ')
    return metadata.st_dev, metadata.st_ino, digest.hexdigest()


def apply_mac_update(plan_path):
    """Separate frozen helper; rollback retains the old app on install failure."""
    log_file = Path('/tmp/vxdevsync_updater.log')
    def _log(msg):
        try:
            with log_file.open('a', encoding='utf-8') as lf:
                lf.write(f"[{time.strftime('%Y-%m-%d %H:%M:%S')}] {msg}\n")
        except Exception:
            pass

    _log(f"apply_mac_update bat dau voi plan_path={plan_path}")
    try:
        plan_path = Path(plan_path)
        plan = json.loads(plan_path.read_text(encoding='utf-8'))
        executable = Path(sys.executable).resolve()
        current = next((p for p in executable.parents if p.suffix == '.app'), None)
        raw_target, raw_stage = Path(plan['target']), Path(plan['stage'])
        if raw_target.is_symlink() or raw_stage.is_symlink():
            raise ValueError('Bundle symlink không hợp lệ')
        target = raw_target.resolve()
        stage = raw_stage.resolve()
        _log(f"current={current}, target={target}, stage={stage}")
        if current is None or target != current or target.name != 'VXDevSync.app':
            raise ValueError('Đích cài đặt không phải bundle đang chạy')
        if stage.parent.parent != target.parent or not stage.parent.name.startswith('.vxdevsync_update_') or stage.name != 'VXDevSync.app':
            raise ValueError('Staging không hợp lệ')
        if plan_path.resolve().parent != stage.parent:
            raise ValueError('Plan phải nằm cùng staging')
        receipt_path = target.parent / '.vxdevsync_update_receipt.json'
        receipt = {'job_id': plan.get('job_id', stage.parent.name), 'target': str(target), 'state': 'preparing'}
        with (stage / 'Contents/Info.plist').open('rb') as f:
            info = plistlib.load(f)
        receipt['version'] = info.get('CFBundleShortVersionString')

        target_plist = target / 'Contents/Info.plist'
        if target_plist.is_file():
            with target_plist.open('rb') as f:
                target_info = plistlib.load(f)
            base_ver = target_info.get('CFBundleShortVersionString', VERSION)
        else:
            base_ver = VERSION

        if info.get('CFBundleIdentifier') != APP_ID or semver(info['CFBundleShortVersionString']) <= semver(base_ver):
            raise ValueError(f"Không cho phép rollback hoặc bundle khác (stage={info.get('CFBundleShortVersionString')}, base={base_ver})")
        pid = int(plan['pid'])
        if pid <= 0 or pid == os.getpid():
            raise ValueError('PID không hợp lệ')

        target_snapshot = bundle_snapshot(target)
        stage_snapshot = bundle_snapshot(stage)

        # Thong bao cho tien trinh me biet helper da khoi dong va xac thuc bundle thanh cong
        ready_file = Path(plan['ready_file']) if plan.get('ready_file') else None
        if ready_file:
            if ready_file.is_symlink() or ready_file.resolve().parent != stage.parent:
                raise ValueError('Ready receipt phải nằm trong staging')
            write_receipt(receipt_path, {**receipt, 'state': 'ready'})
            ready_file.write_text('ready', encoding='utf-8')
            _log(f"Da tao ready_file xac nhan: {ready_file}")

        _log(f"Dang cho PID cha {pid} thoat...")
        for _ in range(300):
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                _log(f"PID cha {pid} da thoat.")
                break
            time.sleep(0.1)
        else:
            raise TimeoutError('Ứng dụng chưa đóng; chưa thay bundle')
        if bundle_snapshot(target) != target_snapshot:
            raise ValueError('Bundle đích đã thay đổi sau khi helper sẵn sàng; chưa thay bundle')
        if bundle_snapshot(stage) != stage_snapshot:
            raise ValueError('Staging đã thay đổi sau khi helper sẵn sàng; chưa thay bundle')
        _log("Tien hanh hoan doi bundle...")
        write_receipt(receipt_path, {**receipt, 'state': 'installing'})
        backup = swap_mac_bundle(stage, target)
        receipt['backup'] = str(backup)
        write_receipt(receipt_path, {**receipt, 'state': 'awaiting_launch_confirmation'})
        _log(f"Da hoan doi bundle thanh cong. Backup: {backup}. Khoi chay phien ban moi...")
        try:
            open_res = subprocess.run(['/usr/bin/open', '-n', str(target)], capture_output=True, timeout=15)
            if open_res.returncode != 0:
                raise RuntimeError(open_res.stderr.decode('utf-8', errors='replace'))
        except BaseException as launch_error:
            failed = target.with_name('.vxdevsync_failed_' + uuid.uuid4().hex + '.app')
            target.rename(failed)
            try:
                backup.rename(target)
            except BaseException:
                failed.rename(target)
                raise
            write_receipt(receipt_path, {**receipt, 'state': 'relaunch_failed', 'failed_bundle': str(failed), 'error': str(launch_error)})
            raise RuntimeError('Không mở được bản mới; đã khôi phục bundle cũ') from launch_error
        plan_path.unlink(missing_ok=True)
        shutil.rmtree(stage.parent, ignore_errors=True)
        _log('Đã yêu cầu mở bản mới; chờ xác nhận startup, giữ backup.')
    except Exception as error:
        _log(f"Loi apply_mac_update: {error}")
        import traceback
        _log(traceback.format_exc())
        raise

class AppUpdater:
    def __init__(self):
        config=json.loads(Path(__file__).with_name('release_config.json').read_text(encoding='utf-8'))
        self.public_key=config['public_key']
        self.pending=None
        self.install_dispatched=False
        self._operation_lock = threading.RLock()
        self._state_lock = threading.Lock()
        self._state = {'status': 'idle', 'current_version': VERSION, 'noticeVisible': False}
        self._acknowledge_launch()

    def _acknowledge_launch(self):
        if not getattr(sys, 'frozen', False):
            return
        if sys.platform == 'win32':
            target = Path(sys.executable).resolve().parent
            receipt = target.parent / '.vxdevsync_update_receipt.ini'
            try:
                document = configparser.ConfigParser()
                document.read(receipt, encoding='utf-16')
                value = document['Update']
                if (Path(value.get('target', '')).resolve() == target and value.get('version') == VERSION
                        and value.get('state') == 'awaiting_launch_confirmation'):
                    value['state'] = 'completed'
                    temporary = receipt.with_name(receipt.name + '.tmp')
                    with temporary.open('w', encoding='utf-16') as out:
                        document.write(out)
                    os.replace(temporary, receipt)
            except (OSError, ValueError, KeyError, configparser.Error):
                pass
            return
        if sys.platform != 'darwin':
            return
        target = next((p for p in Path(sys.executable).resolve().parents if p.suffix == '.app'), None)
        if target is None:
            return
        receipt = target.parent / '.vxdevsync_update_receipt.json'
        try:
            value = json.loads(receipt.read_text(encoding='utf-8'))
            if (value.get('target') == str(target) and value.get('version') == VERSION
                    and value.get('state') in ('restarting', 'awaiting_launch_confirmation')):
                write_receipt(receipt, {**value, 'state': 'completed'})
        except (OSError, ValueError):
            pass

    def _publish(self, status, **fields):
        with self._state_lock:
            self._state = {'status': status, 'current_version': VERSION, **fields}

    def snapshot(self):
        with self._state_lock:
            return dict(self._state)

    @serialized_updater

    def check(self):
        if self.install_dispatched:
            return {'success': True, **self.snapshot()}
        self.pending = None
        self._publish('checking')
        url=f'https://github.com/{REPOSITORY}/releases/latest/download/latest.json'
        context=get_ssl_context()
        with urlopen(url, timeout=15, context=context) as response:
            data=response.read(1024*1024+1)
        if len(data)>1024*1024:raise ValueError('Manifest vượt giới hạn')
        payload=verify_manifest(json.loads(data),self.public_key)
        newer = semver(payload['version']) > semver(VERSION)
        if newer and platform_key() not in payload['platforms']:
            raise ValueError('Release chưa có gói cho nền tảng này')
        self.pending=payload if newer else None
        self._publish('available' if newer else 'current', version=payload['version'], available=newer, noticeVisible=newer)
        return {'success':True,'current_version':VERSION,'available':bool(self.pending),'version':payload['version']}

    @serialized_updater
    def install(self):
        if self.install_dispatched:raise ValueError('Gói cập nhật đã được gửi tới bộ cài; hãy đóng ứng dụng để hoàn tất')
        if not getattr(sys,'frozen',False):raise ValueError('Chỉ cập nhật từ app đã đóng gói')
        # Always revalidate the current signed manifest before an install.
        self.check()
        if not self.pending:raise ValueError('Chưa có phiên bản mới')
        key=platform_key();entry=self.pending['platforms'].get(key)
        if not entry:raise ValueError('Release chưa có gói cho nền tảng này')
        folder=Path(tempfile.mkdtemp(prefix='vxdevsync_download_'));package=folder/('setup.exe' if key=='windows_x64' else 'app.tar.gz')
        staging=None
        helper_proc=None
        context=get_ssl_context()
        try:
            self._publish('downloading', version=self.pending['version'], noticeVisible=True)
            download_deadline = time.monotonic() + 300
            with urlopen(entry['url'],timeout=30,context=context) as response,package.open('xb') as output:
                size=0
                while True:
                    if time.monotonic() > download_deadline:
                        raise TimeoutError('Quá thời gian tải gói cập nhật (tổng thời gian vượt quá 300 giây)')
                    block=response.read(65536)
                    if not block:break
                    size+=len(block)
                    if size>entry['size']:raise ValueError('Gói tải về vượt kích thước đã ký')
                    output.write(block)
                    self._publish('downloading', version=self.pending['version'], progress=min(100, round(size / entry['size'] * 100)), noticeVisible=True)
            self._publish('verifying', version=self.pending['version'], noticeVisible=True)
            verify_package(package,entry)
            if key=='windows_x64':
                executable = Path(sys.executable).resolve()
                if executable.name.lower() != 'vxdevsync.exe':
                    raise ValueError('Đích cài đặt không phải VXDevSync.exe đang chạy')
                ready_file = folder / 'ready.flag'
                receipt_file = executable.parent.parent / '.vxdevsync_update_receipt.ini'
                receipt_temp = receipt_file.with_name('.vxdevsync_receipt_' + uuid.uuid4().hex + '.ini')
                with receipt_temp.open('x', encoding='utf-16') as out:
                    out.write('[Update]\n')
                os.replace(receipt_temp, receipt_file)
                helper_proc = subprocess.Popen([str(package), '/S', f'/PARENT_PID={os.getpid()}',
                    f'/UPDATE_READY={ready_file}', f'/UPDATE_RECEIPT={receipt_file}',
                    f'/D={executable.parent}'], close_fds=True)
                for _ in range(50):
                    if ready_file.is_file():
                        break
                    if helper_proc.poll() is not None:
                        raise RuntimeError('Bộ cài đã thoát trước khi xác nhận sẵn sàng')
                    time.sleep(0.1)
                else:
                    raise TimeoutError('Bộ cài chưa xác nhận sẵn sàng; ứng dụng chưa đóng')
            else:
                app=next((p for p in Path(sys.executable).resolve().parents if p.suffix=='.app'),None)
                if app is None or app.name!='VXDevSync.app' or not os.access(app.parent,os.W_OK):
                    raise ValueError('Hãy cài VXDevSync vào thư mục có quyền ghi; không chạy trực tiếp trong DMG')
                staging=Path(tempfile.mkdtemp(prefix='.vxdevsync_update_',dir=app.parent))
                staged_app=extract_mac_archive(package,staging,self.pending['version'])
                subprocess.run(['codesign','--verify','--deep','--strict',str(staged_app)],check=True,capture_output=True,timeout=30)
                self._publish('installing', version=self.pending['version'], noticeVisible=True)
                ready_file = staging / 'ready.flag'
                plan=staging/'plan.json'
                plan.write_text(json.dumps({
                    'job_id': staging.name,
                    'target': str(app),
                    'stage': str(staged_app),
                    'pid': os.getpid(),
                    'ready_file': str(ready_file)
                }), encoding='utf-8')
                plan.chmod(0o600)
                helper_proc = subprocess.Popen([sys.executable,'--apply-update',str(plan)],start_new_session=True,close_fds=True)
                for _ in range(50):
                    if ready_file.is_file():
                        break
                    if helper_proc.poll() is not None:
                        raise RuntimeError(f"Trình cập nhật thoát bất thường với mã {helper_proc.returncode}")
                    time.sleep(0.1)
                else:
                    helper_proc.terminate()
                    raise TimeoutError("Trình cài đặt cập nhật không khởi động kịp thời (timeout 5s)")
            self.install_dispatched=True
            self._publish('handed_off', version=self.pending['version'], noticeVisible=True)
            if key != 'windows_x64':
                shutil.rmtree(folder,ignore_errors=True)
            return {'success':True,'restart_required':True,'handoff_started':True,'status':'handed_off'}
        except BaseException:
            if helper_proc is not None and helper_proc.poll() is None:
                helper_proc.terminate()
                try:
                    helper_proc.wait(timeout=2)
                except subprocess.TimeoutExpired:
                    helper_proc.kill()
                    helper_proc.wait(timeout=2)
            shutil.rmtree(folder,ignore_errors=True)
            if staging is not None:
                shutil.rmtree(staging,ignore_errors=True)
            raise
