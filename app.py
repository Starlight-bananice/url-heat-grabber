from __future__ import annotations

import argparse
import contextlib
import json
import os
import platform
import queue
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import tkinter as tk
import tkinter.font as tkfont
import webbrowser
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

import engine
from ui_model import (METRICS, TaskStore, describe_result, metric_text, parse_links,
                      platform_name, read_links, valid_url, write_private_file,
                      write_result_workbook)

APP_TITLE = '链接热度抓取 · 新版预览'
APP_VERSION = '0.6.0 preview.3'
COLORS = dict(bg='#F3F5F2', surface='#FFFFFF', sidebar='#E9EDE7', ink='#213D33',
              muted='#69796F', line='#DEE5DD', accent='#28684F', hover='#20543F',
              pale='#E5F0E8', warning='#9A681D', danger='#B34D42', input='#F7F9F6')


def app_data_dir():
    system = platform.system()
    if system == 'Windows':
        return Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming')) / 'URLHeatPreview'
    if system == 'Darwin':
        return Path.home() / 'Library' / 'Application Support' / 'URLHeatPreview'
    return Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'URLHeatPreview'


DATA_DIR = app_data_dir()
OUTPUT_DIR = Path.home() / 'Documents' / '链接热度抓取' / '新版预览'
ASSET_DIR = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent)) / 'assets'


def remove_legacy_captcha_credentials(path):
    try:
        Path(path).unlink(missing_ok=True)
        return True
    except OSError:
        return False


class QueueWriter:
    def __init__(self, events):
        self.events = events

    def write(self, value):
        if value.strip():
            self.events.put(('log', value.strip()))
        return len(value)

    def flush(self):
        pass


