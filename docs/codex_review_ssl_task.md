# Yêu cầu tham vấn / review chỉ đọc cho VXDevSync v1.0.2

Chỉ tham vấn/review chỉ đọc; không sửa nguồn; không gọi agent khác.
Tuân thủ AGENTS.md, tiếng Việt, UTF-8, snake_case và không LaTeX.

## Bối cảnh và vấn đề
Trên macOS, ứng dụng VXDevSync đóng gói bằng PyInstaller bị lỗi khi kiểm tra cập nhật (Auto-Update):
`<urlopen error [SSL: CERTIFICATE_VERIFY_FAILED] certificate verify failed: unable to get local issuer certificate (_ssl.c:1010)>`
Nguyên nhân: Môi trường build CI nhúng Python 3.12 có OPENSSLDIR trỏ tới `/Library/Frameworks/Python.framework/Versions/3.12/etc/openssl`, đường dẫn này không tồn tại trên máy người dùng, và `urllib.request.urlopen` mặc định không tìm thấy Root CA certificates.

## Các thay đổi đã thực hiện cho v1.0.2
1. `src/updater.py`:
   - Bổ sung hàm `get_ssl_context()` ưu tiên `certifi.where()` (nếu có certifi và tồn tại cacert.pem), sau đó kiểm tra các bundle chứng chỉ hệ thống phổ biến trên macOS/Linux (`/etc/ssl/cert.pem`, `/private/etc/ssl/cert.pem`, `/etc/pki/tls/certs/ca-bundle.crt`, `/etc/ssl/certs/ca-certificates.crt`), fallback về `ssl.create_default_context()`.
   - Truyền `context=get_ssl_context()` vào các lời gọi `urlopen(url, timeout=15, context=context)` trong `check()` và `install()`.
2. `src/main.py`:
   - Gán `os.environ["SSL_CERT_FILE"]` sang `/etc/ssl/cert.pem` (hoặc bundle hệ thống) ngay khi khởi động nếu biến môi trường này chưa được thiết lập.
3. `requirements.txt`:
   - Bổ sung `certifi>=2024.2.2`.
4. `VXDevSync.spec`:
   - Thu thập data files của certifi bằng `collect_data_files('certifi')` đưa vào `datas`.
   - Thêm `'certifi'` vào `hiddenimports`.
5. `installer/windows_installer.nsi`:
   - Cập nhật default version lên 1.0.2.
6. `src/version.py`:
   - Nâng `VERSION = "1.0.2"`.
7. `tests/test_updater.py`:
   - Thêm unit test `test_get_ssl_context_returns_valid_context`.
   - Toàn bộ 34 unit & mock tests + 1 frontend security test đều PASS 100%.

## Mục tiêu review
Rà soát chỉ đọc toàn bộ các thay đổi trên:
1. Tính đúng đắn, an toàn và tương thích đa nền tảng (macOS Silicon, macOS Intel, Windows x64) của cơ chế nạp CA và SSL context.
2. Kiểm tra xem có edge cases nào liên quan đến SSL verification, PyInstaller bundle data, hoặc auto-update flow bị bỏ sót hay không.
3. Đánh giá tính sẵn sàng để release v1.0.2.
