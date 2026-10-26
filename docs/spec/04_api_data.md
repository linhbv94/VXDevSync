# 04. Cấu trúc Dữ liệu & Bridge API — VXDevSync
Version: 1.0.0 — Ngày cập nhật: 2026-10-15

Tài liệu này đặc tả lược đồ dữ liệu cấu hình tập trung (`config.json`), các mô hình dữ liệu nội bộ (Data Models) và hợp đồng giao tiếp (Desktop Bridge API Contract) giữa Python Core Engine và Webview Frontend.

---

## 1. File Cấu hình Hợp nhất (`config.json`)

File cấu hình duy nhất được lưu tại:
- **macOS:** `~/Library/Application Support/VXDevSync/config.json`
- **Windows:** `%APPDATA%\VXDevSync\config.json`

### A. Lược đồ Cấu hình (JSON Schema & Sample)

```json
{
  "version": "1.0.0",
  "general": {
    "lang": "vi",
    "theme": "dark",
    "default_tab": "git_sync",
    "auto_scan_on_startup": true
  },
  "git_sync": {
    "scan_path": "/Users/vic/_Work",
    "recent_paths": [
      "/Users/vic/_Work",
      "/Users/vic/_Work/zTools"
    ],
    "ignore_list": [
      "node_modules",
      "venv",
      ".venv",
      "build",
      "dist",
      ".git"
    ],
    "max_depth": 3,
    "max_concurrency": 8,
    "timeout": 10
  },
  "skills_sync": {
    "skills_lib": "/Users/vic/my_skills_library",
    "git_repo": "https://github.com/linhbv94/my_skills_library.git",
    "agents": {
      "anti": 1,
      "codex": 1,
      "claude": 0
    },
    "custom_agent_paths": {
      "anti": "",
      "codex": "",
      "claude": ""
    },
    "ignore_patterns": [
      "**/.system/**",
      "**/.git/**",
      "**/.DS_Store",
      "**/desktop.ini",
      "**/*.tmp",
      "**/*.bak*"
    ],
    "deleted_skills": [
      {
        "name": "_mkt9_obsolete_test",
        "deleted_at": "2026-10-15T10:30:00Z"
      }
    ]
  }
}
```

### B. File "Sổ Khai Tử" Dùng Chung Trong Git Repo (`.vxdevsync/tombstones.json`)
File này được lưu ngay trong repository của Central Skills Library và commit lên GitHub để phục vụ đồng bộ việc xóa kỹ năng xuyên thiết bị:

```json
{
  "schema_version": "1.0.0",
  "updated_at": "2026-10-15T10:35:00Z",
  "tombstones": [
    {
      "name": "_mkt9_obsolete_test",
      "deleted_at": "2026-10-15T10:30:00Z",
      "deleted_by": "vic-macbook",
      "reason": "Skill deprecated"
    }
  ]
}
```

---


## 2. Mô hình Dữ liệu Nội bộ (Internal Data Models)

### A. Model Trạng thái Repository Git (`RepoStatus`)

```python
from dataclasses import dataclass, field
from typing import Optional, List

@dataclass
class RepoStatus:
    name: str                       # Tên thư mục repo (ví dụ: 'vxmedia')
    path: str                       # Đường dẫn tuyệt đối đến repo
    rel_path: str                   # Đường dẫn tương đối từ scan_path
    current_branch: str             # Nhánh hiện tại (ví dụ: 'main', 'dev')
    is_git: bool = True             # Có phải thư mục Git hợp lệ không
    has_remote: bool = True         # Có gắn remote origin không
    is_clean: bool = True           # Không có file thay đổi dở dang
    is_dirty: bool = False          # Có file sửa đổi chưa commit
    dirty_files_count: int = 0      # Số lượng file dirty
    ahead_count: int = 0            # Số commit local chưa push lên remote
    behind_count: int = 0           # Số commit remote chưa pull về local
    is_diverged: bool = False       # Lệch cả 2 chiều (ahead > 0 và behind > 0)
    suggested_action: str = ""      # 'Up-to-date', 'Auto Pull', 'Auto Push', 'Safe-Skip', 'Manual Merge'
    is_ignored: bool = False        # Nằm trong ignore_list
```

### B. Model Kỹ năng AI Inventory (`SkillItem`)

