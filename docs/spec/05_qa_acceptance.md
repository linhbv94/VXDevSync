# 05. Tiêu chuẩn Nghiệm thu & QA — VXDevSync
Version: 1.1.0 — Ngày cập nhật: 2026-10-26

Tài liệu này định nghĩa bộ tiêu chuẩn nghiệm thu chất lượng (Quality Assurance Acceptance Criteria) dưới dạng kịch bản Gherkin chuẩn hóa và danh mục kiểm tra (Checklist) cho **VXDevSync**.

---

## 1. Test Suite 1: Luồng Khởi tạo Lần đầu (Onboarding Wizard)

### Kịch bản 1.1: Khởi động lần đầu chưa có cấu hình
```gherkin
Given Ứng dụng VXDevSync được mở lần đầu tiên trên máy tính
And File cấu hình config.json chưa tồn tại trong thư mục Application Support / AppData
When Cửa sổ ứng dụng hiển thị hoàn tất
Then Ứng dụng phải tự động mở Onboarding Modal (Welcome Wizard)
And Tự động gợi ý đường dẫn Workspace Root phù hợp (dựa trên thư mục người dùng hoặc cwd)
And Tự động phát hiện các Agent cục bộ đã cài đặt (Antigravity tại ~/.gemini/config, Codex tại ~/.codex)
And Cho phép người dùng bấm "Bắt đầu làm việc" để lưu cấu hình
And Sau khi lưu, ứng dụng phải chuyển ngay vào tab Git Multi-Sync và tự động kích hoạt quét
```

---

## 2. Test Suite 2: Quét Git, Lưu nhớ Workspace & Dropdown Recent

### Kịch bản 2.1: Tự động nạp lại Workspace đã lưu từ phiên trước
```gherkin
Given Người dùng đã cấu hình scan_path là "/Users/vic/_Work" trong phiên làm việc trước
When Người dùng khởi động lại ứng dụng VXDevSync
Then Ứng dụng phải tự động hiển thị tab Git Multi-Sync làm mặc định
And Thanh tiêu đề phải hiển thị đường dẫn hiện tại là "/Users/vic/_Work"
And Tiến trình quét Git phải tự động kích hoạt mà không cần bấm thêm nút nào
And Toàn bộ danh sách repositories tìm thấy phải được hiển thị kèm trạng thái màu chuẩn xác
```

### Kịch bản 2.2: Chuyển đổi Workspace qua Dropdown Recent
```gherkin
Given Người dùng đang ở Workspace "/Users/vic/_Work"
When Người dùng hover chuột vào nút Open Folder trên Titlebar
Then Một dropdown phải hiển thị tối đa 5 thư mục mở gần nhất, xếp theo thứ tự mới nhất ở trên
When Người dùng click vào một thư mục trong danh sách gần đây (ví dụ: "/Users/vic/_Work/zTools")
Then Đường dẫn scan_path trong cấu hình phải được cập nhật thành thư mục mới
And Ứng dụng phải kích hoạt ngay lượt quét mới cho thư mục vừa chọn
And Thư mục vừa chọn phải được đưa lên vị trí số 1 trong danh sách recent_paths
```

---

## 3. Test Suite 3: Checkbox Đa chọn, 1-Click Sync & Floating Action Bar

### Kịch bản 3.1: Chọn nhanh các repo có thay đổi (Select Changed Only)
```gherkin
Given Bảng Git Sync hiển thị 10 repositories, trong đó có 2 repo Behind, 1 repo Ahead và 7 repo Up-to-date
When Người dùng click vào nút "Chỉ chọn repo có thay đổi"
Then Đúng 3 repo (2 Behind, 1 Ahead) được tick chọn checkbox
And 7 repo Up-to-date giữ nguyên trạng thái bỏ chọn (Unchecked)
And Thanh tác vụ nổi (Action Bar) hiển thị: "3 đã chọn"
And Các nút icon action trên thanh nổi chuyển sang trạng thái sẵn sàng
```

### Kịch bản 3.2: Đồng bộ chỉ các repo được chọn qua Floating Action Bar (Icon-Only)
```gherkin
Given Người dùng đã tick chọn 2 repos: "vxmedia" (Behind) và "vxphotos" (Ahead)
When Thanh tác vụ nổi (Floating Action Bar dạng Icon-Only) hiển thị ở đáy màn hình
Then Nút [] hiển thị ActionTooltip: "Smart Sync đã chọn (Pull & Push)" khi hover
And Nút [↓] hiển thị ActionTooltip: "Pull đã chọn (Remote → Local)" khi hover
And Nút [↑] hiển thị ActionTooltip: "Push đã chọn (Local → Remote)" khi hover
And Nút [X] hiển thị ActionTooltip: "Bỏ chọn tất cả (Esc)" khi hover
When Người dùng click nút [] (Smart Sync đã chọn)
Then Giao diện bị khóa tạm thời (Busy Guard) và hiển thị thanh tiến trình đồng bộ
And Hệ thống thực hiện git pull cho "vxmedia" và git push cho "vxphotos"
And Các repo khác không được chọn (dù có thay đổi) tuyệt đối không bị tác động
And Sau khi hoàn tất, hiển thị Toast thông báo thành công
And Bảng Git Sync tự động quét lại để cập nhật trạng thái mới nhất
```

