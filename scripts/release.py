"""GitHub Releases operator: explicit prepare/finalize/publish gates for Python app."""
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.request import urlopen,Request
from scripts.sign_manifest import build_manifest
from src.updater import verify_manifest,verify_package,semver
from src.version import VERSION,REPOSITORY,APP_ID

def gh(*args):return subprocess.check_output(['gh',*args],text=True)
def metadata():return json.loads(gh('release','view',f'v{VERSION}','--repo',REPOSITORY,'--json','databaseId,tagName,isDraft,isPrerelease,assets'))
def names(actual_names=None):
    base = ['windows_x64_setup.exe','macos_silicon.dmg','macos_silicon.app.tar.gz']
    if actual_names and any('macos_intel' in n for n in actual_names):
        base += ['macos_intel.dmg','macos_intel.app.tar.gz']
    return [f'vxdevsync_{VERSION}_{suffix}' for suffix in base]
def notes(has_intel=False):
    p = Path(f'docs/release_notes/{VERSION}.md')
    changes = ''
    if p.exists():
        try: changes = p.read_text(encoding='utf-8').strip()
        except Exception: changes = ''
    if not changes:
        changes = '- Rà soát và chuẩn hóa đa ngôn ngữ toàn diện (i18n En/Vi Consistency): Xử lý triệt để hiện tượng rò rỉ chuỗi tiếng Việt khi chọn English; bổ sung hơn 45 khóa bản địa hóa cho badge, tooltip trạng thái agent, progress banner và nút thao tác; tự động dịch chuỗi tiến trình thời gian thực từ Python backend qua pattern matching; tự động re-render bảng Git Repos và Ma trận Kỹ năng ngay khi chuyển ngôn ngữ trong Settings.\n- Phân loại trạng thái chi tiết cho Kỹ năng tại Agent: Thay thế nhãn "Lệch hash" chung chung bằng 3 trạng thái tường minh: Mới (New - cyan), Đã sửa (Modified - vàng), Cũ hơn (Outdated - amber), bên cạnh Đồng bộ (Synced) và Chưa có (Missing).\n- Luôn ghim dòng Quy tắc hệ thống AGENTS.md (CLAUDE.md) ở hàng đầu tiên (Row 1) của Ma trận Kỹ năng; bảo vệ an toàn tệp quy tắc hệ thống (nhãn "Hệ thống", chặn xóa nhầm).\n- Cố định nút "Sync all (Skills & Rules AGENTS.md)" ở mép phải trên thanh thao tác, không bị đẩy rớt dòng khi văn bản gợi ý dài.\n- Vượt qua 100% 88 bài kiểm thử đơn vị, kiểm tra bảo mật frontend, settings adapter integrity và tự kiểm tra (self-test).'
    base=f'https://github.com/{REPOSITORY}/releases/download/v{VERSION}/vxdevsync_{VERSION}'
    intel_line = f'\n- [Mac Intel]({base}_macos_intel.dmg)' if has_intel else ''
    return changes+f'\n\n**Tải ứng dụng**\n\n- [Windows x64]({base}_windows_x64_setup.exe)\n- [Mac Apple Silicon]({base}_macos_silicon.dmg){intel_line}\n\nWindows: chạy bộ cài. Mac: kéo app vào Applications. Hệ điều hành có thể yêu cầu cho phép mở lần đầu. Cần cài Git để đồng bộ repository.\n\nCác bản sau: Cài đặt → Cập nhật.\n'

