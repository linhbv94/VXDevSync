# 03. Đặc tả Giao diện & Wireframes — VXDevSync
Version: 1.5.0 — Ngày cập nhật: 2026-10-26

Tài liệu này đặc tả toàn diện cấu trúc giao diện người dùng (UI/UX), bố cục màn hình (Layout Wireframes), quy chuẩn phím tắt và các tokens thiết kế của **VXDevSync**, tuân thủ nghiêm ngặt [desktop_ui_standards.md](../../../.agents/desktop_ui_standards.md) và [master_theme.md](../../../_summary/master_theme.md). Tuyệt đối tuân thủ quy chuẩn No-Emoji: 100% icon sử dụng vector SVG (Lucide style) và CSS LED Indicator Dots.

---

## 1. Quy chuẩn Cửa sổ & Thanh Tiêu đề (Chrome Standards)

### A. Thông số Kỹ thuật Chuẩn (Window Metrics)
- **Kích thước cửa sổ mặc định:** Chiều rộng 1040px, Chiều cao 680px (Tối thiểu: 860px × 540px).
- **Thanh trên cùng (Titlebar):**
  - Chiều cao cố định: **32px** (đúng 1 hàng duy nhất).
  - Phông chữ tiêu đề: System Font (`-apple-system, BlinkMacSystemFont, "Segoe UI", Roboto`), cỡ **12px**, `font-weight: 600`.
  - Icon ứng dụng: Kích thước **16px**, khoảng cách giữa Icon và Tên ứng dụng là **6px**.
  - **Trên macOS:** Bộ nút traffic lights native ở góc trái chuẩn kích thước 12pt (đường kính hiển thị 12pt / 24px Retina, khoảng cách tâm 20pt, căn giữa theo trục Y tại 15.5pt); giữ native actions; kế tiếp là nút Open Folder + Dropdown Recent; ở giữa là Pill Mode Switcher; góc phải là nút Settings (Gear icon).
    * *Đảm bảo tương thích AppKit SDK 15.5:* Mach-O binary đóng gói được cấu hình metadata SDK 15.5 thông qua `vtool` để AppKit tự động duy trì kích thước bezel 12pt (frame 14x16), tương đồng 100% với VXMedia và VXmp3.
    * *Duy trì Layout ổn định:* `window_chrome.py` tách biệt 2 pass (unhide toàn bộ trước khi tính toán toạ độ từ content view qua `convertPoint:fromView:`); gắn `NSNotificationCenter` observer theo dõi các sự kiện key/resize/deminiaturize để ngăn chặn AppKit giật nút về vị trí mặc định.
  - **Trên Windows:** Bỏ hoàn toàn titlebar native (`decorations: false`); menu File/Edit bên trái; Pill Mode Switcher ở giữa; đúng 1 bộ nút minimize/maximize/close bên phải.

```text
+--------------------------------------------------------------------------------------------------------------------+
| (o)(o)(o)  [Open Folder v]       |    [ Git Multi-Sync ]   [ Skills Auto-Sync ]         |           [Refresh] [Settings]|
+--------------------------------------------------------------------------------------------------------------------+
```

---

## 2. Màn hình 1: Git Sync Dashboard (Chế độ Mặc định)

Chế độ hiển thị danh sách các repositories trong Workspace hiện tại với hệ thống Checkbox đa chọn và thanh công cụ tác vụ nổi.

