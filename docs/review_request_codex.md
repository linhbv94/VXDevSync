# Yêu cầu Tham vấn & Review Chỉ Đọc: Dự án VXDevSync

> **Vai trò:** Tham vấn và Review chỉ đọc (Read-only Consultation).
> **Nguyên tắc:** Chỉ review/nhận xét; không sửa nguồn; không gọi agent khác.
> **Quy chuẩn:** Tuân thủ AGENTS.md (Tiếng Việt chuyên nghiệp, UTF-8, snake_case, Tuyệt đối KHÔNG dùng LaTeX).

---

## 1. Bối cảnh & Mục tiêu

Dự án `vxdevsync/` là ứng dụng Desktop GUI (Python Webview + HTML/CSS/JS thuần theo chuẩn VXUtilities UI) hợp nhất hai công cụ dòng lệnh:
1. `zcli_gitsync`: Quét và đồng bộ hàng loạt repo Git trong workspace.
2. `zcli_skillssync`: Quét và đồng bộ Skills + Rules (`AGENTS.md` ↔ `CLAUDE.md`) giữa Central Library và các AI Agents (Antigravity, Codex, Claude Code).

Đặc biệt giải quyết các bài toán người dùng yêu cầu:
- **Git Sync:** Bảng dữ liệu hỗ trợ **Row-click Selection** (click bất kỳ đâu trên dòng để toggle chọn, trừ nút action), header Checkbox Select All / Changed Only, Floating Action Bar, nút "Smart Sync TẤT CẢ", lưu `scan_path` và recent paths trong `config.json`.
- **Skills Sync:** Bật/tắt agent qua Toggle Cards; nút gộp duy nhất `[ Đồng bộ Tất cả (Kỹ năng & Rules AGENTS.md) ]`; cơ chế đổi Central Library trực tiếp trên UI và Settings.
- **Cascade Delete & Anti-Resurrection:** Xóa vật lý đồng loạt tại Central Library và mọi Agent, lưu `tombstones.json` trong Git repo để khi Máy B pull về sẽ tự động dọn sạch Agent trên Máy B; thực thi Git Commit & Push tức thì ngay khi xác nhận xóa.

---

## 2. Danh mục File Cần Review

### A. Mã nguồn Backend Python (`vxdevsync/src/`)
- `src/main.py`: Khởi tạo cửa sổ 1040×680, bridge API, background `#0f1117`.
- `src/bridge_api.py`: Các methods giao tiếp JS ↔ Python (`get_initial_state`, `scan_git_workspace`, `sync_git_repos`, `get_skills_inventory`, `sync_skills_unified`, `delete_skills_cascade`, `pick_folder`).
- `src/config_manager.py`: Quản lý `config.json` hệ thống (`~/Library/Application Support/VXDevSync/config.json`), recent paths, ignore list, tombstones.
- `src/git_engine.py`: Quét đệ quy `max_depth`, check branch, offset `ahead_count`/`behind_count`, uncommitted files, async sync.
- `src/skills_engine.py`: Quét ma trận inventory, Tombstone sync từ git repo, upstream/downstream sync, cascade delete.
- `src/adapter_engine.py`: Chuyển đổi và phân bổ rules `AGENTS.md` ↔ `CLAUDE.md`.

### B. Mã nguồn Frontend UI (`vxdevsync/frontend/`)
- `frontend/index.html`: Cấu trúc 2 tab, Titlebar 32px chuẩn VXUtilities, Modal Settings 2 nhóm, Modal Cascade Delete, Modal Onboarding.
- `frontend/css/master_theme.css` & `frontend/css/style.css`: Theme Dark `#0f1117`, Electric Cyan, tokens VXUtilities.
- `frontend/js/app.js`: Tương tác UI, Row-click selection, filter repos, agent toggles, toast notifications.

### C. Bộ Kiểm thử Đã chạy PASS (`vxdevsync/tests/test_vxdevsync.py`)
- Đã chạy 5/5 unit tests PASS (initial state, recent paths & ignore, cascade delete & tombstones, rules adapter, git status).

---

## 3. Nội dung Yêu cầu Codex Đánh giá

Vui lòng rà soát và cho nhận xét chi tiết về các khía cạnh:
1. **Kiến trúc & Tính toàn vẹn logic:**
   - Cơ chế Tombstone Manifest (`.vxdevsync/tombstones.json` + `deleted_skills`) có kẽ hở nào có thể khiến skill bị hồi sinh ngoài ý muốn không?
   - Luồng Git Instant Commit & Push khi xóa skill xử lý các trường hợp mạng yếu hoặc branch master/main đã chuẩn chưa?
   - Luồng Rules Adapter giữa `AGENTS.md` và `CLAUDE.md` có bảo toàn nội dung và tương thích tốt không?
2. **Xử lý Ngoại lệ & Edge Cases:**
   - Các trường hợp Git: repo chưa có commit (unborn HEAD), repo detached HEAD, repo không có remote.
   - Các trường hợp đường dẫn thư mục có khoảng trắng, symlink, unicode trên macOS/Windows.
3. **Frontend UI & UX:**
   - Việc bắt sự kiện Row-click selection và phân tách với các nút action trên hàng (`.table-action-btn`) đã tối ưu và mượt mà chưa?
   - Trải nghiệm chuyển đổi tab và đồng bộ cấu hình có điểm nào cần lưu ý?
4. **Đề xuất Cải tiến:**
   - Các khuyến nghị kỹ thuật ngắn gọn, thiết thực để mã nguồn thêm phần vững chắc.
