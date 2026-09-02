# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-file configuration for Windows x64."""

from pathlib import Path

import selenium
from PyInstaller.utils.hooks import collect_submodules


project_dir = Path(SPECPATH)
selenium_dir = Path(selenium.__file__).resolve().parent
selenium_manager = selenium_dir / 'webdriver' / 'common' / 'windows' / 'selenium-manager.exe'

if not selenium_manager.is_file():
    raise FileNotFoundError(f'Selenium Manager binary not found: {selenium_manager}')


a = Analysis(
    [str(project_dir / 'app.py')],
    pathex=[str(project_dir)],
    binaries=[(str(selenium_manager), 'selenium/webdriver/common/windows')],
    datas=[],
    hiddenimports=(
        collect_submodules('selenium')
        + collect_submodules('openpyxl')
    ),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='链接热度抓取',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
)
