"""Native window presentation only; no sync/config/engine operations."""
import sys

_observer_registered = False


def _load_about_icon(path):
    """Match muda's 512-point About image; PNG DPI must not halve its size."""
    import AppKit
    icon = AppKit.NSImage.alloc().initWithContentsOfFile_(str(path))
    if icon is not None:
        icon.setSize_((512.0, 512.0))
    return icon


def sync_native_chrome(window):
    if sys.platform != 'darwin':
        return
    # pywebview events run outside the AppKit main thread.
    from PyObjCTools import AppHelper
    AppHelper.callAfter(_position_mac_controls, window)


def _position_mac_controls(window):
    global _observer_registered
    import AppKit
    from Foundation import NSObject, NSNotificationCenter

    native = getattr(window, "native", None)
    if native is None:
        return

    style_mask = native.styleMask()
    if style_mask & AppKit.NSFullScreenWindowMask:
        return

    native.setTitleVisibility_(AppKit.NSWindowTitleHidden)
    native.setTitlebarAppearsTransparent_(True)
    native.setMovableByWindowBackground_(False)

    content_view = native.contentView()
    if content_view is None:
        return

    # 1. Unhide toàn bộ 3 nút trước
    # Quan trọng: Không unhide xen kẽ trong vòng lặp setFrame, vì việc unhide nút sau
    # sẽ kích hoạt AppKit layout pass nội bộ giật các nút trước đó về vị trí mặc định.
    buttons = []
    for kind in (AppKit.NSWindowCloseButton,
                 AppKit.NSWindowMiniaturizeButton,
                 AppKit.NSWindowZoomButton):
        btn = native.standardWindowButton_(kind)
        if btn is not None:
            btn.setHidden_(False)
            buttons.append((kind, btn))

    # 2. Định vị chính xác từng nút theo chuẩn desktop_ui_standards
    # Căn tâm dọc toolbar 32px (y=15.5) và tâm ngang 14pt, 34pt, 54pt (cách đều 20pt)
    cb = content_view.bounds()
    is_flipped = content_view.isFlipped()
    toolbar_center_y = 15.5 if is_flipped else cb.size.height - 15.5

    for index, (kind, btn) in enumerate(buttons):
        sv = btn.superview()
        if sv is None:
            continue

        ref = AppKit.NSWindow.standardWindowButton_forStyleMask_(kind, style_mask)
        if ref is not None:
            btn.setControlSize_(ref.controlSize())
            ref_size = ref.frame().size
            ref_bounds = ref.bounds()
        else:
            ref_size = btn.frame().size
            ref_bounds = btn.bounds()

        content_center = AppKit.NSMakePoint(
            cb.origin.x + 8.0 + (index * 20.0) + 6.0,
            cb.origin.y + toolbar_center_y
        )
        native_center = sv.convertPoint_fromView_(content_center, content_view)
        target_frame = AppKit.NSMakeRect(
            native_center.x - ref_size.width / 2.0,
            native_center.y - ref_size.height / 2.0,
            ref_size.width,
            ref_size.height
        )
        btn.setFrame_(target_frame)
        btn.setBounds_(ref_bounds)

    # 3. Đăng ký Notification Observer để duy trì vị trí khi cửa sổ focus/resize
    if not _observer_registered:
        class ChromeNotificationObserver(NSObject):
            def windowDidChange_(self, notification):
                _position_mac_controls(window)

        observer = ChromeNotificationObserver.alloc().init()
        # Giữ tham chiếu để không bị garbage collect
        native._chrome_observer = observer
        nc = NSNotificationCenter.defaultCenter()
        nc.addObserver_selector_name_object_(
            observer, "windowDidChange:", AppKit.NSWindowDidBecomeKeyNotification, native
        )
        nc.addObserver_selector_name_object_(
            observer, "windowDidChange:", AppKit.NSWindowDidResignKeyNotification, native
        )
        nc.addObserver_selector_name_object_(
            observer, "windowDidChange:", AppKit.NSWindowDidResizeNotification, native
        )
        nc.addObserver_selector_name_object_(
            observer, "windowDidChange:", AppKit.NSWindowDidDeminiaturizeNotification, native
        )
        _observer_registered = True



