
'''
无头浏览器版本
功能：链接有效性判断+互动数抓取
'''


import argparse
import concurrent.futures
import hashlib
import html
import os
import subprocess
import threading
import traceback
from html.parser import HTMLParser
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import getproxies
from ui_model import platform_name, write_result_workbook

import time, re, csv, requests, json, platform, random
from selenium.webdriver import Chrome  # 导入谷歌浏览器的类
# 配置无头信息
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.selenium_manager import SeleniumManager
from selenium.common.exceptions import (
    NoSuchElementException,
    StaleElementReferenceException,
    TimeoutException,
    WebDriverException,
)
from openpyxl import Workbook
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service



# 保存的list
url_lists = []
# print(111, url_lists)

## 获取链接
def get_url_lists():
    ## 判断系统 win or mac
    os_name = platform.system()
    # print(1234, os_name)
    ## 获取抓取需求：只判断链接/互动数+链接判断
    with open('settings.txt', 'r', encoding='utf-8') as file:
        set_lists = file.readlines()
        judge_nedds = set_lists[0].split(':')[1].strip('\n')
    ## 获取链接
    with open('urls.txt', 'r', encoding='utf-8') as file:
        lists = file.readlines()
        # total_lines = len(lists)  # 统计总行数
        # print(34, total_lines)
    num = 1
    for li in lists:
        url = li.strip('\n')
        url_includ(url, num, judge_nedds, os_name)
        num += 1

## 先判断链接是否在处理规则内，如果不在，不用启动浏览器驱动和解析，节约资源
def url_includ(url, num, judge_nedds, os_name):
    ## 判断链接是否在处理规则内
    if (url.find("douyin.com") > -1) or (url.find("baidu.com") > -1) or (url.find("www.toutiao.com") > -1) or (url.find("kuaishou.com") > -1) or (url.find("weibo.com") > -1) or (url.find("ixigua.com") > -1)  or (url.find("haokan.baidu.com") > -1 ) or (url.find("163.com") > -1) or (url.find("yoojia.com") > -1) or (url.find("uczzd.cn") > -1) or (url.find("mp.uc.cn") > -1) or (url.find("ifeng.com") > -1) or (url.find("sohu.com") > -1) or (url.find("360kuai.com") > -1) or (url.find("myzaker.com") > -1) or (url.find("yidianzixun.com") > -1) or (url.find("mp.weixin.qq") > -1) or (url.find("html2.qktoutiao.com") > -1) or (url.find("tieba.baidu.com") > -1) or (url.find("bilibili.com") > -1) or (url.find("dongchedi.com") > -1) or (url.find("news.qq.com") > -1) or (url.find("sina.com") > -1) or (url.find("sina.cn") > -1) or (url.find("iqiyi.com") > -1) or (url.find("xiaohongshu.com") > -1):
        headless_chrom(url, num, judge_nedds, os_name)
    else:
        print(url, '：链接解析不在规则内')
        url_lists.append({'链接': url, '链接状态': '', '点赞': '', '评论/回复': '', '收藏': '', '分享/转发': '', '播放/阅读': ''})   ## 根据二组要求，给正常的状态设置为空就行，不需要写"正常"2个字
        print(f'第{num}条：', url)
        # print(f'第{num}条 ', '链接:',url, '链接状态:', '', '点赞:' '', '评论/回复': '', '收藏': '', '分享/转发': '', '播放/阅读': '')


