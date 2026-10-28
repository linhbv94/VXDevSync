import asyncio
import os
import sys
import time
import threading
from functools import wraps
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.config_manager import ConfigManager
from src.git_engine import GitEngine, RepoStatus
from src.skills_engine import SkillsEngine
from src.adapter_engine import AdapterEngine

def exclusive_mutation(function):
    @wraps(function)
    def call(self, *args, **kwargs):
        if not self._mutation_lock.acquire(blocking=False):
            return {"success": False, "error": "Đang có thao tác khác; hãy chờ hoàn tất"}
        try:
            return function(self, *args, **kwargs)
        except (ValueError, OSError) as error:
            return {"success": False, "error": str(error)}
        finally:
            self._mutation_lock.release()
    return call

class BridgeApi:
    """Cung cấp các API callable từ JavaScript qua pywebview window.pywebview.api."""

    def __init__(self, config_manager: ConfigManager, window_getter=None):
        self._mutation_lock = threading.Lock()
        self._updater = None
        self._config_manager = config_manager
        self._window_getter = window_getter
        self._window_maximized = False
        self._git_engine = GitEngine()
        self._skills_engine = SkillsEngine()
        self._adapter_engine = AdapterEngine()

    def _set_window_maximized(self, value):
        self._window_maximized = bool(value)

    def window_action(self, action: str) -> Dict[str, Any]:
        """Limited chrome controls. Never dispatch arbitrary bridge/native methods."""
        if action not in ("minimize", "toggle_maximize", "close"):
            return {"success": False, "error": "Thao tác cửa sổ không hợp lệ"}
        window = self._window_getter() if self._window_getter else None
        if window is None:
            return {"success": False, "error": "Không có cửa sổ đang hoạt động"}
        if action == "minimize":
            window.minimize()
        elif action == "close":
            window.destroy()
        elif self._window_maximized:
            window.restore()
        else:
            window.maximize()
        return {"success": True}

    def get_initial_state(self) -> Dict[str, Any]:
        """Lấy toàn bộ cấu hình và trạng thái hệ thống khi khởi động ứng dụng."""
        cfg = self._config_manager.config
        default_paths = self._config_manager.get_default_agent_paths()

        # Dò tìm xem các agent có thực sự tồn tại trên máy không
        detected_agents = {
            k: Path(v).exists() for k, v in default_paths.items()
        }

        # Nếu chưa cấu hình scan_path, tự động gợi ý thư mục phù hợp
        suggested_path = cfg.git_sync.scan_path
        if not suggested_path:
            work_dir = Path.home() / "_Work"
            if work_dir.exists():
                suggested_path = str(work_dir)
            else:
                suggested_path = str(Path.home())

        return {
            "platform": "macos" if sys.platform == "darwin" else "windows" if sys.platform == "win32" else "other",
            "is_first_run": self._config_manager.is_first_run,
            "config_error": self._config_manager.load_error,
            "version": cfg.version,
            "general": {
                "lang": cfg.general.lang,
                "theme": cfg.general.theme,
                "default_tab": cfg.general.default_tab,
                "auto_scan_on_startup": cfg.general.auto_scan_on_startup
            },
            "git_sync": {
                "scan_path": cfg.git_sync.scan_path or suggested_path,
                "recent_paths": cfg.git_sync.recent_paths,
                "ignore_list": cfg.git_sync.ignore_list,
                "max_depth": cfg.git_sync.max_depth,
                "max_concurrency": cfg.git_sync.max_concurrency,
                "timeout": cfg.git_sync.timeout
            },
            "skills_sync": {
                "skills_lib": cfg.skills_sync.skills_lib,
                "git_repo": cfg.skills_sync.git_repo,
                "agents": cfg.skills_sync.agents,
                "custom_agent_paths": cfg.skills_sync.custom_agent_paths,
                "ignore_patterns": cfg.skills_sync.ignore_patterns,
                "deleted_skills": cfg.skills_sync.deleted_skills,
                "default_agent_paths": default_paths,
                "detected_agents": detected_agents
            }
        }

    @exclusive_mutation
    def save_config(self, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cập nhật và lưu file cấu hình config.json."""
        success = self._config_manager.update_from_dict(new_data)
        return {"success": success, "error": "" if success else "Không thể lưu config"}

    def pick_folder(self, initial_dir: Optional[str] = None) -> Dict[str, Any]:
        """Mở hộp thoại chọn thư mục gốc của hệ điều hành."""
        window = self._window_getter() if self._window_getter else None
        if window:
            import webview
            result = window.create_file_dialog(
                webview.FOLDER_DIALOG,
                directory=initial_dir or str(Path.home())
            )
            if result and len(result) > 0:
                selected = result[0]
                return {"canceled": False, "path": selected}
        return {"canceled": True, "path": ""}

    def scan_git_workspace(self, scan_path: Optional[str] = None, max_depth: Optional[int] = None) -> Dict[str, Any]:
        """Quét và phân tích trạng thái toàn bộ repositories trong workspace."""
        cfg = self._config_manager.config
        target_path = Path(scan_path) if scan_path else Path(cfg.git_sync.scan_path)
        depth = max_depth if max_depth is not None else cfg.git_sync.max_depth
        ignore_list = cfg.git_sync.ignore_list

        if not target_path.exists() or not target_path.is_dir():
            return {
                "success": False,
                "repos": [],
                "elapsed_sec": 0.0,
                "error": f"Thư mục không tồn tại: {target_path}"
            }

        start_time = time.time()
        # Lưu vào recent paths nếu hợp lệ
        self._config_manager.add_recent_path(str(target_path))

        # Chạy bất đồng bộ
        repos = asyncio.run(
            self._git_engine.scan_and_check_all_async(
                root_path=target_path,
                ignore_list=ignore_list,
                max_depth=depth,
                concurrency=cfg.git_sync.max_concurrency,
                timeout=cfg.git_sync.timeout
            )
        )
        elapsed = round(time.time() - start_time, 2)

        return {
            "success": True,
            "scan_path": str(target_path),
            "repos": [r.to_dict() for r in repos],
            "elapsed_sec": elapsed,
            "total_count": len(repos)
        }

    @exclusive_mutation
    def sync_git_repos(self, repo_paths: List[str], action: str = "smart_sync") -> Dict[str, Any]:
        """Đồng bộ một danh sách repositories được tick chọn (hoặc tất cả)."""
        results = []
        success_count = 0
        cfg = self._config_manager.load_config()
        ignore_list = set(cfg.git_sync.ignore_list or [])

        for p_str in repo_paths:
            p = Path(p_str)
            if p.name in ignore_list or any(part in ignore_list for part in p.parts):
                results.append({
                    "path": str(p),
                    "name": p.name,
                    "action": action,
                    "success": False,
                    "message": "Bỏ qua an toàn: Repository đã nằm trong danh sách loại trừ (Ignored)",
                    "cmd": "",
                    "raw_error": "Repo is in ignore_list"
                })
                continue

            res = self._git_engine.sync_single_repo(p, action=action)
            if res.get("success"):
                success_count += 1
            results.append(res)

        failed_count = len(repo_paths) - success_count
        return {
            "success": True,
            "total": len(repo_paths),
            "success_count": success_count,
            "failed_count": failed_count,
            "results": results
        }

    def toggle_git_ignore(self, repo_name_or_rel: str, add: bool = True) -> Dict[str, Any]:
        """Thêm hoặc gỡ bỏ một repo khỏi danh sách loại trừ (ignore_list)."""
        if add:
            ok = self._config_manager.add_to_git_ignore(repo_name_or_rel)
        else:
            ok = self._config_manager.remove_from_git_ignore(repo_name_or_rel)
        return {
            "success": ok,
            "ignore_list": self._config_manager.config.git_sync.ignore_list
        }

    def get_skills_inventory(self) -> Dict[str, Any]:
        """Lấy danh sách ma trận Kỹ năng (Skills Inventory)."""
        cfg = self._config_manager.config
        lib_path = Path(cfg.skills_sync.skills_lib) if cfg.skills_sync.skills_lib else Path("")
        defaults = self._config_manager.get_default_agent_paths()
        agent_paths = {}
        for ag in ["anti", "codex", "claude"]:
            custom = cfg.skills_sync.custom_agent_paths.get(ag)
            agent_paths[ag] = custom if custom else defaults.get(ag, "")

        active_agents = [ag for ag, state in cfg.skills_sync.agents.items() if state == 1]

        # Kiểm tra nếu có repo Git ở Central Library thì dọn trước các skills trong tombstones từ GitHub
        purged = []
        # Inventory is read-only. Apply remote tombstones only during explicit sync.

        inventory = self._skills_engine.get_skills_inventory(
            library_path=lib_path,
            agent_paths=agent_paths,
            active_agents=active_agents,
            ignore_patterns=cfg.skills_sync.ignore_patterns,
            deleted_skills=cfg.skills_sync.deleted_skills
        )

        return {
            "success": True,
            "skills_lib": str(lib_path),
            "skills": [s.to_dict() for s in inventory],
            "total_count": len(inventory),
            "purged_tombstones": purged
        }

    @exclusive_mutation
    def toggle_agent(self, agent_name: str, is_active: bool) -> Dict[str, Any]:
        """Bật hoặc tắt trạng thái kích hoạt của một AI Agent."""
        ok = self._config_manager.toggle_agent(agent_name, is_active)
        return {
            "success": ok,
            "agents": self._config_manager.config.skills_sync.agents
        }

    @exclusive_mutation
    def set_skills_library_path(self, new_path: str) -> Dict[str, Any]:
        """Thay đổi thư mục Central Skills Library."""
        p = Path(new_path).expanduser().resolve()
        if not p.exists() or not p.is_dir():
            return {"success": False, "error": "Thư mục không tồn tại"}

        self._config_manager.config.skills_sync.skills_lib = str(p)
        # Nếu thư mục có Git repo, tự phát hiện git_repo URL
        code, url, _ = self._git_engine.run_cmd(["remote", "get-url", "origin"], cwd=p)
        if code == 0 and url.strip():
            self._config_manager.config.skills_sync.git_repo = url.strip()

        self._config_manager.save_config()
        return {
            "success": True,
            "skills_lib": str(p),
            "git_repo": self._config_manager.config.skills_sync.git_repo
        }

    def _library_preflight(self, library):
        if not (library / ".git").is_dir():
            return
        code, staged, err = self._git_engine.run_cmd(["diff", "--cached", "--name-only"], library)
        if code or staged:
            raise ValueError("Library có thay đổi đang staged; hãy hoàn tất commit riêng trước khi sync")
        code, dirty, err = self._git_engine.run_cmd(["status", "--porcelain"], library)
        if code:
            raise ValueError("Không kiểm tra được library")
        code, branch, err = self._git_engine.run_cmd(["branch", "--show-current"], library)
        if code or not branch:
            raise ValueError("Library cần nhánh Git hợp lệ")
        code, _, err = self._git_engine.run_cmd(["fetch", "origin", branch], library)
        if code:
            raise ValueError("Không fetch được library; chưa thực hiện thay đổi: " + err)
        code, counts, err = self._git_engine.run_cmd(["rev-list", "--left-right", "--count", "HEAD...FETCH_HEAD"], library)
        if code:
            raise ValueError("Không xác minh được lịch sử library")
        ahead, behind = map(int, counts.split())
        if behind and (ahead or dirty):
            raise ValueError("Library có thay đổi local/remote cần xử lý thủ công trước sync")
        if behind:
            code, _, err = self._git_engine.run_cmd(["pull", "--ff-only", "origin", branch], library)
            if code:
                raise ValueError("Không pull an toàn được library: " + err)

    def _commit_library_changes(self, library, message):
        if not (library / ".git").is_dir():
            return False, False, ""
        # Stage only owned paths, leaving unrelated local files untouched.
        paths = [p for p in ["skills", "AGENTS.md", ".vxdevsync/tombstones.json"]
                 if (library / p).exists() or self._git_engine.run_cmd(["ls-files", "--", p], library)[1]]
        if not paths:
            return False, False, ""
        code, _, err = self._git_engine.run_cmd(["add", "-A", "--", *paths], library)
        if code:
            return False, False, err
        code, changes, err = self._git_engine.run_cmd(["diff", "--cached", "--name-only"], library)
        if code:
            return False, False, err
        committed = bool(changes)
        if committed:
            code, _, err = self._git_engine.run_cmd(["commit", "-m", message], library)
            if code:
                return False, False, err
        code, branch, err = self._git_engine.run_cmd(["branch", "--show-current"], library)
        if code or not branch:
            return True, False, "Đã commit local; không xác minh được nhánh để push"
        code, _, err = self._git_engine.run_cmd(["push", "origin", f"HEAD:refs/heads/{branch}"], library, timeout=15)
        return committed, code == 0, "Đã đồng bộ lên Git" if code == 0 else "Thay đổi còn ở local; push thất bại: " + err

    @exclusive_mutation
    def sync_skills_unified(self) -> Dict[str, Any]:
        """
        Tiến trình Đồng bộ Hợp nhất (Unified Smart Sync):
        1. Dọn dẹp Tombstone từ Git
        2. Upstream Scanner (Skills từ Agent về Library)
        3. Downstream Deploy (Skills từ Library sang Active Agents)
        4. Rules Adapter (AGENTS.md ↔ CLAUDE.md)
        5. Git Commit & Push lên GitHub nếu có repo
        """
        cfg = self._config_manager.config
        if not cfg.skills_sync.skills_lib.strip():
            return {"success": False, "error": "Chưa cấu hình Central Skills Library."}
        lib_path = Path(cfg.skills_sync.skills_lib).expanduser().resolve()

        if not lib_path.exists() or not lib_path.is_dir():
            return {"success": False, "error": "Chưa cấu hình Central Skills Library hoặc đường dẫn không hợp lệ."}

        defaults = self._config_manager.get_default_agent_paths()
        agent_paths = {}
        for ag in ["anti", "codex", "claude"]:
            custom = cfg.skills_sync.custom_agent_paths.get(ag)
            agent_paths[ag] = custom if custom else defaults.get(ag, "")

        selected_agents = [ag for ag, state in cfg.skills_sync.agents.items() if state == 1]
        all_agents = ["anti", "codex", "claude"]

        self._library_preflight(lib_path)

        # 1. Dọn dẹp Tombstone từ file .vxdevsync/tombstones.json kéo từ remote
        purged = self._skills_engine.sync_tombstones_from_git_repo(lib_path, agent_paths, all_agents)

        # 2. Upstream Skills
        upstream_files = self._skills_engine.scan_and_sync_upstream(
            library_path=lib_path,
            agent_paths=agent_paths,
            selected_agents=selected_agents,
            ignore_patterns=cfg.skills_sync.ignore_patterns,
            deleted_skills=cfg.skills_sync.deleted_skills
        )

        # 3. Downstream Skills
        downstream_agents = self._skills_engine.deploy_skills_downstream(
            library_path=lib_path,
            agent_paths=agent_paths,
            selected_agents=selected_agents,
            ignore_patterns=cfg.skills_sync.ignore_patterns
        )

        # 4. Rules Adapter (Upstream + Downstream)
        rules_up_changed, rules_up_msg = self._adapter_engine.sync_rules_upstream(
            library_path=lib_path,
            agent_paths=agent_paths,
            selected_agents=selected_agents
        )
        rules_deployed = self._adapter_engine.deploy_rules_downstream(
            library_path=lib_path,
            agent_paths=agent_paths,
            selected_agents=selected_agents
        )

        _, git_pushed, git_msg = self._commit_library_changes(lib_path, "chore(skills): sync skills and rules")

        return {
            "success": True,
            "upstream_count": len(upstream_files),
            "upstream_files": upstream_files,
            "downstream_agents": downstream_agents,
            "rules_up_changed": rules_up_changed,
            "rules_deployed": rules_deployed,
            "purged_tombstones": purged,
            "git_pushed": git_pushed,
            "git_msg": git_msg
        }

    @exclusive_mutation
    def delete_skills_cascade(self, skill_names: List[str]) -> Dict[str, Any]:
        """
        Xóa Kỹ năng Triệt để & Thực thi Git Commit + Push TỨC THỜI.
        """
        if not skill_names:
            return {"success": False, "error": "Chưa chọn kỹ năng để xóa"}

        cfg = self._config_manager.config
        if not cfg.skills_sync.skills_lib.strip():
            return {"success": False, "error": "Chưa cấu hình Central Skills Library."}
        lib_path = Path(cfg.skills_sync.skills_lib).expanduser().resolve()
        defaults = self._config_manager.get_default_agent_paths()
        agent_paths = {}
        for ag in ["anti", "codex", "claude"]:
            custom = cfg.skills_sync.custom_agent_paths.get(ag)
            agent_paths[ag] = custom if custom else defaults.get(ag, "")

        all_agents = ["anti", "codex", "claude"]

        self._library_preflight(lib_path)

        # 1. Xóa vật lý & cập nhật tombstones.json trong library
        res = self._skills_engine.execute_delete_cascade(
            skill_names=skill_names,
            library_path=lib_path,
            agent_paths=agent_paths,
            all_agents=all_agents
        )

        # 2. Ghi nhận vào deleted_skills trong config_manager
        for name in skill_names:
            self._config_manager.add_deleted_skill_tombstone(name)

        git_committed, git_pushed, git_msg = self._commit_library_changes(lib_path, "chore(skills): delete selected skills")

        return {
            "success": True,
            "deleted_skills": skill_names,
            "deleted_locations": res.get("deleted_locations", []),
            "git_committed": git_committed,
            "git_pushed": git_pushed,
            "git_msg": git_msg
        }

    @exclusive_mutation
    def restore_skill(self, skill_name: str) -> Dict[str, Any]:
        self._skills_engine.validate_skill_name(skill_name)
        cfg = self._config_manager.config
        if not cfg.skills_sync.skills_lib.strip():
            return {"success": False, "error": "Chưa cấu hình Central Skills Library"}
        library = Path(cfg.skills_sync.skills_lib).expanduser().resolve()
        self._library_preflight(library)
        removed = self._skills_engine.remove_tombstone_from_git_repo(library, skill_name)
        self._config_manager.remove_deleted_skill_tombstone(skill_name)
        committed, pushed, message = self._commit_library_changes(library, "chore(skills): restore tombstone")
        return {"success": True, "restored_skill": skill_name, "repo_tombstone_removed": removed,
                "git_committed": committed, "git_pushed": pushed, "git_msg": message}

    def check_updates(self):
        try:
            from src.updater import AppUpdater
            if self._updater is None:
                self._updater = AppUpdater()
            return self._updater.check()
        except Exception as error:
            return {"success": False, "error": "Chưa kiểm tra được cập nhật: " + str(error)}

    @exclusive_mutation
    def install_update(self):
        try:
            from src.updater import AppUpdater
            if self._updater is None:
                self._updater = AppUpdater()
            window = self._window_getter() if self._window_getter else None
            if window is None:
                return {"success": False, "error": "Không có cửa sổ để khởi động lại"}
            result = self._updater.install()
            window.destroy()
            return result
        except Exception as error:
            return {"success": False, "error": "Cập nhật thất bại: " + str(error)}
