import asyncio
import os
import sys
import time
from pathlib import Path
from typing import List, Dict, Any, Optional

from src.config_manager import ConfigManager
from src.git_engine import GitEngine, RepoStatus
from src.skills_engine import SkillsEngine
from src.adapter_engine import AdapterEngine

class BridgeApi:
    """Cung cấp các API callable từ JavaScript qua pywebview window.pywebview.api."""

    def __init__(self, config_manager: ConfigManager, window_getter=None):
        self.config_manager = config_manager
        self.window_getter = window_getter
        self._window_maximized = False
        self.git_engine = GitEngine()
        self.skills_engine = SkillsEngine()
        self.adapter_engine = AdapterEngine()

    def _set_window_maximized(self, value):
        self._window_maximized = bool(value)

    def window_action(self, action: str) -> Dict[str, Any]:
        """Limited chrome controls. Never dispatch arbitrary bridge/native methods."""
        if action not in ("minimize", "toggle_maximize", "close"):
            return {"success": False, "error": "Thao tác cửa sổ không hợp lệ"}
        window = self.window_getter() if self.window_getter else None
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
        cfg = self.config_manager.config
        default_paths = self.config_manager.get_default_agent_paths()

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
            "is_first_run": self.config_manager.is_first_run,
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

    def save_config(self, new_data: Dict[str, Any]) -> Dict[str, Any]:
        """Cập nhật và lưu file cấu hình config.json."""
        success = self.config_manager.update_from_dict(new_data)
        return {"success": success, "error": "" if success else "Không thể lưu config"}

    def pick_folder(self, initial_dir: Optional[str] = None) -> Dict[str, Any]:
        """Mở hộp thoại chọn thư mục gốc của hệ điều hành."""
        window = self.window_getter() if self.window_getter else None
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
        cfg = self.config_manager.config
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
        self.config_manager.add_recent_path(str(target_path))

        # Chạy bất đồng bộ
        repos = asyncio.run(
            self.git_engine.scan_and_check_all_async(
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

    def sync_git_repos(self, repo_paths: List[str], action: str = "smart_sync") -> Dict[str, Any]:
        """Đồng bộ một danh sách repositories được tick chọn (hoặc tất cả)."""
        results = []
        success_count = 0

        for p_str in repo_paths:
            p = Path(p_str)
            res = self.git_engine.sync_single_repo(p, action=action)
            if res.get("success"):
                success_count += 1
            results.append(res)

        return {
            "success": True,
            "total": len(repo_paths),
            "success_count": success_count,
            "results": results
        }

    def toggle_git_ignore(self, repo_name_or_rel: str, add: bool = True) -> Dict[str, Any]:
        """Thêm hoặc gỡ bỏ một repo khỏi danh sách loại trừ (ignore_list)."""
        if add:
            ok = self.config_manager.add_to_git_ignore(repo_name_or_rel)
        else:
            ok = self.config_manager.remove_from_git_ignore(repo_name_or_rel)
        return {
            "success": ok,
            "ignore_list": self.config_manager.config.git_sync.ignore_list
        }

    def get_skills_inventory(self) -> Dict[str, Any]:
        """Lấy danh sách ma trận Kỹ năng (Skills Inventory)."""
        cfg = self.config_manager.config
        lib_path = Path(cfg.skills_sync.skills_lib) if cfg.skills_sync.skills_lib else Path("")
        defaults = self.config_manager.get_default_agent_paths()
        agent_paths = {}
        for ag in ["anti", "codex", "claude"]:
            custom = cfg.skills_sync.custom_agent_paths.get(ag)
            agent_paths[ag] = custom if custom else defaults.get(ag, "")

        active_agents = [ag for ag, state in cfg.skills_sync.agents.items() if state == 1]

        # Kiểm tra nếu có repo Git ở Central Library thì dọn trước các skills trong tombstones từ GitHub
        purged = []
        if lib_path.exists():
            purged = self.skills_engine.sync_tombstones_from_git_repo(lib_path, agent_paths, ["anti", "codex", "claude"])

        inventory = self.skills_engine.get_skills_inventory(
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

    def toggle_agent(self, agent_name: str, is_active: bool) -> Dict[str, Any]:
        """Bật hoặc tắt trạng thái kích hoạt của một AI Agent."""
        ok = self.config_manager.toggle_agent(agent_name, is_active)
        return {
            "success": ok,
            "agents": self.config_manager.config.skills_sync.agents
        }

    def set_skills_library_path(self, new_path: str) -> Dict[str, Any]:
        """Thay đổi thư mục Central Skills Library."""
        p = Path(new_path).expanduser().resolve()
        if not p.exists() or not p.is_dir():
            return {"success": False, "error": "Thư mục không tồn tại"}

        self.config_manager.config.skills_sync.skills_lib = str(p)
        # Nếu thư mục có Git repo, tự phát hiện git_repo URL
        code, url, _ = self.git_engine.run_cmd(["remote", "get-url", "origin"], cwd=p)
        if code == 0 and url.strip():
            self.config_manager.config.skills_sync.git_repo = url.strip()

        self.config_manager.save_config()
        return {
            "success": True,
            "skills_lib": str(p),
            "git_repo": self.config_manager.config.skills_sync.git_repo
        }

    def sync_skills_unified(self) -> Dict[str, Any]:
        """
        Tiến trình Đồng bộ Hợp nhất (Unified Smart Sync):
        1. Dọn dẹp Tombstone từ Git
        2. Upstream Scanner (Skills từ Agent về Library)
        3. Downstream Deploy (Skills từ Library sang Active Agents)
        4. Rules Adapter (AGENTS.md ↔ CLAUDE.md)
        5. Git Commit & Push lên GitHub nếu có repo
        """
        cfg = self.config_manager.config
        lib_path = Path(cfg.skills_sync.skills_lib) if cfg.skills_sync.skills_lib else Path("")

        if not lib_path.exists() or not lib_path.is_dir():
            return {"success": False, "error": "Chưa cấu hình Central Skills Library hoặc đường dẫn không hợp lệ."}

        defaults = self.config_manager.get_default_agent_paths()
        agent_paths = {}
        for ag in ["anti", "codex", "claude"]:
            custom = cfg.skills_sync.custom_agent_paths.get(ag)
            agent_paths[ag] = custom if custom else defaults.get(ag, "")

        selected_agents = [ag for ag, state in cfg.skills_sync.agents.items() if state == 1]
        all_agents = ["anti", "codex", "claude"]

        # 0. Kéo bản mới nhất từ Git Remote về Central Library (nếu có Git repo) để nhận tombstones từ các máy khác
        git_pulled = False
        git_pull_msg = ""
        if (lib_path / ".git").is_dir():
            p_code, _, p_err = self.git_engine.run_cmd(["pull", "origin", "main"], cwd=lib_path, timeout=12)
            if p_code != 0:
                p_code, _, p_err = self.git_engine.run_cmd(["pull", "origin", "master"], cwd=lib_path, timeout=12)
            git_pulled = (p_code == 0)
            git_pull_msg = "Đã kéo cập nhật từ remote" if git_pulled else f"Không thể pull remote: {p_err}"

        # 1. Dọn dẹp Tombstone từ file .vxdevsync/tombstones.json kéo từ remote
        purged = self.skills_engine.sync_tombstones_from_git_repo(lib_path, agent_paths, all_agents)

        # 2. Upstream Skills
        upstream_files = self.skills_engine.scan_and_sync_upstream(
            library_path=lib_path,
            agent_paths=agent_paths,
            selected_agents=selected_agents,
            ignore_patterns=cfg.skills_sync.ignore_patterns,
            deleted_skills=cfg.skills_sync.deleted_skills
        )

        # 3. Downstream Skills
        downstream_agents = self.skills_engine.deploy_skills_downstream(
            library_path=lib_path,
            agent_paths=agent_paths,
            selected_agents=selected_agents,
            ignore_patterns=cfg.skills_sync.ignore_patterns
        )

        # 4. Rules Adapter (Upstream + Downstream)
        rules_up_changed, rules_up_msg = self.adapter_engine.sync_rules_upstream(
            library_path=lib_path,
            agent_paths=agent_paths,
            selected_agents=selected_agents
        )
        rules_deployed = self.adapter_engine.deploy_rules_downstream(
            library_path=lib_path,
            agent_paths=agent_paths,
            selected_agents=selected_agents
        )

        # 5. Git Commit & Push cho Central Library nếu có Git
        git_pushed = False
        git_msg = ""
        if (lib_path / ".git").is_dir():
            # Check status
            code, out, _ = self.git_engine.run_cmd(["status", "--porcelain"], cwd=lib_path)
            if code == 0 and out.strip():
                self.git_engine.run_cmd(["add", "-A"], cwd=lib_path)
                c_code, _, c_err = self.git_engine.run_cmd(["commit", "-m", "chore(skills): auto-sync skills and rules"], cwd=lib_path)
                if c_code == 0:
                    # Push
                    p_code, _, p_err = self.git_engine.run_cmd(["push", "origin", "main"], cwd=lib_path, timeout=15)
                    if p_code != 0:
                        # Thử branch master
                        p_code, _, p_err = self.git_engine.run_cmd(["push", "origin", "master"], cwd=lib_path, timeout=15)
                    git_pushed = (p_code == 0)
                    git_msg = "Đã push lên GitHub" if git_pushed else f"Không thể push: {p_err}"

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

    def delete_skills_cascade(self, skill_names: List[str]) -> Dict[str, Any]:
        """
        Xóa Kỹ năng Triệt để & Thực thi Git Commit + Push TỨC THỜI.
        """
        if not skill_names:
            return {"success": False, "error": "Chưa chọn kỹ năng để xóa"}

        cfg = self.config_manager.config
        lib_path = Path(cfg.skills_sync.skills_lib) if cfg.skills_sync.skills_lib else Path("")
        defaults = self.config_manager.get_default_agent_paths()
        agent_paths = {}
        for ag in ["anti", "codex", "claude"]:
            custom = cfg.skills_sync.custom_agent_paths.get(ag)
            agent_paths[ag] = custom if custom else defaults.get(ag, "")

        all_agents = ["anti", "codex", "claude"]

        # 1. Xóa vật lý & cập nhật tombstones.json trong library
        res = self.skills_engine.execute_delete_cascade(
            skill_names=skill_names,
            library_path=lib_path,
            agent_paths=agent_paths,
            all_agents=all_agents
        )

        # 2. Ghi nhận vào deleted_skills trong config_manager
        for name in skill_names:
            self.config_manager.add_deleted_skill_tombstone(name)

        # 3. Thực thi Git Commit & Push tức thì
        git_committed = False
        git_pushed = False
        git_msg = ""

        if lib_path.exists() and (lib_path / ".git").is_dir():
            self.git_engine.run_cmd(["add", "-A"], cwd=lib_path)
            commit_msg = f"chore(skills): delete skill(s) {', '.join(skill_names)}"
            c_code, _, c_err = self.git_engine.run_cmd(["commit", "-m", commit_msg], cwd=lib_path)
            if c_code == 0:
                git_committed = True
                # Push ngay lên GitHub
                p_code, _, p_err = self.git_engine.run_cmd(["push", "origin", "main"], cwd=lib_path, timeout=12)
                if p_code != 0:
                    p_code, _, p_err = self.git_engine.run_cmd(["push", "origin", "master"], cwd=lib_path, timeout=12)
                git_pushed = (p_code == 0)
                git_msg = "Đã commit và push lên GitHub" if git_pushed else "Đã commit local (sẽ tự push khi có mạng)"

        return {
            "success": True,
            "deleted_skills": skill_names,
            "deleted_locations": res.get("deleted_locations", []),
            "git_committed": git_committed,
            "git_pushed": git_pushed,
            "git_msg": git_msg
        }

    def restore_skill(self, skill_name: str) -> Dict[str, Any]:
        """Phục hồi một skill đã xóa khỏi danh sách Tombstone (cả config và git repo)."""
        self.config_manager.remove_deleted_skill_tombstone(skill_name)
        
        cfg = self.config_manager.config
        lib_path = Path(cfg.skills_sync.skills_lib) if cfg.skills_sync.skills_lib else Path("")
        repo_removed = False
        git_committed = False
        
        if lib_path.exists():
            repo_removed = self.skills_engine.remove_tombstone_from_git_repo(lib_path, skill_name)
            if (lib_path / ".git").is_dir():
                self.git_engine.run_cmd(["add", ".vxdevsync/tombstones.json"], cwd=lib_path)
                c_code, _, _ = self.git_engine.run_cmd(
                    ["commit", "-m", f"chore(skills): restore skill {skill_name} from tombstones"],
                    cwd=lib_path
                )
                if c_code == 0:
                    git_committed = True
                    self.git_engine.run_cmd(["push", "origin", "main"], cwd=lib_path, timeout=12)
                    self.git_engine.run_cmd(["push", "origin", "master"], cwd=lib_path, timeout=12)

        return {
            "success": True, 
            "restored_skill": skill_name, 
            "repo_tombstone_removed": repo_removed,
            "git_committed": git_committed
        }