```text
+--------------------------------------------------------------------------------------------------------------------+
| (o)(o)(o)  [/Users/vic/_Work v]  |   [ Git Multi-Sync (Active) ]   [ Skills Auto-Sync ] |    [Quét lại] [Cài đặt]          |
+--------------------------------------------------------------------------------------------------------------------+
| Workspace: /Users/vic/_Work  •  Độ sâu: 3  •  Thời gian quét: 0.28s  •  Tìm thấy: 14 repos                         |
|                                                                                                                    |
| [ Bộ lọc: [Tất cả (14)]  [Cần Sync (4)]  [Đã Sạch (9)]  [Dirty/Lỗi (1)] ]   [Tìm kiếm repository...]               |
| [x] Chọn tất cả    [v] Chỉ chọn repo có thay đổi (4)    [Smart Sync thay đổi (4)]  |  Đã chọn: 3 / 14 repos     |
+--------------------------------------------------------------------------------------------------------------------+
| [ ] | Dự án (Repository)     | Nhánh (Branch) | Trạng thái File | Git Sync       | Lệch   | Đề xuất   | Thao tác       |
+-----+------------------------+----------------+-----------------+----------------+--------+-----------+----------------+
| [v] | vxmedia                | main           | [• Clean]       | [↓ Behind (2)] | -2 / 0 | Auto Pull | [o] [↓] [↑]    |
| [v] | vxphotos               | main           | [• Clean]       | [↑ Ahead (1)]  | 0 / +1 | Auto Push | [o] [↓] [↑]    |
| [v] | vxclean                | dev            | [• Dirty (3)]   | [↓ Behind (1)] | -1 / 0 | Safe-Skip | [o] [↓] [↑]    |
| [ ] | vxclick                | main           | [• Clean]       | [• Up-to-date] | 0 / 0  | Up-to-date| [o] [↓] [↑]    |
| [ ] | vxmp3                  | main           | [• Clean]       | [• Up-to-date] | 0 / 0  | Up-to-date| [o] [↓] [↑]    |
| [ ] | zcli_gitsync           | master         | [• Diverged]    | [! Conflict]   | +2 / -3| Man. Merge| [o] [↓] [↑]    |
| --- | ---------------------- | -------------- | --------------- | -------------- | ------ | --------- | -------------- |
| [-] | repo_ignored (Mờ 50%)  | main           | [• Clean]       | [• Loại trừ]   | --     | Đã loại trừ| [x] [-] [-]    |
+--------------------------------------------------------------------------------------------------------------------+
| Thanh Tác vụ Nổi (Floating Batch Action Bar - Phong cách VXPhotos):                                                |
| ┌────────────────────────────────────────────────────────┐                                                         |
| │  [ 3 đã chọn ]  │  [Smart Sync]  [↓ Pull]  [↑ Push]    │  [Bỏ chọn]    │  (Icon-Only buttons, ActionTooltip hover)   |
| └────────────────────────────────────────────────────────┘                                                         |
+--------------------------------------------------------------------------------------------------------------------+
```

### Ý nghĩa & Tương tác trên Bảng Git Sync:
- **Nút "Smart Sync thay đổi (N)" (One-Click Sync):** Đặt trực tiếp tại thanh Selection Bar, cho phép người dùng kích hoạt đồng bộ thông minh tất cả repo đang cần sync (Behind/Ahead/Dirty) chỉ với đúng **1 thao tác click chuột duy nhất**, không cần phải trải qua bước chọn checkbox thủ công.
- **Thanh Tác vụ Nổi (Floating Batch Action Bar):**
  - Kế thừa và đồng bộ quy chuẩn từ `BatchActionBar` của [VXPhotos](../../vxphotos/src/components/BatchActionBar.tsx):
  - **Badge số lượng:** Hiển thị `[3 đã chọn]` nổi bật với viền và nền amber glass.
  - **Dạng nút Icon-Only:** Toàn bộ các nút hành động (`Smart Sync`, `Pull`, `Push`, `Clear Selection`) đều là các khối icon vector SVG sắc nét (32px × 32px), loại bỏ hoàn toàn nhãn chữ dài dòng và emoji.
  - **ActionTooltip on Hover:** Khi hover chuột vào từng nút, hiển thị tooltip giải thích hành động nổi lên phía trên (ví dụ: `Smart Sync đã chọn (Pull & Push)`, `Pull đã chọn (Remote → Local)`, `Push đã chọn (Local → Remote)`, `Bỏ chọn tất cả (Esc)`).
  - **Nút Bỏ chọn & Phím tắt Esc:** Nút icon SVG `X` và phím `Escape` cho phép hủy chọn nhanh toàn bộ repos.
  - **Loại bỏ nút "Smart Sync Tất cả" khỏi thanh nổi:** Thanh nổi chỉ tập trung vào nhóm repo đang được chọn; tác vụ đồng bộ tổng thể đã được đảm nhiệm tối ưu bởi nút "Smart Sync thay đổi" tại Selection Bar.
- **Click chọn cả dòng (Row-click Selection):** Người dùng có thể **click vào bất kỳ vị trí nào trên cả dòng** (hàng của repo) để chọn hoặc bỏ chọn repo đó, không bắt buộc phải click trúng ô checkbox nhỏ.
  - *Ngoại lệ an toàn:* Khi click trực tiếp vào các nút hành động trên dòng (Exclude, Pull, Push) thì chỉ thực thi hành động đó, không kích hoạt toggle chọn dòng.