### Kịch bản 3.3: Tiện lợi 1-Click "Smart Sync thay đổi" trên Selection Bar
```gherkin
Given Người dùng không cần tick chọn từng checkbox thủ công
When Người dùng click trực tiếp vào nút "Smart Sync thay đổi (N)" trên thanh Selection Bar
Then Hệ thống tự động lọc toàn bộ các repo hợp lệ có thay đổi (Behind / Ahead / Dirty)
And Thực hiện tự động Pull cho các repo Behind và Push cho các repo Ahead
And Giữ nguyên hành vi Safe-Skip cho các repo Dirty và Manual Merge cho các repo Diverged
And Nếu không có repo nào cần thay đổi (N = 0), hiển thị Toast: "Tất cả repository đã đồng bộ!"
```

### Kịch bản 3.4: Click chọn cả dòng (Row-click Selection) & Phím Esc
```gherkin
Given Repository "vxmedia" đang hiển thị trên bảng Git Sync và chưa được chọn
When Người dùng click vào bất kỳ vùng trống hoặc chữ trên dòng của "vxmedia" (ngoại trừ các nút hành động)
Then Checkbox của dòng "vxmedia" tự động chuyển sang trạng thái đã chọn (Checked)
When Người dùng click lại một lần nữa vào dòng "vxmedia"
Then Checkbox của dòng "vxmedia" tự động chuyển sang trạng thái bỏ chọn (Unchecked)
When Người dùng click trực tiếp vào icon vector [↓] (Pull) trên dòng "vxmedia"
Then Hệ thống chỉ kích hoạt lệnh Pull riêng cho "vxmedia" mà không làm thay đổi trạng thái checkbox của dòng
When Có một hoặc nhiều repo đang được chọn và người dùng bấm phím `Escape`
Then Toàn bộ các repo được bỏ chọn và thanh tác vụ nổi tự động ẩn đi
```

---

## 4. Test Suite 4: Loại trừ Repo trực tiếp trên GUI (Git Exclude)

### Kịch bản 4.1: Bỏ qua repo ngay trên bảng (Đẩy xuống cuối, mờ 45%, hỗ trợ khôi phục)
```gherkin
Given Repository "legacy_test_repo" đang hiển thị bình thường trên bảng Git Sync
When Người dùng click vào icon con mắt gạch chéo [EyeOff] trên dòng của repo đó
Then Repo "legacy_test_repo" không biến mất mà tự động bị đẩy xuống cuối bảng danh sách
And Dòng repo hiển thị mờ (opacity: 0.45, filter: grayscale(0.5))
And Checkbox của dòng bị vô hiệu hóa (disabled)
And Nút hành động con mắt chuyển sang biểu tượng [Eye] (mở mắt)
And Tên "legacy_test_repo" được ghi thêm vào mảng `ignore_list` trong file `config.json`
And Danh sách loại trừ trong Modal Cài đặt (Settings) được cập nhật đồng bộ ngay lập tức
When Người dùng click lại vào icon [Eye] trên dòng bị loại trừ
Then Repo "legacy_test_repo" lập tức được khôi phục về trạng thái bình thường (Unignored)
```

---

## 5. Test Suite 5: Quản lý Agent, Đổi Thư viện & Đồng bộ Hợp nhất

### Kịch bản 5.1: Bật/Tắt Agent trên Skills Sync Dashboard
```gherkin
Given Thẻ card của "Claude Code" đang ở trạng thái Tắt (OFF)
When Người dùng click vào nút Switch trên thẻ "Claude Code"
Then Thẻ chuyển sang trạng thái Bật (ON) với đèn báo màu xanh lá
And Cấu hình `agents.claude` trong `config.json` lập tức được cập nhật thành `1`
And Cột Claude Code trong bảng Skills Inventory lập tức chuyển từ trạng thái ẩn/xám sang hiển thị trạng thái thực tế
```

### Kịch bản 5.2: Đồng bộ Hợp nhất Kỹ năng & Rules trong 1 nút bấm (Unified Smart Sync)
```gherkin
Given Người dùng đang ở màn hình Skills Sync Dashboard
When Người dùng click vào nút "Đồng bộ Tất cả (Kỹ năng & Rules AGENTS.md)"
Then Ứng dụng thực thi tuần tự: Upstream skills -> Downstream skills -> Rules Adapter (AGENTS.md ↔ CLAUDE.md)
And Tự động commit và push lên GitHub Remote nếu có liên kết repo
And Hiển thị Toast thông báo: "Đã đồng bộ thành công Kỹ năng và Rules"
And Bảng ma trận Skills Inventory tự động làm mới với các tick xanh đồng bộ
```

