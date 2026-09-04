import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

import engine


def toolbar(values=None, order=None, href='xlink:href'):
    values = values or {'share_pb': '2', 'comment_pb': '238', 'agree_pb': '745', 'collect': '28'}
    parts = []
    for icon in order or values:
        parts.append(f'<div class="item-warp"><div class="action-item no-disabled"><svg><use {href}="#{icon}"></use></svg><span class="action-number"> {values[icon]} </span></div></div>')
    return '<div class="pc-pb-first-floor-interactive"><div class="action-bar-warp">' + ''.join(parts) + '</div></div>'


class TiebaTests(unittest.TestCase):
    def tearDown(self):
        engine.OPT_STOP_EVENT.clear()

    def test_all_four_metrics_from_post_toolbar(self):
        self.assertEqual(engine.opt_extract_tieba_metrics(toolbar(), '全部回复 (238)'), ('745', '238', '28', '2', ''))

    def test_metric_identity_does_not_depend_on_button_order(self):
        html = toolbar(order=['collect', 'agree_pb', 'share_pb', 'comment_pb'], href='href')
        self.assertEqual(engine.opt_extract_tieba_metrics(html, ''), ('745', '238', '28', '2', ''))

    def test_reply_and_advertisement_likes_are_not_post_likes(self):
        other = '<div class="reply"><div class="action-item"><svg><use href="#agree_pb"/></svg><span class="action-number">9000</span></div></div>'
        self.assertEqual(engine.opt_extract_tieba_metrics(other + toolbar() + other, ''), ('745', '238', '28', '2', ''))

    def test_zero_is_preserved_but_missing_is_not_invented(self):
        html = toolbar({'agree_pb': '0', 'comment_pb': '0', 'share_pb': '转发', 'collect': '收藏'})
        self.assertEqual(engine.opt_extract_tieba_metrics(html, ''), ('0', '0', '', '', ''))
        self.assertEqual(engine.opt_metric_value(0), '0')
        self.assertEqual(engine.opt_metric_value(None), '')

    def test_human_readable_reply_count_legacy_fallback(self):
        self.assertEqual(engine.opt_extract_tieba_metrics('', '全部回复 (238)'), ('', '238', '', '', ''))
        self.assertEqual(engine.opt_extract_tieba_metrics('', '1,238回复贴，共32页'), ('', '1238', '', '', ''))

    def test_status_distinguishes_real_post_challenge_deleted_and_blank(self):
        self.assertEqual(engine.opt_tieba_status('讨论百度安全验证的帖子', '有人说请完成下方验证后继续操作', toolbar()), '正常')
        self.assertEqual(engine.opt_tieba_status('百度安全验证', '请完成下方验证后继续操作', '<div>验证</div>'), '需验证')
        self.assertEqual(engine.opt_tieba_status('百度安全验证', '请完成下方验证后继续操作', '<div class="pc-pb-first-floor-interactive"></div>'), '需验证')
        self.assertEqual(engine.opt_tieba_status('贴吧404', '该贴已被删除', ''), '已删除')
        self.assertEqual(engine.opt_tieba_status('百度贴吧', '加载中...', ''), '访问受限')
        self.assertEqual(engine.opt_tieba_status('旧版帖子', '正文', '<div class="d_post_content">正文</div>'), '正常')

    def test_loaded_post_is_not_refreshed(self):
        for system in ('Darwin', 'Windows'):
            with self.subTest(system=system):
                driver = MagicMock()
                with patch('engine.opt_navigate'), patch('engine.opt_wait_tieba_content', return_value=True) as wait:
                    engine.opt_load_page(driver, 'https://tieba.baidu.com/p/123', system, engine.OptimizedConfig())
                driver.refresh.assert_not_called()
                self.assertEqual(wait.call_count, 1)

    def test_unsettled_post_has_at_most_one_reload(self):
        driver = MagicMock()
        for waits in ([False, True], [False, False]):
            driver.reset_mock()
            with patch('engine.opt_navigate'), patch('engine.opt_wait_body'), patch('engine.opt_wait_tieba_content', side_effect=waits) as wait:
                engine.opt_load_page(driver, 'https://tieba.baidu.com/p/123', 'Darwin', engine.OptimizedConfig())
            driver.refresh.assert_called_once()
            self.assertEqual(wait.call_count, 2)

    def test_stop_does_not_start_a_reload(self):
        engine.OPT_STOP_EVENT.set()
        driver = MagicMock()
        with patch('engine.opt_navigate'), patch('engine.opt_wait_tieba_content', return_value=False):
            engine.opt_load_page(driver, 'https://tieba.baidu.com/p/123', 'Darwin', engine.OptimizedConfig())
        driver.refresh.assert_not_called()

    def test_both_platforms_use_post_toolbar_and_real_challenge_status(self):
        url = 'https://tieba.baidu.com/p/123'
        for system in ('Darwin', 'Windows'):
            with self.subTest(system=system), patch('engine.platform.system', return_value=system):
                driver = MagicMock(title='讨论百度安全验证的帖子', page_source=toolbar())
                driver.execute_script.return_value = '请完成下方验证后继续操作'
                self.assertEqual(engine.url_valid(url, driver), '正常')
                self.assertEqual(engine.get_interactions(url, driver), ('745', '238', '28', '2', ''))
                driver.title = '百度安全验证'
                driver.page_source = '<div>请完成下方验证后继续操作</div>'
                self.assertEqual(engine.url_valid(url, driver), '需验证')

    def test_old_tieba_checkpoint_retries_without_discarding_other_platforms(self):
        for system in ('Darwin', 'Windows'):
            with self.subTest(system=system), patch('engine.platform.system', return_value=system):
                self.check_tieba_checkpoint()

    def check_tieba_checkpoint(self):
        urls = ['https://tieba.baidu.com/p/123', 'https://weibo.com/1/2']
        rows = {1: {'链接': urls[0], '链接状态': '', '评论/回复': '238'}, 2: engine.opt_result_row(urls[1], metrics=('3', '', '', '', ''))}
        signature = engine.opt_signature(urls, '1')
        with TemporaryDirectory() as root:
            checkpoint = Path(root) / 'checkpoint.json'
            engine.opt_write_checkpoint(checkpoint, rows, 2, signature)
            self.assertEqual(list(engine.opt_load_checkpoint(checkpoint, urls, signature)), [2])
            rows[1] = engine.opt_result_row(urls[0], metrics=('745', '238', '28', '2', ''))
            engine.opt_write_checkpoint(checkpoint, rows, 2, signature)
            self.assertEqual(list(engine.opt_load_checkpoint(checkpoint, urls, signature)), [1, 2])


if __name__ == '__main__':
    unittest.main()
