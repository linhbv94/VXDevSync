# VXDevSync — Unified Git Multi-Sync & AI Skills Synchronizer

[![Release](https://img.shields.io/github/v/release/linhbv94/VXDevSync?style=flat-square&color=06b6d4)](https://github.com/linhbv94/VXDevSync/releases/latest)
[![Platform](https://img.shields.io/badge/platform-macOS%20%7C%20Windows-0284c7?style=flat-square)](https://github.com/linhbv94/VXDevSync/releases/latest)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg?style=flat-square)](LICENSE)
[![Ecosystem](https://img.shields.io/badge/part%20of-VXUtilities-0ea5e9?style=flat-square)](../_summary/master_overview.md)

**VXDevSync** là ứng dụng desktop cá nhân hợp nhất hai công cụ vận hành cốt lõi trong quy trình phát triển phần mềm:
1. **Git Multi-Sync:** Quét và quản lý đồng bộ hàng loạt kho lưu trữ Git cục bộ với remote (GitHub, GitLab), hỗ trợ chọn dòng linh hoạt (Row-click Selection), lọc dirty/ahead/behind và Smart Sync 1-click.
2. **Skills Auto-Sync:** Quản lý và đồng bộ kỹ năng (Skills Library) và quy tắc (`AGENTS.md` ↔ `CLAUDE.md`) giữa Central Library và các AI Agents (Antigravity, Codex, Claude Code), xử lý triệt để lỗi hồi sinh kỹ năng (Resurrection Bug) qua cơ chế Cascade Delete và Tombstone Manifest.

> **Tôn chỉ:** *Tự động hóa đồng bộ mã nguồn & kỹ năng AI, an toàn dữ liệu, giao diện Native Webview siêu mượt.*  
> **Phiên bản hiện tại:** `v1.0.5` — Thành viên trong hệ sinh thái [VXUtilities](../_summary/master_overview.md).

---

## 1. Tính năng nổi bật

* **Quản trị Git đa kho lưu trữ (Git Multi-Sync):**
  * Quét đệ quy toàn bộ thư mục làm việc để phát hiện các Git repo.
  * Phân loại trạng thái tức thì: `DIRTY` (có file chưa commit), `AHEAD` (cần push), `BEHIND` (cần pull), `UP_TO_DATE`.
  * Đồng bộ thông minh 1-click (Smart Sync) an toàn, tránh ghi đè xung đột.
* **Đồng bộ Kỹ năng & Quy tắc AI Agents (Skills Auto-Sync):**
  * Quét ma trận skills giữa thư mục chuẩn (`~/.gemini/config/skills/`) và các workspace dự án.
  * Đồng bộ 2 chiều quy tắc hoạt động của các AI Agent (`AGENTS.md` ↔ `CLAUDE.md`).
  * Cơ chế **Cascade Delete** kết hợp Tombstone Manifest đảm bảo khi xóa 1 skill ở thư viện gốc, skill đó sẽ không bị "hồi sinh" vô thức từ các workspace con.
* **Tự động cập nhật trực tiếp (Auto-Update):** Tích hợp thông báo cập nhật góc dưới màn hình, tải và cài đặt phiên bản mới chỉ với 1-click.

---

## 2. Tải xuống & Cài đặt

Tải bản phát hành mới nhất dành cho hệ điều hành của bạn tại [GitHub Releases](https://github.com/linhbv94/VXDevSync/releases/latest):

* **macOS (Apple Silicon & Intel):** Tải tệp `.dmg` hoặc `.app.tar.gz`. Kéo ứng dụng vào thư mục `/Applications`.
* **Windows (x64):** Tải bộ cài `.msi` hoặc tệp thực thi `.exe` độc lập.

---

## 3. Kiến Trúc Hệ Thống (Tech Stack)

* **Desktop Host:** Python 3.9+ kết hợp `pywebview` (Native WebKit trên macOS Cocoa, WebView2 trên Windows).
  * `src/main.py`: Entry point khởi tạo cửa sổ native window 1040×680 chuẩn VXUtilities.
  * `src/bridge_api.py`: API Bridge hai chiều bất đồng bộ giữa JavaScript và Python.
  * `src/config_manager.py`: Quản lý cấu hình tập trung, recent paths, ignore list và tombstones.
  * `src/git_engine.py`: Quét đệ quy, phân tích commit offset (+ahead / -behind) và thực thi pull/push.
  * `src/skills_engine.py`: Quét ma trận skills, phân bổ downstream, thu thập upstream và cascade delete.
  * `src/adapter_engine.py`: Chuẩn hóa quy tắc 2 chiều giữa `AGENTS.md` và `CLAUDE.md`.
* **Frontend UI:** HTML5, CSS3 Tokens chuẩn VXUtilities Dark (`#0f1117`), JavaScript thuần ES6+.
* **Cấu hình lưu trữ:** `~/Library/Application Support/VXDevSync/config.json` (macOS) hoặc `%APPDATA%\VXDevSync\config.json` (Windows).

---

## 4. Hướng dẫn Phát triển & Biên dịch

### Khởi chạy môi trường phát triển
```bash
# Cài đặt và khởi chạy trực tiếp qua run script
./run.sh
```
*Script sẽ tự động tạo virtualenv `.venv`, cài đặt thư viện cần thiết (`pywebview`, `pyobjc`) và mở ứng dụng.*

### Đóng gói ứng dụng macOS (.app)
```bash
./build_macos.sh
# Gói ứng dụng độc lập sẽ nằm tại dist/VXDevSync.app
```

### Chạy kiểm thử tự động (Unit Tests)
```bash
./.venv/bin/python -m scripts.run_tests
```

---

## 5. Tài Liệu Đặc Tả Kỹ Thuật (Specification Suite)

Toàn bộ tài liệu phân tích và thiết kế chi tiết nằm tại `docs/spec/`:
* 📋 `00_system_overview.md`: Tổng quan kiến trúc & phân rã module.
* 🔄 `01_business_process.md`: Quy trình nghiệp vụ Git Sync, Skills Sync và Cascade Delete.
* ⚙️ `02_feature_flow.md`: Luồng tương tác & Sequence Diagrams.
* 🎨 `03_ui_wireframe.md`: Thiết kế giao diện & bố cục màn hình.
* 🔌 `04_api_data.md`: Cấu trúc dữ liệu & Data Contracts.
* 🧪 `05_qa_acceptance.md`: Tiêu chuẩn kiểm thử và kịch bản nghiệm thu Gherkin.

---

## 6. Giấy phép & Bản quyền (License)

Dự án được phân phối dưới giấy phép mã nguồn mở **MIT License**.  
Xem toàn văn giấy phép tại tệp [LICENSE](LICENSE).

Bản quyền © 2026 Viet Linh Bui. Đã đăng ký toàn bộ quyền.