```python
@dataclass
class AgentSkillPresence:
    exists: bool                    # Kỹ năng có mặt tại Agent này không
    is_synced: bool                 # Có cùng mã hash với Central Library không
    mtime: float                    # Timestamp chỉnh sửa gần nhất
    file_count: int                 # Số lượng files trong thư mục skill

@dataclass
class SkillItem:
    name: str                       # Tên kỹ năng (ví dụ: '_spec0_system')
    in_library: bool                # Có tồn tại trong Central Library không
    agents: dict                    # Dict[str, AgentSkillPresence] ('anti', 'codex', 'claude')
    is_tombstoned: bool             # Đang nằm trong danh sách đã xóa (Tombstone)
```

---

## 3. Hợp đồng Desktop Bridge API (Python ↔ Webview JS)

Toàn bộ các phương thức được định nghĩa trên lớp `Api` trong Python và được phơi bày qua `window.pywebview.api` trên Webview Frontend. Mọi lệnh gọi đều là bất đồng bộ (Promise).

### A. Nhóm Quản trị Cấu hình & Hệ thống (System & Config)

| Tên Phương thức | Tham số đầu vào | Dữ liệu trả về (Return) | Mô tả công dụng |
| :--- | :--- | :--- | :--- |
| `get_initial_state()` | Không | `dict` (Config, IsFirstRun, SystemInfo) | Nạp trạng thái ban đầu khi khởi động ứng dụng. |
| `save_config(config_dict)` | `new_config: dict` | `{"success": bool, "error": str}` | Lưu toàn bộ cấu hình mới vào `config.json`. |
| `pick_folder(current_path)` | `initial_dir: Optional[str]` | `{"path": str, "canceled": bool}` | Mở hộp thoại chọn thư mục gốc của hệ điều hành. |
| `open_in_terminal(path)` | `folder_path: str` | `{"success": bool}` | Mở Terminal/Finder/Explorer tại thư mục chỉ định. |

### B. Nhóm Nghiệp vụ Git Multi-Sync

| Tên Phương thức | Tham số đầu vào | Dữ liệu trả về (Return) | Mô tả công dụng |
| :--- | :--- | :--- | :--- |
| `scan_git_workspace(path, depth)` | `scan_path: str, max_depth: int` | `{"repos": List[RepoStatus], "elapsed_sec": float}` | Quét bất đồng bộ toàn bộ repos trong workspace. |
| `sync_git_repos(repo_paths, mode)`| `paths: List[str], mode: str` (`"smart"`, `"pull"`, `"push"`) | `{"results": List[dict], "summary": str}` | Thực thi đồng bộ Git cho danh sách các repo được chọn. |
| `toggle_repo_ignore(path, state)` | `repo_name_or_path: str, add: bool` | `{"success": bool, "ignore_list": List[str]}` | Thêm hoặc xóa repo khỏi danh sách loại trừ trên GUI. |

### C. Nhóm Nghiệp vụ Skills Auto-Sync & Safe Delete

| Tên Phương thức | Tham số đầu vào | Dữ liệu trả về (Return) | Mô tả công dụng |
| :--- | :--- | :--- | :--- |
| `get_skills_inventory()` | Không | `{"skills": List[SkillItem], "agents_status": dict}` | Quét và tổng hợp ma trận Kỹ năng trên toàn hệ thống. |
| `toggle_agent(agent_key, active)`| `agent: str, is_active: bool` | `{"success": bool, "agents": dict}` | Bật hoặc tắt trạng thái kích hoạt của một AI Agent. |
| `sync_skills_now()` | Không | `{"synced_files": List[str], "affected_agents": List[str]}` | Chạy tiến trình đồng bộ 2 chiều (Upstream + Downstream). |
| `delete_skill_cascade(skill_name)`| `skill_name: str` | `{"success": bool, "deleted_locations": List[str]}` | **Xóa vật lý triệt để** skill tại Library và các Agents, đồng thời ghi vào Tombstone list. |
| `unblock_tombstone(skill_name)` | `skill_name: str` | `{"success": bool}` | Xóa skill khỏi danh sách Tombstone khi muốn tạo lại. |

## Gate phát hành1.0.0 — QA độc lập2026-10-26

[QA và sửa lỗi thực tế](../release_1_0_0_review.md) ưu tiên hơn các tuyên bố hoàn tất trước đây. Inventory chỉ đọc; Sync không gom file ngoài phạm vi, dirty/staged/diverged phải safe-skip, tên skill không được thoát root/protected folders. Cấu hình lỗi giữ nguyên và có previous backup. Updater Python dùng signed manifest Ed25519/digest, Updates tab/startup check, mutation guard và staging/rollback; không dùng schema Tauri. Windows và haiMac có cùng engine, installer/updater khác nhau. [Vận hành](../desktop_release.md).
