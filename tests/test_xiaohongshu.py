import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import Mock, patch

import engine
from ui_model import parse_links, platform_name


NOTE_ID = '1234567890abcdef12345678'
URL = f'https://www.xiaohongshu.com/explore/{NOTE_ID}?xsec_token=A%2B%3D&xsec_source=app_share'


def note(**info):
    return {'noteId': NOTE_ID, 'title': '不要删除这条笔记',
            'interactInfo': info}


class XiaohongshuTests(unittest.TestCase):
    def test_both_short_domains_are_supported_without_touching_token(self):
        links = ['https://xhslink.cn/o/abc', 'https://xhslink.com/a/abc', URL]
        self.assertEqual(parse_links('\n'.join(links)).links, links)
        for url in links:
            self.assertEqual(platform_name(url), '小红书')
            self.assertTrue(engine.opt_is_supported(url))
            self.assertEqual(engine.opt_group(url), 'xiaohongshu')
        self.assertEqual(platform_name('https://xhslink.cn.example.com/o/abc'), '不支持')

    def test_first_pass_uses_headless_browser_for_all_groups(self):
        assets = engine.OptDriverAssets('/tmp/chromedriver', '/tmp/chrome')
        for system in ('Darwin', 'Windows'):
            for group in ('xiaohongshu', 'other', 'douyin'):
                with self.subTest(system=system, group=group), patch.object(
                    engine.webdriver, 'Chrome', return_value=Mock()
                ) as create, patch.object(engine, 'Service'):
                    engine.opt_create_driver(assets, system, engine.OptimizedConfig(), group)
                    options = create.call_args.kwargs['options']
                    self.assertIn('--headless=new', options.arguments)

    def test_source_selects_only_requested_note_with_numeric_and_string_counts(self):
        state = {'note': {'noteDetailMap': {
            'other': {'note': {'noteId': 'other', 'interactInfo': {'likedCount': 999}}},
            NOTE_ID: {'note': note(likedCount=12, collectedCount='0', commentCount='3')},
        }}}
        source = '<script>window.__INITIAL_STATE__=' + json.dumps(state)[:-1] + ',"x":undefined,"label":"undefined"}</script>'
        selected = engine.opt_xhs_source_note(source, NOTE_ID)
        self.assertEqual(selected['noteId'], NOTE_ID)
        self.assertEqual(engine.opt_xhs_metrics({'note': selected}), ('12', '3', '0', '', ''))
        self.assertEqual(engine.opt_xhs_source_note(source, 'absent'), {})
        source = source.replace('"noteId": "' + NOTE_ID + '"', '"noteId": "other"')
        self.assertEqual(engine.opt_xhs_source_note(source, NOTE_ID), {})

    def test_generic_delete_words_and_note_body_are_not_deletion_evidence(self):
        page = {'url': URL, 'title': '标题 - 小红书', 'note': note(likedCount='1'),
                'text': '作者说不要删除，评论说你访问的页面不见了'}
        self.assertEqual(engine.opt_xhs_status(page), '正常')
        self.assertEqual(engine.opt_xhs_status(dict(page, note={}, content=True)), '正常')

    def test_visible_error_and_actual_404_are_deleted(self):
        for page in (
            {'url': URL, 'errors': '笔记已删除'},
            {'url': 'https://www.xiaohongshu.com/404?error_msg=当前笔记暂时无法浏览'},
            {'url': URL, 'title': '小红书 - 你访问的页面不见了'},
        ):
            self.assertEqual(engine.opt_xhs_status(page), '已删除')

    def test_risk_login_and_empty_pages_are_retryable(self):
        for page in (
            {'url': 'https://www.xiaohongshu.com/website-login/error?redirectPath=/404',
             'text': '安全限制\nIP存在风险，请切换可靠网络环境后重试'},
            {'url': 'https://www.xiaohongshu.com/login?redirectPath=/404'},
            {'url': URL},
        ):
            self.assertEqual(engine.opt_xhs_status(page), '访问受限')
        self.assertEqual(engine.opt_xhs_status({'title': '验证码中间页'}), '需验证')

    def test_live_state_and_current_toolbar_preserve_zero(self):
        driver = Mock(current_url=URL, title='正常笔记', page_source='删除')
        driver.execute_script.return_value = {'content': True, 'domMetrics': ['2.1万', '0', '5']}
        page = engine.opt_read_xhs_page(driver, URL)
        self.assertEqual(engine.opt_xhs_status(page), '正常')
        self.assertEqual(engine.opt_xhs_metrics(page), ('2.1万', '0', '5', '', ''))
        driver.execute_script.assert_called_once()
        self.assertEqual(driver.execute_script.call_args.args[1], NOTE_ID)
        self.assertEqual(engine.opt_xhs_metrics({}), ('', '', '', '', ''))

    def test_waits_for_metrics_after_note_container_appears(self):
        driver = Mock()
        pages = [dict(url=URL), dict(url=URL, content=True),
                 dict(url=URL, note=note(likedCount=0, commentCount=0, collectedCount=0))]
        with patch.object(engine, 'opt_read_xhs_page', side_effect=pages) as read:
            engine.opt_wait_xhs_content(driver, URL, 2)
        self.assertEqual(read.call_count, 3)

    def test_short_link_uses_resolved_id_and_original_output_url(self):
        short = 'https://xhslink.cn/o/abc'
        driver = Mock(current_url=URL, title='正常笔记', page_source='')
        driver.execute_script.return_value = {'note': note(likedCount='13', commentCount='4', collectedCount='2')}
        with patch.object(engine, 'opt_load_page') as load:
            row = engine.opt_process_one((1, short), driver, '1', 'Windows', engine.OptimizedConfig())
        load.assert_called_once()
        self.assertEqual(driver.execute_script.call_args.args[1], NOTE_ID)
        self.assertEqual(row['链接'], short)
        self.assertEqual(row['链接状态'], '')
        self.assertEqual(row['点赞'], '13')
        self.assertEqual(row['_xhs_parser_version'], engine.OPT_XHS_PARSER_VERSION)

    def test_missing_metrics_remain_no_data_and_do_not_trigger_browser_review(self):
        driver = Mock(current_url=URL, title='正常笔记', page_source='')
        driver.execute_script.return_value = {'content': True}
        with patch.object(engine, 'opt_load_page', return_value=''):
            row = engine.opt_process_one((1, URL), driver, '1', 'Darwin', engine.OptimizedConfig())
            self.assertEqual(row['链接状态'], '')
            self.assertTrue(all(row[key] == '' for key in engine.OPT_RESULT_HEADERS[2:]))
            self.assertFalse(engine.opt_xhs_needs_review(row))
            row = engine.opt_process_one((1, URL), driver, '0', 'Darwin', engine.OptimizedConfig())
            self.assertEqual(row['链接状态'], '')

    def test_resume_reprocesses_old_xhs_results_only(self):
        urls = [URL, 'https://xhslink.cn/o/abc', 'https://weibo.com/1/2',
                'https://xhslink.com/a/def']
        rows = {1: {'链接': urls[0], '链接状态': '已删除', '_xhs_parser_version': 4},
                2: {'链接': urls[1], '链接状态': '不支持'},
                3: engine.opt_result_row(urls[2], metrics=('5', '', '', '', '')),
                4: engine.opt_result_row(urls[3], metrics=('2', '', '', '', ''))}
        with TemporaryDirectory() as root:
            path = Path(root) / 'checkpoint.json'
            signature = engine.opt_signature(urls, '1')
            engine.opt_write_checkpoint(path, rows, 4, signature)
            self.assertEqual(set(engine.opt_load_checkpoint(path, urls, signature)), {3, 4})


if __name__ == '__main__':
    unittest.main()
