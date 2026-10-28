# Yêu cầu tham vấn / review chỉ đọc cho VXDevSync v1.0.3

Chỉ tham vấn/review chỉ đọc; không sửa nguồn; không gọi agent khác.
Tuân thủ AGENTS.md, tiếng Việt, UTF-8, snake_case và không LaTeX.

## Bối cảnh và tính năng mới
VXDevSync vừa được nâng cấp bổ sung tính năng thao tác hàng loạt và cơ chế báo cáo lỗi Git chi tiết:
1. Hai nút bấm thao tác nhanh "Pull tất cả (N)" và "Push tất cả (N)" trực tiếp trên thanh Selection Bar với badge số lượng cập nhật thời gian thực theo trạng thái Behind/Ahead.
2. Modal "Chi tiết Lỗi Đồng bộ Git" tự động hiển thị khi có bất kỳ repo nào gặp sự cố, hoặc khi người dùng click vào Badge "Lỗi PULL/PUSH" trên từng dòng repo trong bảng.
3. Phân tích nguyên nhân lỗi Git tự động sang tiếng Việt (xung đột merge, lỗi xác thực SSH/token, mất mạng/timeout, nhánh diverged) kèm lệnh Git đã chạy và raw console output.
4. Hỗ trợ nút sao chép log lỗi 1-click và nút thử lại (retry) chỉ riêng các repository gặp lỗi.

## Các thay đổi mã nguồn chi tiết
1. `src/git_engine.py`:
   - Hàm `sync_single_repo`: Trả về thêm `name`, `cmd`, `raw_error`.
   - Phân tích `raw_output` để sinh `hint` tiếng Việt dễ hiểu cho các tình huống thường gặp (xung đột merge, auth failure, offline, non-fast-forward).
2. `src/bridge_api.py`:
   - Hàm `sync_git_repos`: Bổ sung `failed_count` trong JSON trả về cho frontend.
3. `frontend/index.html` & `frontend/css/style.css`:
   - Bổ sung `#btn-pull-all`, `#btn-push-all`, modal `#git-error-modal`, `#btn-copy-error-log`, `#btn-retry-failed-sync`.
4. `frontend/js/app.js`:
   - Tích hợp logic Pull All / Push All, kiểm tra điều kiện an toàn trước khi chạy.
   - Hiển thị inline error badge `btn-view-repo-error` trên dòng repo gặp sự cố.
   - Render modal lỗi với `escapeHtml()` cho toàn bộ dữ liệu động (`item.name`, `item.path`, `item.action`, `item.message`, `item.cmd`, `item.raw_error`).
5. `tests/test_vxdevsync.py`:
   - Bổ sung unit test `test_sync_git_repos_error_details`.
6. Kiểm thử:
   - 35/35 Python unit & mock tests PASS 100%.
   - 1/1 Node frontend security test PASS.
   - `python src/main.py --self-test` PASS.
   - Version nâng lên 1.0.3 trong `src/version.py`, `installer/windows_installer.nsi`, `docs/release_notes/1.0.3.md`.

## Mục tiêu review
Rà soát chỉ đọc toàn bộ các thay đổi trên:
1. Độ an toàn thực thi lệnh Git trong `git_engine.py`, tính chính xác của các error hints và xử lý timeout/error formatting.
2. Tính bảo mật trong `frontend/js/app.js`: xác thực không có nguy cơ XSS / HTML injection khi hiển thị tên repo, lệnh Git, error messages hay raw terminal log.
3. Trải nghiệm người dùng và tính nhất quán với VXUtilities UI standards (bố cục, modal, badge, copy clipboard, retry flow).
4. Đánh giá tính sẵn sàng để release v1.0.3.
