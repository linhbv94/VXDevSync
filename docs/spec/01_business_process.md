# 01. Quy trình Nghiệp vụ — VXDevSync
Version: 1.0.0 — Ngày cập nhật: 2026-10-15

Tài liệu này đặc tả các quy trình nghiệp vụ cốt lõi (Business Processes) của ứng dụng **VXDevSync**, bao gồm luồng chào đón & khởi tạo lần đầu (Onboarding), luồng đồng bộ Git đa dự án (Git Multi-Sync), luồng đồng bộ Kỹ năng AI (Skills Auto-Sync) và cơ chế xóa kỹ năng triệt để chống hồi sinh (Cascade Delete & Tombstone).

---

## 1. Quy trình Nghiệp vụ 1: Khởi tạo Lần đầu (Onboarding Wizard)

Quy trình kích hoạt khi ứng dụng phát hiện chưa có file cấu hình hệ thống `config.json` tại `Application Support/VXDevSync` (macOS) hoặc `%APPDATA%\VXDevSync` (Windows).

```mermaid
flowchart TD
    Start(["Mở VXDevSync lần đầu"]) --> CheckConfig{"Đã có config.json?"}
    CheckConfig -- "Có" --> LoadApp["Nạp config → Vào thẳng Tab Git Sync"]
    CheckConfig -- "Chưa có" --> ShowWizard["Mở Onboarding Modal (2 bước)"]
    
    subgraph Step1 ["Bước 1: Thiết lập Git Sync (Bắt buộc)"]
        ShowWizard --> DetectHome["Gợi ý thư mục làm việc (~/Work hoặc cwd cũ)"]
        DetectHome --> UserPickRoot["Người dùng chọn Workspace Root"]
        UserPickRoot --> SetMaxDepth["Thiết lập Độ sâu quét (Mặc định: 3)"]
    end

    subgraph Step2 ["Bước 2: Thiết lập Skills Sync (Tùy chọn)"]
        SetMaxDepth --> DetectAgents["Tự động quét đường dẫn Agents cục bộ"]
        DetectAgents --> ShowAgentToggles["Hiển thị checkbox các Agent tìm thấy (Anti, Codex, Claude)"]
        ShowAgentToggles --> PickSkillsLib["Chọn Central Skills Library (Local Directory)"]
        PickSkillsLib --> InputGitRepo["Nhập Git Remote URL của Skills Lib tổng (hỗ trợ tự nhận diện)"]
    end

    InputGitRepo --> SaveConfig["Tạo config.json hợp nhất chuẩn hệ thống"]
    SaveConfig --> AutoScanGit["Chuyển vào Dashboard Git Sync & Quét tự động"]
    AutoScanGit --> Done(["Sẵn sàng làm việc"])
```

### Tiêu chuẩn Nghiệp vụ Bước Onboarding:
1. **Không làm gián đoạn người dùng:** Cung cấp nút "Sử dụng mặc định & Tiếp tục" (1-click) để dev có thể vào làm việc ngay trong 5 giây nếu không muốn tùy chỉnh sâu.
2. **Tự động dò tìm (Auto-detection):**
   - Tự động kiểm tra xem `~/.gemini/config` (Antigravity), `~/.codex` (Codex), `~/.claude` (Claude Code) có tồn tại trên máy hay không; nếu tồn tại thì tự động gạt bật toggle tương ứng.
3. **Mặc định đích đến:** Sau khi kết thúc Onboarding, ứng dụng luôn điều hướng người dùng vào tab **Git Sync** — đây là chế độ chính thường xuyên sử dụng nhất trong ngày.

---

## 2. Quy trình Nghiệp vụ 2: Quét & Đồng bộ Git Đa Dự án (Git Multi-Sync)

Quy trình giải quyết nghiệp vụ kiểm tra trạng thái nhiều kho mã nguồn (repositories) trong một Workspace và thực hiện các hành động đồng bộ hóa linh hoạt.

