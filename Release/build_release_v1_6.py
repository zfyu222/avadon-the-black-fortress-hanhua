from pathlib import Path
import sys, shutil, zipfile, subprocess
import build_release_v1_2 as base
from build_release import GAME_VERSION, PLATFORM, PYTHON, PACKAGER
P=base.P
VERSION='1.6'
ARCHIVE=P/f'Dispatch/阿瓦登：黑色要塞_子非鱼汉化{VERSION}.zip'
DICT='AvadonChinese/translations.bin'
def prepare():
    staging=P/'Repack/ReleasePayload16'
    with zipfile.ZipFile(P/'Dispatch/阿瓦登：黑色要塞_子非鱼汉化1.5.zip') as z:
        files=base.load(P/'Dispatch/v1.5/PATCH_MANIFEST.json')['files']
        for row in files:
            target=staging/row['path'];target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(z.read(row['archive_path']));assert base.sha(target)==row['sha256']
    shutil.copy2(P/'Repack/Payload'/DICT,staging/DICT)
    assert base.sha(staging/DICT)==base.load(P/'Repack/UserFeedback/prompt-fix-install.json')['dictionary_sha256']
    info=base.load(P/'Repack/RELEASE_CANDIDATE.json')
    info['payload_files']={r['path']:base.sha(staging/r['path']) for r in files}
    for r in info['records']:r['installed_sha256']=info['payload_files'][r['path']]
    base.write(P/'Repack/RELEASE_CANDIDATE_V16.json',info)
    config=base.load(P/'Release/installer_config.json')
    row=dict(path=DICT,sha256=info['payload_files'][DICT]);
    if row not in config['legacy']:config['legacy'].append(row)
    base.write(P/'Release/installer_config.json',config)
    sys.path.insert(0,str(P.parents[1]/'Tools/localization'))
    from translation_workflow import Workflow
    for project in (P,P/'TranslateFiles/image-text'):
        if project!=P:shutil.copytree(staging,project/'Repack/ReleasePayload16',dirs_exist_ok=True)
        evidence=project/'Repack/ReleaseAcceptance/v1.6.json';evidence.parent.mkdir(parents=True,exist_ok=True)
        base.write(evidence,dict(user_statement='发布吧',in_game_validation='pending',date='2026-11-15',scope='codex and ability targeting notifications'))
        flow=Workflow(project)
        with flow.db() as db: export=flow.meta(db,'last_export')
        flow.record_release_acceptance(dict(authorization='explicit_user_release',in_game_validation='pending',accept_pending_runtime=True,user_statement='发布吧',game_version=GAME_VERSION,platform=PLATFORM,translation_sha256=export['translation_sha256'],payload_files=[dict(path='Repack/ReleasePayload16/'+n,game_path=n,sha256=h) for n,h in info['payload_files'].items()],evidence_files=[dict(path='Repack/ReleaseAcceptance/v1.6.json',sha256=base.sha(evidence))]))
        assert flow.release_check()['status']=='passed'
    return staging,info

def main():
    history=P/'Dispatch/v1.5';history.mkdir(exist_ok=True)
    for name in ('PATCH_MANIFEST.json','SHA256SUMS.txt','补丁说明.txt','RELEASE_VALIDATION.json','GITHUB_RELEASE_VERIFICATION.json'):
        if not (history/name).exists():shutil.copy2(P/'Dispatch'/name,history/name)
    staging,info=prepare()
    args=[PYTHON,PACKAGER,'--project',P,'--game-name','阿瓦登：黑色要塞','--chinese-name','阿瓦登：黑色要塞','--english-name','Avadon: The Black Fortress','--steam-url','https://store.steampowered.com/app/112100/','--version',VERSION,'--game-version',GAME_VERSION,'--platform',PLATFORM,'--release-date','2026-11-15','--introduction','这是一款奇幻队伍角色扮演游戏。你将作为黑色要塞的代理人调查阴谋、招募同伴，在回合制战斗中运用职业技能，并决定如何应对盟约各地的冲突。','--coverage','游戏正文、菜单、提示及地图文字。','--install','解压到 Avadon.exe 所在文件夹，双击“安装汉化.cmd”。','--upgrade','将新版解压到同一文件夹，双击“安装汉化.cmd”。','--uninstall','双击“卸载汉化.cmd”。','--changes','补译 26 个百科主题的首次收录和重复阅读提示，以及治疗之触、野蛮打击、缴械打击的目标选择提示。','--installer-config',P/'Release/installer_config.json']
    for k,v in base.load(P/'Release/player_links.json').items():args.extend(['--'+k.replace('_','-'),v])
    for name in info['payload_files']:args.extend(['--include',str(staging/name)+'='+name])
    for flags in (['--dry-run'],[]):subprocess.run([str(x) for x in args]+flags,check=True)

def verify():
    base.VERSION=VERSION
    base.ARCHIVE=ARCHIVE
    base.INSTALLATION_PATH=P/'Repack/RELEASE_CANDIDATE_V16.json'
    base.VERIFY_PAYLOAD=P/'Repack/ReleasePayload16'
    base.VERIFY_UPGRADE_ARCHIVE=P/'Dispatch/阿瓦登：黑色要塞_子非鱼汉化1.5.zip'
    base.PAYLOAD_BASELINE=None
    base.ACCEPTANCE_VERSION=VERSION
    base.verify()

if __name__=='__main__':
    if '--verify-only' not in sys.argv:main()
    verify()
