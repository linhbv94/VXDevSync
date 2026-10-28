# Yêu cầu tham vấn / review chỉ đọc cho VXDevSync — Sửa lỗi Auto-Update bị treo

Chỉ tham vấn/review chỉ đọc; không sửa nguồn; không gọi agent khác.
Tuân thủ AGENTS.md, tiếng Việt, UTF-8, snake_case và không LaTeX.

## Bối cảnh và sự cố phát sinh
Người dùng báo cáo khi bấm Cài đặt và khởi động lại trong Cài đặt → Cập nhật, ứng dụng bị treo ở trạng thái loading vô tận ("loading đến tận thế"), không đóng cửa sổ và không khởi động lại vào phiên bản mới.

## Nguyên nhân gốc rễ đã xác định
1. **Lỗ hổng RPC IPC & Window Destroy:**
   Trong `src/bridge_api.py`, hàm `install_update()` thực hiện:
   ```python
   result = self._updater.install()
   window.destroy()
   return result
   ```
   Lệnh `window.destroy()` hủy NSWindow và giải phóng WKWebView trước khi `return result` có thể trả về qua JavaScript IPC bridge. WKWebView bị giải phóng khiến Promise `await window.pywebview.api.install_update()` ở frontend không bao giờ resolve hoặc reject, giữ giao diện kẹt vĩnh viễn ở trạng thái "Đang tải, xác minh và cài cập nhật...".

2. **Tiến trình Python cũ không thoát & Helper Process bị Timeout:**
   Trong pywebview (Cocoa backend), việc gọi `window.destroy()` chỉ gửi tín hiệu đóng NSWindow. Tuy nhiên, luồng gọi JS API được pywebview khởi chạy dưới dạng một `threading.Thread` không có cờ `daemon=True` (`Thread-2`).
   Do còn non-daemon thread, tiến trình Python chính (PID cũ) không thoát sau khi cửa sổ đóng.
   Tiến trình con helper `--apply-update` được spawn độc lập chạy vòng lặp `os.kill(pid, 0)` lặp 300 lần (30 giây) để chờ PID cũ chết trước khi hoán đổi bundle `.app`. Vì PID cũ không bao giờ thoát, helper bị `TimeoutError` sau 30 giây và crash, để lại thư mục staging `.vxdevsync_update_xxx` và file `plan.json` mà chưa hề hoán đổi bundle.

3. **Frontend thiếu timeout bảo vệ và error recovery:**
   Trong `frontend/js/app.js`, không có timeout bảo vệ cho Promise và không mở lại nút khi gặp sự cố mạng, khiến nút bị vô hiệu hóa vĩnh viễn nếu backend không phản hồi.

## Các thay đổi mã nguồn đã thực hiện
1. **`src/bridge_api.py`:**
   - Trả về ngay lập tức JSON response `{"success": True, "restart_required": True}` cho WebView để frontend kịp cập nhật UI.
   - Khởi chạy một background daemon thread đệm 0.8 giây, sau đó mới gọi `window.destroy()` và gọi `os._exit(0)` để dứt điểm toàn bộ tiến trình Python C-level, giải phóng PID cũ ngay lập tức cho helper process.
2. **`src/updater.py`:**
   - Trong `apply_mac_update`:
     - Lấy version hiện tại trực tiếp từ `Info.plist` của target app trên đĩa để so sánh phiên bản cơ sở, tránh sai lệch khi so sánh với hằng số `VERSION` trong mã nguồn.
     - Dọn dẹp thư mục staging `.vxdevsync_update_xxx` sau khi hoán đổi thành công.
     - Sử dụng `open -n` để mở instance ứng dụng mới độc lập.
     - Bổ sung logging chẩn đoán chi tiết ra `/tmp/vxdevsync_updater.log` để theo dõi và khắc phục sự cố nếu có lỗi phát sinh trong helper.
   - Trong `AppUpdater.install()`:
     - Tăng timeout tải tệp từ 30 giây lên 60 giây.
     - Tự động dọn dẹp thư mục nén tải về trong `/tmp` sau khi giải nén thành công, và dọn dẹp staging nếu có lỗi phát sinh trong khối `try/except`.
3. **`frontend/js/app.js`:**
   - Bổ sung timeout bảo vệ 120 giây bằng `Promise.race()`.
   - Hiển thị thông báo chi tiết: "Đang tải gói cập nhật, xác thực chữ ký và giải nén (có thể mất 15-30 giây)..." và "Cập nhật thành công. Ứng dụng đang khởi động lại...".
   - Mở khóa lại nút bấm khi có lỗi để người dùng có thể thử lại.
4. **`tests/test_updater.py`:**
   - Bổ sung `test_apply_mac_update_flow` kiểm tra logic hoán đổi bundle, dọn dẹp staging và gọi open.
   - Bổ sung `test_bridge_api_install_update_delayed_exit` kiểm tra thread thoát trễ là daemon thread.
   - Toàn bộ 39/39 Python tests và Node frontend security test PASS 100%.

## Mục tiêu review của Codex CLI
Rà soát chỉ đọc toàn bộ các thay đổi trên:
1. **Tính đúng đắn và an toàn của vòng đời thoát tiến trình:**
   - Đánh giá cơ chế dùng background daemon thread 0.8s kết hợp `os._exit(0)` trong `bridge_api.py`. Có rủi ro nào về race condition, rò rỉ tài nguyên, hoặc xung đột với WKWebView không?
2. **Tính tin cậy của helper process `--apply-update`:**
   - Kiểm tra vòng lặp `for _ in range(300): os.kill(pid, 0)` trong `apply_mac_update`. Liệu sau khi PID cũ gọi `os._exit(0)`, helper có bắt được `ProcessLookupError` ngay lập tức và hoán đổi bundle an toàn không?
   - Cơ chế rollback `swap_mac_bundle` và dọn dẹp staging có đảm bảo không bao giờ làm hỏng bundle đang chạy nếu có lỗi?
3. **Khả năng tương thích đa nền tảng (macOS và Windows):**
   - Đánh giá xem luồng trên Windows (`setup.exe /S /PARENT_PID=...`) có được hưởng lợi tương tự từ việc thoát tiến trình bằng `os._exit(0)` không.
4. **Trải nghiệm người dùng và xử lý ngoại lệ ở Frontend:**
   - Đánh giá timeout 120s và error handling trong `frontend/js/app.js`. Có trường hợp nào có thể khiến UI bị đơ hoặc kẹt nữa không?
5. **Đề xuất cải tiến (nếu có):**
   - Bất kỳ điểm nào cần bổ sung hoặc tối ưu hóa thêm trước khi đóng gói bản cập nhật tiếp theo.
