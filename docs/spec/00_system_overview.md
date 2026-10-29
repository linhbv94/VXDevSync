# 00. Tổng quan Hệ thống — VXDevSync
Version: 1.0.0 — Ngày cập nhật: 2026-10-15

Tài liệu này đặc tả kiến trúc tổng thể, mô hình kỹ thuật và định hướng hợp nhất của **VXDevSync** — ứng dụng máy tính (Desktop App) hợp nhất hai công cụ dòng lệnh `zcli_gitsync` và `zcli_skillssync` thành một giải pháp đồng bộ phát triển toàn diện, có giao diện đồ họa hiện đại, trực quan và tối ưu năng suất cho nhà phát triển AI coding.

---

## 1. Bối cảnh & Mục tiêu Sản phẩm

### A. Vấn đề thực tế từ hai công cụ CLI
Trong quy trình làm việc thực tế với AI coding agents (`Antigravity`, `Codex`, `Claude Code`) và nhiều dự án Git cục bộ (`VXUtilities` workspaces):
1. **`zcli_gitsync`:**
   - Hoạt động xuất sắc khi đặt ngay tại thư mục root của workspace: quét nhanh toàn bộ repos, chỉ cần gõ `1` và `Enter` là đồng bộ tự động.
   - **Hạn chế:** Không có giao diện trực quan; khi đóng gói thành ứng dụng macOS `.app` nằm trong `/Applications`, công cụ mất đi vị trí tương đối với workspace; không hỗ trợ chọn/bỏ chọn từng repo theo ý muốn (chỉ có sync all hoặc push/pull all); việc cấu hình loại trừ (ignore) trên CLI phải gõ tay từng dòng.
2. **`zcli_skillssync`:**
   - Tự động hóa tốt việc quản lý và đồng bộ kỹ năng (`skills/`) và quy tắc (`AGENTS.md`) chéo giữa các Agent cục bộ và Central Skills Library.
   - **Hạn chế:** Cấu hình bật/tắt Agent phải chỉnh sửa file `config.json` thủ công (`0` hoặc `1`); **đặc biệt gặp bad case nghiêm trọng:** Khi xóa một skill ra khỏi 1 Agent hoặc Central Library, cơ chế đồng bộ 2 chiều (upstream/downstream) nhận diện nơi còn lại có phiên bản "mới hơn" và tự động sync ngược lại skill đã xóa vào tất cả mọi nơi (hiện tượng hồi sinh skill - Resurrection Bug).

### B. Mục tiêu của VXDevSync
- **Hợp nhất 2 trong 1:** Tạo một ứng dụng Desktop đồ họa duy nhất (`VXDevSync.app` trên macOS và `VXDevSync.exe` trên Windows) quản lý song song hai nghiệp vụ: **Git Multi-Sync** và **Skills Auto-Sync**.
- **Giữ trọn tốc độ & sự tiện lợi của CLI:** Không đánh mất trải nghiệm "1-click Smart Sync", tự động lưu nhớ workspace làm việc gần nhất, mở app là tự động quét và sẵn sàng thao tác.
- **Nâng cấp trải nghiệm người dùng (UX Desktop):**
  - Quản lý danh sách repository với bảng dữ liệu tương tác: Checkbox chọn từng repo, bộ lọc trạng thái, quick action bar.
  - Quản lý danh mục Skills dạng Inventory ma trận: Trực quan hóa vị trí tồn tại của skill trên từng Agent, hỗ trợ xóa triệt để (Cascade Delete) kèm cơ chế chặn hồi sinh (Tombstone Manifest).
  - Gạt toggle bật/tắt từng AI Agent trực tiếp trên giao diện trong 1 click.
- **Chuẩn hóa giao diện VXUtilities:** Kế thừa trọn vẹn quy chuẩn thiết kế [desktop_ui_standards.md](../../../_summary/standard_docs/desktop_ui_standards.md) và [master_theme.md](../../../_summary/standard_docs/master_theme.md).

---

