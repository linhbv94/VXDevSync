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
        target = Path(plan['target']).resolve()
        stage = Path(plan['stage']).resolve()
        _log(f"current={current}, target={target}, stage={stage}")
        if current is None or target != current or target.name != 'VXDevSync.app':
            raise ValueError('Đích cài đặt không phải bundle đang chạy')
        if stage.parent.parent != target.parent or not stage.parent.name.startswith('.vxdevsync_update_') or stage.name != 'VXDevSync.app':
            raise ValueError('Staging không hợp lệ')
        with (stage / 'Contents/Info.plist').open('rb') as f:
            info = plistlib.load(f)

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
        _log("Tien hanh hoan doi bundle...")
        backup = swap_mac_bundle(stage, target)
        _log(f"Da hoan doi bundle thanh cong. Backup: {backup}. Khoi chay phien ban moi...")
        subprocess.Popen(['/usr/bin/open', '-n', str(target)], close_fds=True)
        plan_path.unlink(missing_ok=True)
        shutil.rmtree(stage.parent, ignore_errors=True)
        _log("Cap nhat hoan tat thanh cong.")
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

    def check(self):
        url=f'https://github.com/{REPOSITORY}/releases/latest/download/latest.json'
        context=get_ssl_context()
        with urlopen(url, timeout=15, context=context) as response:
            data=response.read(1024*1024+1)
        if len(data)>1024*1024:raise ValueError('Manifest vượt giới hạn')
        payload=verify_manifest(json.loads(data),self.public_key)
        self.pending=payload if semver(payload['version'])>semver(VERSION) else None
        return {'success':True,'current_version':VERSION,'available':bool(self.pending),'version':payload['version']}

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
        context=get_ssl_context()
        try:
            with urlopen(entry['url'],timeout=60,context=context) as response,package.open('xb') as output:
                size=0
                while True:
                    block=response.read(65536)
                    if not block:break
                    size+=len(block)
                    if size>entry['size']:raise ValueError('Gói tải về vượt kích thước đã ký')
                    output.write(block)
            verify_package(package,entry)
            if key=='windows_x64':
                subprocess.Popen([str(package),'/S',f'/PARENT_PID={os.getpid()}'],close_fds=True)
            else:
                app=next((p for p in Path(sys.executable).resolve().parents if p.suffix=='.app'),None)
                if app is None or app.name!='VXDevSync.app' or not os.access(app.parent,os.W_OK):
                    raise ValueError('Hãy cài VXDevSync vào thư mục có quyền ghi; không chạy trực tiếp trong DMG')
                staging=Path(tempfile.mkdtemp(prefix='.vxdevsync_update_',dir=app.parent))
                staged_app=extract_mac_archive(package,staging,self.pending['version'])
                subprocess.run(['codesign','--verify','--deep','--strict',str(staged_app)],check=True,capture_output=True,timeout=30)
                plan=staging/'plan.json';plan.write_text(json.dumps({'target':str(app),'stage':str(staged_app),'pid':os.getpid()}),encoding='utf-8');plan.chmod(0o600)
                subprocess.Popen([sys.executable,'--apply-update',str(plan)],start_new_session=True,close_fds=True)
            self.install_dispatched=True
            shutil.rmtree(folder,ignore_errors=True)
            return {'success':True,'restart_required':True}
        except BaseException:
            shutil.rmtree(folder,ignore_errors=True)
            if staging is not None:
                shutil.rmtree(staging,ignore_errors=True)
            raise