## 无头浏览器
def headless_chrom(url, num, judge_nedds, os_name):

    if os_name=='Windows':
    # if os_name=='mac':
        driver_path = 'chromedriver.exe'
    else:
        with open('chromedriver_path.txt', 'r', encoding='utf-8') as file:
            driver_path = file.readlines()[0]  ## 获取mac系统里的 驱动链接（目前看要从根目录开始）
            # judge_nedds = set_lists[0].split(':')[1].strip('\n')
        # driver_path =
    service = Service(driver_path)
    opt = Options()
    opt.add_argument("--headless")  # 设置为无头模式
    opt.add_argument("--disable-gpu")  # 禁用GPU加速
    if os_name=='Windows':
        opt.add_argument(f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')   ## 不带请求头有时候头条的源码会有问题，导致解析有问题
    else:
        opt.add_argument(f'User-Agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36')  ## 不带请求头有时候头条的源码会有问题，导致解析有问题
    # 创建浏览器对象

    # web = Chrome(service=service, options=opt)
    web = webdriver.Chrome(service=service, options=opt)

    # 链接处理
    # if (url.find("www.iesdouyin.com") > -1) and (url.find("?schema_type=37") == -1):
    if (url.find("www.iesdouyin.com") > -1) and (url.find("?schema_type=37") == -1):
        current_url = url + '/?schema_type=37'
    elif url.find("www.douyin.com/video") > -1:
        current_url = url.replace('www.douyin.com/video/','www.iesdouyin.com/share/video/') + '/?schema_type=37'
        # print(2222, current_url)
    elif url.find("www.myzaker.com/article/") > -1:
        part_url = url.replace('http://www.myzaker.com/article/','').replace('https://www.myzaker.com/article/','')
        current_url = 'http://app.myzaker.com/news/article.php?pk=' + part_url
        # print(234, icurrent_url)
    else:
        current_url = url  ## 这个只在 判断的时候有用，因为判断的时候 头条那块是用 跳转后链接判断的

    ## 请求链接
    if current_url.find("haokan.baidu.com") > -1:
        web.get(current_url)
        time.sleep(2)
        web.refresh()
        time.sleep(2)
    elif current_url.find("tieba.baidu.com") > -1:
        web.get(current_url)
        time.sleep(2)
        web.refresh()
        time.sleep(2)
    elif current_url.find("douyin.com") > -1:
        web, html_source = douyin_page(current_url, os_name)
    elif current_url.find("xiaohongshu.com") > -1:
        web, html_source = hong_page(current_url, os_name)
    else:
        web.get(current_url)


    # 只判断链接 还是 互动数+链接 ———— 只判断链接：1  互动数+链接:0
    # if judge_nedds == '1'

    # # 关闭弹窗
    # close_button = web.find_element(By.XPATH, '//*[@id="douyin_login_comp_flat_panel"]/div/div[1]/div[3]/svg')
    # close_button.click()
    #
    # try:
    #     close_button = WebDriverWait(web, 10).until(
    #         EC.element_to_be_clickable((By.CLASS_NAME, "close-button"))
    #     )
    #     close_button.click()
    # except Exception as e:
    #     # print("未找到弹窗：", e)
    #     # print("未找到弹窗：")
    #     pass

    # 互动数抓取： 互动数+链接判断：1     只判断链接：0
    if judge_nedds == '1':
        # print(3333)
        ## 先判断链接
        # get_valid = url_valid(url, current_url, web)
        # html_source = html_source
        if (current_url.find("xiaohongshu.com") > -1):
            get_valid = url_valid(current_url, web, html_source)
        else:
            get_valid = url_valid(current_url, web)
        ## 获取互动数
        if get_valid == '正常':
            if (current_url.find("douyin.com") > -1) or (current_url.find("xiaohongshu.com") > -1):
                engagements = get_interactions(current_url, web, html_source, os_name)  ## 互动数
            else:
                engagements = get_interactions(current_url, web)    ## 互动数

            ## 根据项目组同学要求，将“链接状态”是“正常”的改成空
            url_lists.append({'链接': url, '链接状态': '', '点赞': engagements[0], '评论/回复': engagements[1], '收藏': engagements[2], '分享/转发': engagements[3], '播放/阅读': engagements[4]})  ## 根据二组要求，给正常的状态设置为空就行，不需要写"正常"2个字
            print(f'第{num}条：', url)
        else:
            likes = ''
            comments = ''
            collects = ''
            shares = ''
            plays = ''
            url_lists.append({'链接': url, '链接状态':get_valid, '点赞':likes, '评论/回复':comments, '收藏':collects, '分享/转发':shares, '播放/阅读':plays})
            print(f'第{num}条：', url)

    else:
        ## 只判断链接
        # url_result = url_valid(url, current_url, web)
        url_result = url_valid(current_url, web)
        # print(f'第{num}条', url, url_result)
        if url_result == '正常':
            url_lists.append({'链接': url, '链接状态': '', '点赞': '', '评论/回复': '', '收藏': '', '分享/转发': '', '播放/阅读': ''})   ## 根据二组要求，给正常的状态设置为空就行，不需要写"正常"2个字
            print(f'第{num}条：', url)
        else:
            url_lists.append({'链接': url, '链接状态': url_result, '点赞': '', '评论/回复': '', '收藏': '', '分享/转发': '', '播放/阅读': ''})
            print(f'第{num}条：', url)

## 无头浏览器----mac系统
# def headless_chrom_mac(url, url_pinjie):
#     driver_path = 'chromedriver.exe'
#     service = Service(driver_path)
#     opt = Options()
#     opt.add_argument("--headless")  # 设置为无头模式
#     opt.add_argument("--disable-gpu")  # 禁用GPU加速
#     # opt.add_argument(f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')   ## 不带请求头有时候头条的源码会有问题，导致解析有问题
#     opt.add_argument(f'User-Agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')  ## 不带请求头有时候头条的源码会有问题，导致解析有问题

## 链接判断
def opt_wait_element_text(web, by, selector, timeout=6.0, empty_values=()):
    """等待动态互动控件出现，并返回去除首尾空白后的文本。"""
    def read_text(current):
        try:
            value = current.find_element(by, selector).text.strip()
            return value if value and value not in empty_values else False
        except (NoSuchElementException, StaleElementReferenceException):
            return False

    try:
        return WebDriverWait(
            web, min(max(timeout, 0.5), 15.0), poll_frequency=0.25
        ).until(read_text)
    except TimeoutException:
        return ''


def url_valid(current_url, web, html_source=None):
    try:
        if platform_name(current_url) == '今日头条':
            return opt_toutiao_status(current_url, web) or '访问受限'
        if platform_name(current_url) == '百度贴吧':
            return opt_tieba_status(web.title, opt_page_text(web), web.page_source)
        if platform.system() != 'Windows':
            mac_status = opt_macos_url_status(current_url, web)
            if mac_status is not None:
                return mac_status
        # if (current_url.find("www.iesdouyin.com") > -1) or (current_url.find("www.douyin.com") > -1):  # http://www.iesdouyin.com/share/video/7484537032434273545, https://www.douyin.com/share/video/7584440207907228934
        if (current_url.find("douyin.com") > -1):  # http://www.iesdouyin.com/share/video/7484537032434273545, https://www.douyin.com/share/video/7584440207907228934
            # 只读取当前页面，不再因为一个 XPath 失效就跳转到 /note/。
            # 跳转会重复加载页面，并使后续互动数解析与当前 URL 不一致。
            source = html_source or ''
            try:
                content = web.execute_script(
                    'return document.body ? document.body.innerText : "";'
                ) or ''
            except WebDriverException:
                raise
            searchable = f'{content}\n{source}'
            if any(marker in searchable for marker in OPT_DOUYIN_DELETED_MARKERS):
                return '已删除'
            return '正常'

        if (current_url.find("xiaohongshu.com") > -1):
            # time.sleep(2)
            # print(4444, web.page_source)
            html_source = html_source
            if (html_source.find('你访问的页面不见了') > -1) or (html_source.find('删除') > -1):
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        # elif (current_url.find("mbd.baidu.com") > -1) or (current_url.find("baijiahao.baidu.com") > -1):
        elif (current_url.find("mbd.baidu.com") > -1) or (current_url.find("baijiahao.baidu.com") > -1) or (current_url.find("quanmin.baidu.com") > -1):
            if platform.system() == 'Windows':
                content = web.execute_script(
                    'return document.body ? document.body.innerText : "";'
                ) or ''
                deleted_markers = (
                    '抱歉，你找的页面不见啦', '这里空空如也', '文章暂时找不到了'
                )
                return '已删除' if any(marker in content for marker in deleted_markers) else '正常'
            time.sleep(3)
            content = web.find_element(By.XPATH,'//*[@id="contaniner"]|//*[@id="app"]/div/div[2]/div/p').text
            if any(marker in content for marker in (
                '抱歉，你找的页面不见啦', '这里空空如也', '文章暂时找不到了'
            )):
                return '已删除'
            return '正常'

        elif current_url.find("html2.qktoutiao.com") > -1:    ##  趣头条判断要放在头条前面，因为他链接域名包含了今日头条的。   https://html2.qktoutiao.com/detail/2025/03/23/1746714228.html
            time.sleep(3)
            content = web.page_source
            if content.find('NoSuchKey') > -1:
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        elif current_url.find("kuaishou.com") > -1:
            if platform.system() == 'Windows':
                content = web.execute_script(
                    'return document.body ? document.body.innerText : "";'
                ) or ''
                deleted_markers = ('作品已失效', '您要访问的页面弄丢了', '该作品已被删除')
                return '已删除' if any(marker in content for marker in deleted_markers) else '正常'
            time.sleep(1)
            title_text = (web.title).strip()   ## strip():删除前后空格
            # content = web.find_element(By.XPATH, '//*[@id="__next"]/div/div[2]/section/div/div[2]/div[1]').text    ## '您要访问的页面弄丢了'
            # if content.find('您要访问的页面弄丢了') > -1:
            # if (title_text.find('快手') > -1) or (content.find('短视频-快手') > -1) or (content.find('您要访问的页面弄丢了') > -1):
            # if  (title_text.find('短视频-快手') == 0) or (title_text.find('快手') == 0):
            if title_text.find('快手') == 0:
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        # elif current_url.find("www.kuaishou.com") > -1:
        #     time.sleep(1)
        #     # title_text = (web.title).strip()   ## strip():删除前后空格
        #     # print(33,title_text)
        #     # print(334,title_text.find('快手'))
        #     print(335,web.page_source)
        #     content = web.find_element(By.XPATH, '//*[@id="app"]/div[1]/section/div/div/div/div[1]/div[4]/p').text    ## '您要访问的页面弄丢了'
        #     print(222, content)
        #     # if content.find('您要访问的页面弄丢了') > -1:
        #     # if (title_text.find('快手') > -1) or (content.find('短视频-快手') > -1) or (content.find('您要访问的页面弄丢了') > -1):
        #     # if  (title_text.find('短视频-快手') == 0) or (title_text.find('快手') == 0):
        #     if content.find('作品已失效') == 0:
        #         ls = '已删除'
        #     else:
        #         ls = '正常'
        #     # print(url, ls)
        #     # url_lists.append([url, ls])
        #     return ls

        elif current_url.find("weibo.com") > -1:  # 贴吧： http://weibo.com/1003386063/On1jCcdY3     微博头条：http://weibo.com/ttarticle/p/show?id=2309405000545722302653
            if platform.system() == 'Windows':
                content = web.execute_script(
                    'return document.body ? document.body.innerText : "";'
                ) or ''
                deleted_markers = ('该微博不存在', '原文章已被删除', '暂无查看权限')
                return '已删除' if any(marker in content for marker in deleted_markers) else '正常'
            time.sleep(3)
            content = web.find_element(By.XPATH, '//*[@id="app"]/div[2]/div[2]/div[2]/main/div[1]/div/div[2]/div/div/span|//*[@id="plc_main"]/div/div/div/div/p[1]|//*[@class="woo-tip-text"]').text
            if (content.find('该微博不存在') > -1) or (content.find('原文章已被删除') > -1) or (content.find('暂无查看权限') > -1):
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        elif current_url.find("ixigua.com") > -1:    ## 西瓜视频 PC版本已经合并到抖音里（不存在pc版了），但是被删除的信息链接还是西瓜界面
            time.sleep(3)
            title_text = web.title
            # if (title_text.find('内容可能已删除') > -1) or (content.find('非常抱歉！您查看的页面找不到了...') > -1):
            if (title_text.find('内容可能已删除') > -1):
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        elif current_url.find("haokan.baidu.com") > -1:     ## https://haokan.baidu.com/v?vid=4543273714238499923
            if platform.system() == 'Windows':
                content = web.execute_script(
                    'return document.body ? document.body.innerText : "";'
                ) or ''
                return '已删除' if '抱歉，您访问的视频不存在' in content else '正常'
            content = web.find_element(
                By.XPATH, '//*[@id="rooot"]/div/p[@class="error-text"]/span'
            ).text
            return '已删除' if '抱歉，您访问的视频不存在，点击' in content else '正常'

        elif current_url.find("163.com") > -1:
            time.sleep(1)
            title_text = web.title
            if title_text.find('网易-404') > -1:
                ls = '已删除'
            elif title_text.find('内容不存在或已被删除') > -1:
                ls = '已删除'
            elif title_text.find('内容不存在或被删除') > -1:
                ls = '已删除'
            elif title_text.find('网页跑丢了') > -1:
                ls = '已删除'
            elif title_text.find('404!页面找不到了') > -1:
                ls = '已删除'
            elif title_text.find('视频不存在或已被删除') > -1:
                ls = '已删除'
            elif title_text.find('动态不存在或已被删除') > -1:
                ls = '已删除'
            elif title_text.find('该内容无法查看') > -1:
                ls = '已删除'
            elif title_text == '网易':  ## http://dy.163.com/v2/article/detail/KH04T5JV055616YC.html
                ls = '已删除'
            elif title_text == '手机网易网':  ## https://m.163.com/news/article/KH51T5R30553TF8P.html
                ls = '已删除'
            elif platform.system() == 'Windows':
                content = web.execute_script(
                    'return document.body ? document.body.innerText : "";'
                ) or ''
                deleted_markers = ('动态不存在或已被删除', '内容不存在或已被删除')
                ls = '已删除' if any(marker in content for marker in deleted_markers) else '正常'
            else:
                content = web.find_element(By.XPATH, '//*[@class="text"]').text
                if content.find('动态不存在或已被删除') > -1:
                    ls = '已删除'
                else:
                    ls = '正常'
            return ls

        elif current_url.find("www.yoojia.com") > -1:
            time.sleep(3)
            title_text = web.title    ## title=404错误页 为已删除
            if (title_text.find('undefined-有驾') > -1) or (title_text.find('有驾-真车评，懂行情！') > -1):
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        elif (current_url.find("uczzd.cn") > -1) or (current_url.find("mp.uc.cn") > -1):   # https://m.uczzd.cn/ucnews/news?aid=5392058188236442797
            time.sleep(3)
            title_text = web.title  ## title=404错误页 为已删除
            # if content.find('文章不存在') > -1:
            if (title_text.find('UC头条') > -1) or (title_text == ''):
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        # elif current_url.find("ishare.ifeng.com/") > -1:  # http://ishare.ifeng.com/c/s/v006iNtWf2WUJSB7FM6gaIpjZQBbX8--6w46QcobUGu2jegTeTDwjNSPf88fXvDvSNZv0
        elif current_url.find("ifeng.com/") > -1:  # http://ishare.ifeng.com/c/s/v006iNtWf2WUJSB7FM6gaIpjZQBbX8--6w46QcobUGu2jegTeTDwjNSPf88fXvDvSNZv0
            time.sleep(1)
            title_text = web.title  ## title=404错误页 为已删除
            # if content.find('对不起, 该网页随风而逝') > -1:
            if (
                platform.system() == 'Windows'
                and '/c/' in current_url
                and web.current_url.rstrip('/') in (
                    'https://finance.ifeng.com', 'http://finance.ifeng.com'
                )
            ):
                ls = '已删除'
            elif title_text.find('凤凰热榜') > -1:
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        elif current_url.find("3g.k.sohu.com/h5apps/t/") > -1:  # 因为这个搜狐链接不能通过web.title方法判断链接是否正常，所以单独拿出来判断     http://3g.k.sohu.com/h5apps/t/feed?action=307&uid=1604507970-6843825581097138949-U&type=1&currentPage=1&pageSize=20&cursorId=0&snstype=1
            time.sleep(1)
            # title_text = web.title  ## title=404错误页 为已删除
            # print(11, title_text)
            try:
                content = web.find_element(By.XPATH, '//*[@class="user"]/span[1]').text   ## 获取作者， 因为这个链接暂时没有找到被删除的，所以先进行下反向判断，先判断含有作者的都为正常，反之为删除
            except:
                content = ''
            # if content.find('您访问的页面不见了') > -1:
            if content == '':
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        elif current_url.find("sohu.com") > -1:  # https://www.sohu.com/a/802546848_121157845
            time.sleep(1)
            title_text = web.title  ## title=404错误页 为已删除
            # content = web.find_element(By.XPATH, '/html/body/div[1]/div/div/h4').text
            # if content.find('您访问的页面不见了') > -1:
            if (title_text=='手机搜狐网') or (title_text=='404 Not Found') or (title_text=='404,您访问的页面已经不存在!') or (title_text=='搜狐新闻-时间线'):
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        elif current_url.find("www.360kuai.com") > -1:  # 快资讯： https://www.360kuai.com/9ca8c1d1b4eba540a?d5bf6b48de6a1a232e012c47272b5717
            time.sleep(3)
            title_text = web.title  ## title=404错误页 为已删除
            # content = web.find_element(By.XPATH, '//*[@id="content-container"]/div[2]/div[1]/div[1]/div[2]/div').text
            # if content.find('该文章已删除') > -1:
            if title_text=='undefined_【快资讯】':
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        elif (current_url.find("app.myzaker.com/news") > -1) or (current_url.find("www.myzaker.com") > -1):  # zaker： https://app.myzaker.com/news/article.php?pk=666a524fb15ec042d65b320a  http://www.myzaker.com/article/66129c0a8e9f092aed59b90b
            time.sleep(3)
            title_text = web.title  ## title=404错误页 为已删除
            # content = web.find_element(By.XPATH,'/html/body/div[2]').text
            # if content.find('您访问的文章不存在或者已经下线') > -1:
            if (title_text=='ZAKER') or (title_text=='404页面'):
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        elif current_url.find("yidianzixun.com") > -1:  # 一点资讯： http://www.yidianzixun.com/article/0sxktYvz
            time.sleep(3)
            title_text = web.title  ## title=404错误页 为已删除
            # content = web.find_element(By.XPATH, '/html/body/div[1]/div[1]/p').text
            # if content.find('出错了！文章没有找到哦') > -1:
            if title_text=='【一点资讯】 www.yidianzixun.com':
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        elif current_url.find("mp.weixin.qq") > -1:   ## 需要测试
            if platform.system() == 'Windows':
                content = web.execute_script(
                    'return document.body ? document.body.innerText : "";'
                ) or ''
                if 'wappoc_appmsgcaptcha' in web.current_url:
                    return '需验证'
                deleted_markers = (
                    '该内容已被发布者删除', '此内容被投诉且经审核涉嫌侵权，无法查看',
                    '此账号已自主注销，内容无法查看',
                )
                return '已删除' if any(marker in content for marker in deleted_markers) else '正常'
            time.sleep(3)
            content = web.find_element(By.XPATH,'//*[@id="activity-detail"]/div[2]/div[2]/div').text
            if (content.find('该内容已被发布者删除') > -1) or (content.find('此内容被投诉且经审核涉嫌侵权，无法查看') > -1) or (content.find('此账号已自主注销，内容无法查看') > -1):
            # if (title_text.find('该内容已被发布者删除') > -1) or (title_text.find('此内容被投诉且经审核涉嫌侵权，无法查看') > -1) or (title_text.find('此账号已自主注销，内容无法查看') > -1):
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        elif current_url.find("tieba.baidu.com") > -1:   ##贴吧链接在队列最后的时候，不要多出空行，不然会报错，因为涉及到验证码平台     http://tieba.baidu.com/p/8731976443   https://tieba.baidu.com/p/10056041768
            # time.sleep(3)
            title_text = web.title
            if platform.system() == 'Windows':
                content = web.execute_script(
                    'return document.body ? document.body.innerText : "";'
                ) or ''
                if '百度安全验证' in title_text or '请完成下方验证后继续操作' in content:
                    return '需验证'
                if '该贴已被删除' in content or title_text.find('贴吧404') > -1:
                    return '已删除'
                return '正常'
            # content = web.find_element(By.XPATH, '//*[@id="errorText"]/h1').text
            # if content.find('该贴已被删除') > -1:
            if title_text.find('贴吧404') > -1:
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        elif current_url.find("bilibili.com") > -1:   ## https://www.bilibili.com/video/BV11C4y1Y7fn     https://t.bilibili.com/1138734158186545157?tab=2
            if platform.system() == 'Windows':
                content = web.execute_script(
                    'return document.body ? document.body.innerText : "";'
                ) or ''
                deleted_markers = ('啊叻？视频不见了？', '视频已失效', '稿件不可见')
                return '已删除' if any(marker in content for marker in deleted_markers) else '正常'
            content = web.find_element(By.XPATH, '//*[@id="mirror-vdcon"]/div[1]/div/div[2]/div[1]|/html/body/div[2]/div[1]/div/a').text
            if (content.find('啊叻？视频不见了？') > -1) or (content.find('返回上一页') > -1):
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        elif current_url.find("dongchedi.com") > -1:   # 懂车帝 https://www.dongchedi.com/article/7292053577869197875
            title_text = web.title
            if title_text.find('懂车帝 - 说真的还得懂车帝') > -1:
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        elif current_url.find("news.qq.com") > -1:   # https://news.qq.com/rain/a/20250920A03AF000
            title_text = web.title
            if title_text.find('404') > -1:
                ls = '已删除'
            else:
                ls = '正常'
            return ls

        elif (current_url.find("sina.com") > -1) or (current_url.find("sina.cn") > -1):   # https://k.sina.com.cn/article_1893761531_m70e081fb02002wyys.html
            title_text = web.title
            if (title_text.find('该文章已不存在') > -1) or (title_text == '财经头条') or (title_text == '新浪财经'):
                ls = '已删除'
            else:
                ls = '正常'
            return ls
        else:
            print('链接不在规则内')
            return '正常'

    except WebDriverException:
        raise
    except Exception as e:
        return '正常'


def opt_clean_douyin_metric(value):
    value = ' '.join(str(value or '').split())
    if value in {'赞', '评论', '抢首评', '收藏', '分享', '0'}:
        return ''
    return value


def opt_extract_douyin_metrics(html_source):
    """从已加载页面源码中快速读取互动数，避免为取数再次导航。"""
    source = html_source or ''
    if not source:
        return None

    variants = (
        source,
        source.replace(r'\"', '"').replace(r'\u0022', '"'),
        html.unescape(source),
        html.unescape(source).replace(r'\"', '"').replace(r'\u0022', '"'),
    )
    patterns = {
        key: (
            re.compile(rf'"{key}"\s*:\s*"([^"]*)"'),
            re.compile(rf'"{key}"\s*:\s*([^,}}]+)'),
        )
        for key in ('diggCount', 'commentCount', 'collectCount', 'shareCount')
    }
    values = {}
    for key, key_patterns in patterns.items():
        for variant in variants:
            for pattern in key_patterns:
                match = pattern.search(variant)
                if match:
                    values[key] = opt_clean_douyin_metric(match.group(1).strip())
                    break
            if key in values:
                break

    ordered = tuple(values.get(key, '') for key in (
        'diggCount', 'commentCount', 'collectCount', 'shareCount'
    ))
    return ordered + ('',) if any(ordered) else None


def opt_extract_douyin_dom_metrics(driver, timeout):
    """仅在源码没有互动数时短暂等待 DOM，避免重复刷新页面。"""
    def read_values(current):
        values = []
        for xpath in OPT_DOUYIN_METRIC_XPATHS:
            if platform.system() != 'Windows':
                try:
                    values.append(opt_clean_douyin_metric(
                        current.find_element(By.XPATH, xpath).text
                    ))
                except (NoSuchElementException, StaleElementReferenceException):
                    values.append('')
                continue
            value = ''
            try:
                for element in current.find_elements(By.XPATH, xpath):
                    text = current.execute_script(
                        'return (arguments[0].innerText || arguments[0].textContent || "").trim();',
                        element,
                    )
                    value = opt_clean_douyin_metric(text)
                    if value:
                        break
            except StaleElementReferenceException:
                value = ''
            values.append(value)
        return tuple(values) if any(values) else False

    try:
        max_wait = 8.0 if platform.system() == 'Windows' else 2.5
        values = WebDriverWait(
            driver, min(max(timeout, 0.5), max_wait), poll_frequency=0.2
        ).until(read_values)
    except TimeoutException:
        return None
    return values + ('',)


OPT_TOUTIAO_METRIC_SELECTORS = (
    '.detail-side-interaction .detail-like, .ttp-video-extras-bar .video-action-button.like',
    '.detail-side-interaction .detail-interaction-comment, .ttp-video-extras-bar .video-action-button.comment',
    '.detail-side-interaction .detail-interaction-collect, .ttp-video-extras-bar .video-action-button.favour',
    '.detail-side-interaction .share-btn, .ttp-video-extras-bar .share-btn',
    '.ttp-video-extras-bar .views-count',
)
OPT_TOUTIAO_CONTENT_SELECTOR = (
    '.article-content, .weitoutiao-html, .wtt-content, '
    '.ttp-video-extras-title h1'
)


def opt_extract_toutiao_metrics(driver):
    """仅从当前文章、微头条或视频的互动栏取数，不混入评论和推荐。"""
    # opt_load_page 已等到正文和互动栏；各指标独立读取，缺少收藏不应丢失点赞。
    values = []
    for selector in OPT_TOUTIAO_METRIC_SELECTORS:
        value = ''
        for element in driver.find_elements(By.CSS_SELECTOR, selector):
            try:
                value = opt_metric_value(element.text) or opt_metric_value(element.get_attribute('aria-label'))
                if value:
                    break
            except StaleElementReferenceException:
                continue
        values.append(value)
    return tuple(values)


def opt_toutiao_status(current_url, driver):
    """None 表示还在加载；空白页不能当成正常且没有互动数。"""
    landed = urlparse(driver.current_url or '')
    if landed.hostname == 'sso.toutiao.com' or (driver.title or '').strip() == '今日头条登录':
        return '需验证'
    if (driver.title or '').strip() == '404错误页':
        return '已删除'
    for element in driver.find_elements(By.CSS_SELECTOR, '.error-content .error-tips'):
        if opt_contains_any(element.text, ('你访问的内容不存在', '内容已删除', '内容不存在')):
            return '已删除'
    requested = urlparse(current_url)
    if (landed.hostname in ('www.toutiao.com', 'toutiao.com')
            and landed.path in ('', '/')
            and re.match(r'^/(?:i\d+|(?:article|video|w)/\d+)/?$', requested.path)):
        return '已删除'
    for element in driver.find_elements(By.CSS_SELECTOR, OPT_TOUTIAO_CONTENT_SELECTOR):
        if element.text.strip():
            return '正常'
    # 仅在没有正文时识别验证/限流提示，避免误读文章中的引用。
    text = opt_page_searchable(driver)
    if opt_contains_any(text, ('请完成验证', '安全验证', '验证后继续')):
        return '需验证'
    if opt_contains_any(text, ('访问过于频繁', '请求过于频繁', '访问受限')):
        return '访问受限'
    return None


def opt_wait_toutiao_content(driver, current_url, timeout):
    def ready(current):
        if OPT_STOP_EVENT.is_set():
            return True
        status = opt_toutiao_status(current_url, current)
        if status and status != '正常':
            return True
        if status != '正常':
            return False
        # 视频正文、空工具栏与数字会分阶段渲染；不能只等待容器出现。
        for selector in OPT_TOUTIAO_METRIC_SELECTORS[:2]:
            if not any(element.text.strip() or element.get_attribute('aria-label')
                       for element in current.find_elements(By.CSS_SELECTOR, selector)):
                return False
        if '/video/' in (current.current_url or ''):
            return bool(opt_first_element_text(current, By.CSS_SELECTOR, (OPT_TOUTIAO_METRIC_SELECTORS[4],)))
        return True
    try:
        WebDriverWait(driver, min(max(timeout, 0.5), 15.0), poll_frequency=0.25,
                      ignored_exceptions=(StaleElementReferenceException,)).until(ready)
    except TimeoutException:
        pass


def opt_extract_bilibili_metrics(current_url):
    """Windows 版通过哔哩哔哩公开详情接口读取视频互动数。"""
    match = re.search(r'/video/(BV[0-9A-Za-z]+)', current_url, re.IGNORECASE)
    if not match:
        return None
    try:
        response = requests.get(
            'https://api.bilibili.com/x/web-interface/view',
            params={'bvid': match.group(1)},
            headers={'User-Agent': 'Mozilla/5.0'},
            timeout=12,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get('code') != 0:
            return None
        stat = (payload.get('data') or {}).get('stat') or {}
    except (requests.RequestException, ValueError):
        return None

    def clean(value):
        return '' if value in (None, 0, '0') else str(value)

    return (
        clean(stat.get('like')),
        clean(stat.get('reply')),
        clean(stat.get('favorite')),
        clean(stat.get('share')),
        clean(stat.get('view')),
    )


def opt_extract_kuaishou_metrics(current_url, web):
    """从 Windows Chrome 已完成的快手 GraphQL 响应中读取互动数。"""
    photo_match = re.search(r'/short-video/([^/?#]+)', current_url)
    if not photo_match:
        return None
    photo_id = photo_match.group(1)
    likes = opt_wait_element_text(
        web, By.CSS_SELECTOR, '.interactive-item.like-item .item-count', 2.0,
        {'0', 'undefined'},
    )
    comments = ''
    shares = ''
    plays = ''

    try:
        logs = web.get_log('performance')
    except Exception:
        logs = []
    operations = {}
    responses = set()
    for entry in logs:
        try:
            message = json.loads(entry['message'])['message']
            params = message.get('params') or {}
            if message.get('method') == 'Network.requestWillBeSent':
                request = params.get('request') or {}
                if request.get('url') != 'https://www.kuaishou.com/graphql':
                    continue
                post_data = request.get('postData') or ''
                if photo_id not in post_data:
                    continue
                operation = (json.loads(post_data) or {}).get('operationName')
                if operation in ('visionVideoDetail', 'commentListQuery'):
                    operations[params.get('requestId')] = operation
            elif (
                message.get('method') == 'Network.responseReceived'
                and (params.get('response') or {}).get('url')
                == 'https://www.kuaishou.com/graphql'
            ):
                responses.add(params.get('requestId'))
        except (KeyError, TypeError, ValueError):
            continue

    for request_id, operation in operations.items():
        if request_id not in responses:
            continue
        try:
            body = web.execute_cdp_cmd(
                'Network.getResponseBody', {'requestId': request_id}
            ).get('body', '')
            data = (json.loads(body).get('data') or {})
            if operation == 'visionVideoDetail':
                photo = ((data.get('visionVideoDetail') or {}).get('photo') or {})
                likes = photo.get('likeCount') or likes
                plays = photo.get('viewCount') or plays
            else:
                comment_data = data.get('visionCommentList') or {}
                comments = (
                    comment_data.get('commentCountV2')
                    if comment_data.get('commentCountV2') is not None
                    else comment_data.get('commentCount')
                )
        except (WebDriverException, TypeError, ValueError):
            continue

    if not likes or not plays:
        try:
            response = requests.get(
                f'https://v.m.chenzhongtech.com/fw/photo/{photo_id}',
                headers={
                    'User-Agent': (
                        'Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 '
                        '(KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36'
                    )
                },
                timeout=12,
            )
            response.raise_for_status()
            source = response.text
            likes_match = re.search(r'"likeCount"\s*:\s*(\d+)', source)
            shares_match = re.search(r'"forwardCount"\s*:\s*(\d+)', source)
            plays_match = re.search(r'"viewCount"\s*:\s*(\d+)', source)
            likes = likes or (likes_match.group(1) if likes_match else '')
            shares = shares_match.group(1) if shares_match else ''
            plays = plays or (plays_match.group(1) if plays_match else '')
        except requests.RequestException:
            pass

    def clean(value):
        return '' if value in (None, 0, '0', 'undefined') else str(value)

    return clean(likes), clean(comments), '', clean(shares), clean(plays)


## 抓取互动数
# def get_interactions(url, current_url, web):
def get_interactions(current_url, web, html_source=None, os_name=None):
    try:
        if platform_name(current_url) == '今日头条':
            return opt_extract_toutiao_metrics(web)
        if platform_name(current_url) == '百度贴吧':
            return opt_extract_tieba_metrics(web.page_source, opt_page_text(web))
        if platform.system() != 'Windows':
            mac_metrics = opt_macos_interactions(current_url, web)
            if mac_metrics is not None:
                return mac_metrics
        ## 抖音
        # if (current_url.find("www.iesdouyin.com") > -1) or (current_url.find("www.douyin.com") > -1):  # 抖音
        if (current_url.find("douyin.com") > -1):  # 抖音
            # 优先解析当前页面源码，不再为取互动数重复导航同一页面。
            metrics = opt_extract_douyin_metrics(html_source)
            if metrics is not None:
                return metrics
            # 这样不会因为指标暂未渲染而重复触发完整页面请求。
            metrics = opt_extract_douyin_dom_metrics(
                web,
                getattr(getattr(OPT_THREAD_STATE, 'config', None), 'element_timeout', 2.5),
            )
            return metrics or ('', '', '', '', '')

        ## 小红书
        if (current_url.find("xiaohongshu.com") > -1):
            html_source = html_source
            os_name = os_name
            max_cycles = min(
                getattr(getattr(OPT_THREAD_STATE, 'config', None), 'douyin_retries', 3),
                3,
            )
            for cycles in range(1, max_cycles + 1):
                try:
                    likes = web.find_element(By.XPATH,'//*[@id="noteContainer"]/div[4]/div[3]/div/div/div[1]/div[2]/div/div[1]/span[1]/span[2]').text  ## 点赞
                    comments = web.find_element(By.XPATH,'//*[@id="noteContainer"]/div[4]/div[3]/div/div/div[1]/div[2]/div/div[1]/span[3]/span').text  ## 评论
                    collects = web.find_element(By.XPATH, '//*[@id="note-page-collect-board-guide"]/span').text  ## 收藏
                    shares = ''  ## 分享
                    plays = ''
                    break  ## 执行到这，说明已经解析顺利，跳出循环
                except:
                    if html_source.find('interactInfo') > -1:
                        likes = re.findall(r'likedCount":"(.*?)"', html_source)[0]  ## 点赞
                        comments = re.findall(r'"commentCount":"(.*?)"', html_source)[0]  ## 评论
                        collects = re.findall(r'collectedCount":"(.*?)"', html_source)[0]  ## 收藏
                        shares = ''
                        plays = ''
                        break  ## 执行到这，说明已经解析顺利，跳出循环
                        # print(2222222, likes, comments, collects, shares, plays)
                    else:
                        print(f'第 {cycles} 次尝试出现异常！')
                if cycles < max_cycles:
                    print(f'重试第{cycles}次')
                    time.sleep(random.uniform(1.0, 2.0))
                    web, html_source = hong_page(current_url, os_name)
                else:
                    print('已达最大重试次数，请手动补充数据。')
            if (likes == '赞') or (likes == '0'):
                likes = ''
            if (comments == '评论') or (comments == '0'):
                comments = ''
            if (collects == '收藏') or (collects == '0'):
                collects = ''
            if (shares == '分享') or (shares == '0'):
                shares = ''
            # print(234521, likes, comments, collects, shares, plays)
            return likes, comments, collects, shares, plays

        # elif (current_url.find("mbd.baidu.com") > -1) or (current_url.find("baijiahao.baidu.com") > -1):   ## 百家号
        elif (current_url.find("mbd.baidu.com") > -1) or (current_url.find("baijiahao.baidu.com") > -1) or (current_url.find("quanmin.baidu.com") > -1):   ## 百家号
            if current_url.find('videolanding') > -1:
                try:
                    likes = web.find_element(By.XPATH, '//*[@id="app"]/div/div[2]/div[1]/div[1]/div[1]/div[2]/ul[1]/li[1]').text  ## 点赞
                except:
                    likes = ''
                try:
                    comments = web.find_element(By.XPATH, '//*[@id="page-comment"]/div[2]/div/h2').text.replace('评论列表（','').replace('条）','')  ## 评论
                except:
                    comments = ''
                try:
                    collects = web.find_element(By.XPATH, '//*[@id="app"]/div/div[2]/div[1]/div[1]/div[1]/div[2]/ul[1]/li[2]').text  ## 收藏
                except:
                    collects = ''
                try:
                    shares = web.find_element(By.XPATH, '//*[@id="app"]/div/div[2]/div[1]/div[1]/div[1]/div[2]/ul[1]/li[3]/div[1]').text  ## 分享
                except:
                    shares = ''
                try:
                    plays = web.find_element(By.XPATH, '//*[@id="app"]/div/div[2]/div[1]/div[1]/div[1]/div[2]/ul[2]/span').text.replace('次播放','')  ## 播放
                except:
                    plays = ''
            elif (current_url.find('dtlandingwise') > -1) or (current_url.find('dtlandingsuper') > -1):
                try:
                    likes = web.find_element(By.XPATH, '//*[@id="app"]/div/div[2]/div/div[1]/div[1]/div[3]/div/div[2]').text  ## 点赞
                except:
                    likes = ''
                try:
                    comments = web.find_element(By.XPATH, '//*[@id="app"]/div/div[2]/div/div[1]/div[1]/div[3]/div/div[1]').text  ## 评论
                except:
                    comments = ''
                collects = ''  ## 收藏
                shares = ''  ## 分享
                plays = ''  ## 播放
            elif current_url.find('baijiahao.baidu.com') > -1:
                if platform.system() == 'Windows':
                    timeout = getattr(
                        getattr(OPT_THREAD_STATE, 'config', None), 'element_timeout', 6.0
                    )
                    likes = opt_wait_element_text(
                        web, By.CSS_SELECTOR,
                        '[data-testid="like-btn"] .interact-desc', max(timeout, 12.0),
                        {'0', '赞'},
                    )
                    comments = opt_wait_element_text(
                        web, By.CSS_SELECTOR,
                        '[data-testid="comment-btn"] .interact-desc', max(timeout, 12.0),
                        {'0', '评论'},
                    )
                else:
                    try:
                        likes = web.find_element(By.XPATH, '//*[@id="ssr-content"]/div[2]/div[2]/div[2]').text
                    except Exception:
                        likes = ''
                    try:
                        comments = web.find_element(By.XPATH, '//*[@id="ssr-content"]/div[2]/div[2]/div[1]').text
                    except Exception:
                        comments = ''
                collects = ''  ## 收藏
                shares = ''  ## 分享
                plays = ''  ## 播放
            elif current_url.find('quanmin.baidu.com') > -1:
                # print(1234,web.page_source)
                try:
                    likes = web.find_element(By.XPATH, '//*[@class="main"]/div[2]/div/div/div/div[2]/ul/li[1]').text  ## 点赞
                except:
                    likes = ''
                try:
                    comments = web.find_element(By.XPATH, '//*[@class="xcp-list-title"]').text.replace('评论列表（','').replace('条）','')  ## 评论
                except:
                    comments = ''
                try:
                    collects = web.find_element(By.XPATH, '//*[@class="main"]/div[2]/div/div/div/div[2]/ul/li[2]').text  ## 收藏
                except:
                    collects = ''
                try:
                    shares = web.find_element(By.XPATH, '//*[@class="main"]/div[2]/div/div/div/div[2]/ul/li[3]/div[1]').text  ## 分享
                except:
                    shares = ''
                try:
                    plays = web.find_element(By.XPATH, '//*[@class="main"]/div[2]/div/div/div/div[2]/ul[2]/span').text.replace('次播放','')  ## 播放
                except:
                    plays = ''
            else:
                likes = ''  ## 点赞
                comments = ''  ## 评论
                collects = ''  ## 收藏
                shares = ''  ## 分享
                plays = ''
            if (likes == '赞') or (likes == '0'):
                likes = ''
            if (comments == '评论') or (comments == '0'):
                comments = ''
            if (collects == '收藏') or (collects == '0'):
                collects = ''
            if (shares == '分享') or (shares == '0'):
                shares = ''
            if plays == '0':
                plays = ''
            return likes, comments, collects, shares, plays

        elif current_url.find("html2.qktoutiao.com") > -1:    ##  趣头条   没有互动数
            likes = ''
            comments = ''
            collects = ''
            shares = ''
            plays = ''
            return likes, comments, collects, shares, plays

        elif current_url.find("kuaishou.com") > -1 and platform.system() == 'Windows':
            metrics = opt_extract_kuaishou_metrics(current_url, web)
            return metrics or ('', '', '', '', '')

        elif current_url.find("weibo.com") > -1:  # 贴吧： http://weibo.com/1003386063/On1jCcdY3     微博头条：http://weibo.com/ttarticle/p/show?id=2309405000545722302653
            if platform.system() == 'Windows':
                timeout = getattr(
                    getattr(OPT_THREAD_STATE, 'config', None), 'element_timeout', 6.0
                )
                likes = opt_wait_element_text(
                    web, By.CSS_SELECTOR, 'button[title="赞"] .woo-like-count', timeout,
                    {'0', '赞'},
                )
                comments = opt_wait_element_text(
                    web, By.XPATH,
                    '(//i[@title="评论"]/ancestor::div[contains(@class,"woo-box-item-flex")][1])[1]',
                    timeout, {'0', '评论'},
                )
                shares = opt_wait_element_text(
                    web, By.XPATH,
                    '(//i[@title="转发"]/ancestor::div[contains(@class,"woo-box-item-flex")][1])[1]',
                    timeout, {'0', '转发'},
                )
                return likes, comments, '', shares, ''
            try:
                likes = web.find_element(By.XPATH, '//*[@id="app"]/div[1]/div[2]/div[2]/main/div[1]/div/div[2]/article/footer/div/div[1]/div/div[3]|//*[@id="commonts_container"]/div/footer/div/div/div/div[3]/div/button/span[2]').text  ## 点赞
            except:
                likes = ''
            try:
                comments = web.find_element(By.XPATH, '//*[@id="app"]/div[1]/div[2]/div[2]/main/div[1]/div/div[2]/article/footer/div/div[1]/div/div[2]|//*[@id="app"]/div[1]/div[2]/div[2]/main/div[1]/div/div[2]/article/footer/div/div[1]/div/div[2]').text  ## 评论
            except:
                comments = ''
            try:
                shares = web.find_element(By.XPATH, '//*[@id="app"]/div[1]/div[2]/div[2]/main/div[1]/div/div[2]/article/footer/div/div[1]/div/div[1]|//*[@id="commonts_container"]/div/footer/div/div/div/div[1]/div/div/span').text  ## 分享/转发
            except:
                shares = ''
            collects = ''  ## 收藏
            plays = ''  ## 播放
            if (likes == '赞') or (likes == '0'):
                likes = ''
            if (comments == '评论') or (comments == '0'):
                comments = ''
            if (shares == '转发') or (shares == '0'):
                shares = ''
            return likes, comments, collects, shares, plays

        elif current_url.find("ixigua.com") > -1:    ## 西瓜视频 PC版本已经合并到抖音里（不存在pc版了），互动数只有播放数
            likes = ''  ## 点赞
            comments = ''  ## 评论
            collects = ''  ## 收藏
            shares = ''  ## 分享/转发
            try:
                plays = web.find_element(By.XPATH, '//*[@class="xigua-timetag-item xigua-timetag-item--circle"]').text.replace('次播放','')  ## 播放
                # print(22, plays)
            except:
                plays = ''
            if plays == '0':
                plays = ''
            return likes, comments, collects, shares, plays

        elif current_url.find("haokan.baidu.com") > -1:     ## https://haokan.baidu.com/v?vid=4543273714238499923
            if platform.system() == 'Windows':
                timeout = getattr(
                    getattr(OPT_THREAD_STATE, 'config', None), 'element_timeout', 6.0
                )
                likes = opt_wait_element_text(
                    web, By.CSS_SELECTOR, '.extrainfo-zan', timeout, {'0', '点赞', '首赞'}
                )
                comments = opt_wait_element_text(
                    web, By.CSS_SELECTOR, '.extrainfo-comments', timeout, {'0', '评论'}
                )
                plays = opt_wait_element_text(
                    web, By.CSS_SELECTOR, '.extrainfo-playnums', timeout
                ).split('次播放')[0].strip()
            else:
                try:
                    likes = web.find_element(By.XPATH, '//*[@id="pageScrollContainer"]/div[1]/div/div[1]/div[2]/div/div[3]').text
                except Exception:
                    likes = ''
                try:
                    comments = web.find_element(By.XPATH, '//*[@id="pageScrollContainer"]/div[1]/div/div[1]/div[2]/div/div[2]').text
                except Exception:
                    comments = ''
                try:
                    plays = web.find_element(By.XPATH, '//*[@class="extrainfo-playnums"]').text.split('次播放')[0]
                except Exception:
                    plays = ''
            collects = ''  ## 收藏
            shares = ''
            if (likes == '首赞') or (likes == '点赞') or (likes == '0'):
                likes = ''
            if (comments == '评论') or (comments == '0'):
                comments = ''
            if (collects == '收藏') or (collects == '0'):
                collects = ''
            if (shares == '分享') or (shares == '0'):
                shares = ''
            if plays == '0':
                plays = ''
            return likes, comments, collects, shares, plays

        elif current_url.find("163.com") > -1:
            jump_url = web.current_url
            if jump_url.find("dy/article") > -1:
                likes = ''  ## 点赞
                comments = web.find_element(By.XPATH, '//*[@id="content"]/div[1]/div[1]/a[2]').text  ## 评论
                collects = ''  ## 收藏
                shares = ''  ## 分享/转发
                plays = ''  ## 播放
            elif jump_url.find("c.m.163.com/news/a") > -1:
                if platform.system() == 'Windows':
                    timeout = getattr(
                        getattr(OPT_THREAD_STATE, 'config', None), 'element_timeout', 6.0
                    )
                    likes = opt_wait_element_text(
                        web, By.CSS_SELECTOR, '.action-like .s-text', timeout,
                        {'0', '赞'},
                    ).replace('赞', '')
                    comments = opt_wait_element_text(
                        web, By.CSS_SELECTOR, '.commentBar .count', timeout,
                        {'0', '评论'},
                    )
                else:
                    likes = web.find_element(By.XPATH, '//*[@id="app"]/div/div[2]/div/div[1]/div[2]/div[2]').text.replace('赞', '')  ## 点赞
                    comments = web.find_element(By.XPATH, '//*[@class="left"]/p').text  ## 评论
                collects = ''  ## 收藏
                shares = ''  ## 分享/转发
                plays = ''  ## 播放c.m.163.com/news
            elif jump_url.find("c.m.163.com/news/rec") > -1:
                likes = ''  ## 点赞
                comments = web.find_element(By.XPATH, '//*[@class="footer"]/p[3]').text  ## 评论
                collects = ''  ## 收藏
                shares = ''  ## 分享/转发
                plays = ''  ## 播放c.m.163.com/news
            elif jump_url.find("m.163.com/news/article") > -1:
                likes = ''  ## 点赞
                comments = web.find_element(By.XPATH, '/html/body/main/article/header/section/aside/a/span').text  ## 评论
                collects = ''  ## 收藏
                shares = ''  ## 分享/转发
                plays = ''  ## 播放c.m.163.com/news
            elif (jump_url.find("v.163.com") > -1) or (jump_url.find("www.163.com/v/video") > -1):
                likes = ''  ## 点赞
                comments = web.find_element(By.XPATH, '//*[@class="post_top_tie"]').text  ## 评论
                collects = ''  ## 收藏
                shares = ''  ## 分享/转发
                plays = ''  ## 播放c.m.163.com/news
            else:
                likes = ''  ## 点赞
                comments = ''  ## 评论
                collects = ''  ## 收藏
                shares = ''  ## 分享/转发
                plays = ''  ## 播放c.m.163.com/news
            if (likes == '首赞') or (likes == '点赞') or (likes == '0'):
                likes = ''
            if (comments == '评论') or (comments == '0'):
                comments = ''
            if (collects == '收藏') or (collects == '0'):
                collects = ''
            if (shares == '分享') or (shares == '0'):
                shares = ''
            if plays == '0':
                plays = ''
            return likes, comments, collects, shares, plays

        elif current_url.find("yoojia.com") > -1:                ## https://www.yoojia.com/article/9688334622013398222.html、https://www.yoojia.com/video/4278804346076627019.html
            try:
                likes = web.find_element(By.XPATH, '//*[@class="point-zan"]/span|//*[@id="app"]/section/main/div/div[1]/div/div[2]/div[3]/span/span|//*[@class="comment-msg"]/div[2]').text  ## 点赞   视频点赞准，文章点赞源码显示为0，跟页面显示不一致
            except:
                likes = ''
            try:
                comments = web.find_element(By.XPATH, '//*[@id="app"]/section/main/div/article/div[1]/div[2]/h2/span|//*[@id="app"]/section/main/div/div[1]/div/div[3]/h2/span').text.replace('（','').replace('）','')  ## 评论
            except:
                comments = ''
            collects = ''  ## 收藏
            shares = ''  ## 分享/转发
            plays = ''  ## 播放
            if (likes == '首赞') or (likes == '点赞') or (likes == '0'):
                likes = ''
            if (comments == '评论') or (comments == '0'):
                comments = ''
            return likes, comments, collects, shares, plays

        elif (current_url.find("uczzd.cn") > -1) or (current_url.find("mp.uc.cn") > -1):   # 目前互动数没有      https://m.uczzd.cn/ucnews/news?aid=5392058188236442797
            likes = ''  ## 点赞
            comments = ''  ## 评论
            collects = ''  ## 收藏
            shares = ''  ## 分享/转发
            plays = ''  ## 播放
            return likes, comments, collects, shares, plays

        # elif current_url.find("ishare.ifeng.com/") > -1:  # http://ishare.ifeng.com/c/s/v006iNtWf2WUJSB7FM6gaIpjZQBbX8--6w46QcobUGu2jegTeTDwjNSPf88fXvDvSNZv0
        elif current_url.find("ifeng.com/") > -1:  # https://finance.ifeng.com/c/8ovOXjF1Jbt
            try:
                likes = web.find_element(By.XPATH, '//*[@class="index_vote_OHWb9"]/span|//*[@id="js_supportCount"]').text  ## 点赞   视频点赞准，文章点赞源码显示为0，跟页面显示不一致
            except:
                likes = ''
            try:
                comments = web.find_element(By.XPATH, '//*[@class="index_count_Ahc5j"][1]/a/span|//*[@class="index_commentNum_Ow-Ts"]/span|//*[@id="js_ping"]').text  ## 评论
            except:
                comments = ''
            collects = ''  ## 收藏
            shares = ''  ## 分享/转发
            try:
                plays = web.find_element(By.XPATH, '//*[@id="root"]/section/section[1]/div[1]/div[2]/div[2]').text.replace('阅读','')  ## 播放
            except:
                plays = ''
            if (likes == '首赞') or (likes == '点赞') or (likes == '0'):
                likes = ''
            if (comments == '评论') or (comments == '0'):
                comments = ''
            if plays == '0':
                plays = ''
            return likes, comments, collects, shares, plays

        elif current_url.find("3g.k.sohu.com/h5apps/t/") > -1:  # 因为这个搜狐链接不能通过web.title方法判断链接是否正常，所以单独拿出来判断     http://3g.k.sohu.com/h5apps/t/feed?action=307&uid=1604507970-6843825581097138949-U&type=1&currentPage=1&pageSize=20&cursorId=0&snstype=1
            try:
                likes = web.find_element(By.XPATH, '//*[@class="praise"]/i').text  ## 点赞
            except:
                likes = ''
            try:
                comments = web.find_element(By.XPATH, '//*[@class="comment"]/i').text  ## 评论
            except:
                comments = ''
            try:
                shares = web.find_element(By.XPATH, '//*[@class="forward selected"]/i').text  ## 分享/转发
            except:
                shares = ''
            collects = ''  ## 收藏
            plays = ''  ## 播放
            if (likes == '首赞') or (likes == '点赞') or (likes == '0'):
                likes = ''
            if (comments == '评论') or (comments == '0'):
                comments = ''
            if (shares == '分享') or (shares == '0'):
                shares = ''
            return likes, comments, collects, shares, plays

        elif current_url.find("sohu.com") > -1:  # https://www.sohu.com/a/963883619_114988
            try:
                likes = web.find_element(By.XPATH, '//*[@id="shareInteraction"]/div/div[1]/div/div[2]|//*[@id="mySwiper"]/div/div[2]/div/div[2]/div[2]|//*[@class="interact-horizon"]/div/div/div[2]').text  ## 点赞
            except:
                likes = ''
            try:
                comments = web.find_element(By.XPATH,'//*[@id="leftComment"]/div[2]|//*[@id="interaction"]/div[1]/div|//*[@id="interaction"]/div[1]/div/span|//*[@id="mySwiper"]/div/div[2]/div/div[2]/div[3]|//*[@class="interact-horizon"]/div[2]/div[2]').text.replace('评论 ','')  ## 评论
            except:
                comments = ''
            try:
                collects = web.find_element(By.XPATH, '//*[@id="shareInteraction"]/div/div[3]/div[2]|//*[@id="mySwiper"]/div/div[2]/div/div[2]/div[4]|//*[@class="interact-horizon"]/div[3]/div[2]').text  ## 收藏
            except:
                collects = ''
            shares = ''  ## 分享/转发
            try:
                plays = web.find_element(By.XPATH, '//*[@class="read-num"]/em|//*[@class="content-main-desc--see"]/span[2]|//*[@id="readNum"]').text.replace('阅读','')  ## 阅读/播放
            except:
                plays = ''
            if (likes == '首赞') or (likes == '点赞') or (likes == '0'):
                likes = ''
            if (comments == '评论') or (comments == '0'):
                comments = ''
            if (collects == '收藏') or (collects == '0'):
                collects = ''
            if (shares == '分享') or (shares == '0'):
                shares = ''
            if plays == '0':
                plays = ''
            return likes, comments, collects, shares, plays

        elif current_url.find("www.360kuai.com") > -1:  # 快资讯： https://www.360kuai.com/9ca8c1d1b4eba540a?d5bf6b48de6a1a232e012c47272b5717
            try:
                likes = web.find_element(By.XPATH, '//*[@class="article-toolbar__item zan"]|//*[@class="short-video__side--like"]').text  ## 点赞
            except:
                likes = ''
            try:
                comments = web.find_element(By.XPATH, '//*[@class="article-toolbar__item comment"]|//*[@class="short-video__side--comment"]').text  ## 评论
            except:
                comments = ''
            try:
                collects = web.find_element(By.XPATH, '//*[@class="article-toolbar__item collect"]|//*[@class="short-video__side--favor"]').text  ## 收藏
            except:
                collects = ''
            if (likes == '点赞') or (likes == '0'):
                likes = ''
            if (comments == '评论') or (comments == '0'):
                comments = ''
            if (collects == '收藏') or (collects == '0'):
                collects = ''
            shares = ''  ## 分享/转发
            plays = ''  ## 播放
            return likes, comments, collects, shares, plays

        elif current_url.find("dongchedi.com") > -1:   # 懂车帝 https://www.dongchedi.com/article/7292053577869197875    https://www.dongchedi.com/article/7567948882954207795
            try:
                likes = web.find_element(By.XPATH, '//*[@id="__next"]/div[1]/div[2]/div/div/div/main/section/div[1]/article/div[3]/div/div/div[2]/div[2]|//*[@class="tw-flex tw-items-center"]/div[2]').text.replace('赞同','')  ## 点赞
            except:
                likes = ''
            try:
                comments = web.find_element(By.XPATH, '//*[@id="__next"]/div[1]/div[2]/div/div/div/main/section/div[1]/article/div[3]/div/div/div[2]/div[1]|//*[@class="tw-flex tw-items-center"]/div[1]').text.replace('评论','')  ## 评论
            except:
                comments = ''
            if (likes == '点赞') or (likes == '0'):
                likes = ''
            if (comments == '评论') or (comments == '0'):
                comments = ''
            collects = ''  ## 收藏
            shares = ''  ## 分享/转发
            plays = ''  ## 阅读  目前阅读量进行了加密，后面抽时间处理下
            return likes, comments, collects, shares, plays

        elif current_url.find("news.qq.com") > -1:   # https://news.qq.com/rain/a/20250920A03AF000
            text = web.page_source
            likes = web.find_element(By.XPATH, '//*[@id="left-tool"]/div/div/div/div[2]/p|//*[@id="videodc-meta-content"]/div/div[2]/div/div[1]/span').text  ## 点赞
            comments = web.find_element(By.XPATH, '//*[@id="left-tool"]/div/div/div/div[3]/p|//*[@id="videodc-meta-content"]/div/div[2]/div/div[2]/span').text  ## 评论
            collects = web.find_element(By.XPATH, '//*[@id="left-tool"]/div/div/div/div[4]/p|//*[@id="videodc-meta-content"]/div/div[2]/div/div[3]/span').text  ## 收藏
            try:
                shares = re.findall(r'(?<=class="text-count">).*?(?=</span>)', text)[3]
            except:
                shares = web.find_element(By.XPATH, '//*[@id="left-tool"]/div/div/div/div[5]/p|//*[@id="videodc-meta-content"]/div/div[2]/div/div[4]/span').text  ## 分享/转发
            try:
                plays = web.find_element(By.XPATH, '//*[@class="meta-info"]/span[4]').text.replace(' 观看','')  ## 阅读  目前阅读量进行了加密，后面抽时间处理下
            except:
                plays = ''
            if (likes == '点赞') or (likes == '0'):
                likes = ''
            if (comments == '评论') or (comments == '0'):
                comments = ''
            if (collects == '收藏') or (collects == '0'):
                collects = ''
            if (shares == '分享') or (shares == '0'):
                shares = ''
            return likes, comments, collects, shares, plays

        elif (current_url.find("sina.com") > -1) or (current_url.find("sina.cn") > -1):   # https://k.sina.com.cn/article_1893761531_m70e081fb02002wyys.html
            try:
                likes = web.find_element(By.XPATH, '//*[@id="app"]/div[1]/div/div[1]/div[2]/b|//*[@class="vote new_vote "]').text  ## 点赞
            except:
                likes = ''
            try:
                comments = web.find_element(By.XPATH, '//*[@id="app"]/div[1]/div/div[1]/div[3]/b|//*[@id="cmnt_module"]/div[1]/div/h2/b[2]|//*[@class="fl_fun fr "]|//*[@id="bottom_sina_comment"]/div[1]/div[1]/span[1]/em[1]/a|//*[@class="discuss_tit_num"]|//*[@class="new_msg"]').text  ## 评论
            except:
                comments = ''
            try:
                collects = ''  ## 收藏
            except:
                collects = ''
            try:
                shares = web.find_element(By.XPATH, '//*[@class="reply new_reply"]').text  ## 分享/转发
            except:
                shares = ''
            plays = ''  ## 阅读  目前阅读量进行了加密，后面抽时间处理下
            if (likes == '点赞') or (likes == '0'):
                likes = ''
            if (comments == '评论') or (comments == '0'):
                comments = ''
            if (collects == '收藏') or (collects == '0'):
                collects = ''
            if (shares == '分享') or (shares == '0'):
                shares = ''
            return likes, comments, collects, shares, plays

        elif current_url.find("bilibili.com") > -1 and platform.system() == 'Windows':
            metrics = opt_extract_bilibili_metrics(current_url)
            return metrics or ('', '', '', '', '')

        elif current_url.find("tieba.baidu.com") > -1:   ##贴吧链接在队列最后的时候，不要多出空行，不然会报错，因为涉及到验证码平台     https://tieba.baidu.com/p/10224368141   https://tieba.baidu.com/p/10091943009
            likes = ''  ## 点赞
            if platform.system() == 'Windows':
                content = web.execute_script(
                    'return document.body ? document.body.innerText : "";'
                ) or ''
                match = re.search(r'([\d,]+)\s*回复贴', content)
                if not match:
                    match = re.search(r'全部回复\s*[（(]([\d,]+)[）)]', content)
                if match:
                    comments = match.group(1).replace(',', '')
                else:
                    # PageData.thread.reply_num 包含首帖，互动回复数需减去 1。
                    match = re.search(
                        r'reply_num["\']?\s*[:=]\s*["\']?(\d+)', web.page_source
                    )
                    comments = str(max(int(match.group(1)) - 1, 0)) if match else ''
            else:
                comments = web.find_element(By.XPATH, '//*[@id="thread_theme_5"]/div[1]/ul/li[2]/span[1]').text  ## 评论
                print(555,comments)
            collects = ''  ## 收藏
            shares = ''  ## 分享/转发
            plays = ''  ## 播放
            return likes, comments, collects, shares, plays

        else:
            print('获取互动数时，链接不在规则内')
            likes = ''
            comments = ''
            collects = ''
            shares = ''
            plays = ''
            return likes, comments, collects, shares, plays

    except WebDriverException:
        raise
    except Exception as e:
        # print(f'异常错误: {e}' )
        likes = ''
        comments = ''
        collects = ''
        shares = ''
        plays = ''
        # print(222, f'{current_url}:', likes, comments, collects, shares, plays)
        return likes, comments, collects, shares, plays


def save():
    # with open('url.csv', 'w', newline='') as file:
    #     writer = csv.writer(file)
    #     writer.writerows(url_lists)
    wb = Workbook()
    ws = wb.active
    ws.title = "结果"
    # 写入表头（从字典的key中提取）
    # print(1234567, url_lists)
    headers = list(url_lists[0].keys())
    ws.append(headers)

    # 写入数据行
    for item in url_lists:
        ws.append(list(item.values()))

    current_time = time.strftime('%Y-%m-%d__%H：%M', time.localtime())  ## 获取当前时间，2025-12-17 18:08
    wb.save(f"链接判断结果_{current_time}.xlsx")
    print('完成！')


## 抖音源码获取
# def douyin_page(current_url, os_name, num=None):
def douyin_page(current_url, os_name):
    if os_name=='Windows':
    # if os_name=='mac':
        driver_path = 'chromedriver.exe'
    else:
        with open('chromedriver_path.txt', 'r', encoding='utf-8') as file:
            driver_path = file.readlines()[0]  ## 获取mac系统里的 驱动链接（目前看要从根目录开始）
            # judge_nedds = set_lists[0].split(':')[1].strip('\n')
        # driver_path =
    service = Service(driver_path)
    opt = Options()
    opt.add_argument("--headless")  # 设置为无头模式
    opt.add_argument("--disable-gpu")  # 禁用GPU加速
    if os_name=='Windows':
        opt.add_argument(f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')   ## 不带请求头有时候头条的源码会有问题，导致解析有问题
    else:
        opt.add_argument(f'User-Agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36')  ## 不带请求头有时候头条的源码会有问题，导致解析有问题
    # 创建浏览器对象
    # web = Chrome(service=service, options=opt)
    web = webdriver.Chrome(service=service, options=opt)
    web.get(current_url)
    wait = WebDriverWait(web, 20)  ## 最长等待时间设置15秒
    wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    time.sleep(2)
    # 此时获取的 page_source 包含了动态加载的内容
    html_source = web.page_source
    # nu = 1
    # with open(f'{num}{nu}.txt', 'w', encoding='utf-8') as file:
    #     file.writelines(web.page_source)
    # nu += 1
    return web, html_source


def hong_page(current_url, os_name):
    if os_name=='Windows':
    # if os_name=='mac':
        driver_path = 'chromedriver.exe'
    else:
        with open('chromedriver_path.txt', 'r', encoding='utf-8') as file:
            driver_path = file.readlines()[0]  ## 获取mac系统里的 驱动链接（目前看要从根目录开始）
            # judge_nedds = set_lists[0].split(':')[1].strip('\n')
        # driver_path =
    service = Service(driver_path)
    opt = Options()
    opt.add_argument("--headless")  # 设置为无头模式
    opt.add_argument("--disable-gpu")  # 禁用GPU加速
    if os_name=='Windows':
        opt.add_argument(f'user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36')   ## 不带请求头有时候头条的源码会有问题，导致解析有问题
    else:
        opt.add_argument(f'User-Agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36')  ## 不带请求头有时候头条的源码会有问题，导致解析有问题
    # 创建浏览器对象
    # web = Chrome(service=service, options=opt)
    web = webdriver.Chrome(service=service, options=opt)
    web.get(current_url)
    # wait = WebDriverWait(web, 20)  ## 小红书不用等待，因为网页出现一瞬间就有登录页面出现，不然获取不到源码
    # wait.until(EC.presence_of_element_located((By.TAG_NAME, "body")))
    # time.sleep(2)
    # 此时获取的 page_source 包含了动态加载的内容
    html_source = web.page_source

    return web, html_source







# ==================== 优化版批量入口 ====================
# 原有解析函数保留在上方；下面的入口只替换浏览器生命周期、等待和调度方式。
OPT_BASE_DIR = Path(__file__).resolve().parent
OPT_RESULT_HEADERS = ('链接', '链接状态', '点赞', '评论/回复', '收藏', '分享/转发', '播放/阅读')
OPT_SUPPORTED_MARKERS = (
    'douyin.com', 'baidu.com', 'www.toutiao.com', 'kuaishou.com',
    'weibo.com', 'ixigua.com', 'haokan.baidu.com', '163.com', 'yoojia.com',
    'uczzd.cn', 'mp.uc.cn', 'ifeng.com', 'sohu.com', '360kuai.com',
    'myzaker.com', 'yidianzixun.com', 'mp.weixin.qq', 'html2.qktoutiao.com',
    'tieba.baidu.com', 'bilibili.com', 'dongchedi.com', 'news.qq.com',
    'sina.com', 'sina.cn', 'iqiyi.com', 'xiaohongshu.com',
)
OPT_MAX_TOTAL_WORKERS = 4
OPT_CHECKPOINT_VERSION = 4
OPT_DOUYIN_VALID_XPATH = (
    '//*[@id="douyin-right-container"]/div[2]/p[1]|'
    '//*[@id="douyin-right-container"]/div[2]/div/div/p[1]'
)
if platform.system() == 'Windows':
    OPT_DOUYIN_METRIC_XPATHS = (
        '//*[@data-e2e="video-player-digg"]|//*[@id="douyin-right-container"]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[1]/div[1]/span',
        '//*[@data-e2e="feed-comment-icon"]|//*[@id="douyin-right-container"]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[1]/div[2]/span',
        '//*[@data-e2e="video-player-collect"]|//*[@id="douyin-right-container"]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[1]/div[3]/span',
        '//*[@data-e2e="video-player-share"]|//*[@id="douyin-right-container"]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[1]/div[4]/span',
    )
else:
    OPT_DOUYIN_METRIC_XPATHS = (
        '//*[@id="douyin-right-container"]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[1]/div[1]/span',
        '//*[@id="douyin-right-container"]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[1]/div[2]/span',
        '//*[@id="douyin-right-container"]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[1]/div[3]/span',
        '//*[@id="douyin-right-container"]/div[2]/div/div/div[1]/div[3]/div/div[2]/div[1]/div[4]/span',
    )
OPT_DOUYIN_DELETED_MARKERS = (
    '你要观看的图文不存在',
    '你要观看的视频不存在',
    '作品不存在',
    '内容不存在',
    '作品已删除',
    '视频已删除',
)
OPT_THREAD_STATE = threading.local()
OPT_STOP_EVENT = threading.Event()
OPT_LOG_LOCK = threading.Lock()
OPT_DRIVER_ASSETS_LOCK = threading.Lock()
OPT_DRIVER_ASSETS = None
OPT_DRIVER_RESOLUTION_ERROR = None
OPT_SESSION_RECOVERY_PAUSE = 8.0
OPT_DOUYIN_ERROR_PAUSE = (6.0, 10.0)
OPT_DOUYIN_MAX_CONSECUTIVE_ERRORS = 3
OPT_TOUTIAO_ERROR_PAUSE = (4.0, 8.0)
OPT_TOUTIAO_MAX_CONSECUTIVE_NETWORK_ERRORS = 3
OPT_SELENIUM_MANAGER_TIMEOUT = 12
OPT_SESSION_ERROR_MARKERS = (
    'invalid session id',
    'session deleted',
    'chrome not reachable',
    'not connected to devtools',
    'disconnected: not connected',
    'tab crashed',
    'target window already closed',
    'unable to receive message from renderer',
)
OPT_NETWORK_ERROR_MARKERS = (
    'net::err_connection_reset',
    'net::err_connection_closed',
    'net::err_connection_aborted',
    'net::err_connection_timed_out',
    'net::err_timed_out',
    'net::err_network_changed',
    'net::err_internet_disconnected',
    'net::err_proxy_connection_failed',
    'net::err_tunnel_connection_failed',
    'net::err_name_not_resolved',
)


@dataclass(frozen=True)
class OptimizedConfig:
    page_timeout: float = 20.0
    element_timeout: float = 6.0
    douyin_retries: int = 3
    checkpoint_every: int = 50
    progress_every: int = 10
    toutiao_workers: int = 2
    douyin_workers: int = 1
    other_workers: int = 1


@dataclass(frozen=True)
class OptDriverAssets:
    driver_path: str
    browser_path: str = ''
    browser_major: str = ''


# 同域请求之间保留很短的随机间隔，避免多个浏览器形成突发请求。
OPT_COOLDOWNS = {
    'toutiao': (0.25, 0.60),
    # 抖音仍保持单 worker；缩短正常间隔，异常时单独退避。
    'douyin': (1.50, 3.00),
    'kuaishou': (0.80, 1.50),
    'other': (0.30, 0.80),
}
OPT_PARSER_VERSION = '0.5.2-macos-r2-ui1'
OPT_TIEBA_PARSER_VERSION = 1
OPT_TOUTIAO_PARSER_VERSION = 1
OPT_RETRYABLE_STATUSES = {'处理失败', '访问受限', '需验证'}
OPT_HTTP_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) '
        'AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36'
    ),
    'Accept': 'application/json, text/plain, */*',
}


