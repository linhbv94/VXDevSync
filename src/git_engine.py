import asyncio
import os
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Tuple, Dict, Any, Optional

@dataclass
class RepoStatus:
    name: str
    path: str
    rel_path: str
    current_branch: str = "main"
    is_git: bool = True
    has_remote: bool = True
    remote_url: str = ""
    is_clean: bool = True
    is_dirty: bool = False
    dirty_files_count: int = 0
    dirty_files: List[str] = field(default_factory=list)
    ahead_count: int = 0
    behind_count: int = 0
    is_diverged: bool = False
    sync_state: str = "UP_TO_DATE"  # UP_TO_DATE, BEHIND, AHEAD, DIVERGED, NO_REMOTE, OFFLINE, AUTH_ERROR, ERROR
    suggested_action: str = "Up-to-date"  # Up-to-date, Auto Pull, Auto Push, Safe-Skip, Manual Merge
    is_ignored: bool = False
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

SYSTEM_EXCLUDE_DIRS = {
    ".git", "node_modules", ".venv", "venv", "build", "dist",
    ".next", ".cache", "__pycache__", ".idea", ".vscode"
}

class GitEngine:
    """Xử lý toàn bộ các thao tác Git: quét workspace, phân tích trạng thái và thực thi pull/push."""

    @staticmethod
    def is_git_available() -> bool:
        return shutil.which("git") is not None

    def run_cmd(self, args: List[str], cwd: Path, timeout: int = 15) -> Tuple[int, str, str]:
        """Thực thi lệnh git subprocess an toàn, ngăn prompt hỏi mật khẩu/passphrase."""
        try:
            env = os.environ.copy()
            env["GIT_TERMINAL_PROMPT"] = "0"
            env["GIT_SSH_COMMAND"] = "ssh -o BatchMode=yes"
            res = subprocess.run(
                ["git"] + args,
                cwd=cwd,
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                env=env,
                timeout=timeout
            )
            return res.returncode, res.stdout.strip(), res.stderr.strip()
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except Exception as e:
            return -1, "", str(e)

    def scan_workspace_for_repos(self, scan_path: Path, ignore_list: Optional[List[str]] = None, max_depth: int = 3) -> List[Path]:
        """Quét đệ quy tìm toàn bộ các repository Git trong thư mục workspace."""
        if not scan_path.exists() or not scan_path.is_dir():
            return []
        
        repos: List[Path] = []
        ignores = set(ignore_list or [])
        self._scan_recursive(scan_path, scan_path, ignores, max_depth, 1, repos)
        return sorted(repos, key=lambda p: str(p).lower())

    def _scan_recursive(self, root: Path, current: Path, ignores: set, max_depth: int, depth: int, acc: List[Path]):
        if depth > max_depth:
            return

        # Bỏ qua các thư mục hệ thống / dependencies cấm quét
        if current.name in SYSTEM_EXCLUDE_DIRS:
            return

        # Nếu là thư mục Git Repository
        if (current / ".git").is_dir():
            acc.append(current)
            # Một khi đã là git repo, không quét sâu vào bên trong
            return

        # Nếu không phải git repo, nhưng nằm trong danh sách ignore thì không cần duyệt cây thư mục con này
        if current.name in ignores:
            return

        try:
            for child in current.iterdir():
                if child.is_dir() and child.name not in SYSTEM_EXCLUDE_DIRS:
                    self._scan_recursive(root, child, ignores, max_depth, depth + 1, acc)
        except (PermissionError, Exception):
            pass

    def get_repo_status(self, repo_path: Path, root_path: Path, ignore_list: Optional[List[str]] = None, timeout: int = 10) -> RepoStatus:
        """Kiểm tra toàn diện trạng thái của một repository đơn lẻ."""
        name = repo_path.name
        try:
            rel_path = str(repo_path.relative_to(root_path))
        except ValueError:
            rel_path = name

        if not (repo_path / ".git").is_dir():
            return RepoStatus(name=name, path=str(repo_path), rel_path=rel_path, is_git=False, sync_state="ERROR", error_message="Not a git repo")

        # Kiểm tra xem repo có nằm trong ignore_list không
        is_ignored = False
        if ignore_list:
            if name in ignore_list or rel_path in ignore_list:
                is_ignored = True
            else:
                parts = Path(rel_path).parts
                if any(part in ignore_list for part in parts):
                    is_ignored = True

        # 1. Nhánh hiện tại
        code, out, _ = self.run_cmd(["branch", "--show-current"], cwd=repo_path, timeout=timeout)
        branch = out.strip() if code == 0 and out.strip() else "main"

        # 2. Kiểm tra Remote & URL
        has_remote = False
        remote_url = ""
        remote_name = "origin"
        code, out, _ = self.run_cmd(["remote"], cwd=repo_path, timeout=timeout)
        if code == 0 and out.strip():
            remotes = [r.strip() for r in out.splitlines() if r.strip()]
            if remotes:
                has_remote = True
                remote_name = "origin" if "origin" in remotes else remotes[0]
                _, url_out, _ = self.run_cmd(["remote", "get-url", remote_name], cwd=repo_path, timeout=timeout)
                remote_url = url_out.strip()

        # 3. Kiểm tra Dirty files (Chưa commit)
        is_dirty = False
        dirty_files = []
        code, out, _ = self.run_cmd(["status", "--porcelain"], cwd=repo_path, timeout=timeout)
        if code == 0 and out:
            dirty_files = [line.strip() for line in out.splitlines() if line.strip()]
            is_dirty = len(dirty_files) > 0

        # Nếu repo đã bị loại trừ (is_ignored), không cần fetch remote để tiết kiệm thời gian
        if is_ignored:
            return RepoStatus(
                name=name,
                path=str(repo_path),
                rel_path=rel_path,
                current_branch=branch,
                is_git=True,
                has_remote=has_remote,
                remote_url=remote_url,
                is_clean=not is_dirty,
                is_dirty=is_dirty,
                dirty_files_count=len(dirty_files),
                dirty_files=dirty_files,
                sync_state="IGNORED",
                suggested_action="Đã loại trừ",
                is_ignored=True
            )

        # Nếu không có remote
        if not has_remote:
            return RepoStatus(
                name=name,
                path=str(repo_path),
                rel_path=rel_path,
                current_branch=branch,
                is_git=True,
                has_remote=False,
                is_clean=not is_dirty,
                is_dirty=is_dirty,
                dirty_files_count=len(dirty_files),
                dirty_files=dirty_files,
                sync_state="NO_REMOTE",
                suggested_action="Link Remote Required"
            )

        # 4. Fetch nhẹ từ remote để lấy offset
        code, _, err = self.run_cmd(["fetch", remote_name, branch], cwd=repo_path, timeout=timeout)
        if code != 0:
            err_lower = err.lower()
            if "could not resolve host" in err_lower or "network is down" in err_lower or "timed out" in err_lower:
                return RepoStatus(
                    name=name, path=str(repo_path), rel_path=rel_path, current_branch=branch,
                    is_git=True, has_remote=True, remote_url=remote_url,
                    is_clean=not is_dirty, is_dirty=is_dirty, dirty_files_count=len(dirty_files), dirty_files=dirty_files,
                    sync_state="OFFLINE", suggested_action="Connection Warning", error_message="Offline"
                )
            if "permission denied" in err_lower or "authentication failed" in err_lower:
                return RepoStatus(
                    name=name, path=str(repo_path), rel_path=rel_path, current_branch=branch,
                    is_git=True, has_remote=True, remote_url=remote_url,
                    is_clean=not is_dirty, is_dirty=is_dirty, dirty_files_count=len(dirty_files), dirty_files=dirty_files,
                    sync_state="AUTH_ERROR", suggested_action="Auth Warning", error_message="Auth failed"
                )

        # 5. Tính commit offset (Ahead / Behind)
        ahead = 0
        behind = 0
        code, out, _ = self.run_cmd(["rev-list", "--left-right", "--count", f"HEAD...{remote_name}/{branch}"], cwd=repo_path, timeout=timeout)
        if code == 0 and out:
            parts = out.split()
            if len(parts) >= 2:
                try:
                    ahead = int(parts[0])
                    behind = int(parts[1])
                except ValueError:
                    pass

        # 6. Đánh giá trạng thái và hành động đề xuất
        if ahead > 0 and behind > 0:
            sync_state = "DIVERGED"
            action = "Manual Merge Required"
        elif behind > 0:
            sync_state = "BEHIND"
            action = "Safe-Skip (Dirty)" if is_dirty else "Auto Pull"
        elif ahead > 0:
            sync_state = "AHEAD"
            action = "Safe-Skip (Dirty)" if is_dirty else "Auto Push"
        else:
            sync_state = "UP_TO_DATE"
            action = "Safe-Skip (Dirty)" if is_dirty else "Up-to-date"

        return RepoStatus(
            name=name,
            path=str(repo_path),
            rel_path=rel_path,
            current_branch=branch,
            is_git=True,
            has_remote=True,
            remote_url=remote_url,
            is_clean=not is_dirty,
            is_dirty=is_dirty,
            dirty_files_count=len(dirty_files),
            dirty_files=dirty_files,
            ahead_count=ahead,
            behind_count=behind,
            is_diverged=(ahead > 0 and behind > 0),
            sync_state=sync_state,
            suggested_action=action
        )

    async def scan_and_check_all_async(self, root_path: Path, ignore_list: List[str], max_depth: int = 3, concurrency: int = 8, timeout: int = 10) -> List[RepoStatus]:
        """Quét và phân tích bất đồng bộ danh sách repository."""
        repo_paths = await asyncio.to_thread(self.scan_workspace_for_repos, root_path, ignore_list, max_depth)
        if not repo_paths:
            return []

        sem = asyncio.Semaphore(concurrency)

        async def _check_one(p: Path) -> RepoStatus:
            async with sem:
                return await asyncio.to_thread(self.get_repo_status, p, root_path, ignore_list, timeout)

        tasks = [_check_one(p) for p in repo_paths]
        results = await asyncio.gather(*tasks)
        return list(results)

    def sync_single_repo(self, repo_path: Path, action: str = "smart_sync", timeout: int = 15) -> Dict[str, Any]:
        """Revalidate the worktree before every mutation; never merge diverged history."""
        def result(success, message, selected=action, cmd="", raw_error=""):
            return {
                "path": str(repo_path),
                "name": repo_path.name,
                "action": selected,
                "success": success,
                "message": message,
                "cmd": cmd,
                "raw_error": raw_error
            }

        if action not in ("smart_sync", "pull", "push"):
            return result(False, "Thao tác Git không hợp lệ")
        if not (repo_path / ".git").is_dir():
            return result(False, "Không phải Git repo")

        code, branch, err = self.run_cmd(["branch", "--show-current"], repo_path, timeout)
        if code or not branch:
            return result(False, "Không xác định được nhánh; không đồng bộ detached HEAD", cmd="git branch --show-current", raw_error=err)

        code, dirty, err = self.run_cmd(["status", "--porcelain"], repo_path, timeout)
        if code:
            return result(False, "Không kiểm tra được trạng thái worktree: " + err, cmd="git status --porcelain", raw_error=err)
        if dirty:
            return result(False, "Bỏ qua an toàn: Repo có file chưa commit (Dirty)", cmd="git status --porcelain", raw_error=f"Dirty files:\n{dirty.strip()}")

        code, remotes, err = self.run_cmd(["remote"], repo_path, timeout)
        names = remotes.splitlines() if not code else []
        remote = "origin" if "origin" in names else (names[0] if names else "")
        if not remote:
            return result(False, "Chưa gắn remote", cmd="git remote", raw_error="No remote configured")

        if action == "smart_sync":
            code, _, err = self.run_cmd(["fetch", remote, branch], repo_path, timeout)
            if code:
                return result(False, "Không xác minh được remote: " + err, cmd=f"git fetch {remote} {branch}", raw_error=err)
            code, counts, err = self.run_cmd(["rev-list", "--left-right", "--count", "HEAD...FETCH_HEAD"], repo_path, timeout)
            if code:
                return result(False, "Không xác định được ahead/behind: " + err, cmd="git rev-list --left-right --count HEAD...FETCH_HEAD", raw_error=err)
            try:
                ahead, behind = map(int, counts.split())
            except ValueError:
                return result(False, "Trạng thái Git không hợp lệ", raw_error=counts)
            if ahead and behind:
                return result(False, "Cần merge thủ công (Diverged)", cmd=f"git fetch {remote} {branch}", raw_error=f"Ahead: {ahead}, Behind: {behind}")
            if not ahead and not behind:
                return result(True, "Đã đồng bộ", "none", cmd=f"git fetch {remote} {branch}")
            action = "push" if ahead else "pull"

        args = ["pull", "--ff-only", remote, branch] if action == "pull" else ["push", remote, f"HEAD:refs/heads/{branch}"]
        code, out, err = self.run_cmd(args, repo_path, timeout)
        cmd_str = f"git {' '.join(args)}"
        raw_output = ((err or "") + ("\n" + out if out else "")).strip()

        if code == 0:
            return result(True, f"Đã {action} thành công", action, cmd=cmd_str, raw_error=raw_output)
        else:
            err_lower = raw_output.lower()
            hint = ""
            if "overwritten by merge" in err_lower or "local changes" in err_lower:
                hint = "Xung đột: Có file thay đổi cục bộ chưa commit hoặc stash."
            elif any(x in err_lower for x in ["auth", "permission denied", "could not read username", "terminal prompts disabled"]):
                hint = "Lỗi xác thực Git Remote (Token / SSH key)."
            elif any(x in err_lower for x in ["could not resolve host", "network is down", "timed out", "unable to access"]):
                hint = "Lỗi kết nối mạng (Offline hoặc Timeout)."
            elif "not possible to fast-forward" in err_lower or "non-fast-forward" in err_lower:
                hint = "Nhánh đã bị phân kỳ (Diverged), không thể auto fast-forward."

            msg = f"Lỗi {action}: {hint} {raw_output}".strip() if hint else f"Lỗi {action}: {raw_output}"
            return result(False, msg, action, cmd=cmd_str, raw_error=raw_output)
