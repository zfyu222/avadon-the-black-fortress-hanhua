param(
    [ValidateSet('install','uninstall','scale','camera','speed','settings')][string]$Action='install',
    [ValidateRange(0,200)][int]$Scale=0,
    [ValidateSet(-1,0,1)][int]$Follow=-1,
    [ValidateRange(100,200)][int]$Speed,
    [ValidateSet(-1,0,1)][int]$Inventory=-1,
    [ValidateSet(-1,0,1)][int]$FitLabels=-1,
    [string]$GameRoot=$PSScriptRoot
)
$ErrorActionPreference='Stop'
if($env:AVADON_SETTINGS_UTF8 -eq '1') {
    [Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false)
}
trap {
    if($env:AVADON_SETTINGS_UTF8 -eq '1') {
        [Console]::Error.WriteLine($_.Exception.Message)
        exit 1
    }
    break
}
Import-Module "$PSHOME/Modules/Microsoft.PowerShell.Utility/Microsoft.PowerShell.Utility.psd1" -ErrorAction Stop
Import-Module "$PSHOME/Modules/Microsoft.PowerShell.Management/Microsoft.PowerShell.Management.psd1" -ErrorAction Stop
function Hash([string]$p) { if(Test-Path -LiteralPath $p -PathType Leaf) { (Get-FileHash -LiteralPath $p -Algorithm SHA256).Hash.ToLowerInvariant() } else { $null } }
function Save($value) { $value|ConvertTo-Json -Depth 8|Set-Content -LiteralPath $statePath -Encoding UTF8 }
function Put($source,$target) { Copy-Item -LiteralPath $source -Destination $target -Force; if((Hash $source) -ne (Hash $target)) { throw '文件写入校验失败。' } }
function SetIni($path,$section,$key,$value) {
    if(!('AvadonEnhancementIni' -as [type])) {
        Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class AvadonEnhancementIni {
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode, SetLastError=true)]
    public static extern bool WritePrivateProfileString(string section, string key, string value, string path);
}
'@
    }
    if(![AvadonEnhancementIni]::WritePrivateProfileString($section,$key,[string]$value,$path)) { throw '设置保存失败。' }
}
if($PSBoundParameters.ContainsKey('Scale') -and $Scale -lt 100) { throw '字号范围为100%到200%。' }
if($Action -eq 'scale' -and $Scale -eq 0) { throw '请填写字号。' }
if($Action -eq 'camera' -and $Follow -eq -1) { throw '请选择开启或关闭镜头跟随。' }
$root=(Resolve-Path -LiteralPath $GameRoot).Path
$exe=Join-Path $root 'Avadon.exe'
if(@(Get-Process -Name 'Avadon*' -ErrorAction SilentlyContinue|Where-Object { !$_.Path -or $_.Path -eq $exe }).Count) { throw '请先退出游戏，再安装或切换增强功能。' }
if($Action -eq 'speed' -and !$PSBoundParameters.ContainsKey('Speed')) {
    $enteredSpeed=Read-Host '输入主角移动速度百分比（100 到 200，100 为原速）'
    if($enteredSpeed -notmatch '^(1[0-9]{2}|200)$') { throw '请输入100到200之间的整数。' }
    $Speed=[int]$enteredSpeed
}
$manifest=Get-Content -LiteralPath (Join-Path $PSScriptRoot 'font-manifest.json') -Raw -Encoding UTF8|ConvertFrom-Json
if((Hash $exe) -ne $manifest.exe_sha256) { throw '游戏版本不匹配。' }
$dll=Join-Path $root 'winmm.dll'
$font=Join-Path $root 'AvadonChinese/font.ini'
$camera=Join-Path $root 'AvadonChinese/camera.ini'
$backup=Join-Path $root '.zfy-font-enhancement'
$statePath=Join-Path $backup 'state.json'
$state=$null
if(Test-Path -LiteralPath $statePath) { $state=Get-Content -LiteralPath $statePath -Raw -Encoding UTF8|ConvertFrom-Json }
if($Action -eq 'uninstall') {
    if(!$state) { throw '没有已安装的增强补丁。' }
    if($state.status -eq 'uninstalled') { Write-Output '增强补丁已还原。'; exit 0 }
    if((Hash $dll) -ne $state.dll_installed) { throw '显示插件已被修改，未覆盖。' }
    if((Hash (Join-Path $backup 'winmm.dll')) -ne $state.dll_original) { throw '插件原件校验失败。' }
    if($state.ini_existed -and (Hash (Join-Path $backup 'font.ini')) -ne $state.ini_original) { throw '字体设置原件校验失败。' }
    if($state.camera_existed -and (Hash (Join-Path $backup 'camera.ini')) -ne $state.camera_original) { throw '镜头设置原件校验失败。' }
    Put (Join-Path $backup 'winmm.dll') $dll
    if($state.ini_existed) { Put (Join-Path $backup 'font.ini') $font }
    elseif(Test-Path -LiteralPath $font) { Remove-Item -LiteralPath $font -Force }
    if($state.camera_managed) {
        if($state.camera_existed) { Put (Join-Path $backup 'camera.ini') $camera }
        elseif(Test-Path -LiteralPath $camera) { Remove-Item -LiteralPath $camera -Force }
    }
    $state.status='uninstalled';Save $state
    Write-Output '已恢复增强前的插件与设置，汉化保留。';exit 0
}
foreach($item in $manifest.files.PSObject.Properties) {
    if((Hash (Join-Path $PSScriptRoot ('字体文件/'+$item.Name))) -ne $item.Value) { throw '补丁文件校验失败。' }
}
if((Hash (Join-Path $root 'AvadonChinese/translations.bin')) -ne $manifest.dictionary_sha256) { throw '请先安装本游戏对应的子非鱼汉化。' }
$current=Hash $dll
$wasInstalled=$state -and $state.status -eq 'installed'
if($wasInstalled) {
    if($current -ne $state.dll_installed -or ($current -notin $manifest.supported_dll_sha256 -and $current -ne $manifest.files.'winmm.dll')) { throw '已安装插件不匹配，未覆盖。' }
    if((Hash (Join-Path $backup 'winmm.dll')) -ne $state.dll_original) { throw '插件原件校验失败。' }
} else {
    if($state -and $state.status -notin @('uninstalled','rolled_back')) { throw '上次安装未完成，已保留原件。' }
    if($current -notin $manifest.supported_dll_sha256) { throw '未识别的显示插件，未覆盖。' }
    New-Item -ItemType Directory -Path $backup -Force|Out-Null
    Put $dll (Join-Path $backup 'winmm.dll')
    $state=[pscustomobject]@{status='backed_up';dll_original=$current;dll_installed=$manifest.files.'winmm.dll';ini_existed=(Test-Path -LiteralPath $font);ini_original=(Hash $font)}
    if($state.ini_existed) { Put $font (Join-Path $backup 'font.ini') }
}
# Preserve the original backups from the previous font-only installer.
if(!$state.camera_managed) {
    $state|Add-Member -NotePropertyName camera_existed -NotePropertyValue (Test-Path -LiteralPath $camera) -Force
    $state|Add-Member -NotePropertyName camera_original -NotePropertyValue (Hash $camera) -Force
    if($state.camera_existed) { Put $camera (Join-Path $backup 'camera.ini') }
    $state|Add-Member -NotePropertyName camera_managed -NotePropertyValue $true -Force
}
$oldState=if($wasInstalled) { Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 } else { $null }
$rollback=Join-Path $backup 'upgrade-rollback'
New-Item -ItemType Directory -Path $rollback -Force|Out-Null
$snapshots=@()
foreach($pair in @(@('winmm.dll',$dll),@('font.ini',$font),@('camera.ini',$camera))) {
    $exists=Test-Path -LiteralPath $pair[1]
    if($exists) { Put $pair[1] (Join-Path $rollback $pair[0]) }
    $snapshots+=@{path=$pair[1];name=$pair[0];exists=$exists}
}
if(!$wasInstalled) { Save $state }
try {
    if($current -ne $manifest.files.'winmm.dll') { Put (Join-Path $PSScriptRoot '字体文件/winmm.dll') $dll }
    if(!(Test-Path -LiteralPath $font)) { Put (Join-Path $PSScriptRoot '字体文件/font.ini') $font }
    if(!(Test-Path -LiteralPath $camera)) { Put (Join-Path $PSScriptRoot '字体文件/camera.ini') $camera }
    if($Scale -ne 0) { SetIni $font 'Font' 'ScalePercent' $Scale }
    if($Follow -ne -1) { SetIni $camera 'Camera' 'FollowCharacter' $Follow }
    if($Speed -ge 100) { SetIni $camera 'Movement' 'SpeedPercent' $Speed }
    if($Inventory -ne -1) { SetIni $camera 'Inventory' 'ToggleHotkey' $Inventory }
    if($FitLabels -ne -1) { SetIni $font 'Font' 'FitLabels' $FitLabels }
    $state.dll_installed=$manifest.files.'winmm.dll';$state.status='installed';Save $state
} catch {
    foreach($record in $snapshots) {
        if($record.exists) { Put (Join-Path $rollback $record.name) $record.path }
        elseif(Test-Path -LiteralPath $record.path) { Remove-Item -LiteralPath $record.path -Force }
    }
    if($oldState) { Set-Content -LiteralPath $statePath -Value $oldState -Encoding UTF8 }
    else { $state.status='rolled_back';Save $state }
    throw
}
Write-Output '增强功能设置已保存，重新启动游戏生效。'