def opt_contains_any(value, markers):
    value = value or ''
    return any(marker in value for marker in markers)


def opt_page_text(driver):
    try:
        return driver.execute_script(
            'return document.body ? document.body.innerText : "";'
        ) or ''
    except (NoSuchElementException, StaleElementReferenceException):
        return ''
    except WebDriverException:
        raise


def opt_page_searchable(driver):
    return f'{driver.title or ""}\n{opt_page_text(driver)}'


def opt_metric_value(value):
    value = html.unescape(str(value if value is not None else ''))
    value = re.sub(r'<[^>]+>', ' ', value)
    value = ' '.join(value.split()).replace(',', '')
    if value in {
        '', '赞', '点赞', '首赞', '评论', '抢首评', '收藏', '分享',
        '转发', '播放', '阅读', '--', '-',
    }:
        return ''
    match = re.search(r'\d+(?:\.\d+)?(?:万|亿)?', value)
    return match.group(0) if match else ''


def opt_first_match(value, patterns):
    for pattern in patterns:
        match = re.search(pattern, value or '', flags=re.IGNORECASE | re.DOTALL)
        if match:
            cleaned = opt_metric_value(match.group(1))
            if cleaned:
                return cleaned
    return ''


def opt_first_element_text(driver, by, selectors):
    for selector in selectors:
        try:
            for element in driver.find_elements(by, selector):
                value = opt_metric_value(element.text)
                if value:
                    return value
        except (NoSuchElementException, StaleElementReferenceException):
            continue
        except WebDriverException:
            raise
    return ''


