import builtins
import unittest
from unittest.mock import patch
from src.self_test import run_self_test


class HeadlessPackagingTests(unittest.TestCase):
    def test_no_gui_backend_import_or_launch_receipt_acknowledgement(self):
        original = builtins.__import__
        forbidden = {'webview.platforms.cocoa', 'webview.platforms.winforms',
                     'webview.platforms.edgechromium', 'AppKit', 'WebKit', 'Foundation'}
        def guarded(name, *args, **kwargs):
            if name in forbidden:
                raise AssertionError(f'GUI imported during headless check: {name}')
            return original(name, *args, **kwargs)
        with patch('builtins.__import__', guarded), patch('src.updater.AppUpdater', side_effect=AssertionError('Update receipts must not be acknowledged')):
            result = run_self_test()
        self.assertEqual(result['self_test'], 'ok')
        self.assertFalse(result['gui_initialized'])

    def test_missing_ui_dependency_still_fails_packaging(self):
        with patch('src.self_test.importlib.util.find_spec', return_value=None):
            with self.assertRaises(ImportError):
                run_self_test()
