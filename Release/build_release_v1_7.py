"""Build the polished dictionary and replay the v1.6 to v1.7 installer upgrade."""
import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import zipfile

import build_release_v1_2 as installer
from build_release import DISPATCH, GAME_NAME, GAME_VERSION, P, PACKAGER, PLATFORM, PYTHON, WORKSPACE, load, sha, write

VERSION = '1.7'
DATE = '2026-11-25'
DICT = 'AvadonChinese/translations.bin'
ARCHIVE = DISPATCH / f'{GAME_NAME}_子非鱼汉化{VERSION}.zip'
PREVIOUS = DISPATCH / f'{GAME_NAME}_子非鱼汉化1.6.zip'
OPTIONAL_OLD = DISPATCH / '(可选)阿瓦登_体验优化补丁_2.3.zip'
OPTIONAL = DISPATCH / '(可选)阿瓦登_体验优化补丁_2.4.zip'
STAGING = P / 'Repack/Build/ReleasePayload17'
CANDIDATE = P / 'Repack/Build/RELEASE_CANDIDATE_V17.json'
COVER = 'https://raw.githubusercontent.com/zfyu222/avadon-the-black-fortress-hanhua/main/Dispatch/Artwork/title.jpg'
OPTIONAL_TEXT = ('提供字号调节、镜头跟随、队伍探索加速、背包快捷键和可交互物标记。'
                 '已使用旧版体验优化的玩家，请先在“阿瓦登增强设置.exe”中选择“还原增强补丁”，再升级主汉化。'
                 '安装主汉化后，将体验优化补丁 v2.4 解压到同一文件夹，打开“阿瓦登增强设置.exe”，点击“保存并应用”。')


def prepare_payload():
    sys.path.insert(0, str(P / 'Repack'))
    import build_patch

    with zipfile.ZipFile(PREVIOUS) as archive:
        manifest = json.loads(archive.read('PATCH_MANIFEST.json'))
        for entry in manifest['files']:
            target = STAGING / entry['path']
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(archive.read(entry['archive_path']))
            assert sha(target) == entry['sha256']
    build_patch.PAYLOAD = STAGING
    dictionary = build_patch.dictionary()
    candidate = load(P / 'Repack/RELEASE_CANDIDATE_V16.json')
    candidate['payload_files'][DICT] = dictionary['dictionary_sha256']
    for entry in candidate['records']:
        entry['installed_sha256'] = candidate['payload_files'][entry['path']]
    write(CANDIDATE, candidate)
    return candidate['payload_files']


def authorize(payload):
    sys.path.insert(0, str(WORKSPACE / 'Tools/localization'))
    from translation_workflow import Workflow

    evidence = P / 'Repack/ReleaseAcceptance/v1.7.json'
    write(evidence, {'user_statement': '发布吧', 'date': DATE, 'in_game_validation': 'pending',
                     'scope': '发布已完成独立复审的正文润色版'})
    flow = Workflow(P)
    report = load(P / 'TranslateFiles/reports/final_validation.json')
    flow.record_release_acceptance({
        'authorization': 'explicit_user_release', 'in_game_validation': 'pending',
        'accept_pending_runtime': True, 'user_statement': '发布吧', 'game_version': GAME_VERSION,
        'platform': PLATFORM, 'translation_sha256': report['translation_sha256'],
        'payload_files': [{'path': (STAGING / name).relative_to(P).as_posix(), 'game_path': name,
                           'sha256': digest} for name, digest in payload.items()],
        'evidence_files': [{'path': evidence.relative_to(P).as_posix(), 'sha256': sha(evidence)}],
    })
    assert flow.release_check()['status'] == 'passed'