def opt_extract_baidu_metrics(source, page_text):
    likes = opt_first_match(source, (
        r'"like"\s*:\s*\{[^{}]{0,240}?"count"\s*:\s*"([^"]+)"',
        r'"likeCount"\s*:\s*"?([\d.万亿]+)',
    ))
    comments = opt_first_match(page_text, (
        r'评论列表\s*[（(]\s*([\d.万亿]+)\s*条\s*[)）]',
        r'全部评论\s*[（(]\s*([\d.万亿]+)\s*[)）]',
    ))
    plays = opt_first_match(source, (
        r'"playCount"\s*:\s*"([^"]+)"',
        r'"play_count"\s*:\s*"?([\d.万亿]+)',
    )) or opt_first_match(page_text, (r'([\d.万亿]+)\s*次播放',))
    return likes, comments, '', '', plays


def opt_extract_netease_metrics(source, page_text):
    likes = opt_first_match(source, (
        r'class="s-text"[^>]*>\s*([\d.万亿]+)\s*赞\s*<',
        r'class="action-like".{0,500}?([\d.万亿]+)\s*赞',
    )) or opt_first_match(page_text, (r'(?:分享\s*)?([\d.万亿]+)\s*赞',))
    comments = opt_first_match(source, (
        r'class="commentBar".{0,2500}?<p class="count"[^>]*>\s*([^<]+)\s*</p>',
    )) or opt_first_match(page_text, (r'有\s*([\d.万亿]+)\s*人参与',))
    return likes, comments, '', '', ''


