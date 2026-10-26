import unittest
from unittest.mock import Mock
from src.bridge_api import BridgeApi

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
        self.api.window_getter = lambda: None
        self.assertFalse(self.api.window_action('close')['success'])
