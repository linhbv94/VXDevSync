# VXDevSync 1.0.3 — QA và phát hành tính năng Pull/Push All & Git Error Modal

## 1. Mục tiêu và phạm vi
- Bổ sung thao tác hàng loạt "Pull tất cả (N)" và "Push tất cả (N)" trên thanh Selection Bar với badge số lượng cập nhật thời gian thực.
- Tích hợp Modal Báo cáo Chi tiết Lỗi Git (Git Error Details) khi có repo gặp sự cố hoặc click xem lại từ inline badge.
- Phân tích nguyên nhân lỗi Git tự động sang tiếng Việt dễ hiểu kèm lệnh Git đã chạy và raw console output.
- Hỗ trợ nút sao chép log lỗi 1-click và nút thử lại (retry) bảo toàn đúng thao tác ban đầu.

## 2. Kết quả Codex Review & Xử lý hoàn tất
Đã gọi Codex CLI review chỉ đọc (Run `20261028_020943_codex_e75480fb`) và tiếp thu giải quyết 100% cả 5 điểm khuyến nghị:
1. **[P1] Bảo toàn thao tác khi Retry:** Đã sửa `retryFailedSyncRepos` trong `app.js` nhóm các repo theo đúng action ban đầu (`pull`, `push`, `smart_sync`) thay vì ép toàn bộ sang `smart_sync` gây rủi ro vô tình push commit.
2. **[P2] Tôn trọng trạng thái loại trừ (Ignore List):** Đã lọc bỏ `repo.is_ignored` trong luồng retry frontend, đồng thời bổ sung kiểm tra an toàn trong `src/bridge_api.py:sync_git_repos` tự động bỏ qua các repo nằm trong danh sách loại trừ.
3. **[P2] Phân loại lỗi mạng và xác thực chính xác:** Đã hiệu chỉnh `src/git_engine.py` phân tách rõ ràng giữa lỗi chứng chỉ SSL/TLS, lỗi xác thực 401/403/permission denied và lỗi mất kết nối mạng thật sự (offline / host not found).
4. **[P2] Đồng bộ số đếm Badge và thao tác Pull tất cả:** Đã sửa `btnPullAll` chỉ kéo các repo đang Behind (khớp đúng số đếm trên badge `count-pull-now`), hiển thị thông báo nếu không có repo nào cần pull thay vì âm thầm pull toàn bộ repo sạch.
5. **[P3] Cải thiện Accessibility & Phím tắt:** Chuyển inline badge lỗi sang thẻ `button` có aria-label đầy đủ, thêm quản lý focus cho modal lỗi và hỗ trợ phím `Escape` để đóng modal.

## 3. Bằng chứng kiểm thử tự động
- 37/37 Python unit & mock tests PASS (`scripts.run_tests`), bổ sung regression tests `test_sync_git_repos_skips_ignored` và `test_git_error_hints_classification`.
- 1/1 Node frontend security test PASS (`test_frontend_security.mjs`), xác thực escapeHtml 100% các trường dữ liệu động của modal lỗi.
- `python src/main.py --self-test` PASS (`version: 1.0.3`, `self_test: ok`).
