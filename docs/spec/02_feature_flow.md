# 02. Chi tiết Luồng Tính năng — VXDevSync
Version: 1.0.0 — Ngày cập nhật: 2026-10-15

Tài liệu này đặc tả chi tiết các luồng chức năng (Feature Flows), các trạng thái dữ liệu (State Transitions) và chuỗi gọi hàm (Sequence Interactions) cho toàn bộ các tính năng của **VXDevSync**.

---

## 1. Luồng Tính năng 1: Khởi động, Khôi phục Workspace & Tự động Quét

Mục tiêu: Đảm bảo tính tiện lợi ngang ngửa CLI (mở app lên là sẵn sàng làm việc ngay, không cần thao tác chọn lại thư mục làm việc).

### Sequence Diagram: Khởi động ứng dụng

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Nhà phát triển
    participant App as VXDevSync UI
    participant Bridge as pywebview Bridge
    participant CfgMgr as Config Manager
    participant GitEng as Git Sync Engine

    Dev->>App: Mở ứng dụng VXDevSync
    App->>Bridge: get_initial_state()
    Bridge->>CfgMgr: load_config()
    CfgMgr-->>Bridge: AppConfig (scan_path, agents, etc.)
    
    alt Chưa có config (Lần đầu mở)
        Bridge-->>App: { is_first_run: true }
        App->>Dev: Hiển thị Onboarding Wizard Modal
    else Đã có config
        Bridge-->>App: { is_first_run: false, config: AppConfig, active_tab: "git_sync" }
        App->>App: Hiển thị Tab Git Sync & Skeleton Loader
        App->>Bridge: trigger_scan(scan_path, max_depth)
        Bridge->>GitEng: scan_repositories(scan_path, max_depth, ignore_list)
        GitEng-->>Bridge: List[RepoStatus] (Projects, Branches, States, Offsets)
        Bridge-->>App: on_scan_completed(data)
        App->>Dev: Hiển thị Bảng Repository đã phân loại màu
    end
