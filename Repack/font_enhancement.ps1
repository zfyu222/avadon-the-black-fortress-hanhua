param(
    [ValidateSet('install','uninstall')][string]$Action = 'install',
    [string]$GameRoot = $PSScriptRoot
)
$ErrorActionPreference = 'Stop'
Import-Module "$PSHOME/Modules/Microsoft.PowerShell.Utility/Microsoft.PowerShell.Utility.psd1" -ErrorAction Stop
Import-Module "$PSHOME/Modules/Microsoft.PowerShell.Management/Microsoft.PowerShell.Management.psd1" -ErrorAction Stop
function Hash([string]$Path) { (Get-FileHash -LiteralPath $Path -Algorithm SHA256).Hash.ToLowerInvariant() }
$root = (Resolve-Path -LiteralPath $GameRoot).Path
$package = Join-Path $PSScriptRoot 'font-manifest.json'
$manifest = Get-Content -LiteralPath $package -Raw -Encoding UTF8 | ConvertFrom-Json
$gameExe = Join-Path $root 'Avadon.exe'
if (@(Get-Process -Name 'Avadon*' -ErrorAction SilentlyContinue | Where-Object { !$_.Path -or $_.Path -eq $gameExe }).Count) { throw '请先退出游戏。' }
if ((Hash (Join-Path $root 'Avadon.exe')) -ne $manifest.exe_sha256) { throw '游戏版本不匹配。' }
$dll = Join-Path $root 'winmm.dll'
$ini = Join-Path $root 'AvadonChinese/font.ini'
$backup = Join-Path $root '.zfy-font-enhancement'
$statePath = Join-Path $backup 'state.json'
if ($Action -eq 'uninstall') {
    if (!(Test-Path -LiteralPath $statePath)) { throw '没有已安装的字体增强补丁。' }
    $state = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($state.status -eq 'uninstalled') { Write-Output '字体增强已还原。'; exit 0 }
    if ((Hash $dll) -ne $state.dll_installed) { throw '显示插件已被其他补丁修改，未执行还原。' }
    if ((Hash (Join-Path $backup 'winmm.dll')) -ne $state.dll_original) { throw '原件校验失败。' }
    if ($state.ini_existed -and (Hash (Join-Path $backup 'font.ini')) -ne $state.ini_original) { throw '字号设置原件校验失败。' }
    Copy-Item -LiteralPath (Join-Path $backup 'winmm.dll') -Destination $dll -Force
    if ($state.ini_existed) { Copy-Item -LiteralPath (Join-Path $backup 'font.ini') -Destination $ini -Force }
    elseif (Test-Path -LiteralPath $ini) { Remove-Item -LiteralPath $ini -Force }
    $state.status = 'uninstalled'
    $state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
    Write-Output '已还原安装前的字体插件，汉化内容保留。'; exit 0
}
foreach ($name in @('winmm.dll','font.ini')) {
    $expected = $manifest.files.$name
    if ((Hash (Join-Path $PSScriptRoot "字体文件/$name")) -ne $expected) { throw "补丁文件校验失败：$name" }
}
if ((Hash (Join-Path $root 'AvadonChinese/translations.bin')) -ne $manifest.dictionary_sha256) { throw '请先安装本游戏的对应汉化补丁。' }
if (Test-Path -LiteralPath $statePath) {
    $previous = Get-Content -LiteralPath $statePath -Raw -Encoding UTF8 | ConvertFrom-Json
    if ($previous.status -eq 'installed') {
        if ((Hash $dll) -ne $previous.dll_installed -or $previous.dll_installed -ne $manifest.files.'winmm.dll') { throw '已安装的显示插件版本不同，请先还原字体增强。' }
        if (!(Test-Path -LiteralPath $ini)) { Copy-Item -LiteralPath (Join-Path $PSScriptRoot '字体文件/font.ini') -Destination $ini }
        Write-Output '字体增强已安装，保留当前字号设置。'; exit 0
    }
    if ($previous.status -notin @('uninstalled','rolled_back')) { throw '上次安装未完成，已保留原件，请先还原字体增强。' }
}
$old = Hash $dll
if ($old -notin $manifest.supported_dll_sha256) { throw '未识别的显示插件，未覆盖。' }
New-Item -ItemType Directory -Path $backup -Force | Out-Null
$state = [ordered]@{ status='backed_up'; dll_original=$old; dll_installed=$manifest.files.'winmm.dll'; ini_existed=(Test-Path -LiteralPath $ini); ini_original=$null }
Copy-Item -LiteralPath $dll -Destination (Join-Path $backup 'winmm.dll') -Force
if ((Hash (Join-Path $backup 'winmm.dll')) -ne $old) { throw '备份校验失败。' }
if ($state.ini_existed) {
    $state.ini_original=Hash $ini
    Copy-Item -LiteralPath $ini -Destination (Join-Path $backup 'font.ini') -Force
    if ((Hash (Join-Path $backup 'font.ini')) -ne $state.ini_original) { throw '设置备份校验失败。' }
}
$state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
try {
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot '字体文件/winmm.dll') -Destination $dll -Force
    Copy-Item -LiteralPath (Join-Path $PSScriptRoot '字体文件/font.ini') -Destination $ini -Force
    if ((Hash $dll) -ne $manifest.files.'winmm.dll' -or (Hash $ini) -ne $manifest.files.'font.ini') { throw '安装后校验失败。' }
} catch {
    Copy-Item -LiteralPath (Join-Path $backup 'winmm.dll') -Destination $dll -Force
    if ($state.ini_existed) { Copy-Item -LiteralPath (Join-Path $backup 'font.ini') -Destination $ini -Force }
    elseif (Test-Path -LiteralPath $ini) { Remove-Item -LiteralPath $ini -Force }
    $state.status='rolled_back';$state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
    throw
}
$state.status='installed';$state | ConvertTo-Json | Set-Content -LiteralPath $statePath -Encoding UTF8
Write-Output '字体增强已安装：150%。启动原游戏即可。'
