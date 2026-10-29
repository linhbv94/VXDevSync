"""Build native packages; filenames describe the built executable, not the host."""
import argparse
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
# Support module and direct script invocation from any working directory.
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))
from src.version import VERSION


def run(args):
    subprocess.run(args, check=True)


def macos_chips(architectures):
    archs = set(architectures.split())
    if not archs or not archs <= {'arm64', 'x86_64'}:
        raise RuntimeError(f'Unsupported built macOS architectures: {architectures!r}')
    return [chip for arch, chip in [('arm64', 'silicon'), ('x86_64', 'intel')] if arch in archs]


def retire_unsupported_packages(dist, chips):
    """Preserve old mislabeled output outside release upload globs."""
    stale = [dist / f'vxdevsync_{VERSION}_macos_{chip}.{suffix}'
             for chip in ('silicon', 'intel') if chip not in chips
             for suffix in ('dmg', 'app.tar.gz')]
    stale = [path for path in stale if path.exists()]
    if stale:
        (dist.parent / 'build').mkdir(exist_ok=True)
        rejected = Path(tempfile.mkdtemp(prefix='stale_macos_', dir=dist.parent / 'build'))
        for path in stale:
            path.rename(rejected / path.name)
        print(f'Unsupported architecture output preserved outside dist: {rejected}')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--app-only', action='store_true', help='Build/verify app without installer archives')
    args = parser.parse_args()
    os.chdir(PROJECT_ROOT)
    os.environ.setdefault('PYINSTALLER_CONFIG_DIR', str(Path('build/pyinstaller_cache').resolve()))
    run([sys.executable, str(Path(__file__).with_name('check_settings_ui.py'))])
    if sys.platform == 'darwin':
        from scripts.build_macos_bootloader import ensure_bootloader
        ensure_bootloader()
    run([sys.executable, '-m', 'PyInstaller', '--clean', '--noconfirm', 'VXDevSync.spec'])
    if sys.platform == 'darwin':
        app = Path('dist/VXDevSync.app')
        executable = app / 'Contents/MacOS/VXDevSync'
        run(['node', 'scripts/macos_sdk_gate.mjs', '--artifact', str(executable)])
        run(['codesign', '--force', '--deep', '--sign', '-', str(app)])
        run(['codesign', '--verify', '--deep', '--strict', str(app)])
        run([str(executable.resolve()), '--self-test'])
        chips = macos_chips(subprocess.check_output(['lipo', '-archs', str(executable)], text=True))
        retire_unsupported_packages(Path('dist'), chips)
        if args.app_only:
            return
        for chip in chips:
            with tarfile.open(f'dist/vxdevsync_{VERSION}_macos_{chip}.app.tar.gz', 'w:gz', dereference=False) as archive:
                archive.add(app, arcname='VXDevSync.app')
            with tempfile.TemporaryDirectory(prefix='dmg_stage_', dir='dist') as directory:
                staging = Path(directory)
                shutil.copytree(app, staging / 'VXDevSync.app', symlinks=True)
                (staging / 'Applications').symlink_to('/Applications')
                run(['hdiutil', 'create', '-volname', 'VXDevSync', '-srcfolder', str(staging), '-ov', '-format', 'UDZO', f'dist/vxdevsync_{VERSION}_macos_{chip}.dmg'])
    elif sys.platform == 'win32':
        run([str(Path('dist/VXDevSync/VXDevSync.exe').resolve()), '--self-test'])
        if args.app_only:
            return
        makensis = Path(os.environ.get('ProgramFiles(x86)', 'C:/Program Files (x86)')) / 'NSIS/makensis.exe'
        if not makensis.exists():
            raise RuntimeError('Missing NSIS on Windows runner')
        run([str(makensis), f'/DVERSION={VERSION}', '/NOCD', 'installer/windows_installer.nsi'])
    else:
        raise RuntimeError('Unsupported build platform')


if __name__ == '__main__':
    main()