def _dispatch_menu_js(window, script):
    # evaluate_js waits for WebKit completion; never block AppKit's event loop.
    from threading import Thread
    import logging

    def run():
        try:
            window.evaluate_js(script)
        except Exception:
            logging.getLogger(__name__).exception("Native menu JavaScript dispatch failed")

    worker = Thread(target=run, name="vx_menu_dispatch", daemon=True)
    worker.start()
    return worker


def sync_app_menu(window, language):
    """Rebuild app-owned menu labels on AppKit's main thread."""
    if sys.platform != 'darwin' or window is None:
        return
    from PyObjCTools import AppHelper
    AppHelper.callAfter(_install_app_menu, window, language)


_app_menu_target_class = None

def _install_app_menu(window, language):
    global _app_menu_target_class
    import AppKit
    from Foundation import NSObject, NSMutableAttributedString, NSURL, NSMakeRange
    from .version import VERSION
    vi = language != 'en'
    app = AppKit.NSApplication.sharedApplication()

    if _app_menu_target_class is None:
        class AppMenuTarget(NSObject):
            def settings_(self, sender):
                _dispatch_menu_js(self._vx_window, 'openSettingsModal()')

            def workspace_(self, sender):
                _dispatch_menu_js(self._vx_window, 'document.getElementById("btn-open-workspace").click()')

            def about_(self, sender):
                url = 'https://github.com/linhbv94/VXDevSync'
                description = ('Đồng bộ Git và thư viện kỹ năng AI' if self._vx_language != 'en' else 'Sync Git repositories and AI skills')
                text = f'Bùi Việt Linh\n{description}\nGitHub: {url}'
                credits = NSMutableAttributedString.alloc().initWithString_(text)
                opts = {'ApplicationName': 'VXDevSync', 'ApplicationVersion': VERSION, 'Version': '', 'Copyright': '© 2026 Bùi Việt Linh. All rights reserved.', 'Credits': credits}
                # About uses transparent art, not the Dock squircle (Search reference).
                from pathlib import Path
                resource_root = Path(getattr(sys, '_MEIPASS', Path(__file__).resolve().parent.parent))
                icon = _load_about_icon(resource_root / 'icon.png')
                if icon is not None:
                    opts['ApplicationIcon'] = icon
                app.orderFrontStandardAboutPanelWithOptions_(opts)

        _app_menu_target_class = AppMenuTarget

    target = _app_menu_target_class.alloc().init()
    target._vx_window = window
    target._vx_language = language
    window._vx_menu_target = target
    bar = AppKit.NSMenu.alloc().init()
    def submenu(title):
        holder = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, None, '')
        menu = AppKit.NSMenu.alloc().initWithTitle_(title)
        holder.setSubmenu_(menu); bar.addItem_(holder)
        return menu
    def item(menu, title, selector, key='', owner=target):
        entry = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(title, selector, key)
        entry.setTarget_(owner); menu.addItem_(entry)
        return entry
    main = submenu('VXDevSync')
    item(main, 'Giới thiệu VXDevSync' if vi else 'About VXDevSync', 'about:')
    main.addItem_(AppKit.NSMenuItem.separatorItem())
    item(main, 'Cài đặt…' if vi else 'Settings…', 'settings:', ',')
    main.addItem_(AppKit.NSMenuItem.separatorItem())
    service_item = item(main, 'Services', None)
    services = AppKit.NSMenu.alloc().initWithTitle_('Services')
    service_item.setSubmenu_(services); app.setServicesMenu_(services)
    main.addItem_(AppKit.NSMenuItem.separatorItem())
    item(main, 'Hide VXDevSync', 'hide:', 'h', app)
    item(main, 'Hide Others', 'hideOtherApplications:', '', app)
    item(main, 'Show All', 'unhideAllApplications:', '', app)
    main.addItem_(AppKit.NSMenuItem.separatorItem())
    item(main, 'Quit VXDevSync', 'terminate:', 'q', app)
    files = submenu('Tệp' if vi else 'File')
    item(files, 'Mở workspace…' if vi else 'Open workspace…', 'workspace:', 'o')
    edit = submenu('Edit')
    for title, selector, key in [('Undo','undo:','z'), ('Cut','cut:','x'), ('Copy','copy:','c'), ('Paste','paste:','v'), ('Select All','selectAll:','a')]:
        # nil target uses the native responder chain, including WebView text fields.
        item(edit, title, selector, key, None)
    app.setMainMenu_(bar)
