"""Check the actual frozen EXE on a Windows desktop; Pillow is CI-only."""
import ctypes
from ctypes import wintypes
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

from PIL import Image


def capture_window(title, destination):
    user = ctypes.WinDLL('user32', use_last_error=True)
    gdi = ctypes.WinDLL('gdi32', use_last_error=True)
    user.FindWindowW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR]
    user.FindWindowW.restype = wintypes.HWND
    user.GetWindowDC.argtypes = [wintypes.HWND]
    user.GetWindowDC.restype = wintypes.HDC
    user.GetWindowRect.argtypes = [wintypes.HWND, ctypes.POINTER(wintypes.RECT)]
    user.PrintWindow.argtypes = [wintypes.HWND, wintypes.HDC, wintypes.UINT]
    user.ReleaseDC.argtypes = [wintypes.HWND, wintypes.HDC]
    gdi.CreateCompatibleDC.argtypes = [wintypes.HDC]
    gdi.CreateCompatibleDC.restype = wintypes.HDC
    gdi.CreateCompatibleBitmap.argtypes = [wintypes.HDC, ctypes.c_int, ctypes.c_int]
    gdi.CreateCompatibleBitmap.restype = wintypes.HBITMAP
    gdi.SelectObject.argtypes = [wintypes.HDC, wintypes.HGDIOBJ]
    gdi.SelectObject.restype = wintypes.HGDIOBJ
    gdi.GetDIBits.argtypes = [wintypes.HDC, wintypes.HBITMAP, wintypes.UINT,
                            wintypes.UINT, ctypes.c_void_p, ctypes.c_void_p, wintypes.UINT]
    gdi.DeleteObject.argtypes = [wintypes.HGDIOBJ]
    gdi.DeleteDC.argtypes = [wintypes.HDC]
    window = user.FindWindowW(None, title)
    assert window, 'Packaged application window not found'
    rect = wintypes.RECT()
    assert user.GetWindowRect(window, ctypes.byref(rect))
    width, height = rect.right - rect.left, rect.bottom - rect.top
    dc = user.GetWindowDC(window)
    memory = gdi.CreateCompatibleDC(dc)
    bitmap = gdi.CreateCompatibleBitmap(dc, width, height)
    old = gdi.SelectObject(memory, bitmap)
    try:
        assert user.PrintWindow(window, memory, 2), 'PrintWindow failed'
        gdi.SelectObject(memory, old)
        import struct
        header = ctypes.create_string_buffer(struct.pack('<IiiHHIIiiII', 40, width, -height, 1, 32, 0, 0, 0, 0, 0, 0))
        pixels = ctypes.create_string_buffer(width * height * 4)
        assert gdi.GetDIBits(memory, bitmap, 0, height, pixels, header, 0) == height
        image = Image.frombytes('RGB', (width, height), pixels.raw, 'raw', 'BGRX')
        assert max(high - low for low, high in image.getextrema()) > 40, 'Empty window capture'
        image.save(destination)
    finally:
        gdi.SelectObject(memory, old)
        gdi.DeleteObject(bitmap)
        gdi.DeleteDC(memory)
        user.ReleaseDC(window, dc)


def main():
    exe, evidence = [Path(value).resolve() for value in sys.argv[1:]]
    evidence.mkdir(parents=True, exist_ok=True)
    assert not (evidence / 'report.json').exists(), 'Use a fresh evidence directory'
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(('PYTHON', 'SE_')) and key != 'VIRTUAL_ENV'}
    driver = shutil.which('chromedriver')
    driver_dir = str(Path(driver).parent).lower() if driver else None
    environment['PATH'] = os.pathsep.join(part for part in environment['PATH'].split(os.pathsep)
                                        if 'python' not in part.lower() and part.lower() != driver_dir)
    process = subprocess.Popen([str(exe), '--smoke-test', str(evidence)], env=environment)
    try:
        deadline = time.monotonic() + 270
        report_file = evidence / 'report.json'
        while not report_file.exists() and time.monotonic() < deadline:
            assert process.poll() is None, f'EXE exited early: {process.returncode}'
            time.sleep(1)
        assert report_file.exists(), 'Packaged app timed out before reporting'
        report = json.loads(report_file.read_text(encoding='utf-8'))
        print(json.dumps(report, ensure_ascii=False, indent=2), flush=True)
        assert report['ok'] and report['frozen'] and report['system'] == 'Windows', report
        capture_window('链接热度抓取 · 新版预览', evidence / 'windows-app.png')
        (evidence / 'capture.done').touch()
        assert process.wait(timeout=30) == 0
    finally:
        if process.poll() is None:
            subprocess.run(['taskkill', '/PID', str(process.pid), '/T', '/F'], check=False)


if __name__ == '__main__':
    main()