```mermaid
flowchart TD
    OpenTab["Vào Tab Git Sync"] --> ReadScanPath["Đọc scan_path từ config.json"]
    ReadScanPath --> TriggerScan["Kích hoạt quét đồng thời (Async Pool, timeout=10s)"]
    
    subgraph ScanPhase ["Pha Quét & Phân loại"]
        TriggerScan --> ReadGitStatus["git status --porcelain, git rev-parse, git fetch"]
        ReadGitStatus --> Classify["Phân loại trạng thái từng repo:
        - Clean (Đã đồng bộ)
        - Dirty (Có file sửa chưa commit)
        - Behind (Chậm hơn remote)
        - Ahead (Có commit chưa push)
        - Diverged (Lệch nhánh cần merge)"]
        Classify --> FilterIgnored["Lọc bỏ các repo nằm trong ignore_list"]
    end

    FilterIgnored --> RenderTable["Hiển thị Bảng trạng thái kèm Checkbox từng dòng"]
    
    subgraph SelectionPhase ["Pha Lựa chọn (GUI Interaction)"]
        RenderTable --> UserAction{"Người dùng tương tác:"}
        UserAction -- "Tick/Untick checkbox" --> UpdateSelected["Cập nhật danh sách repo được chọn"]
        UserAction -- "Chọn Filter/Quick Select" --> SelectChanged["Chọn tất cả repo có thay đổi (Behind/Ahead)"]
        UserAction -- "Bấm Quick Exclude" --> AddToIgnore["Thêm repo vào danh sách loại trừ"]
        UserAction -- "Đổi Workspace Root" --> SwitchPath["Chọn path mới qua Open Folder / Recent Dropdown"]
        SwitchPath --> SaveRecent["Lưu vào recent_paths (tối đa 5)"] --> TriggerScan
    end

    subgraph SyncExecution ["Pha Thực thi Đồng bộ"]
        UpdateSelected --> ClickAction{"Chọn hành động:"}
        ClickAction -- "Smart Sync đã chọn" --> ExecSmartSync["Thực hiện Auto Pull (Behind) & Auto Push (Ahead)"]
        ClickAction -- "⬇️ Pull đã chọn" --> ExecPull["Chỉ kéo mã nguồn mới cho các repo được chọn"]
        ClickAction -- "⬆️ Push đã chọn" --> ExecPush["Chỉ đẩy commit cục bộ cho các repo được chọn"]
        ClickAction -- "Smart Sync TẤT CẢ" --> ExecAll["Chạy Smart Sync toàn bộ (giữ nguyên flow CLI cũ)"]
    end

    ExecSmartSync --> Refresh["Tự động quét lại & Làm mới giao diện"]
    ExecPull --> Refresh
    ExecPush --> Refresh
    ExecAll --> Refresh
```

### Nguyên tắc An toàn trong Git Sync:
- **Nguyên tắc "Safe-Skip" với Dirty Repo:** Tuyệt đối không tự động pull hoặc push đè lên các repo đang có file sửa đổi dở dang (Dirty), trừ khi người dùng chủ động commit hoặc stash thủ công.
- **Bảo vệ nhánh Diverged:** Khi repo bị lệch cả 2 chiều (vừa có commit mới ở local, vừa có commit mới ở remote), hệ thống hiển thị cảnh báo màu đỏ và yêu cầu người dùng merge thủ công, không tự động force push làm mất code.

---

## 3. Quy trình Nghiệp vụ 3: Đồng bộ Kỹ năng AI Chéo (Skills Auto-Sync)

Quy trình đồng bộ các bộ quy tắc (`AGENTS.md`) và thư viện kỹ năng (`skills/`) giữa các Agent cục bộ và Central Skills Library.

```mermaid
flowchart TD
    OpenSkills["Vào Tab Skills Sync"] --> LoadConfig["Đọc cấu hình agents active & skills_lib"]
    LoadConfig --> ScanInventory["Quét toàn bộ skills hiện hữu ở Thư viện & các Agent"]
    ScanInventory --> ShowInventory["Hiển thị Bảng Skills Inventory & Trạng thái Agents"]

    subgraph AgentToggle ["Tương tác Bật/Tắt Agent & Thay đổi Central Library"]
        ShowInventory --> ClickToggle["Gạt bật/tắt toggle Agent (Anti, Codex, Claude)"]
        ClickToggle --> SaveAgentConfig["Lưu trạng thái vào config.json realtime"]
        SaveAgentConfig --> ScanInventory
        ShowInventory --> ChangeLib["Click [Đổi Thư viện...] hoặc đổi trong Settings"]
        ChangeLib --> ValidateAndSaveLib["Xác thực Git/Folder và lưu skills_lib vào config.json"]
        ValidateAndSaveLib --> ScanInventory
    end

    subgraph SyncWorkflow ["Luồng Đồng bộ Hợp nhất (Unified Smart Sync)"]
        ShowInventory --> ClickSync["Bấm 'Đồng bộ Tất cả (Kỹ năng & Rules AGENTS.md)'"]
        
        ClickSync --> UpstreamPhase["1. Pha Upstream: Quét các Agent đang Active"]
        UpstreamPhase --> CheckTombstone{"File có nằm trong deleted_skills?"}
        CheckTombstone -- "Có (Đã bị xóa trước đó)" --> PruneFromAgent["Xóa file rác khỏi Agent để dọn dẹp"]
        CheckTombstone -- "Không" --> CompareHash{"Hash hoặc mtime mới hơn Library?"}
        CompareHash -- "Có" --> CopyToLibrary["Copy skill vào Central Library"]
        CompareHash -- "Không" --> SkipUpstream["Bỏ qua"]

        CopyToLibrary --> DownstreamPhase["2. Pha Downstream: Phân bổ từ Library sang các Agent"]
        PruneFromAgent --> DownstreamPhase
        SkipUpstream --> DownstreamPhase
        DownstreamPhase --> DeployActive["Copy toàn bộ skills chuẩn từ Library sang các Agent đang active"]
        DeployActive --> RulesAdapter["3. Chuyển đổi Quy tắc: AGENTS.md ↔ CLAUDE.md"]
    end

    RulesAdapter --> GitSyncLib{"Có cấu hình git_repo cho Library?"}
    GitSyncLib -- "Có" --> GitCommitLib["Tự động Git Commit & Push cho Central Library"]
    GitSyncLib -- "Không / Chế độ Offline" --> FinishSync["Hoàn tất đồng bộ"]
    GitCommitLib --> FinishSync
    FinishSync --> ShowSuccess["Hiển thị Toast: 'Đã đồng bộ thành công Kỹ năng và Rules'"]
```

