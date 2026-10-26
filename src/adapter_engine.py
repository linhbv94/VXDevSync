import hashlib
from pathlib import Path
from typing import List, Dict, Tuple, Optional

CLAUDE_HEADER_METADATA = """# Claude Code Project & Global Instructions

> **Source:** Synchronized automatically by VXDevSync from AGENTS.md
> **Note:** Follow these global rules and guidelines strictly.

"""

class AdapterEngine:
    """Chịu trách nhiệm chuyển đổi và đồng bộ quy tắc chung: AGENTS.md ↔ CLAUDE.md."""

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

    def get_agent_rules_files(self, agent_name: str, agent_dir_str: str) -> List[Path]:
        if not agent_dir_str:
            return []
        agent_dir = Path(agent_dir_str)
        files = []

        if agent_name in ["anti", "codex", "antigravity"]:
            if agent_dir.name == "skills":
                files.append(agent_dir.parent / "AGENTS.md")
            else:
                files.append(agent_dir / "AGENTS.md")
        elif agent_name == "claude":
            files.append(agent_dir / "CLAUDE.md")

        return [f for f in files if f.exists()]

    def sync_rules_upstream(
        self,
        library_path: Path,
        agent_paths: Dict[str, str],
        selected_agents: List[str]
    ) -> Tuple[bool, str]:
        """
        [Upstream Rules Sync]: Phát hiện nếu AGENTS.md hoặc CLAUDE.md ở bất kỳ Agent nào mới hơn
        bản trong Central Library (AGENTS.md), tự động gom về Library.
        """
        lib_root_file = library_path / "AGENTS.md"
        
        # Nếu Central Library đã có AGENTS.md, Central Library là Single Source of Truth
        if lib_root_file.exists() and lib_root_file.stat().st_size > 0:
            return False, "Central Library AGENTS.md là Single Source of Truth."

        # Nếu Central Library chưa có AGENTS.md, nạp từ Agent có rules hợp lệ
        for agent_name in selected_agents:
            agent_dir_str = agent_paths.get(agent_name, "")
            rules_files = self.get_agent_rules_files(agent_name, agent_dir_str)

            for rf in rules_files:
                if rf.exists() and rf.stat().st_size > 0:
                    try:
                        with open(rf, "r", encoding="utf-8") as f:
                            content = f.read()

                        if rf.name == "CLAUDE.md" and CLAUDE_HEADER_METADATA.strip() in content:
                            content = content.replace(CLAUDE_HEADER_METADATA, "").strip()

                        library_path.mkdir(parents=True, exist_ok=True)
                        with open(lib_root_file, "w", encoding="utf-8") as f:
                            f.write(content)

                        return True, f"Khởi tạo AGENTS.md cho Central Library từ {agent_name} ({rf.name})."
                    except Exception as e:
                        return False, f"Lỗi đọc rules từ {agent_name}: {e}"

        return False, "Chưa tìm thấy rules nào để khởi tạo."

    def deploy_rules_downstream(
        self,
        library_path: Path,
        agent_paths: Dict[str, str],
        selected_agents: List[str]
    ) -> List[str]:
        """
        [Downstream Rules Deploy]: Phân bổ AGENTS.md từ Central Library sang các Agent đang active.
        Tự động tạo CLAUDE.md có header tương thích cho Claude Code.
        """
        lib_root_file = library_path / "AGENTS.md"
        if not lib_root_file.exists():
            return []

        try:
            with open(lib_root_file, "r", encoding="utf-8") as f:
                base_content = f.read()
        except Exception:
            return []

        claude_content = CLAUDE_HEADER_METADATA + base_content
        deployed = []

        for agent_name in selected_agents:
            agent_dir_str = agent_paths.get(agent_name, "")
            if not agent_dir_str:
                continue

            agent_dir = Path(agent_dir_str)
            agent_dir.mkdir(parents=True, exist_ok=True)

            if agent_name in ["anti", "codex", "antigravity"]:
                target_file = agent_dir.parent / "AGENTS.md" if agent_dir.name == "skills" else agent_dir / "AGENTS.md"
                target_hash = self.get_file_hash(target_file)
                if self.get_file_hash(lib_root_file) != target_hash:
                    with open(target_file, "w", encoding="utf-8") as f:
                        f.write(base_content)
                    deployed.append(f"{agent_name} (AGENTS.md)")

            elif agent_name == "claude":
                target_file = agent_dir / "CLAUDE.md"
                # So sánh nội dung
                current_text = ""
                if target_file.exists():
                    try:
                        with open(target_file, "r", encoding="utf-8") as f:
                            current_text = f.read()
                    except Exception:
                        pass
                if current_text != claude_content:
                    with open(target_file, "w", encoding="utf-8") as f:
                        f.write(claude_content)
                    deployed.append("claude (CLAUDE.md)")

        return deployed
