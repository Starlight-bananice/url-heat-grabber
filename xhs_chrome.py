"""macOS Chrome bridge: reuse an existing Xiaohongshu login, never sign in."""
import json
import re
import subprocess
import time
from urllib.parse import urlsplit


_CREATE = '''on run argv
    tell application "Google Chrome"
        if (count of windows) is 0 then error "Open your signed-in Chrome window first"
        set browserWindow to front window
        set previousIndex to active tab index of browserWindow
        set targetTab to make new tab at end of tabs of browserWindow with properties {URL:item 1 of argv}
        set targetId to id of targetTab as string
        set active tab index of browserWindow to previousIndex
        return targetId
    end tell
end run'''
_EXECUTE = '''on run argv
    tell application "Google Chrome"
        repeat with browserWindow in windows
            repeat with browserTab in tabs of browserWindow
                if (id of browserTab as string) is item 1 of argv then
                    if URL of browserTab does not start with "https://www.xiaohongshu.com/" then error "Unexpected tab origin"
                    return execute browserTab javascript (item 2 of argv)
                end if
            end repeat
        end repeat
        error "Capture tab was closed"
    end tell
end run'''
_NAVIGATE = '''on run argv
    tell application "Google Chrome"
        repeat with browserWindow in windows
            repeat with browserTab in tabs of browserWindow
                if (id of browserTab as string) is item 1 of argv then
                    execute browserTab javascript "window.__URLHEAT_NAVIGATING__ = true"
                    set URL of browserTab to item 2 of argv
                    return
                end if
            end repeat
        end repeat
        error "Capture tab was closed"
    end tell
end run'''
_CLOSE = '''on run argv
    tell application "Google Chrome"
        repeat with browserWindow in windows
            repeat with browserTab in tabs of browserWindow
                if (id of browserTab as string) is item 1 of argv then
                    close browserTab
                    return
                end if
            end repeat
        end repeat
    end tell
end run'''
_SNAPSHOT = r'''JSON.stringify((() => {
    const requested = NOTE_ID;
    const match = location.pathname.match(/^\/(?:explore|discovery\/item)\/([a-f0-9]{24})\/?$/i);
    const id = requested || (match ? match[1] : '');
    const note = window.__INITIAL_STATE__?.note?.noteDetailMap?.[id]?.note;
    const root = document.querySelector('#noteContainer');
    const toolbar = root?.querySelector('.interact-container');
    const visible = el => Boolean(el && el.getClientRects().length);
    const text = el => el ? (el.innerText || '').trim() : '';
    const read = selector => text(toolbar?.querySelector(selector));
    return {url:location.href,title:document.title,text:text(document.body),
        pendingNavigation:Boolean(window.__URLHEAT_NAVIGATING__),
        note:note?.noteId === id ? note : null,
        content:visible(root?.querySelector('.note-content, .note-scroller')),
        errors:Array.from(document.querySelectorAll('.error-wrapper, .error-container, .error-page, .not-found-wrapper')).filter(visible).map(text).join('\n'),
        domMetrics:[read('.like-wrapper .count'),read('.chat-wrapper .count'),read('.collect-wrapper .count')],
        logged:document.querySelector('#global')?.getAttribute('data-logged') === '1'};
})())'''


def _run(script, *arguments):
    try:
        result = subprocess.run(['osascript', '-e', script, '--', *arguments],
                                capture_output=True, text=True, timeout=25)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise RuntimeError('连接原 Chrome 失败，请确认 Chrome 已打开。') from exc
    if result.returncode:
        # Never include returned page/session values or the command in logs.
        raise RuntimeError('原 Chrome 页面访问失败，请检查自动化权限及“允许 Apple 事件中的 JavaScript”。')
    return result.stdout.strip()


def _check_url(url):
    parsed = urlsplit(url)
    if parsed.scheme not in ('http', 'https') or parsed.hostname not in (
        'www.xiaohongshu.com', 'xiaohongshu.com', 'xhslink.cn', 'www.xhslink.cn',
        'xhslink.com', 'www.xhslink.com',
    ):
        raise ValueError('只能在小红书抓取标签页中打开小红书链接。')


class OriginalChrome:
    def __init__(self, url, stop_event=None):
        _check_url(url)
        self.tab_id = _run(_CREATE, url)
        self.requested_url = url

    def _navigate(self, url):
        _run(_NAVIGATE, self.tab_id, url)

    def _snapshot(self, note_id):
        script = _SNAPSHOT.replace('NOTE_ID', json.dumps(note_id))
        return json.loads(_run(_EXECUTE, self.tab_id, script))

    def read_page(self, url, timeout, stop_event=None):
        _check_url(url)
        if url != self.requested_url:
            self._navigate(url)
            self.requested_url = url
        match = re.fullmatch(r'/(?:explore|discovery/item)/([a-fA-F0-9]{24})/?', urlsplit(url).path)
        note_id = match[1] if match else ''
        deadline = time.monotonic() + timeout
        page = None
        while True:
            try:
                current = self._snapshot(note_id)
                # Navigation can briefly expose the previous document. Never reuse it.
                actual = urlsplit(current.get('url', ''))
                if not current.get('pendingNavigation') and (not match or actual.path.rstrip('/').endswith('/' + match[1]) or actual.path in ('/404', '/login', '/website-login/error')):
                    page = current
            except RuntimeError:
                if time.monotonic() >= deadline:
                    raise
            if page:
                info = (page.get('note') or {}).get('interactInfo') or {}
                has_counts = any(info.get(key) not in (None, '') for key in ('likedCount', 'commentCount', 'collectedCount'))
                has_counts = has_counts or any(re.search(r'\d', value) for value in page.get('domMetrics', []))
                if has_counts or page.get('errors') or urlsplit(page.get('url', '')).path in ('/404', '/website-login/error'):
                    return page
            if time.monotonic() >= deadline or (stop_event and stop_event.is_set()):
                return page or dict(url=url, title='', text='')
            time.sleep(0.4)

    def close(self):
        if self.tab_id:
            tab_id, self.tab_id = self.tab_id, None
            _run(_CLOSE, tab_id)
