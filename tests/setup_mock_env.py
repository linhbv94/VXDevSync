#!/usr/bin/env python3
"""
Tạo môi trường giả lập (Mock Environment) toàn diện để kiểm thử VXDevSync:
- Git Multi-Sync: Tạo 7 loại repository đa dạng (clean, dirty, ahead, behind, diverged, no_remote, unborn).
- Skills Auto-Sync: Tạo Central Library (có Git repo) và mock agents (anti, codex, claude).
"""

import os
import shutil
import subprocess
from pathlib import Path

MOCK_ROOT = Path("/tmp/vxdevsync_mock_env")

def run(cmd, cwd):
    return subprocess.run(cmd, cwd=cwd, shell=True, capture_output=True, text=True)

def setup_mock_environment():
    if MOCK_ROOT.exists():
        shutil.rmtree(MOCK_ROOT)
    MOCK_ROOT.mkdir(parents=True, exist_ok=True)
    
    workspace_dir = MOCK_ROOT / "mock_workspace"
    workspace_dir.mkdir(parents=True, exist_ok=True)
    
    remotes_dir = MOCK_ROOT / "mock_remotes"
    remotes_dir.mkdir(parents=True, exist_ok=True)
    
    # ----------------------------------------------------
    # PHẦN 1: TẠO CÁC GIT REPOSITORIES TRONG WORKSPACE
    # ----------------------------------------------------
    print("[Setup] Đang tạo các Mock Git Repositories...")
    
    # Helper tạo remote bare repo
    def make_remote(name):
        bare = remotes_dir / f"{name}.git"
        bare.mkdir(parents=True, exist_ok=True)
        run("git init --bare", cwd=bare)
        return str(bare)

    # 1. repo_clean (Sạch, Up-to-date)
    r1 = workspace_dir / "repo_clean"
    r1.mkdir()
    r1_remote = make_remote("repo_clean")
    run("git init", cwd=r1)
    run("git config user.name 'Dev Mock' && git config user.email 'dev@mock.local'", cwd=r1)
    (r1 / "README.md").write_text("# Clean Repo\nAll clean and up-to-date.")
    run("git add -A && git commit -m 'feat: initial clean commit'", cwd=r1)
    run("git branch -M main", cwd=r1)
    run(f"git remote add origin {r1_remote}", cwd=r1)
    run("git push -u origin main", cwd=r1)

    # 2. repo_dirty (Có uncommitted files)
    r2 = workspace_dir / "repo_dirty"
    r2.mkdir()
    r2_remote = make_remote("repo_dirty")
    run("git init", cwd=r2)
    run("git config user.name 'Dev Mock' && git config user.email 'dev@mock.local'", cwd=r2)
    (r2 / "app.py").write_text("print('version 1.0')")
    run("git add -A && git commit -m 'initial'", cwd=r2)
    run("git branch -M main", cwd=r2)
    run(f"git remote add origin {r2_remote}", cwd=r2)
    run("git push -u origin main", cwd=r2)
    # Tạo thay đổi chưa commit
    (r2 / "app.py").write_text("print('version 2.0 uncommitted')")
    (r2 / "untracked_note.txt").write_text("This is an untracked file.")

    # 3. repo_ahead (Commit local chưa push)
    r3 = workspace_dir / "repo_ahead"
    r3.mkdir()
    r3_remote = make_remote("repo_ahead")
    run("git init", cwd=r3)
    run("git config user.name 'Dev Mock' && git config user.email 'dev@mock.local'", cwd=r3)
    (r3 / "feature.txt").write_text("Base feature")
    run("git add -A && git commit -m 'initial'", cwd=r3)
    run("git branch -M main", cwd=r3)
    run(f"git remote add origin {r3_remote}", cwd=r3)
    run("git push -u origin main", cwd=r3)
    # Thêm 2 commit local
    (r3 / "feature.txt").write_text("Base feature + update 1")
    run("git commit -am 'feat: update 1'", cwd=r3)
    (r3 / "feature.txt").write_text("Base feature + update 2")
    run("git commit -am 'feat: update 2'", cwd=r3)

    # 4. repo_behind (Remote có commit mới)
    r4 = workspace_dir / "repo_behind"
    r4.mkdir()
    r4_remote = make_remote("repo_behind")
    run("git init", cwd=r4)
    run("git config user.name 'Dev Mock' && git config user.email 'dev@mock.local'", cwd=r4)
    (r4 / "file.txt").write_text("Commit 1")
    run("git add -A && git commit -m 'c1'", cwd=r4)
    run("git branch -M main", cwd=r4)
    run(f"git remote add origin {r4_remote}", cwd=r4)
    run("git push -u origin main", cwd=r4)
    # Clone tạm một nơi khác để push vào remote
    tmp_clone = MOCK_ROOT / "tmp_clone_r4"
    run(f"git clone {r4_remote} {tmp_clone}", cwd=MOCK_ROOT)
    run("git config user.name 'Dev Remote' && git config user.email 'remote@mock.local'", cwd=tmp_clone)
    (tmp_clone / "file.txt").write_text("Commit 1 + Remote Commit 2")
    run("git commit -am 'remote commit 2' && git push origin main", cwd=tmp_clone)
    shutil.rmtree(tmp_clone)
    # Fetch tại r4 để git biết nó đang behind
    run("git fetch origin main", cwd=r4)

    # 5. repo_diverged (Vừa ahead vừa behind)
    r5 = workspace_dir / "repo_diverged"
    r5.mkdir()
    r5_remote = make_remote("repo_diverged")
    run("git init", cwd=r5)
    run("git config user.name 'Dev Mock' && git config user.email 'dev@mock.local'", cwd=r5)
    (r5 / "shared.txt").write_text("Common ancestor")
    run("git add -A && git commit -m 'root'", cwd=r5)
    run("git branch -M main", cwd=r5)
    run(f"git remote add origin {r5_remote}", cwd=r5)
    run("git push -u origin main", cwd=r5)
    # Remote push 1 nhánh
    tmp_clone5 = MOCK_ROOT / "tmp_clone_r5"
    run(f"git clone {r5_remote} {tmp_clone5}", cwd=MOCK_ROOT)
    run("git config user.name 'Dev Remote' && git config user.email 'remote@mock.local'", cwd=tmp_clone5)
    (tmp_clone5 / "remote_change.txt").write_text("Remote branch change")
    run("git add -A && git commit -m 'remote diverged commit' && git push origin main", cwd=tmp_clone5)
    shutil.rmtree(tmp_clone5)
    # Local commit 1 thay đổi khác
    (r5 / "local_change.txt").write_text("Local branch change")
    run("git add -A && git commit -m 'local diverged commit'", cwd=r5)
    # Fetch để thấy diverged
    run("git fetch origin main", cwd=r5)

    # 6. repo_no_remote (Không có remote)
    r6 = workspace_dir / "repo_no_remote"
    r6.mkdir()
    run("git init", cwd=r6)
    run("git config user.name 'Dev Mock' && git config user.email 'dev@mock.local'", cwd=r6)
    (r6 / "local_only.txt").write_text("Only local git")
    run("git add -A && git commit -m 'init local repo'", cwd=r6)

    # 7. repo_unborn (Vừa init, chưa có commit)
    r7 = workspace_dir / "repo_unborn"
    r7.mkdir()
    run("git init", cwd=r7)

    # ----------------------------------------------------
    # PHẦN 2: TẠO CENTRAL SKILLS LIBRARY & MOCK AGENTS
    # ----------------------------------------------------
    print("[Setup] Đang tạo Central Skills Library và Mock AI Agents...")
    
    central_lib = MOCK_ROOT / "central_skills_lib"
    central_lib.mkdir(parents=True, exist_ok=True)
    central_remote = make_remote("central_skills_lib")
    
    run("git init", cwd=central_lib)
    run("git config user.name 'Dev Mock' && git config user.email 'dev@mock.local'", cwd=central_lib)
    (central_lib / "AGENTS.md").write_text("# Quy tắc chung AI Agent (Central Rules)\n- Rule 1: No LaTeX\n- Rule 2: snake_case\n", encoding="utf-8")
    
    # Tạo các skills mẫu trong Central Library
    skills_base = central_lib / "skills"
    skills_base.mkdir(parents=True, exist_ok=True)
    
    for s_name in ["mkt_growth", "devops_release", "uxui_styling"]:
        s_dir = skills_base / s_name
        s_dir.mkdir(parents=True, exist_ok=True)
        (s_dir / "SKILL.md").write_text(f"# Skill: {s_name}\nDescription for {s_name}", encoding="utf-8")
        (s_dir / "config.json").write_text('{"active": true}', encoding="utf-8")

    run("git add -A && git commit -m 'chore: initial skills library'", cwd=central_lib)
    run("git branch -M main", cwd=central_lib)
    run(f"git remote add origin {central_remote}", cwd=central_lib)
    run("git push -u origin main", cwd=central_lib)

    # Mock Agents
    agents_root = MOCK_ROOT / "mock_agents"
    agents_root.mkdir(parents=True, exist_ok=True)
    
    anti_dir = agents_root / "anti"
    (anti_dir / "skills").mkdir(parents=True, exist_ok=True)
    # Anti có sẵn mkt_growth và 1 custom skill
    shutil.copytree(skills_base / "mkt_growth", anti_dir / "skills" / "mkt_growth")
    custom_anti = anti_dir / "skills" / "anti_custom_helper"
    custom_anti.mkdir(parents=True, exist_ok=True)
    (custom_anti / "SKILL.md").write_text("# Anti Custom Helper", encoding="utf-8")

    codex_dir = agents_root / "codex"
    (codex_dir / "skills").mkdir(parents=True, exist_ok=True)
    # Codex có sẵn devops_release
    shutil.copytree(skills_base / "devops_release", codex_dir / "skills" / "devops_release")

    claude_dir = agents_root / "claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    (claude_dir / "CLAUDE.md").write_text("# Claude Code Old Rules\nOld content\n", encoding="utf-8")

    print("[Setup] Môi trường giả lập đã sẵn sàng tại:")
    print(f"   - Workspace: {workspace_dir}")
    print(f"   - Central Library: {central_lib}")
    print(f"   - Mock Agents: {agents_root}")
    return {
        "workspace": str(workspace_dir),
        "central_lib": str(central_lib),
        "anti": str(anti_dir),
        "codex": str(codex_dir),
        "claude": str(claude_dir)
    }

if __name__ == "__main__":
    setup_mock_environment()