class UrlHeatApp(tk.Tk):
    def __init__(self, data_dir=None, output_dir=None):
        super().__init__()
        self.data_dir = Path(data_dir) if data_dir else DATA_DIR
        self.store = TaskStore(self.data_dir)
        self.title(APP_TITLE)
        self.geometry('1240x880')
        self.minsize(1080, 760)
        self.configure(bg=COLORS['bg'])
        self.protocol('WM_DELETE_WINDOW', self.close_app)
        self.events = queue.Queue()
        self.running = False
        self.stopping = False
        self.worker_thread = None
        self.task = None
        self.results = {}
        self.run_links = []
        self.run_mode = '1'
        self.output_path = None
        self.export_saved = False
        self.started_at = None
        self.elapsed = 0
        self.close_when_done = False
        self._edit_job = None
        self._table_job = None
        self._rendered = {}
        self._history_records = {}
        self.log_lines = []
        self.current_page = 'workspace'
        self.current_filter = '全部'
        self.result_view = 'results'
        self.result_focus = False
        prefs = self.read_preferences()
        self.input_path = tk.StringVar()
        self.output_path_var = tk.StringVar(value=str(output_dir or prefs.get('output_dir') or OUTPUT_DIR))
        self.mode = tk.StringVar(value=prefs.get('mode', '1') if prefs.get('mode') in ('0', '1') else '1')
        self.resume = tk.BooleanVar(value=prefs.get('resume', True))
        self.deduplicate = tk.BooleanVar(value=prefs.get('deduplicate', True))
        self.toutiao_workers = tk.IntVar(value=prefs.get('workers', 2) if prefs.get('workers') in (1, 2, 3) else 2)
        self.status = tk.StringVar(value='就绪 · 添加链接即可开始')
        self.input_summary = tk.StringVar(value='0 条链接')
        self.input_note = tk.StringVar(value='支持从分享文案中提取网址，也可以直接粘贴 Excel 单元格。')
        self.progress_text = tk.StringVar(value='等待开始')
        self.timer_text = tk.StringVar(value='')
        self.search = tk.StringVar()
        self.detail_text = tk.StringVar(value='选择一条结果查看说明；双击链接可在浏览器中打开。')
        self.stat_values = [tk.StringVar(value='0') for _ in range(4)]
        self.configure_theme()
        self.build_ui()
        self.search.trace_add('write', lambda *_: self.schedule_table())
        self.deduplicate.trace_add('write', lambda *_: self.refresh_input())
        shortcut = 'Command' if platform.system() == 'Darwin' else 'Control'
        self.bind(f'<{shortcut}-o>', lambda _: self.choose_input())
        self.bind(f'<{shortcut}-Return>', lambda _: self.start())
        self.bind(f'<{shortcut}-Shift-S>', lambda _: self.save_as())
        self.bind(f'<{shortcut}-a>', self.select_all)
        self.bind(f'<{shortcut}-q>', lambda _: self.close_app())
        self.after(100, self.drain_events)
        self.after(500, self.tick)
        self.refresh_input()

    def configure_theme(self):
        families = set(tkfont.families(self))
        self.font_name = next((name for name in ('PingFang SC', 'Microsoft YaHei UI', 'Noto Sans CJK SC') if name in families), 'TkDefaultFont')
        self.mono_name = 'Menlo' if 'Menlo' in families else 'Consolas' if 'Consolas' in families else self.font_name
        for name in ('TkDefaultFont', 'TkTextFont', 'TkMenuFont', 'TkHeadingFont'):
            tkfont.nametofont(name).configure(family=self.font_name, size=11)
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure('.', font=(self.font_name, 11), foreground=COLORS['ink'], background=COLORS['surface'])
        self.style.configure('TButton', padding=(12, 7), borderwidth=1, relief='flat',
                             background=COLORS['surface'], bordercolor=COLORS['line'], focuscolor=COLORS['accent'])
        self.style.map('TButton', background=[('active', COLORS['pale']), ('disabled', '#F0F2EE')],
                       foreground=[('disabled', '#9BA69E')], bordercolor=[('focus', COLORS['accent'])])
        self.style.configure('Primary.TButton', background=COLORS['accent'], foreground='#FFFFFF',
                             bordercolor=COLORS['accent'], font=(self.font_name, 12, 'bold'), padding=(15, 10))
        self.style.map('Primary.TButton', background=[('disabled', '#AAB9AE'), ('active', COLORS['hover'])],
                       foreground=[('disabled', '#FFFFFF')], bordercolor=[('disabled', '#AAB9AE')])
        self.style.configure('Quiet.TButton', borderwidth=0, padding=(10, 5), background=COLORS['surface'], foreground=COLORS['muted'])
        self.style.configure('Tab.TButton', borderwidth=0, padding=(12, 7), background=COLORS['surface'], foreground=COLORS['muted'])
        self.style.configure('Selected.Tab.TButton', borderwidth=0, padding=(12, 7), background=COLORS['pale'], foreground=COLORS['accent'], font=(self.font_name, 11, 'bold'))
        self.style.map('Selected.Tab.TButton', background=[('active', COLORS['pale'])])
        self.style.configure('Nav.TButton', borderwidth=0, anchor='w', padding=(16, 12), background=COLORS['sidebar'], foreground=COLORS['muted'])
        self.style.configure('Active.Nav.TButton', background='#D7E4D8', foreground=COLORS['ink'], borderwidth=0,
                             anchor='w', padding=(16, 12), font=(self.font_name, 11, 'bold'))
        for style in ('Nav.TButton', 'Active.Nav.TButton'):
            self.style.map(style, background=[('active', '#DAE4D8')])
        self.style.configure('TCheckbutton', background=COLORS['surface'], padding=(0, 4))
        self.style.map('TCheckbutton', background=[('active', COLORS['surface'])])
        self.style.configure('TRadiobutton', background=COLORS['surface'], padding=(0, 3))
        self.style.map('TRadiobutton', background=[('active', COLORS['surface'])])
        self.style.configure('TEntry', padding=(8, 7), fieldbackground=COLORS['input'], bordercolor=COLORS['line'])
        self.style.map('TEntry', bordercolor=[('focus', COLORS['accent'])])
        self.style.configure('Treeview', font=(self.font_name, 11), rowheight=36, borderwidth=0,
                             fieldbackground=COLORS['surface'], background=COLORS['surface'], foreground=COLORS['ink'])
        self.style.configure('Treeview.Heading', font=(self.font_name, 10, 'bold'), padding=(8, 9),
                             background='#F0F4EF', foreground=COLORS['muted'], borderwidth=0, relief='flat')
        self.style.map('Treeview', background=[('selected', '#DAEBDD')], foreground=[('selected', '#193B2B')])
        self.style.map('Treeview.Heading', background=[('active', '#E9F0E7')])
        self.style.configure('Horizontal.TProgressbar', troughcolor='#E5EAE2', background=COLORS['accent'],
                             borderwidth=0, bordercolor='#E5EAE2', lightcolor=COLORS['accent'], darkcolor=COLORS['accent'])
        for orientation in ('Vertical', 'Horizontal'):
            self.style.configure(f'{orientation}.TScrollbar', borderwidth=0, arrowsize=8,
                                 background='#DAE2D7', troughcolor=COLORS['surface'],
                                 bordercolor=COLORS['surface'], lightcolor='#DAE2D7', darkcolor='#DAE2D7')
            self.style.layout(f'{orientation}.TScrollbar', [(f'{orientation}.Scrollbar.trough', {
                'sticky': 'nswe', 'children': [(f'{orientation}.Scrollbar.thumb', {'sticky': 'nswe', 'expand': True})]})])

    def label(self, parent, text=None, *, size=11, color='ink', bold=False, bg=None, **kwargs):
        return tk.Label(parent, text=text, font=(self.font_name, size, 'bold' if bold else 'normal'),
                        fg=COLORS.get(color, color), bg=bg or parent.cget('bg'), bd=0, **kwargs)

    def frame(self, parent, bg='surface', **kwargs):
        return tk.Frame(parent, bg=COLORS.get(bg, bg), bd=0, **kwargs)

    def line(self, parent):
        return tk.Frame(parent, bg=COLORS['line'], height=1)

    def build_ui(self):
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        sidebar = self.frame(self, 'sidebar', width=182)
        sidebar.grid(row=0, column=0, sticky='nsew')
        sidebar.pack_propagate(False)
        brand = self.frame(sidebar, 'sidebar')
        brand.pack(fill='x', padx=22, pady=(32, 26))
        self.brand_icon = tk.PhotoImage(file=str(ASSET_DIR / 'sidebar_icon.png'))
        tk.Label(brand, image=self.brand_icon, bg=COLORS['sidebar'], bd=0).pack(anchor='w', pady=(0, 12))
        if platform.system() == 'Windows':
            self.iconbitmap(default=str(ASSET_DIR / 'app_icon.ico'))
        self.label(brand, '链接热度', size=18, bold=True).pack(anchor='w')
        self.label(brand, 'URL HEAT', size=10, color='muted').pack(anchor='w', pady=(3, 0))
        self.label(sidebar, '工作空间', size=9, color='muted').pack(anchor='w', padx=27, pady=(8, 10))
        self.nav_buttons = {}
        for key, label in (('workspace', '＋   链接工作台'), ('history', '◷   任务记录'), ('guide', '？   使用指南')):
            button = ttk.Button(sidebar, text=label, style='Nav.TButton', command=lambda name=key: self.show_page(name))
            button.pack(fill='x', padx=12, pady=3)
            self.nav_buttons[key] = button
        bottom = self.frame(sidebar, 'sidebar')
        bottom.pack(side='bottom', fill='x', padx=24, pady=25)
        self.line(bottom).pack(fill='x', pady=(0, 14))
        self.label(bottom, '文件保存在本机', size=10, color='muted').pack(anchor='w')
        self.label(bottom, '0.6 / 贴吧修复版', size=9, color='muted').pack(anchor='w', pady=(7, 0))
        main = self.frame(self, 'bg')
        main.grid(row=0, column=1, sticky='nsew', padx=28, pady=(24, 14))
        main.columnconfigure(0, weight=1)
        main.rowconfigure(1, weight=1)
        header = self.frame(main, 'bg')
        header.grid(row=0, column=0, sticky='ew', pady=(0, 18))
        titles = self.frame(header, 'bg')
        titles.pack(side='left')
        self.page_title = self.label(titles, '链接工作台', size=25, bold=True)
        self.page_title.pack(anchor='w')
        self.page_caption = self.label(titles, '让一批链接，变成一份清楚的结果。', color='muted', size=11)
        self.page_caption.pack(anchor='w', pady=(5, 0))
        self.label(header, '●  本地工作空间', size=10, color='accent', bg='#E2EBDD', padx=12, pady=7).pack(side='right')
        self.pages = {}
        for name in ('workspace', 'history', 'guide'):
            page = self.frame(main, 'bg')
            page.grid(row=1, column=0, sticky='nsew')
            self.pages[name] = page
        self.build_workspace(self.pages['workspace'])
        self.build_history(self.pages['history'])
        self.build_guide(self.pages['guide'])
        footer = self.frame(main, 'bg')
        footer.grid(row=2, column=0, sticky='ew', pady=(11, 0))
        self.status_label = self.label(footer, textvariable=self.status, color='muted', size=10, anchor='w', width=1)
        self.status_label.pack(fill='x', expand=True)
        self.show_page('workspace')

    def build_workspace(self, page):
        page.columnconfigure(0, weight=1)
        page.rowconfigure(1, weight=1)
        top = self.frame(page, 'bg')
        self.input_section = top
        top.grid(row=0, column=0, sticky='ew', pady=(0, 16))
        top.columnconfigure(0, weight=1)
        top.columnconfigure(1, minsize=298)
        input_card = self.frame(top)
        input_card.grid(row=0, column=0, sticky='nsew', padx=(0, 16))
        input_card.columnconfigure(0, weight=1)
        input_card.rowconfigure(2, weight=1)
        heading = self.frame(input_card)
        heading.grid(row=0, column=0, sticky='ew', padx=20, pady=(14, 5))
        self.label(heading, '01', size=10, color='accent', bg=COLORS['pale'], padx=6, pady=3).pack(side='left', padx=(0, 10))
        self.label(heading, '添加链接', size=14, bold=True).pack(side='left')
        self.import_button = ttk.Button(heading, text='导入文件 ↗', command=self.choose_input)
        self.import_button.pack(side='right')
        self.label(input_card, '粘贴链接或分享文案 · 支持 TXT / CSV / Excel', size=10, color='muted').grid(row=1, column=0, sticky='w', padx=20, pady=(0, 12))
        text_frame = self.frame(input_card, 'input', highlightbackground=COLORS['line'], highlightthickness=1)
        text_frame.grid(row=2, column=0, sticky='nsew', padx=20)
        text_frame.columnconfigure(0, weight=1)
        text_frame.rowconfigure(0, weight=1)
        self.input_text = tk.Text(text_frame, height=6, width=20, wrap='word', undo=True,
                                  font=(self.mono_name, 11), padx=12, pady=10, bd=0,
                                  bg=COLORS['input'], fg=COLORS['ink'], insertbackground=COLORS['accent'],
                                  selectbackground='#D6E7D5', highlightthickness=0)
        self.input_text.grid(row=0, column=0, sticky='nsew')
        scrollbar = ttk.Scrollbar(text_frame, command=self.input_text.yview)
        scrollbar.grid(row=0, column=1, sticky='ns')
        self.input_text.configure(yscrollcommand=scrollbar.set)
        self.input_text.bind('<<Modified>>', self.on_input_modified)
        self.placeholder = self.label(text_frame, '在这里粘贴链接…\n\n每行一条，也可以直接粘贴一整段分享文案。',
                                      color='#849187', size=11, justify='left', bg=COLORS['input'])
        self.placeholder.place(x=12, y=12)
        self.placeholder.bind('<Button-1>', lambda _: self.input_text.focus_set())
        tools_row = self.frame(input_card)
        tools_row.grid(row=3, column=0, sticky='ew', padx=14, pady=(5, 2))
        self.paste_button = ttk.Button(tools_row, text='粘贴剪贴板', style='Quiet.TButton', command=self.paste_clipboard)
        self.paste_button.pack(side='left')
        self.clean_button = ttk.Button(tools_row, text='整理链接', style='Quiet.TButton', command=self.clean_input)
        self.clean_button.pack(side='left')
        self.clear_button = ttk.Button(tools_row, text='清空', style='Quiet.TButton', command=self.clear_input)
        self.clear_button.pack(side='right')
        self.label(input_card, textvariable=self.input_summary, color='accent', size=10, bold=True, anchor='w', width=1).grid(row=4, column=0, sticky='ew', padx=20, pady=(0, 3))
        self.input_note_label = self.label(input_card, textvariable=self.input_note, size=9, color='muted', anchor='w', width=1, justify='left', wraplength=480)
        self.input_note_label.grid(row=5, column=0, sticky='ew', padx=20, pady=(0, 12))
        self.input_note_label.bind('<Configure>', lambda e: self.resize_wrapped_label(self.input_note_label, e.width))
        settings = self.frame(top, width=298)
        settings.grid(row=0, column=1, sticky='nsew')
        settings.columnconfigure(0, weight=1)
        title = self.frame(settings)
        title.grid(row=0, column=0, sticky='ew', padx=20, pady=(15, 6))
        self.label(title, '02', size=10, color='accent', bg=COLORS['pale'], padx=6, pady=3).pack(side='left', padx=(0, 10))
        self.label(title, '抓取设置', size=14, bold=True).pack(side='left')
        self.advanced_button = ttk.Button(title, text='更多', style='Quiet.TButton', command=self.show_settings)
        self.advanced_button.pack(side='right')
        modes = self.frame(settings)
        modes.grid(row=1, column=0, sticky='ew', padx=20)
        self.mode_buttons = []
        for text, mode in (('链接状态 + 互动数据', '1'), ('仅检查链接是否可访问', '0')):
            radio = ttk.Radiobutton(modes, text=text, variable=self.mode, value=mode)
            radio.pack(anchor='w')
            self.mode_buttons.append(radio)
        self.line(settings).grid(row=2, column=0, sticky='ew', padx=20, pady=7)
        location = self.frame(settings)
        location.grid(row=3, column=0, sticky='ew', padx=20)
        self.label(location, '结果保存到', size=10, color='muted').pack(side='left')
        self.output_button = ttk.Button(location, text='更改', style='Quiet.TButton', command=self.choose_output)
        self.output_button.pack(side='right')
        self.output_label = self.label(settings, size=10, anchor='w', justify='left', wraplength=250, width=1)
        self.output_label.grid(row=4, column=0, sticky='ew', padx=20, pady=(0, 5))
        self.refresh_output_label()
        self.resume_button = ttk.Checkbutton(settings, text='继续同一批链接的上次进度', variable=self.resume)
        self.resume_button.grid(row=5, column=0, sticky='w', padx=20, pady=(3, 5))
        actions = self.frame(settings)
        actions.grid(row=6, column=0, sticky='ew', padx=20, pady=(5, 12))
        actions.columnconfigure(0, weight=1)
        self.start_button = ttk.Button(actions, text='开始抓取  →', style='Primary.TButton', command=self.start)
        self.start_button.grid(row=0, column=0, sticky='ew')
        self.stop_button = ttk.Button(actions, text='停止', command=self.stop)
        self.stop_button.grid(row=0, column=1, padx=(8, 0))
        self.stop_button.grid_remove()
        self.build_results(page)

    def build_results(self, page):
        card = self.frame(page)
        card.grid(row=1, column=0, sticky='nsew')
        card.columnconfigure(0, weight=1)
        card.rowconfigure(4, weight=1)
        header = self.frame(card)
        header.grid(row=0, column=0, sticky='ew', padx=20, pady=(12, 8))
        self.label(header, '任务结果', size=14, bold=True).pack(side='left', padx=(0, 16))
        self.results_tab = ttk.Button(header, text='结果', style='Selected.Tab.TButton', command=lambda: self.show_result_view('results'))
        self.results_tab.pack(side='left')
        self.logs_tab = ttk.Button(header, text='运行日志', style='Tab.TButton', command=lambda: self.show_result_view('logs'))
        self.logs_tab.pack(side='left')
        self.open_button = ttk.Button(header, text='打开 Excel ↗', command=self.open_result, state='disabled')
        self.open_button.pack(side='right')
        self.export_button = ttk.Button(header, text='另存为', command=self.save_as, state='disabled')
        self.export_button.pack(side='right', padx=(0, 8))
        self.focus_button = ttk.Button(header, text='展开结果', style='Quiet.TButton', command=self.toggle_result_focus)
        self.focus_button.pack(side='right', padx=(0, 8))
        progress_row = self.frame(card)
        progress_row.grid(row=1, column=0, sticky='ew', padx=20)
        stats = self.frame(progress_row)
        stats.pack(side='left')
        for idx, name in enumerate(('已处理', '有数据 / 可访问', '需要关注', '未处理')):
            item = self.frame(stats)
            item.pack(side='left', padx=(0, 24))
            self.label(item, textvariable=self.stat_values[idx], size=21, bold=True, color='warning' if idx == 2 else 'ink').pack(side='left', padx=(0, 7))
            self.label(item, name, size=10, color='muted').pack(side='left')
        self.label(progress_row, textvariable=self.timer_text, size=10, color='muted').pack(side='right')
        bar = self.frame(card)
        bar.grid(row=2, column=0, sticky='ew', padx=20, pady=(6, 6))
        self.progress = ttk.Progressbar(bar, mode='determinate', maximum=1, value=0)
        self.progress.pack(side='left', fill='x', expand=True, ipady=0)
        self.label(bar, textvariable=self.progress_text, size=10, color='muted', width=18, anchor='e').pack(side='right', padx=(12, 0))
        filters = self.frame(card)
        filters.grid(row=3, column=0, sticky='ew', padx=20, pady=(0, 6))
        self.filter_buttons = {}
        for value in ('全部', '需要关注', '已获取数据'):
            button = ttk.Button(filters, text=value, style='Tab.TButton', command=lambda selected=value: self.set_filter(selected))
            button.pack(side='left', padx=(0, 3))
            self.filter_buttons[value] = button
        self.retry_button = ttk.Button(filters, text='重试待处理链接', command=self.retry_attention, state='disabled')
        self.retry_button.pack(side='right')
        self.search_entry = ttk.Entry(filters, textvariable=self.search, width=17)
        self.search_entry.pack(side='right', padx=(0, 10))
        self.label(filters, '搜索', color='muted', size=10).pack(side='right', padx=(4, 7))
        self.table_area = self.frame(card)
        self.table_area.grid(row=4, column=0, sticky='nsew', padx=20)
        self.table_area.columnconfigure(0, weight=1)
        self.table_area.rowconfigure(0, weight=1)
        columns = ('index', 'platform', 'url', 'status', 'like', 'comment', 'favorite', 'share', 'view')
        self.tree = ttk.Treeview(self.table_area, columns=columns, show='headings', selectmode='extended', height=5)
        self.tree.grid(row=0, column=0, sticky='nsew')
        titles = ('#', '平台', '链接', '处理结果', '点赞', '评论', '收藏', '分享', '播放 / 阅读')
        widths = (42, 80, 260, 124, 63, 63, 63, 63, 92)
        for col, title, width in zip(columns, titles, widths):
            self.tree.heading(col, text=title, anchor='w')
            self.tree.column(col, width=width, minwidth=width if col != 'url' else 180, stretch=(col == 'url'), anchor='w')
        for tone, color in (('success', COLORS['ink']), ('warning', COLORS['warning']), ('danger', COLORS['danger']), ('muted', '#89958C')):
            self.tree.tag_configure(tone, foreground=color)
        scroll_y = ttk.Scrollbar(self.table_area, command=self.tree.yview)
        scroll_y.grid(row=0, column=1, sticky='ns')
        scroll_x = ttk.Scrollbar(self.table_area, orient='horizontal', command=self.tree.xview)
        scroll_x.grid(row=1, column=0, sticky='ew')
        self.tree.configure(yscrollcommand=scroll_y.set, xscrollcommand=scroll_x.set)
        self.tree.bind('<<TreeviewSelect>>', self.on_result_selected)
        self.tree.bind('<Double-1>', self.open_selected)
        self.tree.bind('<Return>', self.open_selected)
        self.tree.bind('<Button-3>', self.result_context_menu)
        self.empty_state = self.frame(self.table_area)
        self.empty_state.place(relx=.5, rely=.55, anchor='center')
        self.empty_title = self.label(self.empty_state, '结果会出现在这里', size=15, bold=True)
        self.empty_title.pack(pady=(5, 7))
        self.empty_caption = self.label(self.empty_state, '添加链接并开始抓取，进度与互动数据会实时更新。', color='muted', size=10)
        self.empty_caption.pack(pady=(0, 10))
        self.log_area = self.frame(card)
        self.log_area.grid(row=4, column=0, sticky='nsew', padx=20)
        self.log_area.columnconfigure(0, weight=1)
        self.log_area.rowconfigure(0, weight=1)
        self.log_text = tk.Text(self.log_area, height=5, wrap='word', state='disabled', bd=0, padx=12, pady=10,
                                bg=COLORS['input'], fg=COLORS['ink'], font=(self.mono_name, 10))
        self.log_text.grid(row=0, column=0, sticky='nsew')
        log_scroll = ttk.Scrollbar(self.log_area, command=self.log_text.yview)
        log_scroll.grid(row=0, column=1, sticky='ns')
        self.log_text.configure(yscrollcommand=log_scroll.set)
        self.log_area.grid_remove()
        detail = self.frame(card)
        detail.grid(row=5, column=0, sticky='ew', padx=20, pady=(7, 9))
        detail.columnconfigure(0, weight=1)
        self.detail_label = self.label(detail, textvariable=self.detail_text, color='muted', size=9, anchor='w', justify='left', width=1, wraplength=650)
        self.detail_label.grid(row=0, column=0, sticky='ew')
        self.detail_label.bind('<Configure>', lambda e: self.resize_wrapped_label(self.detail_label, e.width))
        self.copy_button = ttk.Button(detail, text='复制选中链接', style='Quiet.TButton', command=self.copy_selected)
        self.copy_button.grid(row=0, column=1, padx=(8, 0))
        self.set_filter('全部')

    def build_history(self, page):
        page.columnconfigure(0, weight=1)
        page.rowconfigure(0, weight=1)
        card = self.frame(page)
        card.grid(row=0, column=0, sticky='nsew')
        card.columnconfigure(0, weight=1)
        card.rowconfigure(1, weight=1)
        self.label(card, '最近任务', size=15, bold=True).grid(row=0, column=0, sticky='w', padx=22, pady=20)
        self.history_tree = ttk.Treeview(card, columns=('date', 'mode', 'total', 'done', 'state'), show='headings', selectmode='browse')
        self.history_tree.grid(row=1, column=0, sticky='nsew', padx=(22, 0))
        for col, title, width in zip(('date', 'mode', 'total', 'done', 'state'), ('创建时间', '抓取模式', '链接数', '已处理', '任务状态'), (205, 200, 100, 100, 185)):
            self.history_tree.heading(col, text=title, anchor='w')
            self.history_tree.column(col, width=width, anchor='w')
        scroll = ttk.Scrollbar(card, command=self.history_tree.yview)
        scroll.grid(row=1, column=1, sticky='ns', padx=(0, 20))
        self.history_tree.configure(yscrollcommand=scroll.set)
        self.history_tree.bind('<Double-1>', lambda _: self.load_history())
        self.history_empty = self.label(card, '还没有任务记录。完成第一批抓取后，会自动保存在这里。', color='muted')
        self.history_empty.place(relx=.5, rely=.4, anchor='center')
        controls = self.frame(card)
        controls.grid(row=2, column=0, columnspan=2, sticky='ew', padx=22, pady=20)
        self.history_load_button = ttk.Button(controls, text='载入任务 / 继续处理', style='Primary.TButton', command=self.load_history)
        self.history_load_button.pack(side='left')
        ttk.Button(controls, text='打开任务结果', command=self.open_history_result).pack(side='left', padx=10)
        self.label(controls, '双击记录可载入链接和已有结果。', color='muted', size=10).pack(side='right')

    def build_guide(self, page):
        card = self.frame(page)
        card.pack(fill='both', expand=True)
        self.label(card, '从链接到结果，只需三步', size=19, bold=True).pack(anchor='w', padx=30, pady=(28, 8))
        self.label(card, '无需手动配置浏览器驱动。首次抓取时请保持联网。', color='muted').pack(anchor='w', padx=30, pady=(0, 20))
        sections = [
            ('01  添加链接', '直接粘贴链接或分享文案，或导入 TXT、CSV、XLSX。Excel 会读取当前工作表所有列的链接与超链接。\n默认合并完全相同的网址；“更多”中可关闭去重以保留重复行。'),
            ('02  选择范围，开始抓取', '需要点赞、评论等数据时，选择“链接状态 + 互动数据”；只筛查可访问性时，选择“仅检查链接”。\n暂停时点击“停止”，等待当前页面结束和结果保存后即可关闭。'),
            ('03  筛查结果，导出 Excel', '进度统计与结果表实时更新。“需要关注”集中显示空数据、验证、受限、删除和失败的链接。\n选中一行查看处理建议，双击打开原网页；完成后直接打开 Excel，或另存一份结果。'),
            ('读懂结果，避免误判', '“—”表示没有获取到这一项，0 表示读到了零。“暂无互动数据”不代表链接已失效。\n“需验证 / 访问受限”需要人工核实；“不支持”表示本工具没有判断该链接是否有效。'),
            ('继续任务与本机记录', '任务记录保留每批链接及其进度。载入同一批链接后，保持“继续上次进度”即可跳过已完成项。\n想获取更新的互动数，请取消“继续上次进度”，重新抓取；本地预览版使用独立的数据目录。'),
        ]
        for title, text in sections:
            self.line(card).pack(fill='x', padx=30, pady=(0, 12))
            self.label(card, title, size=12, bold=True).pack(anchor='w', padx=30, pady=(0, 6))
            self.label(card, text, size=10, color='muted', justify='left', anchor='w', wraplength=800).pack(anchor='w', padx=30, pady=(0, 16))
        shortcut = '⌘' if platform.system() == 'Darwin' else 'Ctrl'
        self.label(card, f'快捷键   {shortcut} O 导入文件     ·     {shortcut} Enter 开始抓取     ·     {shortcut} Shift S 另存结果', size=10, color='accent').pack(anchor='w', padx=30, pady=(0, 15))

    def show_page(self, name):
        self.current_page = name
        self.pages[name].tkraise()
        titles = dict(workspace=('链接工作台', '让一批链接，变成一份清楚的结果。'),
                      history=('任务记录', '每次抓取都有记录，随时回来接着处理。'),
                      guide=('使用指南', '更少操作，更清楚地理解每一条结果。'))
        title, caption = titles[name]
        self.page_title.configure(text=title)
        self.page_caption.configure(text=caption)
        for key, button in self.nav_buttons.items():
            button.configure(style='Active.Nav.TButton' if key == name else 'Nav.TButton')
        if name == 'history':
            self.refresh_history()

    @staticmethod
    def resize_wrapped_label(label, width):
        target = max(100, width)
        if int(label.cget('wraplength')) != target:
            label.configure(wraplength=target)

    def read_preferences(self):
        try:
            value = json.loads((self.data_dir / 'preferences.json').read_text(encoding='utf-8'))
            return value if isinstance(value, dict) else {}
        except (OSError, ValueError):
            return {}

    def save_preferences(self):
        try:
            write_private_file(self.data_dir / 'preferences.json', json.dumps(dict(
                output_dir=self.output_path_var.get(), mode=self.mode.get(), resume=self.resume.get(),
                deduplicate=self.deduplicate.get(), workers=self.toutiao_workers.get()), ensure_ascii=False))
        except (OSError, tk.TclError) as exc:
            self.notice(f'设置未保存：{exc}', 'warning')

    def notice(self, text, tone='muted'):
        self.status.set(str(text).replace('\n', ' ')[:190])
        self.status_label.configure(fg=COLORS.get(tone, COLORS['muted']))

    def select_all(self, event):
        if isinstance(event.widget, tk.Text):
            event.widget.tag_add('sel', '1.0', 'end-1c')
            return 'break'

    def on_input_modified(self, _=None):
        if not self.input_text.edit_modified():
            return
        self.input_text.edit_modified(False)
        if self._edit_job:
            self.after_cancel(self._edit_job)
        self._edit_job = self.after(180, self.refresh_input)

    def refresh_input(self):
        self._edit_job = None
        raw = self.input_text.get('1.0', 'end-1c')
        if raw:
            self.placeholder.place_forget()
        else:
            self.placeholder.place(x=12, y=12)
        batch = parse_links(raw, self.deduplicate.get())
        platform_count = len([key for key in batch.platforms if key != '不支持'])
        summary = f'{len(batch.links)} 条链接'
        if platform_count:
            summary += f'   ·   {platform_count} 个平台'
        if batch.duplicates:
            summary += f'   ·   {"合并" if self.deduplicate.get() else "保留"} {batch.duplicates} 条重复'
        if batch.unsupported:
            summary += f'   ·   {batch.unsupported} 条暂不支持'
        self.input_summary.set(summary)
        known = ' / '.join(f'{name} {count}' for name, count in batch.platforms.most_common(5))
        note = known or '支持从分享文案中提取网址，也可以直接粘贴 Excel 单元格。'
        if batch.ignored_lines:
            note += f'  ·  跳过 {batch.ignored_lines} 行非网址内容'
        if batch.unsupported:
            note += '  ·  不支持的网址会保留并标注'
        self.input_note.set(note)
        if not self.running:
            self.start_button.configure(state='normal' if batch.links else 'disabled',
                                        text=f'开始抓取 {len(batch.links)} 条  →' if batch.links else '开始抓取  →')
        return batch

    def set_input(self, text):
        if self.result_focus:
            self.toggle_result_focus()
        self.input_text.configure(state='normal')
        self.input_text.delete('1.0', 'end')
        self.input_text.insert('1.0', text)
        self.input_text.edit_reset()
        self.refresh_input()

    def clear_input(self):
        if not self.running:
            self.set_input('')
            self.input_path.set('')
            self.notice('已清空输入；已完成的结果仍保留在任务记录中。')

    def clean_input(self):
        if self.running:
            return
        batch = self.refresh_input()
        if batch.links:
            self.set_input('\n'.join(batch.links))
            self.notice(f'已整理为 {len(batch.links)} 条链接；合并 {batch.duplicates if self.deduplicate.get() else 0} 条重复，跳过 {batch.ignored_lines} 行非网址内容。', 'accent')

    def paste_clipboard(self):
        if self.running:
            return
        try:
            text = self.clipboard_get()
            if self.input_text.get('1.0', 'end-1c').strip():
                self.input_text.insert('end', '\n')
            self.input_text.insert('end', text)
            self.input_text.see('end')
            self.input_text.focus_set()
            self.refresh_input()
        except tk.TclError:
            self.notice('剪贴板中没有可粘贴的文字。', 'warning')

    def choose_input(self):
        if self.running:
            return
        path = filedialog.askopenfilename(parent=self, title='导入链接文件', filetypes=[('链接文件', '*.txt *.csv *.xlsx'), ('所有文件', '*.*')])
        if path:
            self.import_file(path)

    def import_file(self, path):
        if self.running:
            return
        try:
            values = read_links(path)
            # Extract URLs from cells before display so captions and headers are not sent to the engine.
            imported = parse_links('\n'.join(values), deduplicate=False)
            if not imported.links:
                self.notice('文件中没有找到完整的 http / https 链接，请检查工作表或文件内容。', 'warning')
                return
            text = '\n'.join(imported.links)
            existing = self.input_text.get('1.0', 'end-1c').strip()
            self.set_input(existing + '\n' + text if existing else text)
            self.input_path.set(str(path))
            self.show_page('workspace')
            self.notice(f'已追加导入 {len(imported.links)} 条网址：{Path(path).name}。重复链接将按设置处理。', 'accent')
        except Exception as exc:
            self.notice(f'导入失败：{exc}。请确认文件可读取且没有加密。', 'danger')

    def refresh_output_label(self):
        path = Path(self.output_path_var.get()).expanduser()
        try:
            display = '~/' + str(path.relative_to(Path.home()))
        except ValueError:
            display = str(path)
        self.output_label.configure(text=display if len(display) < 64 else '…/' + '/'.join(path.parts[-2:]))

    def choose_output(self):
        if self.running:
            return
        initial = Path(self.output_path_var.get()).expanduser()
        path = filedialog.askdirectory(parent=self, title='选择结果保存文件夹', initialdir=str(initial if initial.is_dir() else Path.home()))
        if path:
            self.output_path_var.set(path)
            self.refresh_output_label()
            self.save_preferences()

    def show_settings(self):
        if self.running:
            return
        dialog = tk.Toplevel(self)
        dialog.title('更多设置')
        dialog.configure(bg=COLORS['surface'])
        dialog.geometry('470x360')
        dialog.resizable(False, False)
        dialog.transient(self)
        self.label(dialog, '保持简单，也保留选择', size=17, bold=True).pack(anchor='w', padx=26, pady=(24, 16))
        ttk.Checkbutton(dialog, text='自动合并完全相同的链接', variable=self.deduplicate).pack(anchor='w', padx=26)
        self.label(dialog, '关闭后保留重复行；链接参数与分享凭证不会被删改。', color='muted', size=10).pack(anchor='w', padx=26, pady=(0, 15))
        self.label(dialog, '处理速度', size=12, bold=True).pack(anchor='w', padx=26)
        for text, value in (('稳妥 · 头条单页处理', 1), ('标准 · 头条同时处理 2 页（推荐）', 2), ('较快 · 头条同时处理 3 页', 3)):
            ttk.Radiobutton(dialog, text=text, variable=self.toutiao_workers, value=value).pack(anchor='w', padx=26)
        self.label(dialog, '抖音、快手保持单页处理，总浏览器数不超过 4。', size=10, color='muted').pack(anchor='w', padx=26, pady=(7, 12))
        def close():
            self.save_preferences()
            dialog.destroy()
        ttk.Button(dialog, text='完成', style='Primary.TButton', command=close).pack(anchor='e', padx=26)
        dialog.protocol('WM_DELETE_WINDOW', close)
        dialog.grab_set()

    def set_running(self, value):
        self.running = value
        state = 'disabled' if value else 'normal'
        self.input_text.configure(state=state)
        for widget in [self.import_button, self.paste_button, self.clear_button, self.clean_button,
                       self.advanced_button, self.output_button, self.resume_button, self.history_load_button,
                       *self.mode_buttons]:
            widget.configure(state=state)
        if value:
            self.start_button.configure(state='disabled', text='正在抓取…')
            self.stop_button.configure(state='normal', text='停止')
            self.stop_button.grid()
            self.retry_button.configure(state='disabled')
        else:
            self.stop_button.grid_remove()
            self.refresh_input()
            self.update_result_actions()

    def start(self):
        if self.running:
            return
        batch = self.refresh_input()
        if not batch.links:
            self.notice('请先粘贴链接，或导入包含链接的文件。', 'warning')
            self.input_text.focus_set()
            return
        output_dir = Path(self.output_path_var.get()).expanduser()
        mode = self.mode.get()
        try:
            workers = int(self.toutiao_workers.get())
            if workers not in (1, 2, 3):
                raise ValueError('处理速度应为 1、2 或 3')
            output_dir.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryFile(dir=output_dir):
                pass
            self.data_dir.mkdir(parents=True, exist_ok=True)
            if not remove_legacy_captcha_credentials(self.data_dir / 'yzm.txt'):
                raise OSError('无法清理旧版验证码配置')
            signature = engine.opt_signature(batch.links, mode)
            previous = self.store.latest_checkpoint(signature) if self.resume.get() else None
            record = self.store.create(batch.links, mode, signature, output_dir)
            task_dir = self.store.directory(record)
            write_private_file(task_dir / 'urls.txt', '\n'.join(batch.links) + '\n')
            write_private_file(task_dir / 'settings.txt', f'只判断链接or抓取互动数和链接判断(0/1):{mode}\n')
            if previous:
                shutil.copy2(previous, task_dir / '链接判断结果_进行中.json')
        except (OSError, ValueError, tk.TclError) as exc:
            self.notice(f'无法开始：{exc}。请检查输入及保存目录权限。', 'danger')
            return
        self.save_preferences()
        self.task = record
        self.run_links = list(batch.links)
        self.run_mode = mode
        self.results = {}
        self.output_path = Path(record['output'])
        self.export_saved = False
        self.started_at = time.monotonic()
        self.elapsed = 0
        self.stopping = False
        self.log_lines.clear()
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        self.log_text.configure(state='disabled')
        self.search.set('')
        self.set_filter('全部')
        self.show_result_view('results')
        self.show_page('workspace')
        self.set_running(True)
        self.update_stats()
        self.progress_text.set(f'准备中 · 0 / {len(batch.links)}')
        self.notice('正在准备浏览器；首次使用可能需要下载组件，请保持联网。', 'accent')
        self.detail_text.set('结果将逐条更新；“—”表示未获取到数据，0 表示读到的数值为零。')
        self.append_log(f'新任务：{len(batch.links)} 条链接；{"继续上次进度" if self.resume.get() else "重新抓取全部"}。')
        engine.OPT_BASE_DIR = task_dir
        os.environ.setdefault('SE_CACHE_PATH', str(self.data_dir / 'selenium-cache'))
        engine.OPT_STOP_EVENT.clear()
        args = ['--input', str(task_dir / 'urls.txt'), '--output', str(self.output_path),
                '--toutiao-workers', str(workers), '--douyin-workers', '1', '--other-workers', '1', '--checkpoint-every', '10']
        if self.resume.get():
            args.append('--resume')
        self.worker_thread = threading.Thread(target=self.run_engine, args=(args,), daemon=True)
        self.worker_thread.start()

    def run_engine(self, args):
        writer = QueueWriter(self.events)
        try:
            with contextlib.redirect_stdout(writer), contextlib.redirect_stderr(writer):
                return_code = engine.opt_main(args, on_event=lambda kind, payload: self.events.put((kind, payload)))
            self.events.put(('done', return_code))
        except Exception as exc:
            self.events.put(('fatal', f'{type(exc).__name__}: {exc}'))

    def stop(self):
        if self.running and not self.stopping:
            self.stopping = True
            engine.OPT_STOP_EVENT.set()
            self.notice('正在停止：等待当前浏览器操作结束，然后保存已完成结果。', 'warning')
            self.stop_button.configure(state='disabled', text='停止中')
            self.start_button.configure(text='正在停止…')

    def drain_events(self):
        changed = False
        for _ in range(160):
            try:
                event, value = self.events.get_nowait()
            except queue.Empty:
                break
            if event == 'log':
                self.append_log(value)
            elif event == 'prepared':
                self.results = value['restored']
                changed = True
                if self.results:
                    self.append_log(f'恢复了 {len(self.results)} 条结果；这些数据来自上次抓取。')
            elif event == 'result':
                self.results[value['index']] = value['row']
                changed = True
            elif event == 'phase':
                if not self.stopping or value['text'].startswith('正在保存'):
                    self.notice(value['text'], 'accent')
            elif event == 'saved':
                self.export_saved = Path(value['path']).is_file()
            elif event == 'done':
                self.finish(value)
            elif event == 'fatal':
                self.append_log(value)
                self.finish(1, error=value)
        if changed:
            self.update_stats()
            self.schedule_table()
        self.after(100, self.drain_events)

    def append_log(self, text):
        stamped = f'{time.strftime("%H:%M:%S")}  {text}'
        self.log_lines.append(stamped)
        if len(self.log_lines) > 1200:
            self.log_lines = self.log_lines[-1200:]
        self.log_text.configure(state='normal')
        at_bottom = self.log_text.yview()[1] >= .98
        self.log_text.insert('end', stamped + '\n')
        line_count = int(self.log_text.index('end-1c').split('.')[0])
        if line_count > 1201:
            self.log_text.delete('1.0', f'{line_count - 1200}.0')
        if at_bottom:
            self.log_text.see('end')
        self.log_text.configure(state='disabled')

    def tick(self):
        if self.running and self.started_at is not None:
            self.elapsed = int(time.monotonic() - self.started_at)
            self.timer_text.set(f'已用时 {self.elapsed // 60:02d}:{self.elapsed % 60:02d}')
        self.after(500, self.tick)

    def update_stats(self):
        done = len(self.results)
        total = len(self.run_links)
        infos = [describe_result(row, self.run_mode) for row in self.results.values()]
        counts = (done, sum(info.tone == 'success' for info in infos), sum(info.review for info in infos), max(0, total - done))
        for var, value in zip(self.stat_values, counts):
            var.set(str(value))
        self.progress.configure(maximum=max(1, total), value=done)
        if total:
            self.progress_text.set(f'{round(done / total * 100)}% · {done} / {total}')
        else:
            self.progress_text.set('等待开始')
        self.update_result_actions()

    def finish(self, code, error=None):
        self.elapsed = int(time.monotonic() - self.started_at) if self.started_at else 0
        self.timer_text.set(f'用时 {self.elapsed // 60:02d}:{self.elapsed % 60:02d}')
        self.set_running(False)
        completed, total = len(self.results), len(self.run_links)
        review = sum(describe_result(row, self.run_mode).review for row in self.results.values())
        if error or not self.export_saved:
            state = '结果未保存'
            self.notice(f'未能保存 Excel：{error or "没有收到保存成功确认"}。可点击“另存为”保存当前结果。', 'danger')
        elif self.stopping or completed < total or code:
            state = '已停止' if self.stopping else '部分完成'
            self.notice(f'{state} · 已处理 {completed}/{total} 条，Excel 已保存。可从任务记录继续。', 'warning')
        elif review:
            state = '完成 · 需关注'
            self.notice(f'已完成并保存 · {total} 条链接中有 {review} 条需要关注，可切换筛选查看原因。', 'warning')
        else:
            state = '已完成'
            self.notice(f'已完成 · {total} 条链接的结果已保存，可直接打开 Excel。', 'accent')
        if self.task:
            self.task.update(state=state, completed=completed, saved=self.export_saved,
                             elapsed=self.elapsed, attention=review, finished_at=time.strftime('%Y-%m-%d %H:%M:%S'))
            try:
                self.store.save(self.task)
                write_private_file(self.store.directory(self.task) / '运行日志.txt', '\n'.join(self.log_lines))
            except OSError as exc:
                self.notice(f'{self.status.get()}；任务记录保存失败：{exc}', 'warning')
        self.update_stats()
        self.schedule_table()
        if self.current_page == 'history':
            self.refresh_history()
        if self.close_when_done and self.export_saved:
            self.after_idle(self.close_app)
        self.close_when_done = False

    def retry_candidates(self):
        selected = []
        for index, url in enumerate(self.run_links, 1):
            row = self.results.get(index)
            if row is None or row.get('链接状态') in engine.OPT_RETRYABLE_STATUSES or describe_result(row, self.run_mode).label == '暂无互动数据':
                selected.append(url)
        return selected

    def update_result_actions(self):
        self.open_button.configure(state='normal' if self.export_saved and self.output_path and self.output_path.is_file() else 'disabled')
        self.export_button.configure(state='normal' if self.run_links else 'disabled')
        self.retry_button.configure(state='normal' if not self.running and self.retry_candidates() else 'disabled')

    def retry_attention(self):
        if self.running:
            return
        links = self.retry_candidates()
        if not links:
            return
        self.set_input('\n'.join(links))
        self.mode.set(self.run_mode)
        self.resume.set(False)
        self.notice(f'已载入 {len(links)} 条待处理链接。建议稍后点击开始，避免连续请求触发平台限制。', 'warning')
        self.input_text.focus_set()

    def set_filter(self, value):
        self.current_filter = value
        for key, button in self.filter_buttons.items():
            button.configure(style='Selected.Tab.TButton' if key == value else 'Tab.TButton')
        self.schedule_table()

    def schedule_table(self):
        if not self._table_job:
            self._table_job = self.after(80, self.render_table)

    def render_table(self):
        self._table_job = None
        search = self.search.get().strip().lower()
        visible = []
        for index, url in enumerate(self.run_links, 1):
            row = self.results.get(index, {'链接': url, '链接状态': '未处理'})
            info = describe_result(row, self.run_mode)
            if self.current_filter == '需要关注' and not info.review:
                continue
            if self.current_filter == '已获取数据' and info.tone != 'success':
                continue
            platform_label = platform_name(url)
            if search and search not in f'{url} {platform_label} {info.label}'.lower():
                continue
            iid = str(index)
            visible.append(iid)
            values = (index, platform_label, url, info.label, *(metric_text(row.get(key)) for key in METRICS))
            fingerprint = (values, info.tone)
            if not self.tree.exists(iid):
                self.tree.insert('', 'end', iid=iid, values=values, tags=(info.tone,))
            elif self._rendered.get(iid) != fingerprint:
                self.tree.item(iid, values=values, tags=(info.tone,))
            self._rendered[iid] = fingerprint
        visible_set = set(visible)
        for iid in self.tree.get_children():
            if iid not in visible_set:
                self.tree.delete(iid)
                self._rendered.pop(iid, None)
        for position, iid in enumerate(visible):
            self.tree.move(iid, '', position)
        if visible:
            self.empty_state.place_forget()
        else:
            self.empty_title.configure(text='没有符合条件的结果' if self.run_links else '结果会出现在这里')
            self.empty_caption.configure(text='试试其他筛选或搜索内容。' if self.run_links else '添加链接并开始抓取，进度与互动数据会实时更新。')
            self.empty_state.place(relx=.5, rely=.55, anchor='center')

    def show_result_view(self, name):
        self.result_view = name
        self.results_tab.configure(style='Selected.Tab.TButton' if name == 'results' else 'Tab.TButton')
        self.logs_tab.configure(style='Selected.Tab.TButton' if name == 'logs' else 'Tab.TButton')
        if name == 'results':
            self.log_area.grid_remove()
            self.table_area.grid()
        else:
            self.table_area.grid_remove()
            self.log_area.grid()

    def toggle_result_focus(self):
        self.result_focus = not self.result_focus
        if self.result_focus:
            self.input_section.grid_remove()
            self.focus_button.configure(text='返回输入')
        else:
            self.input_section.grid()
            self.focus_button.configure(text='展开结果')

    def selected_urls(self):
        return [self.run_links[int(iid) - 1] for iid in self.tree.selection() if 0 < int(iid) <= len(self.run_links)]

    def on_result_selected(self, _=None):
        selected = self.tree.selection()
        if selected:
            row = self.results.get(int(selected[0]), {'链接状态': '未处理'})
            self.detail_text.set(describe_result(row, self.run_mode).hint)

    def open_selected(self, event=None):
        if event is not None and hasattr(event, 'y') and event.type == tk.EventType.ButtonPress:
            if self.tree.identify_region(event.x, event.y) not in ('cell', 'tree'):
                return
        urls = self.selected_urls()
        if urls and valid_url(urls[0]):
            webbrowser.open(urls[0])

    def copy_selected(self):
        urls = self.selected_urls()
        if urls:
            self.clipboard_clear()
            self.clipboard_append('\n'.join(urls))
            self.notice(f'已复制 {len(urls)} 条链接。', 'accent')
        else:
            self.notice('请先在结果表中选择链接。')

    def result_context_menu(self, event):
        iid = self.tree.identify_row(event.y)
        if not iid:
            return
        if iid not in self.tree.selection():
            self.tree.selection_set(iid)
        menu = tk.Menu(self, tearoff=False)
        menu.add_command(label='在浏览器打开', command=self.open_selected)
        menu.add_command(label='复制选中链接', command=self.copy_selected)
        menu.tk_popup(event.x_root, event.y_root)

    def open_path(self, path):
        try:
            path = Path(path)
            if not path.exists():
                self.notice('文件已移动或删除。已有结果可以点击“另存为”重新导出。', 'warning')
                return
            if platform.system() == 'Windows':
                os.startfile(str(path))
            else:
                subprocess.run(['open' if platform.system() == 'Darwin' else 'xdg-open', str(path)], check=True)
        except (OSError, subprocess.SubprocessError) as exc:
            self.notice(f'无法打开文件：{exc}', 'danger')

    def open_result(self):
        if self.output_path and self.export_saved:
            self.open_path(self.output_path)

    def open_output_dir(self):
        self.open_path(Path(self.output_path_var.get()).expanduser())

    def save_as(self):
        if not self.run_links:
            return
        path = filedialog.asksaveasfilename(parent=self, title='另存当前结果', defaultextension='.xlsx',
                    initialdir=self.output_path_var.get(), initialfile=f'链接热度结果_{time.strftime("%Y%m%d-%H%M%S")}.xlsx',
                    filetypes=[('Excel 工作簿', '*.xlsx')])
        if not path:
            return
        if self.running and self.output_path and Path(path).resolve() == self.output_path.resolve():
            self.notice('任务仍在运行，请选择另一个文件名保存当前快照。', 'warning')
            return
        try:
            snapshot = {index: dict(row) for index, row in self.results.items()}
            write_result_workbook(path, snapshot, self.run_links, self.run_mode)
            if not self.running and not self.export_saved:
                self.output_path = Path(path)
                self.export_saved = True
                if self.task:
                    self.task.update(output=str(path), saved=True, state='手动保存')
                    self.store.save(self.task)
                self.update_result_actions()
            self.notice(f'已另存 {len(snapshot)} 条已处理结果；未处理链接也已标注：{Path(path).name}', 'accent')
        except OSError as exc:
            self.notice(f'另存失败：{exc}。请检查文件是否正被 Excel 占用。', 'danger')

    def refresh_history(self):
        selected = self.history_tree.selection()
        self.history_tree.delete(*self.history_tree.get_children())
        records = self.store.records()
        self._history_records = {record['id']: record for record in records}
        for record in records:
            state = record.get('state', '未知')
            if state == '准备中':
                state = '正在处理' if self.running and self.task and record['id'] == self.task['id'] else '可恢复 / 未完成'
            if record.get('saved') and not Path(record.get('output', '')).is_file():
                state = '结果文件已移动'
            self.history_tree.insert('', 'end', iid=record['id'], values=(record['created_at'],
                '链接 + 互动数据' if record['mode'] == '1' else '仅检查链接', record['total'], record['completed'], state))
        if selected and selected[0] in self._history_records:
            self.history_tree.selection_set(selected[0])
        if records:
            self.history_empty.place_forget()
        else:
            self.history_empty.place(relx=.5, rely=.4, anchor='center')

    def selected_history(self):
        selection = self.history_tree.selection()
        if not selection:
            self.notice('请先选择一条任务记录。')
            return None
        return self._history_records.get(selection[0])

    def load_history(self):
        if self.running:
            self.notice('当前任务仍在运行，请先停止并等待保存，再载入其他任务。', 'warning')
            return
        record = self.selected_history()
        if not record:
            return
        self.task = record
        self.run_links = list(record['links'])
        self.run_mode = record['mode']
        self.results = self.store.results(record)
        self.output_path = Path(record['output'])
        self.export_saved = bool(record.get('saved') and self.output_path.is_file())
        self.set_input('\n'.join(self.run_links))
        self.mode.set(self.run_mode)
        self.resume.set(True)
        self.search.set('')
        self.set_filter('全部')
        self.show_result_view('results')
        self.show_page('workspace')
        self.elapsed = record.get('elapsed', 0)
        self.timer_text.set(f'上次用时 {self.elapsed // 60:02d}:{self.elapsed % 60:02d}')
        self.log_text.configure(state='normal')
        self.log_text.delete('1.0', 'end')
        try:
            previous_logs = (self.store.directory(record) / '运行日志.txt').read_text(encoding='utf-8')
        except OSError:
            previous_logs = '此任务尚无已保存的日志。'
        self.log_text.insert('1.0', previous_logs)
        self.log_text.configure(state='disabled')
        self.update_stats()
        self.notice(f'已载入 {record["created_at"]} 的任务。点击开始可继续；更新数据请取消“继续上次进度”。', 'accent')

    def open_history_result(self):
        record = self.selected_history()
        if record:
            if record.get('saved'):
                self.open_path(record['output'])
            else:
                self.notice('此任务没有保存成功的 Excel；载入任务后可另存当前结果。', 'warning')

    def close_app(self):
        if self.running:
            if messagebox.askyesno(APP_TITLE, '任务仍在运行。要完成当前页面、保存已有结果后自动退出吗？', parent=self):
                self.close_when_done = True
                self.stop()
            return
        self.save_preferences()
        self.destroy()

    def destroy(self):
        # Cancel Tcl timers before destroying widgets, including queued render jobs.
        with contextlib.suppress(tk.TclError):
            for timer in self.tk.splitlist(self.tk.call('after', 'info')):
                self.after_cancel(timer)
        super().destroy()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=APP_TITLE)
    parser.add_argument('--data-dir', type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--output-dir', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    UrlHeatApp(data_dir=args.data_dir, output_dir=args.output_dir).mainloop()
