"""Exercise the real Windows Chrome extension and background tab transport.

Uses an isolated Chrome for Testing profile. XHS DNS is disabled; no account
is logged in and no live note is requested. Parser counts have separate tests.
"""
import concurrent.futures
import json
from pathlib import Path
import socket
import sys
import threading
import time

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.common.selenium_manager import SeleniumManager

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from xhs_windows import EXTENSION_ID, PORT, WindowsChrome


def main():
    paths = SeleniumManager().binary_paths([
        '--browser', 'chrome', '--browser-version', 'stable',
        '--skip-browser-in-path', '--force-browser-download', '--avoid-stats',
    ])
    options = Options()
    options.binary_location = paths['browser_path']
    options.add_argument('--load-extension=' + str(ROOT / 'chrome_extension'))
    options.add_argument('--disable-background-networking')
    options.add_argument('--no-first-run')
    options.add_argument('--host-resolver-rules=MAP www.xiaohongshu.com ~NOTFOUND')
    stop = threading.Event()
    capture = None
    with webdriver.Chrome(service=Service(paths['driver_path']), options=options) as driver:
        driver.get(f'chrome-extension://{EXTENSION_ID}/popup.html')
        assert driver.find_element(By.ID, 'connect').is_displayed(), 'Extension failed to load'

        def active_tab():
            return driver.execute_async_script('''const done = arguments[0];
                chrome.tabs.query({active:true,currentWindow:true}).then(tabs => done(tabs[0].id));''')

        before = active_tab()
        try:
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(WindowsChrome,
                    'https://www.xiaohongshu.com/explore/1234567890abcdef12345678', stop)
                try:
                    deadline = time.monotonic() + 10
                    while True:
                        try:
                            with socket.create_connection(('127.0.0.1', PORT), timeout=0.2):
                                break
                        except OSError:
                            if future.done():
                                future.result()
                            if time.monotonic() >= deadline:
                                raise TimeoutError('Task bridge did not start')
                            time.sleep(0.05)
                    driver.find_element(By.ID, 'connect').click()
                    capture = future.result(timeout=35)
                finally:
                    if capture is None:
                        stop.set()
            captured_id = capture.tab_id
            assert captured_id != before
            assert active_tab() == before, 'Creating capture tab stole the active tab'
            snapshot = capture._snapshot('1234567890abcdef12345678')
            assert isinstance(snapshot, dict)
            assert active_tab() == before, 'Snapshot stole the active tab'
            capture._navigate('https://www.xiaohongshu.com/explore/abcdef1234567890abcdef12')
            assert active_tab() == before, 'Navigating capture tab stole the active tab'
            capture.close()
            capture = None
            assert active_tab() == before, 'Closing capture tab changed the active tab'
            remaining = driver.execute_async_script('''const done=arguments[0];
                chrome.tabs.query({currentWindow:true}).then(tabs=>done(tabs.map(t=>t.id)));''')
            assert captured_id not in remaining
            report = dict(ok=True, browser=driver.capabilities['browserVersion'],
                          separate_capture_tab=True, active_tab_preserved=True,
                          capture_tab_closed=True, snapshot_transport=True,
                          live_xiaohongshu=False)
            print(json.dumps(report), flush=True)
            evidence = ROOT / 'qa' / 'windows-bundle'
            evidence.mkdir(parents=True, exist_ok=True)
            (evidence / 'chrome-extension.json').write_text(json.dumps(report, indent=2), encoding='utf-8')
        finally:
            if capture is not None:
                capture.close()


if __name__ == '__main__':
    main()