def opt_extract_weibo_metrics(source):
    likes = opt_first_match(source, (
        r'<span class="woo-like-count"[^>]*>\s*([^<]+)\s*</span>',
        r'"attitudes_count"\s*:\s*"?([\d.万亿]+)',
    ))
    comments = opt_first_match(source, (
        r'title="评论".{0,700}?<span class="[^"]*_num_[^"]*"[^>]*>'
        r'(?:<!---->)?\s*([^<]+)</span>',
        r'"comments_count"\s*:\s*"?([\d.万亿]+)',
    ))
    shares = opt_first_match(source, (
        r'title="转发".{0,700}?<span class="[^"]*_num_[^"]*"[^>]*>'
        r'(?:<!---->)?\s*([^<]+)</span>',
        r'"reposts_count"\s*:\s*"?([\d.万亿]+)',
    ))
    return likes, comments, '', shares, ''


class TiebaToolbarParser(HTMLParser):
    """Read the first post's labelled toolbar, never reply/advertisement counts."""
    ICONS = {'agree_pb': 'likes', 'comment_pb': 'comments',
             'collect': 'collects', 'share_pb': 'shares'}
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input',
            'link', 'meta', 'param', 'source', 'track', 'wbr'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.scope = None
        self.action = None
        self.number = None
        self.icon = ''
        self.parts = []
        self.metrics = {}
        self.has_toolbar = False
        self.has_legacy_post = False

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        classes = set(attrs.get('class', '').split())
        if tag in self.VOID:
            return
        self.stack.append(tag)
        depth = len(self.stack)
        if 'd_post_content' in classes or 'j_d_post_content' in classes:
            self.has_legacy_post = True
        if 'pc-pb-first-floor-interactive' in classes:
            self.scope = depth
        if self.scope and 'action-item' in classes:
            self.action, self.icon, self.parts = depth, '', []
        if self.action and tag == 'use':
            self.icon = (attrs.get('href') or attrs.get('xlink:href') or '').rsplit('#', 1)[-1]
            if self.icon in self.ICONS:
                self.has_toolbar = True
        if self.action and 'action-number' in classes:
            self.number = depth

    def handle_data(self, data):
        if self.action and self.number:
            self.parts.append(data)

    def handle_endtag(self, tag):
        match = next((i for i in range(len(self.stack) - 1, -1, -1) if self.stack[i] == tag), None)
        if match is None:
            return
        depth = match + 1
        if self.number and depth <= self.number:
            self.number = None
        if self.action and depth <= self.action:
            key = self.ICONS.get(self.icon)
            value = opt_metric_value(''.join(self.parts))
            if key and value:
                self.metrics.setdefault(key, value)
            self.action = None
        if self.scope and depth <= self.scope:
            self.scope = None
        del self.stack[match:]


def opt_tieba_document(source):
    parser = TiebaToolbarParser()
    parser.feed(source or '')
    return parser


def opt_extract_tieba_metrics(source, page_text):
    toolbar = opt_tieba_document(source).metrics
    comments = toolbar.get('comments') or opt_first_match(f'{page_text}\n{source}', (
        r'全部回复\s*[（(]\s*([\d.万亿]+)\s*[)）]',
        r'([\d,]+)\s*回复贴',
        r'"reply_num"\s*:\s*"?([\d.万亿]+)',
    ))
    return toolbar.get('likes', ''), comments, toolbar.get('collects', ''), toolbar.get('shares', ''), ''


