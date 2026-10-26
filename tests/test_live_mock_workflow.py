#!/usr/bin/env python3
"""
Test kịch bản end-to-end trên môi trường giả lập (/tmp/vxdevsync_mock_env).
Mô phỏng chính xác các thao tác của người dùng trên Desktop GUI qua BridgeApi.
"""

import os
import sys
import unittest
from pathlib import Path

# Thêm root vào sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

from src.config_manager import ConfigManager
from src.bridge_api import BridgeApi
from tests.setup_mock_env import setup_mock_environment, MOCK_ROOT


class TestLiveMockWorkflow(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        print("\n[LiveMock] Khởi tạo môi trường giả lập...")
        cls.env = setup_mock_environment()
        cls.config_dir = MOCK_ROOT / "test_config"
        cls.config_mgr = ConfigManager(custom_dir=cls.config_dir)
        cls.api = BridgeApi(config_manager=cls.config_mgr)

    def test_01_git_scan_all_types(self):
        print("\n[TEST 01] Quét Git Workspace và nhận diện 7 loại Repository...")
        res = self.api.scan_git_workspace(scan_path=self.env["workspace"], max_depth=2)
        self.assertTrue(res["success"])
        repos = {r["name"]: r for r in res["repos"]}
        
        self.assertEqual(len(repos), 7, f"Kỳ vọng 7 repos, thực tế tìm thấy: {len(repos)}")

        # 1. Clean
        self.assertTrue(repos["repo_clean"]["is_clean"])
        self.assertEqual(repos["repo_clean"]["ahead_count"], 0)
        self.assertEqual(repos["repo_clean"]["behind_count"], 0)
        print("  [OK] repo_clean: Up-to-date chính xác")

        # 2. Dirty
        self.assertTrue(repos["repo_dirty"]["is_dirty"])
        self.assertGreaterEqual(repos["repo_dirty"]["dirty_files_count"], 1)
        print("  [OK] repo_dirty: Phát hiện đúng file chưa commit")

        # 3. Ahead
        self.assertEqual(repos["repo_ahead"]["ahead_count"], 2)
        print("  [OK] repo_ahead: Phát hiện đúng +2 commits ahead")

        # 4. Behind
        self.assertEqual(repos["repo_behind"]["behind_count"], 1)
        print("  [OK] repo_behind: Phát hiện đúng -1 commit behind")

        # 5. Diverged
        self.assertTrue(repos["repo_diverged"]["is_diverged"])
        print("  [OK] repo_diverged: Phát hiện đúng xung đột Ahead & Behind")

        # 6. No Remote
        self.assertFalse(repos["repo_no_remote"]["has_remote"])
        print("  [OK] repo_no_remote: Nhận diện chính xác repo local")

        # 7. Unborn
        self.assertEqual(repos["repo_unborn"]["name"], "repo_unborn")
        print("  [OK] repo_unborn: Xử lý an toàn repo chưa có commit")

    def test_02_git_sync_actions(self):
        print("\n[TEST 02] Thực thi Action Push và Pull trên Git Repos...")
        repo_ahead_path = str(Path(self.env["workspace"]) / "repo_ahead")
        repo_behind_path = str(Path(self.env["workspace"]) / "repo_behind")

        # Push repo_ahead
        res_push = self.api.sync_git_repos([repo_ahead_path], action="push")
        self.assertTrue(res_push["success"])
        self.assertEqual(res_push["success_count"], 1)

        # Pull repo_behind
        res_pull = self.api.sync_git_repos([repo_behind_path], action="pull")
        self.assertTrue(res_pull["success"])
        self.assertEqual(res_pull["success_count"], 1)

        # Quét lại để kiểm tra trạng thái đã được đồng bộ
        res_rescan = self.api.scan_git_workspace(scan_path=self.env["workspace"])
        repos = {r["name"]: r for r in res_rescan["repos"]}

        self.assertEqual(repos["repo_ahead"]["ahead_count"], 0, "repo_ahead sau push phải có ahead = 0")
        self.assertEqual(repos["repo_behind"]["behind_count"], 0, "repo_behind sau pull phải có behind = 0")
        print("  [OK] Push và Pull thành công: Cả 2 repos đã trở về Up-to-date")

    def test_03_skills_inventory_and_unified_sync(self):
        print("\n[TEST 03] Thiết lập Central Library và Chạy Đồng bộ Hợp nhất...")
        # Cấu hình paths
        self.config_mgr.config.skills_sync.skills_lib = self.env["central_lib"]
        self.config_mgr.config.skills_sync.custom_agent_paths["anti"] = self.env["anti"]
        self.config_mgr.config.skills_sync.custom_agent_paths["codex"] = self.env["codex"]
        self.config_mgr.config.skills_sync.custom_agent_paths["claude"] = self.env["claude"]
        self.config_mgr.config.skills_sync.agents = {"anti": 1, "codex": 1, "claude": 1}

        # 1. Inventory ban đầu
        inv = self.api.get_skills_inventory()
        self.assertTrue(inv["success"])
        skill_names = [s["name"] for s in inv["skills"]]
        self.assertIn("anti_custom_helper", skill_names)
        print(f"  [OK] Phát hiện {len(skill_names)} skills trong ma trận (gồm skill mới từ Agent: anti_custom_helper)")

        # 2. Chạy Unified Sync
        sync_res = self.api.sync_skills_unified()
        self.assertTrue(sync_res["success"])
        print(f"  [OK] Unified Sync thành công: Gom {sync_res['upstream_count']} skills mới, phân bổ sang {len(sync_res['downstream_agents'])} agents")
        print(f"  [OK] Git Sync Central Library: {sync_res['git_msg']}")

        # Kiểm tra skill mới đã được gom về Central Library
        central_custom = Path(self.env["central_lib"]) / "skills" / "anti_custom_helper"
        self.assertTrue(central_custom.exists())
        self.assertTrue((central_custom / "SKILL.md").exists())

        # Kiểm tra skill mới đã được deploy sang Codex
        codex_custom = Path(self.env["codex"]) / "skills" / "anti_custom_helper"
        self.assertTrue(codex_custom.exists())

        # Kiểm tra Rules đã đồng bộ sang Claude Code
        claude_rules = Path(self.env["claude"]) / "CLAUDE.md"
        self.assertTrue(claude_rules.exists())
        self.assertIn("Rule 1: No LaTeX", claude_rules.read_text(encoding="utf-8"))
        print("  [OK] Rules Adapter: AGENTS.md đã được đồng bộ chuẩn hóa vào CLAUDE.md")

    def test_04_skills_cascade_delete_and_anti_resurrection(self):
        print("\n[TEST 04] Xóa Kỹ năng Triệt để (Cascade Delete) & Chống Hồi sinh...")
        target_skill = "anti_custom_helper"

        # Thực thi Cascade Delete
        del_res = self.api.delete_skills_cascade([target_skill])
        self.assertTrue(del_res["success"])
        self.assertTrue(del_res["git_committed"])
        print(f"  [OK] Xóa Cascade hoàn tất: {del_res['git_msg']}")
        print(f"  [OK] Danh sách vị trí đã dọn: {del_res['deleted_locations']}")

        # Xác minh xóa vật lý sạch sẽ
        central_target = Path(self.env["central_lib"]) / "skills" / target_skill
        anti_target = Path(self.env["anti"]) / "skills" / target_skill
        codex_target = Path(self.env["codex"]) / "skills" / target_skill
        self.assertFalse(central_target.exists(), "Central Library không được còn tồn tại skill đã xóa")
        self.assertFalse(anti_target.exists(), "Agent Anti không được còn tồn tại skill đã xóa")
        self.assertFalse(codex_target.exists(), "Agent Codex không được còn tồn tại skill đã xóa")

        # Xác minh file tombstones.json
        tombstone_file = Path(self.env["central_lib"]) / ".vxdevsync" / "tombstones.json"
        self.assertTrue(tombstone_file.exists())
        self.assertIn(target_skill, tombstone_file.read_text(encoding="utf-8"))
        print("  [OK] Tombstone Manifest đã ghi nhận kỹ năng bị khai tử")

        # Test chống hồi sinh (Resurrection Guard):
        # Giả lập: Một agent lén tạo lại skill này hoặc có copy cũ
        anti_target.mkdir(parents=True, exist_ok=True)
        (anti_target / "SKILL.md").write_text("# Phục sinh trái phép", encoding="utf-8")

        # Chạy Unified Sync
        sync_again = self.api.sync_skills_unified()
        self.assertTrue(sync_again["success"])

        # Kiểm tra: Skill này KHÔNG được phép đồng bộ ngược lại Central Library vì nằm trong Tombstone!
        self.assertFalse(central_target.exists(), "Chốt chặn Tombstone phải ngăn cản skill hồi sinh lên Central Library!")
        print("  [OK] Chốt chặn Tombstone hoạt động hoàn hảo: Ngăn chặn triệt để Resurrection Bug!")


if __name__ == "__main__":
    unittest.main()
