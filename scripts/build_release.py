"""Build packages on native standard runners, without uploading anything."""
import os
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path
from src.version import VERSION

os.environ.setdefault('PYINSTALLER_CONFIG_DIR',str(Path('build/pyinstaller_cache').resolve()))
def run(args):subprocess.run(args,check=True)
if sys.platform=='darwin':
    from scripts.build_macos_bootloader import ensure_bootloader
    ensure_bootloader()
run([sys.executable,'-m','PyInstaller','--clean','--noconfirm','VXDevSync.spec'])
if sys.platform=='darwin':
    app=Path('dist/VXDevSync.app')
    run(['node','scripts/macos_sdk_gate.mjs','--artifact',str(app/'Contents/MacOS/VXDevSync')])
    run(['codesign','--force','--deep','--sign','-',str(app)])
    run(['codesign','--verify','--deep','--strict',str(app)])
    run([str((app/'Contents/MacOS/VXDevSync').resolve()),'--self-test'])
    chips = ['silicon', 'intel'] if os.uname().machine == 'arm64' else ['intel']
    for chip in chips:
        with tarfile.open(f'dist/vxdevsync_{VERSION}_macos_{chip}.app.tar.gz','w:gz',dereference=False) as tar:
            tar.add(app,arcname='VXDevSync.app')
        with tempfile.TemporaryDirectory(prefix='dmg_stage_',dir='dist') as directory:
            staging=Path(directory)
            shutil.copytree(app,staging/'VXDevSync.app',symlinks=True)
            (staging/'Applications').symlink_to('/Applications')
            run(['hdiutil','create','-volname','VXDevSync','-srcfolder',str(staging),'-ov','-format','UDZO',f'dist/vxdevsync_{VERSION}_macos_{chip}.dmg'])
elif sys.platform=='win32':
    run([str(Path('dist/VXDevSync/VXDevSync.exe').resolve()),'--self-test'])
    makensis=Path(os.environ.get('ProgramFiles(x86)','C:/Program Files (x86)'))/'NSIS/makensis.exe'
    if not makensis.exists():raise RuntimeError('Missing NSIS on Windows runner')
    run([str(makensis),f'/DVERSION={VERSION}','/NOCD','installer/windows_installer.nsi'])
else:raise RuntimeError('Unsupported build platform')
