# VXDevSync (Desktop GUI)

Ứng dụng Desktop hợp nhất hai công cụ cốt lõi trong hệ sinh thái VXUtilities:
1. **Git Multi-Sync:** Quét và quản lý đồng bộ hàng loạt kho lưu trữ Git cục bộ với remote (GitHub, GitLab), hỗ trợ đa chọn dòng (Row-click Selection), lọc dirty/ahead/behind và Smart Sync 1-click.
2. **Skills Auto-Sync:** Quản lý và đồng bộ kỹ năng (Skills Library) và quy tắc đạo đức (`AGENTS.md` ↔ `CLAUDE.md`) giữa Central Library và các AI Agents (Antigravity, Codex, Claude Code), xử lý triệt để bug hồi sinh kỹ năng (Resurrection Bug) qua Cascade Delete và Tombstone Manifest.

---

## Khởi Chạy Nhanh

```bash
cd vxdevsync
./run.sh
```

Script sẽ tự động kiểm tra/tạo môi trường ảo `.venv`, cài đặt các thư viện cần thiết (`pywebview`, `pyobjc`) và mở cửa sổ Native Desktop Webview.

---

## Kiến Trúc Hệ Thống

- **Cấu hình chung:** Lưu tại `~/Library/Application Support/VXDevSync/config.json` (macOS) hoặc `%APPDATA%\VXDevSync\config.json` (Windows).
- **Backend:** Python 3.9+ (`pywebview` Desktop Native WebKit/Cocoa).
  - `src/main.py`: Entry point khởi tạo cửa sổ native window 1040×680 chuẩn VXUtilities.
  - `src/bridge_api.py`: API Bridge hai chiều giữa JavaScript và Python.
  - `src/config_manager.py`: Quản lý cấu hình tập trung, recent paths, ignore list và tombstones.
  - `src/git_engine.py`: Quét đệ quy, phân tích commit offset (+ahead / -behind) và thực thi pull/push bất đồng bộ.
  - `src/skills_engine.py`: Quét ma trận skills, phân bổ downstream, thu thập upstream và cascade delete.
  - `src/adapter_engine.py`: Chuẩn hóa quy tắc 2 chiều giữa `AGENTS.md` và `CLAUDE.md`.
- **Frontend:** HTML5, CSS3 Tokens chuẩn VXUtilities Dark (`#0f1117`), JavaScript thuần ES6+.
  - `frontend/index.html`: Cấu trúc 2 tab, Titlebar chuẩn 32px, Settings Modal 2 nhóm sidebar, Onboarding Wizard.
  - `frontend/css/master_theme.css`: Bảng màu, typography và tokens VXUtilities.
  - `frontend/css/style.css`: Giao diện hiện đại, row-click hover/selection, floating action bar.
  - `frontend/js/app.js`: Tương tác UI mượt mà, toast notifications, realtime updates.

---

## Đóng Gói macOS Bundle (.app)

Để đóng gói thành ứng dụng macOS độc lập kèm icon app:

```bash
cd vxdevsync
./build_macos.sh
```

Kết quả build sẽ nằm tại `dist/VXDevSync.app` (dung lượng ~15MB, đã ký ad-hoc codesign). Bạn có thể mở trực tiếp hoặc kéo vào `/Applications`:

```bash
open dist/VXDevSync.app
```

---

## Chạy Kiểm Thử Tự Động (Unit Tests)

```bash
cd vxdevsync
./.venv/bin/python -m scripts.run_tests
```

---

## Tài Liệu Đặc Tả Kỹ Thuật (Specs)

Toàn bộ tài liệu phân tích và thiết kế chi tiết nằm tại `docs/spec/`:
- `00_system_overview.md`: Tổng quan kiến trúc & phân rã module.
- `01_business_process.md`: Quy trình nghiệp vụ Git Sync, Skills Sync và Cascade Delete.
- `02_feature_flow.md`: Luồng tương tác & Sequence Diagrams.
- `03_ui_wireframe.md`: Thiết kế giao diện & bố cục màn hình.
- `04_api_data.md`: Cấu trúc dữ liệu & Data Contracts.
- `05_qa_acceptance.md`: Tiêu chuẩn kiểm thử và kịch bản nghiệm thu Gherkin.

## Phát hành và cập nhật

Tải bộ cài tại [GitHub Releases](https://github.com/linhbv94/VXDevSync/releases). Có bản Windows x64, Mac Apple Silicon và Mac Intel. Cần cài Git để đồng bộ repository. Các bản sau kiểm tra tại Cài đặt → Cập nhật.

Quy trình build, ký updater và publish: [desktop_release.md](docs/desktop_release.md).
