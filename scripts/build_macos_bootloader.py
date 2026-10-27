"""Compile the installed PyInstaller's exact source into a real SDK27 macOS bootloader."""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tarfile
import tempfile
import urllib.parse
import urllib.request


def _patch_pyinstaller_sdk_downgrade(home: Path):
    api_file = home / 'building' / 'api.py'
    if api_file.exists():
        text = api_file.read_text(encoding='utf-8')
        target = 'osxutils.set_macos_sdk_version(build_name, *pylib_version)'
        if target in text:
            api_file.write_text(text.replace(target, 'pass # Retain exact SDK27 bootloader'), encoding='utf-8')


def ensure_bootloader():
    if sys.platform != 'darwin':
        return
    import PyInstaller
    home = Path(PyInstaller.__file__).parent
    _patch_pyinstaller_sdk_downgrade(home)
    installed = home / 'bootloader' / 'Darwin-64bit'
    gate = str(Path(__file__).with_name('macos_sdk_gate.mjs'))
    subprocess.run(['node', gate], check=True)
    if all(subprocess.run(['node', gate, '--artifact', str(installed / name)],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL).returncode == 0
           for name in ('run', 'runw')):
        return
    version = PyInstaller.__version__
    with urllib.request.urlopen(f'https://pypi.org/pypi/pyinstaller/{version}/json', timeout=60) as response:
        metadata = json.load(response)
    source = next(item for item in metadata['urls'] if item['packagetype'] == 'sdist')
    assert urllib.parse.urlparse(source['url']).hostname == 'files.pythonhosted.org'
    with urllib.request.urlopen(source['url'], timeout=60) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != source['digests']['sha256']:
        raise RuntimeError('PyInstaller source SHA256 mismatch')
    with tempfile.TemporaryDirectory(prefix='vxdevsync_bootloader_') as directory:
        root = Path(directory).resolve()
        archive_path = root / 'source.tar.gz'
        archive_path.write_bytes(data)
        with tarfile.open(archive_path) as archive:
            for member in archive.getmembers():
                destination = root / member.name
                if not destination.resolve().is_relative_to(root):
                    raise RuntimeError('Unexpected source archive path')
                if member.issym() or member.islnk():
                    target = (destination.parent if member.issym() else root) / member.linkname
                    if not target.resolve().is_relative_to(root):
                        raise RuntimeError('Unexpected source archive link')
            archive.extractall(root)
        source_root = next(root.glob('pyinstaller-*'))
        env = dict(os.environ)
        env['SDKROOT'] = subprocess.check_output(['xcrun', '--sdk', 'macosx', '--show-sdk-path'], text=True).strip()
        env['MACOSX_DEPLOYMENT_TARGET'] = '11.0'
        subprocess.run([sys.executable, './waf', 'all', '--universal2'], cwd=source_root / 'bootloader', env=env, check=True)
        built = source_root / 'PyInstaller' / 'bootloader' / 'Darwin-64bit'
        for name in ('run', 'runw', 'run_d', 'runw_d'):
            subprocess.run(['node', gate, '--artifact', str(built / name)], check=True)
        for name in ('run', 'runw', 'run_d', 'runw_d'):
            shutil.copy2(built / name, installed / name)


if __name__ == '__main__':
    ensure_bootloader()
