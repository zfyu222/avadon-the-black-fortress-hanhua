"""Reversible local installation. Never starts or stops any game process."""
from pathlib import Path, PurePosixPath
from datetime import datetime, timezone
import argparse
import json
import os
import shutil
import subprocess
import tempfile
import build_patch as bp

GAME = Path('D:/Program Files (x86)/Steam/steamapps/common/Avadon The Black Fortress')
ACTIVE = bp.HERE / 'INSTALLATION.json'


def load(path):
    return json.loads(Path(path).read_text(encoding='utf-8-sig'))


def check(condition, message):
    if not condition:
        raise ValueError(message)


def game_root():
    root = GAME.resolve(strict=True)
    check(root == (bp.PROJECT/'Game').resolve(strict=True), 'Game junction no longer points to the authorized directory')
    check(bp.sha(root/'Avadon.exe') == bp.SUPPORTED, 'Unsupported executable')
    command = "@(Get-Process | Where-Object {$_.ProcessName -like 'Avadon*'}).Count"
    result = subprocess.run(['powershell.exe','-NoProfile','-NonInteractive','-Command',command], capture_output=True, text=True, check=True)
    check(result.stdout.strip() == '0', 'Close Avadon before changing the patch; no process was stopped')
    return root


def safe(root, relative):
    item = PurePosixPath(relative)
    check(not item.is_absolute() and bool(item.parts) and all(p not in ('..','.') and ':' not in p and '\\' not in p for p in item.parts), 'Unsafe relative path')
    path = root.joinpath(*item.parts)
    check(path.resolve().is_relative_to(root.resolve()), 'Path escapes intended directory')
    return path


def atomic_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.avzh-', suffix='.tmp', dir=destination.parent)
    try:
        with os.fdopen(fd, 'wb') as target, Path(source).open('rb') as origin:
            shutil.copyfileobj(origin, target)
            target.flush();os.fsync(target.fileno())
        check(bp.sha(temporary) == bp.sha(source), 'Staging copy hash mismatch')
        os.replace(temporary, destination)
    finally:
        if Path(temporary).exists():
            Path(temporary).unlink()


def validate_payload():
    report = load(bp.HERE/'STATIC_VALIDATION.json')
    check(report['status'] == 'passed' and report['in_game_verified'] is False, 'Static validation missing')
    check(bp.sha(bp.HERE/'BUILD_MANIFEST.json') == report['build_manifest_sha256'], 'Build changed after validation')
    check(bp.sha(bp.HERE/'NativeTests/report.json') == report['component_report_sha256'], 'Component test report changed')
    inventory = {p.relative_to(bp.PAYLOAD).as_posix(): bp.sha(p) for p in bp.PAYLOAD.rglob('*') if p.is_file()}
    check(inventory == report['payload_files'], 'Payload changed after validation')
    return report, load(bp.HERE/'BUILD_MANIFEST.json')


def install(preview=False):
    root = game_root();validation,manifest = validate_payload()
    if ACTIVE.exists() and load(ACTIVE)['status'] == 'installed':
        current = load(ACTIVE)
        check(current['payload_files'] == validation['payload_files'], 'A different patch is already installed; uninstall it first')
        for relative,expected in current['payload_files'].items():
            check(bp.sha(safe(root,relative)) == expected, 'Installed file has changed')
        print(json.dumps({'status':'already_installed','files':len(current['payload_files'])}));return
    originals = {item['path']:item['original_sha256'] for item in manifest['images'] if item['path'] == item['original_source']}
    records = []
    for relative,expected in validation['payload_files'].items():
        target = safe(root,relative)
        prior = bp.sha(target) if target.exists() else None
        if relative in originals:
            check(prior == originals[relative], 'Original resource changed: '+relative)
        else:
            check(prior is None, 'Unexpected existing file: '+relative)
        records.append({'path':relative,'original_sha256':prior,'installed_sha256':expected})
    if preview:
        print(json.dumps({'status':'preflight_passed','files':len(records),'overwritten':sum(r['original_sha256'] is not None for r in records),'new':sum(r['original_sha256'] is None for r in records),'game_started':False}));return
    # All originals are copied and verified before the first game file changes.
    stamp = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    backup = bp.HERE/'Backups'/stamp
    backup.mkdir(parents=True,exist_ok=False)
    for item in records:
        if item['original_sha256'] is not None:
            target = safe(backup,item['path']);target.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(safe(root,item['path']),target)
            check(bp.sha(target) == item['original_sha256'], 'Backup verification failed')
    journal = {'status':'backed_up','game_root':str(root),'created_utc':stamp,'backup_directory':str(backup),'records':records,'payload_files':validation['payload_files'],'static_validation_sha256':bp.sha(bp.HERE/'STATIC_VALIDATION.json'),'game_started':False,'in_game_verified':False}
    bp.write_json(backup/'manifest.json',journal)
    written = []
    try:
        for item in records:
            relative = item['path'];target = safe(root,relative)
            current = bp.sha(target) if target.exists() else None
            check(current == item['original_sha256'], 'File changed during installation')
            atomic_copy(safe(bp.PAYLOAD,relative),target);written.append(item)
        for item in records:
            check(bp.sha(safe(root,item['path'])) == item['installed_sha256'], 'Installed hash mismatch')
        check(bp.sha(root/'Avadon.exe') == bp.SUPPORTED, 'Executable changed unexpectedly')
    except Exception:
        for item in reversed(written):
            target = safe(root,item['path'])
            check(bp.sha(target) == item['installed_sha256'], 'Concurrent modification prevents automatic rollback')
            if item['original_sha256']:
                atomic_copy(safe(backup,item['path']),target)
            else:
                target.unlink()
        journal['status'] = 'rolled_back';bp.write_json(backup/'manifest.json',journal)
        raise
    journal['status'] = 'installed'
    bp.write_json(backup/'manifest.json',journal);bp.write_json(ACTIVE,journal)
    print(json.dumps({'status':'installed','files':len(records),'backup_directory':str(backup),'game_started':False,'in_game_verified':False}))


def uninstall():
    root = game_root();journal = load(ACTIVE)
    check(journal['status'] == 'installed' and Path(journal['game_root']).resolve() == root, 'No matching active installation')
    backup = Path(journal['backup_directory']).resolve(strict=True)
    check(backup.is_relative_to((bp.HERE/'Backups').resolve()), 'Backup outside project')
    # Preflight the complete set before removing or restoring any file.
    for item in journal['records']:
        check(bp.sha(safe(root,item['path'])) == item['installed_sha256'], 'Installed file was modified; preserve it and resolve manually: '+item['path'])
        if item['original_sha256']:
            check(bp.sha(safe(backup,item['path'])) == item['original_sha256'], 'Backup damaged')
    for item in reversed(journal['records']):
        target = safe(root,item['path'])
        if item['original_sha256']:
            atomic_copy(safe(backup,item['path']),target)
        else:
            target.unlink()
    for item in journal['records']:
        target = safe(root,item['path'])
        check((bp.sha(target) if target.exists() else None) == item['original_sha256'], 'Restore verification failed')
    journal['status'] = 'uninstalled';bp.write_json(ACTIVE,journal)
    print(json.dumps({'status':'uninstalled','restored_or_removed':len(journal['records'])}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser();parser.add_argument('action',choices=['preflight','install','uninstall']);args = parser.parse_args()
    if args.action == 'uninstall':
        uninstall()
    else:
        install(args.action == 'preflight')