```

### Các trạng thái của Bảng Repository:
1. `IDLE`: Chưa quét hoặc đang chờ lệnh.
2. `SCANNING`: Hiển thị Skeleton loading + thanh thông báo *"Đang quét và kiểm tra nhánh remote..."*.
3. `READY`: Đã có dữ liệu, hiển thị danh sách kèm số lượng (ví dụ: *12 repositories tìm thấy*).
4. `ERROR`: Thư mục không tồn tại hoặc lỗi quyền đọc thư mục.

---

## 2. Luồng Tính năng 2: Chuyển đổi Workspace & Quản lý Recent Paths

Tuân thủ nghiêm ngặt mục "Mở file/thư mục và danh sách gần đây" trong [desktop_ui_standards.md](../../../_summary/standard_docs/desktop_ui_standards.md):
- Nút **Open Folder** đặt tại Titlebar bên cạnh tab navigation.
- Hover hoặc focus nút hiển thị dropdown tối đa **5 thư mục gần đây (Recent Workspaces)**, mới nhất đặt lên đầu.
- Click nút chính: Mở hộp thoại chọn thư mục gốc của hệ điều hành (Native Folder Picker).
- Click một mục trong dropdown: Chuyển ngay workspace hiện tại sang thư mục đó và kích hoạt quét lại.
- Chỉ lưu các lần mở thành công; không trùng lặp đường dẫn.

```mermaid
flowchart TD
    UserTrigger{"Hành động của người dùng:"} -->|Click nút Open Folder| NativeDialog["Mở Native Folder Picker của OS"]
    UserTrigger -->|Hover nút Open Folder| ShowDropdown["Hiển thị Dropdown Recent Workspaces (Tối đa 5 mục)"]
    
    NativeDialog --> UserSelectPath{"Người dùng chọn thư mục?"}
    UserSelectPath -->|Chọn thành công| ValidateDir["Kiểm tra thư mục hợp lệ"]
    UserSelectPath -->|Bấm Cancel| DoNothing["Không làm gì cả"]

    ShowDropdown --> ClickRecentItem["Click chọn 1 đường dẫn trong danh sách"]
    ClickRecentItem --> ValidateDir

    ValidateDir --> UpdateRecentList["Cập nhật mảng recent_paths trong config:
    - Đưa path mới lên đầu danh sách
    - Giữ tối đa 5 phần tử không trùng lặp
    - Gán scan_path = path mới"]
    UpdateRecentList --> SaveCfg["Lưu config.json"]
    SaveCfg --> TriggerNewScan["Kích hoạt quét Git cho Workspace mới"]
```

---

## 3. Luồng Tính năng 3: Quản lý Chọn Repo (Multi-selection) & Quick Exclude

Khắc phục hạn chế lớn nhất của CLI: Cho phép người dùng chủ động kiểm soát chính xác những repo nào sẽ được đồng bộ.

### A. Cơ chế Checkbox, Row-Click Selection & Header Controls
- **Click chọn cả dòng (Row-click Selection):** Người dùng có thể click vào bất kỳ vị trí nào trên hàng của repo để chọn hoặc bỏ chọn repo đó (không bắt buộc phải click chính xác vào ô checkbox nhỏ).
  - *Ngoại lệ an toàn:* Khi click trực tiếp vào các nút hành động (như icon `[️]` Exclude, `[⬇️]` Pull, `[⬆️]` Push) thì hệ thống chỉ thực thi hành động đó, không kích hoạt chọn/bỏ chọn dòng.
  - *Duyệt phím tắt:* Dùng phím mũi tên lên/xuống để di chuyển focus giữa các dòng, phím `Space` để toggle chọn/bỏ chọn dòng đang focus.
- **Header Checkbox:**
  - Trạng thái `Unchecked`: Không chọn repo nào.
  - Trạng thái `Indeterminate`: Đã chọn một số repo (nhưng chưa chọn tất cả).
  - Trạng thái `Checked`: Đã chọn toàn bộ repo hiển thị.
- **Nút "Chọn các repo có thay đổi" (Select Changed Only):** 1-click tự động tick chọn tất cả các repo có trạng thái `Behind` (cần pull) hoặc `Ahead` (cần push) hoặc `Dirty`, bỏ qua các repo đã `Clean` (Up-to-date).
- **Bộ lọc nhanh (Filter Tabs):** Tất cả (`All`), Cần Đồng bộ (`Needs Sync`), Đã Sạch (`Up-to-date`), Bị Lỗi/Lệch (`Conflicts`).

### B. Cơ chế Quick Exclude (Loại trừ Repo trên GUI)
Mỗi dòng trong bảng repository có nút biểu tượng **"Eye-Off / Exclude"** ở cột thao tác:
1. Khi click nút **Exclude**:
   - Hiển thị tooltip xác nhận: *"Bỏ qua repo `{repo_name}` khi quét?"*.
   - Nếu xác nhận: Thêm tên repo hoặc relative path vào `ignore_list` trong `config.json`.
   - Hàng tương ứng lập tức mờ đi hoặc biến mất khỏi danh sách hiển thị.
2. Để khôi phục: Người dùng mở Settings → tab Git Sync → Quản lý danh sách Ignore List → Bấm nút "Remove" bên cạnh tên repo đã loại trừ.

---

## 4. Luồng Tính năng 4: Thực thi Đồng bộ (Smart Sync / Push / Pull)

### Sequence Diagram: Đồng bộ các Repositories được chọn

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Nhà phát triển
    participant App as VXDevSync UI
    participant Bridge as pywebview Bridge
    participant GitEng as Git Sync Engine

    Dev->>App: Chọn 3 repos [repo_A, repo_B, repo_C]
    Dev->>App: Click "Smart Sync đã chọn"
    App->>App: Khóa thao tác giao diện (Busy Guard), hiển thị Thanh Tiến trình (Progress Bar)
    App->>Bridge: execute_sync(repos=["repo_A", "repo_B", "repo_C"], action="smart_sync")
    
    loop Từng Repo trong danh sách
        Bridge->>GitEng: sync_single_repo(repo_path, action)
        GitEng->>GitEng: Kiểm tra an toàn: Dirty? Diverged?
        alt Dirty và không được phép
            GitEng-->>Bridge: { repo: "repo_A", status: "SKIPPED_DIRTY", message: "Bỏ qua an toàn do có file sửa đổi" }
        else Hợp lệ
            GitEng->>GitEng: Thực thi git pull --rebase / git push origin branch
            GitEng-->>Bridge: { repo: "repo_B", status: "SUCCESS", message: "Đã pull 2 commits" }
        end
        Bridge-->>App: on_progress_update(current=1, total=3, detail=repo_result)
        App->>App: Cập nhật thanh tiến trình & Trạng thái icon dòng tương ứng
    end

    Bridge-->>App: on_sync_completed(summary)
    App->>Dev: Hiển thị Toast thông báo hoàn tất: "Đã đồng bộ 3/3 repos"
    App->>Bridge: trigger_scan() (Tự động quét lại để cập nhật bảng)
```

---

## 5. Luồng Tính năng 5: Quản lý Kỹ năng AI (Skills Inventory & Agent Toggling)

### A. Quản lý Bật/Tắt Agent trực tiếp
Trên giao diện tab **Skills Sync**, hiển thị 3 Thẻ Card tương ứng với 3 AI Agents:
1. **Antigravity Card:** Biểu tượng AGY, đường dẫn `~/.gemini/config`, số kỹ năng hiện diện, nút Switch Toggle.
2. **Codex Card:** Biểu tượng Codex, đường dẫn `~/.codex`, số kỹ năng hiện diện, nút Switch Toggle.
3. **Claude Code Card:** Biểu tượng Claude, đường dẫn `~/.claude`, số kỹ năng hiện diện, nút Switch Toggle.

Khi người dùng gạt toggle:
- UI cập nhật trạng thái On/Off ngay lập tức.
- Bridge gọi `update_agent_status(agent_name, is_active)`.
- Config lưu giá trị `1` hoặc `0` vào trường `agents`.
- Bảng Skills Inventory bên dưới tự động tô xám hoặc ẩn cột của Agent bị tắt.

### B. Bảng Ma trận Skills Inventory
Hiển thị danh sách toàn bộ các kỹ năng tìm thấy trên hệ sinh thái:
- Cột **Skill Name:** Tên thư mục kỹ năng (ví dụ: `_spec0_system`, `_uxui1_styling`).
- Cột **Central Library:** Check xanh (tồn tại) hoặc Dấu gạch xám (thiếu).
- Cột **Antigravity:** Check xanh (đồng bộ), Chấm vàng (lệch hash/phiên bản), Gạch xám (chưa có).
- Cột **Codex:** Trạng thái tương tự.
- Cột **Claude Code:** Trạng thái tương tự.
- Cột **Hành động (Action):** Nút **Xóa (Delete)** màu đỏ.

### C. Cơ chế Thay đổi Thư mục Central Skills Library (`skills_lib`)
Người dùng có thể linh hoạt thay đổi thư mục Central Skills Library theo 2 cách thuận tiện:
1. **Thay đổi nhanh ngay tại Dashboard:** Click nút `[Đổi Thư viện...]` trên card Central Library ở đầu màn hình Skills Sync.
2. **Thay đổi trong Settings Modal:** Vào Settings → tab **Skills Sync** → mục `Thư mục Central Skills Library (skills_lib)` → Click `[Duyệt...]`.

**Quy trình xác thực & Cập nhật khi đổi thư mục:**
- Hệ thống mở Native Folder Picker để người dùng chọn thư mục mới.
- Sau khi chọn, hệ thống chạy hàm kiểm tra hợp lệ:
  * Kiểm tra thư mục có tồn tại và đọc được không.
  * Tự động phát hiện xem thư mục đã khởi tạo Git repo chưa (kiểm tra `.git/`). Nếu có Git, tự động lấy branch hiện tại và remote URL để điền vào trường `git_repo`.
  * Kiểm tra xem thư mục có thư mục con `skills/` chưa. Nếu chưa có, hỏi người dùng có muốn tự động tạo không.
- Lưu đường dẫn mới vào trường `skills_sync.skills_lib` trong `config.json`.
- Kích hoạt quét lại toàn bộ hệ thống để làm mới bảng ma trận Skills Inventory ngay lập tức.

### D. Tiến trình Đồng bộ Hợp nhất (Unified Smart Sync)
Thay vì chia tách thành 2 nút riêng biệt gây thừa thao tác ("Đồng bộ Kỹ năng" và "Đồng bộ Rules"), hệ thống gộp thành **1 nút bấm duy nhất**: `[ Đồng bộ Tất cả (Kỹ năng & Rules AGENTS.md) ]`.
Khi click nút này, tiến trình đồng bộ diễn ra tuần tự khép kín:
1. **Upstream Phase:** Quét các thay đổi từ các Agent đang active copy về Central Library (kiểm tra Tombstones để loại trừ kỹ năng đã xóa).
2. **Downstream Phase:** Phân bổ đồng loạt toàn bộ kỹ năng chuẩn từ Central Library sang các Agent đang active.
3. **Rules Adapter Phase:** Tự động đồng bộ và chuyển đổi định dạng quy tắc giữa `AGENTS.md` (chuẩn chung cho Antigravity, Codex) và `CLAUDE.md` (chuẩn Claude Code kèm header tương ứng).
4. **Git Sync Phase (nếu có cấu hình Git repo):** Tự động tạo commit và push các thay đổi mới lên GitHub Remote.

---

## 6. Luồng Tính năng 6: Xóa Skill An toàn & Cơ chế Tombstone Manifest

### A. Thời điểm Thực thi Commit & Push (Timing of Git Operations)
* **Quy tắc Vàng:** Mọi thao tác `git commit` và `git push` đối với việc xóa skill được thực hiện **NGAY TẠI THỜI ĐIỂM NGƯỜI DÙNG XÁC NHẬN XÓA**, tuyệt đối **KHÔNG trì hoãn đến khi đóng app**.
* **Lý do thiết kế:**
  1. *Tránh giật lag khi thoát:* Dev đóng app cần phản hồi tức thì (dưới 100ms), không thể để app bị đơ 2-5 giây chờ kết nối mạng `git push`.
  2. *Bảo vệ dữ liệu trước Force-Quit/Tắt máy:* Nếu OS tắt đột ngột, lệnh push bị ngắt giữa chừng sẽ làm hỏng Git index hoặc kẹt lock file.
  3. *Tính nhất quán tức thời:* Giúp các máy tính khác (Machine B) có thể pull được trạng thái xóa ngay mà không phụ thuộc vào việc Machine A có đóng app hay chưa.

### B. Sequence Diagram: Luồng Xóa Skill Tức Thì (Instant Delete on Machine A)

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Nhà phát triển
    participant App as VXDevSync UI
    participant Bridge as pywebview Bridge
    participant SkillsEng as Skills Engine
    participant GitEng as Git Engine
    participant GitHub as Remote GitHub Repo

    Dev->>App: Chọn 1 hoặc nhiều skills, bấm "Xóa Skill"
    App->>Dev: Hiển thị Modal Cảnh báo Nguy hiểm
    Dev->>App: Bấm "Xác nhận Xóa Triệt Để"
    
    App->>App: Khóa thao tác dòng tương ứng (Deleting spinner)
    App->>Bridge: delete_skills_cascade(skill_names=["_mkt9_obsolete"])
    
    Bridge->>SkillsEng: 1. Xóa vật lý tại Central Library & các Active Agents
    SkillsEng->>SkillsEng: Dọn dẹp thư mục skills/_mkt9_obsolete
    
    Bridge->>GitEng: 2. Cập nhật Git Local (Mất ~0.1s)
    GitEng->>GitEng: git rm -r skills/_mkt9_obsolete
    GitEng->>GitEng: Ghi vào .vxdevsync/tombstones.json
    GitEng->>GitEng: git commit -m "chore(skills): delete skill '_mkt9_obsolete'"
    
    Bridge->>GitEng: 3. Đẩy lên GitHub Remote
    alt Có mạng (Online)
        GitEng->>GitHub: git push origin <branch>
        GitHub-->>GitEng: Push thành công (200 OK)
        GitEng-->>Bridge: { success: true, pushed: true }
        Bridge-->>App: on_delete_completed(status="PUSHED")
        App->>Dev: Toast: "Đã xóa skill và đồng bộ lên GitHub thành công"
    else Mất mạng (Offline)
        GitEng-->>Bridge: { success: true, pushed: false, pending_commits: 1 }
        Bridge-->>App: on_delete_completed(status="PENDING_PUSH")
        App->>Dev: Toast: "Đã xóa local. Đã lưu commit, sẽ tự push khi có mạng"
        App->>App: Hiển thị badge "⬆️ 1 commit chưa push"
    end
```

### C. Sequence Diagram: Luồng Đón Nhận & Dọn Dẹp trên Máy Tính Thứ Hai (Machine B)

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Người dùng trên Máy B
    participant AppB as VXDevSync (Máy B)
    participant GitB as Git Engine (Máy B)
    participant GitHub as Remote GitHub Repo
    participant AgentsB as Local Agents (Máy B)

    Dev->>AppB: Bấm nút "Bắt đầu Đồng bộ Kỹ năng" (Sync Now)
    AppB->>GitB: 1. Kiểm tra & Kéo commit mới từ GitHub
    GitB->>GitHub: git pull --rebase origin <branch>
    GitHub-->>GitB: Tải về commit xóa & file .vxdevsync/tombstones.json mới
    GitB-->>AppB: Pull hoàn tất: Central Library trên Máy B đã sạch skill bị xóa

    AppB->>AppB: 2. Đọc danh sách khai tử trong .vxdevsync/tombstones.json
    AppB->>AgentsB: 3. Kiểm tra các thư mục Agent cục bộ (~/.gemini, ~/.codex, ~/.claude)
    Note over AppB,AgentsB: Phát hiện các Agent trên Máy B vẫn còn giữ bản copy cũ của skill đã xóa
    AppB->>AgentsB: 4. Tự động XÓA SẠCH thư mục skill cũ trên tất cả các Agent
    
    AppB->>AppB: 5. Kích hoạt Upstream Scanner (Lúc này các Agent đã sạch, không bị sync ngược)
    AppB->>AppB: 6. Kích hoạt Downstream Deploy & Rules Adapter
    AppB->>Dev: Toast: "Đồng bộ thành công: Đã dọn dẹp các kỹ năng bị xóa từ GitHub"
```

### D. Xử lý Chi tiết các Trường hợp Biên (Edge Cases):
1. **Xóa hàng loạt (Bulk Delete):**
   - Khi dev tick chọn nhiều skills (ví dụ 3 skills) rồi bấm Xóa: Hệ thống thực hiện dọn dẹp đồng loạt và gom toàn bộ thay đổi vào **đúng 1 commit duy nhất** `chore(skills): delete 3 skills` và chỉ `git push` 1 lần duy nhất, tránh làm rác lịch sử commit.
2. **Khôi phục lại kỹ năng (Restore / Undo):**
   - Trong màn hình Settings → tab Skills Sync → mục **"Quản lý Tombstones"**: Hiển thị danh sách các skills đang bị khai tử.
   - Người dùng bấm nút "Khôi phục" (Restore). Hệ thống xóa tên khỏi `tombstones.json`, dùng `git checkout` lấy lại code từ commit cũ, tạo commit `chore(skills): restore skill` và push lên GitHub, sau đó phân bổ lại cho các Agent.
3. **File đang bị khóa bởi tiến trình OS / AI Agent:**
   - Nếu OS chặn không cho xóa thư mục skill (do Agent đang đọc file), hệ thống thông báo lỗi chi tiết, ghi nhận trạng thái xóa dở dang và thử lại khi đóng ứng dụng.

