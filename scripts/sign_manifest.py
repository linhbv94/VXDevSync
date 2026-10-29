"""Sign only the release-owned package metadata; private key is read from env/stdin."""
import base64
import hashlib
import json
import os
from pathlib import Path
from cryptography.hazmat.primitives import serialization
from src.updater import canonical, verify_manifest
from src.version import VERSION,APP_ID,REPOSITORY

def build_manifest(folder, private_pem):
    platforms={}
    targets = [('windows_x64','_setup.exe'),('macos_silicon','.app.tar.gz')]
    if (folder / f'vxdevsync_{VERSION}_macos_intel.app.tar.gz').exists():
        targets.append(('macos_intel','.app.tar.gz'))
    for platform,suffix in targets:
        filename=f'vxdevsync_{VERSION}_{platform}{suffix}';path=folder/filename
        platforms[platform]={'url':f'https://github.com/{REPOSITORY}/releases/download/v{VERSION}/{filename}', 'size':path.stat().st_size,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()}
    payload={'app_id':APP_ID,'version':VERSION,'platforms':platforms}
    key=serialization.load_pem_private_key(private_pem,password=None)
    document={'payload':payload,'signature':base64.b64encode(key.sign(canonical(payload))).decode()}
    public=json.loads(Path('src/release_config.json').read_text(encoding='utf-8'))['public_key']
    verify_manifest(document,public)
    return document

if __name__=='__main__':
    import sys
    folder=Path(sys.argv[1])
    document=build_manifest(folder,os.environ['VXDEVSYNC_SIGNING_PRIVATE_KEY'].encode())
    (folder/'latest.json').write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Signed manifest created and verified with app public key')
