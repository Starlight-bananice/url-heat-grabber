import base64
import concurrent.futures
import hashlib
import json
import threading
import time
import unittest
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from xhs_windows import ChromeBridge, EXTENSION_ID, ORIGIN


class WindowsBridgeTests(unittest.TestCase):
    def setUp(self):
        self.bridge = ChromeBridge(port=0)
        self.base = f'http://127.0.0.1:{self.bridge.server.server_port}'

    def tearDown(self):
        self.bridge.close()

    def call(self, path, token=None, data=None, **overrides):
        headers = {'X-URLHeat-Extension': EXTENSION_ID, 'X-URLHeat-Instance': 'browser-one'}
        if token:
            headers['Authorization'] = 'Bearer ' + token
        headers.update(overrides)
        body = json.dumps(data).encode() if data is not None else None
        with urlopen(Request(self.base + path, data=body, headers=headers), timeout=3) as response:
            return json.load(response)

    def test_only_expected_extension_can_pair_and_commands_require_task_token(self):
        for overrides in ({'Origin':'https://example.org'},
                          {'Origin':'chrome-extension://unrelated'},
                          {'X-URLHeat-Extension':'unrelated'}, {'Host':'example.org'}):
            with self.subTest(overrides=overrides), self.assertRaises(HTTPError) as error:
                self.call('/session', **overrides)
            self.assertEqual(error.exception.code, 403)
        token = self.call('/session', Origin=ORIGIN)['token']
        self.assertEqual(self.call('/next', token), {'command':None})
        with self.assertRaises(HTTPError) as error:
            self.call('/next', token='wrong-token')
        self.assertEqual(error.exception.code, 403)

    def test_a_second_profile_cannot_take_over_an_active_task(self):
        self.call('/session')
        with self.assertRaises(HTTPError) as error:
            self.call('/session', **{'X-URLHeat-Instance':'browser-two'})
        self.assertEqual(error.exception.code, 409)

    def test_round_trip_and_expired_commands_cannot_be_reused(self):
        token = self.call('/session')['token']
        with concurrent.futures.ThreadPoolExecutor() as executor:
            future = executor.submit(self.bridge.request, 'snapshot', timeout=3, noteId='note-one')
            deadline = time.monotonic() + 2
            command = None
            while command is None and time.monotonic() < deadline:
                command = self.call('/next', token)['command']
            self.assertIsNotNone(command)
            self.assertEqual(command['op'], 'snapshot')
            self.assertEqual(command['noteId'], 'note-one')
            self.call('/result', token, {'id':command['id'], 'value':{'url':'https://www.xiaohongshu.com/404'}})
            self.assertEqual(future.result(timeout=1), {'url':'https://www.xiaohongshu.com/404'})
        with self.assertRaisesRegex(RuntimeError, '未收到 Chrome 扩展响应'):
            self.bridge.request('open', timeout=0.02, url='https://www.xiaohongshu.com/')
        self.assertIsNone(self.call('/next', token)['command'])
        self.assertEqual(self.bridge.pending, {})

    def test_stop_cancels_waiting_without_a_second_browser(self):
        stopped = threading.Event()
        stopped.set()
        with self.assertRaisesRegex(RuntimeError, '已停止'):
            self.bridge.request('open', timeout=60, stop_event=stopped)
        self.assertEqual(self.bridge.pending, {})

    def test_manifest_matches_bridge_and_does_not_request_login_data(self):
        manifest = json.loads((Path(__file__).resolve().parents[1] / 'chrome_extension/manifest.json').read_text())
        public = base64.b64decode(manifest['key'])
        expected = ''.join(chr(ord('a') + int(c, 16)) for c in hashlib.sha256(public).hexdigest()[:32])
        self.assertEqual(expected, EXTENSION_ID)
        self.assertEqual(set(manifest['permissions']), {'scripting','storage','alarms'})
        self.assertEqual(set(manifest['host_permissions']), {'https://www.xiaohongshu.com/*','http://127.0.0.1:18739/*'})


if __name__ == '__main__':
    unittest.main()
