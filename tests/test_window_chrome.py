import unittest
from unittest.mock import Mock
from src.bridge_api import BridgeApi


@unittest.skipUnless(__import__('sys').platform == 'darwin', 'Requires native AppKit image decoding')
class AboutIconTests(unittest.TestCase):
    def test_real_about_asset_has_matching_logical_and_pixel_size(self):
        from pathlib import Path
        from src.window_chrome import _load_about_icon
        path = Path(__file__).resolve().parents[1] / 'icon.png'
        before = path.read_bytes()
        icon = _load_about_icon(path)
        self.assertIsNotNone(icon)
        self.assertEqual(tuple(icon.size()), (512.0, 512.0))
        self.assertTrue(any((r.pixelsWide(), r.pixelsHigh()) == (512, 512)
                            for r in icon.representations()))
        self.assertEqual(path.read_bytes(), before)

    def test_missing_icon_preserves_native_fallback(self):
        from src.window_chrome import _load_about_icon
        self.assertIsNone(_load_about_icon('/nonexistent_vx_about_fixture/icon.png'))

class WindowChromeTests(unittest.TestCase):
    def setUp(self):
        self.window = Mock()
        self.api = BridgeApi(Mock(), lambda: self.window)

    def test_rejects_unknown_action_without_native_call(self):
        self.assertFalse(self.api.window_action('delete')['success'])
        self.assertEqual(self.window.mock_calls, [])

    def test_minimize_and_close_dispatch(self):
        self.assertTrue(self.api.window_action('minimize')['success'])
        self.window.minimize.assert_called_once_with()
        self.assertTrue(self.api.window_action('close')['success'])
        self.window.destroy.assert_called_once_with()

    def test_maximize_uses_native_event_state_for_restore(self):
        self.api.window_action('toggle_maximize')
        self.window.maximize.assert_called_once_with()
        self.api._set_window_maximized(True)
        self.api.window_action('toggle_maximize')
        self.window.restore.assert_called_once_with()
        self.api._set_window_maximized(False)
        self.api.window_action('toggle_maximize')
        self.assertEqual(self.window.maximize.call_count, 2)

    def test_missing_window(self):
        self.api._window_getter = lambda: None
        self.assertFalse(self.api.window_action('close')['success'])


class NativeMenuDispatchTests(unittest.TestCase):
    def test_webkit_wait_does_not_block_appkit_caller(self):
        from threading import Event, get_ident
        from src.window_chrome import _dispatch_menu_js
        entered, release = Event(), Event()
        caller = get_ident()
        worker_threads = []
        def blocking_webkit(script):
            self.assertEqual(script, 'openSettingsModal()')
            worker_threads.append(get_ident())
            entered.set()
            release.wait(2)
        window = Mock(evaluate_js=blocking_webkit)
        worker = _dispatch_menu_js(window, 'openSettingsModal()')
        try:
            self.assertTrue(entered.wait(1))
            self.assertTrue(worker.is_alive())
            self.assertNotEqual(worker_threads, [caller])
        finally:
            release.set()
            worker.join(2)
        self.assertFalse(worker.is_alive())
