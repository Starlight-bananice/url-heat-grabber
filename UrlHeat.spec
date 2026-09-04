# -*- mode: python ; coding: utf-8 -*-
from pathlib import Path

import selenium
from PyInstaller.utils.hooks import collect_submodules


project_dir = Path(SPECPATH)
selenium_dir = Path(selenium.__file__).resolve().parent
selenium_manager = selenium_dir / 'webdriver' / 'common' / 'macos' / 'selenium-manager'

if not selenium_manager.is_file():
    raise FileNotFoundError(f'Selenium Manager binary not found: {selenium_manager}')


a = Analysis(
    [str(project_dir / 'app.py')],
    pathex=[str(project_dir)],
    binaries=[(str(selenium_manager), 'selenium/webdriver/common/macos')],
    datas=[(str(project_dir / 'assets' / 'sidebar_icon.png'), 'assets')],
    hiddenimports=collect_submodules('selenium'),
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
    [],
    name='URLHeat',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    exclude_binaries=True,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name='URLHeat',
)

app = BUNDLE(
    coll,
    name='链接热度抓取-新版预览.app',
    icon=str(project_dir / 'assets' / 'app_icon.icns'),
    version='0.6.0',
    bundle_identifier='com.starlightbananice.urlheat.preview',
    info_plist={'CFBundleVersion': '3', 'CFBundleDisplayName': '链接热度抓取 · 新版预览', 'NSHighResolutionCapable': True},
)
