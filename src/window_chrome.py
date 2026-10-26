"""Native window presentation only; no sync/config/engine operations."""
import sys

_observer_registered = False


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