## 2. Kiến trúc Kỹ thuật Tổng thể (Architecture)

Ứng dụng được thiết kế theo mô hình **Desktop Webview Hybrid Architecture** (Python Core Engine + Web Frontend Renderer via `pywebview`), đảm bảo hiệu năng tính toán cao, khả năng tương tác hệ thống sâu của Python mà vẫn mang lại giao diện Web hiện đại, mượt mà.

```text
┌────────────────────────────────────────────────────────────────────────┐
│                        VXDevSync Desktop Window                        │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │  Native Chrome Titlebar (32px, Traffic Lights, Tab Switcher, Menu) │ │
│ └────────────────────────────────────────────────────────────────────┘ │
│ ┌──────────────────────────────────┬─────────────────────────────────┐ │
│ │        Tab 1: Git Multi-Sync     │     Tab 2: Skills Auto-Sync     │ │
│ │  - Workspace Root & Recent Paths │  - Central Skills Library Card  │ │
│ │  - Repos Table (Checkboxes)      │  - Agent Toggle Cards (Anti...) │ │
│ │  - Status Badges & Quick Exclude │  - Skills Inventory & Cascade Del│ │
│ │  - Smart Sync / Push / Pull Bars │  - Upstream & Downstream Sync   │ │
│ └──────────────────────────────────┴─────────────────────────────────┘ │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │                      Shared Settings Modal                         │ │
│ │  General | Git Sync Config | Skills Sync Config | Updates | About  │ │
│ └────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ pywebview JS Bridge (JSON RPC)
┌───────────────────────────────────|────────────────────────────────────┐
│                       Python Backend Core Engine                       │
│ ┌───────────────────────┐ ┌──────────────────────┐ ┌─────────────────┐ │
│ │     Git Sync Engine   │ │  Skills Sync Engine  │ │ Config Manager  │ │
│ │ - Multi-repo Scanner  │ │ - Upstream Scanner   │ │ - Load/Save     │ │
│ │ - Async Git Commands  │ │ - Downstream Deploy  │ │ - Auto Migr.    │ │
│ │ - Concurrency Pool    │ │ - Tombstone Manifest │ │ - OS Paths      │ │
│ └───────────────────────┘ └──────────────────────┘ └─────────────────┘ │
│ ┌────────────────────────────────────────────────────────────────────┐ │
│ │              Rules Adapter Engine (AGENTS.md ↔ CLAUDE.md)          │ │
│ └────────────────────────────────────────────────────────────────────┘ │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │ File System & OS Shell
┌───────────────────────────────────|────────────────────────────────────┐
│                           Hệ thống Cục bộ                              │
│  - Application Support / AppData (config.json dùng chung duy nhất)     │
│  - Workspaces / Repositories trên đĩa cứng                             │
│  - Agent Folders: ~/.gemini/config, ~/.codex, ~/.claude                │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 3. Các Trụ Cột Nâng Cấp Giải Quyết Yêu Cầu User

| Nhóm chức năng | Hành vi CLI hiện tại | Giải pháp Đột phá trên VXDevSync GUI |
| :--- | :--- | :--- |
| **1. Đường dẫn quét Git** | Phụ thuộc vào vị trí file chạy tool; tool phải nằm cùng thư mục cha với các repo. | **Auto-remember & Quick Switch:** Lưu `scan_path` vào config hệ thống. Khi mở app tự động nạp đường dẫn cũ. Nút Open Folder trên Titlebar có dropdown lưu **tối đa 5 thư mục gần đây (Recent Workspaces)**, click là quét ngay. |
| **2. Loại trừ Repo (Ignore)** | Phải cấu hình bằng tay trong menu text của CLI hoặc sửa file JSON thô. | **Trực quan 2 cấp độ:** (1) Quản lý Global Ignore List trong Settings; (2) Nút Exclude nhanh ngay trên từng hàng repo trong bảng để bỏ qua không quét/không hiển thị. |
| **3. Lựa chọn Repo để Sync** | Chỉ có 3 lựa chọn cứng: Sync Tất cả, Push Tất cả, Pull Tất cả. Không thể tick chọn. | **Checkbox Multi-selection:** Checkbox từng repo, Header Select All / Changed Only, Floating Action Bar với các nút: *Sync đã chọn*, *Push đã chọn*, *Pull đã chọn*, kèm nút *Sync Tất cả* 1-click. |
| **4. Bật/Tắt AI Agents** | Chỉnh số `1` hoặc `0` trong file config CLI. | **Agent Toggle Cards:** Hiển thị thẻ card cho từng Agent (Antigravity, Codex, Claude Code) kèm biểu tượng, đường dẫn thực tế, số skills hiện có và nút gạt Toggle realtime. |
| **5. Xóa Skill & Chống Hồi Sinh** | Xóa ở 1 nơi sẽ bị nơi khác coi là bản mới và sync ngược lại tất cả mọi nơi (Bad case). | **Cascade Delete & Tombstone Manifest:** Giao diện Skills Inventory liệt kê toàn bộ skills; nút Delete thực hiện xóa đồng thời ở Library và toàn bộ Agents; ghi nhận vào `deleted_skills` (Tombstone) để chặn triệt để việc hồi sinh từ agent offline. |
| **6. Cấu hình dùng chung** | 2 CLI có 2 file config riêng biệt ở 2 vị trí khác nhau. | **Hợp nhất 1 file config.json:** Lưu tại `Application Support/VXDevSync/config.json` (macOS) hoặc `%APPDATA%\VXDevSync\config.json` (Windows) quản lý toàn bộ cấu hình 2 mode. |
| **7. Trải nghiệm Khởi động** | CLI mở lên vào menu text hoặc prompt hỏi cấu hình dòng lệnh. | **Onboarding Wizard 2 bước:** Tự động mở khi lần đầu cài đặt, tự động phát hiện đường dẫn Agent, cho phép chọn Workspace Root và vào thẳng Dashboard Git Sync. |

---

## 4. Cấu trúc Tài liệu Đặc tả (Documentation Map)

Hệ thống tài liệu đặc tả của VXDevSync được phân rã chuẩn hóa thành các tài liệu kỹ thuật sau:

1. [00_system_overview.md](00_system_overview.md) *(Tài liệu này)*: Tổng quan hệ thống, kiến trúc tổng thể, mô hình giải pháp.
2. [01_business_process.md](01_business_process.md): Sơ đồ quy trình nghiệp vụ tổng thể (Onboarding, Git Sync, Skills Sync, Cascade Delete).
3. [02_feature_flow.md](02_feature_flow.md): Đặc tả chi tiết các luồng tính năng, logic chuyển đổi trạng thái và xử lý lỗi.
4. [03_ui_wireframe.md](03_ui_wireframe.md): Thiết kế giao diện chi tiết, wireframe ASCII/layout, tokens UI theo chuẩn VXUtilities.
5. [04_api_data.md](04_api_data.md): Cấu trúc dữ liệu `config.json` hợp nhất, schema nội bộ và hợp đồng Desktop Bridge API.
6. [05_qa_acceptance.md](05_qa_acceptance.md): Bộ tiêu chuẩn nghiệm thu (Gherkin Scenarios), ma trận kiểm thử và danh mục checklist.

## Gate phát hành1.0.0 — QA độc lập2026-10-26

[QA và sửa lỗi thực tế](../release_1_0_0_review.md) ưu tiên hơn các tuyên bố hoàn tất trước đây. Inventory chỉ đọc; Sync không gom file ngoài phạm vi, dirty/staged/diverged phải safe-skip, tên skill không được thoát root/protected folders. Cấu hình lỗi giữ nguyên và có previous backup. Updater Python dùng signed manifest Ed25519/digest, Updates tab/startup check, mutation guard và staging/rollback; không dùng schema Tauri. Windows và haiMac có cùng engine, installer/updater khác nhau. [Vận hành](../desktop_release.md).
