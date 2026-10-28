# VXDevSync 1.0.4 — Khắc phục lỗi Auto-Update & Phát hành Bản mới

## 1. Tổng quan Sự cố & Mục tiêu
- **Sự cố:** Khi người dùng nhấn nút "Cài đặt và khởi động lại" trong tab Cài đặt → Cập nhật, ứng dụng bị treo ở trạng thái loading vô tận ("loading đến tận thế"), không đóng cửa sổ và không khởi động lại vào phiên bản mới.
- **Nguyên nhân cốt lõi:**
  1. `src/bridge_api.py` gọi `window.destroy()` trước khi `return result` tới WebView. Việc đóng NSWindow giải phóng WKWebView khiến Promise JS IPC bridge ở frontend không bao giờ resolve hoặc reject.
  2. pywebview gọi JS API trong non-daemon thread, khiến tiến trình Python chính (PID cũ) không thoát hoàn toàn sau khi đóng cửa sổ. Helper độc lập `--apply-update` chờ PID cũ thoát bị timeout sau 30 giây và crash trước khi kịp hoán đổi bundle `.app`.
  3. Frontend `frontend/js/app.js` thiếu timeout bảo vệ và không mở lại nút khi gặp sự cố mạng/treo RPC.
- **Mục tiêu phát hành 1.0.4:**
  - Hoàn tất phản hồi trạng thái JSON sang WebView trước khi dọn dẹp cửa sổ và tiến trình cũ.
  - Sử dụng luồng nền daemon đệm 0.8 giây, gọi `window.destroy()` và `os._exit(0)` dứt điểm tiến trình Python.
  - Tích hợp cơ chế bắt tay `ready_file` giữa tiến trình chính và helper `--apply-update`.
  - Tăng timeout tải tệp lên 60 giây và bổ sung timeout frontend 120 giây bằng `Promise.race`.
  - Bump version lên `1.0.4`, chạy toàn bộ test suites và phát hành multi-platform release.

## 2. Kiểm thử Tự động & Bằng chứng Nghiệm thu
- `python -m scripts.run_tests`: 39/39 tests PASS (100%).
  - Bổ sung `test_apply_mac_update_flow` kiểm tra hoán đổi bundle, dọn dẹp staging và gọi open instance mới.
  - Bổ sung `test_bridge_api_install_update_delayed_exit_and_blocks_mutations` kiểm tra delayed exit luồng daemon và cờ `_shutdown_pending` chặn mutation sau khi kích hoạt cập nhật.
- `node scripts/test_frontend_security.mjs`: PASS (100%).
- `python src/main.py --self-test`: PASS (`version: 1.0.4`, `self_test: ok`).

## 3. Bản phát hành Multi-platform
- Windows x64 NSIS setup EXE: `vxdevsync_1.0.4_windows_x64_setup.exe`
- macOS Apple Silicon DMG: `vxdevsync_1.0.4_macos_silicon.dmg`
- macOS Apple Silicon updater archive: `vxdevsync_1.0.4_macos_silicon.app.tar.gz`
- macOS Intel DMG: `vxdevsync_1.0.4_macos_intel.dmg`
- macOS Intel updater archive: `vxdevsync_1.0.4_macos_intel.app.tar.gz`
- Manifest cập nhật tự động: `latest.json`
