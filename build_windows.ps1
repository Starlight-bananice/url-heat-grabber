$ErrorActionPreference = 'Stop'

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ProjectDir

python -m PyInstaller --noconfirm --clean UrlHeat-windows.spec

$ExePath = Join-Path $ProjectDir 'dist\链接热度抓取-新版预览.exe'
$ZipPath = Join-Path $ProjectDir 'dist\链接热度抓取-新版预览-windows-x64.zip'

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "未找到构建结果：$ExePath"
}

if (Test-Path -LiteralPath $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}

Compress-Archive -LiteralPath $ExePath -DestinationPath $ZipPath -Force
Write-Host "已生成：$ExePath"
Write-Host "已生成：$ZipPath"
