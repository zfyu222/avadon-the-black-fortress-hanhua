"""Package the separately built font add-on; does not publish or launch Avadon."""
import json
import shutil
import subprocess
import tempfile
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw
import build_patch as bp

ROOT=bp.HERE/'FontEnhancement'
FILES=ROOT/'Files'
TESTS=ROOT/'Tests'

def run(action, root, ok=True, scale=None):
    command=['powershell.exe','-NoProfile','-NonInteractive','-ExecutionPolicy','Bypass','-File',str(FILES/'字体增强.ps1'),'-Action',action,'-GameRoot',str(root)]
    if scale is not None:command+=['-Scale',str(scale)]
    result=subprocess.run(command,capture_output=True)
    if (result.returncode==0)!=ok:
        raise RuntimeError(result.stdout.decode('utf-8',errors='replace')+result.stderr.decode('utf-8',errors='replace'))

def main():
    report=json.loads((TESTS/'font_scale_report.json').read_text())
    assert report['status']=='passed'
    assert json.loads((TESTS/'report.json').read_text())['status']=='passed'
    manifest=json.loads((ROOT/'BUILD_MANIFEST.json').read_text(encoding='utf-8'))
    for name,digest in manifest['native_sources'].items():
        assert bp.sha(bp.HERE/'native'/name)==digest
    dll=ROOT/'Payload/winmm.dll'
    assert bp.sha(dll)==manifest['dll_sha256']
    (FILES/'字体文件').mkdir(parents=True,exist_ok=True)
    shutil.copy2(dll,FILES/'字体文件/winmm.dll')
    (FILES/'字体文件/font.ini').write_text('[Font]\r\nScalePercent=150\r\nFitLabels=1\r\n',encoding='ascii')
    (FILES/'字体增强.ps1').write_text((bp.HERE/'font_enhancement.ps1').read_text(encoding='utf-8'),encoding='utf-8-sig')
    for title,action in [('安装字体增强','install'),('还原字体增强','uninstall')]:
        (FILES/(title+'.cmd')).write_bytes(('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0字体增强.ps1" -Action '+action+' -GameRoot "%~dp0."\r\nif errorlevel 1 (pause & exit /b 1)\r\npause\r\n').encode('gbk'))
    for scale in [125,150]:
        (FILES/f'字体{scale}.cmd').write_bytes(('@echo off\r\npowershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0字体增强.ps1" -Action scale -Scale '+str(scale)+' -GameRoot "%~dp0."\r\nif errorlevel 1 (pause & exit /b 1)\r\npause\r\n').encode('gbk'))
    (FILES/'选择字号.cmd').write_bytes(('@echo off\r\necho 1. 125%%\r\necho 2. 150%%\r\nchoice /c 12 /n /m "请选择字号 [1/2]: "\r\nif errorlevel 2 (call "%~dp0字体150.cmd" & exit /b)\r\nif errorlevel 1 (call "%~dp0字体125.cmd" & exit /b)\r\n').encode('gbk'))
    installed_backup=bp.PROJECT/'Game/.zfy-font-enhancement/winmm.dll'
    baseline_dll=installed_backup if installed_backup.exists() else bp.PROJECT/'Game/winmm.dll'
    old=bp.sha(baseline_dll)
    package={'version':'font-1.1','exe_sha256':bp.SUPPORTED,'dictionary_sha256':manifest['dictionary']['dictionary_sha256'],
             'supported_dll_sha256':sorted({old,bp.sha(bp.PAYLOAD/'winmm.dll')}),
             'files':{name:bp.sha(FILES/'字体文件'/name) for name in ['winmm.dll','font.ini']}}
    bp.write_json(FILES/'font-manifest.json',package)
    (FILES/'字体增强说明.txt').write_text('阿瓦登：黑色要塞 字体增强补丁 v1.1\n\n安装及选择：解压到 Avadon.exe 所在文件夹，退出游戏，双击“选择字号.cmd”，按1选择125%，按2选择150%。首次选择会自动安装。\n切换：退出游戏后双击“字体125.cmd”或“字体150.cmd”，重新启动游戏生效。\n也可双击“安装字体增强.cmd”：首次安装默认150%，重复安装保留当前选择。\n还原：双击“还原字体增强.cmd”，恢复增强前的字体插件，保留汉化。\n\n高级设置 AvadonChinese\\font.ini：\nScalePercent=150（范围100至200，100为原汉化字号）\nFitLabels=1（按钮空间不足时缩小，0为关闭）\n切换字号会保留其他设置。\n\n适用于 Steam Build 4252712 / Avadon v1.0s2，需先安装子非鱼汉化。\n放大中文显示插件绘制的文本，图片文字和原生英文回退保持原尺寸。\n正文会重新换行；固定布局的长文仍可能超出原显示区域。\n',encoding='utf-8-sig')
    with tempfile.TemporaryDirectory(prefix='avadon-font-中文 空格-') as temp:
        game=Path(temp)/'游戏 空格';(game/'AvadonChinese').mkdir(parents=True)
        for name in ['Avadon.exe','winmm.dll','AvadonChinese/translations.bin']:
            shutil.copy2(baseline_dll if name=='winmm.dll' else bp.PROJECT/'Game'/name,game/name)
        original=bp.sha(game/'winmm.dll')
        run('install',game);assert bp.sha(game/'winmm.dll')==package['files']['winmm.dll']
        ini=game/'AvadonChinese/font.ini'
        custom_options='[Font]\r\nScalePercent=150\r\nFitLabels=0\r\nExtra=keep\r\n[Other]\r\nScalePercent=177\r\n'
        ini.write_text(custom_options,encoding='ascii')
        for scale in [125,150,125]:
            run('scale',game,scale=scale)
            from configparser import ConfigParser
            config=ConfigParser();config.read(ini,encoding='utf-8-sig')
            assert config['Font']['ScalePercent']==str(scale) and config['Font']['FitLabels']=='0' and config['Font']['Extra']=='keep' and config['Other']['ScalePercent']=='177'
            assert bp.sha(game/'winmm.dll')==package['files']['winmm.dll']
        prior=ini.read_bytes();run('scale',game,False,110);assert ini.read_bytes()==prior
        custom=b'[Font]\r\nScalePercent=125\r\nFitLabels=1\r\n';(game/'AvadonChinese/font.ini').write_bytes(custom)
        run('install',game);assert (game/'AvadonChinese/font.ini').read_bytes()==custom
        run('uninstall',game);assert bp.sha(game/'winmm.dll')==original and not (game/'AvadonChinese/font.ini').exists()
        run('uninstall',game)
        run('scale',game,scale=125)
        assert 'ScalePercent=125' in ini.read_text(encoding='utf-8-sig')
        run('uninstall',game);assert bp.sha(game/'winmm.dll')==original and not ini.exists()
        (game/'AvadonChinese/font.ini').write_bytes(custom)
        run('install',game);run('uninstall',game);assert (game/'AvadonChinese/font.ini').read_bytes()==custom
        (game/'winmm.dll').write_bytes(b'unknown plugin');run('install',game,False);assert (game/'winmm.dll').read_bytes()==b'unknown plugin'
        shutil.copy2(baseline_dll,game/'winmm.dll')
        (game/'Avadon.exe').write_bytes(b'wrong build');run('install',game,False);assert bp.sha(game/'winmm.dll')==original
    previews=[]
    for scale in [100,150]:
        im=Image.open(TESTS/f'font_{scale}.ppm');im.save(TESTS/f'font_{scale}.png');previews.append(im)
    combined=Image.new('RGB',(640,185),(12,16,20));draw=ImageDraw.Draw(combined)
    for i,im in enumerate(previews):
        draw.text((i*320+10,4),f'{[100,150][i]}%',fill='white');combined.paste(im,(i*320,25))
    combined.save(ROOT/'font_comparison.png')
    inventory={p.relative_to(FILES).as_posix():bp.sha(p) for p in FILES.rglob('*') if p.is_file() and p.name!='SHA256SUMS.txt'}
    (FILES/'SHA256SUMS.txt').write_text(''.join(f'{digest}  {name}\n' for name,digest in sorted(inventory.items())),encoding='utf-8-sig')
    archive=ROOT/'阿瓦登_字体增强可选字号_1.1.zip'
    with zipfile.ZipFile(archive,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as out:
        for p in sorted(FILES.rglob('*')):
            if p.is_file():out.write(p,p.relative_to(FILES).as_posix())
    with zipfile.ZipFile(archive) as check:
        assert check.testzip() is None
        for name,digest in inventory.items():
            import hashlib
            assert hashlib.sha256(check.read(name)).hexdigest()==digest
    bp.write_json(ROOT/'VALIDATION.json',{'status':'passed','font_component':report,'installer_replay':['install','idempotent_preserves_custom_scale','uninstall','idempotent_uninstall','prior_config_restored','unknown_plugin_rejected','wrong_exe_rejected','unicode_space_path','switch_150_125_150_125','switch_preserves_other_options_and_sections','invalid_scale_rejected','first_switch_auto_installs_125'],
        'dll_sha256':bp.sha(dll),'archive':str(archive),'archive_sha256':bp.sha(archive),'files':inventory,'game_started':False,'in_game_verified':False})
    print(archive)

if __name__=='__main__':main()
