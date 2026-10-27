# VXDevSync 1.0.2 — QA và phát hành bản vá SSL CA Context

## 1. Mục tiêu và phạm vi
- Khắc phục lỗi `[SSL: CERTIFICATE_VERIFY_FAILED]` khi kiểm tra và tải cập nhật tự động (Auto-Update) trong ứng dụng đóng gói trên macOS.
- Bổ sung nạp chứng chỉ gốc hệ thống kết hợp Mozilla CA roots (`certifi`) và hỗ trợ biến môi trường `SSL_CERT_FILE` tùy chỉnh.
- Đóng gói dữ liệu chứng chỉ certifi vào bundle PyInstaller độc lập trên mọi nền tảng Windows và macOS.

## 2. Kết quả Codex Review & Xử lý hoàn tất
Đã gọi Codex CLI review chỉ đọc (Run `20261027_095632_codex_67080150`) và tiếp thu giải quyết 100% các khuyến nghị:
1. **[P2] Bảo toàn Windows Trust Store & Custom CA:** Đã sửa `get_ssl_context()` nạp `context.load_default_certs()`, ưu tiên `SSL_CERT_FILE` của người dùng nếu có, và bổ sung `context.load_verify_locations(cafile=cafile)` từ `certifi` mà không ghi đè trust store mặc định của hệ điều hành.
2. **[P2] Tránh nuốt lỗi thu thập CA bundle & Thêm verification:** Đã loại bỏ khối try/catch im lặng trong `VXDevSync.spec` để build sẽ dừng ngay nếu thiếu certifi data; tích hợp kiểm tra `get_ssl_context()` ngay trong `--self-test` và bổ sung unit test xác minh `verify_mode == ssl.CERT_REQUIRED` cùng override `SSL_CERT_FILE`.
3. **Cập nhật Release Notes:** Đã ghi rõ hướng dẫn cài đặt thủ công một lần cho người dùng đang ở bản v1.0.0 / v1.0.1 và điều chỉnh văn phong kỹ thuật chính xác.

## 3. Kết quả kiểm thử tự động
- 34/34 Python unit & mock tests PASS (`scripts.run_tests`).
- 1/1 Node frontend security test PASS (`test_frontend_security.mjs`).
- `--self-test` PASS, trả về JSON với `ssl_context: true`.
