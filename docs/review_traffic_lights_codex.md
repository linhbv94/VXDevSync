# Yêu cầu Tham vấn & Review Chỉ Đọc: Cụm Traffic Lights macOS cho VXDevSync

> **Vai trò:** Tham vấn và Review chỉ đọc (Read-only Consultation).
> **Nguyên tắc:** Chỉ review/nhận xét/phân tích; không sửa nguồn; không gọi agent khác.
> **Quy chuẩn:** Tuân thủ AGENTS.md (Tiếng Việt chuyên nghiệp, UTF-8, snake_case, Tuyệt đối KHÔNG dùng LaTeX).

---

## 1. Bối cảnh & Vấn đề Cần Giải Quyết

Dự án `vxdevsync/` là ứng dụng Desktop GUI viết bằng **Python + pywebview (Cocoa/WebKit)**.
Các ứng dụng khác trong hệ sinh thái zTools (VXMedia, VXmp3, VXPhotos, VXClean, VXClick) được viết bằng **Tauri v2 (Rust + Wry)**.

User vừa phản hồi kèm hình ảnh:
- Cụm nút traffic lights (đỏ, vàng, xanh) của VXDevSync hiện đang:
  1. **Vẫn to hơn** so với các ứng dụng khác trong zTools (VXMedia, VXmp3).
  2. **Bị lệch khoảng cách:** Nút đỏ và nút vàng cách nhau 23px, trong khi nút vàng và nút xanh bị dính sát vào nhau (cách chỉ 15px).

---

## 2. Mã nguồn Hiện tại trong `vxdevsync/src/window_chrome.py`

```python
def sync_native_chrome(window):
    if sys.platform != 'darwin':
        return
    from PyObjCTools import AppHelper
    AppHelper.callAfter(_position_mac_controls, window)

def _position_mac_controls(window):
    import AppKit
    native = window.native
    if native is None or native.styleMask() & AppKit.NSFullScreenWindowMask:
        return
    native.setTitleVisibility_(AppKit.NSWindowTitleHidden)
    native.setTitlebarAppearsTransparent_(True)
    native.setMovableByWindowBackground_(False)

    style_mask = native.styleMask()
    for index, kind in enumerate((AppKit.NSWindowCloseButton,
                                  AppKit.NSWindowMiniaturizeButton,
                                  AppKit.NSWindowZoomButton)):
        button = native.standardWindowButton_(kind)
        if button is None or button.superview() is None:
            continue
        button.setHidden_(False)

        sv = button.superview()
        ref = AppKit.NSWindow.standardWindowButton_forStyleMask_(kind, style_mask)
        if ref is not None:
            button.setControlSize_(ref.controlSize())
            ref_size = ref.frame().size
            ref_bounds = ref.bounds()
        else:
            ref_size = button.frame().size
            ref_bounds = button.bounds()

        cx = 14.0 + index * 20.0
        cy = 15.5 if sv.isFlipped() else sv.bounds().size.height - 15.5

        target_frame = AppKit.NSMakeRect(
            cx - ref_size.width / 2.0,
            cy - ref_size.height / 2.0,
            ref_size.width,
            ref_size.height
        )
        button.setFrame_(target_frame)
        button.setBounds_(ref_bounds)
```

Và trong `src/main.py`:
```python
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
    window.events.loaded += lambda: sync_native_chrome(window)
    window.events.resized += lambda: sync_native_chrome(window)
```

---

## 3. Câu hỏi Cần Codex Tham Vấn & Phản Biện

1. **Tại sao cụm nút của VXDevSync lại to hơn các app Tauri (VXMedia, VXmp3)?**
   - Trong `_summary/macos_window_fix_20261015.md`, có ghi nhận SDK compatibility 15.5 vs SDK local (macOS 15/26). Liệu có phải `frameless=True` trong pywebview hoặc cách tạo NSWindow trong pywebview đang tạo một Window kiểu khác, khiến các nút traffic lights hiển thị cỡ mặc định lớn (Regular controlSize thay vì Small / 12pt)?
   - Trong Tauri (VXMedia), cửa sổ được cấu hình `titleBarStyle: Overlay, hiddenTitle: true, decorations: true`. Trong pywebview, hiện đang dùng `frameless=True`. Sự khác biệt này ảnh hưởng như thế nào đến kích thước và rendering của nút traffic lights?

2. **Tại sao nút Zoom (xanh) lại bị dính sát vào nút Vàng (23px vs 15px)?**
   - Cocoa / AppKit có cơ chế `autoresizingMask` hoặc Auto Layout constraints của `NSTitlebarView` ghi đè vị trí của `NSWindowZoomButton` sau khi layout không?
   - Làm thế nào để đặt vị trí 3 nút này cách đều nhau 20pt một cách bền vững trên macOS mà không bị AppKit kéo lệch?

3. **Phương án kiến trúc tối ưu nhất:**
   - Để đạt được diện mạo và kích thước khớp 100% với VXMedia / quy chuẩn `desktop_ui_standards.md` trong môi trường Python + pywebview, giải pháp chuẩn xác nhất ở tầng AppKit / Cocoa là gì?