---

## 4. Quy trình Nghiệp vụ 4: Xóa Kỹ năng Triệt để & Chống Hồi sinh (Cascade Delete & Tombstone)

Đây là quy trình nghiệp vụ quan trọng nhằm giải quyết dứt điểm **Bad Case của bản CLI** (khi xóa một skill ở 1 nơi thì khi sync lại bị các nơi khác copy ngược lại).

### A. Phân tích Bản chất Lỗi (Root Cause)
1. Trong mô hình Sync 2 chiều không có lịch sử trạng thái (state-less), một file không tồn tại ở thư mục A nhưng tồn tại ở thư mục B sẽ được hiểu là: *"Thư mục B vừa tạo ra một file mới cần được backup về A"*.
2. Do đó, việc xóa file thủ công ở một Agent hoặc ngay cả ở Central Library sẽ bị coi là *"nơi này chưa có file, cần được bù đắp từ các nguồn còn lại"*. Kỹ năng đã xóa lập tức được hồi sinh trên toàn bộ hệ thống!

### B. Giải pháp Quy trình: Cascade Delete + Tombstone Manifest

```mermaid
flowchart TD
    UserSelectSkill["Người dùng chọn 1 skill trên Skills Inventory"] --> ClickDelete["Bấm nút Xóa (Delete)"]
    ClickDelete --> ConfirmModal["Hiển thị Hộp thoại Xác nhận Nguy hiểm:
    'Xóa vĩnh viễn skill [Tên Skill] khỏi Thư viện và TẤT CẢ Agents?'"]
    
    ConfirmModal -- "Hủy" --> CancelAction["Đóng hộp thoại, không thay đổi gì"]
    ConfirmModal -- "Xác nhận Xóa" --> Step1_PhysicalDelete["1. Xóa vật lý đồng loạt (Cascade Delete)"]
    
    subgraph CascadeExecution ["Thực thi Xóa Đồng loạt"]
        Step1_PhysicalDelete --> DelLib["Xóa tại Central Library: {skills_lib}/skills/{name}"]
        DelLib --> DelAnti["Xóa tại Antigravity: ~/.gemini/config/skills/{name}"]
        DelAnti --> DelCodex["Xóa tại Codex: ~/.codex/skills/{name}"]
        DelCodex --> DelClaude["Xóa tại Claude Code: ~/.claude/skills/{name}"]
    end

    CascadeExecution --> Step2_Tombstone["2. Ghi nhận Tombstone Manifest"]
    Step2_Tombstone --> AppendTombstone["Thêm tên skill vào mảng deleted_skills trong config.json:
    { 'name': skill_name, 'deleted_at': timestamp }"]
    
    AppendTombstone --> Step3_GitSync["3. Đồng bộ hóa Central Git Repo lên GitHub"]
    
    subgraph GitSyncRemote ["Đồng bộ Git Repo & GitHub Remote"]
        Step3_GitSync --> GitRm["git rm -r skills/{name}"]
        GitRm --> UpdateRepoTombstone["Ghi vào .vxdevsync/tombstones.json trong repo"]
        UpdateRepoTombstone --> GitCommit["git commit -m 'chore(skills): delete skill <name>'"]
        GitCommit --> CheckOnline{"Có kết nối mạng?"}
        CheckOnline -- "Online" --> GitPush["git push origin <branch> lên GitHub"]
        CheckOnline -- "Offline" --> PendingPush["Lưu commit local, đánh dấu ⬆️ 1 commit chưa push"]
    end
    
    GitPush --> Step4_UIUpdate["4. Làm mới giao diện Skills Inventory"]
    PendingPush --> Step4_UIUpdate
    Step4_UIUpdate --> EndDelete(["Skill đã bị xóa triệt để, không thể hồi sinh"])
```

