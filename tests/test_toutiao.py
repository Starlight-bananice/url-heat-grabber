import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import engine


URL = 'https://www.toutiao.com/i123456/'


class ToutiaoTests(unittest.TestCase):
    def tearDown(self):
        engine.OPT_STOP_EVENT.clear()

    @staticmethod
    def driver(title='今日头条', landed=URL, body='', content='', error='', metrics=None):
        driver = MagicMock(title=title, current_url=landed)
        driver.execute_script.return_value = body
        def elements(by, selector):
            if selector == '.error-content .error-tips':
                return [MagicMock(text=error)] if error else []
            if selector.startswith('.article-content,'):
                return [MagicMock(text=content)] if content else []
            if selector == '.detail-side-interaction, .ttp-video-extras-bar':
                return [MagicMock()] if metrics is not None else []
            keys = ['.detail-like,', '.detail-interaction-comment,', '.detail-interaction-collect,', '.share-btn,', '.views-count']
            for index, key in enumerate(keys):
                if key in selector and metrics and metrics[index] is not None:
                    text, label = metrics[index]
                    element = MagicMock(text=text)
                    element.get_attribute.return_value = label
                    return [element]
            return []
        driver.find_elements.side_effect = elements
        return driver

    def test_empty_title_shell_is_unresolved_on_both_platforms(self):
        for system in ('Darwin', 'Windows'):
            with self.subTest(system=system), patch('engine.platform.system', return_value=system):
                driver = self.driver()
                self.assertIsNone(engine.opt_toutiao_status(URL, driver))
                self.assertEqual(engine.url_valid(URL, driver), '访问受限')

    def test_deleted_title_message_and_timed_home_redirect(self):
        cases = [self.driver(title='404错误页'),
                 self.driver(error='抱歉，你访问的内容不存在'),
                 self.driver(landed='https://www.toutiao.com/?wid=123', body='推荐 关注')]
        for driver in cases:
            self.assertEqual(engine.opt_toutiao_status(URL, driver), '已删除')

    def test_article_quoting_error_or_verification_is_valid(self):
        driver = self.driver(title='为什么提示404错误页', body='安全验证 抱歉，你访问的内容不存在', content='文章正在讨论错误页面')
        self.assertEqual(engine.opt_toutiao_status(URL, driver), '正常')

    def test_challenge_and_rate_limit_are_not_deleted(self):
        self.assertEqual(engine.opt_toutiao_status(URL, self.driver(body='请完成验证')), '需验证')
        self.assertEqual(engine.opt_toutiao_status(URL, self.driver(body='访问过于频繁')), '访问受限')

    def test_login_redirect_is_not_a_successful_article(self):
        driver = self.driver(title='今日头条登录', landed='https://sso.toutiao.com/login/?service=example',
                             body='手机登录 扫码登录 获取验证码', content='登录表单')
        self.assertEqual(engine.opt_toutiao_status(URL, driver), '需验证')

    def test_missing_metric_does_not_discard_other_counts(self):
        driver = self.driver(content='微头条正文', metrics=[('3', '点赞3'), ('3', '3评论'), None, ('分享', '分享'), None])
        for system in ('Darwin', 'Windows'):
            with self.subTest(system=system), patch('engine.platform.system', return_value=system):
                self.assertEqual(engine.get_interactions(URL, driver), ('3', '3', '', '', ''))

    def test_zero_and_aria_counts_are_preserved(self):
        driver = self.driver(metrics=[('赞', '点赞0'), ('0', '0评论'), ('收藏', '收藏'), ('分享', '分享'), ('播放 0', None)])
        self.assertEqual(engine.opt_extract_toutiao_metrics(driver), ('0', '0', '', '', '0'))

    def test_video_metrics_include_plays_and_not_author_counts(self):
        driver = self.driver(body='粉丝999 赞888 播放777', content='视频标题',
                             metrics=[('70', None), ('66', None), ('12', None), ('分享', None), ('播放 4,113', None)])
        self.assertEqual(engine.opt_extract_toutiao_metrics(driver), ('70', '66', '12', '', '4113'))

    def test_loader_waits_on_both_platforms_without_reloading(self):
        for system in ('Darwin', 'Windows'):
            driver = self.driver()
            with patch('engine.opt_navigate') as navigate, patch('engine.opt_wait_toutiao_content') as wait:
                engine.opt_load_page(driver, URL, system, engine.OptimizedConfig())
            navigate.assert_called_once()
            wait.assert_called_once()
            driver.refresh.assert_not_called()

    def test_wait_ignores_initial_shell_until_content_and_toolbar(self):
        driver = self.driver(content='微头条正文', metrics=[('3', '点赞3'), ('3', '3评论'), None, None, None])
        with patch('engine.opt_toutiao_status', side_effect=[None, None, '正常']) as status:
            engine.opt_wait_toutiao_content(driver, URL, 1)
        self.assertEqual(status.call_count, 3)

    def test_wait_does_not_accept_empty_video_toolbar(self):
        driver = self.driver(content='视频标题', landed='https://www.toutiao.com/video/123456/',
                             metrics=[('', ''), ('', ''), None, None, None])
        with patch('engine.WebDriverWait') as wait:
            engine.opt_wait_toutiao_content(driver, URL, 1)
            ready = wait.return_value.until.call_args.args[0]
            self.assertFalse(ready(driver))
            loaded = self.driver(content='视频标题', landed=driver.current_url,
                                 metrics=[('赞', ''), ('评论', ''), None, None, ('播放 2', '')])
            self.assertTrue(ready(loaded))

    def test_wait_returns_immediately_for_deleted_or_stop(self):
        driver = self.driver(title='404错误页')
        engine.opt_wait_toutiao_content(driver, URL, 1)
        engine.OPT_STOP_EVENT.set()
        with patch('engine.opt_toutiao_status') as status:
            engine.opt_wait_toutiao_content(driver, URL, 1)
        status.assert_not_called()

    def test_old_headline_checkpoint_is_rechecked_without_losing_other_platforms(self):
        urls = [URL, 'https://weibo.com/1/2']
        signature = engine.opt_signature(urls, '1')
        rows = {1: {'链接': URL, '链接状态': '', '点赞': ''},
                2: engine.opt_result_row(urls[1], metrics=('3', '', '', '', ''))}
        with TemporaryDirectory() as root:
            checkpoint = Path(root) / 'checkpoint.json'
            engine.opt_write_checkpoint(checkpoint, rows, 2, signature)
            self.assertEqual(list(engine.opt_load_checkpoint(checkpoint, urls, signature)), [2])
            rows[1] = engine.opt_result_row(URL, metrics=('3', '3', '', '', ''))
            engine.opt_write_checkpoint(checkpoint, rows, 2, signature)
            self.assertEqual(list(engine.opt_load_checkpoint(checkpoint, urls, signature)), [1, 2])


if __name__ == '__main__':
    unittest.main()
