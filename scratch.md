# VXDevSync — Scratch ý tưởng

Ngày cập nhật: 2026-10-15

## Mục tiêu

Build một app GUI dành cho người dùng AI coding/dev, tổng hợp chức năng của `zcli_skillssync` và `zcli_gitsync` trong cùng một ứng dụng.

- Tên app: **VXDevSync**.
- Thư mục dự án: `vxdevsync`.
- Giữ nguyên hai tool CLI hiện tại; app mới là dự án riêng.
- Đây là scratch đầu vào để user bổ sung scope và tự giao Anti viết spec; chưa phải PRD hoặc spec đã chốt.

## Hướng đã xác định

### 1. Tổng hợp engine của hai CLI

- Rà soát và tái sử dụng logic engine hiện có của cả hai tool; tách phần nghiệp vụ khỏi tương tác Terminal khi cần trong app mới.
- Skills Sync: thư viện skills trung tâm, đồng bộ skills/rules với các AI agent, adapter rules và đồng bộ Git cho thư viện.
- Git Sync: quét workspace nhiều repo, kiểm tra branch/trạng thái, thực hiện các thao tác đồng bộ repo.
- Đọc code thực tế để xác định hành vi hiện có; tài liệu cũ là tham chiếu, không mặc định mọi mô tả đã được triển khai hoặc kiểm chứng.
- Cách đưa engine vào app mới còn cần đánh giá khi viết spec; không sửa hoặc refactor hai dự án CLI trong phạm vi scratch này.

### 2. GUI và visual

- Hướng ưu tiên để khảo sát: Python backend + webview (ví dụ `pywebview`) với giao diện HTML/CSS/JS.
- Chưa chốt framework; cần đánh giá khả năng đóng gói, bridge Python ↔ UI, chạy tác vụ nền và đáp ứng window chrome trên macOS/Windows.
- Visual phải đồng bộ với bộ VX tools: theme, typography, spacing, controls, titlebar và Settings theo quy chuẩn chung.
- Đồng bộ visual không đồng nghĩa bắt buộc dùng cùng framework với các app VX khác.

### 3. Scope mở rộng

Một số scope sẽ lớn hơn hai bản CLI vì GUI gỡ được giới hạn tương tác của Terminal. **User sẽ tự định nghĩa sau.**

- Chưa tự bổ sung tính năng mở rộng hoặc chốt MVP thay user.
- Khi user bổ sung, phân biệt rõ: chức năng kế thừa từ CLI, thay đổi để phù hợp GUI và chức năng mới.

## Nguồn đầu vào cho Anti khi viết spec

| Nhóm | Tài liệu / mã nguồn |
| :--- | :--- |
| Quy tắc workspace | [AGENTS.md](../.agents/AGENTS.md) |
| Chuẩn UI chung VX | [desktop_ui_standards.md](../.agents/desktop_ui_standards.md), [master_theme.md](../_summary/master_theme.md) |
| Skills Sync | [README](../zcli_skillssync/README.md), [main.py](../zcli_skillssync/main.py), [src](../zcli_skillssync/src/), [spec cũ](../zcli_skillssync/docs/spec/) |
| Định hướng GUI Skills Sync trước đây | [06_phase_2_desktop_app.md](../zcli_skillssync/docs/spec/06_phase_2_desktop_app.md) |
| Git Sync | [PRD](../zcli_gitsync/git_sync_prd.md), [src](../zcli_gitsync/src/), [spec cũ](../zcli_gitsync/docs/spec/) |

## Điểm cần làm rõ trong spec

