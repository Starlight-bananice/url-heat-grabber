"""GitHub Release updates; installation runs outside the exiting application."""
from __future__ import annotations

import hashlib
import base64
import os
import platform
import plistlib
import re
import shutil
import stat
import subprocess
import sys
import tempfile
import time
import zipfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

import requests

REPOSITORY = 'Starlight-bananice/url-heat-grabber'
RELEASE_PAGE = f'https://github.com/{REPOSITORY}/releases/latest'
API_URL = f'https://api.github.com/repos/{REPOSITORY}/releases/latest'
MAX_DOWNLOAD = 500 * 1024 * 1024


def version_tuple(value):
    match = re.fullmatch(r'v?(\d+)\.(\d+)\.(\d+)', value or '')
    if not match:
        raise ValueError('版本号需采用 v1.2.3 格式')
    return tuple(int(part) for part in match.groups())


@dataclass(frozen=True)
class Release:
    version: str
    filename: str
    url: str
    checksum_url: str


def release_from_payload(payload, current, system=None, machine=None):
    if payload.get('draft') or payload.get('prerelease'):
        return None
    tag = payload.get('tag_name', '')
    if version_tuple(tag) <= version_tuple(current):
        return None
    system = system or platform.system()
    machine = (machine or platform.machine()).lower()
    if system == 'Darwin' and machine in ('arm64', 'aarch64'):
        suffix = 'macOS-arm64'
    elif system == 'Windows' and machine in ('amd64', 'x86_64'):
        suffix = 'windows-x64'
    else:
        raise ValueError('当前系统没有对应的自动更新安装包')
    version = tag.lstrip('v')
    filename = f'URLHeat-{version}-{suffix}.zip'
    assets = {item['name']: item for item in payload.get('assets', [])}
    urls = []
    for name in (filename, filename + '.sha256'):
        if name not in assets:
            raise ValueError('新版安装包尚未上传完整，请稍后检查')
        url = assets[name].get('browser_download_url', '')
        expected = f'https://github.com/{REPOSITORY}/releases/download/{tag}/{name}'
        if url != expected:
            raise ValueError('安装包下载地址不属于本项目')
        urls.append(url)
    return Release(version, filename, *urls)


def check_release(current):
    response = requests.get(API_URL, headers={'Accept': 'application/vnd.github+json'}, timeout=(8, 15))
    response.raise_for_status()
    return release_from_payload(response.json(), current)


def installed_target():
    if not getattr(sys, 'frozen', False):
        raise ValueError('源码运行时不替换程序，请安装正式版后使用自动更新')
    executable = Path(sys.executable).resolve()
    if platform.system() == 'Darwin':
        target = executable.parents[2]
        if target.suffix != '.app':
            raise ValueError('无法定位当前应用，请从“应用程序”文件夹启动')
    elif platform.system() == 'Windows':
        target = executable
    else:
        raise ValueError('当前系统暂不支持自动安装')
    # Test the exact directory where the replacement will be placed.
    try:
        with tempfile.TemporaryFile(dir=target.parent):
            pass
    except OSError as exc:
        raise ValueError('应用所在目录不可写，请将应用移到可写目录或手动下载更新') from exc
    return target


def download_release(release, directory):
    for attempt in range(3):
        try:
            return _download_release_once(release, directory)
        except (requests.ConnectionError, requests.Timeout,
                requests.exceptions.ChunkedEncodingError) as exc:
            if attempt == 2:
                raise ValueError('下载连接中断，已尝试 3 次；当前程序未被替换，请稍后重试或手动下载') from exc
            time.sleep(attempt + 1)


def _download_release_once(release, directory):
    directory = Path(directory)
    checksum = requests.get(release.checksum_url, timeout=(8, 20))
    checksum.raise_for_status()
    match = re.fullmatch(r'([a-fA-F0-9]{64})\s+\*?([^\r\n]+)\s*', checksum.text.strip())
    if not match or match[2] != release.filename:
        raise ValueError('安装包校验文件不正确')
    archive = directory / release.filename
    digest = hashlib.sha256()
    count = 0
    with requests.get(release.url, stream=True, timeout=(8, 30)) as response:
        response.raise_for_status()
        with archive.open('wb') as handle:
            for block in response.iter_content(1024 * 1024):
                if not block:
                    continue
                count += len(block)
                if count > MAX_DOWNLOAD:
                    raise ValueError('安装包大小异常，已停止下载')
                digest.update(block)
                handle.write(block)
    if digest.hexdigest().lower() != match[1].lower():
        raise ValueError('下载文件校验失败，请重新检查更新')
    return archive


def validate_archive(archive):
    with zipfile.ZipFile(archive) as package:
        if sum(item.file_size for item in package.infolist()) > 2 * 1024 ** 3:
            raise ValueError('安装包解压大小异常')
        for item in package.infolist():
            name = item.filename.replace('\\', '/')
            path = PurePosixPath(name)
            if path.is_absolute() or '..' in path.parts or ':' in name:
                raise ValueError('安装包包含非法路径')
            if stat.S_ISLNK(item.external_attr >> 16):
                link = package.read(item).decode('utf-8')
                if link.startswith('/'):
                    raise ValueError('安装包包含非法符号链接')
                resolved = os.path.normpath(str(path.parent / link)).replace('\\', '/')
                if resolved.startswith('../') or resolved == '..':
                    raise ValueError('安装包符号链接越界')


@dataclass(frozen=True)
class PreparedUpdate:
    directory: Path
    source: Path
    target: Path
    version: str


