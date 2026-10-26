# VXDevSync — QA titlebar và control bar

Ngày: 2026-10-15. Phạm vi: hai thanh desktop; giữ theme dark và engine/CLI.

## Thay đổi

- Titlebar 32px, font hệ thống12px/600 cho tên app, icon16px, branding macOS x82.
- macOS: frameless full-content, khôi phục ba nút native; chỉ dịch origin, giữ frame/bounds và padding AppKit. Tâm dự kiến14/34/54, y15.5. Vùng drag riêng, nút tương tác không drag.
- Windows: ẩn branding/spacer Mac, menu File/View; một cụm minimize/maximize/close gọi API allowlist. Chưa kiểm thử Windows thật.
- Open workspace, recent tối đa5, Settings ở titlebar. Recent hỗ trợ hover/focus và giữ đường dẫn bằng textContent.
- Control bar44px chứa Git/Skills và Quét lại; giữ các hành động hiện có.

## Kết quả

- 5/5 unit tests hiện có và4/4 window-action tests PASS. Unknown action/missing window bị từ chối; maximize/restore theo native events.
- node --check cho app.js/window_chrome.js và AST ba file Python PASS.
- master_theme.css byte-identical so với snapshot trước sửa.
- Browser preview: titlebar32, controlbar44 y32, brandingx82, font12. Click Git→Skills→Git chuyển pane đúng. [Ảnh](../../_summary/vxdevsync_chrome_qa.png).
- Lệnh tests đầu tiên chạy sai cwd gây import src lỗi; chạy lại từ root app đạt5/5.
- AppKit offscreen process abort exit134 trong môi trường hiện tại, không được tính PASS.

## Chưa kiểm chứng

Native GUI macOS: traffic bezel, resize/fullscreen, drag, menu OS và hộp chọn folder; Windows runtime/resize/control buttons. Browser không có Python bridge và không chứng minh native window. Chưa build bundle hoặc release. Cần mở lại app để nạp main.py mới.