- Phạm vi chức năng cụ thể sau khi user bổ sung scope.
- Cách tích hợp và đóng gói engine để app mới hoạt động độc lập với thư mục source của hai CLI.
- Cấu hình của app mới và cách nhập cấu hình cũ nếu có nhu cầu; không tự ghi đè cấu hình CLI.
- Tránh hai luồng Skills Sync và Git Sync cùng thao tác trên một repo/thư mục.
- Hành vi xem trước thay đổi, xử lý conflict, ghi đè, xóa, force/reset và phục hồi; không mặc định bê nguyên các thao tác mạnh của CLI thành hành động một nút.
- Cơ chế chọn phiên bản skills/rules: engine hiện có dùng timestamp ở một số luồng; cần đánh giá khi đưa lên GUI.
- Tiêu chuẩn nghiệm thu engine và GUI theo từng platform; phân biệt source/build checks với runtime/visual đã kiểm chứng.

## User bổ sung scope tại đây (Đã cập nhật 2026-10-15)

### 1. Git Sync
- **Flow thuận tiện:** App dạng `.app` trong `/Applications`, lưu `scan_path` trong config hệ thống, mở lên tự động nạp đúng path và tự động quét. Có nút Open Folder + dropdown Recent Workspaces (tối đa 5 mục) trên Titlebar. Max depth kế thừa engine cũ (`max_depth = 3`).
- **Loại trừ (Exclusion):** Cấu hình linh hoạt trên GUI: quản lý Global Ignore List trong Settings và nút Quick Exclude trực tiếp trên từng repo trong bảng quét.
- **Lựa chọn Repo (Multi-selection):** Bổ sung Checkbox từng repo, Header Select All / Changed Only, Floating Action Bar cho phép: *Sync đã chọn*, *Push đã chọn*, *Pull đã chọn*, kèm nút *Sync Tất cả* 1-click.

### 2. Skills Sync
- **Flow thuận tiện:** Tự động nạp config của Agents và Skills Library từ file config dùng chung.
- **Cơ chế tick chọn Agents:** Chuyển từ config CLI (0/1) thành Agent Toggle Cards / Checkboxes trực quan trên UI với trạng thái realtime.
- **Xử lý Bad Case xóa skill (Resurrection Bug):** Bổ sung bảng ma trận Skills Inventory, cơ chế **Cascade Delete** (xóa đồng loạt tại Thư viện và tất cả Agents) kết hợp **Tombstone Manifest** (`deleted_skills` trong config) để ngăn chặn triệt để việc hồi sinh skill khi một Agent offline bật lại.

### 3. Tổng quan VXDevSync
- **Tab mặc định:** Git Sync.
- **File config dùng chung:** 1 file `config.json` duy nhất lưu tại `Application Support/VXDevSync/config.json` (macOS) hoặc `%APPDATA%\VXDevSync\config.json` (Windows).
- **Luồng Onboarding lần đầu:** Welcome Wizard 2 bước (Bước 1: Git Sync Workspace, Bước 2: Skills Library & Auto-detect Agents), hoàn tất vào thẳng Git Sync Dashboard.

---

## Bộ Tài liệu Đặc tả Hoàn chỉnh (Specification Package)

Đã hoàn thiện bộ tài liệu đặc tả chuẩn hóa theo quy chuẩn VXUtilities tại thư mục `docs/spec/`:

1. [00_system_overview.md](docs/spec/00_system_overview.md): Tổng quan hệ thống, kiến trúc Desktop Webview, phân tích đối sánh.
2. [01_business_process.md](docs/spec/01_business_process.md): Quy trình nghiệp vụ Onboarding, Git Multi-Sync, Skills Auto-Sync, Cascade Delete & Tombstone.
3. [02_feature_flow.md](docs/spec/02_feature_flow.md): Chi tiết các luồng tính năng, sequence diagrams, chuyển đổi trạng thái.
4. [03_ui_wireframe.md](docs/spec/03_ui_wireframe.md): Đặc tả giao diện chi tiết, Titlebar 32px, Git Sync Dashboard, Skills Inventory, Settings Modal chuẩn VXUtilities.
5. [04_api_data.md](docs/spec/04_api_data.md): Lược đồ `config.json` hợp nhất, Data models nội bộ, Desktop Bridge API.
6. [05_qa_acceptance.md](docs/spec/05_qa_acceptance.md): Bộ tiêu chuẩn nghiệm thu Gherkin scenarios và QA checklist.