---

## 5. Cơ chế Đồng bộ Xóa Kỹ năng trên GitHub & Đa Thiết bị (Multi-Device Git Sync)

Đây là mắt xích cốt lõi bảo đảm khi người dùng sử dụng nhiều máy tính (ví dụ: PC tại văn phòng và Laptop cá nhân) cùng liên kết với một Central Skills Library trên GitHub:

### A. Tại máy thực hiện lệnh Xóa (Máy A)
1. **Xóa có kiểm soát qua Git (Tracked Deletion):**
   - Không chỉ xóa thư mục vật lý, engine chạy `git rm -r skills/<skill_name>`.
   - Cập nhật file `.vxdevsync/tombstones.json` nằm ngay trong thư mục gốc của Central Library repo. File này đóng vai trò là "Sổ đăng ký khai tử" dùng chung trên Git.
2. **Tạo Git Commit tường minh:**
   - Tạo commit với thông điệp: `chore(skills): delete skill '<skill_name>'`.
   - Lợi ích: Lịch sử Git rõ ràng, có thể tra cứu hoặc khôi phục lại kỹ năng qua `git revert` nếu người dùng lỡ xóa nhầm.
3. **Đẩy lên GitHub Remote (Push to GitHub):**
   - **Trường hợp Online:** Hệ thống tự động `git push origin <branch>` lên GitHub ngay lập tức. Trên GitHub, thư mục skill biến mất hoàn toàn khỏi branch chính, file `tombstones.json` được cập nhật.
   - **Trường hợp Offline:** Commit được lưu an toàn tại local repo. UI hiển thị badge: `Central Library: ⬆️ 1 commit chưa push`. Khi có mạng trở lại hoặc khi người dùng bấm nút "Đồng bộ", commit này sẽ tự động được đẩy lên GitHub.

### B. Tại máy tính thứ hai của người dùng (Máy B - Multi-Device Synchronization)
Khi người dùng mở VXDevSync trên Máy B (nơi các Agent trên Máy B vẫn còn giữ bản copy cũ của kỹ năng vừa bị xóa ở Máy A):

```mermaid
sequenceDiagram
    autonumber
    actor Dev as Người dùng trên Máy B
    participant AppB as VXDevSync (Máy B)
    participant GitB as Git Engine (Máy B)
    participant GitHub as Remote GitHub Repo
    participant AgentsB as Local Agents (Máy B)

    Dev->>AppB: Bấm nút "Bắt đầu Đồng bộ" (Sync Now)
    AppB->>GitB: 1. Kích hoạt git pull từ GitHub
    GitB->>GitHub: git pull --rebase origin <branch>
    GitHub-->>GitB: Kéo commit xóa và file .vxdevsync/tombstones.json mới
    GitB-->>AppB: Hoàn tất pull: Central Library trên Máy B đã xóa thư mục skill
    
    AppB->>AppB: 2. Đọc file .vxdevsync/tombstones.json vừa cập nhật
    AppB->>AgentsB: 3. Quét các Agent trên Máy B (Antigravity, Codex, Claude)
    Note over AppB,AgentsB: Phát hiện Agent trên Máy B vẫn còn skill nằm trong tombstones.json
    AppB->>AgentsB: 4. Tự động Xóa dọn dẹp (Purge) thư mục skill khỏi tất cả Agent trên Máy B
    
    AppB->>AppB: 5. Chạy Upstream Scanner (Lúc này các Agent đã sạch, không bị sync ngược)
    AppB->>AppB: 6. Chạy Downstream Sync & Rules Adapter
    AppB->>Dev: Hiển thị Toast: "Đã đồng bộ và dọn dẹp kỹ năng đã xóa theo GitHub"
```

### C. Khôi phục Kỹ năng đã Xóa (Undo / Restore via Git History)
Do Central Library được bảo trợ bởi Git:
1. Nếu dev muốn phục hồi một kỹ năng đã xóa:
   - Vào Settings → tab Skills Sync → mục **"Quản lý Tombstones"**.
   - Bấm nút **"Phục hồi" (Restore)** bên cạnh tên kỹ năng.
2. Hệ thống tự động:
   - Xóa tên kỹ năng khỏi `.vxdevsync/tombstones.json`.
   - Tìm commit xóa gần nhất và chạy `git checkout <commit_sha>~1 -- skills/<skill_name>`.
   - Tạo commit mới: `chore(skills): restore skill '<skill_name>'` và push lên GitHub.
   - Tự động deploy kỹ năng trở lại các Agent đang active.