- **Nút "Chỉ chọn repo có thay đổi" (Select Changed Only):** Tự động lọc và tick chọn các repo có trạng thái `Behind` hoặc `Ahead` hoặc `Dirty` (bỏ qua repo đã bị loại trừ).
- **Hành vi Repo bị loại trừ (Git Sync Exclude):**
  - Không biến mất khỏi giao diện mà **vẫn hiển thị trong danh sách**.
  - **Tự động đẩy xuống cuối bảng** và hiển thị mờ (`opacity: 0.45`, `filter: grayscale(0.5)`).
  - Ô checkbox của repo bị loại trừ bị vô hiệu hóa (`disabled`), không tham gia vào `Chọn tất cả`.
  - Nút con mắt trên dòng repo bị loại trừ chuyển sang biểu tượng `Eye` (mở mắt) để cho phép người dùng **bấm lại khôi phục (Unignore/Include)** đưa repo trở lại trạng thái bình thường.
  - Mọi thao tác loại trừ hoặc khôi phục đều **đồng bộ tức thì vào danh sách loại trừ trong Modal Cài đặt (Settings)** và file `config.json`.
- **Hệ thống Icon Vector SVG thay thế Emoji:**
  - Toàn bộ các icon nút dòng (`Exclude/Unexclude`, `Pull`, `Push`, `Delete Skill`) và các badge trạng thái đều sử dụng vector SVG sắc nét (Lucide/Feather style), đồng bộ diện mạo ứng dụng desktop hiện đại, không sử dụng emoji hệ điều hành.
- **Cột Thao tác:**
  - Nút con mắt (Quick Exclude / Unexclude): Vector SVG EyeOff / Eye để toggle trạng thái loại trừ repo.
  - Nút Mũi tên xuống (Pull Only): Vector SVG ArrowDownToLine để kéo commit mới cho riêng repo này.
  - Nút Mũi tên lên (Push Only): Vector SVG ArrowUpFromLine để đẩy commit lên cho riêng repo này.

---

## 3. Màn hình 2: Skills Sync Dashboard

Chế độ quản lý thư viện kỹ năng trung tâm và đồng bộ chéo với các AI Agents cục bộ.

```text
+--------------------------------------------------------------------------------------------------------------------+
| (o)(o)(o)  [Central Library v]       |   [ Git Multi-Sync ]   [ Skills Auto-Sync (Active) ] |  [Kiểm tra] [Cài đặt]        |
+--------------------------------------------------------------------------------------------------------------------+
| Central Skills Library: /Users/vic/my_skills_library  [Git Ready]                               [Đổi Thư viện...]   |
|                                                                                                                    |
| ┌──────────────────────────────┐  ┌──────────────────────────────┐  ┌──────────────────────────────┐               |
| │ [SVG Agy]  Antigravity   (O) │  │ [SVG Codex]  Codex       (O) │  │ [SVG Claude] Claude Code ( ) │               |
| │            ~/.gemini/config  │  │              ~/.codex        │  │              ~/.claude       │               |
| │ ---------------------------- │  │ ---------------------------- │  │ ---------------------------- │               |
| │ [•] Đang kích hoạt 34 skills │  │ [•] Đang kích hoạt 34 skills │  │ [ ] Chưa kích hoạt  0 skills │               |
| └──────────────────────────────┘  └──────────────────────────────┘  └──────────────────────────────┘               |
|                                                                                                                    |
| Ma trận Kỹ năng (Skills Inventory - 34 skills)                                   [Tìm kiếm kỹ năng...]             |
+--------------------------------------------------------------------------------------------------------------------+
| Tên Kỹ Năng (Skill Name)   | Central Library | Antigravity     | Codex           | Claude Code     | Thao tác       |
+----------------------------+-----------------+-----------------+-----------------+-----------------+----------------+
| _spec0_system              | [• Có mặt]      | [• Đồng bộ]     | [• Đồng bộ]     | [• Chưa có]     | [Xóa]          |
| _spec1_business_process    | [• Có mặt]      | [• Đồng bộ]     | [• Đồng bộ]     | [• Chưa có]     | [Xóa]          |
| _uxui0_core                | [• Có mặt]      | [• Lệch hash]   | [• Đồng bộ]     | [• Chưa có]     | [Xóa]          |
| _devops1_desktop_release   | [• Có mặt]      | [• Đồng bộ]     | [• Đồng bộ]     | [• Chưa có]     | [Xóa]          |
+--------------------------------------------------------------------------------------------------------------------+
| Sẵn sàng đồng bộ Kỹ năng và Quy tắc AGENTS.md / CLAUDE.md.     [Đồng bộ Tất cả (Kỹ năng & Rules AGENTS.md)]         |
+--------------------------------------------------------------------------------------------------------------------+
```