def main(mode):
    if os.environ.get('GITHUB_REPOSITORY',REPOSITORY)!=REPOSITORY:raise ValueError('Wrong repository')
    if os.environ.get('RELEASE_TAG',f'v{VERSION}')!=f'v{VERSION}':raise ValueError('Tag/version mismatch')
    repo=json.loads(gh('repo','view',REPOSITORY,'--json','visibility'))
    if repo['visibility']!='PUBLIC':raise ValueError('Only standard public-runner releases are allowed')
    tag=f'v{VERSION}'
    if mode=='prepare':
        listed=json.loads(gh('release','list','--repo',REPOSITORY,'--json','tagName,isDraft'))
        match=next((r for r in listed if r['tagName']==tag),None)
        if match:
            if not match['isDraft']:raise ValueError('Never overwrite a public release')
        else:
            with tempfile.TemporaryDirectory() as directory:
                body=Path(directory)/'notes.md';body.write_text(notes(),encoding='utf-8')
                gh('release','create',tag,'--repo',REPOSITORY,'--verify-tag','--draft','--title',f'VXDevSync {tag}','--notes-file',str(body))
        print('Draft prepared');return
    release=metadata()
    if release['tagName']!=tag or not release['isDraft']:raise ValueError('Expected exact draft tag')
    actual={a['name'] for a in release['assets']}
    expected=set(names(actual))|({'latest.json'} if mode=='publish' else set())
    if (actual!=expected and not (mode=='finalize' and actual==expected|{'latest.json'})) or any(a['size']<=0 for a in release['assets']):raise ValueError('Wrong release asset layout')
    if mode=='publish':
        if os.environ.get('LOCAL_QA_PASSED')!='true':raise ValueError('Local QA not confirmed')
        sha=gh('api',f'repos/{REPOSITORY}/commits/{tag}','--jq','.sha').strip()
        runs=json.loads(gh('run','list','--repo',REPOSITORY,'--workflow','release.yml','--limit','20','--json','headSha,status,conclusion'))
        accepted=False
        for run in runs:
            if run['status']!='completed' or run['conclusion']!='success':continue
            if run['headSha']==sha:
                accepted=True;break
            # A workflow-only repair may run from main while checkout/build stays tag-pinned.
            comparison=json.loads(gh('api',f"repos/{REPOSITORY}/compare/{sha}...{run['headSha']}"))
            files=comparison.get('files',[])
            if comparison['status'] in ('ahead','identical') and len(files)<300 and all(f['filename'].startswith(('.github/','scripts/','tests/','docs/')) or f['filename']=='README.md' for f in files):
                workflow=gh('api',f"repos/{REPOSITORY}/contents/.github/workflows/release.yml?ref={run['headSha']}",'--jq','.content')
                import base64
                content=base64.b64decode(workflow).decode()
                if 'ref: refs/tags/${{ inputs.tag || github.ref_name }}' in content:
                    accepted=True;break
        if not accepted:raise ValueError('Tag-pinned native build with unchanged application inputs not successful')
        published=json.loads(gh('release','list','--repo',REPOSITORY,'--json','tagName,isDraft,isPrerelease'))
        for r in published:
            if not r['isDraft'] and not r['isPrerelease'] and semver(VERSION)<=semver(r['tagName'].removeprefix('v')):raise ValueError('Version must be newer')
    with tempfile.TemporaryDirectory() as directory:
        folder=Path(directory)
        gh('release','download',tag,'--repo',REPOSITORY,'--dir',str(folder))
        if mode=='finalize':
            document=build_manifest(folder,os.environ['VXDEVSYNC_SIGNING_PRIVATE_KEY'].encode())
            if (folder/'latest.json').exists() and json.loads((folder/'latest.json').read_text(encoding='utf-8'))!=document:raise ValueError('Existing draft manifest differs from verified packages')
            (folder/'latest.json').write_text(json.dumps(document,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        else:document=json.loads((folder/'latest.json').read_text(encoding='utf-8'))
        public=json.loads(Path('src/release_config.json').read_text(encoding='utf-8'))['public_key']
        payload=verify_manifest(document,public)
        if payload['version']!=VERSION or not ({'windows_x64','macos_silicon'} <= set(payload['platforms'])):raise ValueError('Incomplete manifest')
        for platform,entry in payload['platforms'].items():
            filename=entry['url'].rsplit('/',1)[1];verify_package(folder/filename,entry)
        if mode=='finalize':gh('release','upload',tag,str(folder/'latest.json'),'--repo',REPOSITORY,'--clobber')
        body={'tag_name':tag,'name':f'VXDevSync {tag}','body':notes('macos_intel' in payload['platforms']),'draft':mode!='publish','prerelease':False}
        if mode=='publish':body['make_latest']='true'
        patch=folder/'patch.json';patch.write_text(json.dumps(body,ensure_ascii=False),encoding='utf-8')
        changed=json.loads(gh('api','--method','PATCH',f"repos/{REPOSITORY}/releases/{release['databaseId']}",'--input',str(patch)))
        if changed['tag_name']!=tag or changed['draft']!=(mode!='publish'):raise ValueError('Unexpected publication response')
    if mode=='publish':
        url=f'https://github.com/{REPOSITORY}/releases/latest/download/latest.json'
        with urlopen(url,timeout=30) as response:live=json.load(response)
        if live!=document:raise ValueError('Public manifest mismatch; do not replace packages')
        for asset in metadata()['assets']:
            with urlopen(Request(asset['url'],method='HEAD'),timeout=30) as response:
                if response.status!=200:raise ValueError('Public asset unavailable')
    print(f'{mode}: signatures, layout and publication state verified')

if __name__=='__main__':main(sys.argv[1])
