"""Local camera/font enhancement package and isolated installer regression."""
from pathlib import Path
import configparser
import hashlib
import json
import shutil
import subprocess
import tempfile
import zipfile
import build_patch as bp

ROOT=bp.HERE/'Enhancement'
FILES=ROOT/'Files'
TESTS=ROOT/'Tests'

def read(path):return json.loads(Path(path).read_text(encoding='utf-8-sig'))
def run(root,action='install',scale=None,follow=None,ok=True,script=None):
    cmd=['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(script or FILES/'字体增强.ps1'),'-GameRoot',str(root),'-Action',action]
    if scale is not None:cmd+=['-Scale',str(scale)]
    if follow is not None:cmd+=['-Follow',str(follow)]
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
    (FILES/'字体文件/camera.ini').write_bytes(b'[Camera]\r\nFollowCharacter=1\r\n')
    (FILES/'字体增强.ps1').write_text((bp.HERE/'enhancement.ps1').read_text(encoding='utf-8'),encoding='utf-8-sig')
    commands={
        '安装增强补丁':'-Action install','还原增强补丁':'-Action uninstall',
        '安装字体增强':'-Action install','还原字体增强':'-Action uninstall',
        '字体125':'-Action scale -Scale 125','字体150':'-Action scale -Scale 150',
        '开启镜头跟随':'-Action camera -Follow 1','关闭镜头跟随':'-Action camera -Follow 0'}
    for title,args in commands.items():
        (FILES/(title+'.cmd')).write_bytes(('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0字体增强.ps1" '+args+' -GameRoot "%~dp0."\r\nif errorlevel 1 (pause & exit /b 1)\r\npause\r\n').encode('gbk'))
    shutil.copy2(bp.HERE/'FontEnhancement/Files/选择字号.cmd',FILES/'选择字号.cmd')
    previous=read(ROOT/'v1.2_VALIDATION.json')
    previous_zip=ROOT/'阿瓦登_字体与镜头增强_1.2.zip'
    assert bp.sha(previous_zip)==previous['archive_sha256']
    manifest={'version':'enhancement-1.3','exe_sha256':bp.SUPPORTED,'dictionary_sha256':build['dictionary']['dictionary_sha256'],
              'supported_dll_sha256':sorted({baseline_hash,font_hash,previous['dll_sha256'],bp.sha(dll)}),'files':{n:bp.sha(FILES/'字体文件'/n) for n in ['winmm.dll','font.ini','camera.ini']}}
    bp.write_json(FILES/'font-manifest.json',manifest)
    (FILES/'增强补丁说明.txt').write_text('阿瓦登：黑色要塞 字体与镜头增强 v1.3\n\n安装：退出游戏，将本包解压到 Avadon.exe 所在文件夹，双击“安装增强补丁.cmd”。\n升级：覆盖解压后运行同一个安装入口，保留当前字号与镜头设置。\n还原：双击“还原增强补丁.cmd”，恢复增强前的插件和设置，保留汉化。\n\n镜头：只跟随1号角色。1号角色行走时自动跟随；停止后可将鼠标移至屏幕边缘浏览；1号角色再次行走自动接回。其他角色移动或切换选中角色不会改变跟随目标。\n双击“开启镜头跟随.cmd”或“关闭镜头跟随.cmd”切换功能，重新启动游戏生效。\n默认开启；菜单和敌方回合保持原游戏镜头行为。\n\n字号：双击“选择字号.cmd”，按1选择125%，按2选择150%；也可使用“字体125.cmd”或“字体150.cmd”。\n退出游戏后切换，重新启动生效。初次安装默认150%，升级保留原设置。\n\n适用版本：Steam Build 4252712 / Avadon v1.0s2，需要先安装子非鱼汉化。\n',encoding='utf-8-sig')
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
        before_dll=bp.sha(game/'winmm.dll');before_ini=font_ini.read_bytes();run(game,'scale',scale=110,ok=False);assert bp.sha(game/'winmm.dll')==before_dll and font_ini.read_bytes()==before_ini;cases.append('invalid_scale_no_write')
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
        (game/'winmm.dll').write_bytes(b'unknown');run(game,ok=False);assert (game/'winmm.dll').read_bytes()==b'unknown';cases.append('unknown_plugin_no_write')
        shutil.copy2(baseline,game/'winmm.dll');(game/'Avadon.exe').write_bytes(b'wrong');run(game,ok=False);assert bp.sha(game/'winmm.dll')==baseline_hash;cases.append('wrong_game_no_write')
    inventory={p.relative_to(FILES).as_posix():bp.sha(p) for p in sorted(FILES.rglob('*')) if p.is_file() and p.name!='SHA256SUMS.txt'}
    (FILES/'SHA256SUMS.txt').write_text(''.join(f'{digest}  {name}\n' for name,digest in inventory.items()),encoding='utf-8-sig')
    archive=ROOT/'阿瓦登_字体与镜头增强_1.3.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(FILES.rglob('*')):
            if p.is_file():z.write(p,p.relative_to(FILES).as_posix())
    with zipfile.ZipFile(archive) as z:
        assert z.testzip() is None
        for name,digest in inventory.items():assert hashlib.sha256(z.read(name)).hexdigest()==digest
    bp.write_json(ROOT/'VALIDATION.json',{'status':'passed','supported_exe_sha256':bp.SUPPORTED,'dll_sha256':bp.sha(dll),'component_exe_sha256':bp.sha(ROOT/'Build/self_test.exe'),'native_sources':build['native_sources'],
        'camera_report':read(TESTS/'camera_report.json'),'font_report':read(TESTS/'font_scale_report.json'),'installer_cases':cases,'files':inventory,'archive':str(archive),'archive_sha256':bp.sha(archive),'game_started':False,'in_game_verified':False,'installed':False})
    print(json.dumps({'status':'passed','archive':str(archive),'installer_cases':len(cases)},ensure_ascii=False))

if __name__=='__main__':main()
