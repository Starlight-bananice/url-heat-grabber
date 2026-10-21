"""Read the user's existing Chrome through the bundled, site-scoped extension.

The loopback bridge exists only during a capture task. It never transports
cookies, browser storage, or arbitrary JavaScript.
"""
import json
import queue
import secrets
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from xhs_chrome import OriginalChrome, _check_url


PORT = 18739
# Matches chrome_extension/manifest.json's public key.
EXTENSION_ID = 'kedbpkfcifeajfobdkacfkgaabcingbc'
ORIGIN = 'chrome-extension://' + EXTENSION_ID


class ChromeBridge:
    def __init__(self, port=PORT):
        self.token = secrets.token_urlsafe(32)
        self.client = None
        self.commands = queue.Queue()
        self.pending = {}
        self.lock = threading.Lock()
        bridge = self

        class Handler(BaseHTTPRequestHandler):
            def setup(self):
                super().setup()
                self.connection.settimeout(10)

            def log_message(self, *args):
                pass  # Page URLs and responses must not enter HTTP access logs.

            def _reply(self, code, value):
                body = json.dumps(value, ensure_ascii=True).encode('utf-8')
                self.send_response(code)
                self.send_header('Content-Type', 'application/json')
                self.send_header('Content-Length', str(len(body)))
                self.send_header('Cache-Control', 'no-store')
                self.send_header('Access-Control-Allow-Origin', ORIGIN)
                self.end_headers()
                try:
                    self.wfile.write(body)
                except (BrokenPipeError, ConnectionResetError):
                    pass

            def _allowed(self):
                # Extension requests may omit Origin. A web page cannot set the
                # custom header without a CORS preflight, which is rejected.
                return (self.headers.get('Host') == f'127.0.0.1:{bridge.server.server_port}'
                        and self.headers.get('Origin') in (None, ORIGIN)
                        and self.headers.get('X-URLHeat-Extension') == EXTENSION_ID)

            def _authenticated(self):
                supplied = self.headers.get('Authorization', '')
                return self._allowed() and secrets.compare_digest(supplied, 'Bearer ' + bridge.token)

            def do_OPTIONS(self):
                self._reply(403, {'error': 'Extension access only'})

            def do_GET(self):
                if not self._allowed():
                    return self._reply(403, {'error': 'Extension access only'})
                if self.path == '/session':
                    client = self.headers.get('X-URLHeat-Instance', '')
                    if not client or len(client) > 128:
                        return self._reply(400, {'error': 'Missing browser instance'})
                    with bridge.lock:
                        if bridge.client not in (None, client):
                            return self._reply(409, {'error': 'Another Chrome profile is connected'})
                        bridge.client = client
                    return self._reply(200, {'token': bridge.token})
                if not self._authenticated():
                    return self._reply(403, {'error': 'Invalid task session'})
                if self.path == '/next':
                    command = None
                    while not bridge.commands.empty():
                        try:
                            candidate = bridge.commands.get_nowait()
                        except queue.Empty:
                            break
                        with bridge.lock:
                            if candidate['id'] in bridge.pending:
                                command = candidate
                                break
                    return self._reply(200, {'command': command})
                self._reply(404, {'error': 'Not found'})

            def do_POST(self):
                if not self._authenticated():
                    return self._reply(403, {'error': 'Invalid task session'})
                if self.path != '/result':
                    return self._reply(404, {'error': 'Not found'})
                try:
                    size = int(self.headers.get('Content-Length', '0'))
                    if not 0 < size <= 2_000_000:
                        return self._reply(413, {'error': 'Invalid result size'})
                    result = json.loads(self.rfile.read(size))
                    if not isinstance(result, dict) or not isinstance(result.get('id'), str):
                        raise ValueError('Invalid result')
                except (ValueError, UnicodeError):
                    return self._reply(400, {'error': 'Invalid result'})
                with bridge.lock:
                    pending = bridge.pending.get(result['id'])
                    if pending:
                        pending['result'] = result
                        pending['event'].set()
                self._reply(200, {'ok': True})

        try:
            self.server = ThreadingHTTPServer(('127.0.0.1', port), Handler)
        except OSError as exc:
            raise RuntimeError('Chrome 连接端口被占用，请先结束其他小红书抓取任务。') from exc
        self.server.timeout = 1
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()

    def request(self, operation, timeout=25, stop_event=None, **arguments):
        request_id = secrets.token_hex(16)
        pending = {'event': threading.Event()}
        with self.lock:
            self.pending[request_id] = pending
        self.commands.put(dict(id=request_id, op=operation,
                               deadline=int((time.time() + timeout) * 1000), **arguments))
        deadline = time.monotonic() + timeout
        try:
            while not pending['event'].wait(0.1):
                if stop_event and stop_event.is_set():
                    raise RuntimeError('已停止 Chrome 抓取。')
                if time.monotonic() >= deadline:
                    raise RuntimeError('未收到 Chrome 扩展响应。请在已登录小红书的 Chrome 中加载随包扩展，并点击“连接抓取工具”。')
            result = pending['result']
            if result.get('error'):
                # Extension errors are fixed messages, never returned page data.
                raise RuntimeError('Chrome 后台标签页读取失败，请检查扩展连接和标签页是否仍打开。')
            return result.get('value')
        finally:
            with self.lock:
                self.pending.pop(request_id, None)

    def close(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)


class WindowsChrome(OriginalChrome):
    def __init__(self, url, stop_event=None):
        _check_url(url)
        self.tab_id = None
        self.stop_event = stop_event
        self.bridge = ChromeBridge()
        print('等待 Chrome 扩展连接：首次使用请加载安装包内的 Chrome扩展 文件夹，并点击扩展中的“连接抓取工具”。')
        try:
            self.tab_id = self.bridge.request('open', url=url, timeout=60, stop_event=stop_event)
            self.requested_url = url
        except Exception:
            self.bridge.close()
            raise

    def _navigate(self, url):
        _check_url(url)
        self.bridge.request('navigate', url=url, stop_event=self.stop_event)

    def _snapshot(self, note_id):
        value = self.bridge.request('snapshot', noteId=note_id, stop_event=self.stop_event)
        if not isinstance(value, dict):
            raise RuntimeError('Chrome 扩展返回的页面信息无效。')
        return value

    def close(self):
        try:
            if self.tab_id is not None:
                self.tab_id = None
                self.bridge.request('close', timeout=3)
        finally:
            self.bridge.close()
