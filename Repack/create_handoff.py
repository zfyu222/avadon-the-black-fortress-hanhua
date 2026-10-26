"""Verify installed bytes and prepare explicitly pending user test records."""
import json
import shutil
from pathlib import Path
import build_patch as bp
from install_patch import load, check, safe, game_root


def main():
    root = game_root()
    active = load(bp.HERE/'INSTALLATION.json')
    check(active['status'] == 'installed', 'Patch not installed')
    for relative,expected in active['payload_files'].items():
        check(bp.sha(safe(root,relative)) == expected, 'Installed payload mismatch: '+relative)
    originals = load(bp.PROJECT/'Extraction/source_manifest.json')
    for relative,meta in originals.items():
        check(bp.sha(safe(root,relative)) == meta['sha256'], 'Internal source file modified')
    build = load(bp.HERE/'BUILD_MANIFEST.json')
    for item in build['images']:
        if item['path'] != item['original_source']:
            check(bp.sha(safe(root,item['original_source'])) == item['original_sha256'], 'Original JPG unexpectedly changed')
    # G290 is the native Latin glyph atlas and is explicitly excluded from the payload.
    image_manifest = load(bp.PROJECT/'ImagePatch/build-v4/IMAGE_PATCH_MANIFEST.json')
    atlas = {origin['path']:origin['file_sha256'] for entry in image_manifest['preserved_regions'] for origin in entry['sources'] if '/G290.' in origin['path']}
    check(atlas, 'Glyph atlas preservation evidence missing')
    for relative,expected in atlas.items():
        check(bp.sha(safe(root,relative)) == expected, 'Native glyph atlas changed')
    backup = Path(active['backup_directory'])
    for item in active['records']:
        if item['original_sha256']:
            check(bp.sha(safe(backup,item['path'])) == item['original_sha256'], 'Original backup damaged')
    verification = {'status':'passed','installation_manifest_sha256':bp.sha(bp.HERE/'INSTALLATION.json'),'installed_payload_files':len(active['payload_files']),'protected_exe_scripts_dat_files_unchanged':len(originals),'native_atlas_unchanged':atlas,'all_backups_verified':True,'game_started':False,'in_game_verified':False,'next_step':'user_game_test'}
    bp.write_json(bp.HERE/'INSTALL_VERIFICATION.json',verification)
    payloads = [{'path':'Repack/Payload/'+relative,'game_path':relative,'sha256':expected} for relative,expected in active['payload_files'].items()]
    # The image workflow is an independent project. Its official game-check
    # validator requires payload copies inside that project, never ../ paths.
    image_project = bp.PROJECT/'TranslateFiles/image-text'
    for relative,expected in active['payload_files'].items():
        local_copy = safe(image_project/'Repack/Payload',relative)
        local_copy.parent.mkdir(parents=True,exist_ok=True)
        shutil.copy2(safe(bp.PAYLOAD,relative),local_copy)
        check(bp.sha(local_copy) == expected, 'Image project payload copy mismatch')
    for name,source in [('normal',bp.PROJECT/'TranslateFiles/reports/in_game_check.template.json'),('images',bp.PROJECT/'TranslateFiles/image-text/TranslateFiles/reports/in_game_check.template.json')]:
        record = load(source)
        record.update({'game_version':'Steam build 4252712 / Avadon v1.0s2','platform':'Windows x86','payload_files':payloads,'evidence_files':[]})
        for item in record['checks']:
            item['status']='pending';item['scene']='';item['notes']='待用户实际测试后填写；离线检查不能代替游戏实测。'
        bp.write_json(bp.HERE/('USER_GAME_CHECK_'+name+'.pending.json'),record)
    print(json.dumps(verification,ensure_ascii=False))


if __name__ == '__main__':
    main()
