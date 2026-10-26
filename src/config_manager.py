import json
import os
import sys
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional

DEFAULT_IGNORE_PATTERNS = [
    "**/.system/**",
    "**/.git/**",
    "**/.DS_Store",
    "**/desktop.ini",
    "**/*.tmp",
    "**/*.bak*"
]

DEFAULT_GIT_IGNORE_LIST = [
    "node_modules",
    "venv",
    ".venv",
    "build",
    "dist",
    ".git"
]

@dataclass
class GeneralConfig:
    lang: str = "vi"
    theme: str = "dark"
    default_tab: str = "git_sync"
    auto_scan_on_startup: bool = True

@dataclass
class GitSyncConfig:
    scan_path: str = ""
    recent_paths: List[str] = field(default_factory=list)
    ignore_list: List[str] = field(default_factory=lambda: list(DEFAULT_GIT_IGNORE_LIST))
    max_depth: int = 3
    max_concurrency: int = 8
    timeout: int = 10

@dataclass
class SkillsSyncConfig:
    skills_lib: str = ""
    git_repo: str = ""
    agents: Dict[str, int] = field(default_factory=lambda: {"anti": 1, "codex": 1, "claude": 0})
    custom_agent_paths: Dict[str, str] = field(default_factory=lambda: {"anti": "", "codex": "", "claude": ""})
    ignore_patterns: List[str] = field(default_factory=lambda: list(DEFAULT_IGNORE_PATTERNS))
    deleted_skills: List[Dict[str, Any]] = field(default_factory=list)

@dataclass
class AppConfig:
    version: str = "1.0.0"
    general: GeneralConfig = field(default_factory=GeneralConfig)
    git_sync: GitSyncConfig = field(default_factory=GitSyncConfig)
    skills_sync: SkillsSyncConfig = field(default_factory=SkillsSyncConfig)

