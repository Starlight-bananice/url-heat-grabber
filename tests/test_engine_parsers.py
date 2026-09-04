import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from selenium.webdriver.common.by import By

import engine
from app import remove_legacy_captcha_credentials


class FakeElement:
    def __init__(self, text=''):
        self.text = text


class FakeDriver:
    def __init__(
        self, *, title='', current_url='', source='', text='', selectors=None,
        cookies=None,
    ):
        self.title = title
        self.current_url = current_url
        self.page_source = source
        self._text = text
        self._selectors = selectors or {}
        self._cookies = cookies or []

    def execute_script(self, _script):
        return self._text

    def find_elements(self, by, selector):
        self.asserted_by = by
        return self._selectors.get(selector, [])

    def get_cookies(self):
        return self._cookies


class FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        return None

    def json(self):
        return self._payload


class ParserTests(unittest.TestCase):
    def test_baidu_embedded_metrics(self):
        source = '"like":{"is_like":"0","count":"41"},"playCount":"2139"'
        text = '41 收藏 分享 手机看 2139次播放 评论列表（6条）'
        self.assertEqual(
            engine.opt_extract_baidu_metrics(source, text),
            ('41', '6', '', '', '2139'),
        )

    def test_netease_rendered_metrics(self):
        source = '<div class="action-like"><div class="s-text">14赞</div></div>'
        text = '分享 14赞 有8人参与 来一起讨论吧'
        self.assertEqual(
            engine.opt_extract_netease_metrics(source, text),
            ('14', '8', '', '', ''),
        )

    def test_weibo_toolbar_metrics(self):
        source = (
            '<i title="转发"></i><span class="x_num_hash"><!----> 3</span>'
            '<i title="评论"></i><span class="x_num_hash"><!----> 1</span>'
            '<button title="赞"><span class="woo-like-count">14</span></button>'
        )
        self.assertEqual(
            engine.opt_extract_weibo_metrics(source),
            ('14', '1', '', '3', ''),
        )

    def test_tieba_reply_count(self):
        self.assertEqual(
            engine.opt_extract_tieba_metrics('', '全部回复 (238)'),
            ('', '238', '', '', ''),
        )

    def test_kuaishou_complete_visible_comment_list(self):
        selectors = {
            '.like-item .item-count': [FakeElement('16')],
            '.comment-list-item': [FakeElement() for _ in range(8)],
        }
        driver = FakeDriver(
            text='16 分享 已经到底了，没有更多评论了', selectors=selectors
        )
        self.assertEqual(
            engine.opt_extract_kuaishou_dom_metrics(driver),
            ('16', '8', '', '', ''),
        )
        self.assertEqual(driver.asserted_by, By.CSS_SELECTOR)

    @patch('engine.requests.get')
    def test_bilibili_api_metric_mapping(self, mock_get):
        mock_get.return_value = FakeResponse({
            'code': 0,
            'data': {'stat': {
                'like': 222,
                'reply': 120,
                'favorite': 35,
                'share': 7,
                'view': 14000,
            }},
        })
        self.assertEqual(
            engine.opt_fetch_bilibili_metrics('https://www.bilibili.com/video/BV1Example'),
            ('222', '120', '35', '7', '14000'),
        )

    def test_statuses_do_not_depend_on_old_xpath(self):
        baidu = FakeDriver(title='有效视频', text='2139次播放')
        self.assertEqual(
            engine.url_valid('https://mbd.baidu.com/newspage/data/videolanding', baidu),
            '正常',
        )

        netease = FakeDriver(title='有效文章', text='正文 分享 14赞')
        self.assertEqual(
            engine.url_valid('https://c.m.163.com/news/a/EXAMPLE.html', netease),
            '正常',
        )

        weibo = FakeDriver(title='微博正文 - 微博', text='公开 正文 3 1 14')
        self.assertEqual(
            engine.url_valid('https://weibo.com/user/example', weibo),
            '正常',
        )

    def test_restricted_and_redirected_statuses(self):
        wechat = FakeDriver(
            current_url='https://mp.weixin.qq.com/mp/wappoc_appmsgcaptcha',
            title='微信公众平台',
            text='当前环境异常，完成验证后即可继续访问。',
        )
        self.assertEqual(
            engine.url_valid('https://mp.weixin.qq.com/s?example=1', wechat),
            '需验证',
        )

        kuaishou = FakeDriver(
            current_url='https://www.kuaishou.com/short-video/example',
            title='短视频-快手',
            text='',
        )
        self.assertEqual(
            engine.url_valid('https://www.kuaishou.com/short-video/example', kuaishou),
            '访问受限',
        )

        ifeng = FakeDriver(
            current_url='https://finance.ifeng.com/',
            title='凤凰网财经',
            text='财经首页',
        )
        self.assertEqual(
            engine.url_valid('https://finance.ifeng.com/c/example', ifeng),
            '已删除',
        )

    def test_parser_version_invalidates_old_checkpoint_signature(self):
        current = engine.opt_signature(['https://example.com/a'], '1')
        old_payload = 'https://example.com/a\n1\nparser=0.5.2'
        import hashlib
        old = hashlib.sha256(old_payload.encode('utf-8')).hexdigest()
        self.assertNotEqual(current, old)

    def test_single_line_settings_and_legacy_credential_cleanup(self):
        with TemporaryDirectory() as directory:
            root = Path(directory)
            settings = root / 'settings.txt'
            settings.write_text(
                '只判断链接or抓取互动数和链接判断(0/1):1\n', encoding='utf-8'
            )
            self.assertEqual(engine.opt_read_settings(settings), '1')

            legacy = root / 'yzm.txt'
            legacy.write_text('旧版账号文件', encoding='utf-8')
            self.assertTrue(remove_legacy_captcha_credentials(legacy))
            self.assertFalse(legacy.exists())

    def test_kuaishou_uses_dedicated_worker_group(self):
        self.assertEqual(
            engine.opt_group('https://www.kuaishou.com/short-video/example'),
            'kuaishou',
        )
        self.assertEqual(engine.OPT_MAX_TOTAL_WORKERS, 4)

    def test_kuaishou_waits_for_complete_anonymous_session(self):
        incomplete = FakeDriver(cookies=[{'name': 'did', 'value': 'anonymous'}])
        complete = FakeDriver(
            current_url='https://www.kuaishou.com/new-reco',
            text='匿名推荐首页已经完成加载，可以继续打开公开作品详情页面',
            cookies=[
                {'name': 'did', 'value': 'anonymous'},
                {'name': 'kwssectoken', 'value': 'session'},
                {'name': 'clientid', 'value': '3'},
            ],
        )
        self.assertFalse(engine.opt_kuaishou_session_ready(incomplete))
        self.assertTrue(engine.opt_kuaishou_session_ready(complete))


if __name__ == '__main__':
    unittest.main()
