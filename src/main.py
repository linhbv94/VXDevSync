import sys
import os
from pathlib import Path

# Thêm đường dẫn project root vào sys.path
if getattr(sys, "frozen", False):
    root_dir = Path(getattr(sys, "_MEIPASS", Path(sys.executable).parent))
else:
    root_dir = Path(__file__).resolve().parent.parent

if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

if len(sys.argv) == 3 and sys.argv[1] == '--apply-update':
    from src.updater import apply_mac_update
    apply_mac_update(sys.argv[2])
    raise SystemExit(0)

if '--self-test' in sys.argv:
    import json
    import webview
    from src.updater import AppUpdater
    from src.version import VERSION, APP_ID
    AppUpdater()
    if sys.platform == 'darwin':
        import webview.platforms.cocoa
    elif sys.platform == 'win32':
        import webview.platforms.edgechromium
        import webview.platforms.winforms
    print(json.dumps({'version': VERSION, 'app_id': APP_ID, 'frozen': bool(getattr(sys, 'frozen', False)), 'self_test': 'ok'}))
    raise SystemExit(0)

import webview
from src.config_manager import ConfigManager
from src.bridge_api import BridgeApi
from src.window_chrome import sync_native_chrome

def main():
    config_mgr = ConfigManager()
    
    # Biến lưu trữ cửa sổ webview
    active_window = None
    
    def get_window():
        return active_window

    api = BridgeApi(config_manager=config_mgr, window_getter=get_window)
    
    frontend_path = root_dir / "frontend" / "index.html"
    if not frontend_path.exists():
        print(f"[Error] Không tìm thấy frontend: {frontend_path}")
        sys.exit(1)

    url = frontend_path.resolve().as_uri()
    
    # Thiết lập kích thước theo chuẩn zTools UI
    window = webview.create_window(
        title="VXDevSync",
        url=url,
        js_api=api,
        width=1040,
        height=680,
        min_size=(860, 540),
        background_color="#0f1117",
        frameless=sys.platform in ("darwin", "win32"),
        easy_drag=False,
        text_select=False
    )
    
    active_window = window
    window.events.loaded += lambda: sync_native_chrome(window)
    window.events.resized += lambda: sync_native_chrome(window)
    window.events.maximized += lambda: api._set_window_maximized(True)
    window.events.restored += lambda: api._set_window_maximized(False)
    webview.settings["DRAG_REGION_DIRECT_TARGET_ONLY"] = True
    
    # Khởi chạy pywebview (dùng Cocoa/WebKit native trên macOS)
    webview.start(debug=False)

if __name__ == "__main__":
    main()
