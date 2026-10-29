"""Headless packaging check: never initialize Cocoa/WinForms or acknowledge updates."""
import base64
import importlib.util
import json
from pathlib import Path
import ssl
import sys
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from src.version import VERSION, APP_ID
from src.updater import get_ssl_context


def run_self_test():
    # Importing the Cocoa backend executes NSApplication.sharedApplication().
    # Discover packaged modules without executing the GUI backend in a CI worker.
    modules = (['webview.platforms.cocoa', 'AppKit', 'WebKit', 'Foundation']
               if sys.platform == 'darwin' else
               ['webview.platforms.edgechromium', 'webview.platforms.winforms']
               if sys.platform == 'win32' else ['webview'])
    for name in modules:
        if importlib.util.find_spec(name) is None:
            raise ImportError(f'Missing packaged UI dependency: {name}')
    context = get_ssl_context()
    if context is None or context.verify_mode != ssl.CERT_REQUIRED or not context.check_hostname:
        raise ValueError('TLS certificate verification is not enabled')
    config = json.loads(Path(__file__).with_name('release_config.json').read_text(encoding='utf-8'))
    Ed25519PublicKey.from_public_bytes(base64.b64decode(config['public_key'], validate=True))
    # Do not construct AppUpdater: its constructor acknowledges launch receipts.
    return {'version': VERSION, 'app_id': APP_ID,
            'frozen': bool(getattr(sys, 'frozen', False)),
            'self_test': 'ok', 'gui_initialized': False}
