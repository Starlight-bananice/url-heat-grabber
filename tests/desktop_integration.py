"""Run explicitly on a desktop: python tests/desktop_integration.py.

Uses the real Tk event loop, task runner, checkpoint and Excel exporter, with a
controlled page worker. No browser/network access or OS-level event injection.
"""
import json
import os
import platform
import subprocess
import sys
import tkinter as tk
import time
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import engine
from app import UrlHeatApp


class DesktopFlowTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / 'data').mkdir()
        (self.root / 'data/preferences.json').write_text(json.dumps({'deduplicate': True}), encoding='utf-8')
        self.app = UrlHeatApp(self.root / 'data', self.root / 'output')
        self.app.withdraw()
        self.errors = []
        self.app.report_callback_exception = lambda *error: self.errors.append(str(error))

    def tearDown(self):
        self.app.destroy()
        self.temp.cleanup()
        engine.OPT_STOP_EVENT.clear()

    def wait_done(self):
        deadline = time.monotonic() + 8
        while self.app.running and time.monotonic() < deadline:
            self.app.update()
            time.sleep(.015)
        self.assertFalse(self.app.running)
        # Flush a pending table render without relying on scraping speed.
        self.app.render_table()
        self.app.update()
        self.assertEqual(self.errors, [])

    @staticmethod
    def fake_worker(bucket, group, driver_path, mode, system, config, callback):
        for index, url in bucket:
            if engine.OPT_STOP_EVENT.is_set():
                break
            row = engine.opt_result_row(url, metrics=('0', '2', '', '', '100')) if index == 1 else engine.opt_result_row(url, status='需验证')
            callback(index, row)

    def test_real_task_lifecycle_filter_history_and_resume(self):
        self.app.set_input('标题\nhttps://weibo.com/1/1\nhttps://weibo.com/1/1\nhttps://weibo.com/1/2\nhttps://example.com/unsupported')
        with patch('engine.opt_worker', self.fake_worker):
            self.app.start()
            self.assertEqual(str(self.app.input_text.cget('state')), 'disabled')
            self.wait_done()
        self.assertTrue(self.app.export_saved)
        self.assertTrue(self.app.output_path.is_file())
        self.assertEqual([var.get() for var in self.app.stat_values], ['4', '2', '2', '0'])
        self.assertEqual(self.app.task['state'], '完成 · 需关注')
        self.app.set_filter('需要关注')
        self.app.render_table()
        self.assertEqual(len(self.app.tree.get_children()), 2)
        self.app.search.set('example.com')
        self.app.render_table()
        self.assertEqual(len(self.app.tree.get_children()), 1)
        self.app.show_page('history')
        self.app.history_tree.selection_set(self.app.task['id'])
        self.app.load_history()
        self.assertEqual(len(self.app.results), 4)
        self.assertTrue(self.app.resume.get())
        restored = self.app.task['id']
        with patch('engine.opt_worker', self.fake_worker):
            self.app.start()
            self.wait_done()
        self.assertNotEqual(self.app.task['id'], restored)
        self.assertEqual(len(self.app.store.records()), 2)
        self.assertEqual(len(self.app.results), 4)

    def test_export_failure_is_never_reported_as_saved(self):
        self.app.set_input('https://example.com/a')
        with patch('engine.opt_save_xlsx', side_effect=PermissionError('QA simulated file lock')):
            self.app.start()
            self.wait_done()
        self.assertFalse(self.app.export_saved)
        self.assertEqual(str(self.app.open_button.cget('state')), 'disabled')
        self.assertEqual(self.app.task['state'], '结果未保存')
        self.assertIn('未能保存', self.app.status.get())
        self.assertEqual(len(self.app.results), 1)

    def test_safe_stop_preserves_pending_links_and_enables_retry(self):
        self.app.set_input('https://weibo.com/1/1\nhttps://weibo.com/1/2')
        def slow_worker(bucket, group, driver_path, mode, system, config, callback):
            engine.OPT_STOP_EVENT.wait(2)
            index, url = bucket[0]
            callback(index, engine.opt_result_row(url, metrics=('2', '', '', '', '')))
        with patch('engine.opt_worker', slow_worker):
            self.app.start()
            self.assertEqual(str(self.app.history_delete_button.cget('state')), 'disabled')
            with patch.object(self.app.store, 'delete_records') as delete:
                self.app.delete_history_records([self.app.task], True)
                delete.assert_not_called()
            self.app.stop()
            self.wait_done()
        self.assertEqual(self.app.task['state'], '已停止')
        self.assertTrue(self.app.export_saved)
        self.assertEqual(self.app.retry_candidates(), ['https://weibo.com/1/2'])
        self.app.toggle_result_focus()
        self.assertTrue(self.app.result_focus)
        self.app.retry_attention()
        self.assertFalse(self.app.result_focus)
        self.assertEqual(self.app.refresh_input().links, ['https://weibo.com/1/2'])
        self.assertFalse(self.app.resume.get())

    def test_bad_output_directory_is_an_inline_error_and_keeps_input(self):
        path = self.root / 'file'
        path.write_text('existing file')
        self.app.output_path_var.set(str(path))
        self.app.set_input('https://example.com/a')
        self.app.start()
        self.assertFalse(self.app.running)
        self.assertIn('无法开始', self.app.status.get())
        self.assertEqual(self.app.refresh_input().links, ['https://example.com/a'])

    def test_layout_at_minimum_size(self):
        self.app.deiconify()
        self.app.geometry('1080x760')
        self.app.update()
        if platform.system() == 'Windows' and os.environ.get('GITHUB_ACTIONS'):
            from windows_bundle import capture_window
            evidence = Path('qa/windows-bundle')
            evidence.mkdir(parents=True, exist_ok=True)
            capture_window(self.app.title(), evidence / 'windows-minimum.png')
            layout = {'font': self.app.font_name, 'scaling': self.app.tk.call('tk', 'scaling'),
                      'window': [self.app.winfo_width(), self.app.winfo_height()],
                      'table_height': self.app.tree.winfo_height(),
                      'input_height': self.app.input_section.winfo_height()}
            (evidence / 'layout.json').write_text(json.dumps(layout, indent=2), encoding='utf-8')
            print(json.dumps(layout))
        for widget in (self.app.start_button, self.app.open_button, self.app.tree, self.app.status_label):
            self.assertTrue(widget.winfo_ismapped())
            self.assertLessEqual(widget.winfo_rootx() + widget.winfo_width(), self.app.winfo_rootx() + self.app.winfo_width() + 1)
            self.assertLessEqual(widget.winfo_rooty() + widget.winfo_height(), self.app.winfo_rooty() + self.app.winfo_height() + 1)
        self.assertGreater(self.app.tree.winfo_height(), 100)

    def test_no_data_is_neutral_and_old_history_status_is_recalculated(self):
        self.app.set_input('https://weibo.com/1/1')
        def empty_worker(bucket, group, driver_path, mode, system, config, callback):
            for index, url in bucket:
                callback(index, engine.opt_result_row(url))
        with patch('engine.opt_worker', empty_worker):
            self.app.start()
            self.wait_done()
        self.assertEqual([var.get() for var in self.app.stat_values], ['1', '0', '0', '0'])
        self.assertEqual(self.app.task['state'], '已完成')
        self.assertEqual(self.app.tree.item('1', 'tags'), ('muted',))
        self.assertEqual(self.app.retry_candidates(), [])
        self.app.set_filter('需要关注')
        self.app.render_table()
        self.assertEqual(self.app.tree.get_children(), ())
        self.app.task.update(state='完成 · 需关注', attention=1)
        self.app.store.save(self.app.task)
        self.app.show_page('history')
        self.assertEqual(self.app.history_tree.item(self.app.task['id'], 'values')[-1], '已完成')

    @staticmethod
    def descendants(parent):
        for child in parent.winfo_children():
            yield child
            yield from DesktopFlowTests.descendants(child)

    def test_history_delete_dialog_cancel_and_multi_selection(self):
        records = [self.app.store.create(['https://example.com/a'], '1', 'test', self.root) for _ in range(2)]
        for record in records:
            Path(record['output']).write_bytes(b'exported result')
        self.app.show_page('history')
        self.app.history_tree.selection_set([record['id'] for record in records])
        self.app.show_delete_history()
        dialog = next(widget for widget in self.app.winfo_children() if isinstance(widget, tk.Toplevel))
        cancel = next(widget for widget in self.descendants(dialog) if widget.winfo_class() == 'TButton' and widget.cget('text') == '取消')
        cancel.invoke()
        self.assertEqual(len(self.app.store.records()), 2)
        self.app.show_delete_history()
        dialog = next(widget for widget in self.app.winfo_children() if isinstance(widget, tk.Toplevel))
        checkbox = next(widget for widget in self.descendants(dialog) if widget.winfo_class() == 'TCheckbutton')
        self.assertFalse(dialog.getvar(checkbox.cget('variable')))
        checkbox.invoke()
        if platform.system() == 'Windows' and os.environ.get('GITHUB_ACTIONS'):
            from windows_bundle import capture_window
            self.app.deiconify()
            self.app.update()
            evidence = Path('qa/windows-bundle')
            evidence.mkdir(parents=True, exist_ok=True)
            capture_window('删除任务记录', evidence / 'windows-delete-dialog.png')
        delete = next(widget for widget in self.descendants(dialog) if widget.winfo_class() == 'TButton' and widget.cget('text') == '删除')
        delete.invoke()
        self.assertEqual(self.app.store.records(), [])
        self.assertTrue(all(not Path(record['output']).exists() for record in records))

    def test_delete_loaded_task_tracks_save_as_and_clears_current_results(self):
        self.app.set_input('https://weibo.com/1/1')
        with patch('engine.opt_worker', self.fake_worker):
            self.app.start()
            self.wait_done()
        record = self.app.task
        copied = self.root / '另存.xlsx'
        with patch('app.filedialog.asksaveasfilename', return_value=str(copied)):
            self.app.save_as()
        self.assertIn(str(copied), self.app.store.records()[0]['exports'])
        self.app.delete_history_records([record], delete_files=True)
        self.assertIsNone(self.app.task)
        self.assertEqual(self.app.run_links, [])
        self.assertEqual(self.app.results, {})
        self.assertFalse(self.app.export_saved)
        self.assertFalse(copied.exists())
        self.assertFalse(Path(record['output']).exists())
        self.assertEqual(self.app.store.records(), [])


if __name__ == '__main__':
    if len(sys.argv) > 1:
        unittest.main(verbosity=2)
    else:
        # Give each case its own Tcl interpreter and application process, as a
        # desktop launch does. Repeated Tk root destruction is unreliable on macOS.
        names = unittest.defaultTestLoader.getTestCaseNames(DesktopFlowTests)
        failed = []
        for name in names:
            try:
                result = subprocess.run([sys.executable, __file__, 'DesktopFlowTests.' + name], timeout=30)
                if result.returncode:
                    failed.append(name)
            except subprocess.TimeoutExpired:
                failed.append(name)
        print(json.dumps({'desktop_cases': len(names), 'passed': len(names) - len(failed), 'failed': failed}, ensure_ascii=False))
        sys.exit(bool(failed))
