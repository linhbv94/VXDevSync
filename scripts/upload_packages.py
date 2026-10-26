import subprocess
from pathlib import Path
from src.version import VERSION,REPOSITORY
files=sorted(str(p) for p in Path('dist').glob(f'vxdevsync_{VERSION}_*') if p.is_file())
if not files:raise ValueError('No packages created')
subprocess.run(['gh','release','upload',f'v{VERSION}',*files,'--repo',REPOSITORY],check=True)
