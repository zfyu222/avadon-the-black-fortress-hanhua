"""Local camera/font enhancement package and isolated installer regression."""
from pathlib import Path
import configparser
import hashlib
import json
import os
import shutil
import subprocess
import tempfile
import zipfile
import build_patch as bp

ROOT=bp.HERE/'Enhancement'
FILES=ROOT/'GuiFiles'
TESTS=ROOT/'Tests'

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def run(root,action='install',scale=None,follow=None,ok=True,script=None,speed=None):
    cmd=['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script or FILES/'字体增强.ps1'),'-GameRoot',str(root),'-Action',action]
    if scale is not None:cmd+=['-Scale',str(scale)]
    if follow is not None:cmd+=['-Follow',str(follow)]
    if speed is not None:cmd+=['-Speed',str(speed)]
    p=subprocess.run(cmd,capture_output=True)
    assert (p.returncode==0)==ok,(p.stdout+p.stderr).decode('utf-8',errors='replace')

def config(path):
    c=configparser.ConfigParser();c.read(path,encoding='utf-8-sig');return c

def main():
    build=read(ROOT/'BUILD_MANIFEST.json');dll=ROOT/'Payload/winmm.dll'
    assert bp.sha(dll)==build['dll_sha256']
    for name,digest in build['native_sources'].items():assert bp.sha(bp.HERE/'native'/name)==digest
    assert read(TESTS/'report.json')['status']=='passed' and read(TESTS/'camera_report.json')['status']=='passed'
    # Keep the committed build summary small; full dictionary evidence stays in Build/.
    build['dictionary']={k:build['dictionary'][k] for k in ['records','keys','source_sha256','translation_sha256','dictionary_sha256','original_game_data_modified']}
    bp.write_json(ROOT/'BUILD_MANIFEST.json',build)
    # This known font install keeps the pre-enhancement Chinese plugin here.
    baseline=bp.PROJECT/'Game/.zfy-font-enhancement/winmm.dll'
    baseline_hash=read(bp.HERE/'BUILD_MANIFEST.json')['dll_sha256']
    assert bp.sha(baseline)==baseline_hash
    font_dll=bp.HERE/'FontEnhancement/Payload/winmm.dll'
    font_hash=read(bp.HERE/'FontEnhancement/BUILD_MANIFEST.json')['dll_sha256'];assert bp.sha(font_dll)==font_hash
    (FILES/'字体文件').mkdir(parents=True,exist_ok=True)
    shutil.copy2(dll,FILES/'字体文件/winmm.dll')
    (FILES/'字体文件/font.ini').write_bytes(b'[Font]\r\nScalePercent=150\r\nFitLabels=1\r\n')
    (FILES/'字体文件/camera.ini').write_bytes(b'[Camera]\r\nFollowCharacter=1\r\n\r\n[Inventory]\r\nToggleHotkey=1\r\n\r\n[Interaction]\r\nHighlightOnShift=1\r\n')
    (FILES/'字体增强.ps1').write_text((bp.HERE/'enhancement.ps1').read_text(encoding='utf-8'),encoding='utf-8-sig')
    csc=Path(os.environ['WINDIR'])/'Microsoft.NET/Framework64/v4.0.30319/csc.exe'
    source=bp.HERE/'EnhancementSettings.cs'
    compiler=[str(csc),'/nologo','/target:winexe','/optimize+','/codepage:65001','/r:System.Windows.Forms.dll','/r:System.Drawing.dll']
    settings_exe=FILES/'阿瓦登增强设置.exe'
    subprocess.run(compiler+['/out:'+str(settings_exe),str(source)],check=True)
    previous13=read(ROOT/'v1.3_VALIDATION.json')
    assert bp.sha(ROOT/'阿瓦登_字体与镜头增强_1.3.zip')==previous13['archive_sha256']
    previous=read(ROOT/'v1.2_VALIDATION.json')
    previous_zip=ROOT/'阿瓦登_字体与镜头增强_1.2.zip'
    assert bp.sha(previous_zip)==previous['archive_sha256']
    previous14=read(ROOT/'v1.4_VALIDATION.json')
    previous15=read(ROOT/'v1.5_VALIDATION.json')
    previous17=read(ROOT/'v1.7_VALIDATION.json')
    manifest={'version':'enhancement-1.8','exe_sha256':bp.SUPPORTED,'dictionary_sha256':build['dictionary']['dictionary_sha256'],
              'supported_dll_sha256':sorted({baseline_hash,font_hash,previous['dll_sha256'],previous13['dll_sha256'],previous14['dll_sha256'],previous15['dll_sha256'],previous17['dll_sha256'],bp.sha(dll)}),'files':{n:bp.sha(FILES/'字体文件'/n) for n in ['winmm.dll','font.ini','camera.ini']}}
    bp.write_json(FILES/'font-manifest.json',manifest)
    (FILES/'增强补丁说明.txt').write_text(
        '阿瓦登：黑色要塞 增强补丁 v1.8\n\n'
        '退出游戏，把补丁解压到 Avadon.exe 所在文件夹。双击“阿瓦登增强设置.exe”，'
        '调整后点击“保存并应用”，再启动游戏。首次保存会安装增强补丁。\n\n'
        '可调整字号、标签自动缩小、镜头跟随、背包快捷键、探索移动速度和交互物标记。'
        '移动速度100%为原速，最高200%。按住Shift会在可见的可交互物上显示金色感叹号。\n'
        '点击“还原增强补丁”可恢复增强前的设置。\n\n'
        '适用版本：Steam Build 4252712 / Avadon v1.0s2，需要先安装子非鱼汉化。\n',
        encoding='utf-8-sig')
    assert read(TESTS/'inventory_report.json')['status']=='passed'
    assert read(TESTS/'movement_report.json')['status']=='passed'
    assert read(TESTS/'interaction_report.json')['status']=='passed'
    cases=[]
    with tempfile.TemporaryDirectory(prefix='avadon-camera-中文 空格-') as temp:
        game=Path(temp)/'游戏 空格';(game/'AvadonChinese').mkdir(parents=True)
        shutil.copy2(bp.PROJECT/'Game/Avadon.exe',game/'Avadon.exe')
        shutil.copy2(bp.PROJECT/'Game/AvadonChinese/translations.bin',game/'AvadonChinese/translations.bin')
        shutil.copy2(baseline,game/'winmm.dll')
        run(game);assert bp.sha(game/'winmm.dll')==bp.sha(dll)
        assert config(game/'AvadonChinese/camera.ini')['Camera']['FollowCharacter']=='1';cases.append('fresh_install_defaults')
        run(game,'scale',scale=125);run(game,'camera',follow=0);run(game)
        assert config(game/'AvadonChinese/font.ini')['Font']['ScalePercent']=='125' and config(game/'AvadonChinese/camera.ini')['Camera']['FollowCharacter']=='0'
        cases.append('repeat_preserves_font_and_camera')
        run(game,'camera',follow=1);run(game,'scale',scale=150);assert config(game/'AvadonChinese/camera.ini')['Camera']['FollowCharacter']=='1';cases.append('independent_toggles')
        run(game,'uninstall');assert bp.sha(game/'winmm.dll')==baseline_hash and not (game/'AvadonChinese/font.ini').exists() and not (game/'AvadonChinese/camera.ini').exists()
        run(game,'uninstall');cases.append('fresh_uninstall_idempotent')
        # Replay an actual previous font-only installation and upgrade in place.
        run(game,script=bp.HERE/'FontEnhancement/Files/字体增强.ps1')
        font_ini=game/'AvadonChinese/font.ini';font_ini.write_bytes(b'[Font]\r\nScalePercent=125\r\nFitLabels=0\r\nExtra=keep\r\n')
        camera_ini=game/'AvadonChinese/camera.ini';camera_ini.write_bytes(b'[Camera]\r\nFollowCharacter=0\r\nExtra=old\r\n')
        camera_before=camera_ini.read_bytes();run(game)
        assert bp.sha(game/'winmm.dll')==bp.sha(dll) and config(font_ini)['Font']['ScalePercent']=='125' and config(font_ini)['Font']['FitLabels']=='0' and camera_ini.read_bytes()==camera_before
        assert bp.sha(game/'.zfy-font-enhancement/winmm.dll')==baseline_hash;cases.append('font_v1_1_upgrade_preserves_original_backup_and_options')
        before_dll=bp.sha(game/'winmm.dll');before_ini=font_ini.read_bytes();run(game,'scale',scale=99,ok=False);assert bp.sha(game/'winmm.dll')==before_dll and font_ini.read_bytes()==before_ini;cases.append('invalid_scale_no_write')
        run(game,'camera',follow=1);run(game,'uninstall');assert bp.sha(game/'winmm.dll')==baseline_hash and not font_ini.exists() and camera_ini.read_bytes()==camera_before;cases.append('upgrade_uninstall_restores_pre_camera_config')
        old_files=Path(temp)/'old-v1.2';old_files.mkdir()
        with zipfile.ZipFile(previous_zip) as old:
            for name,digest in previous['files'].items():
                target=old_files/name;assert target.resolve().is_relative_to(old_files.resolve())
                data=old.read(name);assert hashlib.sha256(data).hexdigest()==digest
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        run(game,script=old_files/'字体增强.ps1')
        assert bp.sha(game/'winmm.dll')==previous['dll_sha256']
        font_ini.write_bytes(b'[Font]\r\nScalePercent=125\r\nFitLabels=0\r\n')
        run(game);assert bp.sha(game/'winmm.dll')==bp.sha(dll) and config(font_ini)['Font']['ScalePercent']=='125'
        assert bp.sha(game/'.zfy-font-enhancement/winmm.dll')==baseline_hash
        run(game,'uninstall');cases.append('camera_v1_2_upgrade_preserves_font_and_original_backup')
        old13=Path(temp)/'old-v1.3';old13.mkdir()
        with zipfile.ZipFile(ROOT/'阿瓦登_字体与镜头增强_1.3.zip') as old:
            for name,digest in previous13['files'].items():
                target=old13/name;assert target.resolve().is_relative_to(old13.resolve())
                data=old.read(name);assert hashlib.sha256(data).hexdigest()==digest
                target.parent.mkdir(parents=True,exist_ok=True);target.write_bytes(data)
        run(game,script=old13/'字体增强.ps1')
        font_ini.write_bytes(b'[Font]\r\nScalePercent=125\r\nFitLabels=0\r\n')
        camera_ini.write_bytes(b'[Camera]\r\nFollowCharacter=0\r\n')
        run(game);assert bp.sha(game/'winmm.dll')==bp.sha(dll)
        assert config(font_ini)['Font']['ScalePercent']=='125' and config(camera_ini)['Camera']['FollowCharacter']=='0'
        run(game,'uninstall');assert bp.sha(game/'winmm.dll')==baseline_hash
        cases.append('v1_3_upgrade_preserves_font_and_disabled_camera')
        run(game,'speed',speed=200)
        assert config(camera_ini)['Movement']['SpeedPercent']=='200'
        run(game,'speed',speed=201,ok=False)
        assert config(camera_ini)['Movement']['SpeedPercent']=='200'
        run(game,'speed',speed=137)
        assert config(camera_ini)['Movement']['SpeedPercent']=='137'
        run(game,'uninstall');cases.append('movement_speed_range_and_persistence')
        for source_file in (FILES/'字体文件').iterdir():
            target=game/'字体文件'/source_file.name
            target.parent.mkdir(exist_ok=True)
            shutil.copy2(source_file,target)
        for name in ['字体增强.ps1','font-manifest.json']:
            shutil.copy2(FILES/name,game/name)
        test_exe=game/'设置组件校验.exe'
        subprocess.run(compiler+['/define:SETTINGS_TEST','/out:'+str(test_exe),str(source)],check=True)
        subprocess.run([str(test_exe),'--verify-save'],check=True,timeout=30)
        assert bp.sha(game/'winmm.dll')==bp.sha(dll)
        run(game,'uninstall');cases.append('winforms_backend_saves_all_fields_unicode_path')

        (game/'winmm.dll').write_bytes(b'unknown');run(game,ok=False);assert (game/'winmm.dll').read_bytes()==b'unknown';cases.append('unknown_plugin_no_write')
        shutil.copy2(baseline,game/'winmm.dll');(game/'Avadon.exe').write_bytes(b'wrong');run(game,ok=False);assert bp.sha(game/'winmm.dll')==baseline_hash;cases.append('wrong_game_no_write')
    inventory={p.relative_to(FILES).as_posix():bp.sha(p) for p in sorted(FILES.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.txt'}
    (FILES/'SHA256SUMS.txt').write_text(''.join(f'{digest}  {name}\n' for name,digest in inventory.items()),encoding='utf-8-sig')
    archive=ROOT/'阿瓦登_增强补丁_1.8.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(FILES.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(FILES).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,digest in inventory.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
    bp.write_json(ROOT/'VALIDATION.json',{'status':'passed','supported_exe_sha256':bp.SUPPORTED,'dll_sha256':bp.sha(dll),'component_exe_sha256':bp.sha(ROOT/'Build/self_test.exe'),'native_sources':build['native_sources'],
        'interaction_report':read(TESTS/'interaction_report.json'),'movement_report':read(TESTS/'movement_report.json'),'inventory_report':read(TESTS/'inventory_report.json'),'camera_report':read(TESTS/'camera_report.json'),'font_report':read(TESTS/'font_scale_report.json'),'installer_cases':cases,'files':inventory,'archive':str(archive),'archive_sha256':bp.sha(archive),'game_started':False,'in_game_verified':False,'installed':False})
    print(json.dumps({'status':'passed','archive':str(archive),'installer_cases':len(cases)},ensure_ascii=False))

if __name__=='__main__':main()
