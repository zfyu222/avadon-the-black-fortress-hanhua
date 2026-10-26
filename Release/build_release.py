"""Prepare the current release from the user's tested payload; never launch Avadon."""
from pathlib import Path
import argparse
import copy
import csv
import hashlib
import json
import shutil
import subprocess
import sys
import tempfile
import zipfile

P=Path(__file__).resolve().parents[1]
WORKSPACE=P.parents[1]
PYTHON=WORKSPACE/'Tools/AINiee/venv/Scripts/python.exe'
FLOW=WORKSPACE/'Tools/localization/translation_workflow.py'
PACKAGER=WORKSPACE/'.agents/skills/game-release-patch/scripts/create_release_patch.py'
DISPATCH=P/'Dispatch'
GAME_NAME='阿瓦登：黑色要塞'
VERSION='1.1'
ARCHIVE=DISPATCH/f'{GAME_NAME}_子非鱼汉化{VERSION}.zip'
REPO='https://github.com/zfyu222/avadon-the-black-fortress-hanhua'
RELEASE=REPO+'/releases/tag/v'+VERSION
GAME_VERSION='Steam Build 4252712 / Avadon v1.0s2'
PLATFORM='Steam Windows 11 x64（游戏与补丁均为 x86）'

def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def load(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(value,ensure_ascii=False,indent=2)+'\n',encoding='utf-8',newline='')
def run(args):subprocess.run([str(x) for x in args],check=True)

def record_user_tests():
    installed=load(P/'Repack/INSTALLATION.json')
    for name,expected in installed['payload_files'].items():
        assert sha(P/'Repack/Payload'/name)==expected
        assert sha(P/'Game'/name)==expected
    evidence={'date':'2026-10-26','tester':'用户本人','source':'本对话用户消息',
        'release_request':'发布吧',
        'question':'当前本地修正版安装后，你是否已重开游戏，确认开门提示、消息栏、快捷键和地图显示正常？若已测试，请简要说明结果；未测试的项目也请注明。',
        'user_response_verbatim':'已测试，上述项目均正常',
        'interpretation':'用户确认当前修正版四项回归均正常并要求发布。仅记录本轮范围；正文译文未改变。',
        'limits':'用户没有另提供本轮逐项场景名称、任务名称或新版截图；不记录全流程通关、全部场景或每张贴图覆盖。此前问题截图不作新版通过证据。',
        'game_version':GAME_VERSION,'platform':PLATFORM,'tested_payload_files':installed['payload_files'],
        'agent_started_game':False}
    evidence_path=P/'Repack/UserTests/confirmation_v1.1_20261026.json';write(evidence_path,evidence)
    for kind,project,template in [
        ('normal',P,P/'Repack/USER_GAME_CHECK_normal.pending.json'),
        ('images',P/'TranslateFiles/image-text',P/'Repack/USER_GAME_CHECK_images.pending.json')]:
        report=load(template);report['game_version']=GAME_VERSION;report['platform']=PLATFORM
        local_evidence=project/'Repack/UserTests/confirmation_v1.1_20261026.json'
        if local_evidence!=evidence_path:write(local_evidence,evidence)
        report['evidence_files']=[dict(path=local_evidence.relative_to(project).as_posix(),sha256=sha(local_evidence))]
        for check in report['checks']:
            category=check['category']
            if category in ('dialogue','quest'):
                check.update(status='not_applicable',scene='',notes='本轮为显示匹配和地图样式增量修复，正式正文译文未改变；未声称本轮重新测试对白分支或全流程任务。v1.0完整类别的用户确认保留于历史记录。消息栏显示本轮已回归。')
            else:
                check.update(status='pass',scene={'fonts':'修正版开门提示、消息栏、快捷键及地图中文显示','layout':'修正版消息栏、快捷键及半透明地图标签排版','ui':'修正版开门提示、消息栏、快捷键及地图界面'}[category],
                    notes='用户对本轮四项回归答复“已测试，上述项目均正常”。据用户实测确认记录；代理未启动游戏，未另提供逐项截图，不推断其他场景覆盖。')
        path=project/f'Repack/UserTests/{kind}_v1.1_game_check.json';write(path,report)
        run([PYTHON,FLOW,'--project',project,'record-game-check','--file',path])
        run([PYTHON,FLOW,'--project',project,'release-check'])

def metadata():
    links=load(P/'Release/player_links.json')
    return dict(introduction='《Avadon: The Black Fortress》简体中文汉化补丁。',
        coverage='游戏正文、菜单、提示及地图文字。',
        install='将补丁解压到 Avadon.exe 所在文件夹。',
        upgrade='将新版解压到同一文件夹即可升级。',
        uninstall='使用最新版提供的“卸载汉化.cmd”。',
        verification='开门提示、消息栏、快捷键和地图显示正常。',**links)