def opt_tieba_status(title, page_text, source):
    document = opt_tieba_document(source)
    # A phrase quoted in a real post is not a verification interstitial.
    if document.has_toolbar or document.has_legacy_post:
        return '正常'
    title = (title or '').strip()
    if title == '百度安全验证' or '请完成下方验证后继续操作' in page_text:
        return '需验证'
    if '贴吧404' in title or opt_contains_any(page_text, ('该贴已被删除', '该帖已被删除')):
        return '已删除'
    return '访问受限'


def opt_fetch_bilibili_metrics(current_url):
    match = re.search(r'(BV[0-9A-Za-z]+)', current_url or '', flags=re.IGNORECASE)
    if not match:
        return None
    try:
        response = requests.get(
            'https://api.bilibili.com/x/web-interface/view',
            params={'bvid': match.group(1)},
            headers={**OPT_HTTP_HEADERS, 'Referer': current_url},
            timeout=6,
        )
        response.raise_for_status()
        payload = response.json()
        if payload.get('code') != 0:
            return None
        stat = (payload.get('data') or {}).get('stat') or {}
        metrics = tuple(opt_metric_value(stat.get(key)) for key in (
            'like', 'reply', 'favorite', 'share', 'view'
        ))
        return metrics if any(metrics) else None
    except (requests.RequestException, ValueError, TypeError):
        return None


def opt_extract_bilibili_dom_metrics(driver):
    likes = opt_first_element_text(driver, By.CSS_SELECTOR, ('.video-like-info',))
    comments = opt_first_element_text(driver, By.CSS_SELECTOR, (
        '.reply-header .total-reply', '.reply-header .reply-count',
    ))
    collects = opt_first_element_text(driver, By.CSS_SELECTOR, ('.video-fav-info',))
    shares = opt_first_element_text(driver, By.CSS_SELECTOR, (
        '.video-share-info-text', '.video-share-info',
    ))
    plays = opt_first_element_text(driver, By.CSS_SELECTOR, ('.view-text',))
    return likes, comments, collects, shares, plays


def opt_extract_kuaishou_dom_metrics(driver):
    likes = opt_first_element_text(driver, By.CSS_SELECTOR, (
        '.like-item .item-count', '.like-item .item-text',
    )) or opt_first_match(driver.page_source, (
        r'class="interactive-item like-item".{0,600}?'
        r'class="item-text item-count"[^>]*>\s*([^<]+)\s*</span>',
    ))
    comments = ''
    page_text = opt_page_text(driver)
    if '已经到底了，没有更多评论了' in page_text:
        try:
            comments = opt_metric_value(
                len(driver.find_elements(By.CSS_SELECTOR, '.comment-list-item'))
            )
        except (NoSuchElementException, StaleElementReferenceException):
            comments = ''
        except WebDriverException:
            raise
    return likes, comments, '', '', ''


def opt_macos_url_status(current_url, driver):
    """Return a macOS-specific status, or None for platforms handled below."""
    lowered = (current_url or '').lower()
    searchable = opt_page_searchable(driver)

    if any(marker in lowered for marker in (
        'mbd.baidu.com', 'baijiahao.baidu.com', 'quanmin.baidu.com',
    )):
        return '已删除' if opt_contains_any(searchable, (
            '抱歉，你找的页面不见啦', '这里空空如也', '文章暂时找不到了',
            '内容不存在', '页面不存在',
        )) else '正常'
    if 'kuaishou.com' in lowered:
        if opt_contains_any(searchable, (
            '作品已失效', '您要访问的页面弄丢了', '该作品已删除', '内容已删除',
        )):
            return '已删除'
        if (driver.title or '').strip() == '短视频-快手' and not opt_page_text(driver).strip():
            return '访问受限'
        return '正常'
    if 'weibo.com' in lowered:
        return '已删除' if opt_contains_any(searchable, (
            '该微博不存在', '原文章已被删除', '暂无查看权限', '微博已被删除',
        )) else '正常'
    if 'haokan.baidu.com' in lowered:
        return '已删除' if '抱歉，您访问的视频不存在' in searchable else '正常'
    if '163.com' in lowered:
        return '已删除' if opt_contains_any(searchable, (
            '网易-404', '内容不存在或已被删除', '内容不存在或被删除',
            '网页跑丢了', '404!页面找不到了', '视频不存在或已被删除',
            '动态不存在或已被删除', '该内容无法查看',
        )) else '正常'
    if 'mp.weixin.qq' in lowered:
        if opt_contains_any(searchable, (
            '该内容已被发布者删除', '此内容被投诉且经审核涉嫌侵权，无法查看',
            '此账号已自主注销，内容无法查看',
        )):
            return '已删除'
        if (
            'wappoc_appmsgcaptcha' in (driver.current_url or '')
            or opt_contains_any(searchable, ('当前环境异常', '完成验证后即可继续访问'))
        ):
            return '需验证'
        return '正常'
    if 'tieba.baidu.com' in lowered:
        return opt_tieba_status(driver.title, opt_page_text(driver), driver.page_source)
    if 'bilibili.com' in lowered:
        return '已删除' if opt_contains_any(searchable, (
            '啊叻？视频不见了？', '视频不见了', '视频已失效', '稿件不可见',
        )) else '正常'
    if 'ifeng.com/' in lowered:
        landed = (driver.current_url or '').rstrip('/')
        if opt_contains_any(searchable, (
            '凤凰热榜', '对不起, 该网页随风而逝', '页面不存在', '内容已删除',
        )):
            return '已删除'
        if '/c/' in lowered and landed in (
            'https://finance.ifeng.com', 'http://finance.ifeng.com',
        ):
            return '已删除'
        return '正常'
    return None


def opt_macos_interactions(current_url, driver):
    """Return macOS parser metrics, or None for the original parser."""
    lowered = (current_url or '').lower()
    if any(marker in lowered for marker in (
        'mbd.baidu.com', 'baijiahao.baidu.com', 'quanmin.baidu.com',
    )):
        return opt_extract_baidu_metrics(driver.page_source, opt_page_text(driver))
    if '163.com' in lowered:
        return opt_extract_netease_metrics(driver.page_source, opt_page_text(driver))
    if 'weibo.com' in lowered:
        return opt_extract_weibo_metrics(driver.page_source)
    if 'bilibili.com' in lowered:
        return opt_fetch_bilibili_metrics(current_url) or opt_extract_bilibili_dom_metrics(driver)
    if 'kuaishou.com' in lowered:
        return opt_extract_kuaishou_dom_metrics(driver)
    if 'mp.weixin.qq' in lowered:
        return '', '', '', '', ''
    if 'tieba.baidu.com' in lowered:
        return opt_extract_tieba_metrics(driver.page_source, opt_page_text(driver))
    return None


def opt_result_row(url, status='', metrics=None):
    metrics = metrics or ('', '', '', '', '')
    row = dict(zip(OPT_RESULT_HEADERS, (url, status, *metrics)))
    if platform_name(url) == '百度贴吧':
        row['_tieba_parser_version'] = OPT_TIEBA_PARSER_VERSION
    if platform_name(url) == '今日头条':
        row['_toutiao_parser_version'] = OPT_TOUTIAO_PARSER_VERSION
    return row


def opt_read_settings(path):
    values = []
    for line in path.read_text(encoding='utf-8').splitlines():
        if ':' in line:
            values.append(line.rsplit(':', 1)[1].strip())
    if not values:
        raise ValueError(f'配置文件格式不完整：{path}')
    return values[0]


def opt_read_urls(path):
    return [line.strip() for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]


def opt_is_supported(url):
    return platform_name(url) != '不支持'


def opt_group(url):
    if not opt_is_supported(url):
        return 'unsupported'
    lowered = url.lower()
    if 'douyin.com' in lowered:
        return 'douyin'
    if 'toutiao.com' in lowered:
        return 'toutiao'
    if platform.system() != 'Windows' and 'kuaishou.com' in lowered:
        return 'kuaishou'
    if opt_is_supported(url):
        return 'other'
    return 'unsupported'


def opt_normalize_url(url):
    lowered = url.lower()
    if 'www.iesdouyin.com' in lowered and '?schema_type=37' not in lowered:
        return url.rstrip('/') + '/?schema_type=37'
    if 'www.douyin.com/video' in lowered:
        return url.replace(
            'www.douyin.com/video/', 'www.iesdouyin.com/share/video/'
        ) + '/?schema_type=37'
    if 'www.myzaker.com/article/' in lowered:
        part_url = url.replace('http://www.myzaker.com/article/', '').replace(
            'https://www.myzaker.com/article/', ''
        )
        return 'http://app.myzaker.com/news/article.php?pk=' + part_url
    return url


def opt_driver_path(os_name):
    if os_name == 'Windows':
        return str(OPT_BASE_DIR / 'chromedriver.exe')
    path = Path(
        (OPT_BASE_DIR / 'chromedriver_path.txt').read_text(encoding='utf-8').splitlines()[0].strip()
    )
    return str(path if path.is_absolute() else OPT_BASE_DIR / path)


def opt_find_browser():
    system = platform.system()
    if system == 'Windows':
        local_app_data = Path(os.environ.get('LOCALAPPDATA', Path.home() / 'AppData' / 'Local'))
        program_files = Path(os.environ.get('PROGRAMFILES', 'C:/Program Files'))
        program_files_x86 = Path(os.environ.get('PROGRAMFILES(X86)', 'C:/Program Files (x86)'))
        candidates = (
            program_files / 'Google/Chrome/Application/chrome.exe',
            program_files_x86 / 'Google/Chrome/Application/chrome.exe',
            local_app_data / 'Google/Chrome/Application/chrome.exe',
            local_app_data / 'Google/Chrome for Testing/Application/chrome.exe',
            program_files / 'Chromium/Application/chrome.exe',
        )
    elif system == 'Darwin':
        candidates = (
            Path('/Applications/Google Chrome.app/Contents/MacOS/Google Chrome'),
            Path.home() / 'Applications/Google Chrome.app/Contents/MacOS/Google Chrome',
            Path('/Applications/Google Chrome for Testing.app/Contents/MacOS/Google Chrome for Testing'),
            Path('/Applications/Chromium.app/Contents/MacOS/Chromium'),
        )
    else:
        candidates = (
            Path('/usr/bin/google-chrome'),
            Path('/usr/bin/google-chrome-stable'),
            Path('/usr/bin/chromium'),
            Path('/usr/bin/chromium-browser'),
        )
    for candidate in candidates:
        if candidate.is_file():
            return candidate
    return None


def opt_selenium_cache_path():
    configured = os.environ.get('SE_CACHE_PATH')
    return Path(configured).expanduser() if configured else OPT_BASE_DIR / 'selenium-cache'


def opt_detect_proxy():
    """Return the concrete HTTP proxy Selenium Manager should use, if any."""
    try:
        proxies = {
            str(key).lower(): str(value).strip()
            for key, value in getproxies().items()
            if value
        }
    except Exception:
        return ''
    for key in ('https', 'all', 'http'):
        proxy = proxies.get(key, '')
        if proxy and proxy.lower() not in {'none', 'direct://'}:
            return proxy
    return ''


def opt_proxy_display(proxy):
    """Describe a proxy without printing embedded credentials."""
    value = proxy if '://' in proxy else f'http://{proxy}'
    try:
        parsed = urlparse(value)
        host = parsed.hostname or ''
        port = f':{parsed.port}' if parsed.port else ''
        if host:
            return f'{parsed.scheme or "http"}://{host}{port}'
    except ValueError:
        pass
    return '<configured proxy>'


def opt_toutiao_user_agent(os_name, browser_major):
    """Use the installed Chrome major without exposing the headless UA token."""
    if not str(browser_major).isdigit():
        return ''
    if os_name == 'Windows':
        platform_token = 'Windows NT 10.0; Win64; x64'
    elif os_name == 'Darwin':
        platform_token = 'Macintosh; Intel Mac OS X 10_15_7'
    else:
        platform_token = 'X11; Linux x86_64'
    return (
        f'Mozilla/5.0 ({platform_token}) AppleWebKit/537.36 '
        f'(KHTML, like Gecko) Chrome/{browser_major}.0.0.0 Safari/537.36'
    )


def opt_browser_major(browser_path, os_name):
    if browser_path is None:
        return ''
    try:
        completed = subprocess.run(
            [str(browser_path), '--version'],
            capture_output=True,
            text=True,
            timeout=5,
            check=False,
            creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0),
        )
        match = re.search(r'\b(\d+)\.\d+\.\d+\.\d+\b', completed.stdout + completed.stderr)
        if match:
            return match.group(1)
    except (OSError, subprocess.SubprocessError):
        pass
    if os_name == 'Windows':
        try:
            versions = [
                child.name for child in browser_path.parent.iterdir()
                if child.is_dir() and re.fullmatch(r'\d+\.\d+\.\d+\.\d+', child.name)
            ]
            if versions:
                return max(versions, key=lambda value: tuple(map(int, value.split('.')))).split('.')[0]
        except OSError:
            pass
    return ''


def opt_cached_driver_path(cache_path, browser_major, os_name):
    if not browser_major:
        return None
    machine = platform.machine().lower()
    if os_name == 'Windows':
        platform_names = {'win64', 'win32'}
        executable_name = 'chromedriver.exe'
    elif os_name == 'Darwin':
        platform_names = {'mac-arm64'} if machine in {'arm64', 'aarch64'} else {'mac-x64', 'mac64'}
        executable_name = 'chromedriver'
    else:
        platform_names = {'linux64'}
        executable_name = 'chromedriver'
    candidates = []
    for platform_name_value in platform_names:
        platform_dir = cache_path / 'chromedriver' / platform_name_value
        if not platform_dir.is_dir():
            continue
        for version_dir in platform_dir.iterdir():
            executable = version_dir / executable_name
            if (
                executable.is_file()
                and version_dir.name.split('.', 1)[0] == browser_major
                and re.fullmatch(r'\d+(?:\.\d+)*', version_dir.name)
            ):
                version = tuple(int(part) for part in version_dir.name.split('.'))
                candidates.append((version, executable))
    return max(candidates, default=((), None), key=lambda item: item[0])[1]


def opt_resolve_driver_assets(os_name):
    """Resolve ChromeDriver once for a batch, preferring a compatible local cache."""
    cache_path = opt_selenium_cache_path()
    browser_path = opt_find_browser()
    browser_major = opt_browser_major(browser_path, os_name)
    cached_driver = opt_cached_driver_path(cache_path, browser_major, os_name)
    if cached_driver is not None:
        print(f'已找到与 Chrome {browser_major} 匹配的缓存 ChromeDriver，本批直接复用。')
        return OptDriverAssets(str(cached_driver), str(browser_path or ''), browser_major)

    proxy = opt_detect_proxy()
    if proxy:
        print(f'检测到网络代理 {opt_proxy_display(proxy)}，本次 Driver 获取将通过代理连接。')
    else:
        print('未检测到 HTTP/HTTPS 代理，本次 Driver 获取使用直连。')
    print(f'本批运行一次 Selenium Manager（联网超时 {OPT_SELENIUM_MANAGER_TIMEOUT} 秒）。')
    arguments = [
        '--browser', 'chrome',
        '--cache-path', str(cache_path),
        '--timeout', str(OPT_SELENIUM_MANAGER_TIMEOUT),
        '--avoid-stats',
    ]
    if browser_path is not None:
        arguments.extend(('--browser-path', str(browser_path), '--avoid-browser-download'))
    else:
        arguments.extend(('--browser-version', 'stable'))
    if proxy:
        arguments.extend(('--proxy', proxy))
    resolved = SeleniumManager().binary_paths(arguments)
    driver_path = Path(resolved.get('driver_path') or '')
    if not driver_path.is_file():
        raise WebDriverException('Selenium Manager 未返回可用的 ChromeDriver')
    resolved_browser = resolved.get('browser_path') or str(browser_path or '')
    resolved_major = browser_major or opt_browser_major(
        Path(resolved_browser) if resolved_browser else None, os_name
    )
    if not resolved_major:
        match = re.match(r'(\d+)\.', driver_path.parent.name)
        resolved_major = match.group(1) if match else ''
    return OptDriverAssets(str(driver_path), str(resolved_browser), resolved_major)


def opt_reset_driver_assets():
    global OPT_DRIVER_ASSETS, OPT_DRIVER_RESOLUTION_ERROR
    with OPT_DRIVER_ASSETS_LOCK:
        OPT_DRIVER_ASSETS = None
        OPT_DRIVER_RESOLUTION_ERROR = None


