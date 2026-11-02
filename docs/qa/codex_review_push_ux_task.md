# Yêu cầu Tham vấn & Review: Cải tiến UX Thao tác Push Git (VXDevSync)

> **Vai trò:** Codex tham vấn/review chỉ đọc; không sửa nguồn; không gọi agent khác.
> **Tuân thủ quy chuẩn:** AGENTS.md, tiếng Việt chuyên nghiệp, UTF-8, snake_case, tuyệt đối KHÔNG sử dụng cú pháp LaTeX (dùng `→`, `≥`, `≤` và plain text).

---

## 1. Bối cảnh & Mục tiêu thay đổi
Người dùng yêu cầu cải tiến trải nghiệm người dùng (UX) đối với thao tác Push Git trong VXDevSync:
- **Vấn đề trước đây:** Khi người dùng nhấn Push riêng cho 1 repository hoặc nhấn nút "Push tất cả", nếu repository đang có file sửa đổi dở dang (`is_dirty`), hệ thống từ chối thực hiện với thông báo "Bỏ qua an toàn: Repo có file chưa commit (Dirty)". Người dùng phản ánh đây là lỗi UX vì khi chủ động chọn Push, người dùng mong muốn hệ thống tự động gom các thay đổi và đẩy lên remote luôn (tương tự như hành vi của Smart Sync).
- **Mục tiêu:** Khi thực hiện action `push`:
  1. Nếu repo đang `dirty`, engine tự động stage toàn bộ (`git add -A`) và commit (`git commit -m "chore: auto-commit changes before push"`) trước khi push.
  2. Nếu thao tác là `pull` hoặc `smart_sync`: Vẫn giữ nguyên cơ chế bảo vệ Safe-Skip để không ghi đè làm mất mã nguồn local chưa commit của người dùng.
  3. Cập nhật frontend để nút "Push tất cả" và bộ đếm nhận diện được các repo đang dirty cần push.

---

## 2. Danh sách tệp đã chỉnh sửa cần Review

1. **`src/git_engine.py`:**
   - Trong `get_repo_status`:
     - Cập nhật `suggested_action` cho repo dirty khi `behind == 0` thành `"Auto Push"` (thay vì `"Safe-Skip (Dirty)"`).
   - Trong `sync_single_repo`:
     - Đảo thứ tự: Kiểm tra `remote` trước khi kiểm tra worktree dirty. Nếu repo chưa gắn remote thì báo lỗi ngay, tránh việc tự động commit tạo commit rác khi không thể push.
     - Xử lý khi `dirty`:
       - Nếu `action in ("pull", "smart_sync")`: Giữ nguyên bỏ qua an toàn với thông báo `Bỏ qua an toàn: Repo có file chưa commit (Dirty)`.
       - Nếu `action == "push"`: Chạy `git add -A`, sau đó `git commit -m "chore: auto-commit changes before push"`. Bắt lỗi và phân loại hint nếu chưa cấu hình `user.name` / `user.email`.
     - Cập nhật thông báo hoàn tất: Trả về `"Đã commit và push thành công"` khi có tạo commit tự động.

2. **`frontend/js/app.js`:**
   - Trong `btnPushAll.addEventListener`:
     - Lọc `pushRepos = activeRepos.filter(r => r.ahead_count > 0 || r.is_dirty)` thay vì chỉ lọc `ahead_count > 0`.
   - Trong `updateGitCounts()`:
     - Tính `pushCount = activeRepos.filter(r => r.has_remote && (r.ahead_count > 0 || r.is_dirty)).length`.

3. **`tests/test_vxdevsync.py`:**
   - Bổ sung `test_push_dirty_repo_auto_commits_and_pushes`: Giả lập bare remote, repo local dirty, chạy sync_single_repo action push, kiểm tra commit tự động, push lên remote và worktree sạch.
   - Bổ sung `test_push_dirty_repo_without_remote_does_not_commit`: Đảm bảo repo không remote thì không auto-commit.

4. **Tài liệu đặc tả:**
   - `docs/spec/01_business_process.md`: Cập nhật nguyên tắc an toàn kết hợp auto-commit cho push.
   - `docs/spec/02_feature_flow.md`: Cập nhật nhánh sequence diagram cho push trên repo dirty.
   - `docs/spec/05_qa_acceptance.md`: Bổ sung Kịch bản 3.5 kiểm thử chấp nhận.

---

## 3. Nội dung Codex cần tập trung đánh giá

1. **Độ an toàn của Engine Git (`src/git_engine.py`):**
   - Việc kiểm tra remote trước khi auto-commit đã đủ chặt chẽ chưa?
   - Luồng bắt lỗi commit (ví dụ thiếu cấu hình danh tính git, commit hook fail) có an toàn và trả thông báo rõ ràng cho người dùng không?
   - Thao tác `pull` và `smart_sync` có được bảo vệ tuyệt đối khỏi việc vô tình commit hay ghi đè dữ liệu không?
2. **Logic Giao diện Frontend (`frontend/js/app.js`):**
   - Điều kiện `ahead_count > 0 || r.is_dirty` có đồng bộ giữa bộ đếm trên thanh thao tác, nút "Push tất cả" và bảng danh sách repo không?
   - Có trường hợp nào repo bị unbound remote hoặc unborn branch mà nút Push All vẫn cố đẩy không?
3. **Độ bao phủ của Unit Test (`tests/test_vxdevsync.py`):**
   - 2 test case mới đã đủ xác thực hành vi chưa? Có edge case nào tiềm ẩn cần bổ sung test không?
4. **Tính tuân thủ quy chuẩn toàn suite:**
   - Kiểm tra mã nguồn và giao diện: Không emoji, không LaTeX, tiếng Việt chuẩn xác.

---

## 4. Định dạng đầu ra mong muốn
Codex vui lòng xuất báo cáo review ra câu trả lời cuối với cấu trúc:
1. **Tổng quan đánh giá (Executive Summary):** Đạt / Cần điều chỉnh / Đạt có lưu ý.
2. **Phân tích chi tiết từng khía cạnh:**
   - Git Engine & Luồng xử lý an toàn.
   - Frontend UI & Bộ đếm.
   - Test Coverage & Edge Cases.
   - Tính tuân thủ quy chuẩn (AGENTS.md).
3. **Các phát hiện / Rủi ro tiềm ẩn (nếu có):** Nêu rõ mức độ nghiêm trọng (Thấp / Trung bình / Cao) và nguyên nhân.
4. **Khuyến nghị & Kết luận:** Các bước tiếp theo hoặc điểm cần lưu ý khi phát hành.