def prepare_update(release):
    target = installed_target()
    directory = Path(tempfile.mkdtemp(prefix='.urlheat-update-', dir=target.parent))
    try:
        archive = download_release(release, directory)
        validate_archive(archive)
        unpacked = directory / 'unpacked'
        unpacked.mkdir()
        if platform.system() == 'Darwin':
            subprocess.run(['/usr/bin/ditto', '-x', '-k', str(archive), str(unpacked)], check=True,
                           capture_output=True, timeout=120)
            source = unpacked / '链接热度抓取.app'
            with (source / 'Contents/Info.plist').open('rb') as handle:
                info = plistlib.load(handle)
            if (info.get('CFBundleIdentifier') != 'com.starlightbananice.urlheat'
                    or info.get('CFBundleShortVersionString') != release.version):
                raise ValueError('安装包应用或版本不匹配')
            subprocess.run(['/usr/bin/codesign', '--verify', '--deep', '--strict', str(source)],
                           check=True, capture_output=True, timeout=90)
        else:
            with zipfile.ZipFile(archive) as package:
                name = '链接热度抓取.exe'
                if name not in package.namelist():
                    raise ValueError('安装包中缺少应用程序')
                package.extract(name, unpacked)
            source = unpacked / name
            if source.read_bytes()[:2] != b'MZ':
                raise ValueError('安装包中的程序格式错误')
        return PreparedUpdate(directory, source, target, release.version)
    except Exception:
        shutil.rmtree(directory, ignore_errors=True)
        raise


def launch_installer(update, parent_pid, data_dir):
    """Wait for this process to exit, replace on the same volume, roll back on error."""
    log = Path(data_dir) / 'update-install.log'
    backup = update.directory / ('previous.app' if platform.system() == 'Darwin' else 'previous.exe')
    if platform.system() == 'Darwin':
        script = update.directory / 'install.sh'
        script.write_text('''#!/bin/sh
set -eu
parent="$1"; source="$2"; target="$3"; backup="$4"; work="$5"
count=0
while kill -0 "$parent" 2>/dev/null; do
  count=$((count + 1)); [ "$count" -lt 120 ] || exit 1
  sleep 1
done
moved=0
rollback() {
  if [ "$moved" = 1 ]; then
    [ ! -e "$target" ] || mv "$target" "$work/failed.app"
    mv "$backup" "$target"
    /usr/bin/open "$target" || true
  fi
}
trap rollback EXIT
mv "$target" "$backup"
moved=1
mv "$source" "$target"
/usr/bin/open "$target"
moved=0
trap - EXIT
rm -rf "$work"
''', encoding='utf-8')
        command = ['/bin/sh', str(script), str(parent_pid), str(update.source), str(update.target),
                   str(backup), str(update.directory)]
        flags = {'start_new_session': True}
    else:
        def quote(path):
            return "'" + str(path).replace("'", "''") + "'"
        script = update.directory / 'install.ps1'
        script.write_text(f'''$ErrorActionPreference = 'Stop'
$target = {quote(update.target)}
$source = {quote(update.source)}
$backup = {quote(backup)}
$work = {quote(update.directory)}
[Console]::WriteLine('Starting update installer')
$old = Get-Process -Id {int(parent_pid)} -ErrorAction SilentlyContinue
if ($old -and !$old.WaitForExit(120000)) {{ throw '等待应用退出超时' }}
$moved = $false
try {{
  for ($attempt = 0; $attempt -lt 30; $attempt++) {{
    try {{ Move-Item -LiteralPath $target -Destination $backup; $moved = $true; break }}
    catch {{ if ($attempt -eq 29) {{ throw }}; Start-Sleep -Seconds 1 }}
  }}
  Move-Item -LiteralPath $source -Destination $target
  Start-Process -FilePath $target -WorkingDirectory (Split-Path -LiteralPath $target)
  [Console]::WriteLine('Replacement complete; restart requested')
  $moved = $false
  # The old one-file bootloader can briefly keep previous.exe locked after Python exits.
  for ($attempt = 0; $attempt -lt 20; $attempt++) {{
    try {{ Remove-Item -LiteralPath $work -Recurse -Force; break }}
    catch {{
      if ($attempt -eq 19) {{ [Console]::Error.WriteLine('Updated; temporary files could not be removed') }}
      else {{ Start-Sleep -Milliseconds 500 }}
    }}
  }}
}} catch {{
  [Console]::Error.WriteLine($_.ToString())
  if ($moved) {{
    if (Test-Path -LiteralPath $target) {{ Move-Item -LiteralPath $target -Destination (Join-Path $work 'failed.exe') }}
    Move-Item -LiteralPath $backup -Destination $target
    Start-Process -FilePath $target
  }}
  exit 1
}}
''', encoding='utf-8-sig')
        encoded = base64.b64encode(script.read_text(encoding='utf-8-sig').encode('utf-16le')).decode('ascii')
        command = ['powershell.exe', '-NoProfile', '-NonInteractive', '-EncodedCommand', encoded]
        # DETACHED_PROCESS makes Windows PowerShell exit without running the script.
        flags = {'creationflags': subprocess.CREATE_NO_WINDOW}
    environment = dict(os.environ, PYINSTALLER_RESET_ENVIRONMENT='1')
    # The helper and restarted EXE must outlive the old one-file extraction.
    with log.open('wb') as output:
        return subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=output, stderr=output,
                                env=environment, **flags)
