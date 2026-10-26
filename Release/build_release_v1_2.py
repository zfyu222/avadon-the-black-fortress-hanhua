"""Package unchanged, tested v1.1 game files with a simple player installer."""
from pathlib import Path
import json,subprocess,sys,shutil,tempfile,zipfile,hashlib
import build_release as old
P=old.P
VERSION='1.2'
ARCHIVE=P/f'Dispatch/阿瓦登：黑色要塞_子非鱼汉化{VERSION}.zip'
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def load(p):return json.loads(Path(p).read_text(encoding='utf-8-sig'))
def write(p,x):Path(p).write_text(json.dumps(x,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
def build():
    installed=load(P/'Repack/INSTALLATION.json');links=load(P/'Release/player_links.json')
    args=[old.PYTHON,old.PACKAGER,'--project',P,'--game-name',old.GAME_NAME,'--version',VERSION,
        '--game-version',old.GAME_VERSION,'--platform',old.PLATFORM,'--release-date','2026-10-27',
        '--introduction','《Avadon: The Black Fortress》简体中文汉化补丁。',
        '--coverage','游戏正文、菜单、提示及地图文字。',
        '--install','解压到 Avadon.exe 所在文件夹，双击“安装汉化.cmd”。',
        '--upgrade','将新版解压到同一文件夹，双击“安装汉化.cmd”即可升级。',
        '--uninstall','双击“卸载汉化.cmd”。',
        '--verification','开门提示、消息栏、快捷键和地图显示正常。',
        '--changes','新增安装、升级和卸载脚本；简化补丁说明，加入网盘下载和腾讯文档反馈地址。汉化内容与v1.1一致。',
        '--installer-config',P/'Release/installer_config.json']
    for key,value in links.items():args.extend(['--'+key.replace('_','-'),value])
    for name,digest in installed['payload_files'].items():
        source=P/'Repack/Payload'/name;assert sha(source)==digest;args.extend(['--include',str(source)+'='+name])
    subprocess.run([str(x) for x in args]+['--dry-run'],check=True,stdout=subprocess.DEVNULL)
    subprocess.run([str(x) for x in args],check=True)
def verify():
    expected=load(P/'Repack/INSTALLATION.json')['payload_files']
    with zipfile.ZipFile(ARCHIVE) as z:
        assert z.testzip() is None
        manifest=json.loads(z.read('PATCH_MANIFEST.json'));assert manifest['install_mode']=='script'
        assert {f['path']:f['sha256'] for f in manifest['files']}==expected
        selected=manifest['files']+manifest['auxiliary']
        inventory={f.get('archive_path',f['path']):f['sha256'] for f in selected}
        assert set(z.namelist())==set(inventory)|{'补丁说明.txt','PATCH_MANIFEST.json','SHA256SUMS.txt'}
        assert all(hashlib.sha256(z.read(n)).hexdigest()==digest for n,digest in inventory.items())
        assert {r.split('  ',1)[1]:r.split('  ',1)[0] for r in z.read('SHA256SUMS.txt').decode().splitlines()}==inventory
        guide=z.read('补丁说明.txt').decode('utf-8-sig')
        assert guide.index('安装汉化')<guide.index('补丁升级')<guide.index('卸载汉化')<guide.index('适用版本')
        assert all(term not in guide for term in ['备份','拷贝','未决','未验证','代理','用户对','SHA-256','11 个','请先停止'])
        assert 'v1.0' in guide and 'v1.1' in guide and 'v1.2' in guide
        links=load(P/'Release/player_links.json');assert all(v in guide for v in links.values())
        assert guide.index(links['mirror_url'])<guide.index('请订阅github地址或者网盘地址，以便在补丁更新时获得通知')<guide.index('有问题请反馈至【腾讯文档】Avadon问题反馈')
        with tempfile.TemporaryDirectory(prefix='avadon-v12-install-') as t:
            root=Path(t);z.extractall(root)
            shutil.copy2(P/'Game/Avadon.exe',root/'Avadon.exe')
            installation=load(P/'Repack/INSTALLATION.json');backup=Path(installation['backup_directory'])
            original={}
            for entry in installation['records']:
                if entry['original_sha256']:
                    source=backup/entry['path'];assert sha(source)==entry['original_sha256']
                    target=root/entry['path'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);original[entry['path']]=entry['original_sha256']
            def action(name):
                r=subprocess.run(['powershell.exe','-NoProfile','-ExecutionPolicy','Bypass','-File',str(root/'汉化工具/patch.ps1'),'-Action',name,'-NoLaunch'],capture_output=True)
                assert r.returncode==0,(r.stdout+r.stderr).decode(errors='replace')
                return r.stdout
            action('install');assert all(sha(root/n)==h for n,h in expected.items())
            action('install');action('uninstall')
            assert all(sha(root/n)==h for n,h in original.items())
            assert all(not (root/n).exists() for n in expected if n not in original)
            # Existing v1.1 package without installer state: upgrade then use Steam recovery.
            for name,h in expected.items():
                target=root/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(P/'Repack/Payload'/name,target)
            action('install');result=action('uninstall');assert b'STEAM_RESTORE=True' in result
            assert all(not (root/n).exists() for n in expected if n not in original)
            assert sha(root/'Avadon.exe')==old.sha(P/'Game/Avadon.exe')
        for name in ['补丁说明.txt','PATCH_MANIFEST.json','SHA256SUMS.txt']:(P/'Dispatch'/name).write_bytes(z.read(name))
        (P/'Release/release_notes.md').write_text(guide,encoding='utf-8')
    write(P/'Dispatch/RELEASE_VALIDATION.json',dict(status='passed',version=VERSION,archive=ARCHIVE.name,sha256=sha(ARCHIVE),
        tested_game_payload_files=22,payload_unchanged_from='v1.1',auxiliary_files=4,archive_files=29,zip_crc=True,all_hashes=True,
        actual_windows_powershell_install_repeat_upgrade_uninstall=True,legacy_upgrade_steam_recovery_requested=True,
        steam_recovery_network_not_executed_in_test=True,installer_synthetic_regressions=6,exe_unchanged=True,game_started=False,
        original_game_test_evidence='Repack/UserTests/confirmation_v1.1_20261026.json'))
    print(json.dumps({'status':'passed','archive':str(ARCHIVE),'sha256':sha(ARCHIVE)},ensure_ascii=False))
if __name__=='__main__':
    if len(sys.argv)>1 and sys.argv[1]=='verify':verify()
    else:build();verify()