def package(dry_run=False):
    installed=load(P/'Repack/INSTALLATION.json');args=[PYTHON,PACKAGER,'--project',P,'--game-name',GAME_NAME,'--version',VERSION,
        '--game-version',GAME_VERSION,'--platform',PLATFORM,'--release-date','2026-10-26','--changes','修复开门提示数字拼接、消息栏空格及战斗提示、快捷键列表漏译；地图标签改用约25%不透明度的暖色底与描边，并补上两处跨贴图地名。']
    for key,value in metadata().items():args.extend(['--'+key.replace('_','-'),value])
    for relative,expected in installed['payload_files'].items():
        source=P/'Repack/Payload'/relative;assert sha(source)==expected
        args.extend(['--include',str(source)+'='+relative])
    if dry_run:args.append('--dry-run')
    run(args)

def stage():
    expected=load(P/'Repack/INSTALLATION.json')['payload_files']
    base=DISPATCH/'Files';base.mkdir(parents=True,exist_ok=True)
    for relative,digest in expected.items():
        source=P/'Repack/Payload'/relative;target=base/relative
        assert target.resolve().is_relative_to(base.resolve()) and sha(source)==digest
        target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);assert sha(target)==digest
    assert {p.relative_to(base).as_posix():sha(p) for p in base.rglob('*') if p.is_file()}==expected
    print(json.dumps(dict(status='staged_and_checked',files=len(expected)),ensure_ascii=False))

def verify():
    installed=load(P/'Repack/INSTALLATION.json');expected=installed['payload_files']
    with zipfile.ZipFile(ARCHIVE) as archive:
        assert archive.testzip() is None
        assert set(archive.namelist())==set(expected)|{'补丁说明.txt','PATCH_MANIFEST.json','SHA256SUMS.txt'}
        guide=archive.read('补丁说明.txt').decode('utf-8-sig');assert 'v1.0' in guide and 'v1.1' in guide and '25%' in guide
        assert archive.read('补丁说明.txt').startswith(b'\xef\xbb\xbf')
        manifest=json.loads(archive.read('PATCH_MANIFEST.json'))
        assert {e['path']:e['sha256'] for e in manifest['files']}==expected
        sums={line.split('  ',1)[1]:line.split('  ',1)[0] for line in archive.read('SHA256SUMS.txt').decode().splitlines()}
        assert sums==expected
        with tempfile.TemporaryDirectory(prefix='avadon-release-verify-') as directory:
            root=Path(directory);clean=root/'game';clean.mkdir();original=root/'backup';original.mkdir()
            backup=Path(installed['backup_directory'])
            for item in installed['records']:
                if item['original_sha256']:
                    path=clean/item['path'];path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(backup/item['path'],path)
                    saved=original/item['path'];saved.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(path,saved)
            untouched=['Avadon.exe','Avadon Files/Graphics Core/G290.png']
            build=load(P/'Repack/BUILD_MANIFEST.json')
            untouched += [r['original_source'] for r in build['images'] if r['original_source']!=r['path']]
            for name in untouched:
                path=clean/name;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(P/'Game'/name,path)
            baseline={p.relative_to(clean).as_posix():sha(p) for p in clean.rglob('*') if p.is_file()}
            archive.extractall(root/'extracted')
            for relative,digest in expected.items():
                path=clean/relative;path.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(root/'extracted'/relative,path);assert sha(path)==digest
                assert sha(DISPATCH/'Files'/relative)==digest
            for name in untouched:assert sha(clean/name)==baseline[name]
            # Follow the guide's restore/delete operations without starting a game.
            for item in installed['records']:
                path=clean/item['path']
                if item['original_sha256']:shutil.copy2(original/item['path'],path)
                else:path.unlink()
            assert {p.relative_to(clean).as_posix():sha(p) for p in clean.rglob('*') if p.is_file()}==baseline
        for name in ['补丁说明.txt','PATCH_MANIFEST.json','SHA256SUMS.txt']:(DISPATCH/name).write_bytes(archive.read(name))
    write(DISPATCH/'RELEASE_VALIDATION.json',dict(status='passed',archive=ARCHIVE.name,sha256=sha(ARCHIVE),
        payload_files=len(expected),archive_files=len(expected)+3,zip_crc=True,extracted_hashes=True,guide_install_uninstall_roundtrip=True,
        source_exe_and_original_jpg_and_atlas_unchanged=True,agent_started_game=False,user_test_evidence='Repack/UserTests/confirmation_v1.1_20261026.json'))
    print(json.dumps(dict(status='passed',archive=str(ARCHIVE),sha256=sha(ARCHIVE)),ensure_ascii=False))

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('action',choices=['record-tests','dry-run','stage','package','verify']);action=parser.parse_args().action
    if action=='record-tests':record_user_tests()
    elif action=='dry-run':package(True)
    elif action=='package':package()
    elif action=='stage':stage()
    else:verify()
