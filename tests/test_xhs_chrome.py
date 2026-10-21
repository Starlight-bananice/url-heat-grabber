import json
import unittest
from unittest.mock import Mock, patch

import engine
import xhs_chrome

NOTE = '1234567890abcdef12345678'
URL = 'https://www.xiaohongshu.com/explore/' + NOTE
SECOND = 'https://www.xiaohongshu.com/discovery/item/abcdef1234567890abcdef12'


def page(url=URL, likes=13):
    return dict(url=url, title='正常笔记', logged=True,
                note={'noteId':url.rsplit('/', 1)[-1],
                      'interactInfo':dict(likedCount=likes, commentCount=11, collectedCount=0)})


class ChromeBridgeTests(unittest.TestCase):
    def setUp(self):
        engine.OPT_STOP_EVENT.clear()

    def test_rejects_unrelated_origin_before_browser_access(self):
        for url in ('https://example.org/', 'https://www.xiaohongshu.com.example.org/', 'file:///tmp/test'):
            with self.subTest(url=url), patch.object(xhs_chrome, '_run') as run:
                with self.assertRaises(ValueError):
                    xhs_chrome.OriginalChrome(url)
                run.assert_not_called()

    def test_navigation_never_returns_previous_note(self):
        chrome = xhs_chrome.OriginalChrome.__new__(xhs_chrome.OriginalChrome)
        chrome.tab_id = '123'
        chrome.requested_url = SECOND
        old = page(SECOND)
        pending = dict(page(), pendingNavigation=True)
        current = page()
        with patch.object(xhs_chrome, '_run', side_effect=['', json.dumps(pending), json.dumps(old), json.dumps(current)]), patch.object(xhs_chrome.time, 'sleep'):
            self.assertEqual(chrome.read_page(URL, 5), current)

    def test_only_original_tab_is_used_without_exporting_a_session(self):
        chrome = Mock(spec=xhs_chrome.OriginalChrome)
        chrome.read_page.side_effect = [page(), page(SECOND, 5)]
        rows = []
        with patch.object(xhs_chrome, 'OriginalChrome', return_value=chrome), patch.object(engine, 'opt_create_driver') as create, patch.object(engine.OPT_STOP_EVENT, 'wait'):
            engine.opt_xhs_original_worker([(1, URL), (2, SECOND)], '1', 'Darwin', engine.OptimizedConfig(), lambda i, row: rows.append((i, row)))
        create.assert_not_called()
        chrome.close.assert_called_once()
        self.assertEqual([row['点赞'] for _, row in rows], ['13', '5'])
        self.assertEqual([row['收藏'] for _, row in rows], ['0', '0'])

    def test_restriction_does_not_launch_a_separate_browser(self):
        chrome = Mock(spec=xhs_chrome.OriginalChrome)
        chrome.read_page.return_value = {'url': URL, 'text': 'IP存在风险'}
        callback = Mock()
        with patch.object(xhs_chrome, 'OriginalChrome', return_value=chrome), patch.object(engine, 'opt_create_driver') as create:
            engine.opt_xhs_original_worker([(1, URL)], '1', 'Darwin', engine.OptimizedConfig(), callback)
        create.assert_not_called()
        self.assertEqual(callback.call_args.args[1]['链接状态'], '访问受限')
        chrome.close.assert_called_once()

    def test_permission_failure_does_not_create_another_login(self):
        chrome = Mock(spec=xhs_chrome.OriginalChrome)
        chrome.read_page.side_effect = RuntimeError('需要页面权限')
        callback = Mock()
        with patch.object(xhs_chrome, 'OriginalChrome', return_value=chrome), patch.object(engine, 'opt_create_driver') as create:
            engine.opt_xhs_original_worker([(1, URL)], '1', 'Darwin', engine.OptimizedConfig(), callback)
        create.assert_not_called()
        chrome.close.assert_called_once()
        self.assertEqual(callback.call_args.args[1]['链接状态'], '处理失败')

    def test_stop_closes_owned_tab_and_leaves_later_items_pending(self):
        chrome = Mock(spec=xhs_chrome.OriginalChrome)
        chrome.read_page.return_value = page()
        rows = []
        def stop(index, row):
            rows.append(index)
            engine.OPT_STOP_EVENT.set()
        try:
            with patch.object(xhs_chrome, 'OriginalChrome', return_value=chrome):
                engine.opt_xhs_original_worker([(1, URL), (2, SECOND)], '1', 'Darwin', engine.OptimizedConfig(), stop)
            self.assertEqual(rows, [1])
            chrome.close.assert_called_once()
        finally:
            engine.OPT_STOP_EVENT.clear()

    def test_windows_uses_extension_instead_of_selenium(self):
        with patch('xhs_windows.WindowsChrome') as chrome, patch.object(engine, 'opt_create_driver_with_retry') as create:
            chrome.return_value.read_page.return_value = page()
            callback = Mock()
            engine.opt_worker([(1, URL)], 'xiaohongshu', None, '1', 'Windows', engine.OptimizedConfig(), callback)
            create.assert_not_called()
            self.assertEqual(callback.call_args.args[1]['点赞'], '13')
            chrome.return_value.close.assert_called_once()


if __name__ == '__main__':
    unittest.main()
