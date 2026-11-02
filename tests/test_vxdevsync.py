import os
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

    def test_get_git_remote_url(self):
        # 1. Thư mục không tồn tại hoặc không phải git repo
        non_git = self.test_path / "non_git_dir"
        non_git.mkdir(parents=True, exist_ok=True)
        res = self.api.get_git_remote_url(str(non_git))
        self.assertFalse(res["success"])
        self.assertEqual(res["url"], "")

        # 2. Thư mục Git repo có remote origin
        git_dir = self.test_path / "git_with_remote"
        git_dir.mkdir(parents=True, exist_ok=True)
        self.api._git_engine.run_cmd(["init", "-b", "main"], cwd=git_dir)
        expected_url = "https://github.com/test-user/my_skills_lib.git"
        self.api._git_engine.run_cmd(["remote", "add", "origin", expected_url], cwd=git_dir)

        res = self.api.get_git_remote_url(str(git_dir))
        self.assertTrue(res["success"])
        self.assertEqual(res["url"], expected_url)

    def test_save_config_with_skills_git_repo(self):
        # Kiểm tra lưu cấu hình skills_lib và git_repo đồng bộ từ GUI / Onboarding
        test_lib = str(self.test_path / "central_skills")
        test_repo = "https://github.com/my-org/central-skills.git"
        res = self.api.save_config({
            "skills_sync": {
                "skills_lib": test_lib,
                "git_repo": test_repo
            }
        })
        self.assertTrue(res["success"])
        cfg = self.api._config_manager.config
        self.assertEqual(cfg.skills_sync.skills_lib, test_lib)
        self.assertEqual(cfg.skills_sync.git_repo, test_repo)

    def test_push_dirty_repo_auto_commits_and_pushes(self):
        # Thiết lập bare remote và local repo
        bare_remote = self.test_path / "push_remote.git"
        self.api._git_engine.run_cmd(["init", "--bare", str(bare_remote)], cwd=self.test_path)

        local_repo = self.test_path / "push_local_repo"
        local_repo.mkdir(parents=True, exist_ok=True)
        self.api._git_engine.run_cmd(["init", "-b", "main"], cwd=local_repo)
        self.api._git_engine.run_cmd(["config", "user.name", "Tester"], cwd=local_repo)
        self.api._git_engine.run_cmd(["config", "user.email", "test@example.com"], cwd=local_repo)

        (local_repo / "initial.txt").write_text("v1", encoding="utf-8")
        self.api._git_engine.run_cmd(["add", "."], cwd=local_repo)
        self.api._git_engine.run_cmd(["commit", "-m", "init"], cwd=local_repo)
        self.api._git_engine.run_cmd(["remote", "add", "origin", str(bare_remote)], cwd=local_repo)
        self.api._git_engine.run_cmd(["push", "-u", "origin", "main"], cwd=local_repo)

        # Tạo file sửa đổi và file mới (dirty worktree)
        (local_repo / "initial.txt").write_text("v2 dirty modification", encoding="utf-8")
        (local_repo / "new_untracked.txt").write_text("new content", encoding="utf-8")

        code, dirty_status, _ = self.api._git_engine.run_cmd(["status", "--porcelain"], cwd=local_repo)
        self.assertTrue(dirty_status.strip())

        # Thực thi push trên dirty repo: engine phải tự động commit và push thành công
        res = self.api._git_engine.sync_single_repo(local_repo, action="push")
        self.assertTrue(res["success"], f"Push dirty repo thất bại: {res.get('message')}")
        self.assertIn("Đã commit và push thành công", res["message"])

        # Kiểm tra trạng thái sau push: worktree phải clean
        code, status_after, _ = self.api._git_engine.run_cmd(["status", "--porcelain"], cwd=local_repo)
        self.assertEqual(status_after.strip(), "")

        # Kiểm tra log commit tự động
        code, log_out, _ = self.api._git_engine.run_cmd(["log", "-1", "--pretty=%B"], cwd=local_repo)
        self.assertIn("chore: auto-commit changes before push", log_out)

        # Kiểm tra bare remote đã nhận commit mới nhất
        code, local_rev, _ = self.api._git_engine.run_cmd(["rev-parse", "HEAD"], cwd=local_repo)
        code, remote_rev, _ = self.api._git_engine.run_cmd(["rev-parse", "refs/heads/main"], cwd=bare_remote)
        self.assertEqual(local_rev.strip(), remote_rev.strip())

    def test_push_dirty_repo_without_remote_does_not_commit(self):
        no_remote_repo = self.test_path / "no_remote_repo"
        no_remote_repo.mkdir(parents=True, exist_ok=True)
        code, _, _ = self.api._git_engine.run_cmd(["init", "-b", "main"], cwd=no_remote_repo)
        self.assertEqual(code, 0)
        (no_remote_repo / "dirty.txt").write_text("dirty content", encoding="utf-8")

        res = self.api._git_engine.sync_single_repo(no_remote_repo, action="push")
        self.assertFalse(res["success"])
        self.assertIn("Chưa gắn remote", res["message"])

        # Không được tự động commit khi không có remote
        code, log_code, _ = self.api._git_engine.run_cmd(["rev-parse", "HEAD"], cwd=no_remote_repo)
        self.assertNotEqual(code, 0)

    def test_push_dirty_repo_without_identity_fails_and_does_not_push(self):
        bare_remote = self.test_path / "no_ident_remote.git"
        code, _, _ = self.api._git_engine.run_cmd(["init", "--bare", str(bare_remote)], cwd=self.test_path)
        self.assertEqual(code, 0)

        local_repo = self.test_path / "no_ident_local"
        local_repo.mkdir(parents=True, exist_ok=True)
        code, _, _ = self.api._git_engine.run_cmd(["init", "-b", "main"], cwd=local_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["config", "user.name", "Tester"], cwd=local_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["config", "user.email", "tester@example.com"], cwd=local_repo)
        self.assertEqual(code, 0)

        (local_repo / "base.txt").write_text("base", encoding="utf-8")
        code, _, _ = self.api._git_engine.run_cmd(["add", "."], cwd=local_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["commit", "-m", "init"], cwd=local_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["remote", "add", "origin", str(bare_remote)], cwd=local_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["push", "-u", "origin", "main"], cwd=local_repo)
        self.assertEqual(code, 0)

        # Xóa danh tính và cấu hình user.useConfigOnly để ép lỗi khi commit nếu thiếu config
        code, _, _ = self.api._git_engine.run_cmd(["config", "--unset-all", "user.name"], cwd=local_repo)
        code, _, _ = self.api._git_engine.run_cmd(["config", "--unset-all", "user.email"], cwd=local_repo)
        code, _, _ = self.api._git_engine.run_cmd(["config", "user.useConfigOnly", "true"], cwd=local_repo)
        (local_repo / "dirty_no_id.txt").write_text("mod", encoding="utf-8")

        # Lưu lại SHA HEAD trước khi push
        code, rev_before, _ = self.api._git_engine.run_cmd(["rev-parse", "HEAD"], cwd=local_repo)
        self.assertEqual(code, 0)

        # Giả lập môi trường cô lập danh tính để commit chắc chắn thất bại do thiếu identity
        saved_env = {}
        override_keys = [
            "GIT_CONFIG_GLOBAL", "GIT_CONFIG_SYSTEM",
            "GIT_AUTHOR_NAME", "GIT_AUTHOR_EMAIL",
            "GIT_COMMITTER_NAME", "GIT_COMMITTER_EMAIL"
        ]
        for k in override_keys:
            saved_env[k] = os.environ.get(k)
        os.environ["GIT_CONFIG_GLOBAL"] = "/dev/null"
        os.environ["GIT_CONFIG_SYSTEM"] = "/dev/null"
        os.environ.pop("GIT_AUTHOR_NAME", None)
        os.environ.pop("GIT_AUTHOR_EMAIL", None)
        os.environ.pop("GIT_COMMITTER_NAME", None)
        os.environ.pop("GIT_COMMITTER_EMAIL", None)

        try:
            res = self.api._git_engine.sync_single_repo(local_repo, action="push")
            self.assertFalse(res["success"])
            self.assertIn("Lỗi commit tự động", res["message"])
            self.assertIn("user.name", res["message"])

            # Đảm bảo HEAD không thay đổi và remote không nhận commit mới
            code, rev_after, _ = self.api._git_engine.run_cmd(["rev-parse", "HEAD"], cwd=local_repo)
            self.assertEqual(rev_before.strip(), rev_after.strip())
        finally:
            for k, v in saved_env.items():
                if v is None:
                    os.environ.pop(k, None)
                else:
                    os.environ[k] = v

    def test_push_dirty_repo_with_ongoing_merge_fails_safe(self):
        bare_remote = self.test_path / "merge_remote.git"
        code, _, _ = self.api._git_engine.run_cmd(["init", "--bare", str(bare_remote)], cwd=self.test_path)
        self.assertEqual(code, 0)

        local_repo = self.test_path / "merge_local"
        local_repo.mkdir(parents=True, exist_ok=True)
        code, _, _ = self.api._git_engine.run_cmd(["init", "-b", "main"], cwd=local_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["config", "user.name", "Tester"], cwd=local_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["config", "user.email", "test@example.com"], cwd=local_repo)
        self.assertEqual(code, 0)

        (local_repo / "init.txt").write_text("init", encoding="utf-8")
        code, _, _ = self.api._git_engine.run_cmd(["add", "."], cwd=local_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["commit", "-m", "init"], cwd=local_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["remote", "add", "origin", str(bare_remote)], cwd=local_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["push", "-u", "origin", "main"], cwd=local_repo)
        self.assertEqual(code, 0)

        # Tạo file sửa đổi dở dang và tạo cờ MERGE_HEAD giả lập merge dở
        (local_repo / "dirty_merge.txt").write_text("content", encoding="utf-8")
        git_dir = local_repo / ".git"
        (git_dir / "MERGE_HEAD").write_text("0123456789abcdef0123456789abcdef01234567\n", encoding="utf-8")

        res = self.api._git_engine.sync_single_repo(local_repo, action="push")
        self.assertFalse(res["success"])
        self.assertIn("merge/rebase/cherry-pick dở dang", res["message"])

        # Dọn dẹp cờ
        (git_dir / "MERGE_HEAD").unlink(missing_ok=True)

    def test_push_rejected_after_auto_commit_preserves_local_commit(self):
        bare_remote = self.test_path / "reject_remote.git"
        code, _, _ = self.api._git_engine.run_cmd(["init", "--bare", str(bare_remote)], cwd=self.test_path)
        self.assertEqual(code, 0)

        # Clone / tạo repo 1 push commit lên trước
        peer_repo = self.test_path / "reject_peer"
        peer_repo.mkdir(parents=True, exist_ok=True)
        code, _, _ = self.api._git_engine.run_cmd(["init", "-b", "main"], cwd=peer_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["config", "user.name", "Tester"], cwd=peer_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["config", "user.email", "test@example.com"], cwd=peer_repo)
        self.assertEqual(code, 0)
        (peer_repo / "common.txt").write_text("common base", encoding="utf-8")
        code, _, _ = self.api._git_engine.run_cmd(["add", "."], cwd=peer_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["commit", "-m", "init base"], cwd=peer_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["remote", "add", "origin", str(bare_remote)], cwd=peer_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["push", "-u", "origin", "main"], cwd=peer_repo)
        self.assertEqual(code, 0)

        # Repo chính clone từ bare_remote
        local_repo = self.test_path / "reject_local"
        code, _, _ = self.api._git_engine.run_cmd(["clone", str(bare_remote), str(local_repo)], cwd=self.test_path)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["config", "user.name", "Tester"], cwd=local_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["config", "user.email", "test@example.com"], cwd=local_repo)
        self.assertEqual(code, 0)

        # Peer repo đẩy commit mới lên remote (làm remote ahead so với local)
        (peer_repo / "peer.txt").write_text("peer commit", encoding="utf-8")
        code, _, _ = self.api._git_engine.run_cmd(["add", "."], cwd=peer_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["commit", "-m", "peer push"], cwd=peer_repo)
        self.assertEqual(code, 0)
        code, _, _ = self.api._git_engine.run_cmd(["push", "origin", "main"], cwd=peer_repo)
        self.assertEqual(code, 0)

        # Local repo có dirty file, chạy push: auto-commit sẽ tạo commit nhưng push bị reject non-fast-forward
        (local_repo / "local_dirty.txt").write_text("local changes", encoding="utf-8")
        res = self.api._git_engine.sync_single_repo(local_repo, action="push")

        self.assertFalse(res["success"])
        self.assertIn("đã tạo commit cục bộ", res["message"])

        # Kiểm tra commit cục bộ vẫn được bảo toàn tại local_repo
        code, log_out, _ = self.api._git_engine.run_cmd(["log", "-1", "--pretty=%B"], cwd=local_repo)
        self.assertEqual(code, 0)
        self.assertIn("chore: auto-commit changes before push", log_out)


if __name__ == "__main__":
    unittest.main()