def build_optional(dictionary_hash):
    with zipfile.ZipFile(OPTIONAL_OLD) as archive:
        assert archive.testzip() is None
        files = {name: archive.read(name) for name in archive.namelist() if not name.endswith('/')}
    sums = files.pop('SHA256SUMS.txt').decode('utf-8-sig').splitlines()
    assert {name: hashlib.sha256(data).hexdigest() for name, data in files.items()} == {
        name: digest for digest, name in (line.split('  ', 1) for line in sums)}
    manifest = json.loads(files['font-manifest.json'])
    manifest.update(version='enhancement-2.4', dictionary_sha256=dictionary_hash)
    manifest['supported_dictionary_sha256'] = sorted(set(manifest['supported_dictionary_sha256']) | {dictionary_hash})
    files['font-manifest.json'] = (json.dumps(manifest, ensure_ascii=False, indent=2) + '\n').encode()
    guide = files['增强补丁说明.txt'].decode('utf-8-sig').replace('v2.3', 'v2.4', 1)
    files['增强补丁说明.txt'] = (guide.rstrip() + '\n\nv2.4：兼容主汉化 v1.7 的润色词典。\n').encode('utf-8-sig')
    checksums = ''.join(f'{hashlib.sha256(files[name]).hexdigest()}  {name}\n' for name in sorted(files))
    with zipfile.ZipFile(OPTIONAL, 'x', zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in files.items():
            archive.writestr(name, data)
        archive.writestr('SHA256SUMS.txt', checksums.encode('utf-8-sig'))
    with zipfile.ZipFile(OPTIONAL) as archive:
        assert archive.testzip() is None
        assert all(archive.read(name) == data for name, data in files.items())
    return manifest


def build_main(payload):
    config_path = P / 'Release/installer_config.json'
    config = load(config_path)
    entry = {'path': DICT, 'sha256': payload[DICT]}
    if entry not in config['legacy']:
        config['legacy'].append(entry)
        write(config_path, config)
    args = [PYTHON, PACKAGER, '--project', P, '--game-name', GAME_NAME, '--chinese-name', GAME_NAME,
            '--english-name', 'Avadon: The Black Fortress', '--steam-url', 'https://store.steampowered.com/app/112100/',
            '--version', VERSION, '--game-version', GAME_VERSION, '--platform', PLATFORM, '--release-date', DATE,
            '--introduction', '这是一款奇幻队伍角色扮演游戏。你将作为黑色要塞的代理人调查阴谋、招募同伴，在回合制战斗中运用职业技能，并决定如何应对盟约各地的冲突。',
            '--coverage', '游戏正文、菜单、提示及地图文字。\n\n体验优化补丁（可选，推荐使用）\n' + OPTIONAL_TEXT,
            '--install', '解压到 Avadon.exe 所在文件夹，双击“安装汉化.cmd”。',
            '--upgrade', '将新版解压到同一文件夹，双击“安装汉化.cmd”。',
            '--uninstall', '双击“卸载汉化.cmd”。', '--changes', '润色 2,777 条正文，改善对白、叙事和教程表达。',
            '--installer-config', config_path]
    for key, value in load(P / 'Release/player_links.json').items():
        args.extend(['--' + key.replace('_', '-'), value])
    for name in payload:
        args.extend(['--include', f'{STAGING / name}={name}'])
    subprocess.run([str(arg) for arg in args], check=True)


def verify_optional(payload, manifest):
    with tempfile.TemporaryDirectory(prefix='avadon-v17-中文 空格-') as temp:
        root = Path(temp)
        with zipfile.ZipFile(OPTIONAL) as archive:
            archive.extractall(root)
        shutil.copy2(P / 'Game/Avadon.exe', root / 'Avadon.exe')
        for name in ('winmm.dll', DICT):
            (root / name).parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(STAGING / name, root / name)
        script = root / '字体增强.ps1'
        command = ['powershell.exe', '-NoProfile', '-NonInteractive', '-ExecutionPolicy', 'Bypass',
                   '-File', str(script), '-GameRoot', str(root), '-Action']
        subprocess.run(command + ['install'], check=True)
        assert sha(root / 'winmm.dll') == manifest['files']['winmm.dll']
        settings = root / 'AvadonChinese/font.ini'
        settings.write_bytes(b'[Font]\r\nScalePercent=125\r\nFitLabels=0\r\n')
        before = settings.read_bytes()
        subprocess.run(command + ['install'], check=True)
        assert settings.read_bytes() == before
        subprocess.run(command + ['uninstall'], check=True)
        assert sha(root / 'winmm.dll') == payload['winmm.dll']
        assert sha(root / DICT) == payload[DICT]
    write(DISPATCH / 'ENHANCEMENT_V24_VALIDATION.json', {
        'status': 'passed', 'archive': OPTIONAL.name, 'sha256': sha(OPTIONAL),
        'dictionary_sha256': payload[DICT], 'installer_cases': ['install', 'repeat_preserves_settings', 'uninstall'],
    })


def sync_local():
    candidate = load(CANDIDATE)
    game = (P / 'Game').resolve()
    assert game == Path(candidate['game_root']).resolve()
    assert sha(game / 'Avadon.exe') == load(P / 'Release/installer_config.json')['exe_sha256']
    process = subprocess.run(['tasklist.exe', '/FI', 'IMAGENAME eq Avadon.exe', '/FO', 'CSV', '/NH'],
                             check=True, capture_output=True)
    if b'"Avadon.exe"' in process.stdout:
        raise RuntimeError('Avadon is running')
    state_rel = '.zfy-localization/state.json'
    optional_rel = 'font-manifest.json'
    state = load(game / state_rel)
    assert state['status'] == 'installed'
    record = next(entry for entry in state['records'] if entry['path'] == DICT)
    old_hash = sha(game / DICT)
    new_hash = candidate['payload_files'][DICT]
    assert sha(STAGING / DICT) == new_hash
    enhancements = load(game / '.zfy-font-enhancement/state.json')
    assert enhancements['status'] == 'installed'
    assert sha(game / 'winmm.dll') == enhancements['dll_installed']
    assert sha(game / '.zfy-font-enhancement/winmm.dll') == candidate['payload_files']['winmm.dll']
    for name, digest in candidate['payload_files'].items():
        if name not in (DICT, 'winmm.dll'):
            assert sha(game / name) == digest
    with zipfile.ZipFile(OPTIONAL_OLD) as before, zipfile.ZipFile(OPTIONAL) as after:
        old_manifest = before.read(optional_rel)
        new_manifest = after.read(optional_rel)
    assert (game / optional_rel).read_bytes() in (old_manifest, new_manifest) or (
        load(game / optional_rel) == json.loads(old_manifest))
    if old_hash == new_hash and record['installed'] == new_hash and (game / optional_rel).read_bytes() == new_manifest:
        return
    assert old_hash == load(P / 'Repack/RELEASE_CANDIDATE_V16.json')['payload_files'][DICT]
    names = (DICT, state_rel, optional_rel)
    backup = P / 'Repack/Backups' / datetime.now(timezone.utc).strftime('v17-%Y%m%dT%H%M%S%fZ')
    for name in names:
        target = backup / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(game / name, target)
    record.update(installed=new_hash, previous=old_hash)
    updates = {DICT: (STAGING / DICT).read_bytes(), optional_rel: new_manifest,
               state_rel: (json.dumps(state, ensure_ascii=False, indent=2) + '\n').encode('utf-8-sig')}

    def replace(name, data):
        target = game / name
        with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as stream:
            stream.write(data)
            pending = Path(stream.name)
        try:
            os.replace(pending, target)
        finally:
            pending.unlink(missing_ok=True)

    try:
        for name, data in updates.items():
            replace(name, data)
        assert all((game / name).read_bytes() == data for name, data in updates.items())
    except Exception:
        for name in names:
            replace(name, (backup / name).read_bytes())
        raise
    write(P / 'Repack/Build/LOCAL_DEPLOYMENT_V17.json', {
        'status': 'installed', 'game_root': str(game), 'backup_directory': str(backup),
        'dictionary_sha256': new_hash, 'preserved_enhancement_dll_sha256': enhancements['dll_installed'],
        'game_started': False,
    })


def main():
    if ARCHIVE.exists() or OPTIONAL.exists():
        raise FileExistsError('Release archives already exist')
    history = DISPATCH / 'v1.6'
    history.mkdir(exist_ok=True)
    for name in ('PATCH_MANIFEST.json', 'SHA256SUMS.txt', '补丁说明.txt', 'RELEASE_VALIDATION.json', 'GITHUB_RELEASE_VERIFICATION.json'):
        if not (history / name).exists():
            shutil.copy2(DISPATCH / name, history / name)
    payload = prepare_payload()
    authorize(payload)
    optional = build_optional(payload[DICT])
    verify_optional(payload, optional)
    build_main(payload)
    installer.VERSION = VERSION
    installer.ARCHIVE = ARCHIVE
    installer.INSTALLATION_PATH = CANDIDATE
    installer.VERIFY_PAYLOAD = STAGING
    installer.VERIFY_UPGRADE_ARCHIVE = PREVIOUS
    installer.PAYLOAD_BASELINE = None
    installer.ACCEPTANCE_VERSION = VERSION
    installer.verify()
    notes = P / 'Release/release_notes.md'
    body = notes.read_text(encoding='utf-8')
    body = body.replace('\n游戏介绍\n', '\n### 游戏介绍\n\n')
    body = body.replace('\n体验优化补丁（可选，推荐使用）\n', '\n### 体验优化补丁（可选，推荐使用）\n\n')
    links = load(P / 'Release/player_links.json')['download_url'].rstrip('/') + '/download/v1.7/'
    body = body.replace('### 安装汉化', f'[下载汉化补丁 v1.7]({links}Avadon_The_Black_Fortress_1.7.zip)\n\n### 安装汉化')
    body = body.replace(OPTIONAL_TEXT, f'[下载体验优化补丁 v2.4]({links}Avadon_Enhancement_2.4.zip)\n\n{OPTIONAL_TEXT}')
    notes.write_text(f'![阿瓦登子非鱼汉化封面]({COVER})\n\n{body}', encoding='utf-8')


if __name__ == '__main__':
    if sys.argv[1:] == ['--sync-local']:
        sync_local()
    else:
        main()
