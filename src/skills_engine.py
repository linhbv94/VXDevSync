import os
import shutil
import hashlib
import fnmatch
import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Set, Tuple

@dataclass
class AgentPresence:
    exists: bool = False
    is_synced: bool = False
    mtime: float = 0.0
    file_count: int = 0

@dataclass
class SkillItem:
    name: str
    in_library: bool = False
    agents: Dict[str, AgentPresence] = field(default_factory=dict)
    is_tombstoned: bool = False

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        return d

@dataclass
class SkillsSyncSummary:
    success: bool
    upstream_collected: List[str] = field(default_factory=list)
    downstream_deployed: List[str] = field(default_factory=list)
    rules_deployed: List[str] = field(default_factory=list)
    purged_tombstones: List[str] = field(default_factory=list)
    git_pushed: bool = False
    message: str = ""

class SkillsEngine:
    """Xử lý đồng bộ Kỹ năng (skills/), Cascade Delete và Tombstone Manifest chống hồi sinh."""

    @staticmethod
    def validate_skill_name(name: str) -> str:
        if (not isinstance(name, str) or not name or name != name.strip()
                or name in (".", "..", ".system", ".git")
                or any(c in name for c in '/\\:\x00')
                or Path(name).is_absolute()):
            raise ValueError("Tên skill không hợp lệ hoặc nằm ngoài phạm vi cho phép")
        return name

    @classmethod
    def skill_directory(cls, library_or_agent: Path, name: str) -> Path:
        cls.validate_skill_name(name)
        root = library_or_agent / "skills"
        candidate = root / name
        if root.is_symlink() or candidate.is_symlink() or candidate.resolve().parent != root.resolve():
            raise ValueError("Không thao tác skill qua symlink hoặc ngoài thư mục skills")
        return candidate

    @staticmethod
    def is_ignored(rel_path: str, ignore_patterns: List[str]) -> bool:
        rel_str = rel_path.replace("\\", "/")
        parts = rel_str.split("/")
        if ".system" in parts:
            return True
        for pattern in ignore_patterns:
            clean_pat = pattern.replace("\\", "/")
            if fnmatch.fnmatch(rel_str, clean_pat) or any(fnmatch.fnmatch(p, clean_pat.strip("*/")) for p in parts):
                return True
        return False

    @staticmethod
    def get_file_hash(filepath: Path) -> str:
        if not filepath.exists() or not filepath.is_file():
            return ""
        hasher = hashlib.md5()
        try:
            with open(filepath, "rb") as f:
                while chunk := f.read(8192):
                    hasher.update(chunk)
            return hasher.hexdigest()
        except Exception:
            return ""

    def get_dir_hash_and_mtime(self, dir_path: Path, ignore_patterns: List[str]) -> Tuple[str, float, int]:
        """Tính toán tổng hợp mã hash và mtime lớn nhất của toàn bộ files trong một thư mục skill."""
        if not dir_path.exists() or not dir_path.is_dir():
            return "", 0.0, 0

        hasher = hashlib.md5()
        max_mtime = 0.0
        file_count = 0

        for root, dirs, files in os.walk(dir_path):
            if ".system" in dirs:
                dirs.remove(".system")
            if ".git" in dirs:
                dirs.remove(".git")

            for file_name in sorted(files):
                fpath = Path(root) / file_name
                try:
                    rel = str(fpath.relative_to(dir_path))
                    if self.is_ignored(rel, ignore_patterns):
                        continue
                    mtime = fpath.stat().st_mtime
                    if mtime > max_mtime:
                        max_mtime = mtime
                    file_count += 1
                    fhash = self.get_file_hash(fpath)
                    hasher.update(f"{rel}:{fhash}".encode("utf-8"))
                except Exception:
                    continue

        return hasher.hexdigest(), max_mtime, file_count

    def get_skills_inventory(
        self,
        library_path: Path,
        agent_paths: Dict[str, str],
        active_agents: List[str],
        ignore_patterns: List[str],
        deleted_skills: List[Dict[str, Any]]
    ) -> List[SkillItem]:
        """Quét và tổng hợp bảng ma trận toàn bộ các skills trong Thư viện trung tâm và các Agent."""
        tombstone_names = {item.get("name") for item in deleted_skills if item.get("name")}
        skills_set: Set[str] = set()

        lib_skills_dir = library_path / "skills"
        if lib_skills_dir.exists() and lib_skills_dir.is_dir():
            for child in lib_skills_dir.iterdir():
                if child.is_dir() and child.name != ".git" and child.name != ".system":
                    skills_set.add(child.name)

        for agent in active_agents:
            agent_dir_str = agent_paths.get(agent, "")
            if not agent_dir_str:
                continue
            agent_skills = Path(agent_dir_str) / "skills"
            if agent_skills.exists() and agent_skills.is_dir():
                for child in agent_skills.iterdir():
                    if child.is_dir() and child.name != ".git" and child.name != ".system":
                        skills_set.add(child.name)

        inventory: List[SkillItem] = []

        for skill_name in sorted(skills_set):
            in_lib = (lib_skills_dir / skill_name).is_dir()
            lib_hash, _, _ = self.get_dir_hash_and_mtime(lib_skills_dir / skill_name, ignore_patterns) if in_lib else ("", 0.0, 0)

            agents_dict: Dict[str, AgentPresence] = {}
            for agent in ["anti", "codex", "claude"]:
                agent_dir_str = agent_paths.get(agent, "")
                if not agent_dir_str:
                    agents_dict[agent] = AgentPresence(exists=False, is_synced=False)
                    continue

                agent_skill_dir = Path(agent_dir_str) / "skills" / skill_name
                exists = agent_skill_dir.is_dir()
                if exists:
                    ag_hash, ag_mtime, count = self.get_dir_hash_and_mtime(agent_skill_dir, ignore_patterns)
                    is_synced = (in_lib and ag_hash == lib_hash and lib_hash != "")
                    agents_dict[agent] = AgentPresence(exists=True, is_synced=is_synced, mtime=ag_mtime, file_count=count)
                else:
                    agents_dict[agent] = AgentPresence(exists=False, is_synced=False)

            item = SkillItem(
                name=skill_name,
                in_library=in_lib,
                agents=agents_dict,
                is_tombstoned=(skill_name in tombstone_names)
            )
            inventory.append(item)

        return inventory

    def sync_tombstones_from_git_repo(self, library_path: Path, agent_paths: Dict[str, str], all_agents: List[str]) -> List[str]:
        """
        Đọc file .vxdevsync/tombstones.json trong Central Library repo.
        Tự động XÓA SẠCH các skills đã bị khai tử khỏi tất cả các Agent trên máy này (Multi-device cleanup).
        """
        tombstone_file = library_path / ".vxdevsync" / "tombstones.json"
        if not tombstone_file.exists():
            return []

        try:
            with open(tombstone_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            tombstones = data.get("tombstones", [])
        except Exception:
            return []

        for item in tombstones:
            self.validate_skill_name(item.get("name") if isinstance(item, dict) else item)
        purged = []
        for item in tombstones:
            skill_name = item.get("name") if isinstance(item, dict) else str(item)
            if not skill_name:
                continue

            # Xóa khỏi Central Library nếu lỡ còn
            lib_skill_dir = self.skill_directory(library_path, skill_name)
            if lib_skill_dir.exists():
                shutil.rmtree(lib_skill_dir)
                purged.append(f"library:{skill_name}")

            # Xóa sạch khỏi toàn bộ các Agent
            for agent in all_agents:
                agent_dir_str = agent_paths.get(agent, "")
                if not agent_dir_str:
                    continue
                ag_skill_dir = self.skill_directory(Path(agent_dir_str), skill_name)
                if ag_skill_dir.exists():
                    shutil.rmtree(ag_skill_dir)
                    purged.append(f"{agent}:{skill_name}")

        return purged

    def remove_tombstone_from_git_repo(self, library_path: Path, skill_name: str) -> bool:
        """Gỡ bỏ một skill khỏi file .vxdevsync/tombstones.json khi người dùng phục hồi."""
        self.validate_skill_name(skill_name)
        tombstone_file = library_path / ".vxdevsync" / "tombstones.json"
        if not tombstone_file.exists():
            return False

        try:
            with open(tombstone_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            tombstones = data.get("tombstones", [])
            new_tombstones = [item for item in tombstones if (item.get("name") if isinstance(item, dict) else str(item)) != skill_name]
            
            import datetime
            now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()
            data["tombstones"] = new_tombstones
            data["updated_at"] = now_iso
            
            with open(tombstone_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            return True
        except Exception as e:
            print(f"[SkillsEngine] Lỗi gỡ tombstone: {e}")
            return False

    def scan_and_sync_upstream(
        self,
        library_path: Path,
        agent_paths: Dict[str, str],
        selected_agents: List[str],
        ignore_patterns: List[str],
        deleted_skills: List[Dict[str, Any]]
    ) -> List[str]:
        """
        Pha Upstream: Quét các agent active.
        CHỐT CHẶN TOMBSTONE: Nếu file/skill nằm trong danh sách đã xóa, tự động XÓA KHỎI AGENT thay vì copy về library!
        """
        tombstone_names = {self.validate_skill_name(item.get("name")) for item in deleted_skills if item.get("name")}
        library_skills_dir = library_path / "skills"
        library_skills_dir.mkdir(parents=True, exist_ok=True)

        synced_files = []
        candidates = {}

        for agent_name in selected_agents:
            agent_dir_str = agent_paths.get(agent_name, "")
            if not agent_dir_str:
                continue

            agent_skills_dir = Path(agent_dir_str) / "skills"
            if not agent_skills_dir.exists():
                continue

            # Kiểm tra và dọn dẹp các thư mục skill nằm trong tombstone
            for skill_dir in agent_skills_dir.iterdir():
                if skill_dir.is_dir() and skill_dir.name in tombstone_names:
                    shutil.rmtree(skill_dir)

            for root, dirs, files in os.walk(agent_skills_dir):
                if ".system" in dirs:
                    dirs.remove(".system")
                if ".git" in dirs:
                    dirs.remove(".git")

                for file_name in files:
                    agent_file = Path(root) / file_name
                    try:
                        rel_path = agent_file.relative_to(agent_skills_dir)
                    except ValueError:
                        continue

                    # Nếu thuộc skill đã bị xóa, bỏ qua
                    skill_root_name = rel_path.parts[0] if rel_path.parts else ""
                    if skill_root_name in tombstone_names:
                        continue

                    rel_str = str(rel_path)
                    if self.is_ignored(rel_str, ignore_patterns):
                        continue

                    library_file = library_skills_dir / rel_path
                    agent_hash = self.get_file_hash(agent_file)
                    lib_hash = self.get_file_hash(library_file)

                    if agent_hash and agent_hash != lib_hash:
                        agent_mtime = agent_file.stat().st_mtime
                        lib_mtime = library_file.stat().st_mtime if library_file.exists() else 0
                        if agent_mtime > lib_mtime:
                            current = candidates.get(rel_path)
                            if current is None or agent_mtime > current[0]:
                                candidates[rel_path] = (agent_mtime, agent_name, agent_file)

        for rel_path in sorted(candidates, key=lambda p: p.as_posix()):
            _, agent_name, agent_file = candidates[rel_path]
            library_file = library_skills_dir / rel_path
            library_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(agent_file, library_file)
            synced_files.append(f"{agent_name}: {rel_path.as_posix()}")

        return synced_files

    def deploy_skills_downstream(
        self,
        library_path: Path,
        agent_paths: Dict[str, str],
        selected_agents: List[str],
        ignore_patterns: List[str]
    ) -> List[str]:
        """Pha Downstream: Phân bổ toàn bộ skills chuẩn từ Central Library sang các Agent đang active."""
        library_skills_dir = library_path / "skills"
        if not library_skills_dir.exists():
            return []

        deployed_agents = []

        for agent_name in selected_agents:
            agent_dir_str = agent_paths.get(agent_name, "")
            if not agent_dir_str:
                continue

            target_skills_dir = Path(agent_dir_str) / "skills"
            target_skills_dir.mkdir(parents=True, exist_ok=True)

            for root, dirs, files in os.walk(library_skills_dir):
                if ".system" in dirs:
                    dirs.remove(".system")
                if ".git" in dirs:
                    dirs.remove(".git")

                for file_name in files:
                    src_file = Path(root) / file_name
                    try:
                        rel_path = src_file.relative_to(library_skills_dir)
                    except ValueError:
                        continue

                    if self.is_ignored(str(rel_path), ignore_patterns):
                        continue

                    dest_file = target_skills_dir / rel_path
                    dest_file.parent.mkdir(parents=True, exist_ok=True)

                    src_hash = self.get_file_hash(src_file)
                    dest_hash = self.get_file_hash(dest_file)

                    if src_hash != dest_hash:
                        shutil.copy2(src_file, dest_file)

            deployed_agents.append(agent_name)

        return deployed_agents

    def execute_delete_cascade(
        self,
        skill_names: List[str],
        library_path: Path,
        agent_paths: Dict[str, str],
        all_agents: List[str]
    ) -> Dict[str, Any]:
        """
        Xóa vật lý triệt để danh sách skills tại Central Library và toàn bộ Agent.
        Tự động cập nhật file .vxdevsync/tombstones.json trong Central Git repo.
        """
        # Validate the entire request before the first mutation.
        for name in skill_names:
            self.skill_directory(library_path, name)
            for agent in all_agents:
                if agent_paths.get(agent):
                    self.skill_directory(Path(agent_paths[agent]), name)
        deleted_locations = []

        # 1. Cập nhật .vxdevsync/tombstones.json trong library repo
        tombstone_dir = library_path / ".vxdevsync"
        tombstone_dir.mkdir(parents=True, exist_ok=True)
        tombstone_file = tombstone_dir / "tombstones.json"

        existing_tombstones = []
        if tombstone_file.exists():
            try:
                with open(tombstone_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                existing_tombstones = data.get("tombstones", [])
            except Exception:
                pass

        import datetime
        now_iso = datetime.datetime.now(datetime.timezone.utc).isoformat()

        for name in skill_names:
            existing_tombstones = [item for item in existing_tombstones if (item.get("name") if isinstance(item, dict) else str(item)) != name]
            existing_tombstones.append({"name":name,"deleted_at":now_iso,"deleted_by":"vxdevsync"})
        import tempfile
        fd, temporary = tempfile.mkstemp(prefix="tombstones_",dir=tombstone_dir)
        try:
            with os.fdopen(fd,"w",encoding="utf-8") as stream:
                json.dump({"schema_version":"1.0.0","updated_at":now_iso,"tombstones":existing_tombstones},stream,indent=2,ensure_ascii=False)
                stream.flush();os.fsync(stream.fileno())
            os.replace(temporary,tombstone_file)
        finally:
            if os.path.exists(temporary):os.unlink(temporary)
        for name in skill_names:
            targets = [("Central Library",self.skill_directory(library_path,name))]
            targets += [(agent,self.skill_directory(Path(agent_paths[agent]),name)) for agent in all_agents if agent_paths.get(agent)]
            for label,target in targets:
                if target.exists():
                    shutil.rmtree(target)
                    deleted_locations.append(f"{label}: skills/{name}")

        return {
            "success": True,
            "deleted_skills": skill_names,
            "deleted_locations": deleted_locations
        }