class ConfigManager:
    """Quản lý nạp và lưu file cấu hình config.json hợp nhất của VXDevSync."""

    def __init__(self, custom_dir: Optional[Path] = None):
        if custom_dir:
            self.config_dir = custom_dir
        elif os.environ.get("VXDEVSYNC_CONFIG_DIR"):
            self.config_dir = Path(os.environ["VXDEVSYNC_CONFIG_DIR"])
        else:
            self.config_dir = self._get_system_config_dir()
            
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_file = self.config_dir / "config.json"
        self.config: AppConfig = AppConfig()
        self.is_first_run: bool = not self.config_file.exists()
        self.load_config()

    @staticmethod
    def _get_system_config_dir() -> Path:
        home = Path.home()
        if sys.platform == "darwin":
            return home / "Library" / "Application Support" / "VXDevSync"
        elif sys.platform == "win32":
            app_data = Path(os.environ.get("APPDATA", home / "AppData" / "Roaming"))
            return app_data / "VXDevSync"
        else:
            return home / ".config" / "VXDevSync"

    @staticmethod
    def get_default_agent_paths() -> Dict[str, str]:
        home = Path.home()
        if sys.platform == "win32":
            user_profile = Path(os.environ.get("USERPROFILE", home))
            return {
                "anti": str(user_profile / ".gemini" / "config"),
                "codex": str(user_profile / ".codex"),
                "claude": str(user_profile / ".claude")
            }
        else:
            return {
                "anti": str(home / ".gemini" / "config"),
                "codex": str(home / ".codex"),
                "claude": str(home / ".claude")
            }

    def load_config(self) -> AppConfig:
        if self.config_file.exists():
            try:
                with open(self.config_file, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # General
                gen_data = data.get("general", {})
                self.config.general.lang = gen_data.get("lang", "vi")
                self.config.general.theme = gen_data.get("theme", "dark")
                self.config.general.default_tab = gen_data.get("default_tab", "git_sync")
                self.config.general.auto_scan_on_startup = gen_data.get("auto_scan_on_startup", True)

                # Git Sync
                git_data = data.get("git_sync", {})
                self.config.git_sync.scan_path = git_data.get("scan_path", "")
                self.config.git_sync.recent_paths = git_data.get("recent_paths", [])
                self.config.git_sync.ignore_list = git_data.get("ignore_list", list(DEFAULT_GIT_IGNORE_LIST))
                self.config.git_sync.max_depth = git_data.get("max_depth", 3)
                self.config.git_sync.max_concurrency = git_data.get("max_concurrency", 8)
                self.config.git_sync.timeout = git_data.get("timeout", 10)

                # Skills Sync
                skills_data = data.get("skills_sync", {})
                self.config.skills_sync.skills_lib = skills_data.get("skills_lib", "")
                self.config.skills_sync.git_repo = skills_data.get("git_repo", "")
                self.config.skills_sync.agents = skills_data.get("agents", {"anti": 1, "codex": 1, "claude": 0})
                self.config.skills_sync.custom_agent_paths = skills_data.get("custom_agent_paths", {"anti": "", "codex": "", "claude": ""})
                self.config.skills_sync.ignore_patterns = skills_data.get("ignore_patterns", list(DEFAULT_IGNORE_PATTERNS))
                self.config.skills_sync.deleted_skills = skills_data.get("deleted_skills", [])
            except Exception as e:
                print(f"[ConfigManager] Lỗi đọc config ({e}), lưu cấu hình mặc định.")
                self.save_config()
        else:
            self.save_config()

        return self.config

    def save_config(self) -> bool:
        try:
            self.config_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "version": self.config.version,
                "general": asdict(self.config.general),
                "git_sync": asdict(self.config.git_sync),
                "skills_sync": asdict(self.config.skills_sync)
            }
            with open(self.config_file, "w", encoding="utf-8") as f:
                json.dump(payload, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[ConfigManager] Lỗi lưu file config: {e}")
            return False

    def update_from_dict(self, data: Dict[str, Any]) -> bool:
        """Cập nhật config từ dictionary (ví dụ nhận từ GUI Bridge)."""
        try:
            if "general" in data:
                for k, v in data["general"].items():
                    if hasattr(self.config.general, k):
                        setattr(self.config.general, k, v)
            if "git_sync" in data:
                for k, v in data["git_sync"].items():
                    if hasattr(self.config.git_sync, k):
                        setattr(self.config.git_sync, k, v)
            if "skills_sync" in data:
                for k, v in data["skills_sync"].items():
                    if hasattr(self.config.skills_sync, k):
                        setattr(self.config.skills_sync, k, v)
            return self.save_config()
        except Exception as e:
            print(f"[ConfigManager] Lỗi cập nhật config từ dict: {e}")
            return False

    def add_recent_path(self, new_path: str) -> None:
        """Thêm một đường dẫn workspace vào danh sách gần đây (tối đa 5 mục, không trùng lặp)."""
        if not new_path:
            return
        clean_path = str(Path(new_path).resolve())
        paths = [p for p in self.config.git_sync.recent_paths if str(Path(p).resolve()) != clean_path]
        paths.insert(0, clean_path)
        self.config.git_sync.recent_paths = paths[:5]
        self.config.git_sync.scan_path = clean_path
        self.save_config()

    def add_to_git_ignore(self, pattern: str) -> bool:
        if pattern and pattern not in self.config.git_sync.ignore_list:
            self.config.git_sync.ignore_list.append(pattern)
            return self.save_config()
        return False

    def remove_from_git_ignore(self, pattern: str) -> bool:
        if pattern in self.config.git_sync.ignore_list:
            self.config.git_sync.ignore_list.remove(pattern)
            return self.save_config()
        return False

    def toggle_agent(self, agent_name: str, active: bool) -> bool:
        if agent_name in self.config.skills_sync.agents:
            self.config.skills_sync.agents[agent_name] = 1 if active else 0
            return self.save_config()
        return False

    def add_deleted_skill_tombstone(self, skill_name: str, deleted_by: str = "vxdevsync") -> bool:
        """Ghi nhận skill vào danh sách Tombstone (deleted_skills)."""
        import datetime
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
        # Xóa entry cũ nếu trùng tên
        self.config.skills_sync.deleted_skills = [
            item for item in self.config.skills_sync.deleted_skills if item.get("name") != skill_name
        ]
        self.config.skills_sync.deleted_skills.append({
            "name": skill_name,
            "deleted_at": now_iso,
            "deleted_by": deleted_by
        })
        return self.save_config()

    def remove_deleted_skill_tombstone(self, skill_name: str) -> bool:
        """Xóa skill khỏi Tombstone list khi người dùng muốn phục hồi hoặc tạo lại."""
        old_len = len(self.config.skills_sync.deleted_skills)
        self.config.skills_sync.deleted_skills = [
            item for item in self.config.skills_sync.deleted_skills if item.get("name") != skill_name
        ]
        if len(self.config.skills_sync.deleted_skills) != old_len:
            return self.save_config()
        return False