def opt_get_driver_assets(os_name):
    global OPT_DRIVER_ASSETS, OPT_DRIVER_RESOLUTION_ERROR
    with OPT_DRIVER_ASSETS_LOCK:
        if OPT_DRIVER_ASSETS is not None:
            return OPT_DRIVER_ASSETS
        if OPT_DRIVER_RESOLUTION_ERROR is not None:
            raise RuntimeError('本批 Selenium Driver 解析已失败') from OPT_DRIVER_RESOLUTION_ERROR
        try:
            OPT_DRIVER_ASSETS = opt_resolve_driver_assets(os_name)
        except Exception as exc:
            OPT_DRIVER_RESOLUTION_ERROR = exc
            raise
        return OPT_DRIVER_ASSETS


def opt_create_driver(driver_path, os_name, config, group=None):
    if isinstance(driver_path, OptDriverAssets):
        assets = driver_path
    elif driver_path:
        assets = OptDriverAssets(str(driver_path))
    else:
        assets = opt_get_driver_assets(os_name)
    options = Options()
    # eager 让导航在 DOM 已可用时返回，后续由站点专用等待补足动态内容。
    options.page_load_strategy = 'eager'
    options.add_argument('--headless=new')
    options.add_argument('--disable-gpu')
    options.add_argument('--disable-extensions')
    options.add_argument('--disable-notifications')
    options.add_argument('--disable-background-networking')
    options.add_argument('--disable-component-update')
    options.add_argument('--disable-sync')
    options.add_argument('--no-pings')
    options.add_argument('--no-first-run')
    options.add_argument('--no-default-browser-check')
    options.add_experimental_option(
        'prefs', {
            'profile.default_content_setting_values.notifications': 2,
            # 抓取互动数不依赖图片，关闭图片可降低加载量、内存和 tab crash 概率。
            'profile.managed_default_content_settings.images': 2,
        }
    )
    if os_name == 'Windows' and group == 'other':
        # 快手在 DOM 中会隐藏部分数值；保留已完成的 GraphQL 响应用于只读解析。
        options.set_capability('goog:loggingPrefs', {'performance': 'ALL'})
    browser_path = Path(assets.browser_path) if assets.browser_path else opt_find_browser()
    if browser_path is not None:
        options.binary_location = str(browser_path)
    if group == 'toutiao':
        browser_major = assets.browser_major or opt_browser_major(browser_path, os_name)
        user_agent = opt_toutiao_user_agent(os_name, browser_major)
        if user_agent:
            # Chrome 的原生无头 UA 包含 HeadlessChrome，头条会在 /i 跳转前返回 error。
            options.add_argument(f'user-agent={user_agent}')
    service = Service(executable_path=assets.driver_path)
    driver = webdriver.Chrome(service=service, options=options)
    try:
        # 视频本体不是待抓取数据，阻止媒体分片可明显减少无头 Chrome 的资源占用。
        driver.execute_cdp_cmd('Network.enable', {})
        driver.execute_cdp_cmd('Network.setBlockedURLs', {
            'urls': ['*.mp4', '*.m3u8', '*.ts', '*.m4s', '*.webm', '*.mov', '*.avi', '*.flv']
        })
    except Exception:
        # 某些 Chrome/Driver 版本不支持该 CDP 命令时，继续使用正常加载流程。
        pass
    driver.set_page_load_timeout(config.page_timeout)
    driver.set_script_timeout(config.page_timeout)
    driver.implicitly_wait(0)
    return driver


def opt_create_driver_with_retry(driver_path, os_name, config, group=None):
    """首次 Selenium Manager 下载/配对 Driver 失败时允许一次重试。"""
    try:
        return opt_create_driver(driver_path, os_name, config, group)
    except Exception as exc:
        message = ' '.join(str(exc).split())
        print(
            f'{group} worker 首次启动浏览器失败：{type(exc).__name__}: '
            f'{message[:300]}；5 秒后重试。'
        )
        time.sleep(5)
        return opt_create_driver(driver_path, os_name, config, group)


def opt_wait_body(driver, timeout):
    try:
        WebDriverWait(driver, timeout, poll_frequency=0.2).until(
            EC.presence_of_element_located((By.TAG_NAME, 'body'))
        )
    except TimeoutException:
        pass


def opt_wait_title(driver, timeout):
    try:
        WebDriverWait(driver, timeout, poll_frequency=0.2).until(
            lambda current: bool(current.title.strip()) or current.execute_script(
                'return document.readyState === "complete"'
            )
        )
    except TimeoutException:
        pass


def opt_wait_douyin_content(driver, timeout):
    script = """
        const body = document.body;
        if (!body) return false;
        const text = body.innerText || '';
        const target = document.evaluate(
            arguments[0], document, null,
            XPathResult.FIRST_ORDERED_NODE_TYPE, null
        ).singleNodeValue;
        return Boolean(target) || text.includes('你要观看的图文不存在') ||
               text.includes('你要观看的视频不存在');
    """
    try:
        WebDriverWait(driver, timeout, poll_frequency=0.25).until(
            lambda current: current.execute_script(script, OPT_DOUYIN_VALID_XPATH)
        )
    except TimeoutException:
        pass


def opt_kuaishou_session_ready(driver):
    cookies = {
        cookie.get('name'): cookie.get('value', '')
        for cookie in driver.get_cookies()
        if cookie.get('name')
    }
    if not all(cookies.get(name) for name in ('did', 'kwssectoken', 'clientid')):
        return False
    path = urlparse(driver.current_url or '').path.rstrip('/')
    return path == '/new-reco' and len(opt_page_text(driver).strip()) >= 20


def opt_wait_kuaishou_session(driver, timeout):
    try:
        WebDriverWait(driver, timeout, poll_frequency=0.25).until(
            opt_kuaishou_session_ready
        )
    except TimeoutException:
        pass


def opt_wait_kuaishou_content(driver, timeout):
    script = """
        const body = document.body;
        const text = body ? (body.innerText || '').trim() : '';
        const like = document.querySelector('.like-item .item-count');
        return Boolean(like && (like.innerText || '').trim()) ||
               text.includes('作品已失效') ||
               text.includes('您要访问的页面弄丢了');
    """
    try:
        WebDriverWait(driver, timeout, poll_frequency=0.25).until(
            lambda current: current.execute_script(script)
        )
    except TimeoutException:
        pass


def opt_kuaishou_has_content(driver):
    return (
        (driver.title or '').strip() != '短视频-快手'
        and bool(opt_page_text(driver).strip())
    )


def opt_wait_weibo_content(driver, timeout):
    script = """
        const body = document.body;
        const text = body ? (body.innerText || '') : '';
        const metric = document.querySelector(
            'article footer [title="赞"], article footer .woo-like-count'
        );
        return Boolean(metric) || text.includes('该微博不存在') ||
               text.includes('原文章已被删除') || text.includes('暂无查看权限');
    """
    try:
        WebDriverWait(driver, timeout, poll_frequency=0.25).until(
            lambda current: current.execute_script(script)
        )
    except TimeoutException:
        pass


def opt_wait_tieba_content(driver, timeout):
    """Wait for the post, not for a temporary verification/loading page."""
    script = """
        const numbers = document.querySelectorAll(
            '.pc-pb-first-floor-interactive .action-item .action-number'
        );
        const legacy = document.querySelector('.d_post_content, .j_d_post_content');
        const text = document.body ? document.body.innerText : '';
        return Array.from(numbers).some(el => /\\d/.test(el.innerText || '')) ||
            Boolean(legacy) || document.title.includes('贴吧404') ||
            text.includes('该贴已被删除') || text.includes('该帖已被删除');
    """
    try:
        WebDriverWait(driver, timeout, poll_frequency=0.3).until(
            lambda current: current.execute_script(script)
        )
        return True
    except TimeoutException:
        return False


def opt_navigate(driver, url, config):
    try:
        driver.get(url)
    except TimeoutException:
        try:
            driver.execute_script('window.stop();')
        except Exception:
            pass
    opt_wait_body(driver, min(config.element_timeout, config.page_timeout))


def douyin_page(current_url, os_name=None, config=None):
    """兼容原有调用名，但始终复用当前 worker 的 driver。"""
    _ = os_name
    config = config or getattr(OPT_THREAD_STATE, 'config', None) or OptimizedConfig()
    driver = getattr(OPT_THREAD_STATE, 'driver', None)
    if driver is None:
        raise RuntimeError('douyin_page 必须在优化版 worker 中调用')
    opt_navigate(driver, current_url, config)
    opt_wait_douyin_content(driver, min(config.element_timeout, 4.0))
    return driver, driver.page_source


def hong_page(current_url, os_name=None, config=None):
    """兼容原有调用名，但始终复用当前 worker 的 driver。"""
    _ = os_name
    config = config or getattr(OPT_THREAD_STATE, 'config', None) or OptimizedConfig()
    driver = getattr(OPT_THREAD_STATE, 'driver', None)
    if driver is None:
        raise RuntimeError('hong_page 必须在优化版 worker 中调用')
    opt_navigate(driver, current_url, config)
    return driver, driver.page_source


def opt_load_page(driver, current_url, os_name, config):
    html_source = None
    if platform_name(current_url) == '今日头条':
        opt_navigate(driver, current_url, config)
        opt_wait_toutiao_content(driver, current_url, max(config.element_timeout, 10.0))
    elif 'haokan.baidu.com' in current_url:
        opt_navigate(driver, current_url, config)
        driver.refresh()
        opt_wait_body(driver, config.element_timeout)
    elif 'tieba.baidu.com' in current_url:
        opt_navigate(driver, current_url, config)
        ready = opt_wait_tieba_content(driver, config.element_timeout)
        if not ready and not OPT_STOP_EVENT.is_set():
            print('贴吧首次未取得正文，完成等待后重新加载一次。')
            driver.refresh()
            opt_wait_body(driver, config.element_timeout)
            opt_wait_tieba_content(driver, config.element_timeout)
    elif 'douyin.com' in current_url:
        _, html_source = douyin_page(current_url, os_name, config)
    elif 'xiaohongshu.com' in current_url:
        _, html_source = hong_page(current_url, os_name, config)
    elif os_name != 'Windows' and 'kuaishou.com' in current_url:
        if not opt_kuaishou_session_ready(driver):
            opt_navigate(driver, 'https://www.kuaishou.com/', config)
            opt_wait_kuaishou_session(driver, min(config.element_timeout, 6.0))
        opt_navigate(driver, current_url, config)
        opt_wait_kuaishou_content(driver, min(config.element_timeout, 6.0))
        if not opt_kuaishou_has_content(driver):
            opt_navigate(driver, 'https://www.kuaishou.com/', config)
            opt_wait_kuaishou_session(driver, min(config.element_timeout, 6.0))
            opt_navigate(driver, current_url, config)
            opt_wait_kuaishou_content(driver, min(config.element_timeout, 6.0))
    elif os_name != 'Windows' and 'weibo.com' in current_url:
        opt_navigate(driver, current_url, config)
        opt_wait_weibo_content(driver, min(config.element_timeout, 6.0))
    else:
        opt_navigate(driver, current_url, config)
    return html_source


def opt_error_text(exc):
    message = ' '.join(str(exc).split())
    return message if message else repr(exc)


def opt_is_session_error(exc):
    message = opt_error_text(exc).lower()
    return any(marker in message for marker in OPT_SESSION_ERROR_MARKERS)


def opt_is_network_error(exc):
    message = opt_error_text(exc).lower()
    return any(marker in message for marker in OPT_NETWORK_ERROR_MARKERS)


def opt_log_webdriver_error(item, group, exc, driver, phase='process'):
    current_url = ''
    title = ''
    if driver is not None:
        try:
            current_url = driver.current_url
        except Exception:
            current_url = '<driver unavailable>'
        try:
            title = driver.title
        except Exception:
            title = '<title unavailable>'
    log_path = OPT_BASE_DIR / 'webdriver_errors.log'
    log_entry = (
        f'[{time.strftime("%Y-%m-%d %H:%M:%S")}] '
        f'index={item[0]} group={group} phase={phase} '
        f'exception={type(exc).__name__}: {opt_error_text(exc)}\n'
        f'original_url={item[1]}\ncurrent_url={current_url}\ntitle={title}\n'
        f'{traceback.format_exc()}\n'
    )
    with OPT_LOG_LOCK:
        with log_path.open('a', encoding='utf-8') as log_file:
            log_file.write(log_entry)
    print(
        f'第{item[0]}条处理失败：{type(exc).__name__}: '
        f'{opt_error_text(exc)[:300]}'
    )


def opt_quit_driver(driver):
    if driver is not None:
        try:
            driver.quit()
        except Exception:
            pass


def opt_iesdouyin_desktop_url(url):
    """仅为原始 iesdouyin 作品链接选择电脑版入口。"""
    parsed = urlparse(url)
    host = (parsed.hostname or '').lower()
    if host != 'iesdouyin.com' and not host.endswith('.iesdouyin.com'):
        return None
    match = re.fullmatch(r'/(?:share/)?(video|note)/(\d+)/?', parsed.path)
    if not match:
        return None
    return f'https://www.douyin.com/{match[1]}/{match[2]}'


def opt_process_iesdouyin(url, target, driver, judge_needs, config):
    opt_navigate(driver, target, config)
    keys = ('video-player-digg', 'feed-comment-icon',
            'video-player-collect', 'video-player-share')

    def read_page(current):
        text = opt_page_text(current)
        if any(marker in text for marker in OPT_DOUYIN_DELETED_MARKERS):
            return '已删除', None
        title = current.title or ''
        if '验证码中间页' in title or any(frame.is_displayed() for frame in current.find_elements(
            By.CSS_SELECTOR, 'iframe[src*="/verifycenter/captcha/"]'
        )):
            return '需验证', None
        values = []
        for key in keys:
            # display:contents 节点也可能有互动数，不能按自身矩形过滤。
            texts = [current.execute_script(
                'return (arguments[0].innerText || "").trim();', element
            ) for element in current.find_elements(
                By.CSS_SELECTOR, f'[data-e2e="{key}"]'
            )]
            numeric = next((value for value in texts if re.fullmatch(
                r'[0-9]+(?:[.,][0-9]+)*(?:万|亿|[wWkK])?\+?', value
            )), None)
            values.append(numeric if numeric is not None else (
                '0' if any(texts) else None
            ))
        return '', values

    def ready(current):
        if OPT_STOP_EVENT.is_set():
            return True
        status, values = read_page(current)
        # 工具栏可能先显示文字再加载数字；无数字的情况等到超时再记 0。
        # 验证层可能先于删除提示出现，继续等待正文完成状态判定。
        if status:
            return status == '已删除'
        return all(value not in (None, '0') for value in values)

    try:
        WebDriverWait(driver, max(config.element_timeout, 10.0), poll_frequency=0.5,
                      ignored_exceptions=(StaleElementReferenceException,)).until(ready)
    except TimeoutException:
        pass
    status, values = read_page(driver)
    if status:
        return opt_result_row(url, status=status)
    if not all(value is not None for value in values):
        # 工具栏没有加载不代表四项均为 0。
        return opt_result_row(url, status='处理失败')
    metrics = tuple(values) + ('',) if judge_needs == '1' else None
    return opt_result_row(url, metrics=metrics)


def opt_process_one(item, driver, judge_needs, os_name, config):
    num, url = item
    if not opt_is_supported(url):
        return opt_result_row(url, status='不支持')

    current_url = opt_normalize_url(url)
    try:
        desktop_url = opt_iesdouyin_desktop_url(url)
        if desktop_url:
            row = opt_process_iesdouyin(url, desktop_url, driver, judge_needs, config)
            row['_iesdouyin_parser_version'] = 1
            return row
        html_source = opt_load_page(driver, current_url, os_name, config)
        is_xhs = 'xiaohongshu.com' in current_url
        is_douyin = 'douyin.com' in current_url
        if judge_needs == '1':
            valid = url_valid(
                current_url, driver, html_source
            ) if (is_xhs or is_douyin) else url_valid(current_url, driver)
            if valid == '正常':
                if is_douyin or is_xhs:
                    metrics = get_interactions(current_url, driver, html_source, os_name)
                else:
                    metrics = get_interactions(current_url, driver)
                return opt_result_row(url, metrics=metrics)
            if platform_name(url) == '百度贴吧':
                print(f'第{num}条贴吧未取得正文：{valid}（页面标题：{driver.title[:80]}）。')
            return opt_result_row(url, status=valid)

        valid = url_valid(
            current_url, driver, html_source
        ) if (is_xhs or is_douyin) else url_valid(current_url, driver)
        return opt_result_row(url) if valid == '正常' else opt_result_row(url, status=valid)
    except WebDriverException:
        # 交给 worker 判断是本地会话崩溃还是平台/网络类错误。
        raise
    except Exception as exc:
        print(f'第{num}条处理失败：{type(exc).__name__}: {opt_error_text(exc)[:300]}')
        return opt_result_row(url, status='处理失败')