### Ý nghĩa & Tương tác trên Bảng Skills Sync:
- **Layout Card Agent Mới Chuẩn Hóa:**
  - **Brand Logo SVG:** Sử dụng vector SVG chính thức (`Ag-Agy.svg`, `Ag-Codex.svg`, `Ag-Claude.svg`) từ thư mục `public/`.
  - **Thích ứng Đa Chế độ (Light/Dark Mode Adaptation):**
    - Thiết lập `fill: currentColor` trong SVG kết hợp biến CSS `--text-primary` và media query `prefers-color-scheme`.
    - Trên Dark Mode: Logo hiển thị màu trắng sáng tinh tế trên nền thẻ tối.
    - Trên Light Mode: Logo tự động chuyển sang màu tối tương phản rõ nét (`#0f172a`), không bao giờ bị chìm/tàng hình.
  - **Bố cục 2 Tầng Tinh Gọn:**
    - Tầng trên: Cột bên trái gồm Logo SVG (34px) đặt cạnh Tên Agent (14px, Bold) và Đường dẫn cấu hình (11px, Monospace); Cột bên phải là Switch toggle (38px × 22px).
    - Đường Divider ngăn cách ngang mỏng và thanh thoát.
    - Tầng dưới: Đèn LED báo trạng thái 3D (`.status-dot` xanh khi ON, xám khi OFF) kèm chữ mô tả, bên phải là Badge bo góc đếm số lượng kỹ năng của riêng Agent đó.
  - **Loại bỏ hoàn toàn Emoji:** Sử dụng hệ thống đèn LED trạng thái CSS (`.badge-dot`) và vector SVG Lucide sắc nét, tuyệt đối không dùng emoji hệ điều hành.
- **Đổi Central Skills Library tức thì:** Nút `[Đổi Thư viện...]` ngay trên card thư viện cho phép mở hộp thoại native chọn lại folder Central Library mà không bắt buộc phải vào sâu trong Settings.
- **Đồng bộ Hợp nhất (Unified Smart Sync):** Gộp chung tiến trình đồng bộ Kỹ năng (`skills/`) và Quy tắc (`AGENTS.md` ↔ `CLAUDE.md`) vào đúng **1 nút bấm duy nhất**: `[Đồng bộ Tất cả (Kỹ năng & Rules AGENTS.md)]`. Loại bỏ hoàn toàn sự phân mảnh 2 nút thừa thãi.
- **Card Agent Toggle:** Người dùng click vào nút Switch `[ON] / [OFF]` trên từng thẻ để kích hoạt hoặc bỏ qua Agent đó trong phiên đồng bộ.
- **Nút "Xóa" (Delete):** Kích hoạt luồng Cascade Delete an toàn.


---

## 4. Màn hình 3: Hộp thoại Xóa Kỹ năng An toàn (Cascade Delete Modal)

Khi người dùng bấm nút xóa một kỹ năng, hộp thoại cảnh báo nguy hiểm xuất hiện để ngăn chặn việc hồi sinh kỹ năng ngoài ý muốn.

```text
+-----------------------------------------------------------------------+
| [!] XÁC NHẬN XÓA VĨNH VIỄN KỸ NĂNG                                    |
+-----------------------------------------------------------------------+
| Bạn có chắc chắn muốn xóa kỹ năng: `_mkt9_obsolete_test`?             |
|                                                                       |
| Hệ thống sẽ thực hiện xóa vật lý đồng thời tại các vị trí sau:        |
|  [v] Central Skills Library: /Users/vic/my_skills_library/skills/...  |
|  [v] Antigravity Config: ~/.gemini/config/skills/_mkt9_obsolete_test  |
|  [v] Codex Config: ~/.codex/skills/_mkt9_obsolete_test                |
|                                                                       |
| Đồng bộ Git & GitHub tức thì (Instant Commit & Push):                 |
|  Thao tác xóa sẽ được commit và push lên GitHub ngay lập tức          |
|  (không đợi đóng app), giúp các thiết bị khác đồng bộ sạch sẽ ngay.   |
|                                                                       |
| Cơ chế Chống Hồi sinh (Tombstone Manifest):                           |
|  Kỹ năng này sẽ được ghi vào `.vxdevsync/tombstones.json`. Khi các    |
|  máy khác pull về, hệ thống sẽ tự động dọn dẹp Agent trên máy đó.     |
|                                                                       |
|             [ Hủy bỏ (Esc) ]            [ Xóa Triệt Để Ngay ]         |
+-----------------------------------------------------------------------+
```

