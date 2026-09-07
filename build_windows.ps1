$ErrorActionPreference = 'Stop'

$ProjectDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ProjectDir

python -m PyInstaller --noconfirm --clean UrlHeat-windows.spec
if ($LASTEXITCODE -ne 0) {
    throw 'Windows 构建失败。'
}

$ExePath = Join-Path $ProjectDir 'dist\链接热度抓取.exe'
$ZipPath = Join-Path $ProjectDir 'dist\URLHeat-0.6.6-windows-x64.zip'

if (-not (Test-Path -LiteralPath $ExePath)) {
    throw "未找到构建结果：$ExePath"
}

if (Test-Path -LiteralPath $ZipPath) {
    Remove-Item -LiteralPath $ZipPath -Force
}

Compress-Archive -LiteralPath $ExePath -DestinationPath $ZipPath -Force
$Hash = (Get-FileHash -LiteralPath $ZipPath -Algorithm SHA256).Hash.ToLower()
"$Hash  $([System.IO.Path]::GetFileName($ZipPath))" | Set-Content -LiteralPath "$ZipPath.sha256" -Encoding ascii
Write-Host "已生成：$ExePath"
Write-Host "已生成：$ZipPath"