### Kịch bản 5.3: Thay đổi Central Skills Library (Đổi đường dẫn skills_lib)
```gherkin
Given Người dùng muốn chuyển sang dùng Thư viện Kỹ năng khác tại "/Users/vic/another_skills_lib"
When Người dùng click nút "[Đổi Thư viện...]" trên Dashboard (hoặc nút [Duyệt...] trong Settings)
And Chọn thư mục mới qua hộp thoại Folder Picker của hệ điều hành
Then Đường dẫn `skills_lib` trong file `config.json` được cập nhật thành thư mục mới
And Thẻ thông tin Central Library trên UI cập nhật đường dẫn, trạng thái Git và số lượng skills tương ứng
And Bảng Skills Inventory được quét lại và hiển thị chính xác danh mục skills của thư viện mới
```

---

## 6. Test Suite 6: Xóa Kỹ năng Triệt để & Chống Hồi sinh (Tombstone)

### Kịch bản 6.1: Xóa một kỹ năng qua Cascade Delete
```gherkin
Given Kỹ năng "_test_temp_skill" đang tồn tại ở cả Central Library, Antigravity và Codex
When Người dùng click nút vector [Trash] bên cạnh dòng "_test_temp_skill"
Then Hộp thoại xác nhận nguy hiểm hiển thị, liệt kê rõ các đường dẫn sẽ bị xóa
When Người dùng bấm "Xác nhận Xóa Triệt Để"
Then Thư mục "_test_temp_skill" bị xóa vĩnh viễn khỏi Central Library
And Thư mục "_test_temp_skill" bị xóa vĩnh viễn khỏi ~/.gemini/config/skills/
And Thư mục "_test_temp_skill" bị xóa vĩnh viễn khỏi ~/.codex/skills/
And Tên "_test_temp_skill" được ghi nhận vào mảng `deleted_skills` trong file `config.json`
And Dòng kỹ năng đó biến mất khỏi bảng Skills Inventory
```

### Kịch bản 6.2: Chặn hồi sinh khi một Agent offline bật lại (Anti-Resurrection)
```gherkin
Given Kỹ năng "_test_temp_skill" đã bị xóa và nằm trong `deleted_skills`
And Một thư mục Agent (ví dụ Claude Code) vừa được bật lại và vẫn còn chứa bản copy cũ của "_test_temp_skill"
When Người dùng bấm nút "Bắt đầu Đồng bộ Kỹ năng" (Sync Now)
Then Pha Upstream Scanner phát hiện "_test_temp_skill" nằm trong danh sách Tombstone
And Hệ thống tự động xóa bỏ thư mục rác này khỏi Claude Code
And Tuyệt đối KHÔNG copy ngược "_test_temp_skill" trở lại Central Library
And Không phân bổ "_test_temp_skill" sang các Agent khác
```

### Kịch bản 6.3: Đồng bộ Xóa Kỹ năng Đa Thiết bị qua GitHub
```gherkin
Given Người dùng đã xóa kỹ năng "_test_temp_skill" trên Máy A
And Máy A đã commit và push commit xóa kèm file .vxdevsync/tombstones.json lên GitHub
And Người dùng chuyển sang Máy B (nơi các Agent trên Máy B vẫn còn thư mục "_test_temp_skill")
When Người dùng bấm nút "Bắt đầu Đồng bộ" trên Máy B
Then Máy B thực hiện git pull từ GitHub về Central Library thành công
And Máy B đọc file .vxdevsync/tombstones.json vừa kéo về
And Tự động xóa sạch thư mục "_test_temp_skill" tại tất cả các Agent trên Máy B
And Bảng Skills Inventory trên Máy B cập nhật trạng thái đã xóa, không xảy ra hiện tượng sync ngược lại GitHub
```

---

## 7. Checklist Tuân thủ Chuẩn zTools Desktop UI

- [ ] **Thanh tiêu đề (Titlebar):** Chiều cao đúng 32px, phông system 12px weight 600, icon 16px gap 6px.
- [ ] **Nút Traffic Lights (macOS):** Đúng đường kính hiển thị 12pt (chuẩn AppKit SDK 15.5 compatibility), khoảng cách tâm 20pt native, căn giữa toolbar 15.5pt, ổn định qua focus/resize.
- [ ] **Titlebar Windows:** Bỏ hoàn toàn native chrome (`decorations: false`), không bị double bar.
- [ ] **Dropdown Recent Workspaces:** Hiển thị tối đa 5 thư mục, nhớ qua restart, không trùng lặp path.
- [ ] **Settings Modal chuẩn 2 nhóm:**
  - Nhóm 1 (Tính năng): General, Git Sync, Skills Sync.
  - Nhóm 2 (Thông tin & Hỗ trợ): Updates (card check GitHub Releases), About (Bùi Việt Linh), Support Author (mã QR VietQR căn giữa nền trắng).
- [ ] **Bảng màu:** Chuẩn Master Theme Dark `#0f1117`, Amber/Cyan accent `#f59e0b` / `#06b6d4`.
- [ ] **Biểu tượng Vector:** 100% sử dụng Lucide vector SVG, không sử dụng emoji hệ thống.
- [ ] **Định dạng văn bản:** Tuyệt đối không chứa công thức LaTeX; dùng Unicode `→`, `←`, `≥`, `≤`, `×`.