---

## 5. Màn hình 4: Hộp thoại Cài đặt (Settings Modal)

Tuân thủ nghiêm ngặt chuẩn cấu trúc Sidebar 2 nhóm của zTools:

```text
+-----------------------------------------------------------------------------------------+
| Cài đặt VXDevSync                                                                [x] Đóng|
+--------------------------+--------------------------------------------------------------+
| [Nhóm Tính Năng]         | CẤU HÌNH GIT MULTI-SYNC                                      |
| • Chung (General)        |                                                              |
| • Git Sync (Đang chọn)   | Thư mục Quét Mặc định (scan_path):                           |
| • Skills Sync            | [/Users/vic/_Work                               ] [Duyệt...] |
|                          |                                                              |
| ------------------------ | Độ sâu quét tối đa (max_depth):                              |
| [Nhóm Thông Tin]         | [ 3 ] (Từ 1 đến 10 cấp thư mục con)                         |
| • Cập nhật (Updates)     |                                                              |
| • Giới thiệu (About)     | Danh sách Thư mục Loại trừ (Ignore List):                    |
| • Ủng hộ tác giả (Support)| +----------------------------------------------------------+ |
|                          | | node_modules                                      [Xóa]  | |
|                          | | venv                                              [Xóa]  | |
|                          | | .venv                                             [Xóa]  | |
|                          | | build, dist                                       [Xóa]  | |
|                          | +----------------------------------------------------------+ |
|                          | [Nhập tên thư mục cần bỏ qua...]              [+ Thêm]      |
|                          |                                                              |
|                          | Số luồng quét đồng thời (Concurrency): [ 8 ]                |
+--------------------------+--------------------------------------------------------------+
| [ Khôi phục mặc định ]                                                    [ Lưu & Đóng ]|
+-----------------------------------------------------------------------------------------+
```text
+-----------------------------------------------------------------------------------------+
| Cài đặt VXDevSync                                                                [x] Đóng|
+--------------------------+--------------------------------------------------------------+
| [Nhóm Tính Năng]         | CẤU HÌNH SKILLS AUTO-SYNC                                    |
| • Chung (General)        |                                                              |
| • Git Sync               | Thư mục Central Skills Library (skills_lib):                 |
| • Skills Sync (Đang chọn)| [/Users/vic/my_skills_library                   ] [Duyệt...] |
|                          | [•] Thư mục hợp lệ • Git: main (Up-to-date) • 34 skills       |
| ------------------------ |                                                              |
| [Nhóm Thông Tin]         | Git Remote URL (Tùy chọn, để trống nếu dùng Offline):        |
| • Cập nhật (Updates)     | [https://github.com/linhbv94/my_skills_library.git         ] |
| • Giới thiệu (About)     |                                                              |
| • Ủng hộ tác giả (Support)| Quản lý Kỹ năng đã Xóa (Tombstone Manifest):                 |
|                          | +----------------------------------------------------------+ |
|                          | | _mkt9_obsolete_test (Xóa ngày 15/10/2026)    [Khôi phục] | |
|                          | +----------------------------------------------------------+ |
|                          |                                                              |
|                          | Đường dẫn Agent Tùy chỉnh (Mặc định tự động nhận diện):      |
|                          | • Antigravity: ~/.gemini/config                              |
|                          | • Codex:       ~/.codex                                      |
|                          | • Claude Code: ~/.claude                                     |
+--------------------------+--------------------------------------------------------------+
| [ Khôi phục mặc định ]                                                    [ Lưu & Đóng ]|
+-----------------------------------------------------------------------------------------+
```

### Chi tiết các Tab trong Settings:
1. **Chung (General):** Ngôn ngữ (Tiếng Việt / English), Theme (Dark Navy `#0f1117` mặc định / Light), Tab mặc định khi mở app (Git Sync / Skills Sync).
2. **Git Sync:** Cấu hình `scan_path`, `max_depth`, `ignore_list`, `max_concurrency`, `timeout`.
3. **Skills Sync:** 
   - **Thay đổi Central Library (`skills_lib`):** Nút `[Duyệt...]` mở hộp thoại chọn thư mục; tự động kiểm tra Git repo và đếm số skills.
   - **Git Remote URL:** Cấu hình link GitHub repo để đồng bộ từ xa (hoặc để trống nếu chỉ dùng offline cục bộ).
   - **Quản lý Tombstone Manifest:** Xem danh sách skills đã bị khai tử và nút "Khôi phục" (Restore).
4. **Cập nhật (Updates):** Card kiểm tra phiên bản mới từ GitHub Releases (`linhbv94/VXDevSync`) và updater thật.
5. **Giới thiệu (About):** Biểu tượng, Tên app `VXDevSync`, Phiên bản `1.0.0`, Tác giả Bùi Việt Linh, Mô tả ngắn 2-3 câu về công cụ đồng bộ nhà phát triển.
6. **Ủng hộ tác giả (Support Author):** Menu nổi bật màu hổ phách (`Coffee` icon), mã QR VietQR (Vietcombank) nền trắng sắc nét đặt ở vị trí trung tâm để người dùng quét trực tiếp từ app ngân hàng.



## Đồng bộ chrome/control bar — 2026-10-15 (ưu tiên sơ đồ cũ)

- Một hàng titlebar32px. Mac giữ traffic lights native nguyên geometry/padding và chỉ căn vị trí, icon16px + gap6px + tên12px/600 tại x82px. Open Workspace/recent và Settings bên phải. Không còn titlebar native riêng phía trên.
- Windows frameless: File/View menus trái, ẩn branding/spacer Mac; đúng một cụm minimize/maximize/close phải. Vùng trống kéo cửa sổ, không kéo khi bấm controls/menus/recent. Linux giữ chrome native hiện có, chưa thuộc QA lượt này.
- Control bar riêng44px ngay dưới titlebar: Git Multi-Sync/Skills Auto-Sync bên trái, Quét lại bên phải; giữ IDs, handlers và nghiệp vụ cũ. Không dồn pill lớn vào titlebar.
- Search/filter/selection bars bên trong view giữ chức năng, compact và wrap khi viewport hẹp; titlebar/controlbar không co/không tràn tại min-width860.
- Giữ nguyên master_theme dark và engine/config/CLI cũ. Không publish trong lượt visual này.


## Đồng bộ Settings theo VXMedia — 2026-10-15

- Dialog672×560, tối đa viewport trừ32px; header/footer56px không co, sidebar192px có cuộn, nội dung padding24px có cuộn độc lập.
- System font12px, header16px/600, sidebar icon SVG16px/nhãn12px, item radius8px/active cyan, nhóm thông tin ngăn divider; Support tông amber.
- Form dùng tiêu đề nhóm cyan uppercase, divider và controls nền tối đồng nhất VXMedia. Giữ các tùy chọn Git/Skills riêng và cơ chế Lưu & Đóng hiện tại.
- Header dùng pywebview drag-region tương đương native startDragging; nút Close không nằm vùng kéo.
- About dùng card tên/version lấy từ config/tác giả/GitHub tác giả (chưa có repo riêng được xác nhận), mô tả ngắn và công nghệ. Updates chưa có backend thật nên hiển thị chưa khả dụng, không báo latest hard-code. Support giữ mã QR hiện có.
- QA: render6 tab bằng app.js với fixture config cô lập; JS syntax đạt; browser đo672×560/header56/sidebar192/footer56 và kiểm tra visual General. Chưa kiểm chứng lưu/đóng/drag native hoặc Windows.


## Hiệu chỉnh Settings theo mẫu thực tế VXMedia — 2026-10-17

- Bỏ nhãn nhóm sidebar thừa; giữ divider giữa tính năng và thông tin như VXMedia. General dùng theme radio cards hai cột, ngôn ngữ radio ngang và dropdown khởi động gọn; không thêm theme ngoài chức năng hiện có. Save đọc radio checked thay selector cũ.
- About gồm card nhận diện với SVG code cùng app, version từ config, tagline/tác giả/link GitHub; card mô tả hai câu và card công nghệ dạng danh sách. Giữ link tác giả do chưa xác lập URL repo riêng.
- Support dùng banner amber + icon Coffee SVG, card QR nền trắng208px theo VXMedia. Asset local `frontend/assets/support_qr.png` sao chép nguyên byte từ `vxmedia/src/assets/qr.png`; không còn URL sinh QR theo tài khoản/số tiền hard-code. Không cần Internet để tải QR.
- QA: render6 template với fixture config; JS syntax đạt; SHA256 asset trùng VXMedia; screenshot browser About/Support đã xem. Nội dung Support cuộn trong panel, footer cố định. Chưa native runtime/save backend/Windows hoặc kiểm thử chuyển tiền (không thuộc phạm vi UI).
