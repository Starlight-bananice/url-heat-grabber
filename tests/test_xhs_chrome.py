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

    def test_headless_driver_closes_before_original_chrome_review_on_both_platforms(self):
        for system, create_name, bridge_name in (
            ('Windows', 'opt_create_driver_with_retry', 'xhs_windows.WindowsChrome'),
            ('Darwin', 'opt_create_driver', 'xhs_chrome.OriginalChrome'),
        ):
            with self.subTest(system=system):
                events = []
                driver = Mock()
                driver.quit.side_effect = lambda: events.append('headless closed')
                chrome = Mock(spec=xhs_chrome.OriginalChrome)
                chrome.read_page.return_value = page()
                def open_review(*args, **kwargs):
                    events.append('review opened')
                    return chrome
                callback = Mock()
                with patch(bridge_name, side_effect=open_review), \
                     patch.object(engine, create_name, return_value=driver) as create, \
                     patch.object(engine, 'opt_process_one', return_value=engine.opt_result_row(URL, status='已删除')):
                    engine.opt_worker([(1, URL)], 'xiaohongshu', None, '1', system, engine.OptimizedConfig(), callback)
                create.assert_called_once()
                self.assertEqual(events, ['headless closed', 'review opened'])
                self.assertEqual(callback.call_count, 1)
                self.assertEqual(callback.call_args.args[1]['点赞'], '13')
                chrome.close.assert_called_once()

    def test_only_suspect_rows_are_reviewed_after_entire_first_pass(self):
        urls = [URL + '?item=' + str(i) for i in range(1, 7)]
        bucket = list(enumerate(urls, 1))
        initial = [
            engine.opt_result_row(urls[0], metrics=('13', '11', '1', '', '')),
            engine.opt_result_row(urls[1]),
            engine.opt_result_row(urls[2], status='已删除'),
            engine.opt_result_row(urls[3], status='访问受限'),
            engine.opt_result_row(urls[4], status='需验证'),
            engine.opt_result_row(urls[5], metrics=('0', '0', '0', '', '')),
        ]
        events = []
        rows = {}
        def first(items, group, driver_path, mode, system, config, callback):
            for (index, url), row in zip(items, initial):
                events.append(('first', index))
                callback(index, row)
            events.append(('first done',))
        def review(items, mode, system, config, callback):
            self.assertEqual(events[-1], ('first done',))
            self.assertEqual([i for i, _ in items], [2, 3, 4, 5])
            for index, url in items:
                callback(index, engine.opt_result_row(url, metrics=('7', '', '', '', '')))
        with patch.object(engine, 'opt_selenium_worker', side_effect=first), \
             patch.object(engine, 'opt_xhs_original_worker', side_effect=review) as original:
            engine.opt_worker(bucket, 'xiaohongshu', None, '1', 'Darwin', engine.OptimizedConfig(), lambda i, row: rows.__setitem__(i, row))
        original.assert_called_once()
        self.assertEqual(set(rows), set(range(1, 7)))
        self.assertEqual(rows[1]['点赞'], '13')
        self.assertEqual(rows[6]['点赞'], '0')
        self.assertEqual([rows[i]['点赞'] for i in (2, 3, 4, 5)], ['7'] * 4)

    def test_successful_first_pass_never_opens_original_chrome(self):
        row = engine.opt_result_row(URL, metrics=('0', '0', '0', '', ''))
        def first(items, group, driver_path, mode, system, config, callback):
            callback(1, row)
        callback = Mock()
        with patch.object(engine, 'opt_selenium_worker', side_effect=first), \
             patch.object(engine, 'opt_xhs_original_worker') as original:
            engine.opt_worker([(1, URL)], 'xiaohongshu', None, '1', 'Windows', engine.OptimizedConfig(), callback)
        original.assert_not_called()
        callback.assert_called_once_with(1, row)

    def test_status_only_success_and_local_failures_do_not_trigger_review(self):
        self.assertFalse(engine.opt_xhs_needs_review(engine.opt_result_row(URL), '0'))
        self.assertFalse(engine.opt_xhs_needs_review(engine.opt_result_row(URL, status='处理失败'), '1'))
        self.assertTrue(engine.opt_xhs_needs_review(engine.opt_result_row(URL, status='已删除'), '0'))

    def test_stop_before_review_does_not_finalize_provisional_deletion(self):
        def first(items, group, driver_path, mode, system, config, callback):
            callback(1, engine.opt_result_row(URL, status='已删除'))
            engine.OPT_STOP_EVENT.set()
        callback = Mock()
        try:
            with patch.object(engine, 'opt_selenium_worker', side_effect=first), \
                 patch.object(engine, 'opt_xhs_original_worker') as original:
                engine.opt_worker([(1, URL)], 'xiaohongshu', None, '1', 'Darwin', engine.OptimizedConfig(), callback)
            original.assert_not_called()
            callback.assert_not_called()
        finally:
            engine.OPT_STOP_EVENT.clear()

    def test_failed_review_does_not_confirm_first_pass_deletion(self):
        def first(items, group, driver_path, mode, system, config, callback):
            callback(1, engine.opt_result_row(URL, status='已删除'))
        def review(items, mode, system, config, callback):
            callback(1, engine.opt_result_row(URL, status='处理失败'))
        callback = Mock()
        with patch.object(engine, 'opt_selenium_worker', side_effect=first), \
             patch.object(engine, 'opt_xhs_original_worker', side_effect=review):
            engine.opt_worker([(1, URL)], 'xiaohongshu', None, '1', 'Windows', engine.OptimizedConfig(), callback)
        callback.assert_called_once()
        self.assertEqual(callback.call_args.args[1]['链接状态'], '处理失败')


if __name__ == '__main__':
    unittest.main()