def opt_split_buckets(items, count):
    count = max(1, min(count, len(items)))
    buckets = [[] for _ in range(count)]
    for index, item in enumerate(items):
        buckets[index % count].append(item)
    return [bucket for bucket in buckets if bucket]


def opt_worker(bucket, group, driver_path, judge_needs, os_name, config, callback):
    driver = None
    completed = set()
    consecutive_errors = 0
    try:
        if OPT_STOP_EVENT.is_set():
            return
        if os_name == 'Windows':
            driver = opt_create_driver_with_retry(driver_path, os_name, config, group)
        else:
            driver = opt_create_driver(driver_path, os_name, config, group)
        OPT_THREAD_STATE.driver = driver
        OPT_THREAD_STATE.config = config
        low, high = OPT_COOLDOWNS.get(group, OPT_COOLDOWNS['other'])
        for position, item in enumerate(bucket):
            if OPT_STOP_EVENT.is_set():
                break
            try:
                if group == 'toutiao' and position:
                    # 头条旧链接会先跳转；复用上一页会话可能被错误带到 SSO 登录页。
                    # 与原脚本一致，每条头条链接独立会话，先退出再创建以保持并发上限。
                    opt_quit_driver(driver)
                    driver = None
                    OPT_THREAD_STATE.driver = None
                    if OPT_STOP_EVENT.is_set():
                        break
                    driver = opt_create_driver(driver_path, os_name, config, group)
                    OPT_THREAD_STATE.driver = driver
                row = opt_process_one(item, driver, judge_needs, os_name, config)
            except WebDriverException as exc:
                opt_log_webdriver_error(item, group, exc, driver)
                if opt_is_session_error(exc):
                    # 只针对本地 Chrome 会话崩溃恢复一次，不用重启浏览器绕过平台限制。
                    opt_quit_driver(driver)
                    driver = None
                    OPT_THREAD_STATE.driver = None
                    time.sleep(OPT_SESSION_RECOVERY_PAUSE)
                    try:
                        driver = opt_create_driver(driver_path, os_name, config, group)
                        OPT_THREAD_STATE.driver = driver
                        row = opt_process_one(item, driver, judge_needs, os_name, config)
                    except WebDriverException as recovery_exc:
                        opt_log_webdriver_error(item, group, recovery_exc, driver, phase='recovery')
                        callback(item[0], opt_result_row(item[1], status='处理失败'))
                        completed.add(item[0])
                        consecutive_errors += 1
                        if group == 'douyin' and consecutive_errors < OPT_DOUYIN_MAX_CONSECUTIVE_ERRORS:
                            print(
                                f'抖音会话恢复失败，等待后重建浏览器（连续失败 '
                                f'{consecutive_errors}/{OPT_DOUYIN_MAX_CONSECUTIVE_ERRORS}）。'
                            )
                            time.sleep(random.uniform(*OPT_DOUYIN_ERROR_PAUSE))
                            try:
                                driver = opt_create_driver(driver_path, os_name, config, group)
                                OPT_THREAD_STATE.driver = driver
                            except Exception as recreate_exc:
                                print(
                                    f'{group} worker 重建浏览器失败：'
                                    f'{type(recreate_exc).__name__}'
                                )
                                break
                            continue
                        print(f'{group} worker 会话恢复失败，已暂停剩余链接。')
                        break
                    except Exception as recovery_exc:
                        print(
                            f'第{item[0]}条恢复后处理失败：{type(recovery_exc).__name__}: '
                            f'{opt_error_text(recovery_exc)[:300]}'
                        )
                        callback(item[0], opt_result_row(item[1], status='处理失败'))
                        completed.add(item[0])
                        consecutive_errors += 1
                        if group == 'douyin' and consecutive_errors < OPT_DOUYIN_MAX_CONSECUTIVE_ERRORS:
                            time.sleep(random.uniform(*OPT_DOUYIN_ERROR_PAUSE))
                            try:
                                driver = opt_create_driver(driver_path, os_name, config, group)
                                OPT_THREAD_STATE.driver = driver
                            except Exception as recreate_exc:
                                print(
                                    f'{group} worker 重建浏览器失败：'
                                    f'{type(recreate_exc).__name__}'
                                )
                                break
                            continue
                        print(f'{group} worker 恢复后出现异常，已暂停剩余链接。')
                        break
                else:
                    callback(item[0], opt_result_row(item[1], status='处理失败'))
                    completed.add(item[0])
                    if group == 'toutiao' and opt_is_network_error(exc):
                        consecutive_errors += 1
                        if consecutive_errors >= OPT_TOUTIAO_MAX_CONSECUTIVE_NETWORK_ERRORS:
                            print(
                                '头条连续出现网络连接异常，已暂停当前 worker，'
                                '剩余链接可稍后续跑。'
                            )
                            break
                        print(
                            f'头条网络连接异常，退避后继续（连续失败 '
                            f'{consecutive_errors}/{OPT_TOUTIAO_MAX_CONSECUTIVE_NETWORK_ERRORS}）。'
                        )
                        OPT_STOP_EVENT.wait(random.uniform(*OPT_TOUTIAO_ERROR_PAUSE))
                        continue
                    if group == 'douyin':
                        consecutive_errors += 1
                        if consecutive_errors >= OPT_DOUYIN_MAX_CONSECUTIVE_ERRORS:
                            print(
                                '抖音连续出现平台/网络异常，已暂停当前 worker，'
                                '避免继续触发风控。'
                            )
                            break
                        print(
                            f'抖音本次请求失败，等待后继续（连续失败 '
                            f'{consecutive_errors}/{OPT_DOUYIN_MAX_CONSECUTIVE_ERRORS}）。'
                        )
                        time.sleep(random.uniform(*OPT_DOUYIN_ERROR_PAUSE))
                        opt_quit_driver(driver)
                        driver = None
                        OPT_THREAD_STATE.driver = None
                        try:
                            driver = opt_create_driver(driver_path, os_name, config, group)
                            OPT_THREAD_STATE.driver = driver
                        except Exception as recreate_exc:
                            print(
                                f'{group} worker 重建浏览器失败：'
                                f'{type(recreate_exc).__name__}'
                            )
                            break
                        continue
                    continue
            consecutive_errors = 0
            callback(item[0], row)
            completed.add(item[0])
            if position + 1 < len(bucket):
                OPT_STOP_EVENT.wait(random.uniform(low, high))
    except Exception as exc:
        print(f'{group} worker 启动或运行失败：{type(exc).__name__}')
        for item in bucket:
            if item[0] not in completed:
                callback(item[0], opt_result_row(item[1], status='处理失败'))
    finally:
        OPT_THREAD_STATE.driver = None
        OPT_THREAD_STATE.config = None
        if driver is not None:
            opt_quit_driver(driver)


def opt_signature(urls, judge_needs):
    payload = '\n'.join(urls) + f'\n{judge_needs}'
    if platform.system() == 'Windows':
        payload += f'\nv{OPT_CHECKPOINT_VERSION}'
    else:
        payload += f'\nparser={OPT_PARSER_VERSION}'
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()


def opt_write_checkpoint(path, results, total, signature):
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        'saved_at': time.strftime('%Y-%m-%d %H:%M:%S'),
        'completed': len(results),
        'total': total,
        'input_signature': signature,
        'results': {str(index): row for index, row in sorted(results.items())},
    }
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    temporary.replace(path)


def opt_load_checkpoint(path, urls, signature):
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding='utf-8'))
        if payload.get('input_signature') != signature:
            return {}
        restored = {}
        for raw_index, row in payload.get('results', {}).items():
            index = int(raw_index)
            # 失败项不能视为已完成；--resume 应该重新尝试它们。
            if (
                1 <= index <= len(urls)
                and row.get('链接') == urls[index - 1]
                and row.get('链接状态', '') not in OPT_RETRYABLE_STATUSES
                and (
                    not opt_iesdouyin_desktop_url(urls[index - 1])
                    or row.get('_iesdouyin_parser_version') == 1
                )
                and (
                    platform_name(urls[index - 1]) != '百度贴吧'
                    or row.get('_tieba_parser_version') == OPT_TIEBA_PARSER_VERSION
                )
                and (
                    platform_name(urls[index - 1]) != '今日头条'
                    or row.get('_toutiao_parser_version') == OPT_TOUTIAO_PARSER_VERSION
                )
            ):
                restored[index] = row
        return restored
    except (OSError, ValueError, TypeError):
        return {}


def opt_save_xlsx(path, results, urls=None, mode='1'):
    write_result_workbook(path, results, urls, mode)


def opt_positive_int(value):
    value = int(value)
    if value < 1:
        raise argparse.ArgumentTypeError('必须是正整数')
    return value


def opt_nonnegative_int(value):
    value = int(value)
    if value < 0:
        raise argparse.ArgumentTypeError('必须是非负整数')
    return value


def opt_main(argv=None, on_event=None):
    # The UI passes an event sink; all callbacks are queued, never Tk calls.
    def emit(kind, **payload):
        if on_event is not None:
            on_event(kind, payload)

    parser = argparse.ArgumentParser(description='复用浏览器、限并发的链接热度抓取脚本')
    parser.add_argument('--input', default=str(OPT_BASE_DIR / 'urls.txt'), help='输入链接文件')
    parser.add_argument('--output', default='', help='输出 xlsx 路径，默认写入当前优化目录')
    parser.add_argument('--resume', action='store_true', help='从同目录进行中的 checkpoint 继续')
    parser.add_argument('--limit', type=opt_nonnegative_int, default=0, help='只处理前 N 条，0 表示全部')
    parser.add_argument('--toutiao-workers', type=opt_positive_int, default=2, help='头条并发数，最多 3')
    parser.add_argument('--douyin-workers', type=opt_positive_int, default=1, help='抖音并发数，默认固定为 1')
    parser.add_argument('--other-workers', type=opt_positive_int, default=1, help='其他平台并发数，最多 1')
    parser.add_argument('--page-timeout', type=float, default=20.0, help='单页导航超时秒数')
    parser.add_argument('--element-timeout', type=float, default=6.0, help='动态元素等待秒数')
    parser.add_argument('--retries', type=opt_positive_int, default=3, help='抖音/小红书最大重试次数，最多 3 次')
    parser.add_argument('--checkpoint-every', type=opt_nonnegative_int, default=50, help='每 N 条保存一次进度，0 表示关闭')
    args = parser.parse_args(argv)
    opt_reset_driver_assets()
    if on_event is None:
        OPT_STOP_EVENT.clear()

    input_path = Path(args.input).expanduser()
    if not input_path.is_absolute():
        input_path = OPT_BASE_DIR / input_path
    output_path = Path(args.output).expanduser() if args.output else (
        OPT_BASE_DIR / f'链接判断结果_优化_{time.strftime("%Y-%m-%d__%H：%M")}.xlsx'
    )
    if not output_path.is_absolute():
        output_path = OPT_BASE_DIR / output_path

    judge_needs = opt_read_settings(OPT_BASE_DIR / 'settings.txt')
    os_name = platform.system()
    urls = opt_read_urls(input_path)
    if args.limit:
        urls = urls[:args.limit]
    total = len(urls)
    signature = opt_signature(urls, judge_needs)
    checkpoint_path = OPT_BASE_DIR / '链接判断结果_进行中.json'
    config = OptimizedConfig(
        page_timeout=max(1.0, args.page_timeout),
        element_timeout=max(0.5, args.element_timeout),
        douyin_retries=min(args.retries, 3),
        checkpoint_every=args.checkpoint_every,
        toutiao_workers=min(args.toutiao_workers, 3),
        douyin_workers=min(args.douyin_workers, 1),
        other_workers=min(args.other_workers, 1),
    )
    if args.toutiao_workers > 3 or args.douyin_workers > 1 or args.other_workers > 1:
        print('已按安全上限限制并发：头条最多 3、抖音最多 1、其他平台最多 1，总 worker 最多 4。')

    # worker 首次启动时只解析一次 Driver，后续头条独立会话复用该路径。
    driver_path = None
    indexed_urls = list(enumerate(urls, start=1))
    results = opt_load_checkpoint(checkpoint_path, urls, signature) if args.resume else {}
    # Fetch exact duplicate URLs once, but retain every original row and index.
    occurrences = {}
    for index, url in indexed_urls:
        occurrences.setdefault(url, []).append(index)
    for indices in occurrences.values():
        restored = next((results[index] for index in indices if index in results), None)
        if restored is not None:
            for index in indices:
                results[index] = dict(restored)
    emit('prepared', total=total, restored=dict(results))
    if results:
        print(f'已恢复 {len(results)} 条进行中结果。')

    lock = threading.Lock()

    def callback(index, row):
        with lock:
            previous = len(results)
            for original_index in occurrences[urls[index - 1]]:
                if original_index in results:
                    continue
                results[original_index] = dict(row)
                emit('result', index=original_index, row=dict(row), completed=len(results), total=total)
            completed = len(results)
            if completed % config.progress_every == 0 or completed == total:
                print(f'已完成 {completed}/{total}')
            if config.checkpoint_every and completed // config.checkpoint_every > previous // config.checkpoint_every:
                opt_write_checkpoint(checkpoint_path, results, total, signature)

    groups = {'toutiao': [], 'douyin': [], 'kuaishou': [], 'other': []}
    scheduled = set()
    for item in indexed_urls:
        index, url = item
        if index in results or url in scheduled:
            continue
        scheduled.add(url)
        group = opt_group(url)
        if group == 'unsupported':
            callback(index, opt_result_row(url, status='不支持'))
        else:
            groups[group].append(item)

    worker_limits = {
        'toutiao': config.toutiao_workers,
        'douyin': config.douyin_workers,
        'kuaishou': 1,
        'other': config.other_workers,
    }
    tasks = []
    for group in ('toutiao', 'douyin', 'kuaishou', 'other'):
        for bucket in opt_split_buckets(groups[group], worker_limits[group]):
            tasks.append((bucket, group))

    print(
        f'开始处理 {total} 条链接；并发配置：头条 {config.toutiao_workers}、'
        f'抖音 {config.douyin_workers}、其他 {config.other_workers}，'
        f'实际浏览器最多 {OPT_MAX_TOTAL_WORKERS} 个。'
    )
    run_error = None
    try:
        emit('phase', text='正在抓取；首次使用可能需要准备浏览器组件')
        if tasks:
            with concurrent.futures.ThreadPoolExecutor(
                max_workers=min(OPT_MAX_TOTAL_WORKERS, len(tasks))
            ) as executor:
                futures = [
                    executor.submit(
                        opt_worker, bucket, group, driver_path, judge_needs,
                        os_name, config, callback
                    )
                    for bucket, group in tasks
                ]
                for future in futures:
                    future.result()
    except KeyboardInterrupt:
        run_error = '用户中断'
        print('收到中断，正在保存已完成结果。')
    except Exception as exc:
        run_error = type(exc).__name__
        print(f'批处理异常：{run_error}')
    finally:
        with lock:
            opt_write_checkpoint(checkpoint_path, results, total, signature)
            emit('phase', text='正在保存 Excel 结果，请稍候')
            opt_save_xlsx(output_path, results, urls, judge_needs)
            emit('saved', path=str(output_path), completed=len(results), total=total)

    print(f'结果已保存：{output_path}')
    if len(results) == total and run_error is None:
        print('处理完成。')
        return 0
    print(f'当前保存 {len(results)}/{total} 条；可追加 --resume 继续。')
    return 1


if __name__ == '__main__':
    raise SystemExit(opt_main())
