import hashlib
import json
import os
import platform
import subprocess
import tempfile
import time
import unittest
import zipfile
from pathlib import Path
from unittest.mock import Mock, patch

import updater


class UpdateTests(unittest.TestCase):
    def payload(self, version='0.6.8', system='macOS-arm64'):
        name = f'URLHeat-{version}-{system}.zip'
        return {'tag_name': f'v{version}', 'assets': [
            {'name': n, 'browser_download_url': f'https://github.com/{updater.REPOSITORY}/releases/download/v{version}/{n}'}
            for n in (name, name + '.sha256')]}

    def test_versions_platforms_and_release_assets(self):
        self.assertEqual(updater.version_tuple('v0.6.10'), (0, 6, 10))
        self.assertIsNone(updater.release_from_payload(self.payload(), '0.6.8', 'Darwin', 'arm64'))
        self.assertIsNone(updater.release_from_payload(dict(self.payload(), prerelease=True), '0.6.7'))
        result = updater.release_from_payload(self.payload(), '0.6.7', 'Darwin', 'arm64')
        self.assertEqual(result.filename, 'URLHeat-0.6.8-macOS-arm64.zip')
        result = updater.release_from_payload(self.payload(system='windows-x64'), '0.6.7', 'Windows', 'AMD64')
        self.assertTrue(result.filename.endswith('windows-x64.zip'))
        with self.assertRaises(ValueError):
            updater.release_from_payload(self.payload(), '0.6.7', 'Darwin', 'x86_64')
        broken = self.payload()
        broken['assets'].pop()
        with self.assertRaises(ValueError):
            updater.release_from_payload(broken, '0.6.7', 'Darwin', 'arm64')
        broken = self.payload()
        broken['assets'][0]['browser_download_url'] = 'https://example.com/file.zip'
        with self.assertRaises(ValueError):
            updater.release_from_payload(broken, '0.6.7', 'Darwin', 'arm64')

    def test_checksum_and_corrupt_download(self):
        release = updater.release_from_payload(self.payload(), '0.6.7', 'Darwin', 'arm64')
        body = b'archive-data'
        checksum = Mock(text=hashlib.sha256(body).hexdigest() + '  ' + release.filename)
        response = Mock()
        response.__enter__ = Mock(return_value=response)
        response.__exit__ = Mock(return_value=False)
        response.iter_content.return_value = [body]
        with tempfile.TemporaryDirectory() as root, patch.object(updater.requests, 'get', side_effect=[checksum, response]):
            self.assertEqual(updater.download_release(release, root).read_bytes(), body)
        response.iter_content.return_value = [b'corrupt']
        with tempfile.TemporaryDirectory() as root, patch.object(updater.requests, 'get', side_effect=[checksum, response]):
            with self.assertRaises(ValueError):
                updater.download_release(release, root)

    def test_zip_paths_cannot_escape_staging(self):
        with tempfile.TemporaryDirectory() as root:
            archive = Path(root) / 'test.zip'
            for name in ('../outside', '/absolute', 'C:/outside', '..\\outside'):
                with zipfile.ZipFile(archive, 'w') as package:
                    package.writestr(name, 'bad')
                with self.assertRaises(ValueError):
                    updater.validate_archive(archive)
            with zipfile.ZipFile(archive, 'w') as package:
                package.writestr('链接热度抓取.exe', b'MZ')
            updater.validate_archive(archive)

    def test_interrupted_download_restarts_with_fresh_checksum(self):
        release = updater.release_from_payload(self.payload(), '0.6.7', 'Darwin', 'arm64')
        body = b'complete archive'
        checksum = Mock(text=hashlib.sha256(body).hexdigest() + '  ' + release.filename)

        def response(blocks):
            result = Mock()
            result.__enter__ = Mock(return_value=result)
            result.__exit__ = Mock(return_value=False)
            result.iter_content.return_value = blocks
            return result

        def interrupted():
            yield b'partial'
            raise updater.requests.exceptions.ChunkedEncodingError('connection reset')

        with tempfile.TemporaryDirectory() as root, \
             patch.object(updater.requests, 'get', side_effect=[checksum, response(interrupted()),
                                                               checksum, response([body])]), \
             patch.object(updater.time, 'sleep'):
            self.assertEqual(updater.download_release(release, root).read_bytes(), body)

    def test_download_network_retries_are_bounded(self):
        with patch.object(updater.requests, 'get', side_effect=updater.requests.ConnectionError()), \
             patch.object(updater.time, 'sleep'):
            with self.assertRaisesRegex(ValueError, '当前程序未被替换'):
                updater.download_release(Mock(), '.')

    def test_installer_resets_frozen_restart_environment(self):
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            update = updater.PreparedUpdate(root, root / 'new.exe', root / 'app.exe', '0.6.10')
            with patch.object(updater.subprocess, 'Popen') as launch:
                updater.launch_installer(update, 99999999, root)
            self.assertEqual(launch.call_args.kwargs['env']['PYINSTALLER_RESET_ENVIRONMENT'], '1')

    @unittest.skipUnless(platform.system() == 'Darwin', 'macOS replacement helper')
    def test_mac_helper_replaces_and_rolls_back(self):
        for succeed in (True, False):
            with tempfile.TemporaryDirectory(prefix="更新 空格'") as root:
                root = Path(root)
                work = root / 'work'; work.mkdir()
                target = root / 'target.app'; target.mkdir(); (target / 'old').touch()
                source = work / 'new.app'; source.mkdir(); (source / 'new').touch()
                prepared = updater.PreparedUpdate(work, source, target, '0.6.8')
                with patch.object(updater.subprocess, 'Popen') as launch:
                    updater.launch_installer(prepared, 99999999, root)
                command = launch.call_args.args[0]
                script = Path(command[1])
                # Exercise real rename/rollback; avoid launching an app in this test.
                script.write_text(script.read_text().replace('/usr/bin/open "$target"', 'true' if succeed else 'false'))
                result = subprocess.run(command, capture_output=True, timeout=10)
                self.assertEqual(result.returncode == 0, succeed)
                self.assertTrue((target / ('new' if succeed else 'old')).exists())

    @unittest.skipUnless(platform.system() == 'Windows', 'Windows replacement helper')
    def test_windows_helper_replaces_unlocked_executable(self):
        import shutil
        with tempfile.TemporaryDirectory(prefix='urlheat update ') as root:
            root = Path(root)
            work = root / 'work'; work.mkdir()
            target = root / 'old.exe'
            source = work / 'new.exe'
            windows = Path(os.environ['SystemRoot']) / 'System32'
            shutil.copy2(windows / 'where.exe', target)
            shutil.copy2(windows / 'whoami.exe', source)
            expected = source.read_bytes()
            update = updater.PreparedUpdate(work, source, target, '0.6.8')
            process = updater.launch_installer(update, 99999999, root)
            self.assertEqual(process.wait(timeout=45), 0,
                             (root / 'update-install.log').read_text(encoding='utf-8'))
            self.assertEqual(target.read_bytes(), expected)
            # The helper deliberately returns while the new process is running.
            # Wait for the short-lived test EXE to release its Windows file lock.
            deadline = time.monotonic() + 15
            while True:
                try:
                    target.unlink()
                    break
                except PermissionError:
                    if time.monotonic() >= deadline:
                        raise
                    time.sleep(.1)
