import unittest
import shutil
import tempfile
from pathlib import Path

from src.config_manager import ConfigManager
from src.git_engine import GitEngine
from src.skills_engine import SkillsEngine
from src.adapter_engine import AdapterEngine
from src.bridge_api import BridgeApi


class TestVXDevSync(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp(prefix="vxdevsync_test_")
        self.test_path = Path(self.test_dir)
        
        # Tạo thư mục config tạm
        self.config_dir = self.test_path / "config"
        self.config_file = self.config_dir / "config.json"
        
        # Khởi tạo ConfigManager với thư mục tạm
        self.config_mgr = ConfigManager(custom_dir=self.config_dir)
        self.api = BridgeApi(config_manager=self.config_mgr)

    def tearDown(self):
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_config_initial_state(self):
        state = self.api.get_initial_state()
        self.assertIn("general", state)
        self.assertIn("git_sync", state)
        self.assertIn("skills_sync", state)
        self.assertEqual(state["general"]["lang"], "vi")
        self.assertEqual(state["general"]["default_tab"], "git_sync")

    def test_recent_paths_and_ignore(self):
        p1 = str((self.test_path / "workspace1").resolve())
        p2 = str((self.test_path / "workspace2").resolve())
        self.config_mgr.add_recent_path(p1)
        self.config_mgr.add_recent_path(p2)
        
        cfg = self.config_mgr.config
        self.assertIn(p2, cfg.git_sync.recent_paths)
        self.assertEqual(cfg.git_sync.recent_paths[0], p2)

        # Ignore toggle
        self.api.toggle_git_ignore("ignore_repo", add=True)
        self.assertIn("ignore_repo", self.config_mgr.config.git_sync.ignore_list)
        self.api.toggle_git_ignore("ignore_repo", add=False)
        self.assertNotIn("ignore_repo", self.config_mgr.config.git_sync.ignore_list)

    def test_skills_cascade_delete_and_tombstones(self):
        # Tạo mock central library và mock agent directories
        lib_dir = self.test_path / "central_lib"
        (lib_dir / "skills").mkdir(parents=True, exist_ok=True)
        
        agent_dir = self.test_path / "agents" / "anti"
        (agent_dir / "skills").mkdir(parents=True, exist_ok=True)
        
        # Tạo 1 skill mẫu trong thư mục skills/
        skill_name = "sample_skill_test"
        (lib_dir / "skills" / skill_name).mkdir(parents=True, exist_ok=True)
        ((lib_dir / "skills" / skill_name) / "SKILL.md").write_text("# Sample Skill", encoding="utf-8")
        
        (agent_dir / "skills" / skill_name).mkdir(parents=True, exist_ok=True)
        ((agent_dir / "skills" / skill_name) / "SKILL.md").write_text("# Sample Skill Copy", encoding="utf-8")
        
        # Đặt config
        self.config_mgr.config.skills_sync.skills_lib = str(lib_dir)
        self.config_mgr.config.skills_sync.custom_agent_paths["anti"] = str(agent_dir)
        
        # Gọi delete_skills_cascade
        res = self.api.delete_skills_cascade([skill_name])
        self.assertTrue(res["success"])
        self.assertIn(skill_name, res["deleted_skills"])
        
        # Kiểm tra file đã bị xóa ở cả library và agent
        self.assertFalse((lib_dir / "skills" / skill_name).exists())
        self.assertFalse((agent_dir / "skills" / skill_name).exists())
        
        # Kiểm tra tombstone đã được ghi
        tombstone_file = lib_dir / ".vxdevsync" / "tombstones.json"
        self.assertTrue(tombstone_file.exists())
        self.assertIn(skill_name, tombstone_file.read_text(encoding="utf-8"))

    def test_rules_adapter_sync(self):
        lib_dir = self.test_path / "central_lib"
        lib_dir.mkdir(parents=True, exist_ok=True)
        
        claude_dir = self.test_path / "agents" / "claude"
        claude_dir.mkdir(parents=True, exist_ok=True)
        
        adapter = AdapterEngine()
        agents_content = "# AGENTS.md Global Rules\nRule 1: No LaTeX"
        (lib_dir / "AGENTS.md").write_text(agents_content, encoding="utf-8")
        
        deployed = adapter.deploy_rules_downstream(
            library_path=lib_dir,
            agent_paths={"claude": str(claude_dir)},
            selected_agents=["claude"]
        )
        self.assertTrue(any("claude" in item for item in deployed))
        self.assertTrue((claude_dir / "CLAUDE.md").exists())
        self.assertIn("Rule 1: No LaTeX", (claude_dir / "CLAUDE.md").read_text(encoding="utf-8"))

    def test_git_scan_and_status(self):
        # Tạo mock repo Git
        repo_dir = self.test_path / "mock_repo"
        repo_dir.mkdir(parents=True, exist_ok=True)
        
        # Init git repo
        self.api._git_engine.run_cmd(["init"], cwd=repo_dir)
        self.api._git_engine.run_cmd(["config", "user.name", "Test User"], cwd=repo_dir)
        self.api._git_engine.run_cmd(["config", "user.email", "test@example.com"], cwd=repo_dir)
        
        # Tạo file và commit
        (repo_dir / "README.md").write_text("# Test Repo", encoding="utf-8")
        self.api._git_engine.run_cmd(["add", "-A"], cwd=repo_dir)
        self.api._git_engine.run_cmd(["commit", "-m", "initial commit"], cwd=repo_dir)
        
        # Quét repo
        status = self.api._git_engine.get_repo_status(repo_dir, self.test_path)
        self.assertEqual(status.name, "mock_repo")
        self.assertTrue(status.is_clean)
        self.assertFalse(status.is_dirty)
        self.assertEqual(status.dirty_files_count, 0)
        
        # Tạo dirty state
        (repo_dir / "new_file.txt").write_text("Hello dirty", encoding="utf-8")
        dirty_status = self.api._git_engine.get_repo_status(repo_dir, self.test_path)
        self.assertFalse(dirty_status.is_clean)
        self.assertTrue(dirty_status.is_dirty)
        self.assertEqual(dirty_status.dirty_files_count, 1)

    def test_git_ignored_repo_scan(self):
        # Tạo 2 mock repos
        repo1 = self.test_path / "repo_normal"
        repo2 = self.test_path / "repo_ignored"
        repo1.mkdir(parents=True, exist_ok=True)
        repo2.mkdir(parents=True, exist_ok=True)

        self.api._git_engine.run_cmd(["init"], cwd=repo1)
        self.api._git_engine.run_cmd(["init"], cwd=repo2)

        # Thêm repo2 vào ignore_list của config
        self.config_mgr.config.git_sync.ignore_list.append("repo_ignored")
        self.config_mgr.config.git_sync.scan_path = str(self.test_path)

        # Quét workspace qua BridgeApi
        res = self.api.scan_git_workspace(str(self.test_path))
        self.assertTrue(res["success"])
        repos = res["repos"]
        self.assertEqual(len(repos), 2)

        # repo_ignored vẫn có trong danh sách nhưng có cờ is_ignored = True
        ignored = next(r for r in repos if r["name"] == "repo_ignored")
        normal = next(r for r in repos if r["name"] == "repo_normal")

        self.assertTrue(ignored["is_ignored"])
        self.assertEqual(ignored["sync_state"], "IGNORED")
        self.assertEqual(ignored["suggested_action"], "Đã loại trừ")

        self.assertFalse(normal["is_ignored"])

    def test_sync_git_repos_error_details(self):
        # Tạo mock repo không có remote để kiểm tra cơ chế báo lỗi chi tiết
        repo_no_remote = self.test_path / "repo_no_remote_err"
        repo_no_remote.mkdir(parents=True, exist_ok=True)
        self.api._git_engine.run_cmd(["init", "-b", "main"], cwd=repo_no_remote)
        self.api._git_engine.run_cmd(["config", "user.name", "Tester"], cwd=repo_no_remote)
        self.api._git_engine.run_cmd(["config", "user.email", "test@example.com"], cwd=repo_no_remote)
        (repo_no_remote / "file.txt").write_text("content", encoding="utf-8")
        self.api._git_engine.run_cmd(["add", "."], cwd=repo_no_remote)
        self.api._git_engine.run_cmd(["commit", "-m", "init"], cwd=repo_no_remote)

        # Chạy sync pull trên repo chưa gắn remote
        res = self.api.sync_git_repos([str(repo_no_remote)], action="pull")
        self.assertTrue(res["success"])
        self.assertEqual(res["total"], 1)
        self.assertEqual(res["success_count"], 0)
        self.assertEqual(res["failed_count"], 1)
        self.assertEqual(len(res["results"]), 1)

        err_item = res["results"][0]
        self.assertFalse(err_item["success"])
        self.assertEqual(err_item["name"], "repo_no_remote_err")
        self.assertIn("remote", err_item["message"].lower())
        self.assertIn("cmd", err_item)
        self.assertIn("raw_error", err_item)

    def test_sync_git_repos_skips_ignored(self):
        # Kiểm tra repo nằm trong ignore_list được bỏ qua an toàn khi gọi sync_git_repos
        repo_ignored = self.test_path / "repo_ignored_test"
        repo_ignored.mkdir(parents=True, exist_ok=True)
        self.api._config_manager.add_to_git_ignore("repo_ignored_test")

        res = self.api.sync_git_repos([str(repo_ignored)], action="pull")
        self.assertTrue(res["success"])
        self.assertEqual(res["total"], 1)
        self.assertEqual(res["success_count"], 0)
        self.assertEqual(res["failed_count"], 1)
        self.assertIn("loại trừ", res["results"][0]["message"])

    def test_git_error_hints_classification(self):
        # Kiểm tra phân loại lỗi Git sang gợi ý tiếng Việt chính xác
        repo_test = self.test_path / "repo_hint_test"
        repo_test.mkdir(parents=True, exist_ok=True)
        self.api._git_engine.run_cmd(["init", "-b", "main"], cwd=repo_test)
        self.api._git_engine.run_cmd(["config", "user.name", "Tester"], cwd=repo_test)
        self.api._git_engine.run_cmd(["config", "user.email", "test@example.com"], cwd=repo_test)
        (repo_test / "file.txt").write_text("content", encoding="utf-8")
        self.api._git_engine.run_cmd(["add", "."], cwd=repo_test)
        self.api._git_engine.run_cmd(["commit", "-m", "init"], cwd=repo_test)
        self.api._git_engine.run_cmd(["remote", "add", "origin", "https://invalid.test/repo.git"], cwd=repo_test)

        # Mock các đầu ra lỗi khác nhau để kiểm tra hint
        from unittest.mock import patch

        cases = [
            ("error: Your local changes to the following files would be overwritten by merge", "Xung đột"),
            ("fatal: unable to access 'https://...': SSL certificate problem: certificate has expired", "chứng chỉ bảo mật SSL/TLS"),
            ("fatal: unable to access 'https://...': The requested URL returned error: 403", "403 Forbidden"),
            ("fatal: unable to access 'https://...': Could not resolve host: invalid.test", "Không tìm thấy host, Offline hoặc Timeout"),
            ("fatal: Not possible to fast-forward, aborting.", "phân kỳ (Diverged)")
        ]

        for mock_err, expected_hint in cases:
            orig_run_cmd = self.api._git_engine.run_cmd
            def mock_run_cmd_side_effect(args, cwd, timeout=15):
                if args[0] == "pull":
                    return (1, "", mock_err)
                return orig_run_cmd(args, cwd, timeout)

            with patch.object(self.api._git_engine, "run_cmd", side_effect=mock_run_cmd_side_effect):
                res = self.api._git_engine.sync_single_repo(repo_test, action="pull")
                self.assertFalse(res["success"])
                self.assertIn(expected_hint, res["message"])


if __name__ == "__main__":
    unittest.main()
