import unittest
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import engine


class IesdouyinTests(unittest.TestCase):
    def test_only_original_iesdouyin_work_urls_use_desktop(self):
        self.assertEqual(engine.opt_iesdouyin_desktop_url(
            'https://www.iesdouyin.com/share/video/123/?schema_type=37'),
            'https://www.douyin.com/video/123')
        self.assertEqual(engine.opt_iesdouyin_desktop_url(
            'https://iesdouyin.com/share/note/456?foo=1'),
            'https://www.douyin.com/note/456')
        for url in ('https://www.douyin.com/video/123',
                    'https://v.douyin.com/abc/',
                    'https://iesdouyin.com.example.org/share/video/123',
                    'https://example.org/?url=iesdouyin.com/share/video/123',
                    'https://www.iesdouyin.com/user/123'):
            self.assertIsNone(engine.opt_iesdouyin_desktop_url(url))

    def run_page(self, labels=None, title='', text='', captcha=False, visible=True, wait=None):
        driver = Mock()
        driver.title = title
        driver.execute_script.side_effect = lambda script, *args: args[0].text if args else text
        keys = ('video-player-digg', 'feed-comment-icon',
                'video-player-collect', 'video-player-share')

        def elements(by, selector):
            if 'iframe' in selector:
                return [Mock(is_displayed=Mock(return_value=visible))] if captcha else []
            for key, label in zip(keys, labels or [None] * 4):
                if selector == f'[data-e2e="{key}"]' and label is not None:
                    return [Mock(text=label)]
            return []

        driver.find_elements.side_effect = elements
        url = 'https://www.iesdouyin.com/share/video/123'
        with patch.object(engine, 'opt_navigate') as navigate, patch.object(engine, 'WebDriverWait') as waiter:
            if wait:
                waiter.return_value.until.side_effect = lambda ready: wait(ready, driver)
            row = engine.opt_process_one((1, url), driver, '1', 'Darwin', engine.OptimizedConfig())
        navigate.assert_called_once_with(driver, 'https://www.douyin.com/video/123', engine.OptimizedConfig())
        self.assertEqual(row['链接'], url)
        return row

    def test_metrics_and_label_only_zeroes(self):
        row = self.run_page(['481', '108', '74', '13'])
        fields = ('点赞', '评论/回复', '收藏', '分享/转发')
        self.assertEqual([row[k] for k in fields], ['481', '108', '74', '13'])
        row = self.run_page(['赞', '抢首评', '收藏', '分享'])
        self.assertEqual([row[k] for k in fields], ['0'] * 4)
        self.assertEqual(self.run_page(['1.2万', '2', '收藏', '分享'])['点赞'], '1.2万')

    def test_captcha_deleted_and_missing_toolbar_are_not_zeroes(self):
        self.assertEqual(self.run_page(title='验证码中间页')['链接状态'], '需验证')
        self.assertEqual(self.run_page(captcha=True)['链接状态'], '需验证')
        self.assertEqual(self.run_page(text='你要观看的视频不存在')['链接状态'], '已删除')
        self.assertEqual(self.run_page()['链接状态'], '处理失败')

    def test_deleted_page_takes_priority_over_captcha(self):
        for marker in engine.OPT_DOUYIN_DELETED_MARKERS:
            with self.subTest(marker=marker):
                row = self.run_page(text=marker, captcha=True, title='验证码中间页')
                self.assertEqual(row['链接状态'], '已删除')
                self.assertEqual(row['点赞'], '')

    def test_hidden_captcha_does_not_block_metrics(self):
        row = self.run_page(['12', '3', '4', '5'], captcha=True, visible=False)
        self.assertEqual(row['链接状态'], '')
        self.assertEqual(row['点赞'], '12')

    def test_waits_for_deleted_content_after_captcha(self):
        def wait(ready, driver):
            self.assertFalse(ready(driver))
            driver.execute_script.side_effect = lambda *args: '你要观看的视频不存在'
            self.assertTrue(ready(driver))

        row = self.run_page(captcha=True, wait=wait)
        self.assertEqual(row['链接状态'], '已删除')

    def test_douyin_original_link_keeps_legacy_route(self):
        url = 'https://www.douyin.com/video/123'
        with patch.object(engine, 'opt_process_iesdouyin') as desktop, \
             patch.object(engine, 'opt_load_page') as load, \
             patch.object(engine, 'url_valid', return_value='正常'), \
             patch.object(engine, 'get_interactions', return_value=('1', '', '', '', '')):
            engine.opt_process_one((1, url), Mock(), '1', 'Darwin', engine.OptimizedConfig())
        desktop.assert_not_called()
        self.assertEqual(load.call_args.args[1], engine.opt_normalize_url(url))

    def test_resume_rechecks_old_iesdouyin_results_only(self):
        urls = ['https://www.iesdouyin.com/share/video/123',
                'https://www.douyin.com/video/456',
                'https://www.iesdouyin.com/share/video/789']
        rows = {str(i): {'链接': url, '链接状态': ''} for i, url in enumerate(urls, 1)}
        rows['3']['_iesdouyin_parser_version'] = 1
        with TemporaryDirectory() as root:
            path = Path(root) / 'checkpoint.json'
            path.write_text(json.dumps({'input_signature': 'test', 'results': rows}))
            self.assertEqual(set(engine.opt_load_checkpoint(path, urls, 'test')), {2, 3})
